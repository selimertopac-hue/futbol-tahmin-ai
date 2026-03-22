import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Archive Edition", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL (Aynı Şıklıkta) ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #58A6FF; padding: 12px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem; }
    .form-circle { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    .match-result { font-size: 1.1rem; font-weight: bold; color: #F85149; text-align: center; background: #21262d; border-radius: 5px; padding: 5px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
def master_analiz_et(ev_ad, dep_ad, all_matches):
    try:
        # Sadece oynanmış maçlar üzerinden analiz yap (Parametreler güncel kalmalı)
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if not df_raw: return None
        
        df = pd.DataFrame()
        df['H'] = [m['homeTeam']['name'] for m in df_raw]
        df['A'] = [m['awayTeam']['name'] for m in df_raw]
        df['HG'] = [int(m['score']['fullTime']['home']) for m in df_raw]
        df['AG'] = [int(m['score']['fullTime']['away']) for m in df_raw]
        
        lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
        ev_m, dep_m = df[df['H'] == ev_ad], df[df['A'] == dep_ad]
        
        if ev_m.empty or dep_m.empty:
            ev_std_xg, dep_std_xg = 1.2, 1.0
            ev_bit, dep_bit, ev_sav, dep_sav = 1.0, 1.0, 1.0, 1.0
        else:
            ev_std_xg = (ev_m['HG'].mean() / lig_ev_ort) * (dep_m['HG'].mean() / lig_ev_ort) * lig_ev_ort
            dep_std_xg = (dep_m['AG'].mean() / lig_dep_ort) * (ev_m['AG'].mean() / lig_dep_ort) * lig_dep_ort
            ev_bit = ev_m['HG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)
            dep_bit = dep_m['AG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)
            ev_sav = ev_m['AG'].mean() / (lig_dep_ort * (ev_m['AG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)))
            dep_sav = dep_m['HG'].mean() / (lig_ev_ort * (dep_m['HG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)))

        f_ev_xg, f_dep_xg = ev_std_xg * ev_bit * dep_sav, dep_std_xg * dep_bit * ev_sav

        def get_skor(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}"

        return {"alg_1": get_skor(ev_std_xg, dep_std_xg), "alg_3": get_skor(f_ev_xg, f_dep_xg), "ev_xg": ev_std_xg, "dep_xg": dep_std_xg}
    except: return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def veri_yukle(lig_kodu):
    url = f"https://api.football-data.org/v4/competitions/{lig_kodu}/matches"
    return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}).json().get('matches', [])

# --- 5. ANA EKRAN ---
st.title("🛡️ UltraSkor Pro: Hafta Bazlı Analiz Arşivi")

ligler = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
sol_c1, sol_c2 = st.sidebar.columns(2)
secilen_lig = sol_c1.selectbox("🎯 Lig", list(ligler.keys()))

m_data = veri_yukle(ligler[secilen_lig])

# HAFTA SEÇİCİ MANTIĞI
if m_data:
    mevcut_hafta = max([m['matchday'] for m in m_data if m['matchday'] is not None])
    secilen_hafta = st.sidebar.slider("📅 Hafta Seçimi", 1, mevcut_hafta, mevcut_hafta)
    
    haftanin_maclari = [m for m in m_data if m['matchday'] == secilen_hafta]
    
    st.subheader(f"📊 {secilen_lig} - {secilen_hafta}. Hafta Analizleri")

    for m in haftanin_maclari:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = master_analiz_et(ev, dep, m_data)
        
        if res:
            with st.expander(f"{'✅' if m['status']=='FINISHED' else '⏳'} {ev} vs {dep}"):
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    st.image(m['homeTeam']['crest'], width=40)
                    st.caption(f"xG: {res['ev_xg']:.2f}")
                
                with col2:
                    if m['status'] == 'FINISHED':
                        st.markdown(f"<div class='match-result'>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</div>", unsafe_allow_html=True)
                        st.markdown("<p style='text-align:center; font-size:0.7rem;'>MAÇ SONUCU</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='text-align:center; font-weight:bold; color:#58A6FF;'>Tahmin: {res['alg_3']}</p>", unsafe_allow_html=True)
                
                with col3:
                    st.image(m['awayTeam']['crest'], width=40)
                    st.caption(f"xG: {res['dep_xg']:.2f}")
                
                st.divider()
                # Alt Tablo (Arşiv Modu)
                c1, c2, c3 = st.columns(3)
                c1.metric("📍 Standart Tahmin", res['alg_1'])
                c2.metric("🛡️ Spektrum Tahmin", res['alg_3'])
                
                # Eğer maç bittiyse başarı kontrolü
                if m['status'] == 'FINISHED':
                    gercek_skor = f"{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}"
                    basari = "🎯 TAM İSABET" if gercek_skor == res['alg_3'] else "📈 ANALİZ TAMAM"
                    c3.write(f"**Durum:** {basari}")
                else:
                    c3.write(f"**Başlama:** {m['utcDate'][11:16]}")
