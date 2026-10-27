# Plan de ejecución autónoma

Claude ejecuta todas las fases seguidas, sin intervención del usuario. Cada criterio se comprueba ejecutando código y no se marca como cumplido sin evidencia. Si algún dato del CONTEXTO no coincide con los archivos reales, se corrige el CONTEXTO y se continúa.

```
src/pipeline.py         # toda la lógica
notebooks/main.ipynb    # llama al pipeline y muestra los resultados (entregable 1)
outputs/                # tablas (CSV) y figuras (PNG)
informe/build_informe.py  # genera el .docx a partir de outputs/
informe/informe.docx      # informe APA 7 (entregable 2)
data/                   # el zip y el Parque A extraído (en .gitignore)
requirements.txt
```

## Fase 1: Datos
- [ ] El zip v6 está descargado y su md5 coincide con `2547b58c…500c`. Solo se extrae el Parque A.
- [ ] Se confirmó a partir de los archivos el recuento de anomalías y normales del Parque A, con el separador de los CSV y los nombres reales de las columnas.
- [ ] Las 4 entradas y las temperaturas de componentes quedaron identificadas con `feature_description.csv`. El mapeo se guardó en `outputs/variables.csv`.
- [ ] Se revisó si `energy-fault-detector` implementa CARE y la decisión quedó anotada en el CONTEXTO.
- [ ] La limpieza (punto 1) está aplicada y `outputs/resumen_datasets.csv` muestra las filas de cada dataset antes y después de limpiar.

## Fase 2: Modelo de comportamiento normal
- [ ] Hay un modelo lineal y un GBM por dataset, entrenados solo con datos sanos.
- [ ] Se validó con el último 20 % del entrenamiento, separado por tiempo, y `outputs/metricas_modelo.csv` contiene el RMSE de cada modelo.
- [ ] Hay una figura de valor real contra predicho para un dataset con falla.

## Fase 3: Detección
- [ ] Se calculan el residuo, el EWMA y el umbral fijado solo con datos de entrenamiento, y a partir de ellos la alarma punto a punto.
- [ ] El contador de criticidad entrega la fecha de la primera alarma de cada dataset.
- [ ] Hay una figura por cada anomalía con el EWMA, el umbral, la primera alarma y `event_start`.

## Fase 4: Evaluación
- [ ] `outputs/resultados.csv` contiene, por dataset y modelo, la anticipación en días, si hubo detección y si hubo falsa alarma.
- [ ] Se calculó CARE con sus 4 componentes para cada modelo. Antes se validó la implementación con los casos de referencia del paper: "todo normal" debe dar 0 y "todo anomalía" debe dar 0.
- [ ] Hay una tabla resumen con la mediana de la anticipación, las anomalías detectadas, las falsas alarmas y CARE, comparada con el 0,5 (azar) y el 0,66 (autoencoder) del paper.

## Fase 5: Entregables
- [ ] `notebooks/main.ipynb` corre de principio a fin con `jupyter nbconvert --execute` sin errores y queda guardado con sus salidas.
- [ ] `informe/build_informe.py` genera `informe/informe.docx` con estas secciones: portada de estudiante, introducción, datos, metodología, resultados, discusión con la **respuesta directa a la pregunta**, limitaciones y referencias. Cada cifra se toma de `outputs/`.
- [ ] Se verifica automáticamente el formato del .docx: todo el texto en Arial 11, interlineado doble, márgenes de 2,54 cm, ningún texto en color, sin "—" ni "–", número de página en el encabezado y portada con los datos del CONTEXTO.
- [ ] Antes de crear las figuras se carga la skill `dataviz`. Se revisa cada PNG final y se confirma que cada afirmación del texto sobre una figura se ve en ella.

**Terminado:** el informe contiene la frase *"Un modelo entrenado solo con operación sana detecta fallas con una mediana de X días de anticipación (n/N fallas detectadas, F falsas alarmas, CARE = Z)"*, con valores reales.
