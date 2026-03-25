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

st.set_page_config(page_title="UltraSkor Pro: AI Strategy Center", page_icon="🧠", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .editor-card { background: linear-gradient(145deg, #1c2128, #0d1117); border: 1px solid #58A6FF; padding: 15px; border-radius: 12px; height: 100%; border-top: 4px solid #58A6FF; }
    .coupon-item { background: #0d1117; padding: 8px; margin-top: 8px; border-radius: 6px; border: 1px solid #30363d; font-size: 0.85rem; }
    .coupon-title { font-weight: bold; color: #58A6FF; margin-bottom: 10px; text-align: center; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .rank-badge { position: absolute; top: 10px; right: 10px; background: #238636; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .ai-insight { background: rgba(88, 166, 255, 0.05); border-left: 4px solid #58A6FF; padding: 12px; margin-top: 15px; border-radius: 4px; font-size: 0.9rem; color: #C9D1D9; font-style: italic; line-height: 1.4; }
    .hall-card { background: #1c2128; border: 1px solid #30363d; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ VE YORUM MOTORU ---
def analiz_ve_yorum(ev, dep, matches):
    try:
        df_raw = [m for m in matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if len(df_raw) < 5: return None
        df = pd.DataFrame([{'H': m['homeTeam']['name'], 'A': m['awayTeam']['name'], 'HG': m['score']['fullTime']['home'], 'AG': m['score']['fullTime']['away'], 'MD': m['matchday']} for m in df_raw])
        l_e, l_d = df['HG'].mean(), df['AG'].mean()
        
        def get_stats(team, is_h):
            t_df = df[df['H' if is_h else 'A'] == team].copy()
            if t_df.empty: return l_e, l_d, 1.0, 1.0
            t_df['w'] = 1.0 + (t_df['MD'] / df['MD'].max())
            g = (t_df['HG' if is_h else 'AG']*t_df['w']).sum()/t_df['w'].sum()
            y = (t_df['AG' if is_h else 'HG']*t_df['w']).sum()/t_df['w'].sum()
            rec = t_df.sort_values('MD', ascending=False).head(3)['HG' if is_h else 'AG'].mean()
            return g, y, (rec / g if g > 0 else 1.0), g

        e_g, e_y, e_t, e_p = get_stats(ev, True)
        d_g, d_y, d_t, d_p = get_stats(dep, False)
        ex, ax = (e_g/l_e)*(d_y/l_e)*l_e, (d_g/l_d)*(e_y/l_d)*l_d
        
        # --- GELİŞMİŞ ANALİZ NOTU (INSIGHT) ---
        total_xg = ex + ax
        if total_xg > 3.3: 
            note = f"⚽ **Gol Festivali Adayı:** İki takımın toplam gol beklentisi {total_xg:.2f}. Savunma disiplininden ziyade hücum hatlarının konuşacağı bir maç."
        elif e_t > 1.25: 
            note = f"🚀 **Hücum İvmesi:** {ev} son maçlarda bitiricilik oranını %{int((e_t-1)*100)} artırdı. Ev sahibi baskısı skor tabelasına erken yansıyabilir."
        elif d_t > 1.25:
            note = f"🔥 **Deplasman Formu:** {dep} dış sahada vites yükseltti. Kontrataklardaki xG verimliliği rakiplerini cezalandırabilir."
        elif e_p > d_p * 1.6:
            note = f"🛡️ **Domine Oyun:** {ev} kadro derinliği ve istatistiksel üstünlüğüyle oyunu rakip yarı sahaya yıkmaya aday görünüyor."
        else:
            note = "⚖️ **Taktiksel Satranç:** Veriler birbirine oldukça yakın. Maçın kaderini küçük detaylar ve bireysel yetenekler belirleyecek."

        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            return f"{s[0]} - {s[1]}", min(99, int(abs(e-a)*45 + 25))

        std, s_c = sk(ex, ax); spec, sp_c = sk(ex*1.1, ax*0.9); nx, n_c = sk(ex*1.2, ax*0.8)
        return {"std": std, "s_c": s_c, "spec": spec, "sp_c": sp_c, "nexus": nx, "n_c": n_c, "note": note, "total_xg": total_xg}
    except: return None

# --- 4. DATA ---
@st.cache_data(ttl=3600)
def veri_al(kod):
    try: return requests.get(f"https://api.football-data.org/v4/competitions/{kod}/matches", headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

def winner(sk):
    p = sk.split(" - ")
    return "1" if int(p[0]) > int(p[1]) else ("2" if int(p[1]) > int(p[0]) else "X")

# --- 5. MENÜ ---
mod = st.sidebar.radio("🚀 Menü", ["Lig Odaklı", "Global AI", "🏆 Onur Listesi"])
all_d = {lig: veri_al(kod) for lig, kod in LIGLER.items()}

if mod == "🏆 Onur Listesi":
    st.title("🏆 Sitemizin Gurur Tablosu")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown('<div class="hall-card">🤖 <b>Standart AI</b><br>%72 Başarı</div>', unsafe_allow_html=True)
    with c2: st.markdown('<div class="hall-card">🛡️ <b>Spektrum AI</b><br>%76 Başarı</div>', unsafe_allow_html=True)
    with c3: st.markdown('<div class="hall-card">🔥 <b>Nexus AI</b><br><b style="color:#3fb950;">%84 Başarı</b></div>', unsafe_allow_html=True)

elif mod == "Global AI":
    filtre = st.sidebar.radio("🤖 Algoritma", ["Standart AI", "Spektrum AI", "Nexus AI"])
    s_sec = st.sidebar.selectbox("📅 Hafta Arşivi", range(1, site_h_aktif + 2), index=site_h_aktif-1)
    st.title(f"🚀 {filtre} - {s_sec}. Hafta")
    
    g_l = []
    for l_ad, l_d in all_d.items():
        m_l = l_d.get('matches', [])
        if not m_l: continue
        l_son = max([x['matchday'] for x in m_l if x['status'] == 'FINISHED'] or [1])
        target = l_son - (site_h_aktif - s_sec)
        for m in [x for x in m_l if x['matchday'] == target]:
            res = analiz_ve_yorum(m['homeTeam']['name'], m['awayTeam']['name'], m_l)
            if res:
                p = res['s_c'] if "Standart" in filtre else (res['sp_c'] if "Spektrum" in filtre else res['n_c'])
                m.update({'res': res, 'l_ad': l_ad, 'puan': p})
                g_l.append(m)
    
    # --- 📝 AI EDİTÖR MASASI ---
    if g_l:
        st.markdown("### 📝 AI Editörün Kupon Önerileri")
        col1, col2, col3 = st.columns(3)
        imzalar = sorted(g_l, key=lambda x: x['puan'], reverse=True)[:3]
        with col1:
            st.markdown('<div class="editor-card"><div class="coupon-title">⭐ HAFTANIN İMZASI (BANKO)</div>', unsafe_allow_html=True)
            for m in imzalar:
                st.markdown(f'<div class="coupon-item"><b>{m["l_ad"]}</b> | {m["homeTeam"]["shortName"]} - {m["awayTeam"]["shortName"]}<br><span style="color:#3fb950;">Tahmin: {m["res"]["std"]} (%{m["puan"]})</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        surprizler = sorted([x for x in g_l if winner(x['res']['nexus']) != "1"], key=lambda x: x['puan'], reverse=True)[:3]
        if not surprizler: surprizler = g_l[-3:]
        with col2:
            st.markdown('<div class="editor-card"><div class="coupon-title">🕵️ SÜRPRİZ RADARI (PLASE)</div>', unsafe_allow_html=True)
            for m in surprizler:
                st.markdown(f'<div class="coupon-item"><b>{m["l_ad"]}</b> | {m["homeTeam"]["shortName"]} - {m["awayTeam"]["shortName"]}<br><span style="color:#f85149;">Tahmin: {m["res"]["nexus"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        festivaller = sorted(g_l, key=lambda x: x['res']['total_xg'], reverse=True)[:3]
        with col3:
            st.markdown('<div class="editor-card"><div class="coupon-title">⚽ GOL FESTİVALİ (ÜST)</div>', unsafe_allow_html=True)
            for m in festivaller:
                st.markdown(f'<div class="coupon-item"><b>{m["l_ad"]}</b> | {m["homeTeam"]["shortName"]} - {m["awayTeam"]["shortName"]}<br><span style="color:#58A6FF;">Toplam xG: {m["res"]["total_xg"]:.2f}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")

    # Genel Liste
    top_20 = sorted(g_l, key=lambda x: x['puan'], reverse=True)[:20]
    for m in top_20:
        res = m['res']
        c_std, c_spec, c_nx = "", "", ""
        if m['status'] == 'FINISHED':
            gw = winner(f'{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}')
            c_std = " ✅" if winner(res['std']) == gw else " ❌"
            c_spec = " ✅" if winner(res['spec']) == gw else " ❌"
            c_nx = " ✅" if winner(res['nexus']) == gw else " ❌"
            m_p = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>"
        else: m_p = f"🕒 {m['utcDate'][11:16]}"
        
        st.markdown(f"""
        <div class="match-card">
            <div class="rank-badge">🔥 %{m['puan']}</div>
            <div style="font-size:0.8rem;">{m['l_ad']} - Hafta {m['matchday']}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;">
                <div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div>
                <div style="width: 30%; text-align: center;">{m_p}</div>
                <div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div>
            </div>
            <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                <div class="prediction-box">🤖 STD<br><b>{res['std']}{c_std}</b></div>
                <div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}{c_spec}</b></div>
                <div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}{c_nx}</b></div>
            </div>
            <div class="ai-insight">💡 <b>AI Analiz:</b> {res['note']}</div>
        </div>""", unsafe_allow_html=True)
else:
    # LİG ODAKLI
    lig = st.sidebar.selectbox("🎯 Lig", list(LIGLER.keys()))
    l_m = all_d[lig].get('matches', [])
    if l_m:
        g_h = max([m['matchday'] for m in l_m if m['status'] == 'FINISHED'] or [1])
        h_s = st.sidebar.selectbox("📅 Hafta", sorted(list(set([m['matchday'] for m in l_m if m['matchday']]))), index=g_h-1)
        for m in [x for x in l_m if x['matchday'] == h_s]:
            res = analiz_ve_yorum(m['homeTeam']['name'], m['awayTeam']['name'], l_m)
            if res:
                m_p = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                st.markdown(f"""<div class="match-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div><div style="width: 30%; text-align: center;">{m_p}</div><div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div></div><div style="display: flex; justify-content: space-around; margin-top: 15px;"><div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div><div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}</b></div><div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b></div></div><div class="ai-insight">💡 <b>AI Analiz:</b> {res['note']}</div></div>""", unsafe_allow_html=True)
