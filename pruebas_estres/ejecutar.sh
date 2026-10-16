#!/usr/bin/env bash
# Carga progresiva: 10 → 25 → 50 → 100 usuarios concurrentes.
# Uso: bash pruebas_estres/ejecutar.sh http://IP-O-DOMINIO [segundos_por_etapa] [carpeta]
set -euo pipefail
HOST="${1:?Indique la URL, p. ej. http://127.0.0.1}"
DURACION="${2:-90}"
SALIDA="${3:-pruebas_estres/resultados/$(date +%Y%m%d-%H%M)}"
mkdir -p "$SALIDA"
for USUARIOS in 10 25 50 100; do
  TASA=$(( USUARIOS / 5 > 1 ? USUARIOS / 5 : 2 ))
  echo "== Etapa: $USUARIOS usuarios (llegada $TASA/s) durante ${DURACION}s"
  locust -f pruebas_estres/locustfile.py --host "$HOST" --headless \
         -u "$USUARIOS" -r "$TASA" -t "${DURACION}s" --stop-timeout 10 \
         --csv "$SALIDA/c$USUARIOS" --only-summary --loglevel WARNING || true
  sleep 10   # pausa para observar la recuperación del servidor
  echo "Tras $USUARIOS usuarios: /salud/ $(curl -s -o /dev/null -w '%{http_code} en %{time_total}s' "$HOST/salud/")" | tee -a "$SALIDA/salud.txt"
done
echo "Resultados en $SALIDA"
