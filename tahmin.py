import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR & API ANAHTARLARI ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
ODDS_API_KEY = "b4040bb05379cd7d9b94f18f2b74b133"

st.set_page_config(page_title="UltraSkor Pro: Full Dashboard", page_icon="📈", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .form-circle { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #58A6FF; padding: 12px; border-radius: 8px; margin-top: 10px; }
    .filter-label { font-size: 0.75rem; font-weight: bold; color: #8B949E; margin-bottom: 5px; text-align: center; text-transform: uppercase; }
    .stat-text { font-size: 0.85rem; color: #8B949E; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. YARDIMCI FONKSİYONLAR ---
def form_html_uret(takim, matches):
    son_maclar = [m for m in matches if (m['homeTeam']['name'] == takim or m['awayTeam']['name'] == takim) and m['status'] == 'FINISHED']
    son_maclar = sorted(son_maclar, key=lambda x: x['utcDate'], reverse=True)[:5]
    html = ""
    for m in son_maclar:
        res = ""
        h_skor = m['score']['fullTime']['home']
        a_skor = m['score']['fullTime']['away']
        if m['homeTeam']['name'] == takim:
            res = "win" if h_skor > a_skor else ("draw" if h_skor == a_skor else "loss")
        else:
            res = "win" if a_skor > h_skor else ("draw" if h_skor == a_skor else "loss")
        html += f"<span class='form-circle {res}'></span>"
    return html

def master_analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None
    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score'].apply(lambda x: x['fullTime']['home']), df['score'].apply(lambda x: x['fullTime']['away'])
    
    lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
    ev_m, dep_m = df[df['H'] == ev], df[df['A'] == dep]
    if ev_m.empty or dep_m.empty: return None

    # Algoritma 1: Standart xG
    ev_std_xg = (ev_m['HG'].mean() / lig_ev_ort) * (dep_m['HG'].mean() / lig_ev_ort) * lig_ev_ort
    dep_std_xg = (dep_m['AG'].mean() / lig_dep_ort) * (ev_m['AG'].mean() / lig_dep_ort) * lig_dep_ort

    # Algoritma 2: Ofansif Verimlilik
    ev_bitiricilik = ev_m['HG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)
    dep_bitiricilik = dep_m['AG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)

    # Algoritma 3: Simetrik Gerçeklik (Senin İstediğin)
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
        "ev_xg": ev_std_xg, "dep_xg": dep_std_xg,
        "ev_not": "Disiplinli" if ev_sav_gercek < 1 else "Kırılgan",
        "dep_not": "Fırsatçı" if dep_bitiricilik > 1.1 else "Kısır"
    }

# --- 4. ANA PANEL & LİGLER ---
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
    try: return requests.get(url, headers=headers, timeout=10).json()
    except: return {}

data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_mapping[secim]['code']}/matches", {"X-Auth-Token": FOOTBALL_DATA_KEY})
m_data = data.get('matches', [])
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

st.title("🛡️ UltraSkor Pro AI: Merkezi Analiz Terminali")

if gelecek:
    for m in gelecek[:15]:
        ev_ad, dep_ad = m['homeTeam']['name'], m['awayTeam']['name']
        res = master_analiz_et(ev_ad, dep_ad, m_data)
        
        if res:
            with st.expander(f"🏟️ {ev_ad} vs {dep_ad}"):
                # Üst Kısım: Logolar ve Formlar
                col_a, col_b, col_c = st.columns([1, 2, 1])
                with col_a:
                    st.image(m['homeTeam']['crest'], width=50)
                    st.markdown(f"Form: {form_html_uret(ev_ad, m_data)}", unsafe_allow_html=True)
                    st.markdown(f"<span class='stat-text'>xG: {res['ev_xg']:.2f}</span>", unsafe_allow_html=True)
                
                with col_b:
                    st.markdown("<p style='text-align:center; font-weight:bold; margin-bottom:0;'>GÜVEN ENDEKSİ</p>", unsafe_allow_html=True)
                    st.progress(res['alg_3']['Ev'] / 100)
                    st.markdown(f"<p style='text-align:center;'>Maç Günü: {m['utcDate'][:10]}</p>", unsafe_allow_html=True)

                with col_c:
                    st.image(m['awayTeam']['crest'], width=50)
                    st.markdown(f"Form: {form_html_uret(dep_ad, m_data)}", unsafe_allow_html=True)
                    st.markdown(f"<span class='stat-text'>xG: {res['dep_xg']:.2f}</span>", unsafe_allow_html=True)

                st.divider()

                # Alt Kısım: 3 Algoritma Tahmini
                f1, f2, f3 = st.columns(3)
                with f1:
                    st.markdown("<p class='filter-label'>📍 Standart xG</p>", unsafe_allow_html=True)
                    st.info(f"Skor: **{res['alg_1']['Skor']}**")
                with f2:
                    st.markdown("<p class='filter-label'>🎯 Ofansif Güç</p>", unsafe_allow_html=True)
                    st.success(f"Skor: **{res['alg_2']['Skor']}**")
                with f3:
                    st.markdown("<p class='filter-label'>🛡️ Simetrik Gerçeklik</p>", unsafe_allow_html=True)
                    st.warning(f"Skor: **{res['alg_3']['Skor']}**")

                st.markdown(f"<div class='strategy-box'>📝 <b>Stratejik Not:</b> {ev_ad} savunması <b>{res['ev_not']}</b>, {dep_ad} hücumu ise <b>{res['dep_not']}</b> yapıda.</div>", unsafe_allow_html=True)
