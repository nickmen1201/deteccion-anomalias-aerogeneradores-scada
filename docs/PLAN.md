# Plan por fases y criterios de aceptación

Se busca la máxima automatización: toda la lógica vive en `src/pipeline.py` y el notebook solo la llama y muestra los resultados. Al ejecutar **Run All** en un entorno limpio se debe reproducir todo el trabajo.

Estructura:
```
data/raw/           # CARE to Compare descomprimido (en .gitignore)
src/pipeline.py     # carga, limpieza, modelos, detección y métricas
notebooks/main.ipynb
outputs/            # figuras y tablas generadas
informe/informe.md  # se exporta a PDF
requirements.txt
```

---

## Fase 1: Datos (~2 h)
**Objetivo:** cargar y limpiar cualquier dataset del Parque A con una sola función.

Criterios de aceptación:
- [ ] `requirements.txt` existe y se instala sin errores.
- [ ] Una función descarga y descomprime el dataset desde Zenodo, o el README explica cómo hacerlo manualmente.
- [ ] `load_dataset(id)` devuelve el DataFrame con un índice temporal y la fila correspondiente de `event_info`.
- [ ] Las columnas de entrada (potencia, viento, temperatura ambiente, rotor) y las de salida (temperaturas de componentes) quedan mapeadas en un diccionario a partir de `feature_description.csv`.
- [ ] `clean(df)` deja en el entrenamiento solo `status_type_id == 0`, potencia mayor que 0 y filas sin NaN.
- [ ] El notebook muestra una tabla resumen de los datasets del Parque A con su id, tipo de evento (anomalía o normal), componente y filas de entrenamiento antes y después de la limpieza.

## Fase 2: Modelo de comportamiento normal (~3 h)
**Objetivo:** predecir las temperaturas de los componentes con dos modelos y compararlos.

Criterios de aceptación:
- [ ] `fit_nbm(train, model="linear" | "gbm")` entrena un modelo por cada temperatura objetivo.
- [ ] La validación usa el último 20 % del periodo de entrenamiento, separado por tiempo y sin barajar.
- [ ] Se genera una tabla de RMSE y MAE de validación por dataset y modelo, y el GBM queda mejor que el lineal en la mayoría de los casos.
- [ ] Se incluye una figura de real contra predicho para un dataset de ejemplo.
- [ ] Todo el Parque A se procesa en un bucle, sin ajustes manuales.

## Fase 3: Detección (~2 h)
**Objetivo:** convertir el residuo en alarmas.

Criterios de aceptación:
- [ ] El residuo se estandariza con las estadísticas del entrenamiento y el puntaje es el máximo |z| entre los componentes.
- [ ] El puntaje se suaviza con EWMA (α fijo, por ejemplo 0,05) y el umbral es un cuantil del EWMA en la validación, fijado sin mirar el periodo de predicción.
- [ ] El contador de criticidad produce una detección por evento, con su fecha o "no detectado".
- [ ] Se incluye una figura por cada caso de anomalía con el puntaje EWMA, el umbral, la primera detección y `event_start` marcados.
- [ ] *(Opcional)* Se agrega CUSUM como alternativa si sobra tiempo.

## Fase 4: Evaluación (~1,5 h)
**Objetivo:** responder la pregunta con números.

Criterios de aceptación:
- [ ] Se calcula la **anticipación** de cada anomalía (`event_start − primera detección`, en días) y se reporta su mediana y rango.
- [ ] Se calculan las **falsas alarmas** como el número de datasets normales con detección y el porcentaje de puntos con alarma.
- [ ] Se calcula **CARE** con sus 4 subcomponentes para el modelo lineal y el GBM, usando la implementación oficial o una propia validada.
- [ ] Una tabla final compara el modelo lineal, el GBM y los valores de referencia del paper.
- [ ] Todas las tablas y figuras se guardan en `outputs/`.

## Fase 5: Informe (~1,5 h)
**Objetivo:** documentar los resultados.

Criterios de aceptación:
- [ ] El notebook corre de principio a fin con **Run All** sin errores en un entorno limpio.
- [ ] El informe tiene 4 a 6 páginas con estas secciones: introducción, datos, metodología, resultados, discusión (incluida la respuesta directa a la pregunta) y limitaciones.
- [ ] El informe declara qué fallas no se detectaron y por qué, por ejemplo cuando el componente no tiene sensor de temperatura.

---

### Definición de terminado
El proyecto está terminado cuando, al ejecutar el notebook, se obtiene una tabla con la anticipación, las falsas alarmas y CARE para el modelo lineal y el GBM, y el informe responde: *"El modelo detecta las fallas con una mediana de X días de anticipación, con Y falsas alarmas en los datasets normales y un CARE de Z."*
