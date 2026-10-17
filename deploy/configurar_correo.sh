#!/usr/bin/env bash
# =====================================================================
# Activa el envío real de correos (códigos de recuperación) con Gmail.
# Uso en el servidor:  sudo bash /opt/sgr/app/deploy/configurar_correo.sh
# Requiere una «contraseña de aplicación» de Google (16 letras), creada en
# https://myaccount.google.com/apppasswords con la verificación en 2 pasos activa.
# Los correos se siguen guardando también en la Bandeja de correos de prueba.
# =====================================================================
set -euo pipefail
ENV_FILE=/opt/sgr/.env

read -rp "Correo Gmail que enviará los códigos: " GMAIL
[[ "$GMAIL" == *@* ]] || { echo "Escriba el correo completo, por ejemplo nombre@gmail.com." >&2; exit 1; }
while true; do
  read -rsp "Contraseña de aplicación de Google (16 letras, no se muestra): " CLAVE; echo
  CLAVE="${CLAVE//[[:space:]]/}"           # Google la muestra en grupos de 4 con espacios
  [ "${#CLAVE}" -eq 16 ] && break
  echo "Se recibieron ${#CLAVE} caracteres y deben ser 16. Vuelva a pegarla (clic derecho) y presione Enter."
done

# Quita la configuración de correo anterior y agrega la nueva
sed -i '/^SGR_CORREO_BACKEND=/d; /^SGR_BANDEJA_REENVIAR_SMTP=/d; /^SGR_SMTP_/d; /^SGR_CORREO_REMITENTE=/d' "$ENV_FILE"
cat >> "$ENV_FILE" <<ENV
SGR_CORREO_BACKEND=cuentas.correo.BandejaBackend
SGR_BANDEJA_REENVIAR_SMTP=1
SGR_SMTP_HOST=smtp.gmail.com
SGR_SMTP_PUERTO=587
SGR_SMTP_TLS=1
SGR_SMTP_USUARIO=${GMAIL}
SGR_SMTP_CLAVE=${CLAVE}
SGR_CORREO_REMITENTE=SGR La Serena <${GMAIL}>
ENV
chown sgr:sgr "$ENV_FILE" && chmod 600 "$ENV_FILE"
systemctl restart sgr

cd /opt/sgr/app
echo "Enviando correo de prueba a ${GMAIL}…"
sudo -u sgr /opt/sgr/venv/bin/python manage.py sgr_probar_correo "$GMAIL"
