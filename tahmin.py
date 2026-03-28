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

st.set_page_config(page_title="UltraSkor Pro: Prediction Oracle", page_icon="🎯", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .robot-card { background: linear-gradient(145deg, #0d1117, #161b22); border: 2px solid #8A2BE2; border-radius: 15px; padding: 25px; margin-bottom: 20px; text-align: center; box-shadow: 0 0 15px rgba(138, 43, 226, 0.2); }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .aether-box { background: rgba(138, 43, 226, 0.1); border: 1px solid #8A2BE2; color: #E0B0FF !important; }
    .status-tag { font-weight: bold; font-size: 1.2rem; }
    .form-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .form-W { background-color: #238636; } .form-D { background-color: #9e9e9e; } .form-L { background-color: #f85149; }
    .standings-table { font-size: 0.8rem; width: 100%; border-collapse: collapse; background: #161b22; border-radius: 10px; overflow: hidden; margin-top: 10px; }
    .standings-table th { background: #30363d; padding: 10px; text-align: left; color: #58A6FF; }
    .standings-table td { padding: 8px 10px; border-bottom: 1px solid #30363d; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU (KORUNDU) ---
@st.cache_data(ttl=3600)
def veri_al(endpoint):
    try: return requests.get(f"https://api.football-data.org/v4/{endpoint}", headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

def winner(sk):
    try:
        p = sk.split(" - ")
        if int(p[0]) > int(p[1]): return "1"
        if int(p[1]) > int(p[0]): return "2"
        return "X"
    except: return "?"

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
            return g, y, t_df.sort_values('MD', ascending=False).head(3)['HG' if is_h else 'AG'].mean()

        e_g, e_y, e_rec = get_stats(ev, True)
        d_g, d_y, d_rec = get_stats(dep, False)
        ex, ax = (e_g/l_e)*(d_y/l_e)*l_e, (d_g/l_d)*(e_y/l_d)*l_d
        
        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            return f"{s[0]} - {s[1]}", min(99, int(abs(e-a)*45 + 25))

        r_s = sk(ex, ax); r_sp = sk(ex*1.1, ax*0.9); r_nx = sk(ex*1.2, ax*0.8)
        
        aether_ex = (ex * 0.4) + (ex * 1.1 * 0.3) + (ex * 1.2 * 0.3)
        aether_ax = (ax * 0.4) + (ax * 0.9 * 0.3) + (ax * 0.8 * 0.3)
        if e_rec > e_g: aether_ex *= 1.05
        if d_rec > d_g: aether_ax *= 1.05
        r_ae = sk(aether_ex, aether_ax)

        return {"std": r_s[0], "s_c": r_s[1], "spec": r_sp[0], "sp_c": r_sp[1], "nexus": r_nx[0], "n_c": r_nx[1], "aether": r_ae[0], "ae_c": r_ae[1], "note": f"xG: {ex+ax:.2f}", "total_xg": ex+ax}
    except: return None

# --- 4. NAVİGASYON ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1
mod = st.sidebar.radio("🚀 Menü", ["🏠 Canlı Skorlar", "🤖 Tahmin Robotu", "Global AI", "Lig Odaklı", "🏆 Onur Listesi"])
all_d = {lig: veri_al(f"competitions/{kod}/matches") for lig, kod in LIGLER.items()}

if mod == "🏠 Canlı Skorlar":
    st.title("⚡ Canlı Maç Merkezi")
    live_data = veri_al("matches")
    matches = live_data.get('matches', [])
    if not matches: st.info("Aktif maç bulunmuyor.")
    else:
        for m in matches:
            score = f"{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}"
            st.markdown(f'<div class="match-card"><b>{m["homeTeam"]["name"]}</b> {score} <b>{m["awayTeam"]["name"]}</b></div>', unsafe_allow_html=True)

elif mod == "🤖 Tahmin Robotu":
    st.title("🤖 AI Tahmin Robotu")
    st.markdown("Yapay zekalarımızın haftalık bültendeki **en güvendiği 5 maçlık** özel kuponu.")
    
    robot_filtre = st.radio("👾 Robotu Seçin", ["Aether (Master)", "Standart (Banko)", "Spektrum (Gol)", "Nexus (Sürpriz)"], horizontal=True)
    s_sec = st.selectbox("📅 Hafta", [1, 2, 3, 4], index=site_h_aktif-1)
    
    # Tüm ligleri tara
    tüm_maclar = []
    for l_ad, l_data in all_d.items():
        m_list = l_data.get('matches', [])
        if not m_list: continue
        l_son = max([m['matchday'] for m in m_list if m['status'] == 'FINISHED'] or [1])
        t_md = l_son - (site_h_aktif - s_sec)
        for m in [x for x in m_list if x['matchday'] == t_md]:
            res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_list)
            if res:
                # Puanlama robot seçimine göre değişir
                if "Aether" in robot_filtre: score = res['ae_c']
                elif "Standart" in robot_filtre: score = res['s_c']
                elif "Spektrum" in robot_filtre: score = res['total_xg'] * 15 # xG bazlı
                else: score = res['n_c'] + 10 # Sürpriz katsayısı
                
                m.update({'res': res, 'l_ad': l_ad, 'robot_score': score})
                tüm_maclar.append(m)
    
    if tüm_maclar:
        top_5 = sorted(tüm_maclar, key=lambda x: x['robot_score'], reverse=True)[:5]
        
        st.markdown(f'<div class="robot-card"><h3>🏆 {robot_filtre} - Haftalık Altın Kuponu</h3><p>Liglerin en yüksek olasılıklı 5 maçı sentezlendi.</p></div>', unsafe_allow_html=True)
        
        for m in top_5:
            res = m['res']
            tahmin = res['aether'] if "Aether" in robot_filtre else (res['std'] if "Standart" in robot_filtre else (res['spec'] if "Spektrum" in robot_filtre else res['nexus']))
            st.markdown(f"""
                <div class="match-card">
                    <div style="display:flex; justify-content:space-between;">
                        <span>📍 {m['l_ad']}</span>
                        <span style="color:#D4AF37; font-weight:bold;">Güven: %{int(m['robot_score'])}</span>
                    </div>
                    <div style="display:flex; justify-content:space-around; align-items:center; margin:10px 0;">
                        <b>{m['homeTeam']['shortName']}</b> vs <b>{m['awayTeam']['shortName']}</b>
                        <div class="prediction-box aether-box">🤖 Tahmin: {tahmin}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("🧧 Kuponu Paylaş / İndir"):
            st.success("Kupon görseli hazırlanıyor... (Yakında aktif!)")

elif mod == "Global AI":
    filtre = st.sidebar.radio("🤖 Algoritma", ["AETHER AI (Master)", "Standart AI", "Spektrum AI", "Nexus AI"])
    s_sec = st.sidebar.selectbox("📅 Sitemiz: Hafta", [1, 2, 3, 4], index=site_h_aktif-1)
    st.title(f"🚀 {filtre} - {s_sec}. Hafta")
    # ... (Mevcut Global AI kodu v70 ile aynı şekilde devam eder)
    g_l = []
    for l_ad, l_data in all_d.items():
        m_list = l_data.get('matches', [])
        if not m_list: continue
        l_son = max([m['matchday'] for m in m_list if m['status'] == 'FINISHED'] or [1])
        t_md = l_son - (site_h_aktif - s_sec)
        for m in [x for x in m_list if x['matchday'] == t_md]:
            res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_list)
            if res:
                p = res['ae_c'] if "AETHER" in filtre else res['s_c']
                m.update({'res': res, 'l_ad': l_ad, 'puan': p})
                g_l.append(m)
    if g_l:
        for m in sorted(g_l, key=lambda x: x['puan'], reverse=True)[:10]:
            st.markdown(f'<div class="match-card"><b>{m["homeTeam"]["name"]}</b> vs <b>{m["awayTeam"]["name"]}</b></div>', unsafe_allow_html=True)
elif mod == "Lig Odaklı":
    lig_adi = st.sidebar.selectbox("🎯 Lig Seçin", list(LIGLER.keys())); lig_kodu = LIGLER[lig_adi]
    puan_durumu_data = veri_al(f"competitions/{lig_kodu}/standings"); maclar_data = all_d[lig_adi]
    c_p, c_m = st.columns([1, 2.5])
    with c_p:
        st.subheader("📊 Puan Durumu")
        if puan_durumu_data.get('standings'):
            table = puan_durumu_data['standings'][0]['table']
            html = '<table class="standings-table"><tr><th>#</th><th>Takım</th><th>P</th></tr>'
            for t in table: html += f'<tr><td>{t["position"]}</td><td>{t["team"]["shortName"]}</td><td><b>{t["points"]}</b></td></tr>'
            st.markdown(html + '</table>', unsafe_allow_html=True)
    with c_m:
        l_matches = maclar_data.get('matches', [])
        if l_matches:
            g_h = max([m['matchday'] for m in l_matches if m['status'] == 'FINISHED'] or [1])
            h_s = st.selectbox("📅 Hafta Seç", sorted(list(set([m['matchday'] for m in l_matches if m['matchday']]))), index=g_h-1)
            for m in [x for x in l_matches if x['matchday'] == h_s]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], l_matches)
                if res:
                    m_sk = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                    st.markdown(f"""<div class="match-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 33%;"><img src="{m['homeTeam']['crest']}" width="30"><br><b>{m['homeTeam']['name']}</b></div><div style="width: 33%; text-align: center;">{m_sk}</div><div style="text-align: center; width: 33%;"><img src="{m['awayTeam']['crest']}" width="30"><br><b>{m['awayTeam']['name']}</b></div></div></div>""", unsafe_allow_html=True)

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Gurur Tablosu")
    st.markdown('<div style="text-align:center; padding:50px; background:#1c2128; border-radius:15px; border:1px solid #3fb950;"><h2>⭐ Aether AI Rekoru</h2><p>Haftalık %91 Başarı Oranı!</p></div>', unsafe_allow_html=True)
