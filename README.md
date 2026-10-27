# Detección temprana de anomalías en aerogeneradores con SCADA (CARE to Compare, Parque A)

Proyecto final del curso Integración de Energías Renovables No Convencionales a Sistemas de Potencia (UPB).

## Entregables
- `notebooks/main.ipynb`: notebook reproducible, guardado con sus salidas.
- `informe/informe.docx`: informe en formato APA 7.

## Cómo reproducir
```bash
pip install -r requirements.txt
python notebooks/build_notebook.py
python -m nbconvert --to notebook --execute --inplace notebooks/main.ipynb   # descarga el Parque A si falta (~158 MB)
python informe/build_informe.py                                              # genera y verifica el .docx
```

## Estructura
- `src/download.py`: descarga solo el Parque A del zip de Zenodo v6 mediante HTTP Range y verifica cada archivo con CRC32.
- `src/pipeline.py`: limpieza, modelo de comportamiento normal (lineal y gradient boosting), detección EWMA y evaluación CARE.
- `src/figures.py`: figuras del informe.
- `src/efd_care/`: implementación oficial de CARE (energy-fault-detector 0.8.1, Fraunhofer IEE, licencia MIT).
- `docs/`: contexto (`CONTEXTO.md`) y plan con criterios de aceptación (`PLAN.md`).
- `outputs/`: tablas y figuras generadas.
