import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Dashboard", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .form-circle { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    .match-result { font-size: 1.1rem; font-weight: bold; color: #FFFFFF; text-align: center; background: #21262d; border-radius: 5px; padding: 5px; border: 1px solid #30363d; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 8px; margin-top: 10px; font-size: 0.85rem; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. GÜÇLENDİRİLMİŞ ANALİZ MOTORU ---
def master_analiz_et(ev_ad, dep_ad, all_matches):
    try:
        # Oynanmış maçları süz
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        
        # Eğer ligde hiç oynanmış maç yoksa (sezon başı vb) varsayılan verilerle devam et
        if not df_raw:
            lig_ev_ort, lig_dep_ort = 1.5, 1.2
            ev_std_xg, dep_std_xg = 1.4, 1.1
            ev_bit, dep_bit, ev_sav, dep_sav = 1.0, 1.0, 1.0, 1.0
        else:
            df = pd.DataFrame()
            df['H'] = [m['homeTeam']['name'] for m in df_raw]
            df['A'] = [m['awayTeam']['name'] for m in df_raw]
            df['HG'] = [int(m['score']['fullTime']['home']) for m in df_raw]
            df['AG'] = [int(m['score']['fullTime']['away']) for m in df_raw]
            
            lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
            ev_m, dep_m = df[df['H'] == ev_ad], df[df['A'] == dep_ad]
            
            # Takımların verisi eksikse lig ortalamasını kullan
            ev_h_g = ev_m['HG'].mean() if not ev_m.empty else lig_ev_ort
            ev_h_y = ev_m['AG'].mean() if not ev_m.empty else lig_dep_ort
            dep_d_g = dep_m['AG'].mean() if not dep_m.empty else lig_dep_ort
            dep_d_y = dep_m['HG'].mean() if not dep_m.empty else lig_ev_ort

            ev_std_xg = (ev_h_g / lig_ev_ort) * (dep_d_y / lig_ev_ort) * lig_ev_ort
            dep_std_xg = (dep_d_g / lig_dep_ort) * (ev_h_y / lig_dep_ort) * lig_dep_ort
            
            ev_bit = ev_h_g / (ev_std_xg if ev_std_xg > 0 else 1)
            dep_bit = dep_d_g / (dep_std_xg if dep_std_xg > 0 else 1)
            ev_sav = ev_h_y / (lig_dep_ort * (ev_h_y / (ev_std_xg if ev_std_xg > 0 else 1)))
            dep_sav = dep_d_y / (lig_ev_ort * (dep_d_y / (dep_std_xg if dep_std_xg > 0 else 1)))

        # 3. Sütun (Spektrum)
        f_ev_xg = ev_std_xg * ev_bit * dep_sav
        f_dep_xg = dep_std_xg * dep_bit * ev_sav

        def get_skor(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}"

        return {
            "alg_1": get_skor(ev_std_xg, dep_std_xg),
            "alg_3": get_skor(f_ev_xg, f_dep_xg),
            "ev_xg": ev_std_xg, "dep_xg": dep_std_xg,
            "ev_not": "🛡️ Katı" if ev_sav < 1 else "⚠️ Kırılgan",
            "dep_not": "⚔️ Fırsatçı" if dep_bit > 1.2 else "🐢 Kısır"
        }
    except:
        return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def veri_getir(url):
    try:
        r = requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15)
        return r.json()
    except:
        return {}

# --- 5. ANA PANEL ---
st.title("🛡️ UltraSkor Pro: Spectrum Arşivi")

lig_map = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
secim
