# loaders/sqlite_loader.py

import sqlite3
import logging
import pandas as pd
from pathlib import Path
from datetime import date

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

        CREATE TABLE IF NOT EXISTS hltv_stats (
            player_name  TEXT PRIMARY KEY,
            country      TEXT,
            team_name    TEXT,
            team_url     TEXT,
            player_url   TEXT,
            maps         INTEGER,
            rounds       INTEGER,
            kd_diff      INTEGER,
            kd           REAL,
            rating       REAL,
            scraped_date TEXT   -- fecha en que se descargó el HTML manualmente
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

def cargar_hltv(datos: list[dict], scraped_date: str | None = None) -> None:
    """
    Carga los datos de HLTV en la tabla hltv_stats.
    scraped_date: fecha del HTML descargado, formato YYYY-MM-DD.
                  Si no se pasa, usa la fecha de hoy.
    """
    if not datos:
        logger.warning("Lista vacía, nada que cargar en hltv_stats")
        return

    fecha = scraped_date or date.today().isoformat()

    # Agregar fecha y convertir tipos numéricos
    registros = []
    for d in datos:
        registros.append({
            "player_name":  d.get("player_name"),
            "country":      d.get("country"),
            "team_name":    d.get("team_name"),
            "team_url":     d.get("team_url"),
            "player_url":   d.get("player_url"),
            "maps":         _a_int(d.get("maps")),
            "rounds":       _a_int(d.get("rounds")),
            "kd_diff":      _a_int(d.get("kd_diff")),
            "kd":           _a_float(d.get("kd")),
            "rating":       _a_float(d.get("rating")),
            "scraped_date": fecha,
        })

    with _get_conn() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        _crear_schema(conn)
        _cargar_tabla(conn, pd.DataFrame(registros), "hltv_stats")

    logger.info(f"Carga HLTV finalizada → {len(registros)} jugadores, fecha: {fecha}")


def _a_int(valor) -> int | None:
    try:
        return int(valor) if valor is not None else None
    except (ValueError, TypeError):
        return None


def _a_float(valor) -> float | None:
    try:
        return float(valor) if valor is not None else None
    except (ValueError, TypeError):
        return None