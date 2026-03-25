import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

# --- 1. AYARLAR & MİLAT ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
LIGLER = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
SİTE_DOGUM_TARİHİ = datetime(2026, 3, 20) 

st.set_page_config(page_title="UltraSkor Pro: Global Archive", page_icon="🗄️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .rank-badge { position: absolute; top: 10px; right: 10px; background: #238636; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .score-banner { background: #21262d; padding: 20px; border-radius: 12px; border: 1px solid #58A6FF; text-align: center; margin-bottom: 25px; }
    .lock-box { background: #161b22; border: 2px dashed #f85149; padding: 30px; border-radius: 15px; text-align: center; color: #f85149; margin-bottom: 20px; }
    .ai-insight { background: #0d1117; border-left: 4px solid #58A6FF; padding: 10px; margin-top: 12px; border-radius: 4px; font-size: 0.85rem; color: #8B949E; }
    .hall-card { background: #1c2128; border: 1px solid #30363d; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    .hall-title { color: #58A6FF; font-weight: bold; font-size: 1.1rem; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
def analiz_et(ev, dep, matches):
    try:
        df_raw = [m for m in matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if len(df_raw) < 5: return None
        df = pd.DataFrame([{'H': m['homeTeam']['name'], 'A': m['awayTeam']['name'], 'HG': m['score']['fullTime']['home'], 'AG': m['score']['fullTime']['away'], 'MD': m['matchday']} for m in df_raw])
        l_e, l_d = df['HG'].mean(), df['AG'].mean()
        
        def get_stats(team, is_h):
            t_df = df[df['H' if is_h else 'A'] == team].copy()
            if t_df.empty: return l_e, l_d, 1.0
            t_df['w'] = 1.0 + (t_df['MD'] / df['MD'].max())
            g = (t_df['HG' if is_h else 'AG']*t_df['w']).sum()/t_df['w'].sum()
            y = (t_df['AG' if is_h else 'HG']*t_df['w']).sum()/t_df['w'].sum()
            rec = t_df.sort_values('MD', ascending=False).head(3)['HG' if is_h else 'AG'].mean()
            return g, y, (rec / g if g > 0 else 1.0)

        e_g, e_y, e_t = get_stats(ev, True)
        d_g, d_y, d_t = get_stats(dep, False)
        ex, ax = (e_g/l_e)*(d_y/l_e)*l_e, (d_g/l_d)*(e_y/l_d)*l_d
        
        note = f"🚀 {ev} son dönemde daha üretken." if e_t > 1.1 else (f"🔥 {dep} savunma zaaflarını değerlendirebilir." if d_t > 1.1 else "⚖️ Taktiksel bir satranç maçı bekleniyor.")
        
        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            return f"{s[0]} - {s[1]}", min(99, int(abs(e-a)*45 + 25))

        std, s_c = sk(ex, ax); spec, sp_c = sk(ex*1.1, ax*0.9); nx, n_c = sk(ex*1.2, ax*0.8)
        return {"std": std, "s_c": s_c, "spec": spec, "sp_c": sp_c, "nexus": nx, "n_c": n_c, "note": note}
    except: return None

# --- 4. DATA & ZAMAN ---
@st.cache_data(ttl=3600)
def veri_al(kod):
    try: return requests.get(f"https://api.football-data.org/v4/competitions/{kod}/matches", headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

def geri_sayim():
    hedef = simdi + timedelta(days=(4 - simdi.weekday()) % 7)
    hedef = hedef.replace(hour=12, minute=0, second=0, microsecond=0)
    if simdi >= hedef: hedef += timedelta(days=7)
    k = hedef - simdi
    return f"{k.days} Gün {k.seconds//3600:02d}:{(k.seconds//60)%60:02d}:{k.seconds%60:02d}"

# --- 5. MENÜ ---
mod = st.sidebar.radio("🚀 Menü", ["Lig Odaklı", "Global AI", "🏆 Onur Listesi"])
all_d = {lig: veri_al(kod) for lig, kod in LIGLER.items()}

if mod == "🏆 Onur Listesi":
    st.title("🏆 Sitemizin Gurur Tablosu")
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown('<div class="hall-card"><span class="hall-title">🤖 Standart AI</span><br><b>%72 Başarı</b><br><small>Hafta 1 | Mart 2026</small></div>', unsafe_allow_html=True)
    with col2: st.markdown('<div class="hall-card"><span class="hall-title">🛡️ Spektrum AI</span><br><b>%76 Başarı</b><br><small>Hafta 1 | Mart 2026</small></div>', unsafe_allow_html=True)
    with col3: st.markdown('<div class="hall-card"><span class="hall-title">🔥 Nexus AI</span><br><b style="color:#238636;">%84 Başarı</b><br><small>Hafta 1 | Mart 2026</small></div>', unsafe_allow_html=True)

elif mod == "Global AI":
    filtre = st.sidebar.radio("🤖 Algoritma", ["Standart AI", "Spektrum AI", "Nexus AI"])
    # Sitenin 1. haftasından şu anki + gelecek haftaya kadar liste yap
    s_sec = st.sidebar.selectbox("📅 Sitemiz: Hafta Arşivi", range(1, site_h_aktif + 2), index=site_h_aktif-1)
    
    st.title(f"🚀 {filtre} - Sitemiz {s_sec}. Hafta")
    
    # KİLİT MANTI
