# SGR · Templates en Django

Sistema de Gestión de Resultados de las Delegaciones Municipales de la Ilustre Municipalidad de La Serena.
Proyecto Integrado INACAP 2026 · Alexis Muñoz, Matías Zepeda y Carlos Araya.

Esta etapa migra las 14 pantallas del prototipo HTML a **templates de Django**: una plantilla base de la que heredan todas las pantallas, formularios validados en el servidor y control de acceso por rol. Todavía no hay base de datos: los datos ficticios viven en memoria (`core/datos.py`).

---

## Cómo ejecutarlo

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS o Linux

pip install -r requirements.txt
python manage.py runserver
```

Abrir `http://127.0.0.1:8000`. Los datos del SGR siguen en memoria; la base SQLite (`db.sqlite3`) solo la usa el admin de Django.

Para el admin (`http://127.0.0.1:8000/admin/`), la primera vez:

```bash
python manage.py migrate
python manage.py createsuperuser
```

### Cuentas de demostración

Contraseña para todas: `demo1234`

| Usuario | Rol | Qué ve en el menú |
|---|---|---|
| `bcastillo` | Funcionario (Rural) | Tablero, actividades, evidencias, agenda y atención social |
| `arojas` | Delegada y verificadora (Rural) | Además, validación e informes |
| `emunoz` | Coordinadora | Validación, agenda, períodos, metas e informes de todas las delegaciones |
| `faguirre` | Administrador | Todo el sistema, incluida la auditoría |

### Pruebas automáticas

```bash
python manage.py test
```

41 pruebas: fórmulas del semáforo, validación de RUT, permisos por rol y cada regla de negocio de los formularios.

---

## Cómo están organizados los templates

```
templates/
├── base.html                  Esqueleto HTML común: estilos, íconos y avisos
├── layouts/
│   └── app.html               Menú lateral + barra superior; hereda de base.html
├── parciales/                 Piezas que se incluyen en varias pantallas
│   ├── _menu.html             Menú filtrado según el rol
│   ├── _barra_superior.html   Selector de período y usuario conectado
│   ├── _campo.html            Un campo de formulario con etiqueta, ayuda y errores
│   ├── _errores_formulario.html
│   ├── _mensajes.html         Avisos de éxito o error
│   └── _medidor.html          Barra del semáforo con la marca de lo esperado
├── acceso/login.html          CU-01
├── tablero/tablero.html       CU-13
├── actividades/               CU-07 · lista, nueva y registrada
├── evidencias/lista.html      CU-09
├── validacion/bandeja.html    CU-10
├── agenda/                    CU-11 y CU-12 · lista e historial de estados
├── atencion_social/casos.html CU-08
├── configuracion/             CU-02, CU-03, CU-05 y CU-06
├── informes/informes.html     CU-14
├── auditoria/auditoria.html   CU-16
├── 403.html                   Acceso denegado
└── 404.html                   Página no encontrada
```

Cada pantalla solo completa sus bloques. Por ejemplo, la de delegaciones:

```django
{% extends "layouts/app.html" %}

{% block titulo_pagina %}Delegaciones municipales{% endblock %}
{% block accion %}<button ...>Nueva delegación</button>{% endblock %}
{% block contenido %}
    ... tabla y formulario ...
{% endblock %}
```

El menú y la barra superior están escritos una sola vez, en `layouts/app.html`. Cambiarlos ahí los cambia en todas las pantallas.

### Etiquetas propias (`core/templatetags/sgr_tags.py`)

| Etiqueta | Uso | Resultado |
|---|---|---|
| `{% estado a.estado %}` | Estado de un registro | Insignia de color con texto |
| `{{ valor\|cifra }}` | Números | `1.234,5` con coma decimal |
| `{% medidor fila esperado %}` | Tablero | Barra de avance del semáforo |
| `{{ usuario_actual\|puede:'informes' }}` | Mostrar un botón solo a quien tiene permiso | `True` o `False` |

---

## Estructura del código

| Archivo | Responsabilidad |
|---|---|
| `core/views.py` | Una vista por caso de uso |
| `core/forms.py` | Formularios y validaciones del servidor (CU-18) |
| `core/calculos.py` | Fórmulas RN-003 a RN-008; equivale a `CalculadoraIndicadores` del diagrama de clases |
| `core/permisos.py` | Roles, menú y decorador `@requiere_permiso` (RNF-005) |
| `core/validadores.py` | RUT con dígito verificador y teléfono chileno |
| `core/datos.py` | Datos ficticios en memoria; cada lista equivale a una tabla de `sgr_schema.sql` |
| `core/tests.py` | Pruebas automáticas |

---

## Reglas de negocio que el servidor hace cumplir

| Regla | Dónde se ve |
|---|---|
| RN-001 · los ponderadores suman 100 % | Metas: no se guarda si la suma no cierra |
| RN-002 · la meta es mayor que cero | Metas |
| RN-007 y RN-008 · meta esperada al día y semáforo | Tablero |
| RN-009 · solo lo aprobado suma | Validación: aprobar sube el avance del tablero en 1 |
| RN-010 · código único e inmutable | Registrar actividad |
| RN-012 · máximo tres gestiones sociales | Atención social |
| RN-013 · un período cerrado no se modifica | Metas y períodos; solo el administrador reabre |
| RF-018 · transiciones de estado controladas | Agenda: solo se ofrecen los estados permitidos |
| RF-036 · auditoría | Cada alta, validación, cambio de estado o de parámetro, exportación y acceso denegado |
| RNF-005 · permisos por rol | Una URL escrita a mano sin permiso responde 403 y queda auditada |
| CA-07 · ámbito por delegación | Funcionario y delegado solo ven su delegación |
| RNF-017 · evidencias | Se revisa el contenido real del archivo, no solo la extensión |

---

## Decisiones técnicas

**Sin base de datos en esta etapa.** `DATABASES` está vacío a propósito. La sesión se guarda en una cookie firmada y las contraseñas de demostración se verifican contra un hash, nunca en texto plano. En la etapa de desarrollo, `core/datos.py` se reemplaza por modelos de Django sobre MySQL (`sgr_schema.sql`) y las vistas cambian poco, porque ya reciben y devuelven la misma estructura.

**Fecha de referencia fija.** El "hoy" del sistema es el 12-09-2026 (`SGR_FECHA_REFERENCIA` en `settings.py`), para que los cálculos coincidan con el script SQL: 74 de 91 días transcurridos, 81,32 % esperado. Para usar la fecha real, cambiar esa línea por `date.today()`.

**Sin dependencias de internet.** Las fuentes IBM Plex y los íconos Bootstrap Icons están dentro de `static/vendor/`, con sus licencias. El sistema se ve igual en un laboratorio sin conexión.

**El JavaScript es opcional.** `static/js/sgr.js` solo abre modales y suma ponderadores en vivo. Toda regla se valida en el servidor: si el navegador bloquea el JavaScript, los formularios siguen funcionando y mostrando sus errores.

---

## Limitaciones conocidas

- Los cambios hechos en pantalla se pierden al reiniciar el servidor.
- Los archivos de evidencia se validan pero no se guardan.
- Los porcentajes de cumplimiento del resumen por delegación son valores fijos de demostración.
- No incluye recuperación de contraseña: la autenticación real se implementará con el sistema de usuarios de Django junto con la base de datos.
