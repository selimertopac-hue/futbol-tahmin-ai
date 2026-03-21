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

# --- GELİŞMİŞ CSS (DARK MODE & VALUE CARD) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .value-card { padding: 15px; border-radius: 10px; text-align: center; margin-top: 10px; border: 1px solid #30363D; }
    .high-value { background-color: #064e3b; color: #34d399; border-color: #059669; }
    .mid-value { background-color: #451a03; color: #fbbf24; border-color: #d97706; }
    .no-value { background-color: #1c1c1c; color: #888; border-color: #333; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def veri_getir(endpoint, lig="PL"):
    url = f"{BASE_URL}competitions/{lig}/{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        return response.json()
    except: return {}

def analiz_et(ev, dep, matches):
    df = pd.DataFrame([m for m in matches if m['status'] == 'FINISHED'])
    if df.empty: return None
    df['H'], df['A'] = df['homeTeam'].apply(lambda x: x['name']), df['awayTeam'].apply(lambda x: x['name'])
    df['HG'], df['AG'] = df['score'].apply(lambda x: x['fullTime']['home']), df['score'].apply(lambda x: x['fullTime']['away'])
    ev_xg = df[df['H'] == ev]['HG'].mean() if not df[df['H'] == ev].empty else 1.5
    dep_xg = df[df['A'] == dep]['AG'].mean() if not df[df['A'] == dep].empty else 1.2
    m = np.outer([poisson.pmf(i, ev_xg) for i in range(5)], [poisson.pmf(i, dep_xg) for i in range(5)])
    sk = np.unravel_index(np.argmax(m), m.shape)
    return {"Ev": np.sum(np.tril(m, -1))*100, "Ber": np.sum(np.diag(m))*100, "Dep": np.sum(np.triu(m, 1))*100, "Skor": f"{sk[0]} - {sk[1]}"}

# --- ANA PANEL ---
st.title("🛡️ UltraSkor Pro AI: Value Bet Manager")

ligler = {"İngiltere (PL)": "PL", "Almanya (BL1)": "BL1", "İtalya (SA)": "SA", "İspanya (PD)": "PD", "Hollanda (DED)": "DED"}
secili_lig = st.sidebar.selectbox("🎯 Lig Seç", list(ligler.keys()))
lig_kodu = ligler[secili_lig]

# VERİ ÇEKİMİ (Hatasız Satır)
m_data = veri_getir("matches", lig_kodu).get('matches', [])
s_data = veri_getir("standings", lig_kodu).get('standings', [{}])[0].get('table', [])
gelecek = [m for m in m_data if m['status'] in ['SCHEDULED', 'TIMED']]

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📈 Lig Tablosu")
    if s_data:
        df_p = pd.DataFrame([{"#": t['position'], "Takım": t['team']['name'], "P": t['points']} for t in s_data])
        st.dataframe(df_p, hide_index=True, use_container_width=True)

with col2:
    st.subheader("📅 Stratejik Analiz Paneli")
    if gelecek:
        for m in gelecek[:8]:
            ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
            res = analiz_et(ev, dep, m_data)
            
            with st.expander(f"🔍 {ev} - {dep} (Detaylı Analiz)"):
                # Sol: İstatistikler, Sağ: Bahis Hesaplayıcı
                c_stats, c_bet = st.columns([1.2, 1])
                
                with c_stats:
                    st.write(f"📊 **AI Tahmini:** {res['Skor']}")
                    st.write(f"🏠 Ev: %{res['Ev']:.1f} | 🤝 Ber: %{res['Ber']:.1f} | 🚀 Dep: %{res['Dep']:.1f}")
                    st.progress(res['Ev']/100)
                
                with c_bet:
                    st.markdown("🔍 **Değer Analizi Yap**")
                    oran = st.number_input(f"Oran Gir:", min_value=1.01, value=1.85, key=f"inp_{ev}")
                    
                    # ANALİZ BUTONU
                    if st.button(f"Hesapla: {ev}", key=f"btn_{ev}"):
                        avantaj = ((res['Ev'] / 100) * oran) - 1
                        
                        if avantaj > 0.15:
                            st.balloons() # Büyük fırsatta balonlar uçsun!
                            st.success(f"💎 ELMAS FIRSAT! \n\n Avantaj: %{avantaj*100:.1f}")
                            st.write("🤖 AI Notu: Bahis şirketi bu maçta ev sahibini çok küçümsemiş!")
                        elif avantaj > 0:
                            st.warning(f"✅ Değerli Bahis \n\n Avantaj: %{avantaj*100:.1f}")
                        else:
                            st.error("❌ Değer Yok \n\n Bu oran risk almaya değmez.")
