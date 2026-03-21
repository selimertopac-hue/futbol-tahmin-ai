import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API ANAHTARLARIN ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
ODDS_API_KEY = "b4040bb05379cd7d9b94f18f2b74b133"

st.set_page_config(page_title="UltraSkor Pro AI", page_icon="🛡️", layout="wide")

# --- GELİŞMİŞ STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .best-card { background-color: #161B22; border: 2px solid #58A6FF; padding: 15px; border-radius: 12px; text-align: center; }
    .stat-card { background-color: #1C2128; border: 1px solid #30363D; padding: 12px; border-radius: 10px; text-align: center; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DERİN ANALİZ FONKSİYONU ---
def derin_analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None

    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score'].apply(lambda x: x['fullTime']['home']), df['score'].apply(lambda x: x['fullTime']['away'])

    lig_ev_ort = df['HG'].mean()
    lig_dep_ort = df['AG'].mean()

    ev_maclar = df[df['H'] == ev]
    dep_maclar = df[df['A'] == dep]

    if ev_maclar.empty or dep_maclar.empty:
        ev_beklenen, dep_beklenen = 1.5, 1.1
    else:
        ev_hucum = ev_maclar['HG'].mean() / lig_ev_ort
        dep_savunma = dep_maclar['HG'].mean() / lig_ev_ort
        dep_hucum = dep_maclar['AG'].mean() / lig_dep_ort
        ev_savunma = ev_maclar['AG'].mean() / lig_dep_ort
        ev_beklenen = ev_hucum * dep_savunma * lig_ev_ort
        dep_beklenen = dep_hucum * ev_savunma * lig_dep_ort

    m = np.outer([poisson.pmf(i, ev_beklenen) for i in range(6)], [poisson.pmf(i, dep_beklenen) for i in range(6)])
    sk = np.unravel_index(np.argmax(m), m.shape)
    
    return {
        "Ev": np.sum(np.tril(m, -1))*100, "Ber": np.sum(np.diag(m))*100, "Dep": np.sum(np.triu(m, 1))*100,
        "Skor": f"{sk[0]} - {sk[1]}", "ev_xg": ev_beklenen, "dep_xg": dep_beklenen
    }

@st.cache_data(ttl=3600)
def veri_getir(url, headers={}):
    try: return requests.get(url, headers=headers, timeout=10).json()
    except: return {}

# --- ANA PANEL ---
st.title("🛡️ UltraSkor Pro AI: Stratejik Radar")

lig_mapping = {
    "İngiltere (PL)": {"code": "PL", "odds": "soccer_epl"},
    "İspanya (PD)": {"code": "PD", "odds": "soccer_spain_la_liga"},
    "İtalya (SA)": {"code": "SA", "odds": "soccer_italy_serie_a"},
    "Almanya (BL1)": {"code": "BL1", "odds": "soccer_germany_bundesliga"}
}
secim = st.sidebar.selectbox("🎯 Lig Seç", list(lig_mapping.keys()))

# Verileri Çek
m_data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_mapping[secim]['code']}/matches", {"X-Auth-Token": FOOTBALL_DATA_KEY}).get('matches', [])
o_data = veri_getir(f"https://api.the-odds-api.com/v4/sports/{lig_mapping[secim]['odds']}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h")
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

# --- BEST PICK HESAPLAMA (Burada yapılıyor ki yukarıda görünsün) ---
best_ai = {"mac": "-", "prob": 0, "skor": "-"}
best_val = {"mac": "-", "avantaj": -100, "oran": 0}
analiz_listesi = []

if gelecek:
    for m in gelecek[:10]:
        res = derin_analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_data)
        if res:
            # Best AI
            p = max(res['Ev'], res['Dep'])
            if p > best_ai['prob']: best_ai = {"mac": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}", "prob": p, "skor": res['Skor']}
            
            # Best Value
            mac_orani = next((o for o in o_data if m['homeTeam']['name'][:5].lower() in o['home_team'].lower()), None)
            avantaj = -100
            oran_ev = 0
            if mac_orani:
                oran_ev = mac_orani['bookmakers'][0]['markets'][0]['outcomes'][0]['price']
                avantaj = ((res['Ev'] / 100) * oran_ev) - 1
                if avantaj*100 > best_val['avantaj']: best_val = {"mac": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}", "avantaj": avantaj*100, "oran": oran_ev}
            
            analiz_listesi.append((m, res, mac_orani, avantaj))

# --- GÖRSEL PANELLER ---
st.markdown("### 🌟 Günün Analiz Raporu")
c_b1, c_b2 = st.columns(2)
with c_b1:
    st.markdown(f"<div class='best-card'><h4>🏆 En Yüksek Olasılık</h4><h2>%{best_ai['prob']:.1f} Güven</h2><p>{best_ai['mac']}<br>Tahmin: {best_ai['skor']}</p></div>", unsafe_allow_html=True)
with c_b2:
    color = "#34d399" if best_val['avantaj'] > 0 else "#8B949E"
    st.markdown(f"<div class='best-card' style='border-color: {color};'><h4>💰 En Yüksek Değer</h4><h2>%{best_val['avantaj']:.1f} Avantaj</h2><p>{best_val['mac']}<br>Oran: {best_val['oran']}</p></div>", unsafe_allow_html=True)

st.markdown("---")

if analiz_listesi:
    for m, res, mac_orani, av in analiz_listesi:
        with st.expander(f"🔍 {m['homeTeam']['name']} vs {m['awayTeam']['name']}"):
            col_st, col_tx = st.columns([2, 1])
            with col_st:
                st.markdown("#### 📊 Maç Dinamikleri (xG)")
                ca, cb = st.columns(2)
                ca.markdown(f"<div class='stat-card'>🏠 Ev xG<br><b>{res['ev_xg']:.2f}</b></div>", unsafe_allow_html=True)
                cb.markdown(f"<div class='stat-card'>🚀 Dep xG<br><b>{res['dep_xg']:.2f}</b></div>", unsafe_allow_html=True)
                st.write(f"Olasılıklar: Ev %{res['Ev']:.1f} | Ber %{res['Ber']:.1f} | Dep %{res['Dep']:.1f}")
                st.progress(res['Ev']/100)
            with col_tx:
                st.info(f"🎯 Skor: **{res['Skor']}**")
                if av > 0.05: st.success(f"🔥 VALUE: %{av*100:.1f}")
