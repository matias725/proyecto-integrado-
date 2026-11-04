# Guía para la defensa · EV2

Preguntas probables de la comisión, la respuesta corta y **qué mostrar** en pantalla para respaldarla. Ordenadas según los criterios de la rúbrica.

**Antes de empezar**

- Abrir http://34.232.208.74 (o local con `SGR_FECHA_HOY=2026-11-04`) con tres pestañas: `bcastillo` (funcionario), `arojas` (delegada, en DEL06 Rural) y `emunoz` (coordinador). Clave: `Serena#2026`.
- Tener abiertos: el Excel trimestral original, `docs/pruebas/matriz_pruebas_sgr_ev2.xlsx` y `docs/bd/modelo_de_datos.md`.
- Terminal lista con `python manage.py test pruebas.test_matriz` (tarda ≈ 4 s).

---

## 1. Interfaces y procesos

**¿Las interfaces cubren todos los procesos del requerimiento?**
Sí. Cada hoja del Excel y cada regla tiene su pantalla: registrar actividad (reglas 1-5), tablero y semáforo (6, 7, 10), compromisos TUBO, validación, ausencias (9), felicitaciones y reclamos (8), períodos, metas e informes. *Mostrar*: la tabla «Del Excel a la base» en `modelo_de_datos.md` y recorrer el menú de `arojas`.

**¿Qué pasa si un funcionario intenta ingresar la octava actividad del día?**
El servidor la rechaza con un mensaje que explica la regla y no la guarda; el botón ya aparece desactivado al llegar a 7. Lo verifica RG-07, y RG-06 verifica que la 7.ª sí entra. *Mostrar*: el contador «Ingresos de hoy 1/7» en el formulario.

**¿Y si dos envíos llegan al mismo tiempo cuando lleva 6?**
El conteo y el guardado ocurren en una transacción que bloquea la fila del usuario (`select_for_update`), así el segundo envío espera y ve 7. *Mostrar*: `gestion/views.py`, función `actividad_nueva`.

**¿Cómo funciona el cierre semanal?**
La semana de lunes a viernes se puede ingresar hasta el lunes siguiente; desde el martes, no. El miércoles 04-11 se acepta el lunes 02-11 y se rechaza el domingo 01-11. *Mostrar*: RG-11 en `pruebas/test_matriz.py` (prueba el lunes 09-11 y el martes 10-11).

**¿Por qué una actividad sin teléfono se guarda si no suma?**
El requerimiento dice que no *puntúa*, no que no exista: el trabajo queda registrado para el delegado, pero no cuenta. Un teléfono **mal escrito** sí se rechaza, porque es un error de digitación. *Mostrar*: la columna «Puntaje» del listado con el motivo.

**¿Cómo se detecta que alguien registra «para cumplir»?**
Alertas para el delegado (regla 6): llegar al tope diario, repetir el mismo texto 3 o más veces, ingresar 3 o más actividades con 3 días de atraso, o tener 5 o más sin puntaje. No bloquean: son para conversar. *Mostrar*: tablero de `arojas`.

## 2. Pautas estéticas y funcionales

**¿Qué pautas siguieron?**
Las normas gráficas municipales (color `#920000`, Arial), mensajes con SweetAlert2, confirmación antes de eliminar o cambiar de delegación, advertencia de cambios sin guardar, prevención de doble envío, diseño adaptable a teléfono y accesibilidad (etiquetas, `aria-*`, enlace «Ir al contenido»). *Mostrar*: UI-14 (móvil) y un formulario con errores.

## 3. Base de datos

**¿Cómo pasaron del Excel a una base relacional?**
Cada hoja por cargo se volvió filas de `gestion_metacargo` (período × cargo × ítem); las actividades y el TUBO son una sola tabla; el semáforo se calcula desde las ausencias; el RESUMEN no se guarda, se calcula. *Mostrar*: diagrama ER.

**¿Está normalizada?**
Sí, en 3FN: cada catálogo una vez, sin grupos repetidos, columnas no clave que dependen de toda la clave. Hay **desnormalizaciones deliberadas** documentadas, por ejemplo `puntua` (se calcula una vez para sumar con un índice) y el nombre y teléfono del solicitante (es el contacto en ese momento, no el maestro de vecinos). *Mostrar*: tabla «Desnormalizaciones deliberadas».

**¿Cómo optimizaron?**
Medimos con 60.000 actividades y `EXPLAIN ANALYZE` en MySQL 8. La bandeja de validación bajó de 13,0 ms a 0,5 ms (el índice ahora incluye el orden) y el avance por ítem de 13,7 ms a 2,1 ms (índice cubriente). El tablero hace las mismas consultas con 10 o 500 actividades. *Mostrar*: `explain_mysql8_antes_de_optimizar.txt` contra `explain_mysql8.txt`.

**¿Qué garantiza la base y no solo la aplicación?**
Claves foráneas con `PROTECT`, unicidad sin distinguir mayúsculas, fechas coherentes con `CHECK`, un token único contra doble envío y **un solo período abierto** mediante una columna generada con índice único. *Dato*: lo último lo descubrimos al probar en MySQL, que no admite índices únicos parciales.

## 4. Seguridad

**¿Qué patrones de seguridad aplicaron?**
Control de acceso en tres niveles (rol, delegación, objeto), validación en servidor, CSP estricta, límite de intentos por cuenta y por IP, archivos validados por contenido, auditoría y secretos fuera del código. *Mostrar*: `docs/seguridad/owasp_top10.md`.

**¿Un funcionario puede ver la actividad de otro cambiando el número en la URL?**
No: responde 403 y queda en auditoría (PV-04). Tampoco un delegado de otra delegación (PV-05). *Demostrar*: con `bcastillo`, abrir `/actividades/1/` de otro funcionario.

**¿Y si alguien sube un ejecutable renombrado como PDF?**
Se rechaza: además de la extensión se revisan los primeros bytes del archivo (PE-03). Se guarda con nombre aleatorio y no queda en una carpeta pública.

**¿Para qué sirve la CSP si no tienen scripts en línea?**
Si alguien lograra inyectar un `<script>`, el navegador no lo ejecutaría. Lo comprobamos: las propias herramientas de prueba que usaban `eval()` fueron bloqueadas.

**¿Qué falta?**
HTTPS con dominio (configuración lista), segundo factor para administradores y `pip-audit` automático. Están en la sección «Pendientes conocidos».

## 5. Trabajo en equipo y entorno

**¿Cómo se organizaron?**
Ramas por tema, PR con revisión antes de unir a `main` y pruebas en verde como condición. *Mostrar*: `CONTRIBUTING.md` y el PR de la matriz SGR.

**¿Cómo se instala desde cero?**
Cinco comandos con SQLite o el script `instalar_ec2.sh` en AWS. *Mostrar*: `docs/instalacion.md` y, si hay tiempo, `/salud/`.

## 6. Pruebas

**¿Cuántas pruebas tienen y qué cubren?**
222 automáticas (205 funcionales + 17 en navegador), todas aprobadas, también contra MySQL 8. 65 casos funcionales con trazabilidad a cada regla. *Mostrar*: hoja «Matriz funcional».

**¿Probaron los bordes?**
Sí: 7.º y 8.º ingreso, lunes y martes del cierre, exactamente 120 % y más, ausencia que empieza antes del período, 4 felicitaciones (cuentan 3), total que no baja de 0. *Mostrar*: sección 5 del plan de pruebas.

**¿Qué resultados no fueron los esperados?**
Siete diferencias encontradas y corregidas, entre ellas la restricción ignorada por MySQL y dos consultas lentas. También diferencias entre el correo y el Excel (tope 120 % vs 150 %, ponderadores que sumaban 85 %), que dejamos configurables por período. *Mostrar*: sección 7 del plan.

**¿Cuánta carga soporta?**
En la t3.small, 0 % de errores hasta 100 usuarios simultáneos; responde bien hasta unos 25 y degrada después por los inicios de sesión simultáneos. La carga real esperada (≈ 40 funcionarios que no entran todos en el mismo segundo) está dentro de ese margen.

## 7. Recomendaciones

**¿Qué recomiendan a la municipalidad?**
Confirmar los parámetros que difieren entre el correo y el Excel, verificar las organizaciones «por verificar», publicar con HTTPS, subir a 2 vCPU si se agregan delegaciones, respaldo diario y CI con pruebas en cada cambio. *Mostrar*: sección 8 del plan.

---

## Demostración sugerida (5 minutos)

1. `bcastillo`: registrar una atención social con nombre y teléfono → suma. Registrar una coordinación → no suma, con motivo.
2. `bcastillo`: intentar una fecha de la semana pasada → mensaje de semana cerrada.
3. `arojas`: tablero del equipo, alertas, ficha con un ítem en «Tope 120 %».
4. `arojas`: rechazar una actividad con motivo → baja el avance del funcionario.
5. `arojas`: registrar una ausencia → la meta ajustada baja en el semáforo.
6. Terminal: `python manage.py test pruebas.test_matriz` → 62 pruebas en verde.
