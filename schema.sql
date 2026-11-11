-- Esquema de la base de datos del Sistema de Control de Gastos Personales.
-- Sale directamente del diagrama de clases: cada clase es una tabla y
-- cada atributo es una columna. Las líneas entre clases son llaves foráneas.

PRAGMA foreign_keys = ON;

-- Clase Usuario
CREATE TABLE IF NOT EXISTS usuario (
    id_usuario      INTEGER PRIMARY KEY AUTOINCREMENT,
    correo          TEXT NOT NULL UNIQUE,
    contrasena      TEXT NOT NULL,                      -- se guarda cifrada (RNF1)
    fecha_registro  TEXT NOT NULL DEFAULT (date('now'))
);

-- Clase Categoria (id_usuario vacío = categoría predefinida)
CREATE TABLE IF NOT EXISTS categoria (
    id_categoria    INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    es_predefinida  INTEGER NOT NULL DEFAULT 0,
    id_usuario      INTEGER REFERENCES usuario(id_usuario)
);

-- Clase Gasto
CREATE TABLE IF NOT EXISTS gasto (
    id_gasto        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario      INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_categoria    INTEGER NOT NULL REFERENCES categoria(id_categoria),
    monto           NUMERIC NOT NULL CHECK (monto > 0),
    fecha           TEXT NOT NULL,                      -- formato AAAA-MM-DD
    descripcion     TEXT
);

-- Clase Ingreso
CREATE TABLE IF NOT EXISTS ingreso (
    id_ingreso      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario      INTEGER NOT NULL REFERENCES usuario(id_usuario),
    monto           NUMERIC NOT NULL CHECK (monto > 0),
    fecha           TEXT NOT NULL,
    descripcion     TEXT
);

-- Clase Deuda
CREATE TABLE IF NOT EXISTS deuda (
    id_deuda        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario      INTEGER NOT NULL REFERENCES usuario(id_usuario),
    nombre          TEXT NOT NULL,
    monto_total     NUMERIC NOT NULL CHECK (monto_total > 0),
    saldo           NUMERIC NOT NULL,
    fecha_limite    TEXT NOT NULL
);

-- Clase PagoDeuda (composición: no existe sin su deuda)
CREATE TABLE IF NOT EXISTS pago_deuda (
    id_pago         INTEGER PRIMARY KEY AUTOINCREMENT,
    id_deuda        INTEGER NOT NULL REFERENCES deuda(id_deuda),
    monto           NUMERIC NOT NULL CHECK (monto > 0),
    fecha           TEXT NOT NULL
);

-- Clase MetaAhorro
CREATE TABLE IF NOT EXISTS meta_ahorro (
    id_meta         INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario      INTEGER NOT NULL REFERENCES usuario(id_usuario),
    nombre          TEXT NOT NULL,
    monto_objetivo  NUMERIC NOT NULL CHECK (monto_objetivo > 0),
    fecha_limite    TEXT NOT NULL,
    monto_ahorrado  NUMERIC NOT NULL DEFAULT 0,
    completada      INTEGER NOT NULL DEFAULT 0
);

-- Clase Aportacion (composición: no existe sin su meta)
CREATE TABLE IF NOT EXISTS aportacion (
    id_aportacion   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_meta         INTEGER NOT NULL REFERENCES meta_ahorro(id_meta),
    monto           NUMERIC NOT NULL CHECK (monto > 0),
    fecha           TEXT NOT NULL
);
