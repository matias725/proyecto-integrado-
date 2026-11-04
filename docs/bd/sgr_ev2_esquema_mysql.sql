-- =====================================================================
-- SGR La Serena · EV2 · esquema MySQL 8 generado desde las migraciones de Django
-- Generado con: python manage.py migrate (MySQL 8.0) + mysqldump --no-data
-- Incluye la matriz SGR (app gestion: períodos, metas por cargo, actividades,
-- evidencias, ausencias, felicitaciones/reclamos y organizaciones).
-- Para crear la base desde cero se recomienda: python manage.py migrate
-- Los datos iniciales se cargan con: python manage.py sgr_inicializar [--demo]
-- Modelo, normalización e índices: docs/bd/modelo_de_datos.md
-- =====================================================================

CREATE DATABASE IF NOT EXISTS sgr_laserena CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE sgr_laserena;
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE `atenciones_atencion` (
CREATE TABLE `atenciones_atencion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `descripcion` longtext NOT NULL,
  `creada` datetime(6) NOT NULL,
  `token_envio` char(32) NOT NULL,
  `delegacion_id` bigint NOT NULL,
  `responsable_id` bigint NOT NULL,
  `subatencion_id` bigint NOT NULL,
  `tipo_id` bigint NOT NULL,
  `solicitante_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token_envio` (`token_envio`),
  KEY `atenciones_atencion_responsable_id_6175a950_fk_cuentas_u` (`responsable_id`),
  KEY `atenciones_atencion_subatencion_id_65e29858_fk_catalogos` (`subatencion_id`),
  KEY `atenciones_atencion_tipo_id_02b07ba8_fk_catalogos` (`tipo_id`),
  KEY `atenciones_atencion_solicitante_id_1ebdac0a_fk_atencione` (`solicitante_id`),
  KEY `atenciones__delegac_fa319a_idx` (`delegacion_id`,`creada` DESC),
  CONSTRAINT `atenciones_atencion_delegacion_id_58e20d54_fk_catalogos` FOREIGN KEY (`delegacion_id`) REFERENCES `catalogos_delegacion` (`id`),
  CONSTRAINT `atenciones_atencion_responsable_id_6175a950_fk_cuentas_u` FOREIGN KEY (`responsable_id`) REFERENCES `cuentas_usuario` (`id`),
  CONSTRAINT `atenciones_atencion_solicitante_id_1ebdac0a_fk_atencione` FOREIGN KEY (`solicitante_id`) REFERENCES `atenciones_solicitante` (`id`),
  CONSTRAINT `atenciones_atencion_subatencion_id_65e29858_fk_catalogos` FOREIGN KEY (`subatencion_id`) REFERENCES `catalogos_subatencion` (`id`),
  CONSTRAINT `atenciones_atencion_tipo_id_02b07ba8_fk_catalogos` FOREIGN KEY (`tipo_id`) REFERENCES `catalogos_tipoatencion` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `atenciones_solicitante` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `rut` varchar(12) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `telefono` varchar(20) NOT NULL,
  `creado` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `rut` (`rut`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `catalogos_cargo` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `activo` tinyint(1) NOT NULL,
  `creado` datetime(6) NOT NULL,
  `actualizado` datetime(6) NOT NULL,
  `codigo` varchar(6) NOT NULL,
  `nombre` varchar(80) NOT NULL,
  `descripcion` varchar(300) NOT NULL,
  `es_delegado` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `nombre` (`nombre`),
  UNIQUE KEY `cargo_nombre_unico_ci` ((lower(`nombre`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `catalogos_delegacion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `activo` tinyint(1) NOT NULL,
  `creado` datetime(6) NOT NULL,
  `actualizado` datetime(6) NOT NULL,
  `codigo` varchar(6) NOT NULL,
  `nombre` varchar(80) NOT NULL,
  `direccion` varchar(150) NOT NULL,
  `comuna` varchar(60) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `nombre` (`nombre`),
  UNIQUE KEY `delegacion_nombre_unico_ci` ((lower(`nombre`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `catalogos_itemmedicion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `activo` tinyint(1) NOT NULL,
  `creado` datetime(6) NOT NULL,
  `actualizado` datetime(6) NOT NULL,
  `codigo` varchar(6) NOT NULL,
  `nombre` varchar(120) NOT NULL,
  `descripcion` varchar(250) NOT NULL,
  `medicion` varchar(8) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `nombre` (`nombre`),
  UNIQUE KEY `item_nombre_unico_ci` ((lower(`nombre`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `catalogos_subatencion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `activo` tinyint(1) NOT NULL,
  `creado` datetime(6) NOT NULL,
  `actualizado` datetime(6) NOT NULL,
  `codigo` varchar(6) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `tipo_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `subatencion_nombre_por_tipo_ci` ((lower(`nombre`)),`tipo_id`),
  KEY `catalogos_subatencio_tipo_id_65f80e79_fk_catalogos` (`tipo_id`),
  CONSTRAINT `catalogos_subatencio_tipo_id_65f80e79_fk_catalogos` FOREIGN KEY (`tipo_id`) REFERENCES `catalogos_tipoatencion` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `catalogos_tipoatencion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `activo` tinyint(1) NOT NULL,
  `creado` datetime(6) NOT NULL,
  `actualizado` datetime(6) NOT NULL,
  `codigo` varchar(6) NOT NULL,
  `nombre` varchar(80) NOT NULL,
  `descripcion` varchar(250) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `nombre` (`nombre`),
  UNIQUE KEY `tipo_nombre_unico_ci` ((lower(`nombre`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `core_auditoria` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `fecha` datetime(6) NOT NULL,
  `usuario_texto` varchar(120) NOT NULL,
  `evento` varchar(20) NOT NULL,
  `entidad` varchar(60) NOT NULL,
  `registro` varchar(40) NOT NULL,
  `detalle` varchar(500) NOT NULL,
  `delegacion` varchar(80) NOT NULL,
  `ip` char(39) DEFAULT NULL,
  `usuario_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `core_auditoria_usuario_id_124e9f95_fk_cuentas_usuario_id` (`usuario_id`),
  KEY `core_auditoria_fecha_43ae8b6b` (`fecha`),
  KEY `core_auditoria_evento_602f26cd` (`evento`),
  CONSTRAINT `core_auditoria_usuario_id_124e9f95_fk_cuentas_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `cuentas_codigorecuperacion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `codigo_hash` varchar(128) NOT NULL,
  `creado` datetime(6) NOT NULL,
  `expira` datetime(6) NOT NULL,
  `intentos` smallint unsigned NOT NULL,
  `verificado_en` datetime(6) DEFAULT NULL,
  `usado_en` datetime(6) DEFAULT NULL,
  `anulado` tinyint(1) NOT NULL,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `cuentas_codigorecupe_usuario_id_1fd123d9_fk_cuentas_u` (`usuario_id`),
  CONSTRAINT `cuentas_codigorecupe_usuario_id_1fd123d9_fk_cuentas_u` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`),
  CONSTRAINT `cuentas_codigorecuperacion_chk_1` CHECK ((`intentos` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `cuentas_correosaliente` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `destinatario` varchar(254) NOT NULL,
  `asunto` varchar(200) NOT NULL,
  `cuerpo` longtext NOT NULL,
  `enviado` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `cuentas_permiso` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `modulo` varchar(30) NOT NULL,
  `accion` varchar(10) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `permiso_unico` (`modulo`,`accion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `cuentas_rol` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `activo` tinyint(1) NOT NULL,
  `creado` datetime(6) NOT NULL,
  `actualizado` datetime(6) NOT NULL,
  `codigo` varchar(6) NOT NULL,
  `nombre` varchar(60) NOT NULL,
  `descripcion` varchar(200) NOT NULL,
  `alcance` varchar(12) NOT NULL,
  `protegido` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `nombre` (`nombre`),
  UNIQUE KEY `rol_nombre_unico_ci` ((lower(`nombre`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `cuentas_rol_permisos` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `rol_id` bigint NOT NULL,
  `permiso_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cuentas_rol_permisos_rol_id_permiso_id_6dfcc9a9_uniq` (`rol_id`,`permiso_id`),
  KEY `cuentas_rol_permisos_permiso_id_7769c370_fk_cuentas_permiso_id` (`permiso_id`),
  CONSTRAINT `cuentas_rol_permisos_permiso_id_7769c370_fk_cuentas_permiso_id` FOREIGN KEY (`permiso_id`) REFERENCES `cuentas_permiso` (`id`),
  CONSTRAINT `cuentas_rol_permisos_rol_id_c015f93e_fk_cuentas_rol_id` FOREIGN KEY (`rol_id`) REFERENCES `cuentas_rol` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `cuentas_usuario` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `nombre_usuario` varchar(40) NOT NULL,
  `correo` varchar(254) NOT NULL,
  `nombre` varchar(120) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `intentos_fallidos` smallint unsigned NOT NULL,
  `bloqueado_hasta` datetime(6) DEFAULT NULL,
  `creado` datetime(6) NOT NULL,
  `actualizado` datetime(6) NOT NULL,
  `rol_id` bigint NOT NULL,
  `cargo_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre_usuario` (`nombre_usuario`),
  UNIQUE KEY `correo` (`correo`),
  KEY `cuentas_usuario_rol_id_2fc1a534_fk_cuentas_rol_id` (`rol_id`),
  KEY `cuentas_usuario_cargo_id_d9b64295_fk_catalogos_cargo_id` (`cargo_id`),
  CONSTRAINT `cuentas_usuario_cargo_id_d9b64295_fk_catalogos_cargo_id` FOREIGN KEY (`cargo_id`) REFERENCES `catalogos_cargo` (`id`),
  CONSTRAINT `cuentas_usuario_rol_id_2fc1a534_fk_cuentas_rol_id` FOREIGN KEY (`rol_id`) REFERENCES `cuentas_rol` (`id`),
  CONSTRAINT `cuentas_usuario_chk_1` CHECK ((`intentos_fallidos` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `cuentas_usuario_delegaciones` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint NOT NULL,
  `delegacion_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cuentas_usuario_delegaci_usuario_id_delegacion_id_d7687d2f_uniq` (`usuario_id`,`delegacion_id`),
  KEY `cuentas_usuario_dele_delegacion_id_ac5f3da3_fk_catalogos` (`delegacion_id`),
  CONSTRAINT `cuentas_usuario_dele_delegacion_id_ac5f3da3_fk_catalogos` FOREIGN KEY (`delegacion_id`) REFERENCES `catalogos_delegacion` (`id`),
  CONSTRAINT `cuentas_usuario_dele_usuario_id_801a885f_fk_cuentas_u` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `gestion_actividad` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `naturaleza` varchar(8) NOT NULL,
  `origen` varchar(3) NOT NULL,
  `fecha` date NOT NULL,
  `titulo` varchar(200) NOT NULL,
  `descripcion` longtext NOT NULL,
  `solicitante_nombre` varchar(150) NOT NULL,
  `solicitante_telefono` varchar(20) NOT NULL,
  `solicitante_es_delegado` tinyint(1) NOT NULL,
  `territorio` varchar(80) NOT NULL,
  `area_apoyo` varchar(120) NOT NULL,
  `estado` varchar(10) NOT NULL,
  `fecha_compromiso` date DEFAULT NULL,
  `fecha_cierre` date DEFAULT NULL,
  `validacion` varchar(9) NOT NULL,
  `validada_en` datetime(6) DEFAULT NULL,
  `motivo_rechazo` varchar(300) NOT NULL,
  `puntua` tinyint(1) NOT NULL,
  `motivo_sin_puntaje` varchar(300) NOT NULL,
  `ingresada_el` date NOT NULL,
  `creada` datetime(6) NOT NULL,
  `token_envio` char(32) NOT NULL,
  `delegacion_id` bigint NOT NULL,
  `funcionario_id` bigint NOT NULL,
  `item_id` bigint NOT NULL,
  `validada_por_id` bigint DEFAULT NULL,
  `organizacion_id` bigint DEFAULT NULL,
  `periodo_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token_envio` (`token_envio`),
  KEY `gestion_actividad_organizacion_id_2e06eb96_fk_gestion_o` (`organizacion_id`),
  KEY `gestion_actividad_periodo_id_9ff80ccb_fk_gestion_periodo_id` (`periodo_id`),
  KEY `act_ingresos_diarios` (`funcionario_id`,`ingresada_el`),
  KEY `act_avance_item` (`funcionario_id`,`periodo_id`,`estado`,`puntua`,`validacion`,`item_id`),
  KEY `act_delegacion_fecha` (`delegacion_id`,`fecha` DESC,`id` DESC),
  KEY `act_bandeja_validacion` (`delegacion_id`,`validacion`,`fecha` DESC,`id` DESC),
  KEY `gestion_actividad_item_id_5fb24d1c_fk_catalogos_itemmedicion_id` (`item_id`),
  KEY `gestion_actividad_validada_por_id_a1024ef8_fk_cuentas_usuario_id` (`validada_por_id`),
  CONSTRAINT `gestion_actividad_delegacion_id_cc54793c_fk_catalogos` FOREIGN KEY (`delegacion_id`) REFERENCES `catalogos_delegacion` (`id`),
  CONSTRAINT `gestion_actividad_funcionario_id_f28aa9a1_fk_cuentas_usuario_id` FOREIGN KEY (`funcionario_id`) REFERENCES `cuentas_usuario` (`id`),
  CONSTRAINT `gestion_actividad_item_id_5fb24d1c_fk_catalogos_itemmedicion_id` FOREIGN KEY (`item_id`) REFERENCES `catalogos_itemmedicion` (`id`),
  CONSTRAINT `gestion_actividad_organizacion_id_2e06eb96_fk_gestion_o` FOREIGN KEY (`organizacion_id`) REFERENCES `gestion_organizacion` (`id`),
  CONSTRAINT `gestion_actividad_periodo_id_9ff80ccb_fk_gestion_periodo_id` FOREIGN KEY (`periodo_id`) REFERENCES `gestion_periodo` (`id`),
  CONSTRAINT `gestion_actividad_validada_por_id_a1024ef8_fk_cuentas_usuario_id` FOREIGN KEY (`validada_por_id`) REFERENCES `cuentas_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `gestion_ausencia` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tipo` varchar(10) NOT NULL,
  `desde` date NOT NULL,
  `hasta` date NOT NULL,
  `observacion` varchar(200) NOT NULL,
  `creada` datetime(6) NOT NULL,
  `funcionario_id` bigint NOT NULL,
  `registrada_por_id` bigint NOT NULL,
  `periodo_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `gestion_ausencia_funcionario_id_4075a350_fk_cuentas_usuario_id` (`funcionario_id`),
  KEY `gestion_ausencia_registrada_por_id_208e361c_fk_cuentas_u` (`registrada_por_id`),
  KEY `aus_periodo_funcionario` (`periodo_id`,`funcionario_id`),
  CONSTRAINT `gestion_ausencia_funcionario_id_4075a350_fk_cuentas_usuario_id` FOREIGN KEY (`funcionario_id`) REFERENCES `cuentas_usuario` (`id`),
  CONSTRAINT `gestion_ausencia_periodo_id_84b14f08_fk_gestion_periodo_id` FOREIGN KEY (`periodo_id`) REFERENCES `gestion_periodo` (`id`),
  CONSTRAINT `gestion_ausencia_registrada_por_id_208e361c_fk_cuentas_u` FOREIGN KEY (`registrada_por_id`) REFERENCES `cuentas_usuario` (`id`),
  CONSTRAINT `ausencia_fechas_validas` CHECK ((`hasta` >= `desde`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `gestion_evidencia` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `archivo` varchar(100) NOT NULL,
  `nombre_original` varchar(150) NOT NULL,
  `tipo_mime` varchar(60) NOT NULL,
  `tamano` int unsigned NOT NULL,
  `descripcion` varchar(200) NOT NULL,
  `subida_en` datetime(6) NOT NULL,
  `actividad_id` bigint NOT NULL,
  `subida_por_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `gestion_evidencia_actividad_id_6356a6c4_fk_gestion_actividad_id` (`actividad_id`),
  KEY `gestion_evidencia_subida_por_id_4ba27aad_fk_cuentas_usuario_id` (`subida_por_id`),
  CONSTRAINT `gestion_evidencia_actividad_id_6356a6c4_fk_gestion_actividad_id` FOREIGN KEY (`actividad_id`) REFERENCES `gestion_actividad` (`id`),
  CONSTRAINT `gestion_evidencia_subida_por_id_4ba27aad_fk_cuentas_usuario_id` FOREIGN KEY (`subida_por_id`) REFERENCES `cuentas_usuario` (`id`),
  CONSTRAINT `gestion_evidencia_chk_1` CHECK ((`tamano` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `gestion_historialactividad` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `fecha` datetime(6) NOT NULL,
  `estado_anterior` varchar(10) NOT NULL,
  `estado_nuevo` varchar(10) NOT NULL,
  `observacion` varchar(500) NOT NULL,
  `actividad_id` bigint NOT NULL,
  `usuario_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `gestion_historialact_actividad_id_97f038d5_fk_gestion_a` (`actividad_id`),
  KEY `gestion_historialact_usuario_id_ebc9d5c1_fk_cuentas_u` (`usuario_id`),
  CONSTRAINT `gestion_historialact_actividad_id_97f038d5_fk_gestion_a` FOREIGN KEY (`actividad_id`) REFERENCES `gestion_actividad` (`id`),
  CONSTRAINT `gestion_historialact_usuario_id_ebc9d5c1_fk_cuentas_u` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `gestion_metacargo` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `meta` int unsigned NOT NULL,
  `ponderador` decimal(5,2) NOT NULL,
  `cargo_id` bigint NOT NULL,
  `item_id` bigint NOT NULL,
  `periodo_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `meta_unica_por_cargo` (`periodo_id`,`cargo_id`,`item_id`),
  KEY `gestion_metacargo_cargo_id_c4fe0ed9_fk_catalogos_cargo_id` (`cargo_id`),
  KEY `gestion_metacargo_item_id_47dfdede_fk_catalogos_itemmedicion_id` (`item_id`),
  CONSTRAINT `gestion_metacargo_cargo_id_c4fe0ed9_fk_catalogos_cargo_id` FOREIGN KEY (`cargo_id`) REFERENCES `catalogos_cargo` (`id`),
  CONSTRAINT `gestion_metacargo_item_id_47dfdede_fk_catalogos_itemmedicion_id` FOREIGN KEY (`item_id`) REFERENCES `catalogos_itemmedicion` (`id`),
  CONSTRAINT `gestion_metacargo_periodo_id_a210cfee_fk_gestion_periodo_id` FOREIGN KEY (`periodo_id`) REFERENCES `gestion_periodo` (`id`),
  CONSTRAINT `gestion_metacargo_chk_1` CHECK ((`meta` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `gestion_observacion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tipo` varchar(12) NOT NULL,
  `fecha` date NOT NULL,
  `medio` varchar(8) NOT NULL,
  `remitente` varchar(150) NOT NULL,
  `descripcion` varchar(500) NOT NULL,
  `respaldo` varchar(100) NOT NULL,
  `respaldo_nombre` varchar(150) NOT NULL,
  `creada` datetime(6) NOT NULL,
  `funcionario_id` bigint NOT NULL,
  `registrada_por_id` bigint NOT NULL,
  `periodo_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `gestion_observacion_funcionario_id_ce43b913_fk_cuentas_u` (`funcionario_id`),
  KEY `gestion_observacion_registrada_por_id_00fcaff6_fk_cuentas_u` (`registrada_por_id`),
  KEY `obs_periodo_funcionario` (`periodo_id`,`funcionario_id`,`tipo`),
  CONSTRAINT `gestion_observacion_funcionario_id_ce43b913_fk_cuentas_u` FOREIGN KEY (`funcionario_id`) REFERENCES `cuentas_usuario` (`id`),
  CONSTRAINT `gestion_observacion_periodo_id_2e63e774_fk_gestion_periodo_id` FOREIGN KEY (`periodo_id`) REFERENCES `gestion_periodo` (`id`),
  CONSTRAINT `gestion_observacion_registrada_por_id_00fcaff6_fk_cuentas_u` FOREIGN KEY (`registrada_por_id`) REFERENCES `cuentas_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `gestion_organizacion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nombre` varchar(200) NOT NULL,
  `domicilio` varchar(200) NOT NULL,
  `socios` int unsigned DEFAULT NULL,
  `fecha_constitucion` date DEFAULT NULL,
  `registro_pj` int unsigned NOT NULL,
  `fecha_inscripcion` date DEFAULT NULL,
  `registro_directiva` int unsigned DEFAULT NULL,
  `verificada` tinyint(1) NOT NULL,
  `observacion` varchar(300) NOT NULL,
  `activo` tinyint(1) NOT NULL,
  `actualizado` datetime(6) NOT NULL,
  `delegacion_id` bigint DEFAULT NULL,
  `tipo_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `registro_pj` (`registro_pj`),
  KEY `gestion_organizacion_tipo_id_42b637ec_fk_gestion_t` (`tipo_id`),
  KEY `org_delegacion_tipo` (`delegacion_id`,`tipo_id`),
  KEY `org_nombre_ci` ((lower(`nombre`))),
  CONSTRAINT `gestion_organizacion_delegacion_id_7f7c90bb_fk_catalogos` FOREIGN KEY (`delegacion_id`) REFERENCES `catalogos_delegacion` (`id`),
  CONSTRAINT `gestion_organizacion_tipo_id_42b637ec_fk_gestion_t` FOREIGN KEY (`tipo_id`) REFERENCES `gestion_tipoorganizacion` (`id`),
  CONSTRAINT `gestion_organizacion_chk_1` CHECK ((`socios` >= 0)),
  CONSTRAINT `gestion_organizacion_chk_2` CHECK ((`registro_pj` >= 0)),
  CONSTRAINT `gestion_organizacion_chk_3` CHECK ((`registro_directiva` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `gestion_periodo` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nombre` varchar(40) NOT NULL,
  `inicio` date NOT NULL,
  `termino` date NOT NULL,
  `estado` varchar(8) NOT NULL,
  `tope_item` smallint unsigned NOT NULL,
  `tope_total` smallint unsigned NOT NULL,
  `bono_felicitacion` smallint unsigned NOT NULL,
  `max_felicitaciones` smallint unsigned NOT NULL,
  `descuento_reclamo` smallint unsigned NOT NULL,
  `umbral_naranjo` smallint unsigned NOT NULL,
  `cumplimiento_minimo` smallint unsigned NOT NULL,
  `creado` datetime(6) NOT NULL,
  `marca_abierto` smallint unsigned GENERATED ALWAYS AS ((case when (`estado` = _utf8mb4'ABIERTO') then 1 else NULL end)) STORED,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`),
  UNIQUE KEY `marca_abierto` (`marca_abierto`),
  CONSTRAINT `gestion_periodo_chk_1` CHECK ((`tope_item` >= 0)),
  CONSTRAINT `gestion_periodo_chk_2` CHECK ((`tope_total` >= 0)),
  CONSTRAINT `gestion_periodo_chk_3` CHECK ((`bono_felicitacion` >= 0)),
  CONSTRAINT `gestion_periodo_chk_4` CHECK ((`max_felicitaciones` >= 0)),
  CONSTRAINT `gestion_periodo_chk_5` CHECK ((`descuento_reclamo` >= 0)),
  CONSTRAINT `gestion_periodo_chk_6` CHECK ((`umbral_naranjo` >= 0)),
  CONSTRAINT `gestion_periodo_chk_7` CHECK ((`cumplimiento_minimo` >= 0)),
  CONSTRAINT `periodo_fechas_validas` CHECK ((`termino` > `inicio`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `gestion_tipoorganizacion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `activo` tinyint(1) NOT NULL,
  `creado` datetime(6) NOT NULL,
  `actualizado` datetime(6) NOT NULL,
  `codigo` varchar(6) NOT NULL,
  `nombre` varchar(60) NOT NULL,
  `familia` varchar(12) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `nombre` (`nombre`),
  UNIQUE KEY `tipo_org_nombre_unico_ci` ((lower(`nombre`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;
