import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
LIGLER = {
    "İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", 
    "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"
}

st.set_page_config(page_title="UltraSkor Pro: Global VIP", page_icon="🌍", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .rank-badge { position: absolute; top: 10px; right: 10px; background: #238636; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .league-label { font-size: 0.7rem; color: #8B949E; text-transform: uppercase; margin-bottom: 5px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .active-algo { border: 1.5px solid #58A6FF !important; background: rgba(88, 166, 255, 0.1); }
    .conf-txt { font-size: 0.7rem; color: #58A6FF; font-weight: bold; }
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

        s_sk, s_cf = get_skor(std_e_xg, std_d_xg)
        sp_sk, sp_cf = get_skor(spec_e_xg, spec_d_xg)
        nx_sk, nx_cf = get_skor(spec_e_xg * 1.1, spec_d_xg * 0.9)

        return {"std": s_sk, "s_c": s_cf, "spec": sp_sk, "sp_c": sp_cf, "nexus": nx_sk, "n_c": nx_cf, "e_xg": std_e_xg, "d_xg": std_d_xg}
    except: return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def lig_verisi_al(lig_kodu):
    try:
        return requests.get(f"https://api.football-data.org/v4/competitions/{lig_kodu}/matches", 
                            headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

# --- 5. SIDEBAR ---
st.sidebar.title("🌍 Global UltraSkor")
filtre = st.sidebar.radio("🚀 Mod Seçimi:", ["Lig Odaklı", "Standart AI (Global)", "Spektrum AI (Global)", "Nexus AI (Global)"])

if filtre == "Lig Odaklı":
    lig_adi = st.sidebar.selectbox("🎯 Lig Seçin", list(LIGLER.keys()))
    data = lig_verisi_al(LIGLER[lig_adi])
    m_data = data.get('matches', [])
    
    if m_data:
        haftalar = sorted(list(set([m['matchday'] for m in m_data if m['matchday'] is not None])), reverse=True)
        mevcut = max([m['matchday'] for m in m_data if m['status'] == 'FINISHED'] or [1])
        hafta_secim = st.sidebar.selectbox("📅 Hafta", haftalar, index=haftalar.index(mevcut))
        
        st.title(f"🏆 {lig_adi} - {hafta_secim}. Hafta")
        for m in [x for x in m_data if x['matchday'] == hafta_secim]:
            res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_data)
            if res:
                st.markdown(f"""
                <div class="match-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div>
                        <div style="width: 30%; text-align: center;">{f'<h3>{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}</h3>' if m['status']=='FINISHED' else f'🕒 {m["utcDate"][11:16]}'}</div>
                        <div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div>
                    </div>
                    <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                        <div class="prediction-box">🤖 STD<br><b>{res['std']}</b><br><span class="conf-txt">%{res['s_c']}</span></div>
                        <div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}</b><br><span class="conf-txt">%{res['sp_c']}</span></div>
                        <div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b><br><span class="conf-txt">%{res['n_c']}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
else:
    # GLOBAL TARAMA MODU
    st.title(f"🚀 Global En İyi 20 ({filtre.replace('(Global)','')})")
    st.info("Tüm Avrupa ligleri taranıyor, %85+ güvenli maçlar listeleniyor...")
    
    global_list = []
    with st.spinner("Veriler analiz ediliyor..."):
        for l_ad, l_kod in LIGLER.items():
            l_data = lig_verisi_al(l_kod).get('matches', [])
            mevcut_h = max([x['matchday'] for x in l_data if x['status'] == 'FINISHED'] or [1])
            # Gelecek maçları tara
            for m in [x for x in l_data if x['matchday'] >= mevcut_h and x['status'] != 'FINISHED']:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], l_data)
                if res:
                    # Filtreye göre puan seç
                    puan = res['s_c'] if "Standart" in filtre else (res['sp_c'] if "Spektrum" in filtre else res['n_c'])
                    if puan >= 85:
                        m['res'] = res
                        m['l_ad'] = l_ad
                        m['puan'] = puan
                        global_list.append(m)
    
    # En yüksek 20'yi sırala
    global_list = sorted(global_list, key=lambda x: x['puan'], reverse=True)[:20]
    
    if global_list:
        for m in global_list:
            res = m['res']
            st.markdown(f"""
            <div class="match-card">
                <div class="rank-badge">🔥 Güven: %{m['puan']}</div>
                <div class="league-label">{m['l_ad']} - {m['matchday']}. Hafta</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;">
                    <div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div>
                    <div style="width: 30%; text-align: center; color:#8B949E; font-weight:bold;">🕒 {m['utcDate'][11:16]}</div>
                    <div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div>
                </div>
                <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                    <div class="prediction-box {'active-algo' if 'Standart' in filtre else ''}">🤖 STD<br><b>{res['std']}</b></div>
                    <div class="prediction-box {'active-algo' if 'Spektrum' in filtre else ''}">🛡️ SPEC<br><b>{res['spec']}</b></div>
                    <div class="prediction-box {'active-algo' if 'Nexus' in filtre else ''}">🔥 NEXUS<br><b>{res['nexus']}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Şu an %85 üzeri güven puanına sahip maç bulunamadı.")
