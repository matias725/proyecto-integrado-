# Seguridad · matriz OWASP Top 10 (2021)

Cada riesgo del OWASP Top 10 con el control implementado en el SGR, dónde está en el código y la prueba automática que lo verifica. Las pruebas se ejecutan con `python manage.py test pruebas pruebas_ui`.

| # | Riesgo | Control en el SGR | Código | Pruebas |
|---|---|---|---|---|
| A01 | **Control de acceso roto** | Permiso por módulo y acción en cada vista (`permiso_requerido`). Alcance por delegación validado en el servidor en cada petición. **Acceso por objeto**: un funcionario solo abre, edita o adjunta a sus propias actividades; un delegado solo las de sus delegaciones. Nadie valida lo propio. Los campos responsable, delegación y día de ingreso los asigna el servidor. Los accesos denegados responden 403 y quedan en auditoría. Las evidencias no se publican en una carpeta abierta: se entregan tras validar el alcance. | `cuentas/permisos.py`, `cuentas/middleware.py`, `gestion/views.py` (`obtener_actividad`, `actividades_visibles`) | PP-xx, PD-xx, PV-02 a PV-07, PV-11, PV-15, PE-05, PE-06, RG-16 |
| A02 | **Fallas criptográficas** | Contraseñas con PBKDF2-SHA256 (Django, 1.000.000 iteraciones). Códigos de recuperación guardados como hash, nunca en claro. Con `SGR_HTTPS=1`: cookies `Secure`, redirección a HTTPS y HSTS. Secretos solo en `.env` del servidor. | `sgr/settings.py`, `cuentas/models.py` (`CodigoRecuperacion.codigo_hash`) | PR-xx |
| A03 | **Inyección** | Todas las consultas con el ORM de Django (parámetros enlazados, sin SQL concatenado). Plantillas con escape automático; los mensajes a SweetAlert2 viajan como JSON y se insertan con `textContent` o escapados. **Content-Security-Policy** sin `unsafe-inline` ni `unsafe-eval`: aunque se colara un `<script>`, el navegador no lo ejecutaría. | `core/seguridad.py`, `static/js/sgr.js` (`escapar`) | PS-05, SG-01, SG-03, UI-15, UI-16 |
| A04 | **Diseño inseguro** | Las reglas del negocio se validan en el servidor, no en el navegador: cupo diario (con bloqueo de fila para envíos simultáneos), cierre semanal, felicitaciones solo con respaldo y solo por el delegado, ausencias solo por el delegado, un único período abierto (también en la base), metas que no superan 100 %. Token de envío único contra el doble envío. | `gestion/reglas.py`, `gestion/forms.py`, `gestion/models.py` | RG-01 a RG-17, PV-08 a PV-16 |
| A05 | **Configuración insegura** | `DEBUG` apagado por defecto. Cabeceras: CSP estricta, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Permissions-Policy` (sin cámara, micrófono, ubicación ni pagos), `Cross-Origin-Opener-Policy`. `Cache-Control: no-store` en páginas con sesión (equipos compartidos en las delegaciones). Páginas de error propias sin trazas. | `sgr/settings.py`, `core/seguridad.py`, `templates/403.html`, `404.html`, `500.html` | SG-01, SG-02, PX-02 a PX-04 |
| A06 | **Componentes vulnerables** | Dependencias fijadas por rango en `requirements.txt` (Django 5.2 LTS, con soporte de seguridad hasta abril de 2028). Bibliotecas del navegador servidas localmente (`static/vendor`), sin CDN de terceros. Recomendación: `pip-audit` en cada entrega. | `requirements.txt` | — (revisión manual) |
| A07 | **Fallas de identificación y autenticación** | Acceso con usuario o correo y mensaje genérico (no revela si la cuenta existe). Bloqueo temporal de la **cuenta** tras 5 intentos fallidos. **Límite por IP** (20 envíos cada 15 min en acceso y recuperación) que frena a quien prueba muchas cuentas desde un mismo equipo; detrás de Nginx se usa la IP que agrega Nginx, no la que inventa el cliente. Código de recuperación de 6 dígitos que vence en 10 min, con máximo de intentos y de códigos por hora. Contraseñas con largo y complejidad mínimos. Sesión que se renueva al ingresar. | `cuentas/forms.py`, `cuentas/models.py`, `core/seguridad.py` | PA-xx, PR-xx, SG-04 a SG-09 |
| A08 | **Integridad de software y datos** | Archivos subidos validados por **contenido** (firma de bytes) además de la extensión, con tamaño máximo y nombre aleatorio (evita sobrescribir o recorrer rutas). CSRF en todos los formularios. La importación de la base JJVV no pisa organizaciones ya verificadas y tiene modo `--simular`. | `gestion/forms.py` (`validar_archivo`), `gestion/importacion.py` | PE-01 a PE-04, PO-03, PO-04, PX-06 |
| A09 | **Fallas de registro y monitoreo** | Auditoría de ingresos, salidas, intentos fallidos, bloqueos, creación, edición, eliminación, exportaciones, validaciones y **accesos denegados**, con usuario, delegación e IP. Nunca guarda contraseñas ni códigos. Consulta y exportación solo para perfiles autorizados. | `core/models.py` (`registrar`), `core/vistas_sistema.py` | PU-xx |
| A10 | **Falsificación de solicitudes del lado del servidor (SSRF)** | El sistema no descarga URLs indicadas por el usuario. El único servicio externo es el correo SMTP configurado por el administrador. | — | No aplica |

## Datos personales (Ley 19.628 y Ley 21.719)

- El repositorio es público: **ningún dato real** se sube. La base JJVV entregada (marcada como confidencial) se importa en el servidor con `sgr_importar_organizaciones`; en el repositorio solo hay datos ficticios (`@example.test`).
- Las evidencias pueden contener datos de vecinos: se guardan fuera de la carpeta pública y se descargan solo con permiso sobre la actividad.
- El teléfono y nombre del usuario se piden porque la regla 2 los exige para validar; no se piden otros datos.

## Pendientes conocidos

| Pendiente | Riesgo | Mitigación propuesta |
|---|---|---|
| HTTPS en la instancia de evaluación | Credenciales viajan sin cifrar en la IP pública | Asignar un dominio y emitir certificado con Let's Encrypt (`certbot --nginx`); la configuración ya está lista con `SGR_HTTPS=1` |
| Segundo factor para administradores | Robo de contraseña del superadministrador | TOTP para el rol Superadministrador |
| `pip-audit` automático | Una dependencia con vulnerabilidad publicada pasa inadvertida | Agregarlo a un flujo de GitHub Actions |
| Antivirus de archivos | Un PDF válido podría contener contenido malicioso | ClamAV en el servidor antes de aceptar la evidencia |
