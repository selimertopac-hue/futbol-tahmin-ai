import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API AYARLARI ---
API_KEY = "b900863038174d07855ace7f33c69c9b"
BASE_URL = "https://api.football-data.org/v4/"
HEADERS = {"X-Auth-Token": API_KEY}

# --- SAYFA TASARIMI (DARK MODE & CUSTOM CSS) ---
st.set_page_config(page_title="UltraSkor Pro AI", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stMetric { background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 15px; }
    [data-testid="stExpander"] { background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; }
    .stDataFrame { background-color: #161B22; }
    h1, h2, h3 { color: #58A6FF !important; font-family: 'Segoe UI', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def veri_getir(endpoint, lig="PL"):
    url = f"{BASE_URL}competitions/{lig}/{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        return response.json()
    except: return {}

def analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None
    
    df['H'] = df['homeTeam'].apply(lambda x: x['name'])
    df['A'] = df['awayTeam'].apply(lambda x: x['name'])
    df['HG'] = df['score'].apply(lambda x: x['fullTime']['home'])
    df['AG'] = df['score'].apply(lambda x: x['fullTime']['away'])

    # Gelişmiş xG: Ev sahibinin iç saha, deplasmanın dış saha performansı
    ev_xg = df[df['H'] == ev]['HG'].mean() if not df[df['H'] == ev].empty else 1.5
    dep_xg = df[df['A'] == dep]['AG'].mean() if not df[df['A'] == dep].empty else 1.2
    
    m = np.outer([poisson.pmf(i, ev_xg) for i in range(5)], [poisson.pmf(i, dep_xg) for i in range(5)])
    sk = np.unravel_index(np.argmax(m), m.shape)
    
    return {
        "Ev": np.sum(np.tril(m, -1))*100, "Ber": np.sum(np.diag(m))*100, "Dep": np.sum(np.triu(m, 1))*100,
        "Skor": f"{sk[0]} - {sk[1]}", "Guven": max(np.sum(np.tril(m, -1)), np.sum(np.triu(m, 1)))*100
    }

# --- ANA PANEL ---
st.title("🛡️ UltraSkor Pro AI: Dark Edition")

# Lig Seçimi
ligler = {"İngiltere (PL)": "PL", "Almanya (BL1)": "BL1", "İtalya (SA)": "SA", "İspanya (PD)": "PD", "Hollanda (DED)": "DED"}
secili_lig = st.sidebar.selectbox("🎯 Analiz Edilecek Lig", list(ligler.keys()))
lig_kodu = ligler[secili_lig]

# Verileri Yükle
m_data = veri_getir("matches", lig_kodu).get('matches', [])
s_data = veri_getir("standings", lig_kodu).get('standings', [{}])[0].get('table', [])

# 🌟 GÜNÜN KAHİNİ (HEADER)
if m_data:
    gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]
    if gelecek:
        analizler = []
        for m in gelecek[:10]:
            res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_data)
            if res: analizler.append({"mac": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}", "guven": res['Guven'], "skor": res['Skor']})
        
        if analizler:
            en_iyi = max(analizler, key=lambda x: x['guven'])
            st.info(f"✨ **YAPAY ZEKA ÖNERİSİ:** {en_iyi['mac']} | **Tahmin:** {en_iyi['skor']} (Güven: %{en_iyi['guven']:.1f})")

st.markdown("---")

# İKİLİ PANEL
col1, col2 = st.columns([1, 1.8])

with col1:
    st.subheader("📈 Puan Tablosu")
    if s_data:
        df_p = pd.DataFrame([{"#": t['position'], "Takım": t['team']['name'], "P": t['points'], "Av": t['goalDifference']} for t in s_data])
        st.dataframe(df_p, hide_index=True, use_container_width=True)

with col2:
    st.subheader("📅 Maç Analizleri")
    if gelecek:
        for m in gelecek[:8]:
            ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
            res = analiz_et(ev, dep, m_data)
            with st.expander(f"🔍 {ev} - {dep}"):
                c_img1, c_text, c_img2 = st.columns([1, 3, 1])
                c_img1.image(m['homeTeam']['crest'], width=50)
                c_text.markdown(f"<h4 style='text-align: center;'>{ev} vs {dep}</h4>", unsafe_allow_html=True)
                c_img2.image(m['awayTeam']['crest'], width=50)
                
                # Olasılık Çubukları
                st.write(f"🏠 Ev: %{res['Ev']:.1f} | 🤝 Ber: %{res['Ber']:.1f} | 🚀 Dep: %{res['Dep']:.1f}")
                st.progress(res['Ev']/100)
                st.markdown(f"### 🎯 Beklenen Skor: {res['Skor']}")
