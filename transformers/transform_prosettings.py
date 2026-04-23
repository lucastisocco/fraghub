# transformers/transform_prosettings.py
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Columnas que deben ser numéricas
NUMERICAS = ["hz", "dpi", "sens", "edpi", "zoom_sens"]

# Columnas que no nos interesan cargar
DESCARTAR = [""]  # columna sin nombre = índice de la tabla original


def transformar(datos: list[dict]) -> dict[str, pd.DataFrame]:
    """
    Recibe los datos crudos del scraper y retorna un dict con tres DataFrames,
    uno por tabla destino en SQLite:
      - "players":  identidad del jugador (quién es)
      - "settings": configuración de juego (cómo juega)
      - "gear":     equipamiento físico (con qué juega)

    Todos comparten player_url como clave de join.
    """
    df = pd.DataFrame(datos)

    # ── 1. Limpieza base ──────────────────────────────────────────────────────

    # Eliminar columnas sin nombre
    df.drop(columns=DESCARTAR, errors="ignore", inplace=True)

    # Eliminar filas sin jugador (no deberían existir, pero por las dudas)
    df.dropna(subset=["player_name"], inplace=True)

    # Quitar duplicados — si el mismo jugador aparece dos veces, nos quedamos
    # con la primera ocurrencia (la de mayor ranking)
    duplicados = df.duplicated(subset=["player_name"], keep="first").sum()
    if duplicados:
        logger.warning(f"{duplicados} jugadores duplicados eliminados")
    df.drop_duplicates(subset=["player_name"], keep="first", inplace=True)

    # ── 2. Conversión de tipos numéricos ──────────────────────────────────────

    for col in NUMERICAS:
        if col not in df.columns:
            continue
        antes = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        nuevos_nulos = df[col].isna().sum() - antes
        if nuevos_nulos > 0:
            logger.warning(f"Columna '{col}': {nuevos_nulos} valores no convertibles → NaN")

    # ── 3. Normalización de strings ───────────────────────────────────────────

    # Campos de texto: strip de espacios y None para strings vacíos
    cols_texto = [
        "player_name", "player_country", "team_name", "role",
        "resolution", "aspect_ratio", "scaling_mode",
        "mouse", "monitor", "gpu", "mousepad", "keyboard", "headset", "chair"
    ]
    for col in cols_texto:
        if col in df.columns:
            df[col] = df[col].str.strip().replace("", None)

    # ── 4. Separar resolución en ancho y alto ─────────────────────────────────

    # "1280x960" → res_width=1280, res_height=960
    res_split = df["resolution"].str.extract(r"^(\d+)x(\d+)$")
    df["res_width"]  = pd.to_numeric(res_split[0], errors="coerce")
    df["res_height"] = pd.to_numeric(res_split[1], errors="coerce")

    no_parseadas = df["res_width"].isna().sum()
    if no_parseadas:
        logger.warning(f"{no_parseadas} resoluciones no parseadas")

    # ── 5. Columna derivada: eDPI calculado (para validación) ─────────────────

    # eDPI = DPI × sens — si el valor scrapeado difiere mucho, puede ser error de datos
    df["edpi_calculado"] = (df["dpi"] * df["sens"]).round(2)
    discrepancias = (
        (df["edpi"].notna()) &
        (df["edpi_calculado"].notna()) &
        ((df["edpi"] - df["edpi_calculado"]).abs() > 1)
    ).sum()
    if discrepancias:
        logger.warning(f"{discrepancias} jugadores con eDPI scrapeado ≠ DPI×sens")

    logger.info(f"Transformación completa: {len(df)} jugadores")

    # ── 6. Split en tres tablas ───────────────────────────────────────────────

    players = df[[
        "player_name", "player_url", "player_country",
        "team_name",   "team_url",
        "role",
    ]].copy()

    settings = df[[
        "player_url",
        "hz", "dpi", "sens", "edpi", "edpi_calculado", "zoom_sens",
        "resolution", "res_width", "res_height",
        "aspect_ratio", "scaling_mode",
    ]].copy()

    gear = df[[
        "player_url",
        "mouse",    "mouse_url",
        "monitor",  "monitor_url",
        "gpu",      "gpu_url",
        "mousepad", "mousepad_url",
        "keyboard", "keyboard_url",
        "headset",  "headset_url",
        "chair",    "chair_url",
    ]].copy()

    logger.info(
        f"Tablas generadas — "
        f"players: {len(players)}, "
        f"settings: {len(settings)}, "
        f"gear: {len(gear)}"
    )

    return {
        "players":  players,
        "settings": settings,
        "gear":     gear,
    }