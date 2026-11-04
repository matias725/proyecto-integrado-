# Cómo trabajamos en el SGR

Guía del equipo para colaborar en el repositorio. Si algo de aquí deja de servir, se cambia en un PR como cualquier otro archivo.

## Ramas

| Rama | Uso |
|---|---|
| `main` | Lo que está publicado o listo para publicar. No se sube directo a `main`. |
| `ev2/<tema>` · `ev3/<tema>` | Trabajo de una evaluación, por tema: `ev2/matriz-sgr`, `ev2/recuperacion-clave` |
| `arreglo/<tema>` | Corrección puntual sobre lo publicado |

```bash
git checkout main && git pull
git checkout -b ev2/mi-tema
```

## Commits

- En español, en presente y diciendo **qué cambia para el usuario o el sistema**: «Regla 3: rechaza el octavo ingreso del día», no «cambios varios».
- Un commit por cambio que se pueda entender solo. Si el mensaje necesita «y además», probablemente son dos.
- Nunca se suben `.env`, contraseñas, llaves `.pem`, la base `db.sqlite3` ni datos reales de vecinos u organizaciones. `.gitignore` ya los excluye; revise `git status` antes de cada commit.

## Pull requests

1. Antes de abrirlo:

   ```bash
   python manage.py test pruebas            # todas en verde
   python manage.py makemigrations --check  # sin migraciones pendientes
   ```

   Si tocó pantallas o JavaScript, también `python manage.py test pruebas_ui`.

2. Título corto y descripción con: qué cambia, por qué, cómo se probó y capturas si cambia la interfaz.
3. Al menos **una revisión** de otro integrante antes de unir a `main`.
4. Se une con *Squash and merge* cuando el historial de la rama tiene commits de prueba; si cada commit se entiende solo, con *Merge*.
5. Después de unir, se publica con `sudo bash /opt/sgr/app/deploy/actualizar.sh` en la instancia.

## Estilo de código

- Python: PEP 8 con líneas de hasta 120 caracteres. Nombres de dominio en español (`actividad`, `funcionario`, `periodo`), nombres técnicos de Django en inglés (`save`, `clean`, `get_queryset`).
- Toda regla del negocio se valida en el **servidor**. El JavaScript solo la anticipa.
- Nada de estilos ni scripts en línea en las plantillas: la Content-Security-Policy los bloquea. Use clases en `static/css/sgr.css` y atributos `data-*` que `static/js/sgr.js` interpreta.
- Mensajes al usuario en español claro, diciendo qué pasó y qué hacer.

## Pruebas

- Cada funcionalidad nueva trae su prueba en `pruebas/`. La primera línea del docstring lleva el identificador y una descripción: `"""RG-07 · Regla 3 (borde): el 8.º ingreso del día se rechaza"""`.
- Cubra el **borde** (el 7.º y el 8.º ingreso, el lunes y el martes), no solo el caso feliz.
- Después de agregar pruebas, regenere la matriz: `python scripts/generar_matriz_pruebas.py --ui`.

| Prefijo | Grupo |
|---|---|
| PA · PR | Acceso y recuperación |
| PC · PI · PL | Mantenedores, integridad, listados |
| PP · PD | Permisos y contexto de delegación |
| PT | Atenciones |
| RG · PM · PV | Reglas, cálculo y validación de la matriz |
| PE · PO · PF | Evidencias, organizaciones, rendimiento |
| SG · PS · PU · PX | Seguridad, mensajes, auditoría, sistema |
| UI | Navegador real |

## Base de datos

- Los cambios de modelo van con su migración en el mismo commit.
- Una migración ya publicada en AWS no se edita: se agrega una nueva.
- Si agrega una consulta que recorre muchas filas, revise su plan con `scripts/medir_consultas.py` y documente el índice en `docs/bd/modelo_de_datos.md`.

## Reparto de la EV2 (propuesta: ajústenlo si se repartieron distinto)

| Integrante | Área principal |
|---|---|
| Alexis Muñoz | Acceso, recuperación, roles, permisos, seguridad, validación y reglas del delegado |
| Matías Zepeda | Mantenedores, registro de actividades y reglas del funcionario |
| Carlos Araya | Atenciones, pruebas, base de datos, despliegue y organizaciones |
