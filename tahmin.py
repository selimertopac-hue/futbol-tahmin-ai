import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
LIGLER = {
    "İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", 
    "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"
}

# --- MİLAT AYARI (BURAYI DEĞİŞTİREREK BAŞLANGICI AYARLAYABİLİRSİN) ---
# Eğer lig şu an 26. haftadaysa ve biz 1. hafta demek istiyorsak OFFSET = 25 olmalı.
# Geçen hafta ligler ortalama 25. haftadaydı.
LIG_HAFTA_OFFSET = 24 

st.set_page_config(page_title="UltraSkor Pro: Bulletin v1", page_icon="🌍", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .rank-badge { position: absolute; top: 10px; right: 10px; background: #238636; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .active-algo { border: 1.5px solid #58A6FF !important; background: rgba(88, 166, 255, 0.1); }
    .score-banner { background: #21262d; padding: 20px; border-radius: 12px; border: 1px solid #58A6FF; text-align: center; margin-bottom: 25px; }
    .lock-box { background: #21262d; border: 1px dashed #f85149; padding: 20px; border-radius: 12px; text-align: center; color: #f85149; margin-bottom: 20px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
def analiz_et(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if len(df_raw) < 5: return None
        df = pd.DataFrame([{'H': m['homeTeam']['name'], 'A': m['awayTeam']['name'], 
                            'HG': m['score']['fullTime']['home'], 'AG': m['score']['fullTime']['away'], 
                            'MD': m['matchday']} for m in df_raw])
        l_ev_ort, l_dep_ort = df['HG'].mean(), df['AG'].mean()
        max_md = df['MD'].max()

        def get_stats(team, is_home):
            t_df = df[df['H' if is_home else 'A'] == team].copy()
            if t_df.empty: return l_ev_ort, l_dep_ort, 1.0
            t_df['w'] = 1.0 + (t_df['MD'] / max_md)
            g = (t_df['HG' if is_home else 'AG']*t_df['w']).sum()/t_df['w'].sum()
            y = (t_df['AG' if is_home else 'HG']*t_df['w']).sum()/t_df['w'].sum()
            return g, y, t_df['w'].mean()

        e_g, e_y, e_w = get_stats(ev_ad, True)
        d_g, d_y, d_w = get_stats(dep_ad, False)
        std_e_xg = (e_g / l_ev_ort) * (d_y / l_ev_ort) * l_ev_ort
        std_d_xg = (d_g / l_dep_ort) * (e_y / l_dep_ort) * l_dep_ort
        bit = np.clip(((e_g / (std_e_xg if std_e_xg > 0 else 1)) * 0.7) + 0.3, 0.8, 1.3)
        spec_e_xg, spec_d_xg = std_e_xg * bit, std_d_xg * (1.1 if d_w > 1.5 else 0.9)

        def get_skor(ex, ax):
            m = np.outer([poisson.pmf(i, max(0.1, ex)) for i in range(6)], [poisson.pmf(i, max(0.1, ax)) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}", min(99, int(abs(ex-ax)*45 + 25))

        res_s = get_skor(std_e_xg, std_d_xg)
        res_sp = get_skor(spec_e_xg, spec_d_xg)
        res_nx = get_skor(spec_e_xg * 1.1, spec_d_xg * 0.9)

        return {"std": res_s[0], "s_c": res_s[1], "spec": res_sp[0], "sp_c": res_sp[1], "nexus": res_nx[0], "n_c": res_nx[1]}
    except: return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def lig_verisi_al(lig_kodu):
    try:
        return requests.get(f"https://api.football-data.org/v4/competitions/{lig_kodu}/matches", 
                            headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

def winner(skor_str):
    p = skor_str.split(" - ")
    return "1" if int(p[0]) > int(p[1]) else ("2" if int(p[1]) > int(p[0]) else "X")

def tahminler_acik_mi():
    simdi = datetime.now()
    if simdi.weekday() < 4: return False # Paz-Per arası kapalı
    if simdi.weekday() == 4 and simdi.hour < 12: return False # Cuma 12:00 öncesi kapalı
    return True

# --- 5. SIDEBAR ---
st.sidebar.title("🌍 Global UltraSkor")
filtre = st.sidebar.radio("🚀 Mod Seçimi:", ["Lig Odaklı", "Standart AI (Global)", "Spektrum AI (Global)", "Nexus AI (Global)"])

# Bülten sayısını liglerin gerçek haftasından hesapla
all_data = {lig: lig_verisi_al(kod) for lig, kod in LIGLER.items()}
current_max_md = max([max([m['matchday'] for m in d.get('matches', []) if m['matchday']]) for lig, d in all_data.items() if d.get('matches')])

# BİZİM BÜLTENİMİZ = GERÇEK HAFTA - OFFSET
bizim_guncel_bulten = current_max_md - LIG_HAFTA_OFFSET

if filtre == "Lig Odaklı":
    lig_adi = st.sidebar.selectbox("🎯 Lig Seçin", list(LIGLER.keys()))
    l_data = all_data[lig_adi].get('matches', [])
    if l_data:
        # Sadece bizim miladımızdan sonraki haftaları göster
        haftalar = sorted(list(set([m['matchday'] for m in l_data if m['matchday'] and m['matchday'] > LIG_HAFTA_OFFSET])))
        mevcut_h = max([m['matchday'] for m in l_data if m['status'] == 'FINISHED'] or [LIG_HAFTA_OFFSET + 1])
        
        hafta_secim = st.sidebar.selectbox("📅 Hafta", haftalar, index=haftalar.index(mevcut_h) if mevcut_h in haftalar else 0, format_func=lambda x: f"{x - LIG_HAFTA_OFFSET}. Bülten (Hafta {x})")
        
        st.title(f"🏆 {lig_adi} - Bülten {hafta_secim - LIG_HAFTA_OFFSET}")
        
        if hafta_secim > mevcut_h and not tahminler_acik_mi():
            st.markdown('<div class="lock-box">🔒 Bu bültenin tahminleri Cuma 12:00\'de yayınlanacaktır.</div>', unsafe_allow_html=True)
        else:
            for m in [x for x in l_data if x['matchday'] == hafta_secim]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], l_data)
                if res:
                    m_p = f'<h3>{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}</h3>' if m['
