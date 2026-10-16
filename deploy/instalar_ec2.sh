#!/usr/bin/env bash
# =====================================================================
# Instalación del SGR en una instancia EC2 Ubuntu 24.04 (una sola vez).
# Uso:  sudo bash deploy/instalar_ec2.sh https://github.com/USUARIO/REPO.git
# Deja: MySQL 8 local, Gunicorn como servicio y Nginx en el puerto 80.
# Si usa Amazon RDS, omita la sección MySQL y complete SGR_DB_HOST en .env.
# =====================================================================
set -euo pipefail
REPO="${1:?Indique la URL del repositorio Git}"
IP_PUBLICA="$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo localhost)"

apt-get update
apt-get install -y python3-venv python3-pip nginx mysql-server git

# --- Usuario y código ---------------------------------------------------
id -u sgr >/dev/null 2>&1 || useradd --system --create-home --home-dir /opt/sgr --shell /bin/bash sgr
sudo -u sgr git clone "$REPO" /opt/sgr/app
sudo -u sgr python3 -m venv /opt/sgr/venv
sudo -u sgr /opt/sgr/venv/bin/pip install -r /opt/sgr/app/requirements.txt

# --- Base de datos MySQL local -------------------------------------------
CLAVE_BD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
sed "s/CAMBIAR_CLAVE/${CLAVE_BD}/; s/'sgr'@'%'/'sgr'@'localhost'/g" /opt/sgr/app/scripts/mysql_crear_bd.sql | mysql

# --- Secretos (fuera del repositorio) ------------------------------------
cat > /opt/sgr/.env <<ENV
SGR_DEBUG=0
SGR_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
SGR_HOSTS=${IP_PUBLICA},localhost,127.0.0.1
SGR_CSRF_ORIGENES=http://${IP_PUBLICA}
SGR_CUENTAS_DEMO=1
SGR_DB_MOTOR=mysql
SGR_DB_NOMBRE=sgr_laserena
SGR_DB_USUARIO=sgr
SGR_DB_CLAVE=${CLAVE_BD}
SGR_DB_HOST=127.0.0.1
ENV
chown sgr:sgr /opt/sgr/.env && chmod 600 /opt/sgr/.env
ln -sf /opt/sgr/.env /opt/sgr/app/.env

# --- Migraciones, datos iniciales y archivos estáticos ---------------------
cd /opt/sgr/app
sudo -u sgr /opt/sgr/venv/bin/python manage.py migrate --noinput
sudo -u sgr /opt/sgr/venv/bin/python manage.py sgr_inicializar --demo
sudo -u sgr /opt/sgr/venv/bin/python manage.py collectstatic --noinput

# --- Servicios -----------------------------------------------------------
cp deploy/sgr.service /etc/systemd/system/sgr.service
cp deploy/nginx-sgr.conf /etc/nginx/sites-available/sgr
ln -sf /etc/nginx/sites-available/sgr /etc/nginx/sites-enabled/sgr
rm -f /etc/nginx/sites-enabled/default
chmod 755 /opt/sgr
systemctl daemon-reload
systemctl enable --now sgr
nginx -t && systemctl restart nginx

echo "Listo: http://${IP_PUBLICA}/  ·  salud: http://${IP_PUBLICA}/salud/"
