import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Master Engine", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem; }
    .form-circle { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    h1, h2, h3 { color: #58A6FF !important; }
    .prediction-header { font-size: 1.5rem; font-weight: bold; color: #FFFFFF; text-align: center; margin-bottom: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU (SPEKTRUM ANALİZİ) ---
def master_analiz_et(ev_ad, dep_ad, matches):
    try:
        df_raw = [m for m in matches if m['status'] == 'FINISHED']
        if not df_raw: return None
        
        df = pd.DataFrame()
        df['H'] = [m['homeTeam']['name'] for m in df_raw]
        df['A'] = [m['awayTeam']['name'] for m in df_raw]
        df['HG'] = [int(m['score']['fullTime']['home']) if m['score']['fullTime']['home'] is not None else 0 for m in df_raw]
        df['AG'] = [int(m['score']['fullTime']['away']) if m['score']['fullTime']['away'] is not None else 0 for m in df_raw]
        
        lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
        ev_m = df[df['H'] == ev_ad]
        dep_m = df[df['A'] == dep_ad]
        
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

        # Senin istediğin tam simetrik Spektrum Analizi (3. Sütun)
        final_ev_xg = ev_std_xg * ev_bit * dep_sav
        final_dep_xg = dep_std_xg * dep_bit * ev_sav

        def get_probs(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}"

        return {
            "alg_1": get_probs(ev_std_xg, dep_std_xg),
            "alg_2": get_probs(ev_std_xg * ev_bit, dep_std_xg * dep_bit),
            "alg_3": get_probs(final_ev_xg, final_dep_xg),
            "not": f"{ev_ad} savunması {'disiplinli' if ev_sav < 1 else 'kırılgan'} bir yapıda.",
            "ev_xg": ev_std_xg, "dep_xg": dep_std_xg
        }
    except: return None

# --- 4. GÖRSEL FONKSİYONLAR ---
def form_html(takim, matches):
    s = sorted([m for m in matches if (m['homeTeam']['name']==takim or m['awayTeam']['name']==takim) and m['status']=='FINISHED'], key=lambda x:x['utcDate'], reverse=True)[:5]
    res_html = ""
    for m in s:
        h, a = m['score']['fullTime']['home'], m['score']['fullTime']['away']
        r = "draw"
        if m['homeTeam']['name'] == takim:
            if h > a: r = "win"
            elif h < a: r = "loss"
        else:
            if a > h: r = "win"
            elif a < h: r = "loss"
        res_html += f"<span class='form-circle {r}'></span>"
    return res_html

# --- 5. ANA PANEL ---
st.title("🛡️ UltraSkor Pro AI: Spectrum Dashboard")

lig_map = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
secim = st.sidebar.selectbox("🎯 Lig Seçimi", list(lig_map.keys()))

@st.cache_data(ttl=3600)
def veri_getir(url):
    return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}).
