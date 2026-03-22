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

# --- 3. ANALİZ MOTORU ---
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
            ev_std_xg = (ev_m['HG'].mean() / lig_ev_ort) * (dep_m['HG'].mean() / lig_ev_ort) * lig_ev_ort
            dep_std_xg = (dep_m['AG'].mean() / lig_dep_ort) * (ev_m['AG'].mean() / lig_dep_ort) * lig_dep_ort
            ev_bit = ev_m['HG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)
            dep_bit = dep_m['AG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)
            ev_sav = ev_m['AG'].mean() / (lig_dep_ort * (ev_m['AG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)))
            dep_sav = dep_m['HG'].mean() / (lig_ev_ort * (dep_m['HG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)))

        f_ev_xg, f_dep_xg = ev_std_xg * ev_bit * dep_sav, dep_std_xg * dep_bit * ev_sav

        def get_skor(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}"

        return {"alg_1": get_skor(ev_std_xg, dep_std_xg), "alg_3": get_skor(f_ev_xg, f_dep_xg), "ev_xg": ev_std_xg, "dep_xg": dep_std_xg, "ev_not": "🛡️ Katı" if ev_sav < 1 else "⚠️ Kırılgan", "dep_not": "⚔️ Fırsatçı" if dep_bit > 1.2 else "🐢 Kısır"}
    except: return None

# --- 4. GÖRSEL FONKSİYONLAR ---
def form_html(takim, matches):
    s = sorted([m for m in matches if (m['homeTeam']['name']==takim or m['awayTeam']['name']==takim) and m['status']=='FINISHED'], key=lambda x:x['utcDate'], reverse=True)[:5]
    res_html = ""
    for m in s:
        h, a = m['score']['fullTime']['home'], m['score']['fullTime']['away']
        r = "win" if (m['homeTeam']['name'] == takim and h > a) or (m['awayTeam']['name'] == takim and a > h) else ("draw" if h == a else "loss")
        res_html += f"<span class='form-circle {r}'></span>"
    return res_html

# --- 5. ANA PANEL ---
st.title("🛡️
