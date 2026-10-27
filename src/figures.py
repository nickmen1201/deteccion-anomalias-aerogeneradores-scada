"""Figuras del informe: PNG a 300 dpi, Arial, texto en negro y legibles en escala de grises.

Colores de serie validados con el validador de paleta (azul y naranja de la paleta de referencia). El modelo
lineal lleva además línea discontinua y marcador hueco para no depender del color.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.lines
import matplotlib.patches
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

from pipeline import OUT_DIR, TARGETS, THRESHOLD_Q

INK, MUTED, GRID, BAND = "#000000", "#555555", "#dddddd", "#e8e8e8"
STYLE = {
    "gbm": dict(color="#2a78d6", linestyle="-", marker="o", mfc="#2a78d6", label="Gradient boosting"),
    "lineal": dict(color="#eb6834", linestyle="--", marker="s", mfc="white", label="Regresión lineal"),
}
WIDTH = 6.3  # pulgadas: ancho de texto con márgenes de 2,54 cm en carta
EVENT_ES = {
    "Generator bearing failure": "Falla rodamiento generador",
    "Gearbox failure": "Falla caja multiplicadora",
    "Gearbox bearings damaged": "Rodamientos caja dañados",
    "Hydraulic group": "Grupo hidráulico",
    "Transformer failure": "Falla transformador",
}

plt.rcParams.update({
    "font.family": "Arial", "font.size": 9, "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "axes.edgecolor": MUTED, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "savefig.dpi": 300,
    "savefig.bbox": "tight", "axes.titlesize": 9, "axes.titleweight": "bold",
})


def _comma(ax, axis="both", decimals=None):
    """Separador decimal con coma (informe en español)."""
    def fmt(v, _):
        s = f"{v:.{decimals}f}" if decimals is not None else f"{v:g}"
        return s.replace(".", ",")
    for a in ([ax.xaxis, ax.yaxis] if axis == "both" else [getattr(ax, f"{axis}axis")]):
        a.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt))


def _save(fig, name):
    path = OUT_DIR / name
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def fig_rmse(metrics):
    """Figura 1: RMSE mediano de validación por componente y modelo (gráfico de puntos)."""
    med = metrics.groupby(["objetivo", "modelo"])["rmse_val"].median().unstack()
    med = med.loc[med["gbm"].sort_values().index]
    y = np.arange(len(med))
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    for i in y:
        ax.plot(med.iloc[i][["gbm", "lineal"]], [i, i], color=GRID, lw=2, zorder=1, marker="")
    for kind in ("lineal", "gbm"):
        s = STYLE[kind]
        ax.plot(med[kind], y, linestyle="none", marker=s["marker"], mfc=s["mfc"], mec=s["color"],
                mew=1.5, ms=7, label=s["label"], zorder=2)
    ax.set_yticks(y, [TARGETS[t] for t in med.index])
    ax.set_xlabel("RMSE mediano en validación (°C)")
    ax.set_xlim(0, np.ceil(med.values.max()) + 0.5)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", ncol=1)
    return _save(fig, "fig1_rmse_modelos.png")


def fig_real_vs_pred(scored, event_id=0, target="sensor_12_avg", days=5):
    """Figura 2: temperatura real frente a predicha en los últimos días de validación de un dataset con falla."""
    s = {k: scored[k][event_id] for k in ("gbm", "lineal")}
    full = s["gbm"]
    last = full.index[full["validacion"]][-1]
    win = full.loc[last - pd.Timedelta(days=days):last]
    win = win.loc[win["validacion"]]
    grid = pd.date_range(win.index[0], win.index[-1], freq="10min")  # NaN donde la turbina no operaba: corta la línea
    fig, ax = plt.subplots(figsize=(WIDTH, 2.8))
    ax.plot(grid, win[f"real_{target}"].reindex(grid), color=INK, lw=1.6, label="Medida real")
    for kind in ("lineal", "gbm"):
        w = s[kind].loc[win.index]
        st = STYLE[kind]
        ax.plot(grid, w[f"pred_{target}"].reindex(grid), color=st["color"], ls=st["linestyle"], lw=1.6,
                label=st["label"])
    _comma(ax, "y", 1)
    ax.set_ylabel(f"{TARGETS[target]} (°C)")
    ax.set_xlabel("Fecha")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d-%m-%Y"))
    ax.legend(loc="upper left", ncol=3, bbox_to_anchor=(0, 1.15))
    err = {k: float(np.sqrt(((win[f"real_{target}"] - s[k].loc[win.index, f"pred_{target}"]) ** 2).mean()))
           for k in ("gbm", "lineal")}
    return _save(fig, "fig2_real_vs_predicho.png"), err


def fig_scores(events, results, scored, kind="gbm", clip=3.0):
    """Figura 3: puntaje EWMA relativo al umbral en el periodo de predicción de cada falla documentada."""
    an = events[events["event_label"] == "anomaly"].reset_index(drop=True)
    res = results[(results["modelo"] == kind)].set_index("event_id")
    fig, axes = plt.subplots(4, 3, figsize=(WIDTH, 7.6), sharey=True)
    for ax, (_, ev) in zip(axes.flat, an.iterrows()):
        s = scored[kind][ev.event_id]
        test = s[s["prueba"]]
        rel = (test["score"] / res.loc[ev.event_id, "umbral"]).clip(upper=clip)
        days = (test.index - ev.event_end) / pd.Timedelta(days=1)
        ax.axvspan((ev.event_start - ev.event_end) / pd.Timedelta(days=1), 0, color=BAND, lw=0)
        ax.plot(days, rel, color=STYLE[kind]["color"], lw=0.9)
        ax.axhline(1, color=INK, lw=1, ls="--")
        ax.axvline(0, color=INK, lw=1)
        first = res.loc[ev.event_id, "primera_deteccion"]
        if pd.notna(first):
            ax.plot((pd.Timestamp(first) - ev.event_end) / pd.Timedelta(days=1), 1, marker="v", color=INK, ms=7)
        ax.set_title(f"Evento {ev.event_id}\n{EVENT_ES.get(ev.event_description, ev.event_description)}",
                     fontsize=8)
        ax.set_ylim(0, clip)
        ax.tick_params(labelsize=8)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5, integer=True))
    for ax in axes[-1]:
        ax.set_xlabel("Días respecto a la falla", fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("Puntaje / umbral", fontsize=8)
    handles = [matplotlib.patches.Patch(color=BAND, label="Ventana de anomalía etiquetada"),
               matplotlib.lines.Line2D([], [], color=STYLE[kind]["color"], lw=1, label="Puntaje EWMA / umbral"),
               matplotlib.lines.Line2D([], [], color=INK, ls="--", lw=1, label="Umbral (= 1)"),
               matplotlib.lines.Line2D([], [], color=INK, lw=1, label="Inicio de la falla")]
    fig.legend(handles=handles, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.045), fontsize=8)
    fig.tight_layout(h_pad=1.0)
    return _save(fig, "fig3_puntaje_fallas.png")


def fig_sensitivity(table):
    """Figura 4: efecto del cuantil del umbral en detecciones, falsas alarmas y CARE."""
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.6))
    qs = sorted(table["q"].unique())
    x = np.arange(len(qs))
    panels = [("anomalias_detectadas", "Fallas detectadas (de 12)", 12),
              ("falsas_alarmas", "Falsas alarmas (de 10)", 10),
              ("CARE", "CARE", 1)]
    for ax, (col, title, top) in zip(axes, panels):
        for kind in ("lineal", "gbm"):
            t = table[table["modelo"] == kind].set_index("q").loc[qs]
            st = STYLE[kind]
            ax.plot(x, t[col], color=st["color"], ls=st["linestyle"], marker=st["marker"], mfc=st["mfc"],
                    mec=st["color"], ms=5, lw=1.5, label=st["label"])
        ax.set_title(title)
        ax.set_xticks(x, [f"{q:g}".replace(".", ",") for q in qs], rotation=45, fontsize=8)
        ax.set_ylim(0, top * 1.05)
        ax.set_xlabel("Cuantil del umbral")
    axes[2].axhline(0.5, color=INK, lw=1, ls=":")
    axes[2].text(x[-1], 0.52, "Azar (0,5)", ha="right", va="bottom", fontsize=8)
    axes[2].axhline(0.66, color=INK, lw=1, ls="-.")
    axes[2].text(x[-1], 0.68, "Autoencoder del paper (0,66)", ha="right", va="bottom", fontsize=8)
    for ax in axes:
        ax.axvline(qs.index(THRESHOLD_Q), color=MUTED, lw=0.8)
    axes[0].text(qs.index(THRESHOLD_Q) - 0.1, 12 * 0.97, "Umbral\nprincipal", ha="right", va="top", fontsize=8)
    _comma(axes[2], "y", 1)
    axes[0].legend(loc="upper center", ncol=2, bbox_to_anchor=(1.75, 1.32))
    fig.tight_layout(w_pad=1.5)
    return _save(fig, "fig4_sensibilidad_umbral.png")


def make_all(events, results, metrics, table, scored):
    paths = [fig_rmse(metrics)]
    p, err = fig_real_vs_pred(scored)
    paths.append(p)
    paths += [fig_scores(events, results, scored), fig_sensitivity(table)]
    return paths, err
