"""
ui/styles.py — Kaikki CSS-tyylit yhdessä paikassa.
"""
import streamlit as st


def inject_global_styles() -> None:
    """Injektoi sovelluksen globaalit CSS-tyylit."""
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = """
<style>
/* ── Pohjatyyli ─────────────────────────────────────────────── */
.stApp { overflow-x: hidden; }

/* ── Mobiiliresponsiivisuus ─────────────────────────────────── */
@media (max-width: 768px) {
    .block-container { padding: 1rem; }
    .stButton button { width: 100%; }
    .ai-card, .rec-card { min-height: auto; }
}

/* ── Linkkipainike ──────────────────────────────────────────── */
.link-btn {
    display: flex; align-items: center; justify-content: center;
    padding: 12px; background: #262730; border: 1px solid #464b5f;
    border-radius: 8px; margin-bottom: 8px; text-decoration: none;
    color: white !important; width: 100%; transition: background 0.2s;
    font-weight: 500; box-sizing: border-box; gap: 9px; min-height: 50px;
}
.link-btn:hover { background: #363740; }
.link-logo {
    display: inline-flex; align-items: center; justify-content: center;
    flex: 0 0 38px; width: 38px; height: 22px; padding: 0;
    background: transparent; border: 0; border-radius: 0; box-sizing: border-box;
}
.link-logo img {
    display: block; width: auto; height: auto; max-width: 38px; max-height: 22px;
    margin: 0; object-fit: contain;
    filter: drop-shadow(0 0 1px rgba(255,255,255,.55))
            drop-shadow(0 1px 1px rgba(0,0,0,.35));
}
.link-logo img.logo-on-dark {
    filter: brightness(1.7) saturate(1.45)
            drop-shadow(0 0 1px rgba(255,255,255,.75))
            drop-shadow(0 1px 1px rgba(0,0,0,.35));
}
.link-logo img.logo-invert-on-dark {
    filter: invert(1) brightness(1.9) contrast(1.15)
            drop-shadow(0 0 1px rgba(255,255,255,.6))
            drop-shadow(0 1px 1px rgba(0,0,0,.35));
}

/* ── CTA-painike ────────────────────────────────────────────── */
.cta-wrap   { display: flex; justify-content: center; margin: 20px 0; }
.cta-btn {
    background-color: #0a66c2; color: white !important; padding: 16px 32px;
    border-radius: 8px; font-weight: bold; text-decoration: none;
    text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,.1); display: inline-block;
}
.cta-btn.dark { background-color: #333; }

/* ── Suositus-kortti ────────────────────────────────────────── */
.rec-card  { background-color: #262730; border: 1px solid #464b5f; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
.rec-title { font-size: 1.1rem; font-weight: bold; color: white; margin-bottom: 5px; }
.rec-cat   { font-size: 0.8rem; text-transform: uppercase; color: #aaa; letter-spacing: 1px; }
.rec-badge { background-color: #0a66c2; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
.rec-reasons { color: #c7d6ea; font-size: .88rem; margin: 0 0 8px; }

/* ── AI-koulutuskortti ──────────────────────────────────────── */
.ai-card {
    background: linear-gradient(135deg, #2b2d42 0%, #1e1e24 100%);
    border: 1px solid #4DA6FF; border-radius: 12px; padding: 20px; min-height: 300px;
    display: flex; flex-direction: column; justify-content: space-between;
    box-shadow: 0 4px 6px rgba(0,0,0,.3);
}
.ai-type     { color: #00d4ff !important; font-size: .75em; font-weight: bold; text-transform: uppercase; }
.ai-title    { color: white !important; font-size: 1.2rem; font-weight: bold; margin: 5px 0; }
.ai-provider { color: #b0b0b0 !important; font-size: .9rem; font-style: italic; margin-bottom: 10px; }
.ai-desc     { color: #e0e0e0 !important; font-size: .9rem; flex-grow: 1; }
.ai-link {
    background: #4DA6FF; color: white !important; padding: 8px 16px;
    border-radius: 20px; text-decoration: none; font-weight: bold;
    display: inline-block; white-space: nowrap; font-size: .9rem;
}
.ai-link:hover { background: #008cff; }

/* ── Portfolio-metriikkakortti ──────────────────────────────── */
.metric-card {
    background: linear-gradient(135deg, #2b2d42 0%, #1e1e24 100%);
    border: 1px solid #464b5f; border-radius: 10px; padding: 15px;
    text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,.3);
}
.metric-value { font-size: 1.8rem; font-weight: bold; color: #4DA6FF; margin: 0; }
.metric-label { font-size: .9rem; color: #b0b0b0; text-transform: uppercase; letter-spacing: 1px; }
</style>
"""
