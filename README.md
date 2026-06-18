# fraghub 🎯

Pipeline ETL + visualizaciones para analizar configuraciones y estadísticas de jugadores profesionales de CS2.

## ¿Qué hace?

Extrae datos de [ProSettings](https://prosettings.net/lists/cs2/) — mouse, DPI, sensitivity, monitor, resolución y más — de 800+ jugadores profesionales, y los cruza con el ranking de rating de [HLTV](https://www.hltv.org/stats) (top 100 jugadores). Todo se transforma y carga en una base de datos SQLite lista para análisis.

## Stack

| Capa | Tecnología |
|---|---|
| Extracción | `requests` + `BeautifulSoup` |
| Transformación | `pandas` |
| Carga | `SQLite3` |
| Visualización | `matplotlib` + `Streamlit` |

## Estructura

```
fraghub/
├── extractor/
│   ├── prosettings_scraper.py   # scraping de ProSettings
│   └── hltv_scraper.py          # parseo de HTML local de HLTV
├── transformer/
│   └── transform_prosettings.py # limpieza y normalización
├── loader/
│   └── sqlite_loader.py         # carga a SQLite
├── dashboard/
│   ├── charts.py                # gráficos estáticos con matplotlib
│   └── app.py                   # dashboard interactivo con Streamlit
├── data/
│   ├── cs2.db                   # base de datos generada (no versionada)
│   └── HLTV.html                # HTML descargado manualmente de HLTV
└── main.py                      # orquestador del pipeline
```

## Instalación

```bash
git clone https://github.com/lucastisocco/fraghub.git
cd fraghub
pip install requests beautifulsoup4 pandas matplotlib streamlit plotly
```

## Uso

### 1. Pipeline ETL

```bash
python main.py
```

El pipeline tarda ~5 segundos. Al finalizar, `data/cs2.db` contiene cuatro tablas:

- **`players`** — nombre, país, equipo, rol
- **`settings`** — DPI, sensitivity, eDPI, resolución, aspect ratio
- **`gear`** — mouse, monitor, GPU, mousepad, teclado, headset, silla
- **`hltv_stats`** — rating, K/D, K/D diff, mapas y rondas jugadas (top 100 HLTV)

> **Nota sobre HLTV:** dado que HLTV usa Cloudflare y bloquea el scraping automático, los datos se obtienen descargando manualmente el HTML de [esta página](https://www.hltv.org/stats/players?startDate=2024-01-01&endDate=2024-12-31&rankingFilter=Top50) y guardándolo en `data/HLTV.html`.

### 2. Gráficos estáticos

```bash
python dashboard/charts.py
```

Te pide elegir el alcance de los datos:

- **Todos los jugadores** (ProSettings completo, ~900 jugadores)
- **Top HLTV** (solo jugadores con mejor rating)

Y genera un panel con 5 gráficos + resumen de estadísticas:

- DPI más usados
- eDPI más usados (Top 10)
- Relaciones de aspecto
- Resoluciones más usadas
- Scaling mode

### 3. Dashboard interactivo

```bash
python -m streamlit run dashboard/app.py
```

Incluye ranking de jugadores con link a ProSettings, filtro por scope y los mismos gráficos en formato interactivo.

## Schema

```sql
players    (player_url PK, player_name, player_country, team_name, team_url, role)
settings   (player_url PK/FK, hz, dpi, sens, edpi, zoom_sens, resolution, aspect_ratio, scaling_mode)
gear       (player_url PK/FK, mouse, monitor, gpu, mousepad, keyboard, headset, chair)
hltv_stats (player_name PK, country, team_name, team_url, player_url, maps, rounds, kd_diff, kd, rating, scraped_date)
```

El join entre `hltv_stats` y `players` se hace por nombre normalizado (`LOWER()`), ya que ambas fuentes pueden diferir en capitalización.

## Roadmap

- [x] Scraper ProSettings
- [x] Transformación y carga SQLite
- [x] Integración HLTV (HTML local)
- [x] Visualizaciones con matplotlib
- [x] Dashboard interactivo con Streamlit
- [ ] Actualización automática programada
