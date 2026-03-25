import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
LIGLER = {
    "İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", 
    "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"
}

SİTE_DOGUM_TARİHİ = datetime(2026, 3, 20) 

st.set_page_config(page_title="UltraSkor Pro: AI Insight", page_icon="🧠", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .rank-badge { position: absolute; top: 10px; right: 10px; background: #238636; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .active-algo { border: 1.5px solid #58A6FF !important; background: rgba(88, 166, 255, 0.1); }
    .score-banner { background: #21262d; padding: 25px; border-radius: 12px; border: 1px solid #58A6FF; text-align: center; margin-bottom: 25px; }
    .lock-box { background: #161b22; border: 2px dashed #f85149; padding: 30px; border-radius: 15px; text-align: center; color: #f85149; margin-bottom: 20px; }
    .timer-txt { font-size: 2rem; font-weight: bold; font-family: monospace; color: #f85149; margin-top: 10px; }
    .success-summary { background: rgba(35, 134, 54, 0.1); border: 1px solid #238636; padding: 15px; border-radius: 10px; color: #3fb950; font-weight: bold; margin-bottom: 15px; text-align: center; }
    .ai-insight { background: #0d1117; border-left: 4px solid #58A6FF; padding: 10px; margin-top: 12px; border-radius: 4px; font-size: 0.85rem; font-style: italic; color: #8B949E; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ VE YORUM MOTORU ---
def analiz_ve_yorum(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if len(df_raw) < 5: return None
        df = pd.DataFrame([{'H': m['homeTeam']['name'], 'A': m['awayTeam']['name'], 
                            'HG': m['score']['fullTime']['home'], 'AG': m['score']['fullTime']['away'], 
                            'MD': m['matchday']} for m in df_raw])
        l_e_o, l_d_o = df['HG'].mean(), df['AG'].mean()
        max_md = df['MD'].max()

        def get_stats(team, is_home):
            t_df = df[df['H' if is_home else 'A'] == team].copy()
            if t_df.empty: return l_e_o, l_d_o, 1.0, 1.0
            t_df['w'] = 1.0 + (t_df['MD'] / max_md)
            g = (t_df['HG' if is_home else 'AG']*t_df['w']).sum()/t_df['w'].sum()
            y = (t_df['AG' if is_home else 'HG']*t_df['w']).sum()/t_df['w'].sum()
            # Son 3 maç form ivmesi
            recent_g = t_df.sort_values('MD', ascending=False).head(3)['HG' if is_home else 'AG'].mean()
            return g, y, (recent_g / g if g > 0 else 1.0), (g / l_e_o if is_home else g / l_d_o)

        e_g, e_y, e_trend, e_pwr = get_stats(ev_ad, True)
        d_g, d_y, d_trend, d_pwr = get_stats(dep_ad, False)
        
        e_xg = (e_g / l_e_o) * (d_y / l_e_o) * l_e_o
        d_xg = (d_g / l_d_o) * (e_y / l_d_o) * l_d_o

        # YORUM ÜRETİCİ
        yorum = ""
        if e_trend > 1.15: yorum = f"🚀 {ev_ad} son maçlarda hücum ivmesini %{int((e_trend-1)*100)} artırdı, baskılı başlayacak."
        elif d_trend > 1.15: yorum = f"🔥 {dep_ad} deplasmanda yükselen bir forma sahip, sürpriz arayabilir."
        elif e_pwr > d_pwr * 1.5: yorum = f"🛡️ {ev_ad} kadro kalitesi ve xG üstünlüğüyle maçı domine etmeye aday."
        else: yorum = "⚖️ İstatistiksel olarak dengeli bir maç; savunma disiplini sonucu belirleyecektir."

        def get_skor(ex, ax):
            m = np.outer([poisson.pmf(i, max(0.1, ex)) for i in range(6)], [poisson.pmf(i, max(0.1, ax)) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}", min(99, int(abs(ex-ax)*45 + 25))

        r_s = get_skor(e_xg, d_xg)
        r_sp = get_skor(e_xg * 1.1, d_xg * 0.9)
        r_nx = get_skor(e_xg * 1.2, d_xg * 0.8)
        
        return {"std": r_s[0], "s_c": r_s[1], "spec": r_sp[0], "sp_c": r_sp[1], "nexus": r_nx[0], "n_c": r_nx[1], "note": yorum}
    except: return None

# --- 4. YARDIMCI ARAÇLAR ---
@st.cache_data(ttl=3600)
def lig_verisi_al(lig_kodu):
    try:
        r = requests.get(f"https://api.football-data.org/v4/competitions/{lig_kodu}/matches", headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15)
        return r.json()
    except: return {}

def winner(sk):
    p = sk.split(" - ")
    return "1" if int(p[0]) > int(p[1]) else ("2" if int(p[1]) > int(p[0]) else "X")

# --- 5. ZAMAN VE HAFTA ---
simdi = datetime.now()
site_aktif_haftasi = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

def geri_sayim():
    hedef = simdi + timedelta(days=(4 - simdi.weekday()) % 7)
    hedef = hedef.replace(hour=12, minute=0, second=0, microsecond=0)
    if simdi >= hedef: hedef += timedelta(days=7)
    k = hedef - simdi
    s, m = divmod(k.seconds, 3600)
    dk, sn = divmod(m, 60)
    return f"{k.days} Gün {s:02d}:{dk:02d}:{sn:02d}"

# --- 6. SIDEBAR ---
st.sidebar.title("🌍 UltraSkor Pro")
filtre = st.sidebar.radio("🚀 Mod Seçimi:", ["Lig Odaklı", "Standart AI (Global)", "Spektrum AI (Global)", "Nexus AI (Global)"])

all_data = {lig: lig_verisi_al(kod) for lig, kod in LIGLER.items()}

if filtre == "Lig Odaklı":
    lig_adi = st.sidebar.selectbox("🎯 Lig Seçin", list(LIGLER.keys()))
    l_m = all_data[lig_adi].get('matches', [])
    if l_m:
        h_liste = sorted(list(set([m['matchday'] for m in l_m if m['matchday']])))
        guncel_h = max([m['matchday'] for m in l_m if m['status'] == 'FINISHED'] or [1])
        h_secim = st.sidebar.selectbox("📅 Lig Haftası", h_liste, index=h_liste.index(guncel_h))
        st.title(f"🏆 {lig_adi} - {h_secim}. Hafta")
        
        if h_secim > guncel_h and not (simdi.weekday() >= 4 and (simdi.weekday() > 4 or simdi.hour >= 12)):
            st.markdown(f'<div class="lock-box">🔒 Gelecek haftanın tahminleri Cuma 12:00\'de yayınlanacaktır.<div class="timer-txt">{geri_sayim()}</div></div>', unsafe_allow_html=True)
        else:
            for m in [x for x in l_m if x['matchday'] == h_secim]:
                res = analiz_ve_yorum(m['homeTeam']['name'], m['awayTeam']['name'], l_m)
                if res:
                    m_sk = f'<h3>{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}</h3>' if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                    st.markdown(f"""<div class="match-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div><div style="width: 30%; text-align: center;">{m_sk}</div><div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div></div><div style="display: flex; justify-content: space-around; margin-top: 15px;"><div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div><div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}</b></div><div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b></div></div><div class="ai-insight">💡 <b>AI Analiz:</b> {res['note']}</div></div>""", unsafe_allow_html=True)
else:
    # GLOBAL MOD
    st.sidebar.markdown("---")
    s_maks = site_aktif_haftasi + 1 
    s_sec = st.sidebar.selectbox("📅 Sitemiz: Hafta No", range(1, s_maks + 1), index=site_aktif_haftasi-1)
    st.title(f"🚀 {filtre.replace(' (Global)','')} - {s_sec}. Hafta Analizi")
    
    if s_sec > site_aktif_haftasi and not (simdi.weekday() >= 4 and (simdi.weekday() > 4 or simdi.hour >= 12)):
        st.markdown(f'<div class="lock-box">🔒 {s_sec}. Hafta Tahminleri Cuma 12:00\'de yayınlanacaktır.<div class="timer-txt">{geri_sayim()}</div></div>', unsafe_allow_html=True)
    else:
        global_list = []
        with st.spinner("Veriler işleniyor..."):
            for l_ad, l_d in all_data.items():
                m_list = l_d.get('matches', [])
                if not m_list: continue
                l_aktif = max([x['matchday'] for x in m_list if x['status'] == 'FINISHED'] or [1])
                target = l_aktif if s_sec <= site_aktif_haftasi else l_aktif + 1
                for m in [x for x in m_list if x['matchday'] == target]:
                    res = analiz_ve_yorum(m['homeTeam']['name'], m['awayTeam']['name'], m_list)
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

        if biten > 0:
            st.markdown(f'<div class="success-summary">📈 BAŞARI NOTU: {biten} maçta {isabet} isabetle %{int((isabet/biten)*100)} oran yakaladık!</div>', unsafe_allow_html=True)

        st.markdown(f"""<div class="score-banner"><h2 style="margin:0;">Sitemiz {s_sec}. Hafta Karnesi</h2><div style="display:flex; justify-content:center; gap:30px; margin-top:10px;"><div><small>Biten</small><br><b style="font-size:1.5rem;">{biten}</b></div><div><small>Doğru</small><br><b style="font-size:1.5rem; color:#238636;">{isabet}</b></div><div><small>Başarı</small><br><b style="font-size:1.5rem; color:#f85149;">%{int((isabet/biten)*100) if biten>0 else 0}</b></div></div></div>""", unsafe_allow_html=True)

        for m in global_list:
            res = m['res']
            c_s, c_sp, c_nx = "", "", ""
            if m['status'] == 'FINISHED':
                gw = "1" if m['score']['fullTime']['home'] > m['score']['fullTime']['away'] else ("2" if m['score']['fullTime']['away'] > m['score']['fullTime']['home'] else "X")
                if winner(res['std']) == gw: c_s = " ✅"
                if winner(res['spec']) == gw: c_sp = " ✅"
                if winner(res['nexus']) == gw: c_nx = " ✅"
                m_p = f'<h3>{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}</h3>'
            else: m_p = f"🕒 {m['utcDate'][11:16]}"

            st.markdown(f"""<div class="match-card"><div class="rank-badge">🔥 Güven: %{m['puan']}</div><div class="league-label">{m['l_ad']} - Lig Haftası {m['matchday']}</div><div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;"><div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div><div style="width: 30%; text-align: center;">{m_p}</div><div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div></div><div style="display: flex; justify-content: space-around; margin-top: 15px;"><div class="prediction-box">🤖 STD<br><b>{res['std']}{c_s}</b></div><div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}{c_sp}</b></div><div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}{c_nx}</b></div></div><div class="ai-insight">💡 <b>AI Analiz:</b> {res['note']}</div></div>""", unsafe_allow_html=True)
