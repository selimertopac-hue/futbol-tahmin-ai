import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API AYARLARI ---
API_KEY = "b900863038174d07855ace7f33c69c9b"
BASE_URL = "https://api.football-data.org/v4/"
HEADERS = {"X-Auth-Token": API_KEY}

st.set_page_config(page_title="UltraSkor Pro AI", page_icon="⚽", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def veri_getir(lig="PL"):
    url = f"{BASE_URL}competitions/{lig}/matches"
    response = requests.get(url, headers=HEADERS)
    return response.json()['matches']

def form_hesapla(takim_adi, tum_maclar):
    # Takımın bitmiş son 5 maçını bul
    bitmis = [m for m in tum_maclar if m['status'] == 'FINISHED' and 
              (m['homeTeam']['name'] == takim_adi or m['awayTeam']['name'] == takim_adi)]
    son_5 = bitmis[-5:]
    
    form_string = ""
    for m in son_5:
        skor_h = m['score']['fullTime']['home']
        skor_a = m['score']['fullTime']['away']
        
        if m['homeTeam']['name'] == takim_adi:
            if skor_h > skor_a: form_string += "🟢 " # Galibiyet
            elif skor_h == skor_a: form_string += "🟡 " # Beraberlik
            else: form_string += "🔴 " # Mağlubiyet
        else:
            if skor_a > skor_h: form_string += "🟢 "
            elif skor_a == skor_h: form_string += "🟡 "
            else: form_string += "🔴 "
    return form_string

def analiz_et(ev, dep, tum_maclar):
    df = pd.DataFrame([m for m in tum_maclar if m['status'] == 'FINISHED'])
    if df.empty: return None

    # İstatistikler için basitleştirilmiş tablo
    df['H'] = df['homeTeam'].apply(lambda x: x['name'])
    df['A'] = df['awayTeam'].apply(lambda x: x['name'])
    df['HG'] = df['score'].apply(lambda x: x['fullTime']['home'])
    df['AG'] = df['score'].apply(lambda x: x['fullTime']['away'])

    ev_xg = df[df['H'] == ev]['HG'].mean() if not df[df['H'] == ev].empty else 1.5
    dep_xg = df[df['A'] == dep]['AG'].mean() if not df[df['A'] == dep].empty else 1.2
    
    ev_probs = [poisson.pmf(i, ev_xg) for i in range(5)]
    dep_probs = [poisson.pmf(i, dep_xg) for i in range(5)]
    m = np.outer(ev_probs, dep_probs)
    
    skor = np.unravel_index(np.argmax(m), m.shape)
    return {
        "Ev": np.sum(np.tril(m, -1)) * 100,
        "Ber": np.sum(np.diag(m)) * 100,
        "Dep": np.sum(np.triu(m, 1)) * 100,
        "Skor": f"{skor[0]} - {skor[1]}"
    }

# --- ARAYÜZ ---
st.title("⚽ UltraSkor Pro: Form & Tahmin Paneli")

secili_lig = st.sidebar.selectbox("Lig Seçiniz", ["PL", "BL1", "SA", "PD", "DED"])
all_matches = veri_getir(secili_lig)

gelecek_maclar = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED']]

st.subheader("📅 Haftalık Fikstür ve AI Analizi")

if gelecek_maclar:
    for match in gelecek_maclar[:10]:
        ev_adi = match['homeTeam']['name']
        dep_adi = match['awayTeam']['name']
        tarih = match['utcDate'][:10]
        
        with st.expander(f"📌 {tarih} | {ev_adi} vs {dep_adi}"):
            res = analiz_et(ev_adi, dep_adi, all_matches)
            
            # Form Durumlarını Çek
            ev_form = form_hesapla(ev_adi, all_matches)
            dep_form = form_hesapla(dep_adi, all_matches)
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**{ev_adi} Form:** {ev_form}")
                st.metric("Ev Kazanma", f"%{res['Ev']:.1f}")
            with c2:
                st.markdown(f"**{dep_adi} Form:** {dep_form}")
                st.metric("Dep. Kazanma", f"%{res['Dep']:.1f}")
            
            st.markdown(f"<h3 style='text-align: center;'>🎯 Tahmin: {res['Skor']}</h3>", unsafe_allow_html=True)
            st.progress(res['Ev'] / 100)
else:
    st.info("Bu ligde planlanmış maç bulunamadı.")
