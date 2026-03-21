import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API AYARLARI ---
API_KEY = "b900863038174d07855ace7f33c69c9b"
BASE_URL = "https://api.football-data.org/v4/"
HEADERS = {"X-Auth-Token": API_KEY}

st.set_page_config(page_title="UltraSkor Pro AI", page_icon="📈", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def veri_getir(lig="PL"):
    url = f"{BASE_URL}competitions/{lig}/matches"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        return response.json()['matches']
    except: return []

def form_hesapla(takim_adi, tum_maclar):
    bitmis = [m for m in tum_maclar if m['status'] == 'FINISHED' and 
              (m['homeTeam']['name'] == takim_adi or m['awayTeam']['name'] == takim_adi)]
    son_5 = bitmis[-5:]
    f = ""
    for m in son_5:
        sh, sa = m['score']['fullTime']['home'], m['score']['fullTime']['away']
        if m['homeTeam']['name'] == takim_adi:
            if sh > sa: f += "🟢"
            elif sh == sa: f += "🟡"
            else: f += "🔴"
        else:
            if sa > sh: f += "🟢"
            elif sa == sh: f += "🟡"
            else: f += "🔴"
    return f if f != "" else "Veri Yok"

def analiz_et(ev, dep, tum_maclar):
    df_bitmis = pd.DataFrame([m for m in tum_maclar if m['status'] == 'FINISHED'])
    if df_bitmis.empty: return None
    df_bitmis['H'] = df_bitmis['homeTeam'].apply(lambda x: x['name'])
    df_bitmis['A'] = df_bitmis['awayTeam'].apply(lambda x: x['name'])
    df_bitmis['HG'] = df_bitmis['score'].apply(lambda x: x['fullTime']['home'])
    df_bitmis['AG'] = df_bitmis['score'].apply(lambda x: x['fullTime']['away'])

    ev_xg = df_bitmis[df_bitmis['H'] == ev]['HG'].mean() if not df_bitmis[df_bitmis['H'] == ev].empty else 1.5
    dep_xg = df_bitmis[df_bitmis['A'] == dep]['AG'].mean() if not df_bitmis[df_bitmis['A'] == dep].empty else 1.2
    
    ev_p = [poisson.pmf(i, ev_xg) for i in range(5)]
    dep_p = [poisson.pmf(i, dep_xg) for i in range(5)]
    m = np.outer(ev_p, dep_p)
    skor_indeks = np.unravel_index(np.argmax(m), m.shape)
    
    return {
        "Ev": np.sum(np.tril(m, -1)) * 100,
        "Ber": np.sum(np.diag(m)) * 100,
        "Dep": np.sum(np.triu(m, 1)) * 100,
        "Skor": f"{skor_indeks[0]} - {skor_indeks[1]}"
    }

# --- ARAYÜZ ---
st.title("🛡️ UltraSkor Pro AI: Canlı Analiz Paneli")

st.sidebar.header("📊 Lig Seçimi")
lig_secenekleri = {"İngiltere (PL)": "PL", "Almanya (BL1)": "BL1", "İtalya (SA)": "SA", "İspanya (PD)": "PD", "Hollanda (DED)": "DED"}
secili_lig_adi = st.sidebar.selectbox("Lig Seçiniz", list(lig_secenekleri.keys()))
secili_lig_kodu = lig_secenekleri[secili_lig_adi]

all_matches = veri_getir(secili_lig_kodu)
gelecek_maclar = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED']]

if gelecek_maclar:
    for match in gelecek_maclar[:10]:
        ev_adi, dep_adi = match['homeTeam']['name'], match['awayTeam']['name']
        ev_logo, dep_logo = match['homeTeam']['crest'], match['awayTeam']['crest']
        
        with st.expander(f"📌 {match['utcDate'][:10]} | {ev_adi} vs {dep_adi}"):
            res = analiz_et(ev_adi, dep_adi, all_matches)
            
            c_l1, c_mid, c_l2 = st.columns([1, 3, 1])
            with c_l1: st.image(ev_logo, width=70)
            with c_mid: st.markdown(f"<h3 style='text-align: center;'>{ev_adi} vs {dep_adi}</h3>", unsafe_allow_html=True)
            with c_l2: st.image(dep_logo, width=70)

            c1, c2, c3 = st.columns(3)
            c1.metric(f"🏠 {ev_adi}", f"%{res['Ev']:.1f}", delta=form_hesapla(ev_adi, all_matches), delta_color="off")
            c2.metric("🤝 Beraberlik", f"%{res['Ber']:.1f}")
            c3.metric(f"🚀 {dep_adi}", f"%{res['Dep']:.1f}", delta=form_hesapla(dep_adi, all_matches), delta_color="off")
            
            st.info(f"🎯 Yapay Zeka Skor Tahmini: **{res['Skor']}**")
else:
    st.info("Planlanmış maç bulunamadı.")
