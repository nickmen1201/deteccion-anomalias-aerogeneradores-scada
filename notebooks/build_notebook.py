"""Genera notebooks/main.ipynb. Ejecutar: python notebooks/build_notebook.py (luego nbconvert --execute)."""
from pathlib import Path

import nbformat as nbf

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    md("# Detección temprana de anomalías en aerogeneradores con datos SCADA mediante modelos de comportamiento normal\n\n"
       "**Pregunta:** ¿con cuánta anticipación puede un modelo entrenado únicamente con operación sana detectar una "
       "falla de componente en un aerogenerador?\n\n"
       "Datos: Parque A de *CARE to Compare* (Zenodo v6, 22 datasets). Toda la lógica está en `src/pipeline.py`; "
       "este notebook la ejecuta de principio a fin y muestra los resultados."),
    code("import sys\nfrom pathlib import Path\n\nROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
         "sys.path.insert(0, str(ROOT / 'src'))\n\nimport pandas as pd\nfrom IPython.display import Image, display\n"
         "import pipeline as p\nimport figures as f\n\npd.set_option('display.max_columns', 30, 'display.width', 200)"),
    md("## 1. Carga y limpieza de los datos\n\nSi el Parque A no está en `data/`, se descarga solo esa carpeta del zip "
       "de Zenodo (HTTP Range, verificación CRC32). Entrenamiento: `status_type_id == 0`, potencia > 0, sin potencia "
       "limitada (potencia real < 90 % de la posible) y sin faltantes."),
    code("if not p.FARM_DIR.exists():\n    import download\n    download.main(dest=ROOT / 'data')\n\n"
         "events = p.load_events()\nprint(events['event_label'].value_counts())\np.variables_table()"),
    code("p.summary_table(events)"),
    md("## 2 a 4. Modelo de comportamiento normal, detección y evaluación\n\n"
       "Por dataset: un modelo por temperatura de componente (regresión lineal y gradient boosting), validación "
       "temporal con el último 20 % del entrenamiento, residuo estandarizado, EWMA (alfa = 0,05), umbral = cuantil "
       "0,995 del puntaje en validación y contador de criticidad oficial (72). CARE se calcula con el código oficial "
       "de los autores (`src/efd_care`). El análisis de sensibilidad varía el cuantil del umbral."),
    code("events, results, metrics, table, scored = p.run_all()\n"
         "metrics.groupby(['objetivo', 'modelo'])['rmse_val'].median().unstack().round(2)"),
    code("w = metrics.pivot_table(index=['event_id', 'objetivo'], columns='modelo', values='rmse_val')\n"
         "print(f\"GBM con menor RMSE en {(w['gbm'] < w['lineal']).sum()} de {len(w)} combinaciones dataset-componente\")"),
    md("### Resultados con el umbral principal (cuantil 0,995)"),
    code("results[['event_id', 'modelo', 'tipo', 'descripcion', 'detectado', 'max_criticidad', 'anticipacion_dias', "
         "'pct_puntos_alarma']].round(2)"),
    code("table[table['q'] == p.THRESHOLD_Q].round(3)"),
    md("### Análisis de sensibilidad del umbral"),
    code("table.round(3)"),
    code("sens = pd.read_csv(p.OUT_DIR / 'resultados_sensibilidad.csv')\n"
         "sens[sens['detectado']][['modelo', 'q', 'event_id', 'tipo', 'descripcion', 'primera_deteccion', "
         "'anticipacion_dias', 'componente_alarma']].round(2)"),
    md("## Figuras"),
    code("paths, err = f.make_all(events, results, metrics, table, scored)\nprint('RMSE ventana figura 2:', err)\n"
         "for path in paths:\n    display(Image(filename=str(path), width=800))"),
    md("## Respuesta a la pregunta"),
    code("main = table[table['q'] == p.THRESHOLD_Q].set_index('modelo')\nfor kind in ('lineal', 'gbm'):\n"
         "    r = main.loc[kind]\n"
         "    print(f\"{kind}: {int(r.anomalias_detectadas)}/{int(r.anomalias_total)} fallas detectadas, \"\n"
         "          f\"{int(r.falsas_alarmas)}/{int(r.normales_total)} falsas alarmas, CARE = {r.CARE:.2f}\")\n"
         "det = sens[sens['detectado'] & (sens['tipo'] == 'anomaly')]\n"
         "print(f\"Relajando el umbral (cuantil 0,90 a 0,98) se detectan como máximo \"\n"
         "      f\"{int(table['anomalias_detectadas'].max())} de 12 fallas, con anticipaciones entre \"\n"
         "      f\"{det['anticipacion_dias'].min():.1f} y {det['anticipacion_dias'].max():.1f} días.\")"),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3",
                                                               "language": "python"}})
nbf.write(nb, Path(__file__).with_name("main.ipynb"))
