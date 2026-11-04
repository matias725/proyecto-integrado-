# Plan de pruebas · SGR La Serena · EV2

| | |
|---|---|
| Versión del sistema | `ev2-2.0.0` (matriz SGR) |
| Fecha de ejecución | 04-11-2026 |
| Resultado | **213 de 213** pruebas aprobadas en SQLite (196 funcionales + 17 en navegador) · **196 de 196** contra MySQL 8.0 · **64 de 64** casos funcionales aprobados |
| Matriz con el detalle | [`matriz_pruebas_sgr_ev2.xlsx`](matriz_pruebas_sgr_ev2.xlsx) (hojas: Matriz funcional, Pruebas automatizadas, Estrés, Umbrales, Pendientes) |

---

## 1. Objetivo y alcance

Verificar que el SGR cumple el **nuevo requerimiento** de la Coordinación de Delegaciones (10 reglas de la matriz SGR) y que lo construido en la EV2 sigue funcionando: acceso, recuperación de clave, mantenedores, atenciones, permisos por rol y delegación.

**Dentro del alcance**: reglas de negocio con sus bordes, cálculo de la matriz contra el Excel trimestral, control de acceso por rol, delegación y objeto, seguridad de archivos y cabeceras, integridad de la base, importación de la base JJVV, interfaz en navegador real, rendimiento con volumen y carga concurrente.

**Fuera del alcance**: navegadores distintos de Chromium (revisión manual), envío SMTP real (se prueba con un backend en memoria), datos reales de la base JJVV (confidenciales; se prueba con un Excel equivalente).

---

## 2. Estrategia por nivel

| Nivel | Qué verifica | Herramienta | Dónde | Cantidad |
|---|---|---|---|---|
| Reglas y cálculo | Cada regla con su caso normal y su **borde** (7.º/8.º ingreso, lunes/martes, exactamente 120 %) | `django.test` | `pruebas/test_matriz.py` | 62 |
| Funcional de pantallas | Flujo completo por HTTP: formulario → servidor → base → respuesta | `django.test.Client` | `pruebas/*.py` | 196 en total |
| Permisos y acceso por objeto | 403 al salir del perfil, de la delegación o del dueño | `django.test.Client` | `test_permisos.py`, `test_matriz.py` | 30+ |
| Seguridad | CSP, cabeceras, límite por IP, archivos maliciosos, CSRF | `django.test.Client` | `test_seguridad.py`, `test_matriz.py`, `test_sistema.py` | 20+ |
| Interfaz | SweetAlert2, confirmaciones, doble clic, lista dependiente, medidores, **sin errores de CSP** | Playwright + Chromium | `pruebas_ui/test_interfaz.py` | 17 |
| Base de datos | Mismas pruebas sobre MySQL 8 (restricciones, columna generada, collation) | `SGR_DB_MOTOR=mysql` | `ejecucion_mysql8.txt` | 196 |
| Rendimiento con volumen | Consultas acotadas (sin N+1) y planes de ejecución con 60.000 actividades | `CaptureQueriesContext`, `EXPLAIN ANALYZE` | `PF-01`, `docs/bd/explain_mysql8.txt` | 1 + 5 consultas |
| Carga concurrente | 10 → 25 → 50 → 100 usuarios simultáneos | Locust + monitor de CPU/memoria | `pruebas_estres/`, `estres/aws/` | 4 etapas |

La fecha del sistema se fija en el **miércoles 04-11-2026** (`SGR_FECHA_HOY`) para que los bordes de semana y de período den siempre el mismo resultado.

---

## 3. Entorno

| Componente | Desarrollo y pruebas | Producción (AWS) |
|---|---|---|
| Sistema operativo | Ubuntu 24.04 | Ubuntu 24.04 (EC2 t3.small) |
| Python / Django | 3.13 / 5.2.19 | 3.12 / 5.2 |
| Base de datos | SQLite 3 y MySQL 8.0.46 | MySQL 8.0 |
| Navegador | Chromium (Playwright) | — |
| Datos | `sgr_inicializar --demo`: 6 delegaciones, 18 cuentas, 29 ítems, 8 cargos, 76 metas, 505 actividades, 12 organizaciones ficticias | Igual |

---

## 4. Criterios

| | Criterio |
|---|---|
| **Entrada** | Migraciones aplicadas sin cambios pendientes (`makemigrations --check`), datos de demostración cargados |
| **Aprobación de un caso** | Todas las pruebas automáticas que lo respaldan pasan |
| **Salida** | 100 % de casos funcionales aprobados; 0 fallas en SQLite y MySQL; 0 errores de JavaScript o CSP en el navegador; umbrales de estrés documentados |
| **Suspensión** | Una falla en acceso, permisos o cálculo detiene la entrega hasta corregirla |

---

## 5. Trazabilidad: requerimiento → casos → pruebas

| Regla del requerimiento | Caso | Pruebas automáticas | Bordes cubiertos |
|---|---|---|---|
| 1 · Si el solicitante es el delegado, no puntúa | CF-43 | RG-01, PM-04 | — |
| 2 · Nombre y teléfono obligatorios para puntuar | CF-44 | RG-02 a RG-05 | Sin nombre, sin teléfono, teléfono inválido, formatos +56 / fijo / móvil |
| 3 · Máximo 7 ingresos diarios | CF-45 | RG-06 a RG-08, PM-13 | **7.º aceptado, 8.º rechazado**, 7 ayer no bloquean hoy, doble envío no consume cupo (RG-15) |
| 4 · Cierre semanal el lunes | CF-46 | RG-09 a RG-12 | **Lunes 09-11 acepta el viernes 06-11; martes 10-11 lo rechaza**; fecha futura |
| 5 · Gestiones previas no puntúan | CF-47 | RG-13, RG-14, RG-17 | Pendiente que pasa a Realizado suma recién entonces |
| 6 · Alertas de registro para cumplir | CF-48 | PM-13 | Tope diario |
| 7 · Tope 120 % por ítem | CF-49 | PM-01 a PM-03 | **Exactamente 120 % no se marca como topado**; 222 % queda en 120 % |
| 8 · Felicitaciones con respaldo, solo el delegado | CF-50 | PV-09 a PV-11, PM-08, PM-09 | Sin respaldo, 4 felicitaciones (cuentan 3), total no negativo |
| 9 · Ausencias ajustan la meta | CF-51 | PM-06, PM-07, PV-07, PV-08 | Ausencia que empieza antes del período, superposición |
| 10 · Resultado de equipo | CF-52 | PM-10 a PM-12, UI-16 | Integrante sin metas no cuenta en el promedio |
| Excel trimestral: TUBO | CF-53 | PM-05 | 3 de 4 resueltas = 75 % |
| Excel trimestral: metas por cargo | CF-57 | PM-14, PM-15, PV-12 a PV-16 | Suma 100 %, un solo período abierto **también en la base** |
| Base JJVV | CF-59, CF-60 | PO-01 a PO-06 | Socios en texto, territorio vacío, repetidos, sin registro, reimportar verificadas |
| Seguridad transversal | CF-55, CF-58, CF-63, CF-64 | PV-04 a PV-06, PE-01 a PE-06, SG-01 a SG-09 | Archivo renombrado, `X-Forwarded-For` falso, otra delegación |
| Rendimiento | CF-62 | PF-01 | 10 vs 500 actividades: mismas consultas |

Los casos CF-01 a CF-42 (acceso, recuperación, mantenedores, atenciones, permisos, interfaz) se mantienen de la primera parte de la EV2 y siguen aprobados.

---

## 6. Ejecución

```bash
python manage.py test pruebas                       # funcionales
python manage.py test pruebas_ui                    # navegador
SGR_DB_MOTOR=mysql python manage.py test pruebas    # contra MySQL 8
python scripts/generar_matriz_pruebas.py --ui       # ejecuta todo y rehace la matriz Excel
```

Evidencias:

- Capturas de las pruebas de interfaz: [`evidencias/`](evidencias/) (UI-01 a UI-17).
- Salida completa contra MySQL: [`ejecucion_mysql8.txt`](ejecucion_mysql8.txt).
- Planes de ejecución: [`../bd/explain_mysql8_antes_de_optimizar.txt`](../bd/explain_mysql8_antes_de_optimizar.txt) y [`../bd/explain_mysql8.txt`](../bd/explain_mysql8.txt).
- Estrés en AWS: [`estres/aws/`](estres/aws/).

---

## 7. Resultados obtenidos vs esperados

### 7.1 Resumen

| Indicador | Esperado | Obtenido | Estado |
|---|---|---|---|
| Casos funcionales aprobados | 100 % | 64 de 64 | Cumple |
| Pruebas automáticas (SQLite) | 0 fallas | 213 de 213 | Cumple |
| Pruebas automáticas (MySQL 8) | 0 fallas | 196 de 196 | Cumple |
| Errores de JavaScript o CSP en el navegador | 0 | 0 en 17 pruebas | Cumple |
| Consultas del tablero al crecer el volumen | Constantes | Iguales con 10 y 500 actividades | Cumple |
| Consulta más lenta de la matriz con 60.000 actividades | ≤ 10 ms | 2,1 ms (avance por ítem) | Cumple tras optimizar |
| Tasa de errores bajo carga (AWS, 100 usuarios) | < 1 % | 0 % | Cumple |
| Latencia p95 de páginas bajo carga | ≤ 800 ms | 320 ms con 10 usuarios; 3,7 s con 25 | Cumple hasta ~10-25 usuarios |

### 7.2 Diferencias encontradas durante las pruebas y su causa

Cada diferencia entre lo esperado y lo obtenido se analizó y se corrigió o se documentó.

| # | Esperado | Obtenido al probar | Causa | Acción |
|---|---|---|---|---|
| 1 | La base impide un segundo período abierto | En MySQL se podía (en SQLite no) | MySQL no admite índices únicos **parciales**; Django lo advierte (W036) y omite la restricción | Columna generada `marca_abierto` con índice único, válida en ambos motores. Prueba nueva PV-16 |
| 2 | La bandeja de validación responde en pocos ms con mucho volumen | 13,0 ms y ordenamiento en memoria de 12.236 filas | El índice no incluía el orden (`fecha DESC, id DESC`) | Índice `(delegacion, validacion, fecha DESC, id DESC)`: **0,5 ms**, sin ordenar |
| 3 | El avance por ítem usa su índice | Leía 4.004 filas completas (13,7 ms) | El optimizador prefería otro índice y debía ir a la tabla por `puntua` y `validacion` | Índice cubriente: **2,1 ms**, sin leer la tabla |
| 4 | El delegado ve una ficha con datos al abrir el tablero | Mostraba su propia ficha, vacía | El cargo Delegado no tiene metas en la matriz | Sin elección, abre la primera ficha del equipo con metas |
| 5 | Las pruebas de interfaz pasan con la CSP activa | 2 pruebas fallaron | Las esperas de Playwright evaluaban texto con `eval()`, que la CSP bloquea (la aplicación no lo usa) | Esperas consultadas desde Python. Confirma que la CSP bloquea código evaluado |
| 6 | UI-06 estable | Fallaba de forma intermitente | La prueba leía la lista dependiente antes de terminar de recargarse | Espera a que la lista tenga exactamente las opciones del nuevo tipo |
| 7 | Una prueba que cambia de usuario actúa como el segundo | Seguía con la sesión del primero | El acceso redirige sin volver a autenticar si ya hay sesión | La utilidad de pruebas cierra la sesión antes de entrar |

### 7.3 Diferencias entre el requerimiento y el Excel trimestral

El correo del requerimiento y la matriz Excel no coinciden en algunos valores. El sistema adopta uno y lo deja **configurable por período**, para no tener que cambiar código si la coordinación decide otro.

| Tema | Requerimiento (correo) | Excel trimestral | Adoptado | Dónde se cambia |
|---|---|---|---|---|
| Tope de sobrecumplimiento | 120 % por ítem | 150 % | 120 % por ítem y 150 % del total | Períodos → tope por ítem y tope total |
| Descuento por reclamo | — | −0,3 en hojas por cargo, −0,2 en RECLAMOS | 20 % | Períodos → descuento por reclamo |
| Ponderadores de «Planificación y control» | — | Suman 85 % | Se completa con «Informe a la jefatura» 15 % | Metas y ponderaciones |
| Meta de emergencias | — | 0 (división por cero) | 2 | Metas y ponderaciones |
| Base JJVV | — | 22 sin territorio, 8 con socios en texto, 108 fechas en texto, 1 repetida | Se importan con observación y quedan «por verificar» | Organizaciones |

### 7.4 Carga concurrente (AWS EC2 t3.small)

| Usuarios | Solicitudes | p95 | Errores | CPU |
|---|---|---|---|---|
| 10 | 478 | 320 ms | 0 % | 13 % |
| 25 | 1.100 | 3,7 s | 0 % | 31 % |
| 50 | 1.670 | 5,6 s | 0 % | 59 % |
| 100 | 1.216 | 38 s | 0 % | 93 % |

Sin errores en ninguna etapa y recuperación inmediata. La degradación viene de los **inicios de sesión simultáneos** (hash PBKDF2, intensivo en CPU); ya dentro, las páginas responden en ~160-220 ms. La carga real esperada (≈ 40 funcionarios en 6 delegaciones, que no ingresan todos en el mismo segundo) queda dentro de lo que soporta la instancia.

---

## 8. Recomendaciones

1. **Repetir la prueba de estrés en AWS con la matriz** tras publicar esta versión, agregando el registro de actividades al escenario de Locust.
2. **Instancia con 2 vCPU o más** (t3.medium) si se suman más delegaciones, o dos instancias tras un balanceador: el cuello de botella medido es la CPU en los inicios de sesión.
3. **HTTPS con dominio propio** (Let's Encrypt): la configuración está lista (`SGR_HTTPS=1`).
4. **Confirmar con la coordinación** los valores de la tabla 7.3 (tope, descuento, ponderadores); se cambian por período sin tocar código.
5. **Verificar las organizaciones con observaciones** de la base JJVV (las que quedan «por verificar») con cada delegación antes de usarlas en informes.
6. **Integración continua**: ejecutar `python manage.py test pruebas` y `pip-audit` en GitHub Actions en cada PR.
7. **Respaldo diario** de la base y de `/opt/sgr/archivos` (comandos en el manual técnico).
8. **Probar en Firefox y Safari** antes de la puesta en marcha (hoy se prueba en Chromium).
