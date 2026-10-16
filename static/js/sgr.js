/* =====================================================================
   SGR · sgr.js
   Comodidades de interfaz y diálogos SweetAlert2. Toda regla de negocio
   se valida también en el servidor: si este archivo no carga, el sistema
   sigue funcionando con formularios HTML normales.
   ===================================================================== */
(function () {
    'use strict';

    const hayAlerta = typeof window.Swal !== 'undefined';
    const COLOR = '#920000';

    /* ---------- Fábrica de diálogos con estilo institucional ---------- */
    const dialogo = hayAlerta ? Swal.mixin({
        confirmButtonColor: COLOR,
        cancelButtonColor: '#5f6368',
        reverseButtons: true,
        focusCancel: false,
        customClass: { popup: 'sgr-alerta' },
        buttonsStyling: true,
    }) : null;

    const aviso = hayAlerta ? Swal.mixin({
        toast: true, position: 'top-end', showConfirmButton: false,
        timer: 3500, timerProgressBar: true,
        customClass: { popup: 'sgr-aviso' },
    }) : null;

    /** Confirmación genérica. Devuelve una promesa booleana. */
    function confirmar({ titulo, texto, boton = 'Sí, continuar', icono = 'warning', peligro = false }) {
        if (!dialogo) return Promise.resolve(window.confirm(titulo + (texto ? '\n\n' + texto : '')));
        return dialogo.fire({
            title: titulo, text: texto || '', icon: icono,
            showCancelButton: true, confirmButtonText: boton, cancelButtonText: 'Cancelar',
            confirmButtonColor: peligro ? '#B3261E' : COLOR,
        }).then(r => r.isConfirmed);
    }
    window.SGR = { confirmar };

    document.addEventListener('DOMContentLoaded', () => {

        /* ---------- 1. Mensajes del servidor → SweetAlert2 ---------- */
        const datos = document.getElementById('mensajes-sgr');
        if (datos) {
            let lista = [];
            try { lista = JSON.parse(datos.textContent); } catch (e) { lista = []; }
            const iconos = { success: 'success', error: 'error', warning: 'warning', info: 'info', debug: 'info' };
            const titulos = { success: 'Operación realizada', error: 'No se pudo completar', warning: 'Atención', info: 'Información' };
            if (hayAlerta && lista.length) {
                // Los errores y advertencias se muestran como diálogo (requieren lectura);
                // los éxitos simples como aviso breve, salvo que indiquen un folio.
                const graves = lista.filter(m => m.nivel === 'error' || m.nivel === 'warning');
                const conFolio = lista.find(m => m.nivel === 'success' && /folio/i.test(m.texto));
                if (graves.length) {
                    const nivel = graves.some(m => m.nivel === 'error') ? 'error' : 'warning';
                    dialogo.fire({ icon: iconos[nivel], title: titulos[nivel],
                        html: graves.map(m => escapar(m.texto)).join('<br>'), confirmButtonText: 'Entendido' });
                } else if (conFolio) {
                    const folio = (conFolio.texto.match(/AT-\d{4}-\d+/) || [''])[0];
                    dialogo.fire({ icon: 'success', title: 'Atención registrada',
                        html: folio ? `Identificador asignado<br><b class="folio-alerta">${escapar(folio)}</b>` : escapar(conFolio.texto),
                        confirmButtonText: 'Aceptar' });
                } else {
                    lista.forEach((m, i) => setTimeout(() => aviso.fire({ icon: iconos[m.nivel] || 'info', title: m.texto }), i * 400));
                }
            } else if (lista.length) {
                // Respaldo accesible si SweetAlert2 no cargó
                const zona = document.createElement('div');
                zona.className = 'aviso';
                zona.setAttribute('role', 'status');
                zona.textContent = lista.map(m => m.texto).join(' ');
                (document.querySelector('main') || document.body).prepend(zona);
            }
        }

        /* ---------- 2. Confirmaciones de acciones (eliminar, desactivar…) ---------- */
        document.querySelectorAll('form[data-confirmar]').forEach(form => {
            form.addEventListener('submit', e => {
                if (form.dataset.confirmado === '1') return;
                e.preventDefault();
                const peligro = /eliminar/i.test(form.dataset.confirmar);
                confirmar({
                    titulo: form.dataset.confirmar,
                    texto: form.dataset.confirmarDetalle,
                    boton: form.dataset.confirmarBoton || (peligro ? 'Sí, eliminar' : 'Sí, continuar'),
                    peligro,
                }).then(ok => {
                    if (ok) {
                        form.dataset.confirmado = '1';
                        bloquearEnvio(form);
                        form.submit();
                    } else if (aviso) {
                        aviso.fire({ icon: 'info', title: 'Acción cancelada. No se realizaron cambios.' });
                    }
                });
            });
        });

        /* ---------- 3. Validación en el navegador ---------- */
        const mensajeCampo = (campo) => {
            const v = campo.validity;
            if (v.valueMissing) return 'Este campo es obligatorio.';
            if (v.typeMismatch && campo.type === 'email') return 'Ingrese un correo válido.';
            if (v.tooShort) return `Debe tener al menos ${campo.minLength} caracteres.`;
            if (v.tooLong) return `No puede superar ${campo.maxLength} caracteres.`;
            if (v.patternMismatch) return campo.title || 'El formato no es válido.';
            if (v.rangeUnderflow || v.rangeOverflow) return 'El valor está fuera del rango permitido.';
            return campo.validationMessage;
        };
        const marcar = (campo) => {
            const contenedor = campo.closest('.campo');
            if (!contenedor) return true;
            const valido = campo.checkValidity();
            const error = contenedor.querySelector('[data-error-cliente]');
            contenedor.classList.toggle('invalido', !valido);
            campo.setAttribute('aria-invalid', valido ? 'false' : 'true');
            if (error) {
                error.hidden = valido;
                error.innerHTML = valido ? '' : '<i class="bi bi-exclamation-circle" aria-hidden="true"></i>' + escapar(mensajeCampo(campo));
            }
            return valido;
        };
        document.querySelectorAll('form[data-validar]').forEach(form => {
            const campos = () => form.querySelectorAll('input:not([type=hidden]):not([type=checkbox]), select, textarea');
            campos().forEach(c => {
                c.addEventListener('blur', () => { if (c.value || c.dataset.tocado) marcar(c); c.dataset.tocado = '1'; });
                c.addEventListener('input', () => { if (c.closest('.campo')?.classList.contains('invalido')) marcar(c); });
            });
            form.addEventListener('submit', e => {
                let primero = null;
                campos().forEach(c => { if (!marcar(c) && !primero) primero = c; });
                if (primero) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    primero.focus();
                    if (dialogo) dialogo.fire({ icon: 'warning', title: 'Revise el formulario',
                        text: 'Hay campos obligatorios vacíos o con formato no válido.', confirmButtonText: 'Revisar' });
                }
            });
        });

        /* ---------- 4. Prevenir doble envío ---------- */
        function bloquearEnvio(form) {
            form.dataset.enviando = '1';
            form.querySelectorAll('button[type=submit], button:not([type])').forEach(b => {
                b.disabled = true;
                if (b.dataset.textoEnvio) {
                    b.dataset.textoOriginal = b.innerHTML;
                    b.innerHTML = '<span class="girando" aria-hidden="true"></span>' + escapar(b.dataset.textoEnvio);
                }
            });
            form.setAttribute('aria-busy', 'true');
        }
        document.querySelectorAll('form[data-un-envio]').forEach(form => {
            form.addEventListener('submit', e => {
                if (e.defaultPrevented) return;
                if (form.dataset.enviando === '1') { e.preventDefault(); return; }
                limpio = true; // no advertir cambios sin guardar al enviar
                // Se bloquea después de que el navegador tome los valores del formulario
                setTimeout(() => bloquearEnvio(form), 0);
            });
        });
        // Al volver con el botón "atrás" el navegador puede restaurar la página bloqueada
        window.addEventListener('pageshow', ev => {
            if (!ev.persisted) return;
            document.querySelectorAll('form[data-enviando="1"]').forEach(form => {
                delete form.dataset.enviando;
                form.removeAttribute('aria-busy');
                form.querySelectorAll('button').forEach(b => {
                    b.disabled = false;
                    if (b.dataset.textoOriginal) b.innerHTML = b.dataset.textoOriginal;
                });
            });
        });

        /* ---------- 5. Cambios sin guardar ---------- */
        let sucio = false;
        let limpio = false;
        document.querySelectorAll('form[data-vigilar-cambios]').forEach(form => {
            const marcarSucio = () => { sucio = true; };
            form.addEventListener('input', marcarSucio);
            form.addEventListener('change', marcarSucio);
        });
        window.addEventListener('beforeunload', e => {
            if (sucio && !limpio) { e.preventDefault(); e.returnValue = ''; }
        });
        document.querySelectorAll('[data-cancelar]').forEach(enlace => {
            enlace.addEventListener('click', e => {
                if (!sucio) return;
                e.preventDefault();
                confirmar({ titulo: '¿Descartar los cambios?', texto: 'Los datos ingresados no se guardarán.',
                    boton: 'Sí, descartar', icono: 'question' })
                    .then(ok => { if (ok) { limpio = true; window.location.href = enlace.href; } });
            });
        });

        /* ---------- 6. Cambio de delegación activa ---------- */
        const selector = document.querySelector('[data-cambio-contexto]');
        if (selector) {
            const inicial = selector.value;
            selector.addEventListener('change', () => {
                const texto = selector.options[selector.selectedIndex].text;
                const detalle = sucio
                    ? 'Tiene cambios sin guardar en esta pantalla. Si continúa, se perderán. Los listados, filtros y exportaciones pasarán a la nueva delegación.'
                    : 'Los listados, filtros, exportaciones y formularios pasarán a mostrar la información de esta delegación.';
                confirmar({ titulo: `¿Cambiar a ${texto}?`, texto: detalle, boton: 'Sí, cambiar', icono: sucio ? 'warning' : 'question' })
                    .then(ok => {
                        if (ok) { limpio = true; selector.form.submit(); }
                        else selector.value = inicial;
                    });
            });
        }

        /* ---------- 7. Listados: búsqueda, filtros y exportación ---------- */
        document.querySelectorAll('[data-enviar-al-cambiar]').forEach(sel =>
            sel.addEventListener('change', () => sel.form.requestSubmit ? sel.form.requestSubmit() : sel.form.submit()));

        document.querySelectorAll('[data-busqueda-viva]').forEach(campo => {
            let espera;
            const valorInicial = campo.value;
            campo.addEventListener('input', () => {
                clearTimeout(espera);
                espera = setTimeout(() => {
                    const v = campo.value.trim();
                    if (v === valorInicial.trim()) return;
                    if (v.length === 0 || v.length >= 2) campo.form.requestSubmit ? campo.form.requestSubmit() : campo.form.submit();
                }, 550);
            });
            // Mantener el cursor al final tras recargar
            if (campo.hasAttribute('autofocus')) { const n = campo.value.length; campo.setSelectionRange(n, n); }
        });
        // Estado de carga visible al filtrar
        document.querySelectorAll('form.herramientas').forEach(form =>
            form.addEventListener('submit', () => {
                document.querySelector('.panel .tabla')?.closest('.panel')?.classList.add('cargando');
                form.querySelector('[data-texto-envio]')?.setAttribute('disabled', '');
            }));

        document.querySelectorAll('[data-exportar]').forEach(enlace =>
            enlace.addEventListener('click', e => {
                if (enlace.getAttribute('aria-disabled') === 'true') {
                    e.preventDefault();
                    if (dialogo) dialogo.fire({ icon: 'info', title: 'Nada que exportar', text: 'No hay registros que coincidan con los filtros actuales.' });
                    return;
                }
                if (aviso) aviso.fire({ icon: 'info', title: 'Generando Excel con todos los resultados filtrados…' });
            }));

        /* ---------- 8. Contraseñas ---------- */
        document.querySelectorAll('[data-mostrar-clave]').forEach(boton => {
            boton.addEventListener('click', () => {
                const campo = document.getElementById(boton.dataset.mostrarClave);
                if (!campo) return;
                const mostrar = campo.type === 'password';
                campo.type = mostrar ? 'text' : 'password';
                boton.textContent = mostrar ? 'Ocultar' : 'Mostrar';
                boton.setAttribute('aria-pressed', String(mostrar));
                boton.setAttribute('aria-label', mostrar ? 'Ocultar contraseña' : 'Mostrar contraseña');
            });
        });

        document.querySelectorAll('[data-requisitos-de]').forEach(lista => {
            const clave = document.getElementById(lista.dataset.requisitosDe);
            const reglas = [...lista.querySelectorAll('li[data-patron]')];
            const coincide = lista.querySelector('li[data-coincide]');
            const confirmacion = coincide ? document.getElementById(coincide.dataset.coincide) : null;
            const pintar = (li, ok) => {
                li.classList.toggle('cumple', ok);
                const i = li.querySelector('i');
                if (i) i.className = 'bi ' + (ok ? 'bi-check-circle-fill' : 'bi-circle');
            };
            const evaluar = () => {
                const v = clave?.value || '';
                reglas.forEach(li => pintar(li, new RegExp(li.dataset.patron).test(v)));
                if (coincide && confirmacion) pintar(coincide, v.length > 0 && v === confirmacion.value);
            };
            clave?.addEventListener('input', evaluar);
            confirmacion?.addEventListener('input', evaluar);
            evaluar();
        });

        /* ---------- 9. Código de verificación en seis casillas ---------- */
        document.querySelectorAll('[data-casillas-codigo]').forEach(grupo => {
            const oculto = document.getElementById(grupo.dataset.casillasCodigo);
            const casillas = [...grupo.querySelectorAll('input')];
            const sincronizar = () => { if (oculto) oculto.value = casillas.map(c => c.value).join(''); };
            const repartir = (texto, desde) => {
                const digitos = texto.replace(/\D/g, '').slice(0, casillas.length - desde).split('');
                digitos.forEach((d, i) => { casillas[desde + i].value = d; });
                const siguiente = Math.min(desde + digitos.length, casillas.length - 1);
                casillas[siguiente].focus();
                sincronizar();
            };
            if (oculto && oculto.value) repartir(oculto.value, 0);
            casillas.forEach((c, i) => {
                c.addEventListener('input', () => {
                    if (c.value.length > 1) { repartir(c.value, i); return; }
                    c.value = c.value.replace(/\D/g, '');
                    if (c.value && i < casillas.length - 1) casillas[i + 1].focus();
                    sincronizar();
                });
                c.addEventListener('keydown', e => {
                    if (e.key === 'Backspace' && !c.value && i > 0) { casillas[i - 1].focus(); casillas[i - 1].value = ''; sincronizar(); e.preventDefault(); }
                    if (e.key === 'ArrowLeft' && i > 0) { casillas[i - 1].focus(); e.preventDefault(); }
                    if (e.key === 'ArrowRight' && i < casillas.length - 1) { casillas[i + 1].focus(); e.preventDefault(); }
                });
                c.addEventListener('paste', e => {
                    e.preventDefault();
                    repartir((e.clipboardData || window.clipboardData).getData('text'), i);
                });
                c.addEventListener('focus', () => c.select());
            });
            grupo.closest('form')?.addEventListener('submit', e => {
                sincronizar();
                if (!/^\d{6}$/.test(oculto.value)) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    casillas.find(c => !c.value)?.focus();
                    if (dialogo) dialogo.fire({ icon: 'warning', title: 'Código incompleto', text: 'Ingrese los 6 dígitos que recibió por correo.' });
                }
            }, true);
        });

        document.querySelectorAll('[data-cuenta-regresiva]').forEach(boton => {
            let restante = parseInt(boton.dataset.cuentaRegresiva, 10) || 0;
            const texto = boton.parentElement.querySelector('[data-texto-espera]');
            const tic = () => {
                if (restante <= 0) {
                    boton.disabled = false;
                    if (texto) texto.textContent = 'Ya puede solicitar un nuevo código.';
                    return;
                }
                boton.disabled = true;
                if (texto) texto.textContent = `Podrá reenviar en ${restante} s.`;
                restante -= 1;
                setTimeout(tic, 1000);
            };
            tic();
        });

        /* ---------- 10. Acceso: cuentas de demostración ---------- */
        document.querySelectorAll('[data-cuenta]').forEach(boton =>
            boton.addEventListener('click', () => {
                const id = document.getElementById('id_identificador');
                const clave = document.getElementById('id_clave');
                if (!id || !clave) return;
                id.value = boton.dataset.cuenta;
                clave.value = 'Serena#2026';
                clave.focus();
            }));

        /* ---------- 11. Ingreso de atención ---------- */
        const formAtencion = document.getElementById('formAtencion');
        if (formAtencion) {
            const tipo = document.getElementById('id_tipo');
            const sub = document.getElementById('id_subatencion');
            const url = formAtencion.dataset.urlSubatenciones;
            const cargarSub = (conservar) => {
                const previo = conservar ? sub.value : '';
                sub.innerHTML = '';
                const opcion = (valor, texto) => { const o = document.createElement('option'); o.value = valor; o.textContent = texto; return o; };
                if (!tipo.value) {
                    sub.appendChild(opcion('', 'Seleccione primero un tipo'));
                    sub.disabled = true;
                    return;
                }
                sub.disabled = true;
                sub.appendChild(opcion('', 'Cargando…'));
                fetch(`${url}?tipo=${encodeURIComponent(tipo.value)}`, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' })
                    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
                    .then(datos => {
                        sub.innerHTML = '';
                        const items = datos.subatenciones || [];
                        sub.appendChild(opcion('', items.length ? 'Seleccione…' : 'Este tipo no tiene sub atenciones activas'));
                        items.forEach(s => sub.appendChild(opcion(s.id, s.nombre)));
                        sub.disabled = items.length === 0;
                        if (previo && items.some(s => String(s.id) === previo)) sub.value = previo;
                    })
                    .catch(() => {
                        sub.innerHTML = '';
                        sub.appendChild(opcion('', 'No se pudieron cargar'));
                        if (dialogo) dialogo.fire({ icon: 'error', title: 'Error de conexión', text: 'No se pudieron cargar las sub atenciones. Intente nuevamente.' });
                    });
            };
            if (tipo && sub) {
                tipo.addEventListener('change', () => cargarSub(false));
                cargarSub(true);
            }

            // Búsqueda del solicitante por RUT
            const rut = document.getElementById('id_rut');
            const nombre = document.getElementById('id_nombre');
            const telefono = document.getElementById('id_telefono');
            const estado = document.getElementById('estadoSolicitante');
            if (rut) {
                rut.addEventListener('blur', () => {
                    const valor = rut.value.trim();
                    if (valor.length < 7) return;
                    fetch(`${formAtencion.dataset.urlSolicitante}?rut=${encodeURIComponent(valor)}`, { credentials: 'same-origin' })
                        .then(r => r.ok ? r.json() : null)
                        .then(d => {
                            if (!d) return;
                            if (d.rut) rut.value = d.rut;
                            if (d.encontrado) {
                                if (!nombre.value) nombre.value = d.nombre;
                                if (telefono && !telefono.value) telefono.value = d.telefono || '';
                                estado.innerHTML = '<i class="bi bi-person-check" aria-hidden="true"></i> Vecino registrado: se reutilizan sus datos.';
                            } else if (d.valido === false) {
                                estado.textContent = 'El RUT ingresado no es válido.';
                            } else {
                                estado.innerHTML = '<i class="bi bi-person-plus" aria-hidden="true"></i> RUT nuevo: se registrará al guardar.';
                            }
                        })
                        .catch(() => {});
                });
            }
        }

        /* ---------- 12. Menú lateral en pantallas pequeñas ---------- */
        const alternar = document.querySelector('[data-alternar-menu]');
        const lateral = document.getElementById('menuLateral');
        if (alternar && lateral) {
            const fijar = (abierto) => {
                document.body.classList.toggle('menu-abierto', abierto);
                alternar.setAttribute('aria-expanded', String(abierto));
            };
            alternar.addEventListener('click', () => fijar(!document.body.classList.contains('menu-abierto')));
            document.addEventListener('keydown', e => { if (e.key === 'Escape') fijar(false); });
            lateral.addEventListener('click', e => { if (e.target.closest('a')) fijar(false); });
        }

        /* ---------- 13. Módulos simulados heredados de la EV1 ---------- */
        const abrirModal = (modal) => { modal.classList.add('abierto'); modal.querySelector('input:not([type=hidden]), select, textarea')?.focus(); };
        const cerrarModal = (modal) => modal?.classList.remove('abierto');
        document.querySelectorAll('[data-abrir]').forEach(boton => boton.addEventListener('click', () => {
            const modal = document.getElementById(boton.dataset.abrir);
            if (!modal) return;
            if (boton.dataset.rellenar) {
                Object.entries(JSON.parse(boton.dataset.rellenar)).forEach(([id, valor]) => {
                    const destino = document.getElementById(id);
                    if (!destino) return;
                    if ('value' in destino && destino.tagName !== 'BUTTON') destino.value = valor; else destino.textContent = valor;
                });
            }
            abrirModal(modal);
        }));
        document.querySelectorAll('[data-cerrar]').forEach(b => b.addEventListener('click', () => cerrarModal(b.closest('.telon'))));
        document.querySelectorAll('.telon').forEach(t => t.addEventListener('click', e => { if (e.target === t) cerrarModal(t); }));
        document.addEventListener('keydown', e => { if (e.key === 'Escape') document.querySelectorAll('.telon.abierto').forEach(cerrarModal); });
        document.querySelector('.telon.abierto .campo.invalido input, .telon.abierto .campo.invalido select, .telon.abierto .campo.invalido textarea')?.focus();

        document.querySelectorAll('[data-ir-a]').forEach(sel => sel.addEventListener('change', () => {
            window.location.href = sel.dataset.irA + encodeURIComponent(sel.value);
        }));

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

    function escapar(texto) {
        return String(texto).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }
})();
