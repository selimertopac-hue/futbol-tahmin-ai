import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Accordion Archive", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .form-circle { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    .match-result { font-size: 1.1rem; font-weight: bold; color: #FFFFFF; text-align: center; background: #21262d; border-radius: 5px; padding: 5px; border: 1px solid #30363d; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 8px; margin-top: 10px; font-size: 0.85rem; }
    h1, h2, h3 { color: #58A6FF !important; }
    .stExpander { border: 1px solid #30363d !important; background-color: #161b22 !important; margin-bottom: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU (TÜM DENKLEMLER BURADA) ---
def master_analiz_et(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if not df_raw: return None
        
        df = pd.DataFrame()
        df['H'] = [m['homeTeam']['name'] for m in df_raw]
        df['A'] = [m['awayTeam']['name'] for m in df_raw]
        df['HG'] = [int(m['score']['fullTime']['home']) for m in df_raw]
        df['AG'] = [int(m['score']['fullTime']['away']) for m in df_raw]
        
        lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
        ev_m, dep_m = df[df['H'] == ev_ad], df[df['A'] == dep_ad]
        
        if ev_m.empty or dep_m.empty:
            ev_std_xg, dep_std_xg = 1.3, 1.1
            ev_bit, dep_bit, ev_sav, dep_sav = 1.0, 1.0, 1.0, 1.0
        else:
            ev_std
