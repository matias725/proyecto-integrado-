# Guía de instalación paso a paso

Tres formas de levantar el SGR, de la más simple a la de producción. Todas usan el mismo código; cambia solo el archivo `.env`.

| Opción | Para qué | Base de datos | Tiempo |
|---|---|---|---|
| [A. Local rápida](#a-instalación-local-rápida-sqlite) | Revisar el sistema o desarrollar | SQLite (sin instalar nada) | 5 min |
| [B. Local con MySQL](#b-instalación-local-con-mysql-8) | Probar como en producción | MySQL 8 | 15 min |
| [C. AWS EC2](#c-despliegue-en-aws-ec2) | Publicar | MySQL 8 en la instancia | 20 min |

Requisitos comunes: **Python 3.11 a 3.13** y **Git**. Compruebe con `python --version` (en Windows también `py --version`).

---

## A. Instalación local rápida (SQLite)

### Linux o macOS

```bash
git clone https://github.com/matias725/proyecto-integrado-.git sgr
cd sgr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
echo "SGR_DEBUG=1" >> .env
python manage.py migrate
python manage.py sgr_inicializar --demo
python manage.py runserver
```

### Windows (PowerShell)

```powershell
git clone https://github.com/matias725/proyecto-integrado-.git sgr
cd sgr
py -m venv .venv
.venv\Scripts\Activate.ps1          # si lo bloquea: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
copy .env.example .env
Add-Content .env "SGR_DEBUG=1"
python manage.py migrate
python manage.py sgr_inicializar --demo
python manage.py runserver
```

Abra **http://127.0.0.1:8000** e ingrese con cualquiera de las cuentas de evaluación (contraseña `Serena#2026`):

| Usuario | Perfil | Para revisar |
|---|---|---|
| `bcastillo` | Funcionario (Rural) | Registrar actividades, tablero propio, TUBO |
| `arojas` | Delegada (Rural y La Antena) | Validación, ausencias, felicitaciones, equipo |
| `emunoz` | Coordinador | Períodos, metas, cargos, catálogos |
| `admin` | Superadministrador | Todo, usuarios, roles, auditoría |
| `lectura` | Consultor | Solo lectura |

**Comprobación**: http://127.0.0.1:8000/salud/ debe responder `{"estado": "ok", ...}`.

> `sgr_inicializar` se puede ejecutar varias veces: no duplica datos. Sin `--demo` carga solo permisos, roles, catálogos, cargos, ítems y el período vigente con sus metas.

### Fijar la fecha para una demostración

Las reglas dependen del día (cierre semanal, ingresos de hoy, esperado al día). Para que una presentación muestre siempre lo mismo:

```bash
echo "SGR_FECHA_HOY=2026-11-04" >> .env
```

---

## B. Instalación local con MySQL 8

1. Instale MySQL 8:
   - **Ubuntu**: `sudo apt install mysql-server`
   - **Windows**: [MySQL Installer](https://dev.mysql.com/downloads/installer/), opción «Server only».
2. Cree la base y el usuario (cambie la clave en el archivo antes de ejecutarlo):

   ```bash
   mysql -u root -p < scripts/mysql_crear_bd.sql
   ```

3. En `.env`:

   ```ini
   SGR_DB_MOTOR=mysql
   SGR_DB_NOMBRE=sgr_laserena
   SGR_DB_USUARIO=sgr
   SGR_DB_CLAVE=la-clave-que-puso
   SGR_DB_HOST=127.0.0.1
   ```

4. Migre y cargue datos:

   ```bash
   python manage.py migrate
   python manage.py sgr_inicializar --demo
   python manage.py runserver
   ```

Para ejecutar las pruebas contra MySQL, el usuario necesita permiso sobre la base de pruebas (línea comentada en `scripts/mysql_crear_bd.sql`) y luego `python manage.py test pruebas`.

---

## C. Despliegue en AWS EC2

Arquitectura: **Nginx (80) → Gunicorn (127.0.0.1:8000) → MySQL 8 local**. Los secretos viven solo en `/opt/sgr/.env` (permisos 600).

1. **Instancia**: EC2 Ubuntu 24.04, t3.small, disco 20 GB.
2. **Grupo de seguridad**: HTTP 80 desde Internet; SSH 22 solo desde su IP.
3. **IP elástica** asociada a la instancia.
4. **Instalación** (por SSH):

   ```bash
   sudo apt update && sudo apt install -y git
   git clone https://github.com/matias725/proyecto-integrado-.git /tmp/sgr
   sudo bash /tmp/sgr/deploy/instalar_ec2.sh https://github.com/matias725/proyecto-integrado-.git
   ```

   El script instala dependencias y MySQL, crea la base con una clave aleatoria, escribe `/opt/sgr/.env`, crea las carpetas `/opt/sgr/archivos` (evidencias) y `/opt/sgr/cache`, migra, carga los datos y deja `nginx` y `sgr` en marcha.

5. **Comprobación**: `http://IP-ELÁSTICA/salud/`.
6. **Base JJVV real** (opcional, datos confidenciales: no se suben al repositorio):

   ```bash
   scp base_jjvv.xlsx ubuntu@IP:/tmp/
   cd /opt/sgr/app
   sudo -u sgr /opt/sgr/venv/bin/python manage.py sgr_importar_organizaciones /tmp/base_jjvv.xlsx --simular
   sudo -u sgr /opt/sgr/venv/bin/python manage.py sgr_importar_organizaciones /tmp/base_jjvv.xlsx
   rm /tmp/base_jjvv.xlsx
   ```

### Actualizar una instancia existente

```bash
sudo bash /opt/sgr/app/deploy/actualizar.sh
```

Baja el código, agrega las carpetas y variables nuevas si faltan, instala dependencias, migra, carga catálogos y metas de la matriz, publica los estáticos, reinicia y espera a que `/salud/` responda.

### HTTPS

Con un dominio apuntando a la IP: `sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d su-dominio`, luego en `/opt/sgr/.env` poner `SGR_HTTPS=1`, agregar `https://su-dominio` a `SGR_CSRF_ORIGENES` y reiniciar con `sudo systemctl restart sgr`.

---

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| `DisallowedHost` | La IP o dominio no está en `SGR_HOSTS` | Agréguelo en `.env` y reinicie |
| 403 «Formulario vencido» al enviar | Origen no autorizado para CSRF | Agregue `http://IP` o `https://dominio` a `SGR_CSRF_ORIGENES` |
| Página sin estilos en el servidor | No se ejecutó `collectstatic` | `python manage.py collectstatic --noinput` |
| `Access denied for user 'sgr'` | Clave de MySQL distinta a `.env` | Revise `SGR_DB_CLAVE` |
| `cryptography is required` | Falta la dependencia para MySQL 8 | `pip install -r requirements.txt` |
| «Demasiados intentos desde este equipo» | Límite por IP (20 envíos en 15 min) | Espere o ajuste `SGR_IP_MAX_INTENTOS` |
| El servicio no arranca | Error de configuración | `journalctl -u sgr -n 50` |
| Las evidencias desaparecen al actualizar | `SGR_ARCHIVOS_DIR` dentro de la carpeta del código | Use `/opt/sgr/archivos` (lo configura `actualizar.sh`) |
