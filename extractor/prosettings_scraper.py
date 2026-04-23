# extractors/prosettings_scraper.py

import time
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

URL_CS2 = "https://prosettings.net/lists/cs2/"

HEADERS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Columnas que esperamos encontrar en el thead.
# Si ProSettings agrega o renombra columnas, el scraper avisa en lugar de fallar silenciosamente.
COLUMNAS_ESPERADAS = {
    "team", "player", "role", "mouse", "hz", "dpi",
    "sens", "edpi", "zoom_sens", "monitor", "gpu",
    "resolution", "aspect_ratio", "scaling_mode",
    "mousepad", "keyboard", "headset", "chair"
}


# ── HTML ──────────────────────────────────────────────────────────────────────

def _obtener_html(url: str, reintentos: int = 3, espera: float = 2.0) -> str | None:
    """
    Descarga el HTML con reintentos y backoff exponencial.
    Retorna el texto HTML o None si todos los intentos fallan.
    """
    for intento in range(1, reintentos + 1):
        try:
            respuesta = requests.get(url, headers=HEADERS_HTTP, timeout=15)
            respuesta.raise_for_status()
            logger.info(f"HTML descargado OK (intento {intento}): {url}")
            return respuesta.text
        except requests.HTTPError as e:
            logger.error(f"HTTP {e.response.status_code} en {url} (intento {intento})")
        except requests.RequestException as e:
            logger.warning(f"Error de red en {url} (intento {intento}): {e}")

        if intento < reintentos:
            tiempo = espera * (2 ** (intento - 1))  # 2s → 4s → 8s
            logger.info(f"Reintentando en {tiempo:.0f}s...")
            time.sleep(tiempo)

    logger.error(f"Todos los intentos fallaron para: {url}")
    return None


# ── Parseo de celdas ──────────────────────────────────────────────────────────

def _texto_limpio(td) -> str:
    """Extrae el texto visible de una celda, eliminando espacios y saltos."""
    return td.get_text(separator=" ", strip=True)


def _parsear_celda_player(td) -> dict:
    """
    La celda de jugador tiene esta estructura:
      <td>
        France         ← texto del país (nodo de texto suelto)
        <a href="/players/zywoo/">ZywOo</a>
      </td>
    Retorna {"player_name": "ZywOo", "player_country": "France", "player_url": "/players/zywoo/"}
    """
    a = td.find("a")
    if not a:
        return {"player_name": _texto_limpio(td), "player_country": None, "player_url": None}

    # El país es el texto del nodo anterior al <a>
    country_node = a.previous_sibling
    country = country_node.strip() if country_node and isinstance(country_node, str) else None

    return {
        "player_name": a.get_text(strip=True),
        "player_country": country,
        "player_url": a.get("href"),
    }


def _parsear_celda_team(td) -> dict:
    """
    La celda de equipo tiene texto duplicado dentro del <a> (nombre aparece dos veces en el HTML).
    Solo tomamos el href y el texto del link.
      <a href="/teams/team-vitality/">Team VitalityTeam Vitality</a>
    """
    a = td.find("a")
    if not a:
        return {"team_name": _texto_limpio(td), "team_url": None}

    # El texto viene duplicado: "Team VitalityTeam Vitality"
    # Nos quedamos con la primera mitad
    texto = a.get_text(strip=True)
    mitad = len(texto) // 2
    nombre = texto[:mitad] if texto[:mitad] == texto[mitad:] else texto

    return {
        "team_name": nombre,
        "team_url": a.get("href"),
    }


def _parsear_celda_gear(td) -> dict[str, str | None]:
    """
    Celdas de equipo (mouse, monitor, etc.): tienen un <a> con el nombre del producto
    y el href lleva al detalle. Retorna nombre y URL.
    """
    a = td.find("a")
    if not a:
        texto = _texto_limpio(td)
        return {"nombre": texto or None, "url": None}
    return {
        "nombre": a.get_text(strip=True) or None,
        "url": a.get("href"),
    }


# ── Parseo de tabla ───────────────────────────────────────────────────────────

def _normalizar_header(texto: str) -> str:
    """'Zoom Sens' → 'zoom_sens', 'eDPI' → 'edpi'"""
    return texto.strip().lower().replace(" ", "_")


def _parsear_headers(tabla) -> list[str]:
    thead = tabla.find("thead")
    if not thead:
        raise ValueError("La tabla no tiene <thead>")
    return [_normalizar_header(th.get_text(strip=True)) for th in thead.find_all("th")]


def _validar_columnas(headers: list[str]) -> None:
    """Avisa si hay columnas nuevas o columnas que desaparecieron."""
    actuales = set(headers) - {""}   # la primer columna es un índice vacío
    nuevas = actuales - COLUMNAS_ESPERADAS
    faltantes = COLUMNAS_ESPERADAS - actuales

    if nuevas:
        logger.warning(f"Columnas nuevas detectadas en ProSettings: {nuevas}")
    if faltantes:
        logger.warning(f"Columnas que ya no están en ProSettings: {faltantes}")


def _parsear_fila(tr, headers: list[str]) -> dict | None:
    """
    Convierte un <tr> en un dict enriquecido.
    Retorna None si la fila no tiene el número esperado de celdas.
    """
    celdas = tr.find_all("td")

    if len(celdas) != len(headers):
        if celdas:  # fila no vacía pero con largo incorrecto
            logger.warning(f"Fila descartada: {len(celdas)} celdas, se esperaban {len(headers)}")
        return None

    fila = {}
    for header, td in zip(headers, celdas):
        if header == "player":
            fila.update(_parsear_celda_player(td))
        elif header == "team":
            fila.update(_parsear_celda_team(td))
        elif header in ("mouse", "monitor", "mousepad", "keyboard", "headset", "chair", "gpu"):
            gear = _parsear_celda_gear(td)
            fila[header] = gear["nombre"]
            fila[f"{header}_url"] = gear["url"]
        else:
            # Campos simples: hz, dpi, sens, edpi, zoom_sens, resolution, etc.
            fila[header] = _texto_limpio(td) or None

    return fila


def _parsear_tabla(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    tabla = soup.find("table", id="pro-list-table")
    if tabla is None:
        logger.error("No se encontró #pro-list-table en el HTML")
        return []

    headers = _parsear_headers(tabla)
    _validar_columnas(headers)

    tbody = tabla.find("tbody")
    if not tbody:
        logger.error("La tabla no tiene <tbody>")
        return []

    filas = []
    for tr in tbody.find_all("tr"):
        fila = _parsear_fila(tr, headers)
        if fila:
            filas.append(fila)

    logger.info(f"{len(filas)} jugadores extraidos de ProSettings")
    return filas


# ── API pública ───────────────────────────────────────────────────────────────

def scrape_prosettings(url: str = URL_CS2) -> list[dict]:
    """
    Punto de entrada principal.
    Retorna lista de dicts con un registro por jugador.
    Ejemplo de registro:
    {
        "player_name":    "ZywOo",
        "player_country": "France",
        "player_url":     "https://prosettings.net/players/zywoo/",
        "team_name":      "Team Vitality",
        "team_url":       "https://prosettings.net/teams/team-vitality/",
        "role":           "Sniper",
        "mouse":          "Pulsar ZywOo The Chosen Mouse White",
        "mouse_url":      "https://amzn.to/...",
        "hz":             "1000",
        "dpi":            "400",
        "sens":           "2",
        "edpi":           "800.00",
        "zoom_sens":      "1",
        "monitor":        "ZOWIE XL2566K",
        "gpu":            "RTX 3080",
        "resolution":     "1280x960",
        "aspect_ratio":   "4:3",
        "scaling_mode":   "Stretched",
        ...
    }
    """
    html = _obtener_html(url)
    if html is None:
        return []
    return _parsear_tabla(html)


# ── Ejecución directa (smoke test) ────────────────────────────────────────────

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    datos = scrape_prosettings()

    if datos:
        print(f"\nTotal jugadores: {len(datos)}")
        print("\nPrimer registro:")
        print(json.dumps(datos[0], indent=2, ensure_ascii=False))
    else:
        print("No se obtuvieron datos.")