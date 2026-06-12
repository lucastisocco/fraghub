# extractor/hltv_scraper.py

import logging
from pathlib import Path
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HTML_PATH = Path("data/HLTV.html")


def _parsear_fila(tr) -> dict | None:
    """
    Estructura de cada <tr>:
      td.playerCol  → flag img (país) + <a> (nombre + URL)
      td.teamCol    → data-sort (nombre equipo) + <a href> (URL equipo)
      td.statsDetail[0] → maps
      td.statsDetail[1] → rounds
      td.kdDiffCol  → data-sort (valor numérico de kd_diff)
      td.statsDetail[2] → k/d ratio
      td.ratingCol  → rating 3.0
    """
    try:
        # Player
        player_td = tr.find("td", class_="playerCol")
        if not player_td:
            return None

        flag_img   = player_td.find("img", class_="flag")
        country    = flag_img["title"] if flag_img else None
        player_a   = player_td.find("a")
        player_name = player_a.get_text(strip=True) if player_a else None
        player_url = player_a["href"].split("?")[0] if player_a else None

        if not player_name:
            return None

        # Team
        team_td   = tr.find("td", class_="teamCol")
        team_name = team_td.get("data-sort") if team_td else None
        team_a    = team_td.find("a") if team_td else None
        team_url = team_a["href"].split("?")[0] if team_a else None

        # Stats numéricas — en orden de aparición en el HTML
        stats_tds = tr.find_all("td", class_="statsDetail")
        maps   = stats_tds[0].get_text(strip=True) if len(stats_tds) > 0 else None
        rounds = stats_tds[1].get_text(strip=True) if len(stats_tds) > 1 else None
        kd     = stats_tds[2].get_text(strip=True) if len(stats_tds) > 2 else None

        # KD Diff — el valor limpio está en data-sort (evita parsear "+402")
        kd_diff_td = tr.find("td", class_="kdDiffCol")
        kd_diff = kd_diff_td.get("data-sort") if kd_diff_td else None

        # Rating
        rating_td = tr.find("td", class_="ratingCol")
        rating = rating_td.get_text(strip=True) if rating_td else None

        return {
            "player_name": player_name,
            "player_url": player_url,
            "country":     country,
            "team_name":   team_name,
            "team_url":   team_url,
            "maps":        maps,
            "rounds":      rounds,
            "kd_diff":     kd_diff,
            "kd":          kd,
            "rating":      rating,
        }

    except Exception as e:
        logger.warning(f"Error parseando fila: {e}")
        return None


def scrape_hltv_local(path: Path = HTML_PATH) -> list[dict]:
    """
    Lee el HTML descargado manualmente y extrae la tabla de stats.
    Retorna lista de dicts, uno por jugador.
    """
    if not path.exists():
        logger.error(f"Archivo no encontrado: {path}")
        return []

    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    tabla = soup.find("table", class_="player-ratings-table")
    if not tabla:
        logger.error("No se encontró la tabla .player-ratings-table en el HTML")
        return []

    tbody = tabla.find("tbody")
    if not tbody:
        logger.error("La tabla no tiene <tbody>")
        return []

    resultados = []
    for tr in tbody.find_all("tr"):
        fila = _parsear_fila(tr)
        if fila:
            resultados.append(fila)

    logger.info(f"{len(resultados)} jugadores extraídos del HTML de HLTV")
    return resultados


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    datos = scrape_hltv_local()
    print(f"\nTotal: {len(datos)} jugadores")
    if datos:
        print(json.dumps(datos[0], indent=2, ensure_ascii=False))