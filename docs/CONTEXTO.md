# Contexto del proyecto

## Encargo (texto original)

**Título:** Detección temprana de anomalías en aerogeneradores con datos SCADA mediante modelos de comportamiento normal.

**Pregunta:** ¿con cuánta anticipación puede un modelo entrenado únicamente con operación sana detectar una falla de componente en un aerogenerador?

**Metodología (alrededor de 10 horas):**
1. Carga y limpieza de los datos, filtrando paradas y operación con potencia limitada.
2. Modelo de comportamiento normal: predicción de la temperatura de un componente a partir de potencia, velocidad de viento, temperatura ambiente y velocidad de rotación. Se compara una regresión base con un modelo de gradient boosting.
3. Detección: análisis del residuo con umbrales tipo EWMA o CUSUM.
4. Evaluación contra las fallas documentadas: anticipación de la detección, falsas alarmas y la métrica CARE definida por los autores del conjunto, lo que permite comparar con resultados publicados.

**Entregables:** notebook de Python reproducible e informe con resultados y análisis.

**El proyecto está terminado cuando** la pregunta queda respondida con números y existen los dos entregables. Todo lo demás es secundario.

---

## Hechos verificados (fuentes al final)

**Dataset "CARE to Compare"** (Gück, Roelofs y Faulstich, 2024)
- La última versión en Zenodo es la v6, del 9 de julio de 2025. Corresponde al registro 15846963, tiene licencia CC BY-SA 4.0 y un único archivo de 5,5 GB:
  `https://zenodo.org/records/15846963/files/CARE_To_Compare.zip?download=1`, con md5 `2547b58c21ac8c242d13232860cf500c`.
- Cada sub-dataset es un CSV con resolución de 10 minutos. Incluye ~1 año de entrenamiento y entre 4 y 98 días de predicción, separados por la columna `train_test`. También trae un id, una marca de tiempo, `asset_id` y `status_type_id`.
- **Parque A** (tabla 3.2 del paper): 22 datasets, 5 turbinas y 86 variables. El paper reporta 11 anomalías y 11 normales, pero la nota de la v5 de Zenodo reetiquetó el evento 51 como anomalía. **El recuento real se toma de `event_info.csv`.**
- Los nombres de los sensores están anonimizados. Solo la potencia y el viento se reconocen por su nombre. **La temperatura ambiente, la velocidad del rotor y las temperaturas de los componentes se identifican con `feature_description.csv`**, que incluye una descripción y la unidad de cada sensor.
- Según el paper, `status_type_id` 0 (normal) y 2 (ralentí) cuentan como normales, y 1, 3, 4 y 5 no. La nota de Zenodo v6 agrega: *"in wind farm A status_type_id labels can be ignored while evaluating prediction time frames"*.

**Métrica CARE** (paper, sección 4.1)
- **Coverage:** F_β puntual con β = 0,5, calculado en los datasets de anomalía.
- **Accuracy:** tn / (fp + tn), calculado en los datasets normales.
- **Reliability:** F_β (β = 0,5) a nivel de evento. Un evento se considera alarma si su contador de criticidad supera **72** (12 h de anomalías seguidas). El contador sube 1 por cada punto anómalo y baja 1 (sin llegar a menos de 0) por cada punto no anómalo. Los puntos con estado anormal no lo modifican.
- **Earliness:** media ponderada de las detecciones dentro del evento. Pesan 1 en la primera mitad del evento y su peso baja linealmente hasta 0 en la segunda mitad.
- **Combinación:** `WA = (Cov + Earl + Rel + 2·Acc) / 5`. CARE vale 0 si no se detecta ninguna anomalía, vale Acc si Acc < 0,5 y en los demás casos vale WA.
- **Referencias publicadas** (95 datasets, no solo el Parque A): "todo normal" y "todo anomalía" obtienen 0, el azar obtiene 0,5 (es el mínimo a superar) e Isolation Forest queda por debajo de 0,5. El autoencoder de los autores obtiene **0,66**.
- Existe el paquete `energy-fault-detector` en PyPI (v0.8.1), del mismo grupo de autores. **Falta verificar** si trae una implementación de CARE. Si la trae, se usa esa. Si no, se implementa a partir de las fórmulas anteriores.

## Decisiones (lo más simple que sigue siendo válido)

| Tema | Decisión | Motivo |
|---|---|---|
| Alcance | Solo el Parque A (22 datasets) | Es el parque más pequeño y basta para responder la pregunta. |
| Datos | Extraer del zip únicamente la carpeta del Parque A | Ahorra disco y tiempo. |
| Limpieza para entrenar | `train_test == train`, `status_type_id == 0`, potencia > 0 y sin NaN | Elimina paradas y operación con potencia limitada (punto 1). |
| Variable objetivo | Una temperatura de componente por dataset: la del componente dañado si `event_description` lo indica, y si no, una temperatura fija (p. ej. la de la caja multiplicadora) | Cumple el punto 2 tal como está redactado ("un componente"). |
| Entradas | Potencia, viento, temperatura ambiente y velocidad del rotor | Son las que pide el punto 2. |
| Modelos | `LinearRegression` frente a `HistGradientBoostingRegressor` (scikit-learn, sin ajuste de hiperparámetros) | Ya está instalado y cumple la comparación pedida. |
| Detección | Residuo estandarizado → EWMA → umbral en el cuantil 99,5 del EWMA del entrenamiento | Un solo método cubre el punto 3. CUSUM es opcional. |
| Evaluación | Anticipación = `event_start − primera alarma` (criticidad > 72), falsas alarmas en los datasets normales y CARE | Responde la pregunta y cubre el punto 4. |
| Ejecución | Claude ejecuta todo de forma autónoma. Cada dato que no esté verificado se comprueba en los archivos antes de usarlo | Así se evita inventar información. |

## Formato del informe (entregable 2)

**Datos de portada**
- **Autor:** Nicolás Meneses Marín
- **Universidad:** Universidad Pontificia Bolivariana
- **Curso:** INTEGRACIÓN DE ENERGÍAS RENOVABLES NO CONVENCIONALES A SISTEMAS DE POTENCIA
- **Docentes:** IDI A. ISAAC MILLAN, JORGE W. GONZALEZ SANCHEZ, CARLOS E. RESTREPO MEJIA
- **Fecha:** la del día de entrega

**Herramienta.** El informe será un documento **Word (.docx)** generado con `python-docx` mediante un script. Se descartó LaTeX porque no está instalado en el equipo y habría que pedirle al usuario que lo instale.

**Norma: APA 7.ª edición, formato de trabajo de estudiante.**
- Fuente **Arial 11 pt**. APA 7 acepta Arial en 11 pt, no en 12.
- Interlineado doble, márgenes de 2,54 cm y sangría de 1,27 cm en la primera línea de cada párrafo.
- Número de página en la esquina superior derecha.
- Portada de estudiante con título, autor, institución, curso, docentes y fecha.
- Títulos según los niveles de APA. Las tablas y figuras van numeradas y con título.
- Referencias en formato APA con sangría francesa, citando al menos el paper y el dataset de Zenodo.

**Restricciones del usuario (obligatorias)**
- No se usan guiones largos (— ni –). En su lugar se usan comas, dos puntos o paréntesis.
- Todo el texto va en negro, sin color.
- La negrita se usa solo cuando es necesaria: títulos y rótulos de tablas y figuras. La cursiva se limita a lo que exige APA (títulos de tablas y figuras y nombres de fuentes en las referencias).

**Gráficas**
- Antes de crear cualquier gráfica se carga la skill `dataviz`.
- Cada figura tiene un solo mensaje, ejes con nombre y unidades, texto legible al tamaño en que se imprime, se exporta a 300 dpi y se puede leer en escala de grises.
- **Toda conclusión que el texto saque de una figura debe verse directamente en ella.** Si no se ve, se cambia la figura o se elimina la afirmación.

## Fuentes
- Paper: https://arxiv.org/abs/2404.10320
- Zenodo v6: https://zenodo.org/records/15846963
- FAQ de los autores: https://aefdi.github.io/EnergyFaultDetector/care2compare_faq.html
