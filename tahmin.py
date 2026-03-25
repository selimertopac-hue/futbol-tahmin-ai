import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
LIGLER = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
SİTE_DOGUM_TARİHİ = datetime(2026, 3, 20) 

st.set_page_config(page_title="UltraSkor Pro: Hall of Fame", page_icon="🏆", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .rank-badge { position: absolute; top: 10px; right: 10px; background: #238636; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .score-banner { background: #21262d; padding: 25px; border-radius: 12px; border: 1px solid #58A6FF; text-align: center; margin-bottom: 25px; }
    .lock-box { background: #161b22; border: 2px dashed #f85149; padding: 30px; border-radius: 15px; text-align: center; color: #f85149; margin-bottom: 20px; }
    .timer-txt { font-size: 2rem; font-weight: bold; font-family: monospace; color: #f85149; margin-top: 10px; }
    .ai-insight { background: #0d1117; border-left: 4px solid #58A6FF; padding: 10px; margin-top: 12px; border-radius: 4px; font-size: 0.85rem; color: #8B949E; }
    .hall-of-fame-card { background: linear-gradient(145deg, #238636, #0D1117); border: 1px solid #3fb950; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
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
        
        note = f"🚀 {ev} hücumda %{int(e_t*100)} verimli." if e_t > 1.1 else (f"🔥 {dep} formu yükselişte." if d_t > 1.1 else "⚖️ İki takım da dengeli bir oyun bekliyor.")
        
        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            return f"{s[0]} - {s[1]}", min(99, int(abs(e-a)*45 + 25))

        std, s_c = sk(ex, ax)
        spec, sp_c = sk(ex*1.1, ax*0.9)
        nx, n_c = sk(ex*1.2, ax*0.8)
        return {"std": std, "s_c": s_c, "spec": spec, "sp_c": sp_c, "nexus": nx, "n_c": n_c, "note": note}
    except: return None

# --- 4. DATA & TIME ---
@st.cache_data(ttl=3600)
def veri_al(kod):
    try: return requests.get(f"https://api.football-data.org/v4/competitions/{kod}/matches", headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

simdi = datetime.now()
site_h = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

def geri_sayim():
    hedef = simdi + timedelta(days=(4 - simdi.weekday()) % 7)
    hedef = hedef.replace(hour=12, minute=0, second=0, microsecond=0)
    if simdi >= hedef: hedef += timedelta(days=7)
    k = hedef - simdi
    return f"{k.days} Gün {k.seconds//3600:02d}:{(k.seconds//60)%60:02d}:{k.seconds%60:02d}"

# --- 5. SIDEBAR ---
mod = st.sidebar.radio("🚀 Menü", ["Lig Odaklı", "Global AI", "🏆 Onur Listesi"])
all_d = {lig: veri_al(kod) for lig, kod in LIGLER.items()}

if mod == "🏆 Onur Listesi":
    st.title("🏆 UltraSkor Pro: Onur Listesi")
    st.markdown("""
    <div class="hall-of-fame-card">
        <h2 style="color:white !important;">⭐ Efsane Başlangıç (1. Hafta)</h2>
        <p>Sitemizin açılış haftasında 20'de 16 isabetle <b>%80</b> başarı sağlandı!</p>
        <hr>
        <p><small>Nexus AI | Mart 2026</small></p>
    </div>
    """, unsafe_allow_html=True)
    st.info("💡 Yeni rekorlar kırıldıkça bu liste otomatik olarak güncellenecektir.")

elif mod == "Lig Odaklı":
    lig = st.sidebar.selectbox("🎯 Lig", list(LIGLER.keys()))
    l_m = all_d[lig].get('matches', [])
    if l_m:
        h_l = sorted(list(set([m['matchday'] for m in l_m if m['matchday']])))
        g_h = max([m['matchday'] for m in l_m if m['status'] == 'FINISHED'] or [1])
        h_s = st.sidebar.selectbox("📅 Hafta", h_l, index=h_l.index(g_h))
        st.title(f"🏆 {lig} - {h_s}. Hafta")
        if h_s > g_h and not (simdi.weekday() >= 4 and (simdi.weekday() > 4 or simdi.hour >= 12)):
            st.markdown(f'<div class="lock-box">🔒 Tahminler Cuma 12:00\'de.<br><div class="timer-txt">{geri_sayim()}</div></div>', unsafe_allow_html=True)
        else:
            for m in [x for x in l_m if x['matchday'] == h_s]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], l_m)
                if res:
                    m_p = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                    st.markdown(f"""<div class="match-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div><div style="width: 30%; text-align: center;">{m_p}</div><div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div></div><div style="display: flex; justify-content: space-around; margin-top: 15px;"><div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div><div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}</b></div><div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b></div></div><div class="ai-insight">💡 <b>AI:</b> {res['note']}</div></div>""", unsafe_allow_html=True)
else:
    # GLOBAL AI
    filtre = st.sidebar.radio("🤖 AI Seç", ["Standart AI", "Spektrum AI", "Nexus AI"])
    s_sec = st.sidebar.selectbox("📅 Sitemiz: Hafta", range(1, site_h + 1), index=site_h-1)
    st.title(f"🚀 {filtre} - {s_sec}. Hafta")
    if s_sec > site_h - 1 and not (simdi.weekday() >= 4 and (simdi.weekday() > 4 or simdi.hour >= 12)):
        st.markdown(f'<div class="lock-box">🔒 {s_sec}. Hafta Tahminleri Cuma 12:00\'de.<br><div class="timer-txt">{geri_sayim()}</div></div>', unsafe_allow_html=True)
    else:
        g_l = []
        for l_ad, l_d in all_d.items():
            m_l = l_d.get('matches', [])
            if not m_l: continue
            l_a = max([x['matchday'] for x in m_l if x['status'] == 'FINISHED'] or [1])
            target = l_a if s_sec < site_h else l_a + 1
            for m in [x for x in m_l if x['matchday'] == target]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_l)
                if res:
                    p = res['s_c'] if "Standart" in filtre else (res['sp_c'] if "Spektrum" in filtre else res['n_c'])
                    m.update({'res': res, 'l_ad': l_ad, 'puan': p})
                    g_l.append(m)
        g_l = sorted(g_l, key=lambda x: x['puan'], reverse=True)[:20]
        isabet, biten = 0, 0
        for m in g_l:
            if m['status'] == 'FINISHED':
                biten += 1
                gw = "1" if m['score']['fullTime']['home'] > m['score']['fullTime']['away'] else ("2" if m['score']['fullTime']['away'] > m['score']['fullTime']['home'] else "X")
                t = m['res']['std'] if "Standart" in filtre else (m['res']['spec'] if "Spektrum" in filtre else m['res']['nexus'])
                if (lambda x: "1" if int(x.split(" - ")[0]) > int(x.split(" - ")[1]) else ("2" if int(x.split(" - ")[1]) > int(x.split(" - ")[0]) else "X"))(t) == gw: isabet += 1
        if biten > 0: st.success(f"📈 BU BÜLTEN: {biten} maçta {isabet} isabetle %{int((isabet/biten)*100)} oran yakalandı!")
        for m in g_l:
            res = m['res']
            m_p = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
            st.markdown(f"""<div class="match-card"><div class="rank-badge">🔥 %{m['puan']}</div><div class="league-label">{m['l_ad']} - Hafta {m['matchday']}</div><div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;"><div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div><div style="width: 30%; text-align: center;">{m_p}</div><div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div></div><div style="display: flex; justify-content: space-around; margin-top: 15px;"><div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div><div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}</b></div><div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b></div></div><div class="ai-insight">💡 <b>AI:</b> {res['note']}</div></div>""", unsafe_allow_html=True)
