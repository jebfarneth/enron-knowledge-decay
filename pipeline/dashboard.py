import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Knowledge & Code",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global reset ─────────────────────────────── */
html, body, [class*="css"], .stApp,
.stApp > div, section.main, .main > div {
    font-family: 'Times New Roman', Times, serif !important;
    background-color: #F5F5F7 !important;
    color: #1D1D1F !important;
}
.block-container {
    padding: 2.5rem 3rem 3rem 3rem !important;
    max-width: 1300px !important;
}

/* ── Typography ───────────────────────────────── */
h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
.stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
    font-family: 'Times New Roman', Times, serif !important;
    color: #1D1D1F !important;
    font-weight: normal !important;
    letter-spacing: -0.01em;
}
p, span, label, div, li, td, th,
.stMarkdown p, .stText {
    font-family: 'Times New Roman', Times, serif !important;
}

/* ── Metrics ──────────────────────────────────── */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #D1D1D6;
    border-radius: 14px;
    padding: 1.25rem 1.6rem;
}
[data-testid="stMetricLabel"] > div,
[data-testid="stMetricLabel"] > div > div {
    font-family: 'Times New Roman', Times, serif !important;
    font-size: 0.76rem !important;
    color: #6E6E73 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
[data-testid="stMetricValue"] > div {
    font-family: 'Times New Roman', Times, serif !important;
    font-size: 2.1rem !important;
    color: #1D1D1F !important;
    font-weight: normal !important;
}

/* ── Tabs ─────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background-color: #F5F5F7;
    border-bottom: 1px solid #D1D1D6;
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Times New Roman', Times, serif !important;
    font-size: 1rem !important;
    color: #86868B !important;
    background-color: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.85rem 2rem !important;
    margin-bottom: -1px;
}
.stTabs [aria-selected="true"] {
    color: #1D1D1F !important;
    border-bottom: 2px solid #1D1D1F !important;
    background-color: transparent !important;
}

/* ── Sidebar ──────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #D1D1D6 !important;
}
[data-testid="stSidebar"] * {
    font-family: 'Times New Roman', Times, serif !important;
    color: #1D1D1F !important;
}

/* ── Selectbox ────────────────────────────────── */
[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid #D1D1D6 !important;
    border-radius: 8px !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] * {
    font-family: 'Times New Roman', Times, serif !important;
    color: #1D1D1F !important;
}
/* Dropdown menu */
[data-baseweb="popover"] * {
    font-family: 'Times New Roman', Times, serif !important;
    background-color: #FFFFFF !important;
}

/* ── DataFrames ───────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #D1D1D6 !important;
    border-radius: 10px !important;
}
.dvn-scroller,
.dvn-scroller * {
    font-family: 'Times New Roman', Times, serif !important;
}

/* ── Dividers ─────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid #D1D1D6 !important;
    margin: 1.5rem 0 !important;
}

/* ── Hide Streamlit chrome ────────────────────── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Palette & layout helpers ───────────────────────────────────────────────────
C = dict(
    ink    = "#1D1D1F",
    dark   = "#424245",
    mid    = "#6E6E73",
    light  = "#86868B",
    border = "#D1D1D6",
    bg     = "#F5F5F7",
    white  = "#FFFFFF",
)

def _base_layout(**overrides) -> dict:
    """Common Plotly layout kwargs — extend per-chart as needed."""
    d = dict(
        paper_bgcolor = C["bg"],
        plot_bgcolor  = C["bg"],
        font          = dict(family="Times New Roman, Times, serif", color=C["ink"]),
        margin        = dict(l=48, r=24, t=40, b=48),
        showlegend    = False,
        hoverlabel    = dict(
            bgcolor     = C["white"],
            font_family = "Times New Roman, Times, serif",
            font_color  = C["ink"],
            bordercolor = C["border"],
        ),
    )
    d.update(overrides)
    return d

def _ax(**kw) -> dict:
    """Common axis styling."""
    base = dict(
        gridcolor = C["border"],
        linecolor = C["border"],
        tickfont  = dict(family="Times New Roman, Times, serif", color=C["mid"]),
        title_font= dict(family="Times New Roman, Times, serif", color=C["dark"]),
        zeroline  = False,
    )
    base.update(kw)
    return base

def _section(text: str):
    st.markdown(
        f"<h3 style='font-size:1.05rem; color:{C['ink']}; font-weight:normal; "
        f"font-family:\"Times New Roman\",Times,serif; "
        f"margin-top:1.5rem; margin-bottom:0.4rem;'>{text}</h3>",
        unsafe_allow_html=True,
    )


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data
def load_risk_scores() -> pd.DataFrame:
    return pd.read_parquet("risk_scores.parquet")

@st.cache_data
def load_sim_dict() -> dict:
    with open("simulation_results.json") as f:
        data = json.load(f)
    return {r["person"]: r for r in data}

@st.cache_data
def load_vuln() -> pd.DataFrame:
    df = pd.read_parquet("topic_vulnerability.parquet")
    df["top3_parsed"] = df["top3_experts"].apply(json.loads)
    return df

@st.cache_data
def load_ep() -> pd.DataFrame:
    return pd.read_parquet("expertise_profiles.parquet")

@st.cache_data
def load_topic_words() -> dict:
    """Load BERTopic topic keywords if the saved model exists; else empty dict."""
    try:
        from bertopic import BERTopic  # noqa: PLC0415
        model_dir = Path("bertopic_model")
        if model_dir.exists():
            m = BERTopic.load(str(model_dir))
            return {
                int(row["Topic"]): [w for w, _ in m.get_topic(row["Topic"])[:6]]
                for _, row in m.get_topic_info().iterrows()
                if row["Topic"] != -1
            }
    except Exception:
        pass
    return {}

rs       = load_risk_scores()
sim_dict = load_sim_dict()
vuln     = load_vuln()
ep       = load_ep()
tw       = load_topic_words()

def topic_label(tid: int, max_words: int = 5) -> str:
    words = tw.get(int(tid), [])
    return ", ".join(words[:max_words]) if words else f"Topic {tid}"


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:1.75rem 0.5rem 2rem 0.5rem;">
      <div style="font-size:1.45rem; color:{C['ink']};
                  font-family:'Times New Roman',Times,serif; line-height:1.25;">
        Knowledge &amp; Code
      </div>
      <div style="font-size:0.80rem; color:{C['mid']}; margin-top:0.35rem;
                  font-family:'Times New Roman',Times,serif;">
        Organizational Intelligence Simulation
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown(f"""
    <div style="font-family:'Times New Roman',Times,serif;
                font-size:0.82rem; color:{C['mid']}; line-height:2.1;">
      <span style="color:{C['ink']}">{len(rs):,}</span>&nbsp; employees indexed<br>
      <span style="color:{C['ink']}">{len(sim_dict)}</span>&nbsp; departures simulated<br>
      <span style="color:{C['ink']}">{len(vuln)}</span>&nbsp; topics mapped
    </div>
    """, unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Person Detail",
    "Topic Vulnerability",
    "Simulation Playback",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── Summary metrics ───────────────────────────────────────────────────────
    n_critical    = int((rs["risk_score"] > 0.3).sum())
    n_vuln_topics = int((vuln["vulnerability_norm"] > 0.5).sum())
    avg_risk      = rs["risk_score"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Employees",   f"{len(rs):,}")
    c2.metric("Avg Risk Score",    f"{avg_risk:.3f}")
    c3.metric("Critical Risk",     f"{n_critical:,}")
    c4.metric("Vulnerable Topics", f"{n_vuln_topics}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Scatter: all employees ────────────────────────────────────────────────
    _section("Risk Landscape — All Employees")

    plot_df = rs.copy()
    # Log-normalise weighted_degree for dot size (range is enormous: 1 → 145k)
    log_wd  = np.log1p(plot_df["weighted_degree"].fillna(1).clip(lower=1))
    lo, hi  = log_wd.min(), log_wd.max()
    sizes   = 3 + (log_wd - lo) / max(hi - lo, 1e-9) * 18

    fig_scatter = go.Figure(go.Scatter(
        x    = plot_df["betweenness"],
        y    = plot_df["risk_score"],
        mode = "markers",
        marker=dict(
            size       = sizes,
            color      = plot_df["risk_score"],
            colorscale = [[0, C["border"]], [0.35, C["light"]], [0.7, C["dark"]], [1, C["ink"]]],
            showscale  = True,
            colorbar   = dict(
                title    = dict(text="Risk", font=dict(family="Times New Roman")),
                tickfont = dict(family="Times New Roman"),
                thickness= 10,
                len      = 0.55,
                x        = 1.01,
            ),
            line    = dict(width=0),
            opacity = 0.72,
        ),
        customdata = np.column_stack([
            plot_df["person"],
            plot_df["risk_score"].round(4),
            plot_df["betweenness"].round(6),
            plot_df["weighted_degree"].fillna(0).astype(int),
            plot_df["topics_top_expert"].fillna(0).astype(int),
        ]),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Risk: %{customdata[1]}<br>"
            "Betweenness: %{customdata[2]}<br>"
            "Weighted degree: %{customdata[3]:,}<br>"
            "Top-expert topics: %{customdata[4]}"
            "<extra></extra>"
        ),
    ))
    fig_scatter.update_layout(
        **_base_layout(height=500),
        xaxis = _ax(title="Betweenness Centrality"),
        yaxis = _ax(title="Risk Score"),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("---")

    # ── Top 50 table ──────────────────────────────────────────────────────────
    _section("Top 50 Highest-Risk People")

    top50 = (
        rs.nlargest(50, "risk_score")
        [["person", "risk_score", "betweenness", "weighted_degree"]]
        .copy()
    )
    top50["Recovery %"] = top50["person"].map(
        lambda p: f"{sim_dict[p]['final_recovery_score']:.1%}" if p in sim_dict else "—"
    )
    top50["Perm. Losses"] = top50["person"].map(
        lambda p: str(sim_dict[p].get("n_permanently_lost", "—")) if p in sim_dict else "—"
    )
    top50["Plateau"] = top50["person"].map(
        lambda p: (
            f"M{sim_dict[p]['plateau_month']}"
            if p in sim_dict and sim_dict[p].get("plateau_month")
            else "none"
        )
    )
    top50 = top50.rename(columns={
        "person":         "Name",
        "risk_score":     "Risk Score",
        "betweenness":    "Betweenness",
        "weighted_degree":"Wtd. Degree",
    })
    top50["Risk Score"]  = top50["Risk Score"].round(4)
    top50["Betweenness"] = top50["Betweenness"].round(5)
    top50["Wtd. Degree"] = top50["Wtd. Degree"].fillna(0).astype(int)

    st.dataframe(
        top50, use_container_width=True, hide_index=True,
        column_config={
            "Name":         st.column_config.TextColumn("Name",        width="large"),
            "Risk Score":   st.column_config.NumberColumn("Risk Score",format="%.4f"),
            "Betweenness":  st.column_config.NumberColumn("Betweenness", format="%.5f"),
            "Wtd. Degree":  st.column_config.NumberColumn("Wtd. Degree", format="%d"),
            "Recovery %":   st.column_config.TextColumn("Recovery %"),
            "Perm. Losses": st.column_config.TextColumn("Perm. Losses"),
            "Plateau":      st.column_config.TextColumn("Plateau"),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PERSON DETAIL
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:

    people_sorted = sorted(sim_dict.keys())
    sel = st.selectbox(
        "Person", people_sorted, key="sel_person",
        label_visibility="collapsed",
    )

    if sel and sel in sim_dict:
        sd = sim_dict[sel]

        st.markdown("<br>", unsafe_allow_html=True)

        # Metrics
        m1, m2, m3, _gap = st.columns([1, 1, 1, 2])
        m1.metric("Risk Score",     f"{sd['risk_score']:.4f}")
        m2.metric("Final Recovery", f"{sd['final_recovery_score']:.1%}")
        m3.metric("Perm. Lost",     str(sd.get("n_permanently_lost", 0)))

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Recovery curve ────────────────────────────────────────────────────
        _section("12-Month Recovery Curve")

        months = list(range(1, 13))
        rates  = sd["recovery_rates"]

        fig_line = go.Figure(go.Scatter(
            x    = months,
            y    = rates,
            mode = "lines+markers",
            line = dict(color=C["ink"], width=2.5),
            marker = dict(color=C["ink"], size=7, line=dict(width=0)),
            hovertemplate = "Month %{x}: %{y:.1%}<extra></extra>",
        ))
        if sd.get("plateau_month"):
            pm = sd["plateau_month"]
            fig_line.add_vline(
                x=pm, line_dash="dot", line_color=C["light"], line_width=1.2,
                annotation_text=f"Plateau  M{pm}",
                annotation_font=dict(family="Times New Roman", color=C["light"], size=11),
                annotation_position="top right",
            )
        fig_line.update_layout(
            **_base_layout(height=320),
            xaxis = _ax(title="Month", tickvals=months),
            yaxis = _ax(title="Recovery Quality", tickformat=".0%",
                        range=[-0.02, 1.05]),
        )
        st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("---")

        # ── Topic coverage table ──────────────────────────────────────────────
        _section("Topic Coverage")

        person_ep      = ep[ep["from"] == sel].sort_values("score", ascending=False)
        perm_lost_set  = {e["topic"] for e in sd.get("permanent_losses", [])}
        succ_analysis  = sd.get("successor_analysis", {})

        rows = []
        for _, row in person_ep.iterrows():
            tid  = int(row["topic"])
            scs  = succ_analysis.get(str(tid), [])
            best = scs[0] if scs else None

            if tid in perm_lost_set:
                status = "Lost"
            elif best and best["readiness"] >= 0.50:
                status = "Covered"
            elif best and best["readiness"] >= 0.25:
                status = "At Risk"
            else:
                status = "Vulnerable"

            rows.append({
                "Topic":          tid,
                "Keywords":       topic_label(tid),
                "Score":          round(float(row["score"]), 3),
                "Best Successor": best["candidate"].split("@")[0] if best else "—",
                "Readiness":      round(best["readiness"], 3) if best else None,
                "Status":         status,
            })

        st.dataframe(
            pd.DataFrame(rows), use_container_width=True, hide_index=True,
            column_config={
                "Topic":    st.column_config.NumberColumn("Topic",   width="small"),
                "Keywords": st.column_config.TextColumn("Keywords",  width="large"),
                "Score":    st.column_config.NumberColumn("Score",   format="%.3f"),
                "Best Successor": st.column_config.TextColumn("Best Successor"),
                "Readiness":      st.column_config.NumberColumn("Readiness", format="%.3f"),
                "Status":         st.column_config.TextColumn("Status"),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TOPIC VULNERABILITY
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    _section("Topic Vulnerability Map")

    vuln_table = vuln.copy()
    vuln_table["Top Words"]    = vuln_table["topic"].apply(topic_label)
    vuln_table["Top 3 Experts"] = vuln_table["top3_parsed"].apply(
        lambda lst: "  ·  ".join(e["from"].split("@")[0] for e in lst[:3])
    )
    vuln_table = (
        vuln_table[["topic", "Top Words", "n_experts", "hhi",
                    "vulnerability_norm", "Top 3 Experts"]]
        .rename(columns={
            "topic":            "Topic",
            "n_experts":        "# Experts",
            "hhi":              "HHI",
            "vulnerability_norm": "Vulnerability",
        })
        .sort_values("Vulnerability", ascending=False)
        .reset_index(drop=True)
    )

    def _vuln_style(row):
        v    = float(row["Vulnerability"])
        gray = int(245 - v * 185)           # 245 (light) → 60 (dark)
        bg   = f"rgb({gray},{gray},{gray})"
        fg   = "#F5F5F7" if v > 0.55 else "#1D1D1F"
        base = f"font-family:'Times New Roman',Times,serif; background-color:{bg}; color:{fg}"
        return [base] * len(row)

    styled = (
        vuln_table.style
        .apply(_vuln_style, axis=1)
        .format({"HHI": "{:.4f}", "Vulnerability": "{:.4f}"})
    )

    st.dataframe(
        styled, use_container_width=True, hide_index=True,
        column_config={
            "Topic":        st.column_config.NumberColumn("Topic",       width="small"),
            "Top Words":    st.column_config.TextColumn("Top Words",     width="large"),
            "# Experts":    st.column_config.NumberColumn("# Experts"),
            "HHI":          st.column_config.NumberColumn("HHI",         format="%.4f"),
            "Vulnerability":st.column_config.NumberColumn("Vulnerability",format="%.4f"),
            "Top 3 Experts":st.column_config.TextColumn("Top 3 Experts", width="large"),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SIMULATION PLAYBACK
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:

    sel4 = st.selectbox(
        "Person", sorted(sim_dict.keys()), key="sel_playback",
        label_visibility="collapsed",
    )

    if sel4 and sel4 in sim_dict:
        sd4    = sim_dict[sel4]
        tl     = sd4["monthly_timeline"]
        rates4 = sd4["recovery_rates"]
        months4= list(range(1, len(rates4) + 1))

        st.markdown("<br>", unsafe_allow_html=True)
        _section("Recovery Curve — Month by Month")

        # Build animation frames: frame i reveals months 1 … i+1
        frames = [
            go.Frame(
                name=str(i + 1),
                data=[go.Scatter(
                    x    = months4[:i + 1],
                    y    = rates4[:i + 1],
                    mode = "lines+markers",
                    line = dict(color=C["ink"], width=2.5),
                    marker = dict(color=C["ink"], size=7),
                )],
            )
            for i in range(len(months4))
        ]

        fig_anim = go.Figure(
            data=[go.Scatter(
                x    = months4[:1],
                y    = rates4[:1],
                mode = "lines+markers",
                line = dict(color=C["ink"], width=2.5),
                marker = dict(color=C["ink"], size=7),
                hovertemplate = "Month %{x}: %{y:.1%}<extra></extra>",
            )],
            frames=frames,
        )
        fig_anim.update_layout(
            **_base_layout(height=360),
            xaxis = _ax(title="Month", tickvals=months4,
                        range=[0.4, 12.6]),
            yaxis = _ax(title="Recovery Quality", tickformat=".0%",
                        range=[-0.02, 1.05]),
            updatemenus=[dict(
                type      = "buttons",
                showactive= False,
                y=-0.20, x=0.0, xanchor="left",
                buttons=[
                    dict(
                        label ="▶  Play",
                        method="animate",
                        args  =[None, dict(
                            frame=dict(duration=420, redraw=True),
                            fromcurrent=True,
                            transition=dict(duration=0),
                        )],
                    ),
                    dict(
                        label ="⏸  Pause",
                        method="animate",
                        args  =[[None], dict(
                            frame=dict(duration=0, redraw=False),
                            mode="immediate",
                            transition=dict(duration=0),
                        )],
                    ),
                ],
                font     = dict(family="Times New Roman", color=C["ink"], size=12),
                bgcolor  = C["white"],
                bordercolor = C["border"],
                pad      = dict(t=6, b=6),
            )],
            sliders=[dict(
                active=0,
                steps=[dict(
                    method="animate",
                    args=[[str(i + 1)], dict(
                        frame=dict(duration=420, redraw=True),
                        mode="immediate",
                        transition=dict(duration=0),
                    )],
                    label=str(i + 1),
                ) for i in range(len(months4))],
                x=0, y=-0.08, len=1.0,
                currentvalue=dict(
                    prefix="Month: ",
                    font  =dict(family="Times New Roman", color=C["ink"], size=12),
                    xanchor="center",
                ),
                font       = dict(family="Times New Roman", color=C["mid"]),
                bgcolor    = C["bg"],
                bordercolor= C["border"],
                tickcolor  = C["mid"],
                pad        = dict(t=36),
            )],
        )
        st.plotly_chart(fig_anim, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Monthly log ───────────────────────────────────────────────────────
        _section("Monthly Log")

        # Pre-index permanent losses by month for O(1) lookup
        perm_by_month: dict[int, list] = {}
        for e in sd4.get("permanent_losses", []):
            perm_by_month.setdefault(e["month"], []).append(e["topic"])

        log_rows = [
            {
                "Month":          m["month"],
                "Recovery Rate":  f"{m['recovery_rate']:.1%}",
                "Requests":       m["n_requests"],
                "Routed":         m["n_recovered"],
                "Dropped":        m["n_lost"],
                "Topics Lost":    (
                    ", ".join(str(t) for t in perm_by_month[m["month"]])
                    if m["month"] in perm_by_month else "—"
                ),
                "Cumul. Lost":    m["n_permanently_lost_topics"],
            }
            for m in tl
        ]

        st.dataframe(
            pd.DataFrame(log_rows), use_container_width=True, hide_index=True,
            column_config={
                "Month":         st.column_config.NumberColumn("Month",     width="small"),
                "Recovery Rate": st.column_config.TextColumn("Recovery Rate"),
                "Requests":      st.column_config.NumberColumn("Requests"),
                "Routed":        st.column_config.NumberColumn("Routed"),
                "Dropped":       st.column_config.NumberColumn("Dropped"),
                "Topics Lost":   st.column_config.TextColumn("Topics Lost This Month"),
                "Cumul. Lost":   st.column_config.NumberColumn("Cumul. Perm. Lost"),
            },
        )
