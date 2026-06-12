# dashboard/charts.py

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

DB_PATH = Path("data/cs2.db")

# ── Estilo ────────────────────────────────────────────────────────────────────

plt.rcParams.update({
    "figure.facecolor":  "#0a0c0f",
    "axes.facecolor":    "#111418",
    "axes.edgecolor":    "#1f2530",
    "axes.labelcolor":   "#64748b",
    "axes.titlecolor":   "#e2e8f0",
    "axes.titlesize":    11,
    "axes.titleweight":  "bold",
    "axes.grid":         True,
    "grid.color":        "#1a2030",
    "grid.linewidth":    0.5,
    "xtick.color":       "#64748b",
    "ytick.color":       "#64748b",
    "text.color":        "#e2e8f0",
    "font.family":       "monospace",
})

ACCENT  = "#e8ff47"
ACCENT2 = "#47c8ff"


# ── Data ──────────────────────────────────────────────────────────────────────

def _cargar(scope: str = "all") -> pd.DataFrame:
    """
    scope = "all"  → todos los jugadores de ProSettings
    scope = "hltv" → solo los 91 del ranking HLTV
    """
    conn = sqlite3.connect(DB_PATH)

    if scope == "hltv":
        df = pd.read_sql("""
            SELECT s.dpi, s.edpi, s.aspect_ratio, s.resolution, s.scaling_mode
            FROM hltv_stats h
            JOIN players p  ON LOWER(h.player_name) = LOWER(p.player_name)
            JOIN settings s ON p.player_url = s.player_url
        """, conn)
    else:
        df = pd.read_sql("""
            SELECT s.dpi, s.edpi, s.aspect_ratio, s.resolution, s.scaling_mode
            FROM players p
            JOIN settings s ON p.player_url = s.player_url
        """, conn)

    conn.close()
    return df


# ── Gráficos ──────────────────────────────────────────────────────────────────

def grafico_dpi(ax, df: pd.DataFrame) -> None:
    data = (
        df["dpi"].dropna().astype(int)
        .value_counts().sort_index()
    )
    ax.bar(data.index.astype(str), data.values, color=ACCENT, width=0.6, zorder=2)
    ax.set_title("DPI más usados")
    ax.set_xlabel("DPI")
    ax.set_ylabel("Jugadores")
    ax.tick_params(axis="x", rotation=45)


def grafico_edpi(ax, df: pd.DataFrame) -> None:
    data = (
        df["edpi"].dropna()
        .astype(int)
        .value_counts()
        .head(10)
        .sort_index()
    )
    ax.bar(data.index.astype(str), data.values, color=ACCENT2, width=0.6, zorder=2)
    ax.set_title("eDPI más usados (Top 10)")
    ax.set_xlabel("eDPI")
    ax.set_ylabel("Jugadores")
    ax.tick_params(axis="x", rotation=45)

    # Valor encima de cada barra
    for x, val in zip(range(len(data)), data.values):
        ax.text(x, val + 0.2, str(val), ha="center", fontsize=8, color="#94a3b8")


def grafico_aspect_ratio(ax, df: pd.DataFrame) -> None:
    data = df["aspect_ratio"].dropna().value_counts().head(6)
    bars = ax.barh(data.index[::-1], data.values[::-1],
                   color=ACCENT, zorder=2, height=0.6)
    ax.set_title("Relaciones de aspecto")
    ax.set_xlabel("Jugadores")

    # Labels al final de cada barra
    for bar, val in zip(bars, data.values[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=8, color="#94a3b8")


def grafico_resoluciones(ax, df: pd.DataFrame) -> None:
    data = df["resolution"].dropna().value_counts().head(10)
    bars = ax.barh(data.index[::-1], data.values[::-1],
                   color=ACCENT2, zorder=2, height=0.6)
    ax.set_title("Resoluciones más usadas")
    ax.set_xlabel("Jugadores")

    for bar, val in zip(bars, data.values[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=8, color="#94a3b8")


def grafico_scaling(ax, df: pd.DataFrame) -> None:
    data = df["scaling_mode"].dropna().value_counts()
    colors = [ACCENT, ACCENT2, "#ff6b6b", "#a78bfa", "#fb923c"]
    wedges, texts, autotexts = ax.pie(
        data.values,
        labels=data.index,
        autopct="%1.0f%%",
        colors=colors[:len(data)],
        startangle=90,
        wedgeprops=dict(linewidth=1.5, edgecolor="#0a0c0f"),
        pctdistance=0.75,
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_color("#0a0c0f")
    ax.set_title("Scaling mode")


# ── Render ────────────────────────────────────────────────────────────────────

def mostrar_graficos(scope: str = "all") -> None:
    """
    scope: "all" | "hltv"
    """
    df = _cargar(scope)
    label = "Top 91 HLTV" if scope == "hltv" else f"Todos ({len(df)} jugadores)"

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle(f"CS2 Pro Settings — {label}",
                 fontsize=14, fontweight="bold", color="#e2e8f0", y=0.98)
    fig.patch.set_facecolor("#0a0c0f")

    grafico_dpi(axes[0, 0], df)
    grafico_edpi(axes[0, 1], df)
    grafico_aspect_ratio(axes[0, 2], df)
    grafico_resoluciones(axes[1, 0], df)
    grafico_scaling(axes[1, 1], df)

    # Último panel: stats resumen
    ax_info = axes[1, 2]
    ax_info.axis("off")
    stats = [
        ("Jugadores",    str(len(df))),
        ("DPI mediano",  str(int(df['dpi'].median())) if df['dpi'].notna().any() else "—"),
        ("eDPI mediano", str(int(df['edpi'].median())) if df['edpi'].notna().any() else "—"),
        ("Res. top",     df['resolution'].value_counts().index[0] if df['resolution'].notna().any() else "—"),
        ("AR top",       df['aspect_ratio'].value_counts().index[0] if df['aspect_ratio'].notna().any() else "—"),
        ("Scaling top",  df['scaling_mode'].value_counts().index[0] if df['scaling_mode'].notna().any() else "—"),
    ]
    for i, (label_s, val) in enumerate(stats):
        y = 0.85 - i * 0.14
        ax_info.text(0.05, y, label_s.upper(),
             fontsize=7, color="#64748b", transform=ax_info.transAxes,
             fontweight="bold")
        ax_info.text(0.05, y - 0.06, val,
                     fontsize=13, color=ACCENT, transform=ax_info.transAxes,
                     fontweight="bold", fontfamily="monospace")

    plt.tight_layout()
    plt.show()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("1 — Todos los jugadores (ProSettings)")
    print("2 — Top 91 HLTV")
    opcion = input("Elegí una opción: ").strip()
    scope = "hltv" if opcion == "2" else "all"
    mostrar_graficos(scope)