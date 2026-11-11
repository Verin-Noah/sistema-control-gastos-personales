"""Acceso a datos.

Este archivo es el componente "Acceso a datos" del diagrama de componentes:
es el único lugar que sabe cómo conectarse a la base de datos. Si algún día
se cambia de motor (por ejemplo a SQL Server o MySQL), solo se modifica aquí.
"""
import os
import sqlite3

from flask import g

CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA_BD = os.path.join(CARPETA, "gestor.db")
RUTA_ESQUEMA = os.path.join(CARPETA, "schema.sql")

CATEGORIAS_BASE = ["Transporte", "Comida", "Materiales escolares", "Gastos personales"]


def _conectar():
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row          # permite usar fila["monto"]
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def obtener_conexion():
    """Devuelve la conexión de la petición actual (se abre una sola vez)."""
    if "db" not in g:
        g.db = _conectar()
    return g.db


def cerrar_conexion(error=None):
    conexion = g.pop("db", None)
    if conexion is not None:
        conexion.close()


def inicializar_bd():
    """Crea las tablas (si no existen) y carga las categorías predefinidas."""
    conexion = _conectar()
    with open(RUTA_ESQUEMA, encoding="utf-8") as archivo:
        conexion.executescript(archivo.read())
    hay_categorias = conexion.execute(
        "SELECT COUNT(*) FROM categoria WHERE es_predefinida = 1"
    ).fetchone()[0]
    if hay_categorias == 0:
        conexion.executemany(
            "INSERT INTO categoria (nombre, es_predefinida) VALUES (?, 1)",
            [(nombre,) for nombre in CATEGORIAS_BASE],
        )
    conexion.commit()
    conexion.close()


if __name__ == "__main__":
    inicializar_bd()
    print("Base de datos lista:", RUTA_BD)
