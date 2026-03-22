import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
LIGLER = {
    "İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", 
    "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"
}

st.set_page_config(page_title="UltraSkor Pro: Global Scorecard", page_icon="🌍", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .rank-badge { position: absolute; top: 10px; right: 10px; background: #238636; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .league-label { font-size: 0.7rem; color: #8B949E; text-transform: uppercase; margin-bottom: 5px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .active-algo { border: 1.5px solid #58A6FF !important; background: rgba(88, 166, 255, 0.1); }
    .success-icon { color: #238636; font-weight: bold; margin-left: 5px; }
    .score-banner { background: #21262d; padding: 20px; border-radius: 12px; border: 1px solid #58A6FF; text-align: center; margin-bottom: 25px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
def analiz_et(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if len(df_raw) < 5: return None
        df = pd.DataFrame([{'H': m['homeTeam']['name'], 'A': m['awayTeam']['name'], 
                            'HG': m['score']['fullTime']['home'], 'AG': m['score']['fullTime']['away'], 
                            'MD': m['matchday']} for m in df_raw])
        l_ev_ort, l_dep_ort = df['HG'].mean(), df['AG'].mean()
        max_md = df['MD'].max()

        def get_stats(team, is_home):
            t_df = df[df['H' if is_home else 'A'] == team].copy()
            if t_df.empty: return l_ev_ort, l_dep_ort, 1.0
            t_df['w'] = 1.0 + (t_df['MD'] / max_md)
            g = (t_df['HG' if is_home else 'AG']*t_df['w']).sum()/t_df['w'].sum()
            y = (t_df['AG' if is_home else 'HG']*t_df['w']).sum()/t_df['w'].sum()
            return g, y, t_df['w'].mean()

        e_g, e_y, e_w = get_stats(ev_ad, True)
        d_g, d_y, d_w = get_stats(dep_ad, False)
        std_e_xg = (e_g / l_ev_ort) * (d_y / l_ev_ort) * l_ev_ort
        std_d_xg = (d_g / l_dep_ort) * (e_y / l_dep_ort) * l_dep_ort
        bit = np.clip(((e_g / (std_e_xg if std_e_xg > 0 else 1)) * 0.7) + 0.3, 0.8, 1.3)
        spec_e_xg, spec_d_xg = std_e_xg * bit, std_d_xg * (1.1 if d_w > 1.5 else 0.9)

        def get_skor(ex, ax):
            m = np.outer([poisson.pmf(i, max(0.1, ex)) for i in range(6)], [poisson.pmf(i, max(0.1, ax)) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}", min(99, int(abs(ex-ax)*45 + 25))

        s_sk, s_cf = get_skor(std_
