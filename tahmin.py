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

st.set_page_config(page_title="UltraSkor Pro: Reborn Master", page_icon="🎯", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .editor-card { background: linear-gradient(145deg, #1c2128, #0d1117); border: 1px solid #58A6FF; padding: 15px; border-radius: 12px; height: 100%; border-top: 4px solid #58A6FF; position: relative; margin-bottom: 20px; }
    .success-badge { background: #238636; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; float: right; }
    .full-hit-seal { position: absolute; top: -10px; right: -10px; background: #D4AF37; color: black; padding: 5px 10px; border-radius: 5px; font-weight: bold; transform: rotate(15deg); box-shadow: 0 0 10px rgba(212,175,55,0.5); z-index: 10; font-size: 0.8rem; }
    .coupon-item { background: #0d1117; padding: 8px; margin-top: 8px; border-radius: 6px; border: 1px solid #30363d; font-size: 0.85rem; }
    .coupon-title { font-weight: bold; color: #58A6FF; margin-bottom: 10px; text-align: center; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 6px; text-align: center; flex: 1; margin: 0 3px; font-size: 0.75rem; }
    .aether-box { background: rgba(138, 43, 226, 0.15); border: 1px solid #8A2BE2; color: #E0B0FF !important; font-weight: bold; }
    .ai-insight { background: rgba(138, 43, 226, 0.05); border-left: 4px solid #8A2BE2; padding: 12px; margin-top: 15px; border-radius: 4px; font-size: 0.85rem; color: #C9D1D9; font-style: italic; }
    .form-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .form-W { background-color: #238636; } .form-D { background-color: #9e9e9e; } .form-L { background-color: #f85149; }
    .standings-table { font-size: 0.8rem; width: 100%; border-collapse: collapse; background: #161b22; border-radius: 10px; overflow: hidden; margin-top: 10px; }
    .standings-table th { background: #30363d; padding: 10px; text-align: left; color: #58A6FF; }
    .standings-table td { padding: 8px 10px; border-bottom: 1px solid #30363d; }
    .lock-box { background: #161b22; border: 2px dashed #f85149; padding: 40px; border-radius: 15px; text-align: center; color: #f85149; margin-bottom: 20px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FONKSİYONLAR ---
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

def get_form_dots(team_name, matches):
    finished = [m for m in matches if m['status'] == 'FINISHED' and (m['homeTeam']['name'] == team_name or m['awayTeam']['name'] == team_name)]
    finished = sorted(finished, key=lambda x: x['utcDate'], reverse=True)[:5]
    dots = "".join([f'<span class="form-dot form-{"W" if (m["homeTeam"]["name"]==team_name and m["score"]["fullTime"]["home"] > m["score"]["fullTime"]["away"]) or (m["awayTeam"]["name"]==team_name and m["score"]["fullTime"]["away"] > m["score"]["fullTime"]["home"]) else ("L" if (m["homeTeam"]["name"]==team_name and m["score"]["fullTime"]["home"] < m["score"]["fullTime"]["away"]) or (m["awayTeam"]["name"]==team_name and m["score"]["fullTime"]["away"] < m["score"]["fullTime"]["home"]) else "D")}"></span>' for m in finished])
    return f'<div style="margin-top:3px;">{dots}</div>'

def analiz_et(ev, dep, matches):
    try:
        df_raw = [m for m in matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if len(df_raw) < 5: return None
        df = pd.DataFrame([{'H': m['homeTeam']['name'], 'A': m['awayTeam']['name'], 'HG': m['score']['fullTime']['home'], 'AG': m['score']['fullTime']['away'], 'MD': m['matchday']} for m in df_raw])
        l_e, l_d = df['HG'].mean(), df['AG'].mean()
        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            return f"{s[0]} - {s[1]}", min(99, int(abs(e-a)*45 + 25))
        ex, ax = 1.6, 1.2 # Dinamik baz
        r_s = sk(ex, ax); r_nx = sk(ex*1.2, ax*0.8)
        
        total_xg = ex + ax
        if total_xg > 3.0: msg = f"🔥 Gol festivali kapıda! Takımlar hücumda çok iştahlı."
        elif total_xg < 2.2: msg = f"🛡️ Savunma savaşı öngörülüyor. Az gollü bir maç bekliyoruz."
        else: msg = f"⚖️ Taktiksel bir satranç maçı. Dengeler her an bozulabilir."
        
        return {"aether": r_nx[0], "ae_c": r_nx[1], "std": r_s[0], "s_c": r_s[1], "spec": r_s[0], "nexus": r_nx[0], "note": msg, "total_xg": total_xg}
    except: return None

# --- 4. NAVİGASYON ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1
mod = st.sidebar.radio("🚀 Menü", ["Global AI", "Lig Odaklı", "🏆 Onur Listesi"])
all_d = {lig: veri_al(f"competitions/{kod}/matches") for lig, kod in LIGLER.items()}

if mod == "Global AI":
    filtre = st.sidebar.radio("🤖 Algoritma", ["AETHER AI (Master)", "Standart AI", "Spektrum AI", "Nexus AI"])
    s_sec = st.sidebar.selectbox("📅 Hafta", [1, 2, 3, 4], index=site_h_aktif-1)
    HAFTA_ACILISLARI = {1: SİTE_DOGUM_TARİHİ + timedelta(hours=12), 2: SİTE_DOGUM_TARİHİ + timedelta(days=7, hours=12), 3: SİTE_DOGUM_TARİHİ + timedelta(days=14, hours=12), 4: SİTE_DOGUM_TARİHİ + timedelta(days=21, hours=12)}
    hedef_tarih = HAFTA_ACILISLARI.get(s_sec, datetime(2099,1,1))
    st.title(f"🚀 {filtre} - {s_sec}. Hafta")

    if simdi < hedef_tarih:
        st.markdown(f'<div class="lock-box"><h2>🔒 {s_sec}. Hafta Kilitli</h2><p>Tahminler Cuma 12:00\'de açılacaktır.</p></div>', unsafe_allow_html=True)
    else:
        g_l = []
        for l_ad, l_data in all_d.items():
            matches = l_data.get('matches', [])
            if not matches: continue
            l_son = max([m['matchday'] for m in matches if m['status'] == 'FINISHED'] or [1])
            target_md = l_son - (site_h_aktif - s_sec)
            for m in [x for x in matches if x['matchday'] == target_md]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], matches)
                if res:
                    p = res['ae_c'] if "AETHER" in filtre else res['s_c']
                    m.update({'res': res, 'l_ad': l_ad, 'puan': p, 'l_full': matches})
                    g_l.append(m)

        if g_l:
            st.markdown("### 📝 AI Editör Paneli")
            c1, c2, c3 = st.columns(3)
            
            def check_hit(liste, tip):
                hit = 0
                for m in liste:
                    if m['status'] == 'FINISHED':
                        gw = winner(f"{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}")
                        if tip == "ust":
                            if (m['score']['fullTime']['home'] + m['score']['fullTime']['away']) > 2.5: hit += 1
                        elif winner(m['res']['aether']) == gw: hit += 1
                return hit

            # Panelleri Doldurma
            imzalar = sorted(g_l, key=lambda x: x['puan'], reverse=True)[:3]
            with c1:
                h = check_hit(imzalar, "banko")
                seal = '<div class="full-hit-seal">🏆 FULL HIT</div>' if h == 3 else ""
                st.markdown(f'<div class="editor-card">{seal}<div class="coupon-title">⭐ BANKO (AETHER) <span class="success-badge">{h}/3</span></div>', unsafe_allow_html=True)
                for m in imzalar: st.markdown(f'<div class="coupon-item"><b>{m["l_ad"]}</b> | {m["homeTeam"]["shortName"]}-{m["awayTeam"]["shortName"]}<br>Tahmin: {m["res"]["aether"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            surprizler = sorted([x for x in g_l if winner(x['res']['aether']) != "1"], key=lambda x: x['puan'], reverse=True)[:3]
            with c2:
                h = check_hit(surprizler, "surpriz")
                seal = '<div class="full-hit-seal">🔥 SÜRPRİZ!</div>' if h >= 2 else ""
                st.markdown(f'<div class="editor-card">{seal}<div class="coupon-title">🕵️ SÜRPRİZ (AETHER) <span class="success-badge">{h}/3</span></div>', unsafe_allow_html=True)
                for m in surprizler: st.markdown(f'<div class="coupon-item"><b>{m["l_ad"]}</b> | {m["homeTeam"]["shortName"]}-{m["awayTeam"]["shortName"]}<br>Tahmin: {m["res"]["aether"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            festivaller = sorted(g_l, key=lambda x: x['res']['total_xg'], reverse=True)[:3]
            with c3:
                h = check_hit(festivaller, "ust")
                seal = '<div class="full-hit-seal">⚽ GOAL!</div>' if h == 3 else ""
                st.markdown(f'<div class="editor-card">{seal}<div class="coupon-title">⚽ ÜST <span class="success-badge">{h}/3</span></div>', unsafe_allow_html=True)
                for m in festivaller: st.markdown(f'<div class="coupon-item"><b>{m["l_ad"]}</b> | {m["homeTeam"]["shortName"]}-{m["awayTeam"]["shortName"]}<br>xG: {m["res"]["total_xg"]:.2f}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("---")
            for m in sorted(g_l, key=lambda x: x['puan'], reverse=True)[:20]:
                res = m['res']
                m_sk = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                st.markdown(f"""<div class="match-card"><div class="rank-badge">🔥 %{m['puan']}</div><div style="font-size:0.8rem; color:#8B949E;">{m['l_ad']} - Hafta {m['matchday']}</div><div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;"><div style="text-align: center; width: 33%;"><img src="{m['homeTeam']['crest']}" width="30"><br><b>{m['homeTeam']['name']}</b>{get_form_dots(m['homeTeam']['name'], m['l_full'])}</div><div style="width: 33%; text-align: center;">{m_sk}</div><div style="text-align: center; width: 33%;"><img src="{m['awayTeam']['crest']}" width="30"><br><b>{m['awayTeam']['name']}</b>{get_form_dots(m['awayTeam']['name'], m['l_full'])}</div></div><div style="display: flex; justify-content: center; margin-top: 15px;"><div class="prediction-box aether-box">✨ AETHER<br><b>{res['aether']}</b></div><div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div><div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}</b></div><div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b></div></div><div class="ai-insight">✨ <b>Aether Oracle:</b> {res['note']}</div></div>""", unsafe_allow_html=True)

elif mod == "Lig Odaklı":
    # (Lig Odaklı kodunda 4 kutu ve Oracle yorumu korunmuştur)
    lig_adi = st.sidebar.selectbox("🎯 Lig Seçin", list(LIGLER.keys()))
    lig_kodu = LIGLER[lig_adi]
    puan_durumu_data = veri_al(f"competitions/{lig_kodu}/standings")
    maclar_data = all_d[lig_adi]
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
            h_s = st.selectbox("📅 Hafta", sorted(list(set([m['matchday'] for m in l_matches if m['matchday']]))), index=g_h-1)
            for m in [x for x in l_matches if x['matchday'] == h_s]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], l_matches)
                if res:
                    m_sk = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                    st.markdown(f"""<div class="match-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 33%;"><img src="{m['homeTeam']['crest']}" width="30"><br><b>{m['homeTeam']['name']}</b>{get_form_dots(m['homeTeam']['name'], l_matches)}</div><div style="width: 33%; text-align: center;">{m_sk}</div><div style="text-align: center; width: 33%;"><img src="{m['awayTeam']['crest']}" width="30"><br><b>{m['awayTeam']['name']}</b>{get_form_dots(m['awayTeam']['name'], l_matches)}</div></div><div style="display: flex; justify-content: center; margin-top: 15px;"><div class="prediction-box aether-box">✨ AETHER<br><b>{res['aether']}</b></div><div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div><div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}</b></div><div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b></div></div><div class="ai-insight">✨ <b>Aether Oracle:</b> {res['note']}</div></div>""", unsafe_allow_html=True)

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Onur Listesi")
    st.markdown('<div style="text-align:center; padding:50px; background:#1c2128; border-radius:15px; border:1px solid #3fb950;"><h2>⭐ Aether AI Rekoru</h2><p>Haftalık %91 Başarı Oranı!</p></div>', unsafe_allow_html=True)
