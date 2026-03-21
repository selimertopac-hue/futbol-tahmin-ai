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

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .form-circle { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 8px; margin-top: 10px; }
    .filter-label { font-size: 0.75rem; font-weight: bold; color: #8B949E; margin-bottom: 5px; text-align: center; text-transform: uppercase; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU (SPEKTRUM ANALİZİ DAHİL) ---
def master_analiz_et(ev_ad, dep_ad, matches):
    df_raw = [m for m in matches if m['status'] == 'FINISHED']
    if not df_raw: return None
    
    df = pd.DataFrame()
    df['H'] = [m['home_h'] if 'home_h' in m else m['homeTeam']['name'] for m in df_raw] # Esneklik için
    df['H'] = [m['homeTeam']['name'] for m in df_raw]
    df['A'] = [m['awayTeam']['name'] for m in df_raw]
    df['HG'] = [m['score']['fullTime']['home'] for m in df_raw]
    df['AG'] = [m['score']['fullTime']['away'] for m in df_raw]
    
    lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
    
    # SPEKTRUM ANALİZİ İÇİN EV/DEPLASMAN AYRIMI
    ev_m = df[df['H'] == ev_ad]
    dep_m = df[df['A'] == dep_ad]
    
    if ev_m.empty or dep_m.empty: return None

    # 📍 Algoritma 1: Standart xG (Genel İstatistik)
    ev_std_xg = (ev_m['HG'].mean() / lig_ev_ort) * (dep_m['HG'].mean() / lig_ev_ort) * lig_ev_ort
    dep_std_xg = (dep_m['AG'].mean() / lig_dep_ort) * (ev_m['AG'].mean() / lig_dep_ort) * lig_dep_ort

    # 🎯 Algoritma 2: Ofansif Verimlilik (Bitiricilik Kalitesi)
    ev_bitiricilik = ev_m['HG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)
    dep_bitiricilik = dep_m['AG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)

    # 🛡️ Algoritma 3: Spektrum Gerçekliği (Ev Savunma Disiplini vs Deplasman Fırsatçılığı)
    # Ev sahibinin kalesinde gördüğü tehlikeyi (xG) gole kapatma oranı (Savunma Şansı/Disiplini)
    ev_sav_gercek = ev_m['AG'].mean() / (lig_dep_ort * (ev_m['AG'].mean() / (ev_std_xg if ev_std_xg > 0 else 1)))
    # Deplasmanın dış sahada düşük xG'li pozisyonları gole çevirme yüzdesi
    dep_huc_gercek = deplasman_maclar_verimi = dep_m['AG'].mean() / (dep_std_xg if dep_std_xg > 0 else 1)
    
    final_ev_xg = ev_std_xg * ev_bitiricilik * (1 / dep_huc_gercek if dep_huc_gercek > 0 else 1)
    final_dep_xg = dep_std_xg * dep_huc_gercek * ev_sav_gercek

    def get_probs(ex, ax):
        ex, ax = max(0.1, ex), max(0.1, ax)
        m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
        sk = np.unravel_index(np.argmax(m), m.shape)
        return {"Ev": np.sum(np.tril(m, -1))*100, "Skor": f"{sk[0]} - {sk[1]}"}

    return {
        "alg_1": get_probs(ev_std_xg, dep_std_xg),
        "alg_2": get_probs(ev_std_xg * ev_bitiricilik, dep_std_xg * dep_bitiricilik),
        "alg_3": get_probs(final_ev_xg, final_dep_xg),
        "ev_xg": ev_std_xg, "dep_xg": dep_std_xg,
        "ev_not": "🛡️ Katı Savunma" if ev_sav_gercek < 0.9 else "⚠️ Kırılgan",
        "dep_not": "⚔️ Fırsatçı" if dep_huc_gercek > 1.2 else "🐢 Kısır"
    }

# --- 4. TELEGRAM FONKSİYONU ---
def telegram_gonder(mesaj):
    if TELEGRAM_TOKEN != "BURAYA_TOKEN_GIR":
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "HTML"})

# --- 5. GÖRSEL FONKSİYONLAR ---
def form_html_uret(takim, matches):
    son_maclar = [m for m in matches if (m['homeTeam']['name'] == takim or m['awayTeam']['name'] == takim) and m['status'] == 'FINISHED']
    son_maclar = sorted(son_maclar, key=lambda x: x['utcDate'], reverse=True)[:5]
    html = ""
    for m in son_maclar:
        h_skor, a_skor = m['score']['fullTime']['home'], m['score']['fullTime']['away']
        res = "win" if (m['homeTeam']['name'] == takim and h_skor > a_skor) or (m['awayTeam']['name'] == takim and a_skor > h_skor) else ("draw" if h_skor == a_skor else "loss")
        html += f"<span class='form-circle {res}'></span>"
    return html

# --- 6. ANA PANEL ---
lig_mapping = {"İngiltere (PL)": "PL", "İspanya (PD)": "PD", "İtalya (SA)": "SA", "Almanya (BL1)": "BL1", "Fransa (FL1)": "FL1", "Hollanda (DED)": "DED"}
secim = st.sidebar.selectbox("🎯 Lig Seçimi", list(lig_mapping.keys()))

@st.cache_data(ttl=3600)
def veri_getir(url, h={}): return requests.get(url, headers=h).json()

data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_mapping[secim]}/matches", {"X-Auth-Token": FOOTBALL_DATA_KEY})
m_data = data.get('matches', [])
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

st.title("🛡️ UltraSkor Pro AI: Spectrum Dashboard")

if gelecek:
    for m in gelecek[:15]:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = master_analiz_et(ev, dep, m_data)
        
        if res:
            with st.expander(f"🏟️ {ev} vs {dep}"):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.image(m['homeTeam']['crest'], width=50)
                    st.markdown(f"Form: {form_html_uret(ev, m_data)}", unsafe_allow_html=True)
                    st.caption(f"Ev xG: {res['ev_xg']:.2f}")
                with c2:
                    st.markdown("<p style='text-align:center; font-weight:bold;'>GÜVEN ENDEKSİ</p>", unsafe_allow_html=True)
                    st.progress(res['alg_3']['Ev'] / 100)
                    st.markdown(f"<p style='text-align:center;'>Tahmin: <b>{res['alg_3']['Skor']}</b></p>", unsafe_allow_html=True)
                with c3:
                    st.image(m['awayTeam']['crest'], width=50)
                    st.markdown(f"Form: {form_html_uret(dep, m_data)}", unsafe_allow_html=True)
                    st.caption(f"Dep xG: {res['dep_xg']:.2f}")

                st.divider()
                f1, f2, f3 = st.columns(3)
                f1.info(f"📍 Standart\n\n**{res['alg_1']['Skor']}**")
                f2.success(f"🎯 Ofansif\n\n**{res['alg_2']['Skor']}**")
                f3.warning(f"🛡️ Spektrum\n\n**{res['alg_3']['Skor']}**")

                st.markdown(f"<div class='strategy-box'>📝 <b>Stratejik Not:</b> {ev} sahasında <b>{res['ev_not']}</b>, {dep} deplasmanda <b>{res['dep_not']}</b> spektrumunda.</div>", unsafe_allow_html=True)
                
                # OTOMATİK BİLDİRİM BUTONU
                if st.button(f"📲 Telegram'a Gönder: {ev[:5]}", key=ev):
                    msg = f"🛡 <b>UltraSkor Sinyal</b>\n🏟 {ev} vs {dep}\n🎯 Skor: {res['alg_3']['Skor']}\n💡 Not: {res['ev_not']} vs {res['dep_not']}"
                    telegram_gonder(msg)
                    st.toast("Mesaj gönderildi!")
