import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API ANAHTARLARIN ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
ODDS_API_KEY = "b4040bb05379cd7d9b94f18f2b74b133"

st.set_page_config(page_title="UltraSkor AI: Pro Analiz", page_icon="🛡️", layout="wide")

# --- GELİŞMİŞ STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stat-card { background-color: #161B22; border: 1px solid #30363D; padding: 10px; border-radius: 8px; text-align: center; }
    .best-card { background-color: #161B22; border: 2px solid #58A6FF; padding: 15px; border-radius: 12px; text-align: center; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DERİN ANALİZ FONKSİYONU (Advanced xG) ---
def derin_analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None

    # Verileri hazırla
    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score'].apply(lambda x: x['fullTime']['home']), df['score'].apply(lambda x: x['fullTime']['away'])

    # 1. Lig Geneli Ortalamalar (Benchmark)
    lig_ev_gol_ort = df['HG'].mean()
    lig_dep_gol_ort = df['AG'].mean()

    # 2. Takım Spesifik İstatistikler
    # Ev sahibinin iç saha hücum gücü / Deplasmanın dış saha savunma zafiyeti
    ev_ic_saha = df[df['H'] == ev]
    dep_dis_saha = df[df['A'] == dep]

    if ev_ic_saha.empty or dep_dis_saha.empty:
        # Yeterli veri yoksa genel ortalamaya dön
        ev_beklenen = 1.5
        dep_beklenen = 1.1
    else:
        # Hücum ve Savunma Katsayıları Hesaplama
        ev_hucum_surp = ev_ic_saha['HG'].mean() / lig_ev_gol_ort
        dep_savunma_surp = dep_dis_saha['HG'].mean() / lig_ev_gol_ort # Rakibe ne kadar gol izni veriyor?
        
        dep_hucum_surp = dep_dis_saha['AG'].mean() / lig_dep_gol_ort
        ev_savunma_surp = ev_ic_saha['AG'].mean() / lig_dep_gol_ort

        # Nihai xG Tahmini
        ev_beklenen = ev_hucum_surp * dep_savunma_surp * lig_ev_gol_ort
        dep_beklenen = dep_hucum_surp * ev_savunma_surp * lig_dep_gol_ort

    # 3. Poisson Matrisi
    m = np.outer([poisson.pmf(i, ev_beklenen) for i in range(6)], [poisson.pmf(i, dep_beklenen) for i in range(6)])
    sk = np.unravel_index(np.argmax(m), m.shape)

    return {
        "Ev": np.sum(np.tril(m, -1))*100, "Ber": np.sum(np.diag(m))*100, "Dep": np.sum(np.triu(m, 1))*100,
        "Skor": f"{sk[0]} - {sk[1]}", "ev_xg": ev_beklenen, "dep_xg": dep_beklenen
    }

# --- DİĞER FONKSİYONLAR (Oran & Maç Çekme) ---
@st.cache_data(ttl=3600)
def oranlari_cek(lig_odds):
    url = f"https://api.the-odds-api.com/v4/sports/{lig_odds}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
    try: return requests.get(url, timeout=10).json()
    except: return []

@st.cache_data(ttl=3600)
def maclari_getir(lig_code):
    url = f"https://api.football-data.org/v4/competitions/{lig_code}/matches"
    try: return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=10).json().get('matches', [])
    except: return []

# --- ARAYÜZ ---
st.title("🛡️ UltraSkor Pro AI: Derin Rakip Analizi")

lig_mapping = {
    "İngiltere (PL)": {"code": "PL", "odds": "soccer_epl"},
    "İspanya (PD)": {"code": "PD", "odds": "soccer_spain_la_liga"},
    "İtalya (SA)": {"code": "SA", "odds": "soccer_italy_serie_a"},
    "Almanya (BL1)": {"code": "BL1", "odds": "soccer_germany_bundesliga"}
}
secim = st.sidebar.selectbox("🎯 Lig Seç", list(lig_mapping.keys()))
m_data = maclari_getir(lig_mapping[secim]['code'])
canli_oranlar = oranlari_cek(lig_mapping[secim]['odds'])
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

# --- ANALİZ VE GÖSTERİM ---
if gelecek:
    st.markdown("### 🏟️ Derinleştirilmiş Maç Analizleri")
    for m in gelecek[:8]:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = derin_analiz_et(ev, dep, m_data)
        
        with st.expander(f"🔍 {ev} vs {dep} | Taktiksel Görünüm"):
            col_img1, col_center, col_img2 = st.columns([1, 2, 1])
            with col_img1: st.image(m['homeTeam']['crest'], width=60)
            with col_center: st.markdown(f"<h3 style='text-align: center;'>{ev} - {dep}</h3>", unsafe_allow_html=True)
            with col_img2: st.image(m['awayTeam']['crest'], width=60)

            # Detaylı İstatistik Kartları
            st.markdown("#### 📊 Maç Dinamikleri")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='stat-card'>🔥 Ev Hücum Gücü<br><b>{res['ev_xg']:.2f} Beklenen Gol</b></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='stat-card'>🛡️ Savunma Dengesi<br><b>%{(res['Ber']):.1f} Beraberlik Riski</b></div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div class='stat-card'>🚀 Dep. Kontra Şansı<br><b>{res['dep_xg']:.2f} Beklenen Gol</b></div>", unsafe_allow_html=True)
            
            # Oran Karşılaştırma (Value Bet)
            mac_orani = next((o for o in canli_oranlar if ev[:5].lower() in o['home_team'].lower() or o['home_team'][:5].lower() in ev.lower()), None)
            if mac_orani:
                h2h = mac_orani['bookmakers'][0]['markets'][0]['outcomes']
                oran_ev = next((o['price'] for o in h2h if o['name'].lower() == mac_orani['home_team'].lower()), 1.0)
                avantaj = ((res['Ev'] / 100) * oran_ev) - 1
                if avantaj > 0.07:
                    st.success(f"💎 DEĞERLİ FIRSAT: %{avantaj*100:.1f} Avantaj Tespit Edildi!")

            st.progress(res['Ev']/100)
            st.write(f"**🤖 AI Skor Tahmini:** {res['Skor']}")
