import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API & TELEGRAM AYARLARI ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
ODDS_API_KEY = "b4040bb05379cd7d9b94f18f2b74b133"
TELEGRAM_TOKEN = "BURAYA_TOKENINI_YAPISTIR" 
TELEGRAM_CHAT_ID = "BURAYA_CHAT_ID_YAPISTIR" 

st.set_page_config(page_title="UltraSkor Pro AI", page_icon="📈", layout="wide")

# --- STİL AYARLARI ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .best-card { background: #161B22; border: 1px solid #30363D; padding: 15px; border-radius: 12px; text-align: center; }
    .form-circle { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #58A6FF; padding: 10px; border-radius: 5px; margin-top: 10px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- GELİŞMİŞ ANALİZ MOTORU ---
def gelismis_analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None
    
    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score'].apply(lambda x: x['fullTime']['home']), df['score'].apply(lambda x: x['fullTime']['away'])
    
    # Lig Ortalamaları
    lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
    
    # Takım Verileri
    ev_m = df[df['H'] == ev]
    dep_m = df[df['A'] == dep]
    
    if ev_m.empty or dep_m.empty: return None

    # 1. STANDART xG HESABI (Mevcut Model)
    ev_hucum_gucu = ev_m['HG'].mean() / lig_ev_ort
    dep_sav_zafiyet = dep_m['HG'].mean() / lig_ev_ort
    ev_beklenen = ev_hucum_gucu * dep_sav_zafiyet * lig_ev_ort
    
    dep_hucum_gucu = dep_m['AG'].mean() / lig_dep_ort
    ev_sav_zafiyet = ev_m['AG'].mean() / lig_dep_ort
    dep_beklenen = dep_hucum_gucu * ev_sav_zafiyet * lig_dep_ort

    # 2. VERİMLİLİK FİLTRESİ (Senin istediğin ekleme)
    # Ev sahibi attığı golleri beklentisinin ne kadar üstünde/altında atmış?
    ev_verimlilik = ev_m['HG'].sum() / (ev_m['HG'].count() * ev_beklenen) if ev_beklenen > 0 else 1
    dep_direnc = dep_m['AG'].sum() / (dep_m['AG'].count() * dep_beklenen) if dep_beklenen > 0 else 1
    
    # Stratejik xG Düzeltmesi
    strat_ev_xg = ev_beklenen * ev_verimlilik
    strat_dep_xg = dep_beklenen * dep_direnc

    # Olasılık Matrisleri
    def get_probs(ex, ax):
        m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
        sk = np.unravel_index(np.argmax(m), m.shape)
        return {"Ev": np.sum(np.tril(m, -1))*100, "Ber": np.sum(np.diag(m))*100, "Dep": np.sum(np.triu(m, 1))*100, "Skor": f"{sk[0]} - {sk[1]}"}

    return {
        "standart": get_probs(ev_beklenen, dep_beklenen),
        "stratejik": get_probs(strat_ev_xg, strat_dep_xg),
        "ev_xg": ev_beklenen, "dep_xg": dep_beklenen,
        "ev_eff": ev_verimlilik, "dep_eff": dep_direnc
    }

# --- DİĞER FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def veri_getir(url, headers={}):
    try: return requests.get(url, headers=headers, timeout=10).json()
    except: return {}

def form_html_yap(takim, matches):
    son_maclar = [m for m in matches if (m['homeTeam']['name'] == takim or m['awayTeam']['name'] == takim) and m['status'] == 'FINISHED']
    son_maclar = sorted(son_maclar, key=lambda x: x['utcDate'], reverse=True)[:5]
    html = ""
    for m in son_maclar:
        res = "win" if (m['homeTeam']['name'] == takim and m['score']['fullTime']['home'] > m['score']['fullTime']['away']) or (m['awayTeam']['name'] == takim and m['score']['fullTime']['away'] > m['score']['fullTime']['home']) else ("draw" if m['score']['fullTime']['home'] == m['score']['fullTime']['away'] else "loss")
        html += f"<span class='form-circle {res}'></span>"
    return html

# --- ARAYÜZ ---
st.title("🛡️ UltraSkor Pro: Çift Filtreli Analiz")

lig_mapping = {
    "İngiltere (PL)": {"code": "PL", "odds": "soccer_epl"},
    "İspanya (PD)": {"code": "PD", "odds": "soccer_spain_la_liga"},
    "İtalya (SA)": {"code": "SA", "odds": "soccer_italy_serie_a"},
    "Almanya (BL1)": {"code": "BL1", "odds": "soccer_germany_bundesliga"},
    "Fransa (FL1)": {"code": "FL1", "odds": "soccer_france_ligue_one"},
    "Hollanda (DED)": {"code": "DED", "odds": "soccer_netherlands_ere_divisie"}
}

secim = st.sidebar.selectbox("🎯 Lig", list(lig_mapping.keys()))
m_data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_mapping[secim]['code']}/matches", {"X-Auth-Token": FOOTBALL_DATA_KEY}).get('matches', [])
o_data = veri_getir(f"https://api.the-odds-api.com/v4/sports/{lig_mapping[secim]['odds']}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h")
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

if gelecek:
    for m in gelecek[:12]:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = gelismis_analiz_et(ev, dep, m_data)
        
        if res:
            with st.expander(f"🏟️ {ev} vs {dep}"):
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.markdown("#### 🤖 Yapay Zeka Tahminleri")
                    sub1, sub2 = st.columns(2)
                    with sub1:
                        st.write("**📍 Standart Tahmin**")
                        st.info(f"Skor: {res['standart']['Skor']}")
                        st.write(f"Kazanma: %{res['standart']['Ev']:.1f}")
                    with sub2:
                        st.write("**🎯 Stratejik Filtre**")
                        st.success(f"Skor: {res['stratejik']['Skor']}")
                        st.write(f"Kazanma: %{res['stratejik']['Ev']:.1f}")
                    
                    st.markdown(f"<div class='strategy-box'>💡 <b>Analiz Notu:</b> Ev sahibi iç sahada beklenen golün {res['ev_eff']:.2f} katı verimlilikle oynuyor.</div>", unsafe_allow_html=True)

                with c2:
                    st.image(m['homeTeam']['crest'], width=40)
                    st.markdown(f"Form: {form_html_yap(ev, m_data)}", unsafe_allow_html=True)
                    st.write(f"xG: {res['ev_xg']:.2f}")
                    st.divider()
                    st.image(m['awayTeam']['crest'], width=40)
                    st.markdown(f"Form: {form_html_yap(dep, m_data)}", unsafe_allow_html=True)
                    st.write(f"xG: {res['dep_xg']:.2f}")
