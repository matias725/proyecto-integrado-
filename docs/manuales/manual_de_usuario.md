# Manual de usuario · SGR La Serena

Sistema de Gestión de Resultados de las delegaciones municipales. Reemplaza el Excel trimestral de la matriz SGR: cada funcionario registra lo que hace, el delegado lo valida y el sistema calcula el cumplimiento, el semáforo y el resultado del equipo.

> Las capturas usan datos ficticios de demostración (fecha del sistema: miércoles 04-11-2026).

**Contenido**

1. [Ingreso y recuperación de clave](#1-ingreso-y-recuperación-de-clave)
2. [Qué ve cada perfil](#2-qué-ve-cada-perfil)
3. [Funcionario: registrar el trabajo diario](#3-funcionario-registrar-el-trabajo-diario)
4. [Delegado: validar, ausencias y felicitaciones](#4-delegado-validar-ausencias-y-felicitaciones)
5. [Coordinación: períodos, metas y organizaciones](#5-coordinación-períodos-metas-y-organizaciones)
6. [Cómo se calcula el puntaje](#6-cómo-se-calcula-el-puntaje)
7. [Mensajes frecuentes y qué hacer](#7-mensajes-frecuentes-y-qué-hacer)

---

## 1. Ingreso y recuperación de clave

1. Abra el sistema y escriba su **usuario o correo** y su **contraseña**.
2. Si se equivoca 5 veces, la cuenta se bloquea 10 minutos. Si desde un mismo equipo se hacen muchos intentos con distintas cuentas, el sistema pausa los intentos de esa conexión durante 15 minutos.
3. ¿Olvidó la clave? Pulse **«¿Olvidó su contraseña?»**, escriba su correo y copie el **código de 6 dígitos** que llega (vence en 10 minutos). Luego defina una clave nueva de al menos 8 caracteres con mayúscula, minúscula, número y símbolo.

**Cuenta nueva.** Cuando el administrador o su delegado crea su cuenta, le llega un correo de bienvenida con su usuario y un enlace para **crear su propia contraseña**. El enlace sirve una sola vez y vence en 72 horas; si vence, use «¿Olvidó su contraseña?».

![Correo de bienvenida](capturas/15-correo-bienvenida.png)

![Crear contraseña](capturas/16-crear-contrasena.png)

Si trabaja en más de una delegación, elija la **delegación activa** en el selector de la cabecera. Todo lo que vea y registre corresponde a esa delegación.

![Inicio del funcionario](capturas/01-inicio-funcionario.png)

---

## 2. Qué ve cada perfil

| Perfil | Puede | No puede |
|---|---|---|
| **Funcionario** | Registrar sus actividades, adjuntar evidencias, ver su ficha y sus compromisos, ver organizaciones de su territorio | Ver actividades de otros, validar, registrar ausencias o felicitaciones |
| **Delegado municipal** | Todo lo del funcionario, más: ver al equipo, validar o rechazar, registrar ausencias, felicitaciones y reclamos, exportar informes | Cambiar metas o períodos; validar sus propias actividades |
| **Coordinador** | Configurar períodos, metas por cargo, cargos, ítems y catálogos; ver todas las delegaciones | Registrar actividades a nombre de otros |
| **Consultor** | Ver tablero, informes y catálogos | Registrar o modificar |
| **Superadministrador** | Todo, incluidos usuarios, roles, permisos y auditoría | Ver o cambiar la contraseña de otra persona |

El menú solo muestra lo que su perfil permite. Si intenta abrir una dirección que no le corresponde, verá «Acceso denegado» y el intento queda registrado.

---

## 3. Funcionario: registrar el trabajo diario

### 3.1 Ver mi avance

**Matriz SGR → Tablero y semáforo** muestra su cumplimiento, cuántos ingresos lleva hoy (máximo 7) y el avance de cada ítem de su cargo. La línea negra marca lo **esperado al día** según cuánto va del trimestre.

![Tablero del funcionario](capturas/02-tablero-funcionario.png)

Colores del semáforo:

- **Verde**: va igual o sobre lo esperado al día.
- **Naranjo**: está bajo lo esperado, pero sobre el 60 % de lo esperado.
- **Rojo**: está bajo el 60 % de lo esperado.

### 3.2 Registrar una actividad

**Actividades y TUBO → Registrar actividad**

![Registrar actividad](capturas/03-registrar-actividad.png)

1. **Fecha**: el día en que hizo la actividad. Puede registrar desde el lunes de la semana anterior hasta hoy; **la semana se cierra el lunes siguiente** (desde el martes ya no se puede ingresar la semana anterior).
2. **Ítem de la matriz**: solo aparecen los ítems con meta para su cargo.
3. **Actividad y detalle**: qué hizo, con suficiente detalle para que el delegado pueda validarlo.
4. **Naturaleza**:
   - *Acción realizada*: suma puntaje (el taller, la visita, la entrega).
   - *Gestión previa*: correos, coordinaciones o invitaciones. Se registra, pero **no suma**.
5. **Usuario atendido**: **nombre y teléfono son obligatorios para que sume**. Sin ellos la actividad se guarda, pero no cuenta.
   En la misma sección elija el **sector** del territorio (por ejemplo *Toqui* en Las Compañías) y, si sirve, una **referencia del lugar** (calle, pasaje o villa). Si elige una organización que ya tiene sector y deja el sector en blanco, se usa el de la organización.
6. **La solicita el delegado**: márquelo si el pedido vino del delegado o de la delegación. Se guarda como otra gestión y **no suma**.
7. **Estado**: si queda *Pendiente* o *En proceso*, indique la **fecha de compromiso**. Así entra al TUBO.
8. Pulse **Guardar actividad**. Aunque haga doble clic, se guarda una sola vez.

Puede registrar **hasta 7 actividades por día**. Al llegar al límite, el botón se desactiva. Registre a diario: acumular varios días en uno genera alertas para el delegado.

### 3.3 Cerrar un compromiso (TUBO)

**Compromisos (TUBO)** muestra las solicitudes con fecha de compromiso en una **tabla con filtros**:

- **Filtros**: búsqueda (folio, actividad, solicitante o área de apoyo), período, estado, **plazo** (vencidas, vencen en 7 días, al día, realizadas), **sector**, responsable (delegado y coordinación) y rango de **fecha de compromiso**. Las listas filtran al elegir una opción; «Limpiar filtros» vuelve a mostrar todo.
- **Resumen**: cuántas hay en el TUBO, cuántas realizadas (con la tasa de resolución frente a la meta habitual de 80 %), en proceso, e ingresadas o pendientes con sus vencidas.
- **Tabla**: lo pendiente primero, ordenado por fecha de compromiso; cada fila indica los días que faltan o los días de atraso, y lo realizado aparece tachado al final.
- **Tablero por estado**: las mismas solicitudes en 4 columnas (Ingresado, Pendiente, En proceso, Realizado), con los filtros aplicados.
- **Exportar a Excel** descarga exactamente lo filtrado, con sector y plazo.

Para cerrar un compromiso, abra la actividad con **Ver**, elija **Realizado**, escriba una observación y guarde. La actividad suma desde ese momento y queda en su historial.

![Compromisos](capturas/05-compromisos-tubo.png)

![Compromisos en tablero](capturas/20-compromisos-tablero.png)

### 3.4 Adjuntar evidencias

En el detalle de la actividad, sección **Evidencias**, adjunte fotos (JPG, PNG) o documentos PDF de hasta 2 MB. El sistema revisa que el archivo sea realmente del tipo indicado.

### 3.5 Mis actividades

**Actividades y TUBO** lista todo lo que registró, con búsqueda, filtros por estado, ítem y validación, y exportación a Excel. La columna «Puntaje» indica si suma y, si no, por qué.

![Mis actividades](capturas/04-mis-actividades.png)

### 3.6 Atenciones: seguimiento, abierta o cerrada

Toda atención que registre queda **Abierta**. En **Atenciones** el listado muestra el estado de cada una y se puede filtrar por *Abiertas* o *Cerradas*; la exportación a Excel incluye el estado, la fecha de cierre y quién la cerró.

1. Abra la atención con **Ver**.
2. En **Registrar seguimiento** elija *Registrar seguimiento (sigue abierta)* para anotar una gestión (llamada, derivación, visita), o *Cerrar la atención* cuando ya se respondió al vecino.
3. Escriba el comentario (obligatorio; al cerrar, la resolución entregada) y pulse **Guardar**.

Cada paso queda en el panel **Seguimiento** con su autor y fecha. Una atención cerrada no admite notas: si el vecino vuelve por lo mismo, use **Reabrir la atención** e indique el motivo. Funcionario y delegado pueden registrar seguimiento; el consultor y la coordinación solo lo ven.

---

## 4. Delegado: validar, ausencias y felicitaciones

### 4.1 Tablero del equipo

El delegado ve el **resultado del equipo** (promedio de quienes tienen metas), el semáforo de cada integrante, las **alertas de registro** y puede abrir la ficha de cualquier integrante con «Ver ficha de».

![Tablero del delegado](capturas/06-tablero-delegado.png)

Las **alertas** (regla 6) no bloquean: avisan cuando alguien llega al tope diario, repite el mismo texto, ingresa muchas actividades días después o tiene muchas que no suman. Úselas para conversar con el equipo.

### 4.2 Validar

**Validación** muestra las actividades pendientes de su delegación. Puede **validar** o **rechazar** indicando el motivo. Una actividad rechazada deja de sumar. No puede validar sus propias actividades.

![Bandeja de validación](capturas/07-bandeja-validacion.png)

### 4.3 Ausencias

**Ausencias del equipo**: registre licencias, vacaciones, emergencias, días administrativos y compensatorios. La meta del funcionario se ajusta a sus días efectivos. Ejemplo: 23 días de licencia en un trimestre de 92 días reducen una meta de 90 a 67,5. El sistema rechaza ausencias superpuestas.

![Ausencias y semáforo](capturas/08-ausencias-semaforo.png)

### 4.4 Felicitaciones y reclamos

Registre la felicitación o el reclamo **con su respaldo formal** (correo, carta, libro de reclamos) en PDF o imagen. Sin respaldo no se guarda. Solo el delegado puede registrarlas.

- Cada felicitación suma **+10 %** al total del funcionario (máximo 3 en el período).
- Cada reclamo descuenta **20 %**.

![Felicitaciones y reclamos](capturas/09-felicitaciones-reclamos.png)

### 4.5 Informes

**Informes** muestra la matriz completa del período por funcionario e ítem y la exporta a Excel (funcionario, cargo, ítem, meta, meta ajustada, avance, cumplimiento, ajustes, total y semáforo).

![Informes](capturas/10-informes.png)

### 4.6 Organizaciones

**Organizaciones** lista las juntas de vecinos y organizaciones funcionales de su territorio, con su **territorio y sector**, sus **funcionarios encargados** y cuántos puestos de encargado están ocupados («2 de 3»). Las marcadas «Por verificar» vienen de la base JJVV y tienen alguna observación (socios no numéricos, fechas dudosas, sector deducido del nombre).

Al crear o editar una organización el formulario se divide en:

- **Identificación**: nombre y subfamilia.
- **Territorio y sector**: la delegación y, dentro de ella, el sector. La lista de sectores cambia según la delegación elegida.
- **Encargados municipales**: hasta **3 funcionarios** de la delegación a cargo de la organización (Encargado 1, 2 y 3). La lista muestra los funcionarios con cargo de la delegación elegida, con su cargo. Se pueden dejar puestos sin asignar; un funcionario no se repite.
- **Registro municipal**: registro de personalidad jurídica, fechas, registro de directiva, socios y observación.

La ficha muestra los 3 puestos de encargado como tarjetas (nombre, cargo y correo del funcionario). La búsqueda también encuentra una organización por el nombre de un encargado, y la dirección `/organizaciones/?a_cargo=mias` lista las que usted tiene a cargo. En la ficha de cada usuario aparecen sus «Organizaciones a cargo»; si a un funcionario le quitan la delegación, deja de ser encargado de sus organizaciones.

![Organizaciones](capturas/11-organizaciones.png)

![Encargados de la organización](capturas/18-organizacion-encargados.png)

---

## 5. Coordinación: períodos, metas y organizaciones

### 5.1 Períodos

**Configuración → Períodos** muestra:

- **Período en curso**: su línea de tiempo (por ejemplo «Día 35 de 92»), los días que quedan, el avance esperado hoy y un resumen de funcionarios con registros, actividades, realizadas, las que suman puntaje, las por validar y los compromisos vencidos.
- **Parámetros de cálculo** como tarjetas con su explicación: tope por ítem 120 %, tope total 150 %, felicitación +10 % (máximo 3), reclamo −20 %, umbral naranjo 60 % y cumplimiento mínimo 80 %.
- **Todos los períodos** como tarjetas, con su estado (abierto o cerrado), su fase según la fecha (en curso, finalizado o por comenzar), metas, actividades y realizadas, y los botones **Ver detalle**, **Abrir/Cerrar** y **Copiar metas**.
- **Nuevo período**: nombre y fechas, topes y semáforo, felicitaciones y reclamos.

**Ver detalle** abre la ficha del período con las actividades por estado del TUBO y por mes, el **resultado por delegación** (promedio del equipo con su semáforo frente a lo esperado al día), las metas por cargo (con aviso si los ponderadores no suman 100 %) y los parámetros. El delegado ve solo sus delegaciones.

Solo puede haber **un período abierto**. Al cerrar un período sus actividades quedan congeladas.

![Períodos](capturas/12-periodos.png)

![Detalle del período](capturas/17-periodo-detalle.png)

### 5.2 Metas y ponderaciones

**Metas y ponderaciones**: para cada cargo, la meta y el ponderador de cada ítem. Los ponderadores de un cargo deben sumar 100 %. Los ítems de tipo TUBO se miden como porcentaje de solicitudes resueltas.

![Metas](capturas/13-metas-ponderaciones.png)

### 5.3 Importar la base de organizaciones

La importación se hace en el servidor (no desde el navegador) porque la base contiene datos personales:

```bash
python manage.py sgr_importar_organizaciones base_jjvv.xlsx --simular   # revisa sin guardar
python manage.py sgr_importar_organizaciones base_jjvv.xlsx             # importa
```

---

## 6. Cómo se calcula el puntaje

| Paso | Fórmula |
|---|---|
| Meta ajustada | meta × días efectivos ÷ días del período (regla 9) |
| Cumplimiento del ítem | avance ÷ meta ajustada × 100, **máximo 120 %** (regla 7) |
| Aporte del ítem | cumplimiento × ponderador ÷ 100 |
| Total | suma de aportes + 10 % por felicitación (máx. 3) − 20 % por reclamo, entre 0 % y 150 % |
| Esperado al día | días transcurridos ÷ días del período × 100 |
| Resultado del equipo | promedio del total de quienes tienen metas (regla 10) |

Solo suman las actividades **realizadas**, que **no** sean gestión previa, **no** las haya pedido el delegado, **tengan** nombre y teléfono, y **no** hayan sido rechazadas.

---

## 7. Administración: usuarios y delegaciones

- **Contraseñas.** Nadie, ni siquiera el superadministrador, puede ver ni cambiar la contraseña de otra persona. Al crear una cuenta no se escribe contraseña: la persona recibe un correo de bienvenida con un enlace para crear la suya. Si la olvida, la recupera con «¿Olvidó su contraseña?».
- **Cargo.** El formulario de usuario incluye el cargo, que define las metas de la matriz SGR que se le aplican.
- **Comuna de la delegación.** Al crear una delegación, la comuna viene seleccionada en **La Serena**; se puede elegir otra comuna de la Región de Coquimbo en la lista.
- **Sectores del territorio.** En **Configuración → Sectores del territorio** se mantienen las partes del territorio de cada delegación (barrios, poblaciones o localidades), como la columna «TERRITORIO» del TUBO de la matriz. Las Compañías (Latorre, Rukalaf, Toqui, Zorrilla) y La Antena (Alfalfares, Antena, Ceres, La Florida) vienen de la matriz Excel; el resto parte con sectores de referencia que cada delegación confirma. El delegado administra los de sus delegaciones; un sector con organizaciones o actividades no se elimina (se desactiva). La ficha de cada delegación lista sus sectores.

![Sectores del territorio](capturas/19-sectores.png)
- **Bandeja de correos de prueba.** Con el correo real activado, la bandeja guarda una copia sin códigos ni enlaces para crear contraseña. Solo sin servidor de correo (entorno de evaluación local) se ven completos.

---

## 8. Mensajes frecuentes y qué hacer

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| «Ya registró 7 actividades hoy, el máximo diario» | Llegó al límite de la regla 3 | Registre el resto mañana (si la semana sigue abierta) |
| «La semana del … ya está cerrada» | Intentó ingresar una fecha de una semana cerrada | No se puede; converse con su delegado |
| «Ingrese un teléfono chileno de 9 dígitos» | El teléfono no es válido | Escriba 9 dígitos, por ejemplo 912345678 |
| «Una solicitud que no queda realizada necesita fecha de compromiso» | Eligió Pendiente o En proceso | Indique hasta cuándo se compromete |
| «El contenido del archivo no corresponde a su extensión» | El archivo fue renombrado o está dañado | Exporte de nuevo a PDF o tome otra foto |
| «Demasiados intentos desde este equipo» | Muchos intentos de acceso desde la misma conexión | Espere 15 minutos |
| «Acceso denegado» | Su perfil no permite esa acción | Pida acceso al administrador si lo necesita |
| «Este campo es obligatorio» al guardar un seguimiento | Faltó el comentario | Escriba qué se hizo o la resolución entregada |
