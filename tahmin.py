import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR & API ANAHTARLARI ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
ODDS_API_KEY = "b4040bb05379cd7d9b94f18f2b74b133"
TELEGRAM_TOKEN = "BURAYA_TOKEN_GIR" 
TELEGRAM_CHAT_ID = "BURAYA_ID_GIR" 

st.set_page_config(page_title="UltraSkor Pro: Spectrum AI", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL (UI) ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 8px; margin-top: 10px; }
    .filter-label { font-size: 0.7rem; font-weight: bold; color: #8B949E; margin-bottom: 5px; text-align: center; text-transform: uppercase; }
    .win { color: #238636; } .draw { color: #D29922; } .loss { color: #DA3633; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SPEKTRUM ANALİZ MOTORU (NİHAİ MANTIK) ---
def spektrum_analiz_et(ev_ad, dep_ad, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None
    
    # Temel Veri Hazırlığı
    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score']['fullTime']['home'], df['score']['fullTime']['away']
    
    # Lig Ortalamaları (Benchmark)
    lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
    
    # SADECE EV VE SADECE DEPLASMAN FİLTRELEMESİ (Senin istediğin ayrım)
    ev_sahibi_maclar = df[df['H'] == ev_ad] # Sadece evdeki performansı
    deplasman_maclar = df[df['A'] == dep_ad] # Sadece dış saha performansı
    
    if ev_sahibi_maclar.empty or deplasman_maclar.empty: return None

    # --- ALGORİTMA 1: STANDART xG ---
    ev_std_xg = (ev_sahibi_maclar['HG'].mean() / lig_ev_ort) * (deplasman_maclar['HG'].mean() / lig_ev_ort) * lig_ev_ort
    dep_std_xg = (deplasman_maclar['AG'].mean() / lig_dep_ort) * (ev_sahibi_maclar['AG'].mean() / lig_dep_ort) * lig_dep_ort

    # --- ALGORİTMA 2: OFANSİF VERİMLİLİK (GENEL) ---
    ev_bitiricilik = ev_sahibi_maclar['HG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)
    dep_bitiricilik = deplasman_maclar['AG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)

    # --- ALGORİTMA 3: SPEKTRUM VE GERÇEKLİK (EV VS DEPLASMAN SİMETRİSİ) ---
    # Ev sahibi evinde az pozisyon verip (düşük xG) çok mu gol yiyor? (Savunma Şanssızlığı/Zafiyeti)
    ev_sav_gercek = ev_sahibi_maclar['AG'].mean() / (lig_dep_ort * (ev_sahibi_maclar['AG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)))
    
    # Deplasman takımı dış sahada az pozisyon bulup (düşük xG) çok mu gol atıyor? (Deplasman Fırsatçılığı)
    dep_huc_gercek = deplasman_maclar['AG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)
    
    # Final Simetrik xG Hesaplaması
    final_ev_xg = ev_std_xg * ev_bitiricilik * (1 / dep_huc_gercek if dep_huc_gercek > 0 else 1)
    final_dep_xg = dep_std_xg * dep_huc_gercek * ev_sav_gercek

    def get_probs(ex, ax):
        m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
        sk = np.unravel_index(np.argmax(m), m.shape)
        return {"Ev": np.sum(np.tril(m, -1))*100, "Skor": f"{sk[0]} - {sk[1]}"}

    return {
        "alg_1": get_probs(ev_std_xg, dep_std_xg),
        "alg_2": get_probs(ev_std_xg * ev_bitiricilik, dep_std_xg * dep_bitiricilik),
        "alg_3": get_probs(final_ev_xg, final_dep_xg),
        "ev_not": "🛡️ Evde Katı Savunma" if ev_sav_gercek < 0.9 else "⚠️ Evde Kırılgan",
        "dep_not": "⚔️ Deplasman Katili" if dep_huc_gercek > 1.2 else "🐢 Kısır Hücum"
    }

# --- 4. YARDIMCI GÖRSEL FONKSİYONLAR ---
def form_html(takim, matches):
    s = sorted([m for m in matches if (m['homeTeam']['name']==takim or m['awayTeam']['name']==takim) and m['status']=='FINISHED'], key=lambda x:x['utcDate'], reverse=True)[:5]
    res = []
    for m in s:
        h, a = m['score']['fullTime']['home'], m['score']['fullTime']['away']
        if m['homeTeam']['name'] == takim: res.append("win" if h>a else ("draw" if h==a else "loss"))
        else: res.append("win" if a>h else ("draw" if h==a else "loss"))
    return "".join([f"<span class='form-circle {r}'></span>" for r in res])

# --- 5. ANA PANEL ---
st.title("🛡️ UltraSkor Pro AI: Spectrum Dashboard")

ligler = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
secim = st.sidebar.selectbox("🎯 Lig Seç", list(ligler.keys()))

@st.cache_data(ttl=3600)
def veri_getir(url, h={}): return requests.get(url, headers=h).json()

m_data = veri_getir(f"https://api.football-data.org/v4/competitions/{ligler[secim]}/matches", {"X-Auth-Token": FOOTBALL_DATA_KEY}).get('matches', [])
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

if gelecek:
    for m in gelecek[:15]:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = spektrum_analiz_et(ev, dep, m_data)
        
        if res:
            with st.expander(f"🏟️ {ev} vs {dep}"):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1: 
                    st.image(m['homeTeam']['crest'], width=45)
                    st.markdown(f"Ev Form: {form_html(ev, m_data)}", unsafe_allow_html=True)
                with c2: 
                    st.markdown("<p style='text-align:center;'><b>SPEKTRUM ANALİZİ</b></p>", unsafe_allow_html=True)
                    st.progress(res['alg_3']['Ev']/100)
                with c3: 
                    st.image(m['awayTeam']['crest'], width=45)
                    st.markdown(f"Dep Form: {form_html(dep, m_data)}", unsafe_allow_html=True)
                
                st.divider()
                f1, f2, f3 = st.columns(3)
                with f1: st.info(f"📍 Standart\n\n**{res['alg_1']['Skor']}**")
                with f2: st.success(f"🎯 Ofansif\n\n**{res['alg_2']['Skor']}**")
                with f3: st.warning(f"🛡️ Spektrum\n\n**{res['alg_3']['Skor']}**")
                
                st.markdown(f"<div class
