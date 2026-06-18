# main.py

import logging
from extractors.prosettings_scraper import scrape_prosettings
from extractors.hltv_scraper import scrape_hltv_local
from transformers.transform_prosettings import transformar
from loaders.sqlite_loader import cargar, cargar_hltv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def main():
    # ── ProSettings ───────────────────────────────────────────────────────────
    datos_ps = scrape_prosettings()
    if datos_ps:
        tablas = transformar(datos_ps)
        cargar(tablas)

    # ── HLTV (HTML local) ─────────────────────────────────────────────────────
    datos_hltv = scrape_hltv_local()
    if datos_hltv:
        cargar_hltv(datos_hltv, scraped_date="2026-06-18")

if __name__ == "__main__":
    main()