/* =====================================================================
   SGR · shell.js
   Plantilla común de la aplicación.
   Cada página declara data-pagina y aquí se construye el menú lateral,
   la barra superior y el pie. Equivale al base.html de un motor de
   plantillas de servidor: una sola definición para las 14 pantallas.
   ===================================================================== */

const MENU = [
    {
        grupo: 'Operación',
        enlaces: [
            { id: 'tablero',         texto: 'Tablero',          icono: 'bi-speedometer2',       url: 'tablero.html' },
            { id: 'actividades',     texto: 'Actividades',      icono: 'bi-journal-text',       url: 'actividades.html' },
            { id: 'evidencias',      texto: 'Evidencias',       icono: 'bi-paperclip',          url: 'evidencias.html' },
            { id: 'validacion',      texto: 'Validación',       icono: 'bi-patch-check',        url: 'validacion.html' },
            { id: 'agenda',          texto: 'Agenda colectiva', icono: 'bi-calendar-week',      url: 'agenda.html' },
            { id: 'atencion-social', texto: 'Atención social',  icono: 'bi-people',             url: 'atencion-social.html' }
        ]
    },
    {
        grupo: 'Configuración',
        enlaces: [
            { id: 'delegaciones', texto: 'Delegaciones', icono: 'bi-geo-alt',    url: 'delegaciones.html' },
            { id: 'usuarios',     texto: 'Usuarios',     icono: 'bi-person-gear',url: 'usuarios.html' },
            { id: 'periodos',     texto: 'Períodos',     icono: 'bi-calendar3',  url: 'periodos.html' },
            { id: 'metas',        texto: 'Metas',        icono: 'bi-bullseye',   url: 'metas.html' }
        ]
    },
    {
        grupo: 'Información',
        enlaces: [
            { id: 'informes',  texto: 'Informes',  icono: 'bi-file-earmark-bar-graph', url: 'informes.html' },
            { id: 'auditoria', texto: 'Auditoría', icono: 'bi-clock-history',          url: 'auditoria.html' }
        ]
    }
];

function iniciales(nombre) {
    return nombre.split(' ').slice(0, 2).map(p => p[0]).join('').toUpperCase();
}

function construirLateral(paginaActiva) {
    const grupos = MENU.map(seccion => {
        const enlaces = seccion.enlaces.map(e => `
            <a href="${e.url}" class="${e.id === paginaActiva ? 'activo' : ''}"
               ${e.id === paginaActiva ? 'aria-current="page"' : ''}>
                <i class="bi ${e.icono}" aria-hidden="true"></i>${e.texto}
            </a>`).join('');
        return `<div class="menu-grupo">${seccion.grupo}</div>${enlaces}`;
    }).join('');

    return `
        <aside class="lateral">
            <div class="marca">
                <strong>SGR</strong>
                <span>Municipalidad de La Serena</span>
            </div>
            <nav class="menu" aria-label="Menú principal">${grupos}</nav>
        </aside>`;
}

function construirBarraSuperior(titulo) {
    const u = SGR.sesion();
    const periodos = SGR.datos.periodos.map(p =>
        `<option value="${p.id}" ${p.estado === 'ABIERTO' ? 'selected' : ''}>${p.nombre}${p.estado === 'CERRADO' ? ' (cerrado)' : ''}</option>`
    ).join('');

    return `
        <header class="barra-superior">
            <span class="ruta">Delegaciones municipales / ${titulo}</span>
            <span class="espacio"></span>
            <label class="selector-periodo">
                Período
                <select id="selectorPeriodo">${periodos}</select>
            </label>
            <div class="usuario-chip">
                <span class="avatar" aria-hidden="true">${iniciales(u.nombre)}</span>
                <span class="datos">
                    <b>${u.nombre}</b>
                    <span>${u.rol} · ${u.delegacion}</span>
                </span>
                <a href="index.html" class="boton sutil pequeno" title="Cerrar sesión">
                    <i class="bi bi-box-arrow-right" aria-hidden="true"></i>
                    <span class="solo-lectores">Cerrar sesión</span>
                </a>
            </div>
        </header>`;
}

/* Monta la plantilla alrededor del contenido ya escrito en la página */
document.addEventListener('DOMContentLoaded', () => {
    const cuerpo = document.querySelector('[data-pagina]');
    if (!cuerpo) return;

    /* data-menu permite que una pantalla de detalle mantenga iluminada
       la sección del menú a la que pertenece (por ejemplo, el formulario
       de registro conserva activo el enlace Actividades). */
    const pagina = cuerpo.dataset.menu || cuerpo.dataset.pagina;
    const titulo = cuerpo.dataset.titulo || '';
    const contenido = cuerpo.innerHTML;

    cuerpo.innerHTML = `
        <div class="app">
            ${construirLateral(pagina)}
            <div class="principal">
                ${construirBarraSuperior(titulo)}
                <main class="contenido">${contenido}</main>
            </div>
        </div>`;

    const selector = document.getElementById('selectorPeriodo');
    if (selector) {
        selector.addEventListener('change', e => {
            const p = SGR.datos.periodos.find(x => x.id === Number(e.target.value));
            if (p && p.estado === 'CERRADO') {
                SGR.notificar('Período cerrado: los datos se muestran solo para consulta');
            } else {
                SGR.notificar('Período actualizado');
            }
        });
    }

    document.dispatchEvent(new CustomEvent('shell:listo'));
});
