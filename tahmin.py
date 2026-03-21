import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API ANAHTARLARIN ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
ODDS_API_KEY = "b4040bb05379cd7d9b94f18f2b74b133" # Yeni aldığın anahtar

st.set_page_config(page_title="UltraSkor AI: Radar", page_icon="📡", layout="wide")

# --- DARK MODE & STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .value-card { background-color: #064e3b; color: #34d399; padding: 10px; border-radius: 5px; border: 1px solid #059669; }
    .no-value { color: #8B949E; font-size: 0.8rem; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- VERİ ÇEKME FONKSİYONLARI ---
@st.cache_data(ttl=3600)
def oranlari_cek(lig_odds):
    url = f"https://api.the-odds-api.com/v4/sports/{lig_odds}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
    try:
        res = requests.get(url)
        return res.json()
    except: return []

@st.cache_data(ttl=3600)
def maclari_getir(lig_code):
    url = f"https://api.football-data.org/v4/competitions/{lig_code}/matches"
    try:
        res = requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY})
        return res.json().get('matches', [])
    except: return []

def analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None
    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score'].apply(lambda x: x['fullTime']['home']), df['score'].apply(lambda x: x['fullTime']['away'])
    ev_xg = df[df['H'] == ev]['HG'].mean() if not df[df['H'] == ev].empty else 1.5
    dep_xg = df[df['A'] == dep]['AG'].mean() if not df[df['A'] == dep].empty else 1.2
    m = np.outer([poisson.pmf(i, ev_xg) for i in range(5)], [poisson.pmf(i, dep_xg) for i in range(5)])
    sk = np.unravel_index(np.argmax(m), m.shape)
    return {"Ev": np.sum(np.tril(m, -1))*100, "Ber": np.sum(np.diag(m))*100, "Dep": np.sum(np.triu(m, 1))*100, "Skor": f"{sk[0]} - {sk[1]}"}

# --- ANA PANEL ---
st.title("📡 UltraSkor AI: Otomatik Oran Radarı")

lig_mapping = {
    "İngiltere (PL)": {"code": "PL", "odds": "soccer_epl"},
    "İspanya (PD)": {"code": "PD", "odds": "soccer_spain_la_liga"},
    "Almanya (BL1)": {"code": "BL1", "odds": "soccer_germany_bundesliga"},
    "İtalya (SA)": {"code": "SA", "odds": "soccer_italy_serie_a"},
    "Fransa (FL1)": {"code": "FL1", "odds": "soccer_france_ligue_one"}
}

secim = st.sidebar.selectbox("🎯 Analiz Edilecek Lig", list(lig_mapping.keys()))

# Verileri çek
m_data = maclari_getir(lig_mapping[secim]['code'])
canli_oranlar = oranlari_cek(lig_mapping[secim]['odds'])

gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

st.subheader(f"🚀 {secim} - AI vs Piyasa Karşılaştırması")

if gelecek:
    for m in gelecek[:12]:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = analiz_et(ev, dep, m_data)
        
        # Oran API'den bu maçı bul (İsim benzerliğine göre)
        mac_orani = next((o for o in canli_oranlar if ev[:5] in o['home_team'] or o['home_team'][:5] in ev), None)
        
        with st.expander(f"🔍 {ev} vs {dep}"):
            c1, c2 = st.columns(2)
            
            with c1:
                st.write("**🤖 AI Analizi**")
                st.write
