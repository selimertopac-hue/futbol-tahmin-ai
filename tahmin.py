import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API ANAHTARLARIN ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
ODDS_API_KEY = "b4040bb05379cd7d9b94f18f2b74b133"

st.set_page_config(page_title="UltraSkor AI: Radar", page_icon="📡", layout="wide")

# --- DARK MODE & STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .best-card { background-color: #161B22; border: 2px solid #58A6FF; padding: 15px; border-radius: 12px; text-align: center; height: 100%; }
    .value-card { background-color: #064e3b; color: #34d399; padding: 15px; border-radius: 10px; border: 1px solid #059669; text-align: center; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def oranlari_cek(lig_odds):
    url = f"https://api.the-odds-api.com/v4/sports/{lig_odds}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
    try: return requests.get(url, timeout=10).json()
    except: return []

@st.cache_data(ttl=3600)
def maclari_getir(lig_code):
    url = f"https://api.football-data.org/v4/competitions/{lig_code}/matches"
    try: return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=10).json().get('matches', [])
    except: return []

def analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return {"Ev": 33.3, "Ber": 33.3, "Dep": 33.3, "Skor": "0 - 0"}
    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score'].apply(lambda x: x['fullTime']['home']), df['score'].apply(lambda x: x['fullTime']['away'])
    ev_xg = df[df['H'] == ev]['HG'].mean() if not df[df['H'] == ev].empty else 1.5
    dep_xg = df[df['A'] == dep]['AG'].mean() if not df[df['A'] == dep].empty else 1.2
    m = np.outer([poisson.pmf(i, ev_xg) for i in range(5)], [poisson.pmf(i, dep_xg) for i in range(5)])
    sk = np.unravel_index(np.argmax(m), m.shape)
    return {"Ev": np.sum(np.tril(m, -1))*100, "Ber": np.sum(np.diag(m))*100, "Dep": np.sum(np.triu(m, 1))*100, "Skor": f"{sk[0]} - {sk[1]}"}

# --- ANA PANEL ---
st.title("🛡️ UltraSkor AI: Stratejik Radar")

lig_mapping = {
    "İngiltere (PL)": {"code": "PL", "odds": "soccer_epl"},
    "İspanya (PD)": {"code": "PD", "odds": "soccer_spain_la_liga"},
    "Almanya (BL1)": {"code": "BL1", "odds": "soccer_germany_bundesliga"},
    "İtalya (SA)": {"code": "SA", "odds": "soccer_italy_serie_a"},
    "Fransa (FL1)": {"code": "FL1", "odds": "soccer_france_ligue_one"}
}

secim = st.sidebar.selectbox("🎯 Analiz Edilecek Lig", list(lig_mapping.keys()))
m_data = maclari_getir(lig_mapping[secim]['code'])
canli_oranlar = oranlari_cek(lig_mapping[secim]['odds'])
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

# --- BEST PICK HESAPLAMA ---
best_ai = {"mac": "-", "prob": 0, "skor": "-"}
best_value = {"mac": "-", "avantaj": -100, "oran": 0, "skor": "-"}

all_results = []
if gelecek:
    for m in gelecek[:12]:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = analiz_et(ev, dep, m_data)
        
        # Best AI bul (Ev veya Dep en yüksek hangisiyse)
        current_max_prob = max(res['Ev'], res['Dep'])
        if current_max_prob > best_ai['prob']:
            best_ai = {"mac": f"{ev} - {dep}", "prob": current_max_prob, "skor": res['Skor']}
            
        # Best Value bul
        mac_orani = next((o for o in canli_oranlar if ev[:5].lower() in o['home_team'].lower() or o['home_team'][:5].lower() in ev.lower()), None)
        if mac_orani and 'bookmakers' in mac_orani:
            h2h = mac_orani['bookmakers'][0]['markets'][0]['outcomes']
            oran_ev = next((o['price'] for o in h2h if o['name'].lower() == mac_orani['home_team'].lower()), 1.0)
            avantaj = ((res['Ev'] / 100) * oran_ev) - 1
            if avantaj > best_value['avantaj']:
                best_value = {"mac": f"{ev} - {dep}", "avantaj": avantaj * 100, "oran": oran_ev, "skor": res['Skor']}
        
        all_results.append((m, res, mac_orani))

# --- GÖRSEL "BEST" PANELİ ---
st.markdown("### 🌟 Günün Analiz Raporu")
c_best1, c_best2 = st.columns(2)

with c_best1:
    st.markdown(f"""<div class='best-card'>
        <h3>🏆 En Yüksek Olasılık</h3>
        <p style='font-size: 1.2rem;'>{best_ai['mac']}</p>
        <h2 style='color: #34d399 !important;'>%{best_ai['prob']:.1f} Güven</h2>
        <p>Tahmin: {best_ai['skor']}</p>
    </div>""", unsafe_allow_html=True)

with c_best2:
    st.markdown(f"""<div class='best-card' style='border-color: #fbbf24;'>
        <h3>💰 En Yüksek Değer (Value)</h3>
        <p style='font-size: 1.2rem;'>{best_value['mac']}</p>
        <h2 style='color: #fbbf24 !important;'>%{best_value['avantaj']:.1f} Avantaj</h2>
        <p>Piyasa Oranı: {best_value['oran']} | Tahmin: {best_value['skor']}</p>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# --- LİSTE GÖRÜNÜMÜ ---
if all_results:
    for m, res, mac_orani in all_results:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        with st.expander(f"🔍 {ev} vs {dep}"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"🏠 Ev: %{res['Ev']:.1f} | 🤝 Ber: %{res['Ber']:.1f} | 🚀 Dep: %{res['Dep']:.1f}")
                st.info(f"🎯 Beklenen Skor: {res['Skor']}")
            with c2:
                if mac_orani:
                    h2h = mac_orani['bookmakers'][0]['markets'][0]['outcomes']
                    oran_ev = next((o['price'] for o in h2h if o['name'].lower() == mac_orani['home_team'].lower()), 1.0)
                    st.write(f"Piyasa Oranı: **{oran_ev}**")
                    avantaj = ((res['Ev'] / 100) * oran_ev) - 1
                    if avantaj > 0.05: st.markdown(f"<div class='value-card'>🔥 VALUE: %{avantaj*100:.1f}</div>", unsafe_allow_html=True)
                else: st.write("❌ Oran eşleşmedi.")
