# Contexto del proyecto

## Enunciado
- **Título:** Detección temprana de anomalías en aerogeneradores con datos SCADA mediante modelos de comportamiento normal.
- **Pregunta:** ¿Con cuánta anticipación puede un modelo entrenado solo con operación sana detectar una falla de un componente en un aerogenerador?
- **Esfuerzo:** alrededor de 10 horas.
- **Entregables:** un notebook de Python reproducible y un informe con resultados y análisis.

## Datos: CARE to Compare
Es un conjunto público de datos SCADA de aerogeneradores publicado por Gück, Roelofs y Faulstich (2024) junto con la métrica **CARE**. Se descarga desde Zenodo buscando "CARE to Compare".

- Tiene 3 parques (A, B y C) con 95 datasets en total. Cada dataset corresponde a una turbina y a un evento.
- Cada dataset trae un **periodo de entrenamiento** y un **periodo de predicción**, marcados en la columna `train_test`. El evento cae dentro del periodo de predicción.
- El evento puede ser una anomalía documentada (falla de un componente) o un caso normal, que no tiene falla. Esta información está en `event_info.csv`, con las columnas `event_label`, `event_start`, `event_end` y la descripción del componente.
- La columna `status_type_id` indica el estado de operación. El 0 es operación normal. Los demás códigos marcan potencia reducida (derating), ralentí, mantenimiento, parada u otros estados.
- El parque **A** tiene unas 86 variables, el B unas 257 y el C unas 957. Los sensores tienen nombres anónimos (`sensor_N_avg`), y `feature_description.csv` explica qué mide cada uno.
- La resolución de los datos es de 10 minutos.

**Decisión de alcance:** se usará **solo el Parque A** porque es el más pequeño, tiene variables interpretables y basta para responder la pregunta dentro de las 10 horas. Los parques B y C quedan como trabajo futuro.

## Métrica CARE
Hay que verificar la definición exacta en el paper y el código de los autores. CARE combina 4 componentes:
- **Coverage:** F-score puntual (β = 0,5) en los datasets con anomalía.
- **Accuracy:** porcentaje de puntos sin alarma en los datasets normales. Mide las falsas alarmas.
- **Reliability:** F-score a nivel de evento (β = 0,5), que indica si se detectó o no cada evento.
- **Earliness:** premia la detección temprana dentro de la ventana previa a la falla.

Un evento cuenta como detectado cuando un **contador de criticidad** supera un umbral. El contador sube con cada punto anómalo en estado normal y baja en caso contrario. El paper usa un umbral del orden de 72 pasos, unas 12 horas. Si la implementación oficial está publicada, se usará esa en lugar de reimplementarla.

## Enfoque técnico
Para cada dataset del Parque A:
1. **Limpieza:** se entrena solo con las filas `train_test == train` que estén en `status_type_id == 0` y tengan potencia mayor que 0. Así se excluyen paradas, derating y datos faltantes.
2. **Modelo de comportamiento normal (NBM):** predice la temperatura de los componentes (caja multiplicadora, rodamientos del generador, devanados y transformador) a partir de la potencia, la velocidad del viento, la temperatura ambiente y la velocidad del rotor.
   - El modelo base es una `LinearRegression`.
   - El modelo principal es un `HistGradientBoostingRegressor` de scikit-learn, que no requiere instalar nada extra.
3. **Residuo:** se calcula la diferencia entre el valor real y el predicho, y se estandariza con la media y la desviación del residuo en el entrenamiento. El puntaje de anomalía es el **máximo |z| entre los componentes**.
4. **Detección:** se suaviza el puntaje con un **EWMA** y se fija como umbral un cuantil alto del EWMA en el entrenamiento, por ejemplo el p99,5. Después se aplica el contador de criticidad.
5. **Evaluación:** se calcula la anticipación como `event_start − primera detección`, se cuentan las falsas alarmas en los datasets normales y se obtiene CARE. Todo se compara entre el modelo base y el gradient boosting.

## Viabilidad
**Sí, el proyecto es viable en unas 10 horas** si se cumplen estas condiciones:
- Se limita al Parque A.
- Se usa un solo pipeline genérico que recorre todos los datasets, sin ajustes manuales por turbina.
- Se usa scikit-learn sin ajuste fino de hiperparámetros.
- Se usa EWMA como método único de detección. CUSUM es opcional y solo se agrega si sobra tiempo.

**Riesgos:**
- La definición de CARE puede no coincidir con la del paper. Para mitigarlo, se debe usar el código oficial o validar la implementación propia contra los valores de referencia publicados.
- Algunas fallas pueden no estar en componentes con sensor de temperatura. Esto se reportará como limitación.
