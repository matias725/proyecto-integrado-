# SGR · Prototipo funcional

Sistema de Gestión de Resultados de las Delegaciones Municipales de la Ilustre Municipalidad de La Serena.

Prototipo de interfaz correspondiente a la Primera Evaluación de la asignatura Proyecto Integrado (INACAP). Cubre navegación, distribución de pantallas, validación de campos y flujos de interacción. No incluye conexión a base de datos ni consumo de API, según lo indicado en la pauta.

---

## Cómo ejecutarlo

No requiere instalación, servidor ni compilación.

1. Clonar el repositorio o descargar la carpeta.
2. Abrir `index.html` con Chrome o Edge.
3. Entrar con cualquiera de las cuentas de demostración.

Si prefiere servirlo por HTTP, desde la carpeta del proyecto:

```bash
python -m http.server 8000
```

y abrir `http://localhost:8000`.

### Cuentas de demostración

Contraseña común: `demo1234`

| Usuario | Rol | Delegación |
|---|---|---|
| `bcastillo` | Funcionario | Rural |
| `arojas` | Verificador y delegado | Rural |
| `emunoz` | Coordinador | Centro |
| `faguirre` | Administrador | Las Compañías |

Todos los datos del prototipo son ficticios. No se utiliza información real de funcionarios ni de ciudadanos.

---

## Tecnologías

| Herramienta | Uso | Por qué |
|---|---|---|
| HTML5 y CSS3 | Estructura y estilos | Sin dependencia de compilación; el prototipo se abre directo en el navegador |
| JavaScript (ES6) | Interacción, validación y datos en memoria | Permite demostrar los flujos sin backend |
| Bootstrap Icons 1.11 | Iconografía | Librería externa liviana, cargada por CDN |
| IBM Plex Sans y Mono | Tipografía | Familia abierta; la variante monoespaciada se reserva para códigos de evidencia |

No se usó un framework de componentes: para catorce pantallas estáticas habría añadido peso de compilación sin aportar a lo que esta entrega evalúa.

---

## Estructura del proyecto

```
mockup-sgr/
├── index.html              Acceso al sistema (CU-01)
├── tablero.html            Tablero de indicadores y semáforo (CU-13)
├── actividades.html        Listado y búsqueda de actividades (CU-07, CU-17)
├── actividad-nueva.html    Registro de actividad (CU-07, CU-18, CU-19)
├── evidencias.html         Carga de evidencias (CU-09)
├── validacion.html         Bandeja del verificador (CU-10)
├── agenda.html             Agenda colectiva (CU-11, CU-12)
├── atencion-social.html    Casos y gestiones sociales (CU-08)
├── delegaciones.html       Administración de delegaciones (CU-02)
├── usuarios.html           Usuarios y roles (CU-03)
├── periodos.html           Períodos de medición (CU-05)
├── metas.html              Metas y ponderaciones (CU-06)
├── informes.html           Informes y exportación (CU-14)
├── auditoria.html          Historial de cambios (CU-16)
└── assets/
    ├── css/sgr.css         Sistema de diseño y componentes
    └── js/
        ├── datos.js        Datos ficticios y cálculos del sistema
        ├── validacion.js   Validaciones de formulario (CU-18)
        └── shell.js        Plantilla común de menú y cabecera
```

### Sobre la plantilla común

`shell.js` construye el menú lateral y la barra superior, y los inyecta alrededor del contenido de cada página. El menú está definido una sola vez, de modo que agregar una pantalla no obliga a editar catorce archivos.

Cada página declara su identidad en el `body`:

```html
<body data-pagina="tablero" data-titulo="Tablero">
```

Si en una etapa posterior el proyecto migra a un motor de plantillas de servidor, este shell equivale al `base.html` del que heredarían las vistas.

---

## Trazabilidad con los demás artefactos

| Pantalla | Caso de uso | Requerimientos | Reglas de negocio |
|---|---|---|---|
| Acceso | CU-01 | RF-002, RNF-004 | — |
| Tablero | CU-13 | RF-008, RF-026 a RF-029 | RN-004, RN-007, RN-008 |
| Actividades | CU-07, CU-17 | RF-009, RF-032 | RN-003 |
| Registrar actividad | CU-07, CU-18, CU-19 | RF-009, RF-010, RF-011 | RN-010 |
| Evidencias | CU-09 | RF-012, RNF-017 | RN-010 |
| Validación | CU-10, CU-20 | RF-013, RF-014 | RN-009 |
| Agenda colectiva | CU-11, CU-12 | RF-016 a RF-019 | — |
| Atención social | CU-08 | RF-015 | RN-012 |
| Delegaciones | CU-02 | RF-001 | — |
| Usuarios | CU-03 | RF-002 | — |
| Períodos | CU-05 | RF-005, RF-038 | RN-006, RN-008, RN-013 |
| Metas | CU-06 | RF-003, RF-006, RF-007 | RN-001, RN-002 |
| Informes | CU-14, CU-17 | RF-032, RF-033 | — |
| Auditoría | CU-16 | RF-036, RNF-008 | — |

Los nombres de módulos, entidades y actores coinciden con los del diagrama de clases, el modelo entidad-relación y el script SQL.

---

## Validaciones implementadas

Concentradas en `assets/js/validacion.js`, que corresponde al caso de uso CU-18.

- **Obligatoriedad**: cada campo requerido informa su falta al perder el foco, no mientras se escribe.
- **RUT chileno**: verificación del dígito verificador por módulo 11.
- **Correo y teléfono**: formato institucional y formato móvil chileno.
- **Fechas**: no se aceptan fechas futuras ni fuera del período abierto (RN-013).
- **Archivos de evidencia**: solo JPG, PNG o PDF de hasta 2 MB (RNF-017).
- **Suma de ponderadores**: en `metas.html` el botón de guardar permanece deshabilitado mientras la suma no cierre en 100 % (RN-001).
- **Meta mayor que cero**: se rechaza cualquier meta igual o menor a cero (RN-002).
- **Transiciones de estado**: en la agenda, el desplegable solo ofrece los estados alcanzables desde el actual (RF-018).
- **Máximo de tres gestiones**: en atención social se avisa al llegar al límite y se bloquea la cuarta (RN-012).
- **Duplicados**: se rechaza crear delegaciones, usuarios o ítems repetidos.

---

## Decisiones de diseño

**Paleta.** Granate institucional de la Municipalidad de La Serena sobre neutros cálidos. Los tres colores del semáforo se reservan exclusivamente para el estado de cumplimiento, de modo que el color siempre signifique lo mismo.

**El semáforo es el elemento central.** Cada barra de avance lleva una marca vertical con la meta esperada al día. Sin esa referencia, un 30 % de avance no dice nada; con ella se ve de inmediato si el funcionario va adelantado o atrasado respecto del día del período. Es la información que la Matriz SGR original entrega y la que justifica el sistema.

**Estados por texto y color.** Las etiquetas de estado combinan color con palabra, para que la información siga siendo legible sin distinguir colores.

**Accesibilidad.** Foco visible en todos los controles, etiquetas asociadas a sus campos, textos alternativos en los iconos decorativos, navegación por teclado y respeto por la preferencia de movimiento reducido del sistema operativo.

**Adaptación a pantallas menores.** El menú lateral pasa a barra horizontal bajo los 760 px y las rejillas se apilan; las tablas conservan desplazamiento horizontal.

---

## Limitaciones conocidas

Declaradas de forma explícita, conforme a la lista de comprobación de la guía del proyecto.

- Los datos viven en memoria: al recargar la página vuelven a su estado inicial.
- La sesión se simula y no existe control de acceso real en el servidor.
- El cierre y la reapertura de períodos muestran el mensaje correspondiente pero no alteran los datos.
- La exportación de informes confirma la acción sin generar el archivo.
- Los indicadores del tablero se calculan con las fórmulas reales (RN-004 a RN-008) sobre datos fijos.

---

## Equipo

| Integrante | Responsabilidad |
|---|---|
| _Completar_ | _Completar_ |

Asignatura: Proyecto Integrado · Docente: Jorge Cortés · INACAP, 2026
