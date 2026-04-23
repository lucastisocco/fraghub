# loaders/sqlite_loader.py

import sqlite3
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("data/cs2.db")


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _crear_schema(conn: sqlite3.Connection) -> None:
    """
    Crea las tablas si no existen.
    player_url es la clave natural que une las tres tablas —
    no usamos un id autoincremental porque player_url ya es único
    y viene de la fuente, así que sirve como clave estable.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            player_url      TEXT PRIMARY KEY,
            player_name     TEXT NOT NULL,
            player_country  TEXT,
            team_name       TEXT,
            team_url        TEXT,
            role            TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            player_url      TEXT PRIMARY KEY,
            hz              REAL,
            dpi             REAL,
            sens            REAL,
            edpi            REAL,
            edpi_calculado  REAL,
            zoom_sens       REAL,
            resolution      TEXT,
            res_width       INTEGER,
            res_height      INTEGER,
            aspect_ratio    TEXT,
            scaling_mode    TEXT,
            FOREIGN KEY (player_url) REFERENCES players(player_url)
        );

        CREATE TABLE IF NOT EXISTS gear (
            player_url      TEXT PRIMARY KEY,
            mouse           TEXT,
            mouse_url       TEXT,
            monitor         TEXT,
            monitor_url     TEXT,
            gpu             TEXT,
            gpu_url         TEXT,
            mousepad        TEXT,
            mousepad_url    TEXT,
            keyboard        TEXT,
            keyboard_url    TEXT,
            headset         TEXT,
            headset_url     TEXT,
            chair           TEXT,
            chair_url       TEXT,
            FOREIGN KEY (player_url) REFERENCES players(player_url)
        );
    """)
    conn.commit()
    logger.info("Schema verificado/creado")


def _cargar_tabla(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
    tabla: str,
) -> None:
    """
    Inserta o reemplaza filas en la tabla destino.
    `if_exists="replace"` en to_sql haría DROP + CREATE, lo que rompería
    las foreign keys. Usamos INSERT OR REPLACE a nivel de fila en su lugar.
    """
    if df.empty:
        logger.warning(f"DataFrame vacío para tabla '{tabla}', saltando")
        return

    registros = df.to_dict(orient="records")
    if not registros:
        return

    cols   = list(registros[0].keys())
    placeholders = ", ".join(["?"] * len(cols))
    col_names    = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO {tabla} ({col_names}) VALUES ({placeholders})"

    valores = [tuple(r.get(c) for c in cols) for r in registros]

    try:
        conn.executemany(sql, valores)
        conn.commit()
        logger.info(f"  '{tabla}': {len(valores)} filas insertadas/actualizadas")
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"  Error insertando en '{tabla}': {e}")
        raise


def cargar(tablas: dict[str, pd.DataFrame]) -> None:
    """
    Punto de entrada del loader.
    Recibe el dict de DataFrames que retorna transformar() y los persiste en SQLite.
    """
    with _get_conn() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        _crear_schema(conn)

        # El orden importa: players primero por la foreign key
        orden = ["players", "settings", "gear"]
        for nombre in orden:
            if nombre in tablas:
                _cargar_tabla(conn, tablas[nombre], nombre)

    logger.info(f"Carga finalizada → {DB_PATH}")