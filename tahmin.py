import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- 1. AYARLAR & API-FOOTBALL TANIMLARI ---
API_KEY = "ca7daa2cfcc7e961d66ba734bd2080d6"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

# API-Football Sayısal Lig ID'leri
LIGLER = {
    "İngiltere": 39,
    "İspanya": 140,
    "İtalya": 135,
    "Almanya": 78,
    "Fransa": 61,
    "Hollanda": 88
}
SEZON = 2024  # Ücretsiz planda en son tamamlanmış/aktif sezon yılı

st.set_page_config(page_title="UltraSkor Pro: AETHER Intelligence", page_icon="🎯", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; }
    .editor-card { background: linear-gradient(145deg, #1c2128, #0d1117); border: 1px solid #58A6FF; padding: 15px; border-radius: 12px; height: 100%; border-top: 4px solid #58A6FF; margin-bottom: 20px; }
    .coupon-item { background: #0d1117; padding: 8px; margin-top: 8px; border-radius: 6px; border: 1px solid #30363d; font-size: 0.85rem; }
    .coupon-title { font-weight: bold; color: #58A6FF; margin-bottom: 10px; text-align: center; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .aether-box { background: rgba(138, 43, 226, 0.1); border: 1px solid #8A2BE2; color: #E0B0FF !important; }
    .ai-insight { background: rgba(88, 166, 255, 0.05); border-left: 4px solid #58A6FF; padding: 12px; margin-top: 15px; border-radius: 4px; font-size: 0.85rem; color: #C9D1D9; }
    .standings-table { font-size: 0.8rem; width: 100%; border-collapse: collapse; background: #161b22; border-radius: 10px; overflow: hidden; margin-top: 10px; }
    .standings-table th { background: #30363d; padding: 10px; text-align: left; color: #58A6FF; }
    .standings-table td { padding: 8px 10px; border-bottom: 1px solid #30363d; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. VERİ ÇEKME MOTORU ---
@st.cache_data(ttl=3600)
def api_get(endpoint, params={}):
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if r.status_code == 200:
            res = r.json()
            return res.get("response", [])
        return []
    except:
        return []

def winner(sk):
    try:
        p = sk.split(" - ")
        if int(p[0]) > int(p[1]): return "1"
        if int(p[1]) > int(p[0]): return "2"
        return "X"
    except:
        return "?"

# --- 4. ANALİZ MOTORU ---
def analiz_et(ev_ad, dep_ad, tum_fikstur):
    try:
        bitenler = [m for m in tum_fikstur if m['fixture']['status']['short'] in ['FT', 'AET', 'PEN']]
        if len(bitenler) < 10:
            return None
            
        df = pd.DataFrame([{
            'H': m['teams']['home']['name'],
            'A': m['teams']['away']['name'],
            'HG': m['goals']['home'],
            'AG': m['goals']['away']
        } for m in bitenler if m['goals']['home'] is not None])
        
        l_e, l_d = df['HG'].mean(), df['AG'].mean()
        
        def takim_istatistik(takim, ev_mi):
            sub = df[df['H' if ev_mi else 'A'] == takim]
            if sub.empty: return l_e, l_d
            g = sub['HG' if ev_mi else 'AG'].mean()
            y = sub['AG' if ev_mi else 'HG'].mean()
            return g, y
            
        e_g, e_y = takim_istatistik(ev_ad, True)
        d_g, d_y = takim_istatistik(dep_ad, False)
        
        ex = (e_g / max(0.1, l_e)) * (d_y / max(0.1, l_e)) * l_e
        ax = (d_g / max(0.1, l_d)) * (e_y / max(0.1, l_d)) * l_d
        
        def skor_hesapla(e, a):
            matrix = np.outer(
                [poisson.pmf(i, max(0.1, e)) for i in range(6)],
                [poisson.pmf(i, max(0.1, a)) for i in range(6)]
            )
            s = np.unravel_index(np.argmax(matrix), matrix.shape)
            conf = min(95, int(abs(e - a) * 35 + 30))
            return f"{s[0]} - {s[1]}", conf

        r_std = skor_hesapla(ex * 1.05, ax * 0.95)
        r_sp = skor_hesapla(ex * 1.15, ax * 1.15)
        r_nx = skor_hesapla(ex * 0.90, ax * 1.05)
        
        ae_e = (ex * 0.4) + (ex * 1.15 * 0.3) + (ex * 0.90 * 0.3)
        ae_a = (ax * 0.4) + (ax * 1.15 * 0.3) + (ax * 1.05 * 0.3)
        r_ae = skor_hesapla(ae_e, ae_a)
        
        return {
            "std": r_std[0], "s_c": r_std[1],
            "spec": r_sp[0], "sp_c": r_sp[1],
            "nexus": r_nx[0], "n_c": r_nx[1],
            "aether": r_ae[0], "ae_c": r_ae[1],
            "total_xg": ex + ax
        }
    except:
        return None

# --- 5. MENÜ VE ARAYÜZ ---
mod = st.sidebar.radio("🚀 Menü", ["🤖 Tahmin Robotu", "🏠 Canlı Skorlar", "📊 Lig Puan Durumu"])

if mod == "🤖 Tahmin Robotu":
    st.title("🤖 AI Tahmin Robotu (API-Football Destekli)")
    secilen_lig = st.sidebar.selectbox("🎯 Analiz Edilecek Lig", list(LIGLER.keys()))
    lig_id = LIGLER[secilen_lig]
    
    with st.spinner("Fikstür ve maç verileri çekiliyor..."):
        fikstur = api_get("fixtures", {"league": lig_id, "season": SEZON})
    
    if not fikstur:
        st.warning(f"⚠️ {secilen_lig} için fikstür verisi bulunamadı. API limitinizi veya sezon yılını kontrol edin.")
    else:
        yaklasanlar = [m for m in fikstur if m['fixture']['status']['short'] in ['NS', 'TBD']][:10]
        if not yaklasanlar:
            yaklasanlar = fikstur[-10:]  # Sezon bittiyse son 10 maçı gösterir
            
        havuz = []
        for m in yaklasanlar:
            ev = m['teams']['home']['name']
            dep = m['teams']['away']['name']
            res = analiz_et(ev, dep, fikstur)
            if res:
                m['res'] = res
                havuz.append(m)
                
        if havuz:
            t1, t2 = st.tabs(["✨ AETHER & STANDART TAHMİNLER", "⚽ GOL / XG BEKLENTİSİ"])
            with t1:
                for m in havuz:
                    res = m['res']
                    st.markdown(f"""
                        <div class="match-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="text-align: right; width: 40%;"><b>{m['teams']['home']['name']}</b></div>
                                <div style="width: 20%; text-align: center; background: #30363d; border-radius: 5px; padding: 5px;">
                                    <h4 style="margin: 0; color: #58A6FF;">{res['aether']}</h4>
                                    <small style="color: #8B949E;">Güven: %{res['ae_c']}</small>
                                </div>
                                <div style="text-align: left; width: 40%;"><b>{m['teams']['away']['name']}</b></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            with t2:
                for m in sorted(havuz, key=lambda x: x['res']['total_xg'], reverse=True):
                    res = m['res']
                    st.markdown(f"""
                        <div class="coupon-item">
                            <b>{m['teams']['home']['name']} - {m['teams']['away']['name']}</b> | 
                            Toplam xG: <b style="color:#3fb950;">{res['total_xg']:.2f}</b> | 
                            Tavsiye: <b>{'2.5 ÜST' if res['total_xg'] > 2.5 else '2.5 ALT'}</b>
                        </div>
                    """, unsafe_allow_html=True)

elif mod == "🏠 Canlı Skorlar":
    st.title("⚡ Canlı Maç Merkezi")
    live_matches = api_get("fixtures", {"live": "all"})
    
    if not live_matches:
        st.info("Şu an dünyada oynanan aktif canlı maç bulunmuyor.")
    else:
        for m in live_matches:
            st.markdown(f"""
                <div class="match-card" style="border-left: 5px solid #3fb950;">
                    <small style="color: #8B949E;">{m['league']['name']} ({m['league']['country']}) - {m['fixture']['status']['elapsed']}'</small>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 5px;">
                        <div style="text-align: right; width: 40%;"><b>{m['teams']['home']['name']}</b></div>
                        <div style="width: 20%; text-align: center; background: #30363d; border-radius: 5px; padding: 5px;">
                            <h3 style="margin: 0; color: #3fb950;">{m['goals']['home']} - {m['goals']['away']}</h3>
                        </div>
                        <div style="text-align: left; width: 40%;"><b>{m['teams']['away']['name']}</b></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

elif mod == "📊 Lig Puan Durumu":
    st.title("📊 Lig Puan Durumu")
    secilen_lig = st.selectbox("Lig Seçin", list(LIGLER.keys()))
    standings_data = api_get("standings", {"league": LIGLER[secilen_lig], "season": SEZON})
    
    if standings_data and len(standings_data) > 0:
        tablo = standings_data[0]['league']['standings'][0]
        html = '<table class="standings-table"><tr><th>#</th><th>Takım</th><th>O</th><th>G</th><th>B</th><th>M</th><th>P</th></tr>'
        for row in tablo:
            html += f'<tr><td>{row["rank"]}</td><td>{row["team"]["name"]}</td><td>{row["all"]["played"]}</td><td>{row["all"]["win"]}</td><td>{row["all"]["draw"]}</td><td>{row["all"]["lose"]}</td><td><b>{row["points"]}</b></td></tr>'
        html += '</table>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.warning("Puan durumu verisi alınamadı.")
