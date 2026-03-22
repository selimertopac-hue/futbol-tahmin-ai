import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Archive", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .form-circle { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    .match-result { font-size: 1.1rem; font-weight: bold; color: #FFFFFF; text-align: center; background: #21262d; border-radius: 5px; padding: 5px; border: 1px solid #30363d; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 8px; margin-top: 10px; font-size: 0.85rem; }
    h1, h2, h3 { color: #58A6FF !important; }
    .stExpander { border: 1px solid #30363d !important; background-color: #161b22 !important; margin-bottom: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
def master_analiz_et(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if not df_raw:
            e_xg, d_xg, e_bit, d_bit, e_sav, d_sav = 1.3, 1.1, 1.0, 1.0, 1.0, 1.0
        else:
            df = pd.DataFrame()
            df['H'] = [m['homeTeam']['name'] for m in df_raw]
            df['A'] = [m['awayTeam']['name'] for m in df_raw]
            df['HG'] = [int(m['score']['fullTime']['home']) for m in df_raw]
            df['AG'] = [int(m['score']['fullTime']['away']) for m in df_raw]
            
            l_ev_ort, l_dep_ort = df['HG'].mean(), df['AG'].mean()
            ev_m, dep_m = df[df['H'] == ev_ad], df[df['A'] == dep_ad]
            
            e_h_g = ev_m['HG'].mean() if not ev_m.empty else l_ev_ort
            e_h_y = ev_m['AG'].mean() if not ev_m.empty else l_dep_ort
            d_d_g = dep_m['AG'].mean() if not dep_m.empty else l_dep_ort
            d_d_y = dep_m['HG'].mean() if not dep_m.empty else l_ev_ort

            e_xg = (e_h_g / l_ev_ort) * (d_d_y / l_ev_ort) * l_ev_ort
            d_xg = (d_d_g / l_dep_ort) * (e_h_y / l_dep_ort) * l_dep_ort
            e_bit = e_h_g / (e_xg if e_xg > 0 else 1)
            d_bit = d_d_g / (d_xg if d_xg > 0 else 1)
            e_sav = e_h_y / (l_dep_ort * (e_h_y / (e_xg if e_xg > 0 else 1)))
            d_sav = d_d_y / (l_ev_ort * (d_d_y / (d_xg if d_xg > 0 else 1)))

        f_e_xg, f_d_xg = e_xg * e_bit * d_sav, d_xg * d_bit * e_sav

        def get_skor(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}"

        return {
            "alg_3": get_skor(f_e_xg, f_d_xg),
            "ev_xg": e_xg, "dep_xg": d_xg,
            "ev_not": "🛡️ Katı" if e_sav < 1 else "⚠️ Kırılgan",
            "dep_not": "⚔️ Fırsatçı" if d_bit > 1.2 else "🐢 Kısır"
        }
    except:
        return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def veri_getir(url):
    try:
        return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except:
        return {}

# --- 5. ANA PANEL ---
st.title("🛡️ UltraSkor Pro: Spectrum Arşivi")

lig_map = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
secim = st.sidebar.selectbox("🎯 Lig Seçimi", list(lig_map.keys()))

api_url = f"https://api.football-data.org/v4/competitions/{lig_map[secim]}/matches"
data = veri_getir(api_url)
m_data = data.get('matches', [])

if m_data:
    haftalar = sorted(list(set([m['matchday'] for m in m_data if m['matchday'] is not None])), reverse=True)
    
    for h_no in haftalar:
        is_expanded = (h_no == max(haftalar))
        with st.expander(f"📅 {h_no}. Hafta Maçları", expanded=is_expanded):
            haftanin_maclari = [m for m in m_data if m['matchday'] == h_no]
            for m in haftanin_maclari:
                ev_ad, dep_ad = m['homeTeam']['name'], m['awayTeam']['name']
                res = master_anal_et = master_analiz_et(ev_ad, dep_ad, m_data)
                if res:
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        st.image(m['homeTeam']['crest'], width=35)
                        st.caption(f"{ev_ad}")
                    with col2:
                        if m['status'] == 'FINISHED':
                            st.markdown(f"<div class='match-result'>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<p style='text-align:center; font-weight:bold; color:#58A6FF; margin-bottom:0;'>AI Tahmin: {res['alg_3']}</p>", unsafe_allow_html=True)
                    with col3:
                        st.image(m['awayTeam']['crest'], width=35)
                        st.caption(f"{dep_ad}")
                    st.markdown(f"<div class='strategy-box'>💡 <b>Analiz:</b> {res['ev_not']} Savunma vs {res['dep_not']} Hücum | <b>Spektrum Skoru: {res['alg_3']}</b></div>", unsafe_allow_html=True)
                    st.divider()
