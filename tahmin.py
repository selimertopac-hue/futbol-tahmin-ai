import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR & API ANAHTARLARI ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
# Telegram kullanacaksan buraları doldurabilirsin
TELEGRAM_TOKEN = "BURAYA_TOKEN_GIR"
TELEGRAM_CHAT_ID = "BURAYA_ID_GIR"

st.set_page_config(page_title="UltraSkor Pro: Spectrum Archive", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .form-circle { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 8px; margin-top: 10px; }
    .match-result { font-size: 1.2rem; font-weight: bold; color: #FFFFFF; text-align: center; background: #21262d; border-radius: 5px; padding: 5px; border: 1px solid #30363d; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU (SPEKTRUM ANALİZİ) ---
def master_analiz_et(ev_ad, dep_ad, matches):
    try:
        df_raw = [m for m in matches if m['status'] == 'FINISHED']
        if not df_raw: return None
        
        df = pd.DataFrame()
        df['H'] = [m['homeTeam']['name'] for m in df_raw]
        df['A'] = [m['awayTeam']['name'] for m in df_raw]
        df['HG'] = [int(m['score']['fullTime']['home']) if m['score']['fullTime']['home'] is not None else 0 for m in df_raw]
        df['AG'] = [int(m['score']['fullTime']['away']) if m['score']['fullTime']['away'] is not None else 0 for m in df_raw]
        
        lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
        ev_m, dep_m = df[df['H'] == ev_ad], df[df['A'] == dep_ad]
        
        if ev_m.empty or dep_m.empty:
            ev_std_xg, dep_std_xg = 1.3, 1.1
            ev_bit, dep_bit, ev_sav, dep_sav = 1.0, 1.0, 1.0, 1.0
        else:
            ev_std_xg = (ev_m['HG'].mean() / lig_ev_ort) * (dep_m['HG'].mean() / lig_ev_ort) * lig_ev_ort
            dep_std_xg = (dep_m['AG'].mean() / lig_dep_ort) * (ev_m['AG'].mean() / lig_dep_ort) * lig_dep_ort
            ev_bit = ev_m['HG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)
            dep_bit = dep_m['AG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)
            ev_sav = ev_m['AG'].mean() / (lig_dep_ort * (ev_m['AG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)))
            dep_sav = dep_m['HG'].mean() / (lig_ev_ort * (dep_m['HG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)))

        f_ev_xg, f_dep_xg = ev_std_xg * ev_bit * dep_sav, dep_std_xg * dep_bit * ev_sav

        def get_probs(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return {"Ev": np.sum(np.tril(m, -1))*100, "Skor": f"{sk[0]} - {sk[1]}"}

        return {
            "alg_1": get_probs(ev_std_xg, dep_std_xg),
            "alg_3": get_probs(final_ev_xg if 'final_ev_xg' in locals() else f_ev_xg, final_dep_xg if 'final_dep_xg' in locals() else f_dep_xg),
            "ev_xg": ev_std_xg, "dep_xg": dep_std_xg,
            "ev_not": "🛡️ Katı" if ev_sav < 1 else "⚠️ Kırılgan",
            "dep_not": "⚔️ Fırsatçı" if dep_bit > 1.2 else "🐢 Kısır"
        }
    except: return None

# --- 4. GÖRSEL FONKSİYONLAR ---
def form_html_uret(takim, matches):
    son_maclar = [m for m in matches if (m['homeTeam']['name'] == takim or m['awayTeam']['name'] == takim) and m['status'] == 'FINISHED']
    son_maclar = sorted(son_maclar, key=lambda x: x['utcDate'], reverse=True)[:5]
    html = ""
    for m in son_maclar:
        h, a = m['score']['fullTime']['home'], m['score']['fullTime']['away']
        res = "win" if (m['homeTeam']['name'] == takim and h > a) or (m['awayTeam']['name'] == takim and a > h) else ("draw" if h == a else "loss")
        html += f"<span class='form-circle {res}'></span>"
    return html

# --- 5. ANA PANEL ---
st.title("🛡️ UltraSkor Pro AI: Spectrum Archive")

lig_mapping = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
secim = st.sidebar.selectbox("🎯 Lig Seçimi", list(lig_mapping.keys()))

@st.cache_data(ttl=3600)
def veri_getir(url):
    return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}).json()

data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_mapping[secim]}/matches")
m_data = data.get('matches', [])

if m_data:
    # Hafta Seçici Sistemi
    haftalar = sorted(list(set([m['matchday'] for m in m_data if m['matchday'] is not None])))
    mevcut_hafta = max([m['matchday'] for m in m_data if m['status'] == 'FINISHED'] or [1])
    secilen_hafta = st.sidebar.select_slider("📅 Hafta Seçimi", options=haftalar, value=mevcut_hafta)
    
    st.markdown(f"### 📊 {secim} Ligi - {secilen_hafta}. Hafta")
    haftanin_maclari = [m for m in m_data if m['matchday'] == secilen_hafta]

    for m in haftanin_maclari:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = master_analiz_et(ev, dep, m_data)
        
        if res:
            with st.expander(f"{'✅' if m['status']=='FINISHED' else '⏳'} {ev} vs {dep}"):
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    st.image(m['homeTeam']['crest'], width=45)
                    st.markdown(f"Form: {form_html_uret(ev, m_data)}", unsafe_allow_html=True)
                    st.caption(f"xG: {res['ev_xg']:.2f}")
                with c2:
                    if m['status'] == 'FINISHED':
                        st.markdown(f"<div class='match-result'>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</div>", unsafe_allow_html=True)
                        st.markdown("<p style='text-align:center; font-size:0.7rem;'>MAÇ SONUCU</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='text-
