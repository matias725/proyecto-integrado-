# Pruebas del SGR · EV2

| Archivo o carpeta | Contenido |
|---|---|
| `plan_de_pruebas_ev2.md` | Plan: estrategia, entorno, criterios, trazabilidad con las 10 reglas, resultados obtenidos vs esperados y recomendaciones |
| `ejecucion_mysql8.txt` | Salida de las 205 pruebas contra MySQL 8.0 |
| `matriz_pruebas_sgr_ev2.xlsx` | Matriz de pruebas funcionales (requisito, módulo, precondiciones, pasos, esperado, obtenido, estado, evidencia, responsable, fecha), detalle de las pruebas automatizadas, estrés, umbrales y pendientes |
| `evidencias/` | Capturas generadas por las pruebas de interfaz (`UI-xx`), una por caso |
| `estres/local/` | Resultados de Locust (`cNN_stats.csv`, historial por segundo) y consumo de CPU/memoria (`monitor.csv`) de la corrida local |
| `estres/aws/` | Resultados de la misma prueba contra el servidor publicado (EC2 t3.small, 17-10-2026) y `monitor.csv` del servidor |

## Cómo regenerar todo

```bash
python manage.py test pruebas                       # 205 pruebas funcionales
python manage.py test pruebas_ui                    # 17 pruebas en navegador + capturas
SGR_DB_MOTOR=mysql python manage.py test pruebas    # las mismas contra MySQL 8 (ejecucion_mysql8.txt)
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
| PX | Sistema (salud, errores, CSRF, módulos de la matriz) |
| RG | Reglas del nuevo requerimiento con sus bordes |
| PM | Cálculo de la matriz (metas, tope, ausencias, semáforo, equipo) |
| PV | Validación, ausencias, felicitaciones y acceso por objeto |
| PE | Evidencias y archivos |
| PO | Organizaciones e importación de la base JJVV |
| PF | Rendimiento (consultas por pantalla) |
| SG | Seguridad (CSP, cabeceras, límite por IP) |
| UI | Pruebas en navegador real |
| CF | Casos funcionales de la matriz (agrupan las anteriores) |
