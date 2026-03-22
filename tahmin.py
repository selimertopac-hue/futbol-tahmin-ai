import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: AI vs Spectrum", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 12px; }
    .match-result { font-size: 1.4rem; font-weight: bold; color: #58A6FF; text-align: center; background: #21262d; border-radius: 5px; padding: 5px; border: 1px solid #30363d; }
    .match-time { font-size: 1rem; color: #8B949E; text-align: center; font-weight: bold; }
    .strategy-box { background-color: #0d1117; border-left: 4px solid #F85149; padding: 10px; border-radius: 5px; font-size: 0.85rem; margin-top: 10px; }
    .prediction-label { font-size: 0.7rem; color: #8B949E; text-transform: uppercase; margin-bottom: 2px; }
    h1, h2, h3 { color: #58A6FF !important; }
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
            "ai_std": get_skor(e_xg, d_xg),
            "spectrum": get_skor(f_e_xg, f_d_xg),
            "ev_xg": e_xg, "dep_xg": d_xg,
            "ev_not": "🛡️ Katı" if e_sav < 1 else "⚠️ Kırılgan",
            "dep_not": "⚔️ Fırsatçı" if d_bit > 1.2 else "🐢 Kısır"
        }
    except: return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def veri_getir(url):
    try:
        return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

# --- 5. SIDEBAR ---
st.sidebar.title("🛡️ UltraSkor Kontrol")
lig_map = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
lig_secim = st.sidebar.selectbox("🎯 Ligi Seçin", list(lig_map.keys()))

data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_map[lig_secim]}/matches")
m_data = data.get('matches', [])

if m_data:
    haftalar = sorted(list(set([m['matchday'] for m in m_data if m['matchday'] is not None])), reverse=True)
    mevcut_hafta = max([m['matchday'] for m in m_data if m['status'] == 'FINISHED'] or [1])
    hafta_secim = st.sidebar.selectbox("📅 Haftayı Seçin", haftalar, index=haftalar.index(mevcut_hafta) if mevcut_hafta in haftalar else 0)

    # --- 6. ANA EKRAN ---
    st.title(f"{lig_secim} - {hafta_secim}. Hafta")
    haftanin_maclari = [m for m in m_data if m['matchday'] == hafta_secim]
    
    for m in haftanin_maclari:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = master_analiz_et(ev, dep, m_data)
        
        if res:
            # Maç saati formatı (UTC'den 3 saat ekleyerek TR saati gibi düşünebiliriz ama API ham verisini basalım)
            m_saat = m['utcDate'][11:16]
            
            st.markdown(f"""
            <div class="match-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center; width: 30%;">
                        <img src="{m['homeTeam']['crest']}" width="40"><br>
                        <b>{ev}</b><br><span style="font-size:0.7rem; color:#8B949E;">xG: {res['ev_xg']:.2f}</span>
                    </div>
                    
                    <div style="width: 30%; text-align: center;">
                        {f'<div class="match-result">{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}</div>' if m['status']=='FINISHED' 
                         else f'<div class="match-time">🕒 {m_saat}</div>'}
                    </div>
                    
                    <div style="text-align: center; width: 30%;">
                        <img src="{m['awayTeam']['crest']}" width="40"><br>
                        <b>{dep}</b><br><span style="font-size:0.7rem; color:#8B949E;">xG: {res['dep_xg']:.2f}</span>
                    </div>
                </div>
                
                <div style="display: flex; justify-content: space-around; margin-top: 15px; border-top: 1px solid #30363d; padding-top: 10px;">
                    <div style="text-align: center;">
                        <div class="prediction-label">🤖 Standart AI</div>
                        <div style="font-weight: bold; color: #C9D1D9;">{res['ai_std']}</div>
                    </div>
                    <div style="text-align: center;">
                        <div class="prediction-label">🛡️ Spektrum AI</div>
                        <div style="font-weight: bold; color: #58A6FF;">{res['spectrum']}</div>
                    </div>
                </div>

                <div class="strategy-box">
                    💡 <b>Spektrum Karakteri:</b> {res['ev_not']} Savunma vs {res['dep_not']} Hücum
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.error("Veri alınamadı, lütfen API anahtarınızı veya internetinizi kontrol edin.")
