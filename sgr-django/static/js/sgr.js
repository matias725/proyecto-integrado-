/* =====================================================================
   SGR · sgr.js
   Comodidades de interfaz. Toda regla de negocio se valida en el servidor
   (forms.py): si este archivo no carga, el sistema sigue funcionando.
   ===================================================================== */

document.addEventListener('DOMContentLoaded', () => {

    /* ---------- Modales ---------- */
    const abrir = (modal) => {
        modal.classList.add('abierto');
        modal.querySelector('input:not([type=hidden]), select, textarea')?.focus();
    };
    const cerrar = (modal) => modal.classList.remove('abierto');

    document.querySelectorAll('[data-abrir]').forEach(boton => {
        boton.addEventListener('click', () => {
            const modal = document.getElementById(boton.dataset.abrir);
            if (!modal) return;
            // Un botón puede traer valores para el formulario (etiqueta {% rellenar %})
            if (boton.dataset.rellenar) {
                Object.entries(JSON.parse(boton.dataset.rellenar)).forEach(([id, valor]) => {
                    const destino = document.getElementById(id);
                    if (!destino) return;
                    if ('value' in destino && destino.tagName !== 'BUTTON') destino.value = valor;
                    else destino.textContent = valor;
                });
            }
            abrir(modal);
        });
    });

    document.querySelectorAll('[data-cerrar]').forEach(boton =>
        boton.addEventListener('click', () => cerrar(boton.closest('.telon'))));

    document.querySelectorAll('.telon').forEach(telon =>
        telon.addEventListener('click', e => { if (e.target === telon) cerrar(telon); }));

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') document.querySelectorAll('.telon.abierto').forEach(cerrar);
    });

    // Si el servidor devolvió el modal abierto por errores, llevar el foco al primero
    document.querySelector('.telon.abierto .campo.invalido input, .telon.abierto .campo.invalido select, .telon.abierto .campo.invalido textarea')?.focus();

    /* ---------- Avisos ---------- */
    document.querySelectorAll('.notificacion').forEach(aviso => {
        aviso.querySelector('.cerrar-notificacion')?.addEventListener('click', () => aviso.remove());
        if (!aviso.classList.contains('error')) setTimeout(() => aviso.remove(), 6000);
    });

    /* ---------- Formularios ---------- */
    document.querySelectorAll('[data-enviar-al-cambiar]').forEach(select =>
        select.addEventListener('change', () => select.form.submit()));

    document.querySelectorAll('[data-ir-a]').forEach(select =>
        select.addEventListener('change', () => {
            window.location.href = select.dataset.irA + encodeURIComponent(select.value);
        }));

    document.querySelectorAll('form[data-confirmar]').forEach(form =>
        form.addEventListener('submit', e => { if (!confirm(form.dataset.confirmar)) e.preventDefault(); }));

    /* ---------- Acceso: cuentas de demostración ---------- */
    document.querySelectorAll('[data-cuenta]').forEach(boton =>
        boton.addEventListener('click', () => {
            document.getElementById('id_usuario').value = boton.dataset.cuenta;
            const clave = document.getElementById('id_clave');
            clave.value = 'demo1234';
            clave.focus();
        }));

    /* ---------- Metas: formset dinámico y suma en vivo ---------- */
    const filas = document.getElementById('filasMetas');
    const totalizador = document.getElementById('totalizador');
    if (filas && totalizador) {
        const totalForms = document.getElementById('id_metas-TOTAL_FORMS');
        const plantilla = document.getElementById('plantillaMeta');
        const guardar = document.getElementById('guardarMetas');
        const coma = n => n.toLocaleString('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

        const totalizar = () => {
            let suma = 0;
            filas.querySelectorAll('.fila-meta').forEach(fila => {
                const quitar = fila.querySelector('input[type=checkbox]');
                fila.classList.toggle('fila-eliminada', !!quitar?.checked);
                if (quitar?.checked) return;
                suma += parseFloat(fila.querySelector('input[name$="-ponderador"]')?.value) || 0;
            });
            const cuadra = Math.abs(suma - 100) < 0.001;
            totalizador.innerHTML = cuadra
                ? '<span class="estado ok"><i class="bi bi-check-circle"></i> Suma de ponderadores: 100 %</span>'
                : `<span class="estado error"><i class="bi bi-exclamation-circle"></i> Suma: ${coma(suma)} % · ${suma < 100 ? 'faltan' : 'sobran'} ${coma(Math.abs(100 - suma))} puntos</span>`;
            if (guardar) guardar.title = cuadra ? '' : 'La suma debe cerrar en 100 % (RN-001)';
        };

        filas.addEventListener('input', totalizar);
        filas.addEventListener('change', totalizar);

        document.getElementById('agregarMeta')?.addEventListener('click', () => {
            const indice = Number(totalForms.value);
            filas.insertAdjacentHTML('beforeend', plantilla.innerHTML.replaceAll('__prefix__', indice));
            totalForms.value = indice + 1;
            filas.lastElementChild.querySelector('select')?.focus();
            totalizar();
        });

        totalizar();
    }
});
