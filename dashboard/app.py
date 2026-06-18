# dashboard/app.py

import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="fraghub",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB_PATH = Path("data/cs2.db")

ACCENT  = "#e8ff47"
ACCENT2 = "#47c8ff"

PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Barlow, sans-serif", color="#94a3b8", size=12),
    margin=dict(t=32, b=32, l=16, r=16),
    xaxis=dict(gridcolor="#1a2030", linecolor="#1f2530", tickcolor="#1f2530"),
    yaxis=dict(gridcolor="#1a2030", linecolor="#1f2530", tickcolor="#1f2530"),
)

# ── Theme ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=Barlow:wght@300;400;500&display=swap');

:root {
    --bg:        #0a0c0f;
    --surface:   #111418;
    --surface2:  #181c22;
    --border:    #1f2530;
    --accent:    #e8ff47;
    --accent2:   #47c8ff;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --danger:    #ff4747;
}

html, body, [data-testid="stApp"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Barlow', sans-serif;
}
.fh-header {
    display: flex;
    align-items: baseline;
    gap: 12px;
    padding: 32px 0 8px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 28px;
}
.fh-logo {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -1px;
    color: var(--accent);
    text-transform: uppercase;
    line-height: 1;
}
.fh-sub {
    font-size: 0.85rem;
    color: var(--muted);
    letter-spacing: 2px;
    text-transform: uppercase;
}
[data-testid="stTabs"] button {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    color: var(--muted) !important;
    border: none !important;
    padding: 10px 20px !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}
.metric-row {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
}
.metric-card {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
}
.metric-label {
    font-size: 0.7rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 4px;
}
.metric-value {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
}
.rank-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
}
.rank-table thead tr { border-bottom: 1px solid var(--border); }
.rank-table thead th {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.72rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
}
.rank-table tbody tr {
    border-bottom: 1px solid #151920;
    transition: background 0.15s;
}
.rank-table tbody tr:hover { background: var(--surface2); }
.rank-table td { padding: 10px 12px; color: var(--text); }
.rank-num { color: var(--muted); font-size: 0.8rem; width: 36px; }
.rank-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.rank-name a { color: var(--text); text-decoration: none; }
.rank-name a:hover { color: var(--accent); }
.rank-team { color: var(--muted); font-size: 0.82rem; }
.rating-high { color: var(--accent); font-weight: 600; }
.rating-mid  { color: var(--accent2); }
.rating-low  { color: var(--muted); }
.kd-pos { color: #4ade80; }
.kd-neg { color: var(--danger); }
.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def cargar_datos():
    conn = sqlite3.connect(DB_PATH)

    ranking = pd.read_sql("""
        SELECT
            ROW_NUMBER() OVER (ORDER BY h.rating DESC) AS rank,
            h.player_name,
            h.country,
            h.team_name,
            h.maps,
            h.rounds,
            h.kd,
            h.kd_diff,
            h.rating,
            p.player_url,
            p.role,
            s.dpi,
            s.sens,
            s.edpi,
            s.resolution,
            s.aspect_ratio,
            s.scaling_mode,
            g.mouse,
            g.monitor
        FROM hltv_stats h
        LEFT JOIN players p  ON LOWER(h.player_name) = LOWER(p.player_name)
        LEFT JOIN settings s ON p.player_url = s.player_url
        LEFT JOIN gear g     ON p.player_url = g.player_url
        ORDER BY h.rating DESC
    """, conn)

    todos = pd.read_sql("""
        SELECT
            p.player_name,
            p.team_name,
            p.role,
            s.dpi,
            s.sens,
            s.edpi,
            s.resolution,
            s.aspect_ratio,
            s.scaling_mode
        FROM players p
        JOIN settings s ON p.player_url = s.player_url
    """, conn)

    conn.close()
    return ranking, todos


ranking_df, todos_df = cargar_datos()
hltv_settings = ranking_df.dropna(subset=["dpi"])

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="fh-header">
    <span class="fh-logo">fraghub</span>
    <span class="fh-sub">CS2 Pro Player Analytics</span>
</div>
""", unsafe_allow_html=True)

# ── Metrics ───────────────────────────────────────────────────────────────────

avg_dpi  = todos_df["dpi"].median()
avg_edpi = todos_df["edpi"].mean()
top_res  = todos_df["resolution"].value_counts().index[0] if not todos_df["resolution"].isna().all() else "—"
top_ar   = todos_df["aspect_ratio"].value_counts().index[0] if not todos_df["aspect_ratio"].isna().all() else "—"

st.markdown(f"""
<div class="metric-row">
    <div class="metric-card">
        <div class="metric-label">Jugadores tracked</div>
        <div class="metric-value">{len(todos_df)}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">DPI mediano</div>
        <div class="metric-value">{int(avg_dpi) if pd.notna(avg_dpi) else '—'}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">eDPI medio</div>
        <div class="metric-value">{int(avg_edpi) if pd.notna(avg_edpi) else '—'}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Resolución top</div>
        <div class="metric-value" style="font-size:1.3rem">{top_res}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Aspect ratio top</div>
        <div class="metric-value">{top_ar}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_ranking, tab_stats = st.tabs(["🏆  Ranking", "📊  Settings & Gear"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — RANKING
# ════════════════════════════════════════════════════════════════════════════

with tab_ranking:

    def rating_class(r):
        if r >= 1.20: return "rating-high"
        if r >= 1.00: return "rating-mid"
        return "rating-low"

    def kd_class(kd):
        return "kd-pos" if kd and float(kd) >= 1.0 else "kd-neg"

    rows = ""
    for _, row in ranking_df.iterrows():
        url      = row["player_url"] or "#"
        ps_link  = f'<a href="{url}" target="_blank">{row["player_name"]}</a>' if url != "#" else row["player_name"]
        r        = float(row["rating"]) if pd.notna(row["rating"]) else 0
        kd       = float(row["kd"]) if pd.notna(row["kd"]) else None
        diff     = int(row["kd_diff"]) if pd.notna(row["kd_diff"]) else None
        diff_str = f'+{diff}' if diff and diff > 0 else str(diff) if diff else "—"

        dpi_str  = f'{int(row["dpi"])}'  if pd.notna(row.get("dpi"))        else '<span style="color:#2a3040">—</span>'
        edpi_str = f'{int(row["edpi"])}' if pd.notna(row.get("edpi"))       else '<span style="color:#2a3040">—</span>'
        res_str  = row["resolution"]     if pd.notna(row.get("resolution")) else '<span style="color:#2a3040">—</span>'

        rows += f"""
        <tr>
            <td class="rank-num">{int(row['rank'])}</td>
            <td class="rank-name">{ps_link}</td>
            <td class="rank-team">{row['team_name'] or '—'}</td>
            <td class="rank-team">{row['country'] or '—'}</td>
            <td>{row['maps'] or '—'}</td>
            <td class="{kd_class(kd)}">{kd or '—'}</td>
            <td style="color:#475569">{diff_str}</td>
            <td class="{rating_class(r)}">{r:.2f}</td>
            <td style="color:#94a3b8">{dpi_str}</td>
            <td style="color:#94a3b8">{edpi_str}</td>
            <td style="color:#64748b; font-size:0.8rem">{res_str}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="rank-table">
          <thead>
            <tr>
              <th>#</th><th>Player</th><th>Team</th><th>Country</th>
              <th>Maps</th><th>K/D</th><th>K/D Diff</th><th>Rating</th>
              <th>DPI</th><th>eDPI</th><th>Resolution</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — SETTINGS & GEAR
# ════════════════════════════════════════════════════════════════════════════

with tab_stats:

    st.markdown('<div class="section-title">Filtro de jugadores</div>', unsafe_allow_html=True)
    scope = st.radio(
        "Filtro",
        ["Todos los jugadores (ProSettings)", "Top HLTV"],
        horizontal=True,
        label_visibility="collapsed",
    )

    df_plot = hltv_settings if scope == "Top HLTV" else todos_df
    st.caption(f"{len(df_plot)} jugadores en la selección actual")
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-title">DPI más usados</div>', unsafe_allow_html=True)
        dpi_data = (
            df_plot["dpi"].dropna().astype(int)
            .value_counts().sort_index().reset_index()
        )
        dpi_data.columns = ["DPI", "Jugadores"]
        fig_dpi = go.Figure(go.Bar(
            x=dpi_data["DPI"].astype(str),
            y=dpi_data["Jugadores"],
            marker_color=ACCENT,
            marker_line_width=0,
            hovertemplate="<b>%{x} DPI</b><br>%{y} jugadores<extra></extra>",
        ))
        fig_dpi.update_layout(**PLOTLY_THEME, height=300)
        st.plotly_chart(fig_dpi, width="stretch", config={"displayModeBar": False})

    with col2:
        st.markdown('<div class="section-title">eDPI más usados (Top 10)</div>', unsafe_allow_html=True)
        edpi_data = (
            df_plot["edpi"].dropna().astype(int)
            .value_counts().head(10).sort_index().reset_index()
        )
        edpi_data.columns = ["eDPI", "Jugadores"]
        fig_edpi = go.Figure(go.Bar(
            x=edpi_data["eDPI"].astype(str),
            y=edpi_data["Jugadores"],
            marker_color=ACCENT2,
            marker_line_width=0,
            hovertemplate="<b>eDPI %{x}</b><br>%{y} jugadores<extra></extra>",
        ))
        fig_edpi.update_layout(**PLOTLY_THEME, height=300)
        st.plotly_chart(fig_edpi, width="stretch", config={"displayModeBar": False})

    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<div class="section-title">Relaciones de aspecto</div>', unsafe_allow_html=True)
        ar_data = (
            df_plot["aspect_ratio"].dropna()
            .value_counts().head(8).reset_index()
        )
        ar_data.columns = ["Aspect Ratio", "Jugadores"]
        fig_ar = go.Figure(go.Bar(
            x=ar_data["Jugadores"],
            y=ar_data["Aspect Ratio"],
            orientation="h",
            marker_color=ACCENT,
            marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>%{x} jugadores<extra></extra>",
        ))
        fig_ar.update_layout(**PLOTLY_THEME, height=300)
        fig_ar.update_yaxes(autorange="reversed", gridcolor="#1a2030")
        st.plotly_chart(fig_ar, width="stretch", config={"displayModeBar": False})

    with col4:
        st.markdown('<div class="section-title">Resoluciones más usadas</div>', unsafe_allow_html=True)
        res_data = (
            df_plot["resolution"].dropna()
            .value_counts().head(10).reset_index()
        )
        res_data.columns = ["Resolución", "Jugadores"]
        fig_res = go.Figure(go.Bar(
            x=res_data["Jugadores"],
            y=res_data["Resolución"],
            orientation="h",
            marker_color=ACCENT2,
            marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>%{x} jugadores<extra></extra>",
        ))
        fig_res.update_layout(**PLOTLY_THEME, height=350)
        fig_res.update_yaxes(autorange="reversed", gridcolor="#1a2030")
        st.plotly_chart(fig_res, width="stretch", config={"displayModeBar": False})

    st.markdown('<div class="section-title">Scaling mode</div>', unsafe_allow_html=True)
    scale_data = (
        df_plot["scaling_mode"].dropna()
        .value_counts().reset_index()
    )
    scale_data.columns = ["Scaling Mode", "Jugadores"]
    colors = [ACCENT, ACCENT2, "#ff6b6b", "#a78bfa", "#fb923c"]
    fig_scale = go.Figure(go.Pie(
        labels=scale_data["Scaling Mode"],
        values=scale_data["Jugadores"],
        hole=0.6,
        marker=dict(colors=colors[:len(scale_data)], line=dict(color="#0a0c0f", width=2)),
        hovertemplate="<b>%{label}</b><br>%{value} jugadores (%{percent})<extra></extra>",
        textfont=dict(family="Barlow Condensed", size=13),
    ))
    fig_scale.update_layout(**PLOTLY_THEME, height=280,
                            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"))
    st.plotly_chart(fig_scale, width="stretch", config={"displayModeBar": False})