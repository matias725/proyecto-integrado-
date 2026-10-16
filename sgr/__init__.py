# PyMySQL reemplaza a mysqlclient: no requiere compilar librerías en el servidor.
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:  # pragma: no cover - solo necesario con MySQL
    pass
