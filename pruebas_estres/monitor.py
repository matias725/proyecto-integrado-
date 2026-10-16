"""Muestrea CPU y memoria del servidor durante la prueba de estrés.

Uso: python pruebas_estres/monitor.py salida.csv  (Ctrl+C para terminar)
Registra CPU total, memoria usada y el consumo de los procesos gunicorn y mysqld.
"""
import csv
import sys
import time

import psutil

salida = sys.argv[1] if len(sys.argv) > 1 else 'monitor.csv'
with open(salida, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['epoch', 'segundo', 'cpu_total_pct', 'memoria_usada_mb', 'memoria_pct', 'gunicorn_cpu_pct',
                'gunicorn_mem_mb', 'mysqld_cpu_pct', 'mysqld_mem_mb'])
    inicio = time.time()
    psutil.cpu_percent(None)
    procesos = {}
    try:
        while True:
            time.sleep(1)
            grupos = {'gunicorn': [0.0, 0.0], 'mysqld': [0.0, 0.0]}
            for p in psutil.process_iter(['name', 'cmdline']):
                nombre = 'gunicorn' if 'gunicorn' in ' '.join(p.info['cmdline'] or []) else p.info['name']
                if nombre in grupos:
                    if p.pid not in procesos:
                        procesos[p.pid] = p
                        p.cpu_percent(None)
                        continue
                    try:
                        grupos[nombre][0] += procesos[p.pid].cpu_percent(None)
                        grupos[nombre][1] += p.memory_info().rss / 1048576
                    except psutil.Error:
                        pass
            mem = psutil.virtual_memory()
            w.writerow([round(time.time()), round(time.time() - inicio), psutil.cpu_percent(None), round(mem.used / 1048576),
                        mem.percent, round(grupos['gunicorn'][0], 1), round(grupos['gunicorn'][1]),
                        round(grupos['mysqld'][0], 1), round(grupos['mysqld'][1])])
            f.flush()
    except KeyboardInterrupt:
        pass
