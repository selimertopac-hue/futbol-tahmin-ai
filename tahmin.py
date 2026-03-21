import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- API AYARLARI ---
# Senin özel API anahtarın
API_KEY = "b900863038174d07855ace7f33c69c9b"
BASE_URL = "https://api.football-data.org/v4/"
HEADERS = {"X-Auth-Token": API_KEY}

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="UltraSkor Pro AI", page_icon="📈", layout="wide")

# CSS ile arka planı ve yazıları biraz daha şık yapalım
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .main { background-color: #f0f2f6; }
    h1, h2, h3 { color: #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR ---
@st.cache_data(ttl=3600) # Veriyi 1 saat hafızada tut
def veri_getir(lig="PL"):
    url = f"{BASE_URL}competitions/{lig}/matches"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        return response.json()['matches']
    except: return []

def form_hesapla(takim_adi, tum_maclar):
    # Takımın bitmiş son 5 maçını bul
    bitmis = [m for m in tum_maclar if m['status'] == 'FINISHED' and 
              (m['homeTeam']['name'] == takim_adi or m['awayTeam']['name'] == takim_adi)]
    son_5 = bitmis[-5:]
    
    f = ""
    for m in son_5:
        skor_h = m['score']['fullTime']['home']
        skor_a = m['score']['fullTime']['away']
        
        if m['homeTeam']['name'] == takim_adi:
            if skor_h > skor_a: f += "🟢" # Galibiyet
            elif skor_h == skor_a: f += "🟡" # Beraberlik
            else: f += "🔴" # Mağlubiyet
        else:
            if skor_a > skor_h: f += "🟢"
            elif skor_a == skor_h: f += "🟡"
            else: f += "🔴"
    return f if f != "" else "Veri Yok"

def analiz_et(ev, dep, tum_maclar):
    # Sadece bitmiş maçlardan istatistik çıkar
    df_bitmis = pd.DataFrame([m for m in tum_maclar if m['status'] == 'FINISHED'])
    if df_bitmis.empty: return None

    # Takım isimlerini ve gollerini basitleştir
    df_bitmis['H'] = df_bitmis['homeTeam'].apply(lambda x: x['name'])
    df_bitmis['A'] = df_bitmis['awayTeam'].apply(lambda x: x['name'])
    df_bitmis['HG'] = df_bitmis['score'].apply(lambda x: x['fullTime']['home'])
    df_bitmis['AG'] = df_bitmis['score'].apply(lambda x: x['fullTime']['away'])

    # xG (Beklenen Gol) hesaplama (Basit ortalama)
    ev_xg = df_bitmis[df_bitmis['H'] == ev]['HG'].mean() if not df_bitmis[df_bitmis['H'] == ev].empty else 1.5
    dep_xg = df_bitmis[df_bitmis['A'] == dep]['AG'].mean() if not df_bitmis[df_bitmis['A'] == dep].empty else 1.2
    
    # Poisson Olasılıkları
    ev_p = [poisson.pmf(i, ev_xg) for i in range(5)]
    dep_p = [poisson.pmf(i, dep_xg) for i in range(5)]
    m = np.outer(ev_p, dep_p)
    
    # En yüksek olasılıklı skoru bul
    skor_indeks = np.unravel_index(np.argmax(m), m.shape)
    
    return {
        "Ev": np.sum(np.tril(m, -1)) * 100,
        "Ber": np.sum(np.diag(m)) * 100,
        "Dep": np.sum(np.triu(m, 1)) * 100,
        "Skor": f"{skor_indeks[0]} - {skis_indeks[1]}"
    }

# --- ARAYÜZ (GÖRÜNÜM) ---
st.title("🛡️ UltraSkor Pro AI: Canlı Analiz Paneli")
st.markdown("`Canlı Veri Bağlantısı: AKTİF ✅`")

# Sol Menü (Sidebar)
st.sidebar.header("📊 Lig Seçimi")
lig_secenekleri = {
    "İngiltere (PL)": "PL",
    "Almanya (BL1)": "BL1",
    "İtalya (SA)": "SA",
    "İspanya (PD)": "PD",
    "Hollanda (DED)": "DED",
    "Şampiyonlar Ligi (CL)": "CL"
}
secili_lig_adi = st.sidebar.selectbox("Lig Seçiniz", list(lig_secenekleri.keys()))
secili_lig_kodu = lig_secenekleri[secili_lig_adi]

# Verileri Çek
all_matches = veri_getir(secili_lig_kodu)

# Gelecek Maçları (Fikstürü) Filtrele
gelecek_maclar = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED']]

st.subheader(f"📅 {secili_lig_adi} - Haftalık Fikstür & AI Tahminleri")

if gelecek_maclar:
    # Sayfa kasmaması için ilk 10 maçı gösterelim
    for match in gelecek_maclar[:10]:
        ev_adi = match['homeTeam']['name']
        dep_adi = match['awayTeam']['name']
        tarih = match['utcDate'][:10]
        ev_logo = match['homeTeam']['crest'] # API'den gelen logo URL'si
        dep_logo = match['awayTeam']['crest'] # API'den gelen logo URL'si
        
        # Her maç için açılır bir kart (expander) oluşturalım
        with st.expander(f"📌 {tarih} | {ev_adi} vs {dep_adi}"):
            res = analiz_et(ev_adi, dep_adi, all_matches)
            
            # Form durumlarını ve logoları gösterelim
            col_logo1, col_text, col_logo2 = st.columns([1, 4, 1])
            with col_logo1: st.image(ev_logo, width=60)
            with col_text: st.markdown(f"<h3 style='text-align: center;'>{ev_adi} vs {dep_adi}</h3>", unsafe_allow_html=True)
            with col_logo2: st.image(dep_logo, width=60)

            # Form ve Analiz Sonuçları
            ev_form = form_hesapla(ev_adi, all_matches)
            dep_form = form_hesapla(dep_adi, all_matches)
            
            c1, c2, c3 = st.columns(3)
            c1.metric(f"🏠 {ev_adi}", f"%{res['Ev']:.1f}", delta=ev_form, delta_color="off")
            c2.metric("🤝 Beraberlik", f"%{res['Ber']:.1f}")
            c3.metric(f"🚀 {dep_adi}", f"%{res['Dep']:.1f}", delta=dep_form, delta_color="off")
            
            st.markdown(f"<h2 style='text-align: center; color: #1E88E5;'>🎯 Beklenen Skor: {res['Skor']}</h2>", unsafe_allow_html=True)
            
            # Risk Çubuğu (Beraberlik ihtimaline göre)
            st.write(f"**🤖 Model Güven Endeksi:** %{(max(res['Ev'], res['Dep'])):.1f}")
            st.progress(min(max(res['Ev'], res['Dep']) / 100, 1.0))

else:
    st.info("Bu ligde şu an planlanmış maç bulunamadı.")
