# Retrospectiva: Observaciones y Lecciones

> **Fecha:** 2026-11-13
> **Propósito:** lo que el proyecto reveló sobre sí mismo: dónde está su valor, de dónde vienen sus límites y qué implica eso para el trabajo posterior. La evidencia detrás de cada observación está en [project-analysis.md](./project-analysis.md); este documento la interpreta.

---

## 1. El valor está en el proceso, no en el artefacto

La propuesta buscaba mostrar que un modelo pequeño se puede especializar, empaquetar y evaluar con hardware limitado y compartido. Cada etapa de ese proceso existe, tiene scripts y se ejecutó:

- datos generados por un modelo maestro;
- entrenamiento LoRA con límite de tiempo en una GPU compartida;
- exportación a GGUF y ejecución offline;
- un cliente hexagonal;
- un benchmark atribuido.

El método "Cold Staging, Hot Burst" y el cuidado de no molestar a los demás usuarios de la máquina compartida se pueden reutilizar con independencia del modelo que produjeron.

El modelo en sí es un producto de ese proceso, y uno modesto. Eso define cómo hay que citar el proyecto. Es evidencia de que el **método** funciona bajo restricciones reales. No es evidencia de que los modelos pequeños rivalicen con los grandes.

## 2. El proyecto se corrigió a sí mismo, y eso forma parte del resultado

Los documentos anteriores reportaban:

- una comparación con modelos frontera que nunca se ejecutó;
- un holdout descrito como aislado que no lo estaba;
- hiperparámetros distintos de los del código que realmente corrió;
- un avance descrito como completo.

El trabajo posterior auditó esas afirmaciones, las volvió a medir, marcó las que no se sostenían y dejó las correcciones visibles en el historial. Durante el periodo de esta retrospectiva hubo una corrección más con el mismo patrón. Una primera medición con chequeo de tipos sugería que el fine-tune escribía código con tipos más correctos que el modelo base. Un chequeo más cuidadoso mostró lo contrario (14/30 frente a 17/30), y la afirmación se retiró.

**Observación:** las partes del proyecto que se miden automáticamente tienden a mantenerse honestas. Las que se escriben a mano derivan hacia el optimismo. Los reportes atribuidos, los scripts de auditoría y los tests hicieron más por la credibilidad de los resultados que cualquier texto.

## 3. El modelo aprendió una plantilla, no una habilidad

El fine-tune supera de forma consistente a su modelo base: +16.8 puntos CAS, 24 victorias y ninguna derrota. De dónde sale esa ganancia es revelador:

- **La mayor parte de la ganancia:** eliminar imports de frameworks y declarar interfaces. Son las dos conductas que la métrica premia con menos esfuerzo.
- **Casi nada de la ganancia:** validar invariantes o usar `Result`, aunque la mayoría de las respuestas de entrenamiento hacían ambas cosas.
- **Forma de las puntuaciones:** 26 de 30 caen en una franja estrecha de 65–75.

El modelo reproduce una forma (una interfaz, una clase con constructor privado y fábrica estática, ningún import) en lugar de adaptarse al código que tiene delante.

**Observación:** con 18 prompts de entrenamiento distintos, un loss de entrenamiento bajo (0.031) midió memorización de las plantillas, no aprendizaje. Un loss bajo sobre un dataset pequeño y repetitivo es una señal de alerta, no de éxito.

## 4. La calidad de los datos fue la restricción decisiva

Los límites del modelo se explican más por los datos que por el tamaño del modelo, los hiperparámetros o el código de entrenamiento:

- **Pocas tareas:** 18 prompts distintos detrás de 138 filas.
- **Respuestas truncadas:** el 35% de las respuestas de entrenamiento termina a mitad de código.
- **`any` explícito:** muchas respuestas lo usan, contradiciendo la propia regla del proyecto.
- **Mezcla de tareas equivocada:** casi ningún ejemplo pide la tarea que mide el benchmark (refactorizar código dado).

Nada de esto se veía mientras se generaban los datos. Solo apareció al auditarlos.

**Observación:** la salida de un modelo maestro es materia prima, no datos de entrenamiento. Entre ambas hace falta un filtro que rechace:

- las respuestas truncadas;
- las construcciones prohibidas;
- el código que no pasa el chequeo de tipos.

Ese filtro ya existe (`split_dataset.py` y `audit_dataset.py --typecheck`). Aplicado a los datos actuales, conserva 82 de 186 filas. El dataset más limpio también es mucho más chico, lo que muestra cuánta señal verificada contenía en realidad el volumen original.

## 5. Una métrica moldea lo que mide

El Clean Architecture Score hizo posible la comparación, y de la comparación salió el único resultado robusto. También tiene puntos ciegos que el modelo encontró:

- **Un piso por no hacer nada:** una respuesta vacía saca 50.
- **"Puertos" laxos:** cualquier interfaz cuenta como puerto.
- **Frontera gratis:** omitir los imports da la puntuación completa de frontera.
- **Sin chequeo de corrección:** que el código compile o siga haciendo lo mismo no forma parte de la puntuación.

El perfil del fine-tune coincide casi exactamente con esos puntos ciegos.

**Observación:** una métrica que revisa la forma de la salida invita a producir salidas con la forma correcta. Si la corrección no forma parte de la puntuación, la puntuación mide apariencia. Los chequeos baratos y deterministas (compilación, tests de comportamiento sobre el código original) deben estar dentro de la métrica, no en una revisión manual posterior.

## 6. Las hipótesis necesitan su grupo de comparación desde el principio

La hipótesis central de la propuesta es una comparación: un modelo pequeño especializado frente a modelos comerciales generales. El proyecto nunca ejecutó ese grupo de comparación. El modelo base fue la única línea base. No hubo base con prompt few-shot, ni modelo maestro, ni modelo frontera.

Por eso la hipótesis no está confirmada ni refutada: está sin probar. Durante un tiempo, una cifra provisional (90.5) circuló como si fuera un resultado.

**Observación:** cuando una hipótesis es una comparación, el grupo de comparación es parte del experimento mínimo viable, no un añadido posterior. Sin él, lo máximo que se puede afirmar es una mejora respecto del punto de partida.

## 7. Las restricciones moldearon el diseño, en general para bien

Las ventanas cortas de GPU, la máquina compartida y un portátil solo con CPU forzaron decisiones que resultaron acertadas:

- el modo de prueba en seco (dry-run);
- el motor de inferencia mock;
- los límites de tiempo y memoria;
- la evaluación con un solo comando;
- particiones sin prompts compartidos que se pueden verificar offline.

Las mismas restricciones explican también las carencias:

- sin loss de validación;
- sin ejecuciones repetidas;
- sin un modelo más grande;
- unos 12 tokens por segundo en CPU (unos 47 s por respuesta), lo que descarta el uso interactivo.

**Observación:** los entornos con restricciones premian invertir en herramientas offline (tests, auditorías, mocks), porque así cada minuto de hardware escaso se dedica a la ejecución en sí.

## 8. Lo que el proyecto deja para el trabajo posterior

Las observaciones anteriores apuntan a las mismas pocas preguntas abiertas. Cada una es concreta y medible:

1. **Datos:** ¿un dataset verificado y diverso (150–200 tareas de refactorización distintas, cada respuesta con su chequeo de tipos) produce un modelo que se adapta al código en lugar de una plantilla?
2. **Medición:** ¿cómo queda la comparación cuando la puntuación incluye compilación y conservación del comportamiento, y resta el piso de no hacer nada?
3. **Comparación:** ¿dónde queda un modelo pequeño especializado frente al mismo modelo base con un buen prompt, frente a su maestro y frente a un modelo frontera, con la misma suite?
4. **Sistemas híbridos:** ¿un modelo pequeño acompañado de un verificador determinista alcanza una calidad aceptable donde el modelo solo no llega? La verificación resultó barata y el modelo solo resultó insuficiente, así que es la continuación más directa.

El proyecto se puede citar por esto: un proceso reproducible para especializar modelos pequeños con hardware limitado, junto con una medición honesta de dónde se queda corto. Lo que le falta define el trabajo siguiente.
