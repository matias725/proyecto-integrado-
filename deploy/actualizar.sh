#!/usr/bin/env bash
# Publica una nueva versión: sudo bash /opt/sgr/app/deploy/actualizar.sh
set -euo pipefail
cd /opt/sgr/app
sudo -u sgr git pull --ff-only
sudo -u sgr /opt/sgr/venv/bin/pip install -r requirements.txt
sudo -u sgr /opt/sgr/venv/bin/python manage.py migrate --noinput
sudo -u sgr /opt/sgr/venv/bin/python manage.py collectstatic --noinput
systemctl restart sgr
curl -fsS http://127.0.0.1:8000/salud/ && echo " · versión publicada"
