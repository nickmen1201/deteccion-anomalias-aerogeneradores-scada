"""Pipeline completo: datos, modelo de comportamiento normal (NBM), detección EWMA y evaluación CARE.

Parque A de CARE to Compare (Zenodo v6). Cada dataset = una turbina con 1 año de entrenamiento y un periodo de
predicción que contiene un evento (anomalía documentada o normal).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression

from efd_care import CAREScore

ROOT = Path(__file__).resolve().parents[1]
FARM_DIR = ROOT / "data" / "CARE_To_Compare" / "Wind Farm A"
OUT_DIR = ROOT / "outputs"

# Entradas exigidas por el enunciado (sensores identificados en feature_description.csv)
INPUTS = {
    "power_30_avg": "Potencia activa (normalizada)",
    "wind_speed_3_avg": "Velocidad de viento (m/s)",
    "sensor_0_avg": "Temperatura ambiente (°C)",
    "sensor_52_avg": "Velocidad del rotor (rpm)",
}
# Temperaturas de componentes modeladas en todas las turbinas por igual (no se usa la etiqueta del evento)
TARGETS = {
    "sensor_11_avg": "Rodamiento caja multiplicadora",
    "sensor_12_avg": "Aceite caja multiplicadora",
    "sensor_13_avg": "Rodamiento generador (lado acople)",
    "sensor_14_avg": "Rodamiento generador (lado opuesto)",
    "sensor_15_avg": "Devanado estator fase 1",
    "sensor_38_avg": "Transformador fase L1",
    "sensor_41_avg": "Aceite grupo hidráulico",
}
POSSIBLE_POWER = "power_29_avg"

# Parámetros fijados a priori (no se ajustan mirando el periodo de predicción)
CURTAIL_RATIO = 0.9      # potencia real < 90 % de la posible = operación con potencia limitada
VAL_FRACTION = 0.2       # último 20 % del entrenamiento como validación temporal
EWMA_ALPHA = 0.05        # memoria efectiva ~20 pasos (~3,3 h)
THRESHOLD_Q = 0.995      # cuantil del puntaje EWMA en validación (umbral principal)
Q_GRID = (0.90, 0.95, 0.98, 0.99, 0.995, 0.999)  # solo para el análisis de sensibilidad
CRITICALITY = 72         # umbral oficial CARE (12 h de anomalías)
ROLL_STEPS = (6, 36)     # medias móviles de 1 h y 6 h (inercia térmica)


# ---------------------------------------------------------------- Fase 1: datos
def load_events():
    ev = pd.read_csv(FARM_DIR / "event_info.csv", sep=";", parse_dates=["event_start", "event_end"])
    return ev.sort_values("event_id").reset_index(drop=True)


def load_features():
    return pd.read_csv(FARM_DIR / "feature_description.csv", sep=";", encoding="latin-1")


def load_dataset(event_id):
    cols = ["time_stamp", "train_test", "status_type_id", POSSIBLE_POWER, *INPUTS, *TARGETS]
    df = pd.read_csv(FARM_DIR / "datasets" / f"{event_id}.csv", sep=";", usecols=cols, parse_dates=["time_stamp"])
    return df.set_index("time_stamp").sort_index()


def operating_mask(df):
    """Turbina produciendo (potencia positiva). Se puntúa solo aquí. No usa status_type_id porque en el Parque A
    las etiquetas de estado del periodo de predicción no son fiables (nota de Zenodo v6)."""
    return df["power_30_avg"] > 0


def healthy_mask(df):
    """Operación sana para entrenar: estado normal (status 0), produciendo, sin potencia limitada y sin faltantes."""
    curtailed = df["power_30_avg"] < CURTAIL_RATIO * df[POSSIBLE_POWER]
    complete = df[[*INPUTS, *TARGETS]].notna().all(axis=1)
    return (df["status_type_id"] == 0) & operating_mask(df) & ~curtailed & complete


def variables_table():
    fd = load_features()
    rows = []
    for col, label in [*INPUTS.items(), *TARGETS.items()]:
        sensor = col.rsplit("_", 1)[0]
        desc = fd.loc[fd["sensor_name"] == sensor, "description"].iloc[0]
        rows.append({"rol": "entrada" if col in INPUTS else "objetivo", "columna": col,
                     "nombre": label, "descripcion_original": desc})
    return pd.DataFrame(rows)


def summary_table(events):
    rows = []
    for _, ev in events.iterrows():
        df = load_dataset(ev.event_id)
        train = df[df["train_test"] == "train"]
        rows.append({
            "event_id": ev.event_id, "turbina": ev.asset, "tipo": ev.event_label,
            "descripcion": ev.event_description if isinstance(ev.event_description, str) else "",
            "filas_entrenamiento": len(train),
            "filas_entrenamiento_limpias": int(healthy_mask(train).sum()),
            "filas_prediccion": int((df["train_test"] == "prediction").sum()),
            "inicio_evento": ev.event_start, "fin_evento": ev.event_end,
        })
    out = pd.DataFrame(rows)
    out["pct_conservado"] = (100 * out["filas_entrenamiento_limpias"] / out["filas_entrenamiento"]).round(1)
    return out


# ---------------------------------------------------------------- Fase 2: modelo de comportamiento normal
def make_features(df):
    X = df[list(INPUTS)].copy()
    for n in ROLL_STEPS:
        X[f"power_roll{n}"] = df["power_30_avg"].rolling(n, min_periods=1).mean()
        X[f"amb_roll{n}"] = df["sensor_0_avg"].rolling(n, min_periods=1).mean()
    return X


def new_model(kind):
    if kind == "lineal":
        return LinearRegression()
    return HistGradientBoostingRegressor(random_state=0)


def split_train(df):
    """Índices de ajuste y validación: corte temporal del entrenamiento sano (sin barajar)."""
    train_idx = df.index[(df["train_test"] == "train") & healthy_mask(df)]
    cut = int(len(train_idx) * (1 - VAL_FRACTION))
    return train_idx[:cut], train_idx[cut:]


def fit_nbm(df, kind):
    """Entrena un modelo por temperatura objetivo. Devuelve predicciones para todo el dataset y RMSE de validación."""
    X = make_features(df)
    fit_idx, val_idx = split_train(df)
    pred, metrics = pd.DataFrame(index=df.index), []
    for target in TARGETS:
        model = new_model(kind).fit(X.loc[fit_idx], df.loc[fit_idx, target])
        pred[target] = model.predict(X)
        err = df.loc[val_idx, target] - pred.loc[val_idx, target]
        metrics.append({"objetivo": target, "modelo": kind,
                        "rmse_val": float(np.sqrt((err ** 2).mean())), "mae_val": float(err.abs().mean())})
    return pred, pd.DataFrame(metrics), fit_idx, val_idx


# ---------------------------------------------------------------- Fase 3: detección
def anomaly_score(df, pred, val_idx):
    """Residuo estandarizado con estadísticas de validación, suavizado EWMA y máximo |z| entre componentes."""
    op = operating_mask(df)
    resid = (df[list(TARGETS)] - pred).where(op)
    z = (resid - resid.loc[val_idx].mean()) / resid.loc[val_idx].std()
    ewma = z.ewm(alpha=EWMA_ALPHA).mean().where(op)
    score = ewma.abs().max(axis=1)
    driver = ewma.abs().fillna(-1).idxmax(axis=1).where(score.notna())
    return score, driver


def threshold_from_validation(score, val_idx, q):
    """Umbral = cuantil q del puntaje en validación (datos sanos, nunca el periodo de predicción)."""
    return float(score.loc[val_idx].quantile(q))


# ---------------------------------------------------------------- Fase 4: evaluación
# Evaluación CARE con ignore_normal_index=True: en el Parque A los status_type_id del periodo de predicción se
# ignoran, como indican los autores en la nota de Zenodo v6.
def score_event(ev, kind):
    """Ajusta el NBM y calcula el puntaje. Devuelve la serie desde el inicio de validación hasta el final."""
    df = load_dataset(ev.event_id)
    pred, metrics, fit_idx, val_idx = fit_nbm(df, kind)
    score, driver = anomaly_score(df, pred, val_idx)
    metrics.insert(0, "event_id", ev.event_id)
    series = pd.DataFrame({"score": score, "componente": driver, "prueba": df["train_test"] == "prediction",
                           "validacion": df.index.isin(val_idx)}).loc[val_idx[0]:]
    for t in TARGETS:
        series[f"real_{t}"], series[f"pred_{t}"] = df.loc[series.index, t], pred.loc[series.index, t]
    return series, metrics


def evaluate(events, scored, kind, q):
    """Aplica el umbral de cuantil q y evalúa todos los datasets con la implementación oficial de CARE."""
    care = CAREScore(criticality_threshold=CRITICALITY)
    rows = []
    for _, ev in events.iterrows():
        series = scored[ev.event_id]
        threshold = threshold_from_validation(series["score"], series.index[series["validacion"]], q)
        test = series[series["prueba"]]
        alarms = (test["score"] > threshold).fillna(False)
        res = care.evaluate_event(event_start=ev.event_start, event_end=ev.event_end, event_label=ev.event_label,
                                  predicted_anomalies=alarms, ignore_normal_index=True, event_id=int(ev.event_id))
        is_anomaly = ev.event_label == "anomaly"
        detected = bool(res["max_criticality"] >= CRITICALITY)
        first = res["first_time_detected"] if detected and is_anomaly else pd.NaT
        rows.append({
            "event_id": ev.event_id, "modelo": kind, "q": q, "tipo": ev.event_label,
            "descripcion": ev.event_description if isinstance(ev.event_description, str) else "",
            "detectado": detected, "max_criticidad": res["max_criticality"], "primera_deteccion": first,
            "anticipacion_dias": res["early_detection_time"] / pd.Timedelta(days=1)
            if detected and is_anomaly else np.nan,
            "componente_alarma": TARGETS.get(test.loc[first, "componente"], "") if detected and is_anomaly else "",
            "pct_puntos_alarma": 100 * alarms.mean(),
            "coverage_fbeta": res["f_beta_score"], "earliness_ws": res["weighted_score"],
            "accuracy": res["accuracy"], "umbral": threshold,
        })
    summary = {
        "modelo": kind, "q": q, "CARE": care.get_final_score(),
        "coverage": care.calculate_avg_coverage(), "accuracy": care.calculate_avg_accuracy(),
        "reliability": care.calculate_reliability(zero_division=0.0), "earliness": care.calculate_avg_earliness(),
    }
    return pd.DataFrame(rows), summary


def summarize(results, summaries):
    rows = []
    for s in summaries:
        r = results[(results["modelo"] == s["modelo"]) & (results["q"] == s["q"])]
        an, no = r[r["tipo"] == "anomaly"], r[r["tipo"] == "normal"]
        ant = an["anticipacion_dias"].dropna()
        rows.append({
            **s,
            "anomalias_detectadas": int(an["detectado"].sum()), "anomalias_total": len(an),
            "falsas_alarmas": int(no["detectado"].sum()), "normales_total": len(no),
            "anticipacion_mediana_dias": ant.median() if len(ant) else np.nan,
            "anticipacion_min_dias": ant.min() if len(ant) else np.nan,
            "anticipacion_max_dias": ant.max() if len(ant) else np.nan,
        })
    return pd.DataFrame(rows)


def run_all(kinds=("lineal", "gbm"), q_grid=Q_GRID):
    """Ejecuta todo y guarda las tablas. El umbral principal es THRESHOLD_Q; q_grid es solo análisis de sensibilidad."""
    import warnings
    warnings.filterwarnings("ignore")
    OUT_DIR.mkdir(exist_ok=True)
    events = load_events()
    variables_table().to_csv(OUT_DIR / "variables.csv", index=False)
    summary_table(events).to_csv(OUT_DIR / "resumen_datasets.csv", index=False)
    results, summaries, metrics, scored = [], [], [], {}
    for kind in kinds:
        scored[kind] = {}
        for _, ev in events.iterrows():
            scored[kind][ev.event_id], m = score_event(ev, kind)
            metrics.append(m)
        for q in sorted({THRESHOLD_Q, *q_grid}):
            r, s = evaluate(events, scored[kind], kind, q)
            results.append(r), summaries.append(s)
    results, metrics = pd.concat(results, ignore_index=True), pd.concat(metrics, ignore_index=True)
    table = summarize(results, summaries)
    main = results["q"] == THRESHOLD_Q
    results[main].to_csv(OUT_DIR / "resultados.csv", index=False)
    table[table["q"] == THRESHOLD_Q].to_csv(OUT_DIR / "resumen_final.csv", index=False)
    table.to_csv(OUT_DIR / "sensibilidad_umbral.csv", index=False)
    results.to_csv(OUT_DIR / "resultados_sensibilidad.csv", index=False)
    metrics.to_csv(OUT_DIR / "metricas_modelo.csv", index=False)
    return events, results[main], metrics, table, scored


if __name__ == "__main__":
    _, res, met, tab, _ = run_all()
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(met.groupby(["modelo", "objetivo"])["rmse_val"].median().unstack(0).round(2))
    print(res.drop(columns=["umbral"]).round(2).to_string())
    print(tab.round(3).to_string())
