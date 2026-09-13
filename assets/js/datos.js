/* =====================================================================
   SGR · datos.js
   Datos ficticios en memoria para el prototipo.
   No existe conexión a base de datos ni consumo de API en esta entrega.
   Ningún dato corresponde a personas reales.
   ===================================================================== */

const SGR = {

    datos: {

        delegaciones: [
            { id: 1, nombre: 'Centro',          ambito: 'Centro histórico, administrativo y comercial', encargado: 'Ana Rojas Miranda',    funcionarios: 8,  estado: 'ACTIVA' },
            { id: 2, nombre: 'Avenida del Mar', ambito: 'Borde costero, turismo y servicios',           encargado: 'Diego Fuentes Lara',   funcionarios: 6,  estado: 'ACTIVA' },
            { id: 3, nombre: 'La Antena',       ambito: 'Sector urbano oriental',                       encargado: 'Elena Muñoz Tapia',    funcionarios: 5,  estado: 'ACTIVA' },
            { id: 4, nombre: 'Las Compañías',   ambito: 'Sector urbano norte de alta densidad',         encargado: 'Felipe Aguirre Núñez', funcionarios: 9,  estado: 'ACTIVA' },
            { id: 5, nombre: 'La Pampa',        ambito: 'Sector urbano sur',                            encargado: 'Camila Vega Soto',     funcionarios: 7,  estado: 'ACTIVA' },
            { id: 6, nombre: 'Rural',           ambito: 'Localidades y comunidades rurales dispersas',  encargado: 'Bruno Castillo Peña',  funcionarios: 6,  estado: 'ACTIVA' }
        ],

        cargos: [
            { id: 1, nombre: 'Delegado' },
            { id: 2, nombre: 'Territorial Org. Comunitarias' },
            { id: 3, nombre: 'Gestor Social' },
            { id: 4, nombre: 'Apoyo Administrativo' },
            { id: 5, nombre: 'Supervisor DISERCO' },
            { id: 6, nombre: 'Coordinador DISERCO' },
            { id: 7, nombre: 'Proyectos y Compras' },
            { id: 8, nombre: 'Planificación y Control' },
            { id: 9, nombre: 'Gestor Seguridad' }
        ],

        roles: ['Administrador', 'Coordinador', 'Delegado', 'Funcionario', 'Verificador', 'Consulta'],

        periodos: [
            { id: 1, nombre: 'Trimestre 2026-Q3', inicio: '2026-07-01', termino: '2026-09-30', dias: 91, estado: 'ABIERTO',
              umbralVerde: 100, umbralAmbar: 60, umbralColectivo: 80, tope: 150 },
            { id: 2, nombre: 'Trimestre 2026-Q2', inicio: '2026-04-01', termino: '2026-06-30', dias: 91, estado: 'CERRADO',
              umbralVerde: 100, umbralAmbar: 60, umbralColectivo: 80, tope: 150 }
        ],

        usuarios: [
            { id: 1, rut: '11.111.111-1', nombre: 'Ana Rojas Miranda',    correo: 'ana.rojas@demo.cl',      cargo: 'Delegado',                     delegacion: 'Rural',         roles: ['Delegado', 'Verificador'], estado: 'ACTIVO' },
            { id: 2, rut: '22.222.222-2', nombre: 'Bruno Castillo Peña',  correo: 'bruno.castillo@demo.cl', cargo: 'Gestor Social',                delegacion: 'Rural',         roles: ['Funcionario'],             estado: 'ACTIVO' },
            { id: 3, rut: '33.333.333-3', nombre: 'Camila Vega Soto',     correo: 'camila.vega@demo.cl',    cargo: 'Territorial Org. Comunitarias',delegacion: 'Rural',         roles: ['Funcionario'],             estado: 'ACTIVO' },
            { id: 4, rut: '44.444.444-4', nombre: 'Diego Fuentes Lara',   correo: 'diego.fuentes@demo.cl',  cargo: 'Supervisor DISERCO',           delegacion: 'Centro',        roles: ['Funcionario', 'Verificador'], estado: 'ACTIVO' },
            { id: 5, rut: '55.555.555-5', nombre: 'Elena Muñoz Tapia',    correo: 'elena.munoz@demo.cl',    cargo: 'Planificación y Control',      delegacion: 'Centro',        roles: ['Coordinador'],             estado: 'ACTIVO' },
            { id: 6, rut: '66.666.666-6', nombre: 'Felipe Aguirre Núñez', correo: 'felipe.aguirre@demo.cl', cargo: 'Apoyo Administrativo',         delegacion: 'Las Compañías', roles: ['Administrador', 'Funcionario'], estado: 'ACTIVO' }
        ],

        items: [
            { id: 1, nombre: 'Atenciones en terreno',         unidad: 'Cantidad' },
            { id: 2, nombre: 'Compromisos cerrados en plazo', unidad: 'Cantidad' },
            { id: 3, nombre: 'Reuniones con organizaciones',  unidad: 'Cantidad' },
            { id: 4, nombre: 'Casos sociales gestionados',    unidad: 'Cantidad' },
            { id: 5, nombre: 'Requerimientos derivados',      unidad: 'Cantidad' }
        ],

        tiposActividad: [
            { id: 1, nombre: 'Atención de público',    area: 'Social',      padre: null },
            { id: 2, nombre: 'Visita a terreno',       area: 'Territorial', padre: null },
            { id: 3, nombre: 'Reunión comunitaria',    area: 'Territorial', padre: null },
            { id: 4, nombre: 'Operativo municipal',    area: 'Territorial', padre: null },
            { id: 5, nombre: 'Orientación de subsidios', area: 'Social',    padre: 1 },
            { id: 6, nombre: 'Derivación a DIDECO',    area: 'Social',      padre: 1 },
            { id: 7, nombre: 'Catastro de emergencia', area: 'Territorial', padre: 2 }
        ],

        /* Metas del cargo Gestor Social en el período abierto. Suma 100 % (RN-001) */
        metas: [
            { id: 1, cargo: 'Gestor Social', item: 'Atenciones en terreno',         objetivo: 60, ponderador: 30, avance: 18 },
            { id: 2, cargo: 'Gestor Social', item: 'Compromisos cerrados en plazo', objetivo: 25, ponderador: 20, avance: 20 },
            { id: 3, cargo: 'Gestor Social', item: 'Casos sociales gestionados',    objetivo: 40, ponderador: 35, avance: 25 },
            { id: 4, cargo: 'Gestor Social', item: 'Requerimientos derivados',      objetivo: 30, ponderador: 15, avance: 24 }
        ],

        actividades: [
            { id: 1, codigo: 'EV-2026-000001', fecha: '2026-09-01', funcionario: 'Bruno Castillo Peña', delegacion: 'Rural',
              descripcion: 'Solicitud de orientación sobre subsidio habitacional', item: 'Casos sociales gestionados',
              tipo: 'Orientación de subsidios', estado: 'VALIDADA', evidencia: 'APROBADA' },
            { id: 2, codigo: 'EV-2026-000002', fecha: '2026-09-02', funcionario: 'Bruno Castillo Peña', delegacion: 'Rural',
              descripcion: 'Atención de público en delegación', item: 'Atenciones en terreno',
              tipo: 'Atención de público', estado: 'REGISTRADA', evidencia: 'SIN_EVIDENCIA' },
            { id: 3, codigo: 'EV-2026-000003', fecha: '2026-09-03', funcionario: 'Camila Vega Soto', delegacion: 'Rural',
              descripcion: 'Reunión con junta de vecinos Las Rojas', item: 'Reuniones con organizaciones',
              tipo: 'Reunión comunitaria', estado: 'VALIDADA', evidencia: 'APROBADA' },
            { id: 4, codigo: 'EV-2026-000004', fecha: '2026-09-04', funcionario: 'Camila Vega Soto', delegacion: 'Rural',
              descripcion: 'Visita a terreno sector El Romero', item: 'Atenciones en terreno',
              tipo: 'Visita a terreno', estado: 'RECHAZADA', evidencia: 'RECHAZADA' },
            { id: 5, codigo: 'EV-2026-000005', fecha: '2026-09-08', funcionario: 'Diego Fuentes Lara', delegacion: 'Centro',
              descripcion: 'Operativo de limpieza en calle Cienfuegos', item: 'Requerimientos derivados',
              tipo: 'Operativo municipal', estado: 'REGISTRADA', evidencia: 'PENDIENTE' },
            { id: 6, codigo: 'EV-2026-000006', fecha: '2026-09-09', funcionario: 'Bruno Castillo Peña', delegacion: 'Rural',
              descripcion: 'Catastro de daños por lluvia en El Islón', item: 'Atenciones en terreno',
              tipo: 'Catastro de emergencia', estado: 'REGISTRADA', evidencia: 'PENDIENTE' }
        ],

        compromisos: [
            { id: 1, solicitante: 'Junta de Vecinos Las Rojas', territorio: 'Las Rojas', delegacion: 'Rural',
              descripcion: 'Reposición de luminarias en calle principal', responsable: 'Bruno Castillo Peña',
              fecha: '2026-09-20', estado: 'EN_PROCESO' },
            { id: 2, solicitante: 'Comité de Agua Potable Rural', territorio: 'El Romero', delegacion: 'Rural',
              descripcion: 'Coordinar operativo de limpieza de canal', responsable: 'Camila Vega Soto',
              fecha: '2026-09-05', estado: 'PENDIENTE' },
            { id: 3, solicitante: 'Cámara de Comercio', territorio: 'Centro', delegacion: 'Centro',
              descripcion: 'Retiro de escombros en calle Cienfuegos', responsable: 'Diego Fuentes Lara',
              fecha: '2026-08-28', estado: 'REALIZADO' },
            { id: 4, solicitante: 'Club Deportivo El Milagro', territorio: 'El Milagro', delegacion: 'Rural',
              descripcion: 'Mantención de multicancha del sector', responsable: 'Bruno Castillo Peña',
              fecha: '2026-09-01', estado: 'PENDIENTE' }
        ],

        casosSociales: [
            { id: 1, rut: '99.999.999-9', nombre: 'Persona Usuaria Demo', telefono: '+56 9 5555 5555',
              delegacion: 'Rural', apertura: '2026-07-10', estado: 'ABIERTO',
              gestiones: [
                  { numero: 1, fecha: '2026-07-10', tipo: 'Atención de público',      resultado: 'Ingreso del caso y evaluación inicial' },
                  { numero: 2, fecha: '2026-08-05', tipo: 'Orientación de subsidios', resultado: 'Orientación de subsidio y postulación' },
                  { numero: 3, fecha: '2026-09-01', tipo: 'Derivación a DIDECO',      resultado: 'Derivación para apoyo complementario' }
              ] },
            { id: 2, rut: '88.888.888-8', nombre: 'Caso Demostración Dos', telefono: '+56 9 4444 4444',
              delegacion: 'Rural', apertura: '2026-08-22', estado: 'ABIERTO',
              gestiones: [
                  { numero: 1, fecha: '2026-08-22', tipo: 'Atención de público', resultado: 'Solicitud de ayuda social' }
              ] }
        ],

        auditoria: [
            { fecha: '2026-09-09 11:42', usuario: 'Ana Rojas Miranda',    evento: 'VALIDACION',        entidad: 'evidencia',   registro: 3, anterior: 'PENDIENTE',        nuevo: 'RECHAZADA' },
            { fecha: '2026-09-08 16:05', usuario: 'Elena Muñoz Tapia',    evento: 'CAMBIO_PARAMETRO',  entidad: 'meta',        registro: 1, anterior: 'ponderador=25,00', nuevo: 'ponderador=30,00' },
            { fecha: '2026-09-08 09:20', usuario: 'Bruno Castillo Peña',  evento: 'CAMBIO_ESTADO',     entidad: 'compromiso',  registro: 1, anterior: 'PENDIENTE',        nuevo: 'EN_PROCESO' },
            { fecha: '2026-09-05 14:58', usuario: 'Felipe Aguirre Núñez', evento: 'ALTA',              entidad: 'delegación',  registro: 6, anterior: '—',                nuevo: 'Rural' },
            { fecha: '2026-09-04 10:13', usuario: 'Camila Vega Soto',     evento: 'ALTA',              entidad: 'actividad',   registro: 4, anterior: '—',                nuevo: 'EV-2026-000004' }
        ]
    },

    /* ---------------------------------------------------------------
       Sesión simulada. La selección real ocurre en index.html.
       --------------------------------------------------------------- */
    sesion() {
        const guardada = window.name && window.name.startsWith('{')
            ? JSON.parse(window.name) : null;
        return guardada || { nombre: 'Bruno Castillo Peña', rol: 'Funcionario', delegacion: 'Rural' };
    },

    iniciarSesion(usuario) {
        window.name = JSON.stringify(usuario);
    },

    /* ---------------------------------------------------------------
       Cálculos del sistema (RN-003 a RN-008)
       --------------------------------------------------------------- */
    periodoAbierto() {
        return this.datos.periodos.find(p => p.estado === 'ABIERTO');
    },

    /* RN-007 · meta esperada al día */
    metaEsperadaAlDia(periodo, fecha = new Date('2026-09-12')) {
        const inicio = new Date(periodo.inicio);
        const transcurridos = Math.floor((fecha - inicio) / 86400000) + 1;
        const acotado = Math.min(Math.max(transcurridos, 0), periodo.dias);
        return (acotado / periodo.dias) * 100;
    },

    /* RN-004 · porcentaje de cumplimiento */
    cumplimiento(avance, objetivo) {
        if (!objetivo || objetivo <= 0) return 0;
        return (avance / objetivo) * 100;
    },

    /* RN-005 · cumplimiento ponderado con tope configurable */
    ponderado(cumplimiento, ponderador, tope) {
        return (Math.min(cumplimiento, tope) * ponderador) / 100;
    },

    /* RN-008 · color del semáforo */
    semaforo(cumplimiento, esperado, periodo) {
        if (cumplimiento >= esperado) return 'verde';
        if (cumplimiento >= esperado * (periodo.umbralAmbar / 100)) return 'ambar';
        return 'rojo';
    },

    /* ---------------------------------------------------------------
       Utilidades de presentación
       --------------------------------------------------------------- */
    cifra(n, decimales = 1) {
        return n.toLocaleString('es-CL', {
            minimumFractionDigits: decimales,
            maximumFractionDigits: decimales
        });
    },

    fecha(iso) {
        if (!iso) return '—';
        const [a, m, d] = iso.split('-');
        return `${d}-${m}-${a}`;
    },

    etiquetaEstado(estado) {
        const mapa = {
            VALIDADA:      ['ok', 'Validada'],
            REGISTRADA:    ['neutro', 'Registrada'],
            RECHAZADA:     ['error', 'Rechazada'],
            ANULADA:       ['neutro', 'Anulada'],
            APROBADA:      ['ok', 'Aprobada'],
            PENDIENTE:     ['pendiente', 'Pendiente'],
            SIN_EVIDENCIA: ['neutro', 'Sin evidencia'],
            EN_CORRECCION: ['pendiente', 'En corrección'],
            INGRESADO:     ['neutro', 'Ingresado'],
            EN_PROCESO:    ['proceso', 'En proceso'],
            REALIZADO:     ['ok', 'Realizado'],
            ACTIVA:        ['ok', 'Activa'],
            ACTIVO:        ['ok', 'Activo'],
            INACTIVA:      ['neutro', 'Inactiva'],
            ABIERTO:       ['ok', 'Abierto'],
            CERRADO:       ['neutro', 'Cerrado']
        };
        const [clase, texto] = mapa[estado] || ['neutro', estado];
        return `<span class="estado ${clase}">${texto}</span>`;
    },

    notificar(mensaje, icono = 'bi-check-circle') {
        document.querySelectorAll('.notificacion').forEach(n => n.remove());
        const aviso = document.createElement('div');
        aviso.className = 'notificacion';
        aviso.setAttribute('role', 'status');
        aviso.innerHTML = `<i class="bi ${icono}" aria-hidden="true"></i>${mensaje}`;
        document.body.appendChild(aviso);
        setTimeout(() => aviso.remove(), 3600);
    },

    abrirModal(id) {
        const m = document.getElementById(id);
        if (m) { m.classList.add('abierto'); m.querySelector('button, input, select')?.focus(); }
    },

    cerrarModal(id) {
        document.getElementById(id)?.classList.remove('abierto');
    },

    /* Genera el código de evidencia (CU-19) */
    generarCodigo() {
        const usados = this.datos.actividades.map(a => Number(a.codigo.split('-')[2]));
        const siguiente = Math.max(0, ...usados) + 1;
        return `EV-2026-${String(siguiente).padStart(6, '0')}`;
    }
};

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.telon.abierto').forEach(m => m.classList.remove('abierto'));
    }
});
