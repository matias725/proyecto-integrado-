-- =====================================================================
-- SGR La Serena · creación de la base de datos y del usuario de la app
-- Ejecutar una sola vez como administrador de MySQL 8:
--   mysql -u root -p < scripts/mysql_crear_bd.sql
-- Reemplace CAMBIAR_CLAVE por una contraseña segura y guárdela solo en
-- el archivo .env del servidor (SGR_DB_CLAVE). No la suba a Git.
-- =====================================================================
CREATE DATABASE IF NOT EXISTS sgr_laserena
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE USER IF NOT EXISTS 'sgr'@'%' IDENTIFIED BY 'CAMBIAR_CLAVE';
GRANT ALL PRIVILEGES ON sgr_laserena.* TO 'sgr'@'%';
-- Solo para ejecutar las pruebas automáticas contra MySQL (crea test_sgr_laserena):
-- GRANT ALL PRIVILEGES ON test_sgr_laserena.* TO 'sgr'@'%';
FLUSH PRIVILEGES;
