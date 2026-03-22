import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Dual Engine", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; }
    .match-result { font-size: 1.5rem; font-weight: bold; color: #58A6FF; text-align: center; background: #21262d; border-radius: 6px; padding: 6px; border: 1px solid #30363d; min-width: 80px; }
    .match-time { font-size: 1.1rem; color: #8B949E; text-align: center; font-weight: bold; border: 1px dashed #30363d; padding: 5px; border-radius: 6px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 10px; text-align: center; width: 48%; }
    .label-std { font-size: 0.65rem; color: #8B949E; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
    .label-spec { font-size: 0.65rem; color: #58A6FF; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 0.85rem; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
def master_analiz_et(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        
        # Eğer yeterli veri yoksa lig ortalaması üzerinden tahmini yürüt
        if len(df_raw) < 10:
            e_xg, d_xg, e_bit, d_bit, e_sav, d_sav = 1.4, 1.2, 1.0, 1.0, 1.0, 1.0
        else:
            df = pd.DataFrame()
            df['H'] = [m['homeTeam']['name'] for m in df_raw]
            df['A'] = [m['awayTeam']['name'] for m in df_raw]
            df['HG'] = [int(m['score']['fullTime']['home']) for m in df_raw]
            df['AG'] = [int(m['score']['fullTime']['away']) for m in df_raw]
            
            l_ev_ort, l_dep_ort = df['HG'].mean(), df['AG'].mean()
            ev_m, dep_m = df[df['H'] == ev_ad], df[df['A'] == dep_ad]
            
            e_h_g = ev_m['HG'].mean() if not ev_m.empty else l_ev_ort
            e_h_y = ev_m['AG'].mean() if not ev_m.empty else l_dep_ort
            d_d_g = dep_m['AG'].mean() if not dep_m.empty else l_dep_ort
            d_d_y = dep_m['HG'].mean() if not dep_m.empty else l_ev_ort

            e_xg = (e_h_g / l_ev_ort) * (d_d_y / l_ev_ort) * l_ev_ort
            d_xg = (d_d_g / l_dep_ort) * (e_h_y / l_dep_ort) * l_dep_ort
            e_bit = e_h_g / (e_xg if e_xg > 0 else 1)
            d_bit = d_d_g / (d_xg if d_xg > 0 else 1)
            e_sav = e_h_y / (l_dep_ort * (e_h_y / (e_xg if e_xg > 0 else 1)))
            d_sav = d_d_y / (l_ev_ort * (d_d_y / (d_xg if d_xg > 0 else 1)))

        f_e_xg, f_d_xg = e_xg * e_bit * d_sav, d
