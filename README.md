# fraghub 🎯

Pipeline ETL + dashboard para analizar configuraciones y estadísticas de jugadores profesionales de CS2.

## ¿Qué hace?

Extrae datos de [ProSettings](https://prosettings.net/lists/cs2/) — mouse, DPI, sensitivity, monitor, resolución y más — de 800+ jugadores profesionales, los transforma y los carga en una base de datos SQLite lista para análisis.

## Stack

| Capa | Tecnología |
|---|---|
| Extracción | `requests` + `BeautifulSoup` |
| Transformación | `pandas` |
| Carga | `SQLite3` |
| Dashboard | `Streamlit` (próximamente) |

## Estructura

```
fraghub/
├── extractor/
│   └── prosettings_scraper.py   # scraping de ProSettings
├── transformer/
│   └── transform_prosettings.py # limpieza y normalización
├── loader/
│   └── sqlite_loader.py         # carga a SQLite
├── data/
│   └── cs2.db                   # base de datos generada (no versionada)
└── main.py                      # orquestador del pipeline
```

## Instalación

```bash
git clone https://github.com/lucastisocco/fraghub.git
cd fraghub
pip install requests beautifulsoup4 pandas
```

## Uso

```bash
python main.py
```

El pipeline completo tarda ~5 segundos. Al finalizar, `data/cs2.db` contiene tres tablas:

- **`players`** — nombre, país, equipo, rol
- **`settings`** — DPI, sensitivity, eDPI, resolución, aspect ratio
- **`gear`** — mouse, monitor, GPU, mousepad, teclado, headset, silla

## Schema

```sql
players  (player_url PK, player_name, player_country, team_name, team_url, role)
settings (player_url PK/FK, hz, dpi, sens, edpi, zoom_sens, resolution, aspect_ratio, scaling_mode)
gear     (player_url PK/FK, mouse, monitor, gpu, mousepad, keyboard, headset, chair)
```

## Roadmap

- [x] Scraper ProSettings
- [x] Transformación y carga SQLite
- [ ] Dashboard Streamlit
- [ ] Scraper segunda fuente (estadísticas de juego)
- [ ] Actualización automática programada