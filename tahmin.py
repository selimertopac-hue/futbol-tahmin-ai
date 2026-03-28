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

st.set_page_config(page_title="UltraSkor Pro: Performance Hub", page_icon="🎯", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .editor-card { background: linear-gradient(145deg, #1c2128, #0d1117); border: 1px solid #58A6FF; padding: 15px; border-radius: 12px; height: 100%; border-top: 4px solid #58A6FF; position: relative; }
    .success-badge { background: #238636; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; float: right; }
    .full-hit-seal { position: absolute; top: -10px; right: -10px; background: #D4AF37; color: black; padding: 5px 10px; border-radius: 5px; font-weight: bold; transform: rotate(15.0deg); box-shadow: 0 0 10px rgba(212,175,55,0.5); z-index: 10; font-size: 0.8rem; }
    .coupon-item { background: #0d1117; padding: 8px; margin-top: 8px; border-radius: 6px; border: 1px solid #30363d; font-size: 0.85rem; }
    .coupon-title { font-weight: bold; color: #58A6FF; margin-bottom: 10px; text-align: center; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .ai-insight { background: rgba(88, 166, 255, 0.05); border-left: 4px solid #58A6FF; padding: 12px; margin-top: 15px; border-radius: 4px; font-size: 0.85rem; color: #C9D1D9; font-style: italic; }
    .form-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .form-W { background-color: #238636; } .form-D { background-color: #9e9e9e; } .form-L { background-color: #f85149; }
    .standings-table { font-size: 0.8rem; width: 100%; border-collapse: collapse; background: #161b22; border-radius: 10px; overflow: hidden; }
    .standings-table th { background: #30363d; padding: 10px; text-align: left; color: #58A6FF; }
    .standings-table td { padding: 8px 10px; border-bottom: 1px solid #30363d; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ VE BAŞARI MOTORU ---
@st.cache_data(ttl=3600)
def veri_al(endpoint):
    try: return requests.get(f"https://api.football-data.org/v4/{endpoint}", headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

def winner(sk):
    try:
        p = sk.split(" - ")
        return "1" if int(p[0]) > int(p[1]) else ("2" if int(p[1]) > int(p[0]) else "X")
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
            rec = t_df.sort_values('MD', ascending=False).head(3)['HG' if is_h else 'AG'].mean()
            return g, y, (rec / g if g > 0 else 1.0)

        e_g, e_y, e_t = get_stats(ev, True)
        d_g, d_y, d_t = get_stats(dep, False)
        ex, ax = (e_g/l_e)*(d_y/l_e)*l_e, (d_g/l_d)*(e_y/l_d)*l_d
        
        note = f"🚀 {ev} son dönemde hücumda çok üretken." if e_t > 1.2 else "⚖️ Taktiksel disiplin ön planda."

        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            return f"{s[0]} - {s[1]}", min(99, int(abs(e-a)*45 + 25))

        r_s = sk(ex, ax); r_sp = sk(ex*1.1, ax*0.9); r_nx = sk(ex*1.2, ax*0.8)
        return {"std": r_s[0], "s_c": r_s[1], "spec": r_sp[0], "sp_c": r_sp[1], "nexus": r_nx[0], "n_c": r_nx[1], "note": note, "total_xg": (ex+ax)}
    except: return None

# --- 4. ZAMAN & HAFTA ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

# --- 5. ANA MENÜ ---
mod = st.sidebar.radio("🚀 Menü", ["Global AI", "Lig Odaklı", "🏆 Onur Listesi"])
all_d = {lig: veri_al(f"competitions/{kod}/matches") for lig, kod in LIGLER.items()}

if mod == "Global AI":
    filtre = st.sidebar.radio("🤖 Algoritma", ["Standart AI", "Spektrum AI", "Nexus AI"])
    s_sec = st.sidebar.selectbox("📅 Sitemiz: Hafta", [1, 2, 3, 4], index=site_h_aktif-1)
    
    HAFTA_ACILISLARI = {
        1: SİTE_DOGUM_TARİHİ + timedelta(hours=12),
        2: SİTE_DOGUM_TARİHİ + timedelta(days=7, hours=12),
        3: SİTE_DOGUM_TARİHİ + timedelta(days=14, hours=12),
        4: SİTE_DOGUM_TARİHİ + timedelta(days=21, hours=12) 
    }
    
    hedef_tarih = HAFTA_ACILISLARI.get(s_sec, datetime(2099,1,1))
    st.title(f"🚀 {filtre} - {s_sec}. Hafta")

    if simdi < hedef_tarih:
        st.info(f"Bu bülten yakında yayına girecek.")
    else:
        # Veri Hazırlama
        g_l = []
        for l_ad, l_data in all_d.items():
            matches = l_data.get('matches', [])
            if not matches: continue
            bitenler = [m['matchday'] for m in matches if m['status'] == 'FINISHED']
            l_son = max(bitenler) if bitenler else 1
            target_md = l_son - (site_h_aktif - s_sec)
            for m in [x for x in matches if x['matchday'] == target_md]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], matches)
                if res:
                    p = res['s_c'] if "Standart" in filtre else (res['sp_c'] if "Spektrum" in filtre else res['n_c'])
                    m.update({'res': res, 'l_ad': l_ad, 'puan': p, 'l_full': matches})
                    g_l.append(m)

        if g_l:
            # --- PERFORMANS KARNESİ HESABI ---
            st.markdown("### 📝 AI Editörün Kupon Önerileri")
            col1, col2, col3 = st.columns(3)
            
            def kupon_basari_hesapla(liste, tip):
                success = 0
                for m in liste:
                    if m['status'] == 'FINISHED':
                        gw = winner(f"{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}")
                        pred = winner(m['res']['std']) if tip=="banko" else (winner(m['res']['nexus']) if tip=="surpriz" else "OVER")
                        if tip == "ust":
                            if (m['score']['fullTime']['home'] + m['score']['fullTime']['away']) > 2.5: success += 1
                        elif pred == gw: success += 1
                return success

            # 1. Banko
            imzalar = sorted(g_l, key=lambda x: x['puan'], reverse=True)[:3]
            with col1:
                b_s = kupon_basari_hesapla(imzalar, "banko")
                seal = '<div class="full-hit-seal">🏆 FULL HIT</div>' if b_s == 3 else ""
                st.markdown(f'<div class="editor-card">{seal}<div class="coupon-title">⭐ HAFTANIN İMZASI <span class="success-badge">{b_s}/3</span></div>', unsafe_allow_html=True)
                for m in imzalar:
                    st.markdown(f'<div class="coupon-item"><b>{m["l_ad"]}</b> | {m["homeTeam"]["shortName"]} - {m["awayTeam"]["shortName"]}<br>Tahmin: {m["res"]["std"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # 2. Sürpriz
            surprizler = sorted([x for x in g_l if winner(x['res']['nexus']) != "1"], key=lambda x: x['puan'], reverse=True)[:3]
            if not surprizler: surprizler = g_l[-3:]
            with col2:
                s_s = kupon_basari_hesapla(surprizler, "surpriz")
                seal = '<div class="full-hit-seal">🔥 SÜRPRİZ!</div>' if s_s >= 2 else ""
                st.markdown(f'<div class="editor-card">{seal}<div class="coupon-title">🕵️ SÜRPRİZ RADARI <span class="success-badge">{s_s}/3</span></div>', unsafe_allow_html=True)
                for m in surprizler:
                    st.markdown(f'<div class="coupon-item"><b>{m["l_ad"]}</b> | {m["homeTeam"]["shortName"]} - {m["awayTeam"]["shortName"]}<br>Tahmin: {m["res"]["nexus"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # 3. Gol
            festivaller = sorted(g_l, key=lambda x: x['res']['total_xg'], reverse=True)[:3]
            with col3:
                f_s = kupon_basari_hesapla(festivaller, "ust")
                seal = '<div class="full-hit-seal">⚽ GOAL!</div>' if f_s == 3 else ""
                st.markdown(f'<div class="editor-card">{seal}<div class="coupon-title">⚽ GOL FESTİVALİ <span class="success-badge">{f_s}/3</span></div>', unsafe_allow_html=True)
                for m in festivaller:
                    st.markdown(f'<div class="coupon-item"><b>{m["l_ad"]}</b> | {m["homeTeam"]["shortName"]} - {m["awayTeam"]["shortName"]}<br>xG: {m["res"]["total_xg"]:.2f}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")

            # TOP 20 LISTESI (Önceki kodun aynısı...)
            top_20 = sorted(g_l, key=lambda x: x['puan'], reverse=True)[:20]
            for m in top_20:
                res = m['res']
                m_sk = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                st.markdown(f"""<div class="match-card"><div class="rank-badge">🔥 %{m['puan']}</div><div style="font-size:0.8rem; color:#8B949E;">{m['l_ad']} - Hafta {m['matchday']}</div><div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;"><div style="text-align: center; width: 33%;"><img src="{m['homeTeam']['crest']}" width="30"><br><b>{m['homeTeam']['name']}</b></div><div style="width: 33%; text-align: center;">{m_sk}</div><div style="text-align: center; width: 33%;"><img src="{m['awayTeam']['crest']}" width="30"><br><b>{m['awayTeam']['name']}</b></div></div><div class="ai-insight">💡 <b>AI Analiz:</b> {res['note']}</div></div>""", unsafe_allow_html=True)

elif mod == "Lig Odaklı":
    # Lig odaklı kodun (v47.0'daki gibi) devam ediyor...
    st.info("Puan Durumlu Lig Analizi aktif.")
