# main.py

import logging
from extractor.prosettings_scraper import scrape_prosettings
from transformer.transform_prosettings import transformar
from loader.sqlite_loader import cargar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def main():
    # Extract
    datos_crudos = scrape_prosettings()
    if not datos_crudos:
        return

    # Transform
    tablas = transformar(datos_crudos)

    # Load
    cargar(tablas)

if __name__ == "__main__":
    main()