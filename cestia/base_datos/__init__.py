"""SQLite local de CestIA."""

from __future__ import annotations

import sqlite3
from pathlib import Path

ESQUEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS productos (
    id TEXT PRIMARY KEY,
    ean TEXT,
    nombre TEXT NOT NULL,
    marca TEXT,
    envase TEXT,
    categoria TEXT,
    miniatura TEXT,
    url_compartir TEXT,
    ingredientes TEXT,
    alergenos TEXT,
    nutriscore TEXT,
    energia_kcal REAL,
    proteinas REAL,
    hidratos REAL,
    grasas REAL,
    fibra REAL,
    azucares REAL,
    sal REAL,
    nutricion_por TEXT DEFAULT '100g',
    tamano_unidad REAL,
    formato_tamano TEXT,
    precio_unidad REAL,
    precio_bulto REAL,
    precio_unidad_anterior REAL,
    tienda TEXT DEFAULT 'mercadona',
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historial_precios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto TEXT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    precio_unidad REAL,
    precio_bulto REAL,
    registrado_en TEXT NOT NULL,
    UNIQUE(id_producto, registrado_en)
);

CREATE INDEX IF NOT EXISTS idx_historial_producto
    ON historial_precios(id_producto, registrado_en);

CREATE TABLE IF NOT EXISTS cesta (
    id_producto TEXT PRIMARY KEY REFERENCES productos(id) ON DELETE CASCADE,
    cantidad REAL NOT NULL DEFAULT 1,
    anadido_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comprado_en TEXT NOT NULL,
    total REAL NOT NULL,
    notas TEXT
);

CREATE TABLE IF NOT EXISTS lineas_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_compra INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
    id_producto TEXT NOT NULL,
    nombre TEXT NOT NULL,
    categoria TEXT,
    cantidad REAL NOT NULL,
    precio_unidad REAL NOT NULL,
    total_linea REAL NOT NULL,
    energia_kcal REAL,
    proteinas REAL,
    hidratos REAL,
    grasas REAL,
    fibra REAL,
    azucares REAL,
    sal REAL
);

CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto TEXT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    nombre_producto TEXT NOT NULL,
    precio_objetivo REAL NOT NULL,
    activa INTEGER NOT NULL DEFAULT 1,
    creada_en TEXT NOT NULL,
    disparada_en TEXT
);

CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
"""


def ruta_bd_por_defecto() -> Path:
    raiz = Path(__file__).resolve().parents[2]
    datos = raiz / "datos"
    datos.mkdir(parents=True, exist_ok=True)
    return datos / "cestia.db"


def conectar(ruta_bd: Path | str | None = None) -> sqlite3.Connection:
    ruta = Path(ruta_bd) if ruta_bd else ruta_bd_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(str(ruta), check_same_thread=False)
    conexion.row_factory = sqlite3.Row
    conexion.executescript(ESQUEMA)
    _migrar_esquema(conexion)
    return conexion


def _migrar_esquema(conexion: sqlite3.Connection) -> None:
    columnas = {
        fila[1]
        for fila in conexion.execute("PRAGMA table_info(productos)").fetchall()
    }
    if "tienda" not in columnas:
        conexion.execute(
            "ALTER TABLE productos ADD COLUMN tienda TEXT DEFAULT 'mercadona'"
        )
        conexion.commit()
