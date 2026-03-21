import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API ANAHTARLARIN ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
ODDS_API_KEY = "b4040bb05379cd7d9b94f18f2b74b133"

st.set_page_config(page_title="UltraSkor Pro: Dashboard", page_icon="📈", layout="wide")

# --- PRO STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .best-card { background: linear-gradient(135deg, #161B22 0%, #0D1117 100%); border: 1px solid #30363D; padding: 20px; border-radius: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .form-circle { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin: 0 2px; }
    .win { background-color: #238636; } .draw { background-color: #D29922; } .loss { background-color: #DA3633; }
    .stat-label { font-size: 0.8rem; color: #8B949E; margin-bottom: 2px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR ---
def form_getir(takim_adi, matches):
    # Takımın son 5 maçını bul ve form dizisini oluştur
    son_maclar = [m for m in matches if (m['homeTeam']['name'] == takim_adi or m['awayTeam']['name'] == takim_adi) and m['status'] == 'FINISHED']
    son_maclar = sorted(son_maclar, key=lambda x: x['utcDate'], reverse=True)[:5]
    
    form = []
    for m in son_maclar:
        skor_h = m['score']['fullTime']['home']
        skor_a = m['score']['fullTime']['away']
        if m['homeTeam']['name'] == takim_adi:
            if skor_h > skor_a: form.append("win")
            elif skor_h == skor_a: form.append("draw")
            else: form.append("loss")
        else:
            if skor_a > skor_h: form.append("win")
            elif skor_a == skor_h: form.append("draw")
            else: form.append("loss")
    return form

def derin_analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None
    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score'].apply(lambda x: x['fullTime']['home']), df['score'].apply(lambda x: x['fullTime']['away'])
    
    lig_ev_ort, lig_dep_ort = df['HG'].mean(), df['AG'].mean()
    ev_m, dep_m = df[df['H'] == ev], df[df['A'] == dep]
    
    if ev_m.empty or dep_m.empty: ev_xg, dep_xg = 1.5, 1.1
    else:
        ev_xg = (ev_m['HG'].mean() / lig_ev_ort) * (dep_m['HG'].mean() / lig_ev_ort) * lig_ev_ort
        dep_xg = (dep_m['AG'].mean() / lig_dep_ort) * (ev_m['AG'].mean() / lig_dep_ort) * lig_dep_ort

    m = np.outer([poisson.pmf(i, ev_xg) for i in range(6)], [poisson.pmf(i, dep_xg) for i in range(6)])
    sk = np.unravel_index(np.argmax(m), m.shape)
    return {"Ev": np.sum(np.tril(m, -1))*100, "Ber": np.sum(np.diag(m))*100, "Dep": np.sum(np.triu(m, 1))*100, "Skor": f"{sk[0]} - {sk[1]}", "ev_xg": ev_xg, "dep_xg": dep_xg}

@st.cache_data(ttl=3600)
def veri_getir(url, headers={}):
    try: return requests.get(url, headers=headers, timeout=10).json()
    except: return {}

# --- ANA PANEL ---
st.title("🛡️ UltraSkor Pro Dashboard")

lig_mapping = {
    "İngiltere (PL)": {"code": "PL", "odds": "soccer_epl"},
    "İspanya (PD)": {"code": "PD", "odds": "soccer_spain_la_liga"},
    "İtalya (SA)": {"code": "SA", "odds": "soccer_italy_serie_a"},
    "Almanya (BL1)": {"code": "BL1", "odds": "soccer_germany_bundesliga"},
    "Fransa (FL1)": {"code": "FL1", "odds": "soccer_france_ligue_one"},
    "Hollanda (DED)": {"code": "DED", "odds": "soccer_netherlands_ere_divisie"}
}

secim = st.sidebar.selectbox("🎯 Lig Seçimi", list(lig_mapping.keys()))

m_data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_mapping[secim]['code']}/matches", {"X-Auth-Token": FOOTBALL_DATA_KEY}).get('matches', [])
o_data = veri_getir(f"https://api.the-odds-api.com/v4/sports/{lig_mapping[secim]['odds']}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h")
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

# --- ANALİZ DÖNGÜSÜ ---
analiz_listesi = []
best_ai = {"mac": "-", "prob": 0, "skor": "-"}
best_val = {"mac": "-", "avantaj": -100}

if gelecek:
    for m in gelecek[:15]:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = derin_analiz_et(ev, dep, m_data)
        if res:
            p = max(res['Ev'], res['Dep'])
            if p > best_ai['prob']: best_ai = {"mac": f"{ev} vs {dep}", "prob": p, "skor": res['Skor']}
            
            mac_orani = next((o for o in o_data if ev[:5].lower() in o['home_team'].lower()), None)
            av = -100
            if mac_orani:
                oran = mac_orani['bookmakers'][0]['markets'][0]['outcomes'][0]['price']
                av = ((res['Ev'] / 100) * oran) - 1
                if av*100 > best_val['avantaj']: best_val = {"mac": f"{ev} vs {dep}", "avantaj": av*100}
            
            analiz_listesi.append((m, res, av))

# --- GÖRSEL RAPOR ---
st.markdown("### 🌟 Stratejik Özet")
c1, c2 = st.columns(2)
with c1: st.markdown(f"<div class='best-card'><h4 style='margin:0'>🏆 EN BANKO</h4><h2 style='color:#58A6FF'>%{best_ai['prob']:.1f}</h2><p>{best_ai['mac']}<br>Skor: {best_ai['skor']}</p></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='best-card'><h4 style='margin:0'>💰 EN DEĞERLİ</h4><h2 style='color:#34D399'>%{best_val['avantaj']:.1f}</h2><p>{best_val['mac']}</p></div>", unsafe_allow_html=True)

st.markdown("---")

# --- DETAYLI MAÇ KARTLARI ---
for m, res, av in analiz_listesi:
    with st.expander(f"🏟️ {m['homeTeam']['name']} vs {m['awayTeam']['name']}"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        # Ev Sahibi Form
        with col1:
            st.image(m['homeTeam']['crest'], width=50)
            form_html = "".join([f"<span class='form-circle {f}'></span>" for f in form_getir(m['homeTeam']['name'], m_data)])
            st.markdown(f"Form: {form_html}", unsafe_allow_html=True)
            st.write(f"xG: **{res['ev_xg']:.2f}**")
            
        # Analiz Merkezi
        with col2:
            st.markdown("<p style='text-align:center; font-weight:bold;'>MAÇ DENGESİ</p>", unsafe_allow_html=True)
            st.progress(res['Ev']/100)
            st.write(f"Ev: %{res['Ev']:.1f} | Ber: %{res['Ber']:.1f} | Dep: %{res['Dep']:.1f}")
            st.markdown(f"<h3 style='text-align:center;'>🎯 {res['Skor']}</h3>", unsafe_allow_html=True)
            
        # Deplasman Form
        with col3:
            st.image(m['awayTeam']['crest'], width=50)
            form_html = "".join([f"<span class='form-circle {f}'></span>" for f in form_getir(m['awayTeam']['name'], m_data)])
            st.markdown(f"Form: {form_html}", unsafe_allow_html=True)
            st.write(f"xG: **{res['dep_xg']:.2f}**")

        if av > 0.10:
            st.success(f"💎 Sinyal: Bu maçta %{av*100:.1f} matematiksel avantaj var!")
