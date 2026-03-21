import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API AYARLARI ---
API_KEY = "b900863038174d07855ace7f33c69c9b"
BASE_URL = "https://api.football-data.org/v4/"
HEADERS = {"X-Auth-Token": API_KEY}

st.set_page_config(page_title="UltraSkor Pro", page_icon="⚽", layout="wide")

# --- VERİ ÇEKME FONKSİYONLARI ---
@st.cache_data(ttl=3600)
def mac_verilerini_getir(lig="PL"):
    url = f"{BASE_URL}competitions/{lig}/matches"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    return data['matches']

def analiz_et(ev, dep, gecmis_maclar):
    df = pd.DataFrame(gecmis_maclar)
    # Sadece bitmiş maçlardan istatistik çıkar
    df_bitmis = df[df['status'] == 'FINISHED'].copy()
    
    # Takım isimlerini düzelt (API yapısına göre)
    df_bitmis['Home'] = df_bitmis['homeTeam'].apply(lambda x: x['name'])
    df_bitmis['Away'] = df_bitmis['awayTeam'].apply(lambda x: x['name'])
    df_bitmis['HG'] = df_bitmis['score'].apply(lambda x: x['fullTime']['home'])
    df_bitmis['AG'] = df_bitmis['score'].apply(lambda x: x['fullTime']['away'])

    ev_xg = df_bitmis[df_bitmis['Home'] == ev]['HG'].mean()
    dep_xg = df_bitmis[df_bitmis['Away'] == dep]['AG'].mean()
    
    # Poisson Olasılıkları
    ev_probs = [poisson.pmf(i, ev_xg if not np.isnan(ev_xg) else 1.5) for i in range(5)]
    dep_probs = [poisson.pmf(i, dep_xg if not np.isnan(dep_xg) else 1.2) for i in range(5)]
    m = np.outer(ev_probs, dep_probs)
    
    skor = np.unravel_index(np.argmax(m), m.shape)
    return {
        "Ev": np.sum(np.tril(m, -1)) * 100,
        "Ber": np.sum(np.diag(m)) * 100,
        "Dep": np.sum(np.triu(m, 1)) * 100,
        "Skor": f"{skor[0]} - {skor[1]}"
    }

# --- ARAYÜZ ---
st.title("🏆 UltraSkor Pro: Haftalık Fikstür & Tahminler")
st.sidebar.markdown("### ⚙️ Ayarlar")
secili_lig = st.sidebar.selectbox("Lig Seçiniz", ["PL", "BL1", "SA", "PD", "FL1", "DED", "CLI"])

all_matches = mac_verilerini_getir(secili_lig)

# Gelecek Maçları Filtrele (SCHEDULED veya TIMED)
gelecek_maclar = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED']]

st.subheader("📅 Önümüzdeki Maçlar ve AI Tahminleri")

if gelecek_maclar:
    for match in gelecek_maclar[:10]: # İlk 10 maçı göster (Sayfa kasmaması için)
        ev_adi = match['homeTeam']['name']
        dep_adi = match['awayTeam']['name']
        tarih = match['utcDate'][:10]
        
        with st.expander(f"📌 {tarih} | {ev_adi} vs {dep_adi}"):
            res = analiz_et(ev_adi, dep_adi, all_matches)
            
            c1, c2, c3, c4 = st.columns([2,1,1,1])
            c1.write(f"**Tahmin Edilen Skor: {res['Skor']}**")
            c2.success(f"🏠 %{res['Ev']:.1f}")
            c3.warning(f"🤝 %{res['Ber']:.1f}")
            c4.error(f"🚀 %{res['Dep']:.1f}")
else:
    st.info("Bu ligde şu an planlanmış gelecek maç bulunmuyor.")

st.sidebar.write("---")
st.sidebar.caption("Veriler football-data.org API üzerinden canlı çekilmektedir.")