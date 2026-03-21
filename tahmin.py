import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR & API ANAHTARLARIN ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
ODDS_API_KEY = "b4040bb05379cd7d9b94f18f2b74b133"
# Telegram bilgilerini buraya girebilirsin
TELEGRAM_TOKEN = "BURAYA_TOKEN" 
TELEGRAM_CHAT_ID = "BURAYA_ID" 

st.set_page_config(page_title="UltraSkor Pro: Master Engine", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 5px; margin-top: 10px; font-size: 0.9rem; }
    .filter-label { font-size: 0.7rem; font-weight: bold; color: #8B949E; margin-bottom: 5px; text-align: center; text-transform: uppercase; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
def master_analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None
    
    # Veri Hazırlama
    df['H'] = df['homeTeam'].apply(lambda x: x['name'])
    df['A'] = df['awayTeam'].apply(lambda x: x['name'])
    df['HG'] = df['score'].apply(lambda x: x['fullTime']['home'])
    df['AG'] = df['score'].apply(lambda x: x['fullTime']['away'])
    
    lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
    ev_m = df[df['H'] == ev]
    dep_m = df[df['A'] == dep]
    
    if ev_m.empty or dep_m.empty: return None

    # ALGORİTMA 1: STANDART xG
    ev_std_xg = (ev_m['HG'].mean() / lig_ev_ort) * (dep_m['HG'].mean() / lig_ev_ort) * lig_ev_ort
    dep_std_xg = (dep_m['AG'].mean() / lig_dep_ort) * (ev_m['AG'].mean() / lig_dep_ort) * lig_dep_ort

    # ALGORİTMA 2: OFANSİF VERİMLİLİK
    ev_bitiricilik = ev_m['HG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)
    dep_bitiricilik = dep_m['AG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)

    # ALGORİTMA 3: TAM SİMETRİK GERÇEKLİK (xG vs Real Gol)
    # Ev Savunma Şansı ve Dep Savunma Şansı Kıyaslaması
    ev_sav_gercek = ev_m['AG'].mean() / (lig_dep_ort * (ev_m['AG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)))
    dep_sav_gercek = dep_m['HG'].mean() / (lig_ev_ort * (dep_m['HG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)))
    
    final_ev_xg = ev_std_xg * ev_bitiricilik * dep_sav_gercek
    final_dep_xg = dep_std_xg * dep_bitiricilik * ev_sav_gercek

    def get_probs(ex, ax):
        m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
        sk = np.unravel_index(np.argmax(m), m.shape)
        return {"Ev": np.sum(np.tril(m, -1))*100, "Skor": f"{sk[0]} - {sk[1]}"}

    return {
        "alg_1": get_probs(ev_std_xg, dep_std_xg),
        "alg_2": get_probs(ev_std_xg * ev_bitiricilik, dep_std_xg * dep_bitiricilik),
        "alg_3": get_probs(final_ev_xg, final_dep_xg),
        "ev_sav_not": "Disiplinli" if ev_sav_gercek < 1 else "Kırılgan",
        "dep_huc_not": "Fırsatçı" if dep_bitiricilik > 1.1 else "Kısır"
    }

# --- 4. ARAYÜZ ---
lig_mapping = {
    "İngiltere (PL)": {"code": "PL", "odds": "soccer_epl"},
    "İspanya (PD)": {"code": "PD", "odds": "soccer_spain_la_liga"},
    "İtalya (SA)": {"code": "SA", "odds": "soccer_italy_serie_a"},
    "Almanya (BL1)": {"code": "BL1", "odds": "soccer_germany_bundesliga"},
    "Fransa (FL1)": {"code": "FL1", "odds": "soccer_france_ligue_one"},
    "Hollanda (DED)": {"code": "DED", "odds": "soccer_netherlands_ere_divisie"}
}

secim = st.sidebar.selectbox("🎯 Lig Seçimi", list(lig_mapping.keys()))

@st.cache_data(ttl=3600)
def veri_getir(url, headers={}):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json()
    except: return {}

m_data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_mapping[secim]['code']}/matches", {"X-Auth-Token": FOOTBALL_DATA_KEY}).get('matches', [])
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

if gelecek:
    for m in gelecek[:12]:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = master_analiz_et(ev, dep, m_data)
        
        if res:
            with st.expander(f"🏟️ {ev} vs {dep}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("<p class='filter-label'>📍 Standart xG</p>", unsafe_allow_html=True)
                    st.info(f"Skor: **{res['alg_1']['Skor']}**")
                with c2:
                    st.markdown("<p class='filter-label'>🎯 Ofansif Güç</p>", unsafe_allow_html=True)
                    st.success(f"Skor: **{res['alg_2']['Skor']}**")
                with c3:
                    st.markdown("<p class='filter-label'>🛡️ Derin Gerçeklik</p>", unsafe_allow_html=True)
                    st.warning(f"Skor: **{res['alg_3']['Skor']}**")

                st.markdown(f"<div class='strategy-box'>📝 <b>Stratejik Not:</b> {ev} savunması <b>{res['ev_sav_not']}</b> karakterde. {dep} hücumu ise deplasmanda <b>{res['dep_huc_not']}</b> bir yapı sergiliyor.</div>", unsafe_allow_html=True)
