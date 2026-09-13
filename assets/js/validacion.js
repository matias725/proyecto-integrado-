/* =====================================================================
   SGR · validacion.js
   Implementa CU-18 "Validar datos de entrada".
   Cubre obligatoriedad, formato, coherencia de fechas y rangos.
   Un mismo módulo atiende a todos los formularios del prototipo.
   ===================================================================== */

const Validador = {

    /* RUT chileno con dígito verificador (módulo 11) */
    rutValido(valor) {
        const limpio = valor.replace(/[.\-]/g, '').toUpperCase();
        if (!/^\d{7,8}[0-9K]$/.test(limpio)) return false;

        const cuerpo = limpio.slice(0, -1);
        const dv = limpio.slice(-1);

        let suma = 0, factor = 2;
        for (let i = cuerpo.length - 1; i >= 0; i--) {
            suma += Number(cuerpo[i]) * factor;
            factor = factor === 7 ? 2 : factor + 1;
        }
        const resto = 11 - (suma % 11);
        const esperado = resto === 11 ? '0' : resto === 10 ? 'K' : String(resto);
        return dv === esperado;
    },

    correoValido(valor) {
        return /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/.test(valor);
    },

    /* Formato chileno: +56 9 XXXX XXXX, con o sin espacios */
    telefonoValido(valor) {
        return /^\+?56\s?9\s?\d{4}\s?\d{4}$/.test(valor.trim());
    },

    fechaNoFutura(valor, hoy = '2026-09-12') {
        return valor <= hoy;
    },

    fechaEnPeriodo(valor, periodo) {
        return valor >= periodo.inicio && valor <= periodo.termino;
    },

    /* ---------------------------------------------------------------
       Aplicación sobre el formulario
       --------------------------------------------------------------- */
    marcarError(campo, mensaje) {
        const contenedor = campo.closest('.campo');
        if (!contenedor) return;
        contenedor.classList.add('invalido');
        contenedor.classList.remove('valido');
        let aviso = contenedor.querySelector('.mensaje-error');
        if (!aviso) {
            aviso = document.createElement('span');
            aviso.className = 'mensaje-error';
            contenedor.appendChild(aviso);
        }
        aviso.innerHTML = `<i class="bi bi-exclamation-circle" aria-hidden="true"></i>${mensaje}`;
        campo.setAttribute('aria-invalid', 'true');
    },

    limpiarError(campo) {
        const contenedor = campo.closest('.campo');
        if (!contenedor) return;
        contenedor.classList.remove('invalido');
        if (campo.value.trim() !== '') contenedor.classList.add('valido');
        campo.removeAttribute('aria-invalid');
    },

    /* Valida un campo según sus atributos data-* */
    validarCampo(campo) {
        const valor = (campo.value || '').trim();
        const reglas = campo.dataset;

        if (campo.hasAttribute('required') && valor === '') {
            this.marcarError(campo, 'Este campo es obligatorio');
            return false;
        }
        if (valor === '') { this.limpiarError(campo); return true; }

        if (reglas.valida === 'rut' && !this.rutValido(valor)) {
            this.marcarError(campo, 'El RUT ingresado no es válido');
            return false;
        }
        if (reglas.valida === 'correo' && !this.correoValido(valor)) {
            this.marcarError(campo, 'Escriba un correo con el formato nombre@dominio.cl');
            return false;
        }
        if (reglas.valida === 'telefono' && !this.telefonoValido(valor)) {
            this.marcarError(campo, 'Use el formato +56 9 1234 5678');
            return false;
        }
        if (reglas.valida === 'fechaPasada' && !this.fechaNoFutura(valor)) {
            this.marcarError(campo, 'La fecha no puede ser posterior a hoy');
            return false;
        }
        if (reglas.valida === 'fechaPeriodo') {
            const p = SGR.periodoAbierto();
            if (!this.fechaNoFutura(valor)) {
                this.marcarError(campo, 'La fecha no puede ser posterior a hoy');
                return false;
            }
            if (!this.fechaEnPeriodo(valor, p)) {
                this.marcarError(campo, `La fecha debe estar dentro del período abierto (${SGR.fecha(p.inicio)} a ${SGR.fecha(p.termino)})`);
                return false;
            }
        }
        if (reglas.min !== undefined && Number(valor) < Number(reglas.min)) {
            this.marcarError(campo, `El valor mínimo permitido es ${reglas.min}`);
            return false;
        }
        if (reglas.max !== undefined && Number(valor) > Number(reglas.max)) {
            this.marcarError(campo, `El valor máximo permitido es ${reglas.max}`);
            return false;
        }
        if (reglas.largoMin && valor.length < Number(reglas.largoMin)) {
            this.marcarError(campo, `Escriba al menos ${reglas.largoMin} caracteres`);
            return false;
        }

        this.limpiarError(campo);
        return true;
    },

    /* Valida el formulario completo y devuelve el resultado */
    validarFormulario(formulario) {
        const campos = formulario.querySelectorAll('input, select, textarea');
        let valido = true;
        let primerError = null;

        campos.forEach(campo => {
            if (campo.type === 'file' || campo.disabled) return;
            if (!this.validarCampo(campo)) {
                valido = false;
                if (!primerError) primerError = campo;
            }
        });

        if (primerError) primerError.focus();
        return valido;
    },

    /* Validación en vivo: se avisa al salir del campo, no mientras se escribe */
    activar(formulario) {
        formulario.querySelectorAll('input, select, textarea').forEach(campo => {
            campo.addEventListener('blur', () => this.validarCampo(campo));
            campo.addEventListener('change', () => this.validarCampo(campo));
        });
    },

    /* Validación de archivos de evidencia (CU-09, RNF-017) */
    archivoValido(archivo, formatos = ['image/jpeg', 'image/png', 'application/pdf'], maxMB = 2) {
        if (!archivo) return { ok: false, motivo: 'Seleccione un archivo' };
        if (!formatos.includes(archivo.type)) {
            return { ok: false, motivo: 'Formato no permitido. Use JPG, PNG o PDF' };
        }
        if (archivo.size > maxMB * 1024 * 1024) {
            return { ok: false, motivo: `El archivo supera el máximo de ${maxMB} MB` };
        }
        return { ok: true };
    }
};

/* Transiciones permitidas de la agenda colectiva (RF-018) */
const TransicionesCompromiso = {
    INGRESADO:  ['PENDIENTE', 'EN_PROCESO'],
    PENDIENTE:  ['EN_PROCESO', 'REALIZADO'],
    EN_PROCESO: ['REALIZADO', 'PENDIENTE'],
    REALIZADO:  [],

    permitida(actual, nuevo) {
        return (this[actual] || []).includes(nuevo);
    }
};
