#!/usr/bin/env bash
# Publica una nueva versión: sudo bash /opt/sgr/app/deploy/actualizar.sh
# (si el código se subió por scp/rsync en vez de Git, se omite el git pull)
set -euo pipefail
cd /opt/sgr/app
if [ -d .git ]; then sudo -u sgr git pull --ff-only; fi

# EV2: carpetas de evidencias y caché fuera del código (se agregan si la instancia es anterior)
install -d -o sgr -g sgr -m 750 /opt/sgr/archivos /opt/sgr/cache
grep -q '^SGR_ARCHIVOS_DIR=' /opt/sgr/.env || echo 'SGR_ARCHIVOS_DIR=/opt/sgr/archivos' >> /opt/sgr/.env
grep -q '^SGR_CACHE_DIR=' /opt/sgr/.env || echo 'SGR_CACHE_DIR=/opt/sgr/cache' >> /opt/sgr/.env

sudo -u sgr /opt/sgr/venv/bin/pip install -r requirements.txt
sudo -u sgr /opt/sgr/venv/bin/python manage.py migrate --noinput
# Catálogos, cargos, ítems, períodos y metas de la matriz (idempotente); con cuentas de evaluación, también la demo
if grep -q '^SGR_CUENTAS_DEMO=1' /opt/sgr/.env; then
  sudo -u sgr /opt/sgr/venv/bin/python manage.py sgr_inicializar --demo
else
  sudo -u sgr /opt/sgr/venv/bin/python manage.py sgr_inicializar
fi
sudo -u sgr /opt/sgr/venv/bin/python manage.py collectstatic --noinput
systemctl restart sgr
for _ in $(seq 1 20); do      # espera a que Gunicorn termine de arrancar
  curl -fsS http://127.0.0.1:8000/salud/ 2>/dev/null && echo " · versión publicada" && exit 0
  sleep 1
done
echo "El servicio no respondió; revise: journalctl -u sgr -n 50" >&2; exit 1
