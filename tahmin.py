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
    df = pd.DataFrame([m for m in tum_maclar if m['status'] == 'FINISHED'])
    if df.empty: return None
    df['H'] = df['homeTeam'].apply(lambda x: x['name'])
    df['A'] = df['awayTeam'].apply(lambda x: x['name'])
    df['HG'] = df['score'].apply(lambda x: x['fullTime']['home'])
    df['AG'] = df['score'].apply(lambda x: x['fullTime']['away'])

    ev_xg = df[df['H'] == ev]['HG'].mean() if not df[df['H'] == ev].empty else 1.5
    dep_xg = df[df['A'] == dep]['AG'].mean() if not df[df['A'] == dep].empty else 1.2
    
    ev_p = [poisson.pmf(i, ev_xg) for i in range(5)]
    dep_p = [poisson.pmf(i, dep_xg) for i in range(5)]
    m = np.outer(ev_p, dep_p)
    
    return {
        "Ev": np.sum(np.tril(m, -1)) * 100,
        "Ber": np.sum(np.diag(m)) * 100,
        "Dep": np.sum(np.triu(m, 1)) * 100,
        "Skor": f"{np.unravel_index(np.argmax(m), m.shape)[0]} - {np.unravel_index(np.argmax(m), m.shape)[1]}"
    }

# --- ARAYÜZ ---
st.title("🏆 UltraSkor Pro: Akıllı Analiz Sistemi")
secili_lig = st.sidebar.selectbox("Lig Seçiniz", ["PL", "BL1", "SA", "PD", "DED"])
all_matches = veri_getir(secili_lig)
gelecek = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED']]

# Analiz Raporu İçin Liste
analiz_listesi = []

st.subheader("📅 Haftalık Fikstür Tahminleri")
if gelecek:
    for match in gelecek[:12]:
        ev_n, dep_n = match['homeTeam']['name'], match['awayTeam']['name']
        res = analiz_et(ev_n, dep_n, all_matches)
        if res:
            # En yüksek olasılığı bul (Güven endeksi için)
            max_prob = max(res['Ev'], res['Ber'], res['Dep'])
            analiz_listesi.append({"mac": f"{ev_n} - {dep_n}", "guven": max_prob, "skor": res['Skor']})

            with st.expander(f"⚽ {ev_n} vs {dep_n}"):
                c1, c2, c3 = st.columns(3)
                c1.metric(f"🏠 {ev_n}", f"%{res['Ev']:.1f}", delta=form_hesapla(ev_n, all_matches), delta_color="off")
                c2.metric("🤝 Beraberlik", f"%{res['Ber']:.1f}")
                c3.metric(f"🚀 {dep_n}", f"%{res['Dep']:.1f}", delta=form_hesapla(dep_n, all_matches), delta_color="off")
                st.info(f"🎯 Yapay Zeka Skor Tahmini: **{res['Skor']}**")

    # --- GÜNÜN FAVORİSİ KÖŞESİ ---
    st.markdown("---")
    st.header("🌟 Günün Yapay Zeka Raporu")
    if analiz_listesi:
        # Güveni en yüksek maçı bul
        en_iyi = max(analiz_listesi, key=lambda x: x['guven'])
        st.warning(f"🤖 **MODELİN EN GÜVENDİĞİ MAÇ:** {en_iyi['mac']} \n\n **Tahmin:** {en_iyi['skor']} (Güven Endeksi: %{en_iyi['guven']:.1f})")
else:
    st.info("Planlanmış maç bulunamadı.")
