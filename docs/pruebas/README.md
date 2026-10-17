# Pruebas del SGR · EV2

| Archivo o carpeta | Contenido |
|---|---|
| `matriz_pruebas_sgr_ev2.xlsx` | Matriz de pruebas funcionales (requisito, módulo, precondiciones, pasos, esperado, obtenido, estado, evidencia, responsable, fecha), detalle de las pruebas automatizadas, estrés, umbrales y pendientes |
| `evidencias/` | Capturas generadas por las pruebas de interfaz (`UI-xx`), una por caso |
| `estres/local/` | Resultados de Locust (`cNN_stats.csv`, historial por segundo) y consumo de CPU/memoria (`monitor.csv`) de la corrida local |
| `estres/aws/` | Resultados de la misma prueba contra el servidor publicado (EC2 t3.small, 17-10-2026) y `monitor.csv` del servidor |

## Cómo regenerar todo

```bash
python manage.py test pruebas                       # 125 pruebas funcionales
python manage.py test pruebas_ui                    # 14 pruebas en navegador + capturas
python scripts/generar_matriz_pruebas.py --ui       # vuelve a ejecutar todo y rehace la matriz
```

Prueba de estrés (en el servidor, el monitor de recursos; desde otro equipo, Locust):

```bash
python pruebas_estres/monitor.py docs/pruebas/estres/aws/monitor.csv &     # en el servidor
bash pruebas_estres/ejecutar.sh http://IP-ELÁSTICA 90 docs/pruebas/estres/aws
python scripts/generar_matriz_pruebas.py --ui --estres docs/pruebas/estres/aws --entorno-estres "AWS EC2 t3.small …"
```

## Identificadores

| Prefijo | Grupo |
|---|---|
| PA | Acceso |
| PR | Recuperación de contraseña |
| PC | Mantenedores (CRUD) |
| PI | Integridad de relaciones |
| PL | Listados, búsqueda, paginador y Excel |
| PP | Perfiles y permisos |
| PD | Contexto de delegación |
| PT | Ingreso de atención |
| PS | SweetAlert2 |
| PU | Auditoría |
| PX | Sistema (salud, errores, CSRF, módulos simulados) |
| UI | Pruebas en navegador real |
| CF | Casos funcionales de la matriz (agrupan las anteriores) |
