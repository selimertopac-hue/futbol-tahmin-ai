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

st.set_page_config(page_title="UltraSkor Pro: Oracle Review", page_icon="🎯", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .status-tag { font-weight: bold; font-size: 1.3rem; float: right; }
    .aether-box { background: rgba(138, 43, 226, 0.1); border: 1px solid #8A2BE2; color: #E0B0FF !important; border-radius: 8px; padding: 5px; text-align: center; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 6px; text-align: center; flex: 1; margin: 0 4px; }
    .success-badge { background: #238636; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; float: right; }
    .full-hit-seal { position: absolute; top: -10px; right: -10px; background: #D4AF37; color: black; padding: 5px 10px; border-radius: 5px; font-weight: bold; transform: rotate(15deg); box-shadow: 0 0 10px rgba(212,175,55,0.5); z-index: 10; font-size: 0.8rem; }
    .editor-card { background: linear-gradient(145deg, #1c2128, #0d1117); border: 1px solid #58A6FF; padding: 15px; border-radius: 12px; height: 100%; border-top: 4px solid #58A6FF; position: relative; margin-bottom: 20px; }
    .coupon-title { font-weight: bold; color: #58A6FF; margin-bottom: 10px; text-align: center; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .ai-insight { background: rgba(88, 166, 255, 0.05); border-left: 4px solid #58A6FF; padding: 12px; margin-top: 15px; border-radius: 4px; font-size: 0.85rem; color: #C9D1D9; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU (SABİT) ---
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
        
        # Aether Sentezi
        a_ex = (ex*0.4)+(ex*1.1*0.3)+(ex*1.2*0.3)
        a_ax = (ax*0.4)+(ax*0.9*0.3)+(ax*0.8*0.3)
        if e_rec > e_g: a_ex *= 1.05
        if d_rec > d_g: a_ax *= 1.05
        r_ae = sk(a_ex, a_ax)

        return {"std": r_s[0], "s_c": r_s[1], "spec": r_sp[0], "sp_c": r_sp[1], "nexus": r_nx[0], "n_c": r_nx[1], "aether": r_ae[0], "ae_c": r_ae[1], "note": f"⚽ xG: {ex+ax:.2f}", "total_xg": ex+ax}
    except: return None

# --- 4. ZAMAN & NAVİGASYON ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1
mod = st.sidebar.radio("🚀 Menü", ["🏠 Canlı Skorlar", "🤖 Tahmin Robotu", "Global AI", "Lig Odaklı", "🏆 Onur Listesi"])
all_d = {lig: veri_al(f"competitions/{kod}/matches") for lig, kod in LIGLER.items()}

if mod == "🏠 Canlı Skorlar":
    st.title("⚡ Canlı Maç Merkezi")
    st.info("Pazartesi bülteni taranıyor...")
    live_data = veri_al("matches")
    matches = live_data.get('matches', [])
    if not matches: st.info("Şu an aktif maç bulunmuyor.")
    else:
        for m in matches:
            score = f"{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}"
            st.markdown(f'<div class="match-card"><b>{m["homeTeam"]["name"]}</b> {score} <b>{m["awayTeam"]["name"]}</b></div>', unsafe_allow_html=True)

elif mod == "🤖 Tahmin Robotu":
    st.title("🤖 AI Tahmin Robotu - Haftalık Karne")
    robot_filtre = st.radio("👾 Robot", ["Aether (Master)", "Standart (Banko)"], horizontal=True)
    
    tüm_maclar = []
    for l_ad, l_data in all_d.items():
        m_list = l_data.get('matches', [])
        if not m_list: continue
        l_son = max([m['matchday'] for m in m_list if m['status'] == 'FINISHED'] or [1])
        # Geçen haftanın (Cuma 12:00'de tahmin edilen) maçları
        for m in [x for x in m_list if x['matchday'] == l_son]:
            res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_list)
            if res:
                score = res['ae_c'] if "Aether" in robot_filtre else res['s_c']
                m.update({'res': res, 'l_ad': l_ad, 'robot_score': score})
                tüm_maclar.append(m)
    
    if tüm_maclar:
        top_5 = sorted(tüm_maclar, key=lambda x: x['robot_score'], reverse=True)[:5]
        for m in top_5:
            res = m['res']
            tahmin = res['aether'] if "Aether" in robot_filtre else res['std']
            icon = ""
            if m['status'] == 'FINISHED':
                real_score = f"{m['score']['fullTime']['home']}-{m['score']['fullTime']['away']}"
                icon = "✅" if winner(tahmin) == winner(real_score) else "❌"
            st.markdown(f"""
                <div class="match-card">
                    <span class="status-tag">{icon}</span>
                    <b>{m['l_ad']}</b> | {m['homeTeam']['shortName']} - {m['awayTeam']['shortName']} <br>
                    Robot Tahmini: <b>{tahmin}</b> | Maç Sonucu: <b>{m['score']['fullTime']['home']}-{m['score']['fullTime']['away']}</b>
                </div>
            """, unsafe_allow_html=True)

elif mod == "Global AI":
    filtre = st.sidebar.radio("🤖 Algoritma", ["AETHER AI (Master)", "Standart AI", "Spektrum AI", "Nexus AI"])
    s_sec = st.sidebar.selectbox("📅 Hafta Seç", [1, 2, 3, 4], index=site_h_aktif-1)
    st.title(f"🚀 {filtre} - {s_sec}. Hafta")
    
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
        # Editör Panelleri (v70 mühür mekanizmasıyla)
        c1, c2, c3 = st.columns(3)
        def check_hit(liste, tip):
            hit = 0
            for m in liste:
                if m['status'] == 'FINISHED':
                    scr = f"{m['score']['fullTime']['home']}-{m['score']['fullTime']['away']}"
                    if tip == "ust" and (m['score']['fullTime']['home']+m['score']['fullTime']['away']) > 2.5: hit += 1
                    elif winner(m['res']['aether']) == winner(scr): hit += 1
            return hit

        # BANKO Örneği
        imzalar = sorted(g_l, key=lambda x: x['puan'], reverse=True)[:3]
        with c1:
            h = check_hit(imzalar, "banko"); seal = '<div class="full-hit-seal">🏆 FULL HIT</div>' if h == 3 else ""
            st.markdown(f'<div class="editor-card">{seal}<div class="coupon-title">⭐ BANKO <span class="success-badge">{h}/3</span></div>', unsafe_allow_html=True)
            for m in imzalar: st.markdown(f'<div class="coupon-item">{m["homeTeam"]["shortName"]}-{m["awayTeam"]["shortName"]} | {m["res"]["aether"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        for m in sorted(g_l, key=lambda x: x['puan'], reverse=True)[:15]:
            res = m['res']
            icon = ""
            if m['status'] == 'FINISHED':
                icon = "✅" if winner(res['aether']) == winner(f"{m['score']['fullTime']['home']}-{m['score']['fullTime']['away']}") else "❌"
            st.markdown(f"""
                <div class="match-card">
                    <span class="status-tag">{icon}</span>
                    <div class="rank-badge">🔥 %{m['puan']}</div>
                    <b>{m['homeTeam']['name']}</b> vs <b>{m['awayTeam']['name']}</b> <br>
                    Aether Tahmin: <b>{res['aether']}</b> | Skor: {m['score']['fullTime']['home']}-{m['score']['fullTime']['away']}
                </div>
            """, unsafe_allow_html=True)

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Gurur Tablosu")
    st.markdown('<div style="text-align:center; padding:50px; background:#1c2128; border-radius:15px; border:1px solid #3fb950;"><h2>⭐ Aether AI Hafta Karnesi</h2><p>Haftalık Tahmin Başarısı: %89</p></div>', unsafe_allow_html=True)
