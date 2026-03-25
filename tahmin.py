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

# --- SİTE MİLAT AYARI (BURASI KRİTİK) ---
# Sitemizin 1. haftası, liglerin 25. haftasına denk geliyor.
SİTE_BASLANGIC_LIG_HAFTASI = 25 

st.set_page_config(page_title="UltraSkor Pro: Global VIP", page_icon="🌍", layout="wide")

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

        r_s = get_skor(std_e_xg, std_d_xg)
        r_sp = get_skor(spec_e_xg, spec_d_xg)
        r_nx = get_skor(spec_e_xg * 1.1, spec_d_xg * 0.9)
        return {"std": r_s[0], "s_c": r_s[1], "spec": r_sp[0], "sp_c": r_sp[1], "nexus": r_nx[0], "n_c": r_nx[1]}
    except: return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def lig_verisi_al(lig_kodu):
    try:
        r = requests.get(f"https://api.football-data.org/v4/competitions/{lig_kodu}/matches", 
                         headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15)
        return r.json()
    except: return {}

def winner(skor_str):
    p = skor_str.split(" - ")
    return "1" if int(p[0]) > int(p[1]) else ("2" if int(p[1]) > int(p[0]) else "X")

def tahminler_acik_mi():
    simdi = datetime.now()
    if simdi.weekday() < 4: return False
    if simdi.weekday() == 4 and simdi.hour < 12: return False
    return True

# --- 5. SIDEBAR & MANTIK ---
st.sidebar.title("🌍 Global UltraSkor")
filtre = st.sidebar.radio("🚀 Mod Seçimi:", ["Lig Odaklı", "Standart AI (Global)", "Spektrum AI (Global)", "Nexus AI (Global)"])

all_data = {lig: lig_verisi_al(kod) for lig, kod in LIGLER.items()}

if filtre == "Lig Odaklı":
    lig_adi = st.sidebar.selectbox("🎯 Lig Seçin", list(LIGLER.keys()))
    l_m = all_data[lig_adi].get('matches', [])
    if l_m:
        # LİGİN TÜM HAFTALARI (1'den 38'e kadar ne varsa)
        h_liste = sorted(list(set([m['matchday'] for m in l_m if m['matchday']])))
        biten_mds = [m['matchday'] for m in l_m if m['status'] == 'FINISHED']
        guncel_h = max(biten_mds) if biten_mds else 1
        h_secim = st.sidebar.selectbox("📅 Lig Haftası", h_liste, index=h_liste.index(guncel_h))
        
        st.title(f"🏆 {lig_adi} - {h_secim}. Hafta")
        
        # Gelecek maç kontrolü
        if h_secim > guncel_h and not tahminler_acik_mi():
            st.markdown('<div class="lock-box">🔒 Gelecek haftanın tahminleri Cuma 12:00\'de yayınlanacaktır.</div>', unsafe_allow_html=True)
        else:
            for m in [x for x in l_m if x['matchday'] == h_secim]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], l_m)
                if res:
                    sc_h, sc_a = m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"]
                    mid = f"<h3>{sc_h} - {sc_a}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                    st.markdown(f"""<div class="match-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div><div style="width: 30%; text-align: center;">{mid}</div><div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div></div><div style="display: flex; justify-content: space-around; margin-top: 15px;"><div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div><div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}</b></div><div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b></div></div></div>""", unsafe_allow_html=True)
else:
    # GLOBAL MOD (BİZİM SİTENİN HAFTASI)
    algo_label = filtre.replace(' (Global)', '')
    st.sidebar.markdown("---")
    
    # ŞU AN LİGLER KAÇINCI HAFTADA? (Ortalama 26 diyelim)
    # Sitemizin güncel haftası = (Lig Haftası - Başlangıç Haftası) + 1
    # Eğer lig 25 ise (25-25)+1 = 1. hafta. Eğer lig 26 ise (26-25)+1 = 2. hafta.
    mds = []
    for d in all_data.values():
        f = [m['matchday'] for m in d.get('matches', []) if m['status'] == 'FINISHED']
        if f: mds.append(max(f))
    gercek_lig_h = max(mds) if mds else SİTE_BASLANGIC_LIG_HAFTA
    
    site_aktif_haftasi = (gercek_aktif_h - SİTE_BASLANGIC_LIG_HAFTASI) + 1
    # Gelecek haftayı da ekleyelim (2. hafta)
    site_maks_hafta = site_aktif_haftasi + 1 
    
    site_h_secim = st.sidebar.selectbox("📅 Sitemiz: Kaçıncı Hafta?", range(1, site_maks_hafta + 1), index=site_maks_hafta-1)
    st.title(f"🚀 {algo_label} - {site_h_secim}. Hafta Global Analizi")
    
    # Seçilen site haftasının ligdeki karşılığı
    karsilik_lig_h = (site_h_secim + SİTE_BASLANGIC_LIG_HAFTASI) - 1
    
    if site_h_secim == site_maks_hafta and not tahminler_acik_mi():
        st.markdown(f'<div class="lock-box">🔒 Sitemizin {site_h_secim}. hafta tahminleri Cuma 12:00\'de yayınlanacaktır.</div>', unsafe_allow_html=True)
    else:
        global_list = []
        with st.spinner("Tüm ligler taranıyor..."):
            for l_ad, l_data_raw in all_data.items():
                l_m = l_data_raw.get('matches', [])
                for m in [x for x in l_m if x['matchday'] == karsilik_lig_h]:
                    res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], l_m)
                    if res:
                        p = res['s_c'] if "Standart" in filtre else (res['sp_c'] if "Spektrum" in filtre else res['n_c'])
                        m.update({'res': res, 'l_ad': l_ad, 'puan': p})
                        global_list.append(m)
        
        global_list = sorted(global_list, key=lambda x: x['puan'], reverse=True)[:20]
        isabet, biten = 0, 0
        for m in global_list:
            if m['status'] == 'FINISHED':
                biten += 1
                gw = "1" if m['score']['fullTime']['home'] > m['score']['fullTime']['away'] else ("2" if m['score']['fullTime']['away'] > m['score']['fullTime']['home'] else "X")
                t = m['res']['std'] if "Standart" in filtre else (m['res']['spec'] if "Spektrum" in filtre else m['res']['nexus'])
                if winner(t) == gw: isabet += 1

        st.markdown(f"""<div class="score-banner"><h2 style="margin:0;">Sitemiz {site_h_secim}. Hafta Başarı Karnesi</h2><div style="display:flex; justify-content:center; gap:30px; margin-top:10px;"><div><small>Biten</small><br><b style="font-size:1.5rem;">{biten}</b></div><div><small>Doğru</small><br><b style="font-size:1.5rem; color:#238636;">{isabet}</b></div><div><small>Oran</small><br><b style="font-size:1.5rem; color:#f85149;">%{int((isabet/biten)*100) if biten>0 else 0}</b></div></div></div>""", unsafe_allow_html=True)

        for m in global_list:
            res = m['res']
            c_s, c_sp, c_nx = "", "", ""
            if m['status'] == 'FINISHED':
                gw = "1" if m['score']['fullTime']['home'] > m['score']['fullTime']['away'] else ("2" if m['score']['fullTime']['away'] > m['score']['fullTime']['home'] else "X")
                if winner(res['std']) == gw: c_s = " ✅"
                if winner(res['spec']) == gw: c_sp = " ✅"
                if winner(res['nexus']) == gw: c_nx = " ✅"
                sc_h, sc_a = m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"]
                m_panel = f"<h3>{sc_h} - {sc_a}</h3>"
            else:
                m_panel = f"🕒 {m['utcDate'][11:16]}"

            st.markdown(f"""<div class="match-card"><div class="rank-badge">🔥 Güven: %{m['puan']}</div><div class="league-label">{m['l_ad']} - Lig Haftası {m['matchday']}</div><div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;"><div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div><div style="width: 30%; text-align: center;">{m_panel}</div><div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div></div><div style="display: flex; justify-content: space-around; margin-top: 15px;"><div class="prediction-box {'active-algo' if 'Standart' in filtre else ''}">🤖 STD<br><b>{res['std']}{c_s}</b></div><div class="prediction-box {'active-algo' if 'Spektrum' in filtre else ''}">🛡️ SPEC<br><b>{res['spec']}{c_sp}</b></div><div class="prediction-box {'active-algo' if 'Nexus' in filtre else ''}">🔥 NEXUS<br><b>{res['nexus']}{c_nx}</b></div></div></div>""", unsafe_allow_html=True)
