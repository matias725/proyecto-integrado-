"""Configuración de Gunicorn para el servidor (AWS EC2)."""
import multiprocessing
import os

bind = os.environ.get('SGR_GUNICORN_BIND', '127.0.0.1:8000')   # Nginx recibe en el puerto 80/443
workers = int(os.environ.get('SGR_GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
threads = int(os.environ.get('SGR_GUNICORN_THREADS', 2))
timeout = 60
graceful_timeout = 30
keepalive = 5
max_requests = 1000            # recicla procesos para evitar fugas de memoria
max_requests_jitter = 100
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('SGR_LOG_NIVEL', 'info').lower()
forwarded_allow_ips = '127.0.0.1'
