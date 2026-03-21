import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API AYARLARI ---
API_KEY = "b900863038174d07855ace7f33c69c9b"
BASE_URL = "https://api.football-data.org/v4/"
HEADERS = {"X-Auth-Token": API_KEY}

st.set_page_config(page_title="UltraSkor Pro AI", page_icon="⚽", layout="wide")

# --- FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def maclari_getir(lig="PL"):
    url = f"{BASE_URL}competitions/{lig}/matches"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        return response.json()['matches']
    except: return []

@st.cache_data(ttl=3600)
def puan_durumu_getir(lig="PL"):
    url = f"{BASE_URL}competitions/{lig}/standings"
    try:
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        return pd.DataFrame([{
            "Sıra": t['position'], "Takım": t['team']['name'], "O": t['playedGames'],
            "G": t['won'], "B": t['draw'], "M": t['lost'], "P": t['points'], "Av": t['goalDifference']
        } for t in data['standings'][0]['table']])
    except: return pd.DataFrame()

def form_hesapla(takim_adi, tum_maclar):
    bitmis = [m for m in tum_maclar if m['status'] == 'FINISHED' and (m['homeTeam']['name'] == takim_adi or m['awayTeam']['name'] == takim_adi)]
    f = ""
    for m in bitmis[-5:]:
        sh, sa = m['score']['fullTime']['home'], m['score']['fullTime']['away']
        if m['homeTeam']['name'] == takim_adi:
            if sh > sa: f += "🟢"
            elif sh == sa: f += "🟡"
            else: f += "🔴"
        else:
            if sa > sh: f += "🟢"
            elif sa == sh: f += "🟡"
            else: f += "🔴"
    return f if f != "" else "Veri Yok"

def analiz_et(ev, dep, tum_maclar):
    df = pd.DataFrame([m for m in tum_maclar if m['status'] == 'FINISHED'])
    if df.empty: return None
    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score'].apply(lambda x: x['fullTime']['home']), df['score'].apply(lambda x: x['fullTime']['away'])
    ev_xg = df[df['H'] == ev]['HG'].mean() if not df[df['H'] == ev].empty else 1.5
    dep_xg = df[df['A'] == dep]['AG'].mean() if not df[df['A'] == dep].empty else 1.2
    m = np.outer([poisson.pmf(i, ev_xg) for i in range(5)], [poisson.pmf(i, dep_xg) for i in range(5)])
    sk = np.unravel_index(np.argmax(m), m.shape)
    return {"Ev": np.sum(np.tril(m, -1))*100, "Ber": np.sum(np.diag(m))*100, "Dep": np.sum(np.triu(m, 1))*100, "Skor": f"{sk[0]} - {sk[1]}"}

# --- ARAYÜZ ---
st.title("🏆 UltraSkor Pro AI: Akıllı Futbol Analiz Merkezi")

st.sidebar.header("📊 Lig Yönetimi")
ligler = {"İngiltere (PL)": "PL", "Almanya (BL1)": "BL1", "İtalya (SA)": "SA", "İspanya (PD)": "PD", "Hollanda (DED)": "DED"}
secili_lig_adi = st.sidebar.selectbox("Lig Seçiniz", list(ligler.keys()))
secili_lig_kodu = ligler[secili_lig_adi]

all_matches = maclari_getir(secili_lig_kodu)
df_puan = puan_durumu_getir(secili_lig_kodu)
gelecek = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED']]

# --- GÜNÜN FAVORİSİ HESAPLAMA ---
favori_mac = None
if gelecek:
    analizler = []
    for m in gelecek[:10]:
        res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], all_matches)
        if res:
            guven = max(res['Ev'], res['Dep'])
            analizler.append({"mac": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}", "guven": guven, "skor": res['Skor']})
    if analizler:
        favori_mac = max(analizler, key=lambda x: x['guven'])

# --- GÜNÜN FAVORİSİ PANELİ ---
if favori_mac:
    st.success(f"🤖 **YAPAY ZEKA GÜNÜN TAVSİYESİ:** {favori_mac['mac']} | **Tahmin:** {favori_mac['skor']} (Güven: %{favori_mac['guven']:.1f})")

st.markdown("---")

# --- ANA PANEL ---
col_puan, col_tahmin = st.columns([1.2, 2])

with col_puan:
    st.subheader("📈 Puan Durumu")
    st.dataframe(df_puan, hide_index=True, use_container_width=True)

with col_tahmin:
    st.subheader("📅 Haftalık Fikstür")
    if gelecek:
        for m in gelecek[:10]:
            ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
            res = analiz_et(ev, dep, all_matches)
            with st.expander(f"⚽ {ev} - {dep}"):
                c_l, c_m, c_r = st.columns([1, 2, 1])
                with c_l: st.image(m['homeTeam']['crest'], width=50)
                with c_m: st.markdown(f"<p style='text-align: center;'>{ev}<br>vs<br>{dep}</p>", unsafe_allow_html=True)
                with c_r: st.image(m['awayTeam']['crest'], width=50)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Ev", f"%{res['Ev']:.1f}", delta=form_hesapla(ev, all_matches), delta_color="off")
                c2.metric("Ber", f"%{res['Ber']:.1f}")
                c3.metric("Dep", f"%{res['Dep']:.1f}", delta=form_hesapla(dep, all_matches), delta_color="off")
                st.info(f"🎯 Skor Tahmini: **{res['Skor']}**")
    else:
        st.info("Maç bulunamadı.")
