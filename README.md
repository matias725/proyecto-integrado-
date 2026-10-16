# SGR · Sistema de Gestión de Resultados — La Serena

Sistema web para registrar y supervisar la gestión de las **delegaciones municipales de la Ilustre Municipalidad de La Serena**: atenciones a vecinos y vecinas, catálogos de atención, usuarios, roles y permisos por delegación.

Proyecto Integrado · INACAP 2026 · **Segunda evaluación (EV2)**.

| Integrante | Responsabilidad principal en la EV2 |
|---|---|
| **Alexis Muñoz** | Acceso, recuperación de contraseña, roles y permisos |
| **Matías Zepeda** | Mantenedores (CRUD), listados y exportación a Excel |
| **Carlos Araya** | Ingreso de atención, pruebas funcionales y de estrés, despliegue en AWS |

> Todos los datos de la aplicación son **ficticios** (RUT, nombres, correos `@example.test`).

---

## 1. Qué incluye esta entrega

| Módulo | Estado | Detalle |
|---|---|---|
| Inicio de sesión | **Operativo** | Usuario **o** correo + contraseña, bloqueo temporal tras 5 intentos fallidos, cierre de sesión, auditoría |
| Recuperación de contraseña | **Operativo** | 3 pasos: código de 6 dígitos por correo (vence en 10 min, reenvío a los 45 s, máximo 5 intentos y 5 códigos por hora), nueva contraseña con requisitos |
| Delegaciones | **Operativo** | CRUD completo, búsqueda, paginador, Excel |
| Roles y permisos | **Operativo** | CRUD + matriz de permisos por módulo y acción; alcance global o por delegación |
| Usuarios | **Operativo** | CRUD, rol, delegaciones autorizadas, contraseña con requisitos |
| Ítems y metas (ítems) | **Operativo** | CRUD de ítems de medición |
| Tipo de Atención | **Operativo** | CRUD; no se desactiva si tiene sub atenciones activas |
| Sub Atención | **Operativo** | CRUD; asociada a un tipo activo, nombre único dentro del tipo |
| Ingreso de atención | **Operativo** | Lista dependiente tipo → sub atención, delegación/responsable/fecha automáticos, folio, sin doble envío |
| Listado de atenciones | **Operativo** | Filtrado por la delegación activa, búsqueda por folio/RUT/nombre, Excel |
| Auditoría | **Operativo** | Solo lectura, filtros y Excel |
| Bandeja de correos de prueba | **Operativo** | Muestra los correos de recuperación sin necesidad de SMTP (solo Superadministrador) |
| Tablero, actividades, evidencias, validación, agenda, atención social, períodos, metas, informes | **Simulado** | Pantallas navegables de la EV1 con datos de demostración en memoria, sujetas a los permisos reales del rol. Se marcan con la etiqueta «Simulado» |
| Despliegue en AWS | **Pendiente** | Archivos listos en `deploy/` y guía en la sección 6; se completa al publicar |

### Perfiles de evaluación

Contraseña de todas las cuentas: **`Serena#2026`** (se muestran en la pantalla de acceso mientras `SGR_CUENTAS_DEMO=1`).

| Usuario | Rol | Delegaciones | Qué demuestra |
|---|---|---|---|
| `admin` | Superadministrador | todas (global) | Todos los módulos, roles, auditoría y bandeja de correos |
| `emunoz` | Coordinador | todas (global) | Mantiene catálogos de atención; consulta usuarios, roles y auditoría |
| `arojas` | Delegado municipal | DEL06 Rural y DEL03 La Antena | **Selector de delegación**; administra funcionarios solo de sus delegaciones |
| `bcastillo` | Funcionario | DEL06 Rural | **Contexto fijo**; registra atenciones de su delegación |
| `lectura` | Consultor | todas (global) | Solo lectura |
| `dfuentes` | Funcionario | DEL01 Centro | Cuenta **inactiva**: no puede ingresar |

---

## 2. Requisitos

- Python 3.11 o superior
- MySQL 8 (servidor) — en desarrollo se puede usar SQLite sin instalar nada
- Git

## 3. Instalación local

```bash
git clone <URL-del-repositorio> sgr && cd sgr
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # Windows: copy .env.example .env
# Edite .env: para desarrollo basta con SGR_DEBUG=1

python manage.py migrate
python manage.py sgr_inicializar --demo   # permisos, roles, catálogos y cuentas de evaluación
python manage.py runserver
```

Abrir `http://127.0.0.1:8000`.

`sgr_inicializar` es idempotente: puede ejecutarse varias veces sin duplicar datos. Sin `--demo` carga solo permisos, roles y catálogos (sin cuentas ni atenciones).

## 4. Configuración

Toda la configuración se lee de variables de entorno (archivo `.env`, que **no** se sube al repositorio). La plantilla comentada es [`.env.example`](.env.example). Las más importantes:

| Variable | Uso |
|---|---|
| `SGR_DEBUG` | `1` solo en desarrollo |
| `SGR_SECRET_KEY` | Obligatoria en el servidor |
| `SGR_HOSTS`, `SGR_CSRF_ORIGENES` | IP pública o dominio de AWS |
| `SGR_DB_MOTOR=mysql` y `SGR_DB_*` | Conexión a MySQL 8 |
| `SGR_CORREO_BACKEND`, `SGR_SMTP_*` | Correo real (por defecto, bandeja de prueba) |
| `SGR_HTTPS=1` | Cookies seguras, redirección y HSTS cuando hay certificado |

### Base de datos

- Esquema: se crea con `python manage.py migrate`.
- Script SQL equivalente (MySQL 8): [`docs/bd/sgr_ev2_esquema_mysql.sql`](docs/bd/sgr_ev2_esquema_mysql.sql).
- Creación de la base y del usuario de la aplicación: [`scripts/mysql_crear_bd.sql`](scripts/mysql_crear_bd.sql).

### Logo institucional

La interfaz sigue las normas gráficas de la Municipalidad (color institucional `#920000`, tipografía Arial). El logo oficial **no se incluye** para no reproducirlo de forma no autorizada: coloque el archivo oficial como `static/img/logo-municipalidad.png` y el sistema lo mostrará automáticamente (ver `static/img/LEEME.txt`).

---

## 5. Pruebas

```bash
python manage.py test pruebas            # 124 pruebas funcionales automatizadas (≈ 5 s)
pip install -r requirements-dev.txt && playwright install chromium
python manage.py test pruebas_ui         # 14 pruebas de interfaz en navegador real (SweetAlert2, doble envío…)
```

| Grupo | Archivo | Qué cubre |
|---|---|---|
| PA | `pruebas/test_acceso.py` | Acceso correcto/incorrecto, campos vacíos, cuenta inactiva, bloqueo, logout, rutas protegidas |
| PR | `pruebas/test_recuperacion.py` | Código válido, incorrecto, vencido, reutilizado, reenvío, límites, requisitos de contraseña |
| PC · PI · PL | `pruebas/test_mantenedores.py` | CRUD de los 6 mantenedores, integridad de relaciones, búsqueda, paginación, Excel |
| PP · PD | `pruebas/test_permisos.py` | Menú por rol, 403 al alterar rutas, escalada de privilegios, contexto de delegación |
| PT | `pruebas/test_atenciones.py` | Ingreso de atención, lista dependiente, doble envío, alcance por delegación |
| PS · PU · PX | `pruebas/test_sistema.py` | Mensajes SweetAlert2, auditoría, salud, CSRF, módulos simulados |
| UI | `pruebas_ui/test_interfaz.py` | Diálogos y confirmaciones en el navegador, con capturas en `docs/pruebas/evidencias/` |

Las pruebas también se ejecutaron contra **MySQL 8.0** (`SGR_DB_MOTOR=mysql`), con el mismo resultado.

- Matriz de pruebas funcionales: [`docs/pruebas/matriz_pruebas_sgr_ev2.xlsx`](docs/pruebas/matriz_pruebas_sgr_ev2.xlsx)
- Pruebas de estrés (Locust, carga progresiva 10 → 100 usuarios): [`pruebas_estres/`](pruebas_estres/) y resultados en [`docs/pruebas/estres/`](docs/pruebas/estres/)

```bash
bash pruebas_estres/ejecutar.sh http://IP-O-DOMINIO 90    # 4 etapas de 90 s
```

---

## 6. Despliegue en AWS

Arquitectura prevista: **EC2 (Ubuntu 24.04) + Nginx + Gunicorn + MySQL 8**, con los secretos solo en `/opt/sgr/.env` del servidor.

| Archivo | Función |
|---|---|
| `deploy/instalar_ec2.sh` | Instala dependencias, MySQL, crea `.env` con claves aleatorias, migra, carga datos y deja los servicios en marcha |
| `deploy/sgr.service` | Servicio systemd de Gunicorn |
| `deploy/nginx-sgr.conf` | Proxy inverso y archivos estáticos |
| `deploy/actualizar.sh` | Publica una nueva versión (`git pull` + migraciones + reinicio) |
| `gunicorn.conf.py` | Procesos y tiempos de Gunicorn |

Pasos resumidos:

1. Crear una instancia EC2 Ubuntu 24.04 (t3.small o t3.micro) con un grupo de seguridad que permita **HTTP 80** desde Internet y **SSH 22** solo desde la IP del equipo.
2. Asignar una **IP elástica**.
3. Conectarse por SSH y ejecutar `sudo bash instalar_ec2.sh <URL-del-repositorio>` (el script está en `deploy/`).
4. Verificar `http://IP-ELÁSTICA/salud/` → `{"estado": "ok"}` e ingresar con las cuentas de evaluación.

**URL pública:** _se completará al publicar_ · **Acceso:** cuentas de la sección 1.

---

## 7. Estructura del proyecto

```
sgr/            configuración de Django (settings por variables de entorno)
cuentas/        usuario, roles, permisos, acceso, recuperación, contexto de delegación
catalogos/      delegaciones, ítems, tipos y sub atenciones
atenciones/     ingreso y listado de atenciones
core/           motor de mantenedores (CRUD), Excel, auditoría y módulos simulados de la EV1
templates/      plantillas (layout institucional, parciales, pantallas)
static/         CSS, JS, SweetAlert2 y Bootstrap Icons (servidos localmente)
pruebas/        pruebas automatizadas · pruebas_ui/ navegador · pruebas_estres/ Locust
deploy/         archivos de despliegue en AWS · scripts/ SQL de creación
docs/           SQL del esquema, matriz de pruebas, evidencias y resultados de estrés
```

## 8. Seguridad aplicada

- Contraseñas con hash (PBKDF2) y requisitos: 8+ caracteres, mayúscula, minúscula, número y carácter especial.
- Mensajes de acceso y recuperación que no revelan si una cuenta existe; códigos guardados con hash.
- Cada vista declara el módulo y la acción que exige; el servidor responde **403** y registra en auditoría cualquier intento fuera del perfil o de la delegación autorizada.
- La delegación, el responsable y la fecha de una atención se asignan en el servidor, nunca desde el formulario.
- Protección CSRF, cookies `HttpOnly`, `X-Frame-Options: DENY`, sin inyección de fórmulas en Excel, exportaciones sin contraseñas ni tokens.
- Secretos fuera del código (`.env` en `.gitignore`).
