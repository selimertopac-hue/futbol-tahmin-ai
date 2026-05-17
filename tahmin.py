import streamlit as st
import json
import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- 1. AYARLAR & API-FOOTBALL KEY ---
# İlettiğin API anahtarı sisteme mühürlendi
API_KEY = "ca7daa2cfcc7e961d66ba734bd2080d6"
BASE_URL = "https://v3.football.api-sports.io"

SİTE_DOGUM_TARİHİ = datetime(2026, 2, 20)
BULTEN_DOSYASI = "msi_bulten_bankasi.json"
VERİ_BANKASI_DOSYASI = "msi_futbol_bankasi.json"

st.set_page_config(page_title="UltraSkor Pro: AETHER API-F", page_icon="🎯", layout="wide")

# --- 2. GÖRSEL STİL (MSI DARK MODE) ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; font-size: 0.8rem; }
    .aether-box { border: 1px solid #8A2BE2; color: #E0B0FF; background: rgba(138, 43, 226, 0.1); }
    h1, h2, h3 { color: #58A6FF !important; }
    .live-badge { color: #f85149; font-weight: bold; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. API-FOOTBALL BAĞLANTI MOTORU ---
def api_get(endpoint, params={}):
    """API-Football v3 standartlarına uygun header bazlı istek motoru"""
    headers = {
        'x-apisports-key': API_KEY,
        'Accept': 'application/json'
    }
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            return {"errors": [f"HTTP Hatası: {response.status_code}"]}
    except Exception as e:
        return {"errors": [str(e)]}

# --- 🛰️ SİDEBAR & ANLIK APİ BAĞLANTI KONTROLÜ ---
st.sidebar.title("🛡️ MSI Operasyon Merkezi")
st.sidebar.markdown("### 📡 API Durum Testi")

# Kod her çalıştığında otomatik olarak anahtarı check eder
with st.sidebar.spinner("API Sağlık Kontrolü yapılıyor..."):
    status_check = api_get("status")
    
if status_check and not status_check.get("errors"):
    account_info = status_check.get("response", {}).get("account", {})
    st.sidebar.success("✅ API Bağlantısı Başarılı!")
    st.sidebar.caption(f"Kullanıcı: {account_info.get('firstname', 'Aktif Geliştirici')} {account_info.get('lastname', '')}")
    # Günlük istek limit takibi (API-Football'da çok önemlidir)
    requests_made = status_check.get("response", {}).get("requests", {}).get("current", 0)
    requests_limit = status_check.get("response", {}).get("requests", {}).get("limit", 100)
    st.sidebar.progress(min(1.0, requests_made / max(1, requests_limit)))
    st.sidebar.caption(f"Bugünkü İstek Tüketimi: {requests_made} / {requests_limit}")
else:
    st.sidebar.error("❌ API Bağlantı Hatası!")
    if status_check and status_check.get("errors"):
        st.sidebar.caption(f"Hata Detayı: {status_check['errors']}")

# --- 4. DATA HARVESTING (HASAT) SİSTEMLERİ ---
def bulten_hasat_et():
    """Gelecek 3 günün maçlarını çeker ve bültene mühürler"""
    today = datetime.now().strftime('%Y-%m-%d')
    # Örnek olarak bugünün fikstürünü çekiyoruz (İstersen date parametresini genişletebilirsin)
    res = api_get("fixtures", params={"date": today})
    
    if not res or res.get("errors") or "response" not in res:
        st.sidebar.error("Bülten çekilirken API hatası oluştu.")
        return []
        
    yeni_bulten = []
    for item in res["response"]:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        
        # API-Football'da xG doğrudan fikstür listesinde gelmediği için 
        # takımların genel güç parametrelerini simüle edecek yedek değerler atıyoruz
        min_mac = {
            'id': fixture.get('id'),
            'league_name': league.get('name'),
            'home_name': teams.get('home', {}).get('name'),
            'away_name': teams.get('away', {}).get('name'),
            'team_a_xg_prematch': 1.6,  # Varsayılan simülasyon değerleri
            'team_b_xg_prematch': 1.3,
            'date_unix': fixture.get('timestamp')
        }
        yeni_bulten.append(min_mac)
        
    if yeni_bulten:
        with open(BULTEN_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(yeni_bulten, f, ensure_ascii=False, indent=4)
    return yeni_bulten

def biten_maclari_arsivle():
    """Dünün tamamlanmış maçlarını derin analiz için yerel veri bankasına işler"""
    import datetime as dt
    yesterday = (datetime.now() - dt.timedelta(days=1)).strftime('%Y-%m-%d')
    res = api_get("fixtures", params={"date": yesterday, "status": "FT"})
    
    if not res or res.get("errors") or "response" not in res:
        return 0
        
    if os.path.exists(VERİ_BANKASI_DOSYASI):
        with open(VERİ_BANKASI_DOSYASI, "r", encoding="utf-8") as f:
            try: mevcut_arsiv = json.load(f)
            except: mevcut_arsiv = []
    else:
        mevcut_arsiv = []
        
    kayitli_idlar = {m.get('fixture', {}).get('id') for m in mevcut_arsiv if 'fixture' in m}
    yeni_sayac = 0
    
    for item in res["response"]:
        f_id = item.get("fixture", {}).get("id")
        if f_id not in kayitli_idlar:
            mevcut_arsiv.append(item)
            yeni_sayac += 1
            
    if yeni_sayac > 0:
        with open(VERİ_BANKASI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(mevcut_arsiv, f, ensure_ascii=False, indent=4)
            
    return yeni_sayac

# --- 5. ANALİZ MOTORU & SKOR TAHMİNİ ---
def analiz_et_v3(xg_h, xg_a):
    try:
        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            conf = min(99, int(m[s[0], s[1]] * 350))
            return f"{s[0]} - {s[1]}", conf

        r_ae = sk(xg_h, xg_a)
        r_w = sk(xg_h * 1.2, xg_a * 0.8) 
        r_nx = sk(xg_h * 0.8, xg_a * 1.1)

        return {
            "aether": r_ae[0], "ae_c": r_ae[1],
            "wickham": r_w[0], "w_c": r_w[1],
            "nexus": r_nx[0], "n_c": r_nx[1],
            "total_xg": xg_h + xg_a
        }
    except: return None

def winner(skor_metni):
    try:
        p = skor_metni.split(" - ")
        if int(p[0]) > int(p[1]): return "1"
        if int(p[1]) > int(p[0]): return "2"
        return "X"
    except: return "X"

simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

# --- MENÜ GEZİNTİSİ ---
mod = st.sidebar.radio("🚀 Menü", ["🤖 Tahmin Robotu", "🏠 Canlı Skorlar", "Global AI", "🏆 Onur Listesi", "📂 Veri Bankası"], key="main_menu")

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Veri İstihbaratı")

if st.sidebar.button("📡 BÜLTENİ HASAT ET (Gelecek)"):
    with st.spinner("🌍 API-Football Ambarı taranıyor..."):
        bulten_listesi = bulten_hasat_et()
        st.sidebar.success(f"✅ {len(bulten_listesi)} Maç Bültene İşlendi!")
        st.rerun()

if st.sidebar.button("💾 PAZARTESİ HASADI (Geçmiş)"):
    with st.spinner("📥 Dünün biten maçları mühürleniyor..."):
        sayi = biten_maclari_arsivle()
        st.sidebar.success(f"📦 {sayi} Yeni Maç Arşivlendi!")

# --- 6. SAYFA MODLARI TASARIMI ---

if mod == "🤖 Tahmin Robotu":
    st.title("🚀 Robotik Karma Kuponlar")
    
    if os.path.exists(BULTEN_DOSYASI):
        with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
            bulten_data = json.load(f)
        
        elit_havuz = []
        for m in bulten_data:
            res = analiz_et_v3(m['team_a_xg_prematch'], m['team_b_xg_prematch'])
            if res:
                m['res'] = res
                if res['ae_c'] >= 50 or res['w_c'] >= 50 or res['n_c'] >= 50:
                    if res['total_xg'] > 2.8: m['pick'] = "2.5 ÜST"; m['conf'] = res['w_c']
                    elif res['total_xg'] < 2.1: m['pick'] = "2.5 ALT"; m['conf'] = res['n_c']
                    elif winner(res['aether']) == "1": m['pick'] = "MS 1"; m['conf'] = res['ae_c']
                    elif winner(res['aether']) == "2": m['pick'] = "MS 2"; m['conf'] = res['ae_c']
                    else: m['pick'] = "KG VAR"; m['conf'] = (res['w_c'] + res['ae_c']) / 2
                    elit_havuz.append(m)

        elit_havuz = sorted(elit_havuz, key=lambda x: x['conf'], reverse=True)

        if len(elit_havuz) >= 4:
            # Örnek gösterim için sütun dinamikleri kuruldu
            k_cols = st.columns(min(4, len(elit_havuz)))
            renkler = ["#FFD700", "#C0C0C0", "#CD7F32", "#8A2BE2"]
            isimler = ["🏆 ELMAS KUPON", "🥇 ALTIN KUPON", "🥈 GÜMÜŞ KUPON", "🎖️ BRONZ KUPON"]

            for i in range(min(4, len(k_cols))):
                with k_cols[i]:
                    st.markdown(f"<h3 style='color:{renkler[i]}; text-align:center;'>{isimler[i]}</h3>", unsafe_allow_html=True)
                    # Havuz büyüklüğüne göre dinamik dağıtım
                    kupon_maclari = elit_havuz[i*1 : (i+1)*2]
                    
                    for m in kupon_maclari:
                        st.markdown(f"""
                            <div class="match-card" style="border-right: 4px solid {renkler[i]};">
                                <small style="color:#8B949E;">{m['league_name'][:15]}</small><br>
                                <b style="font-size:0.8rem;">{m['home_name'][:12]} - {m['away_name'][:12]}</b><br>
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span style="color:{renkler[i]}; font-weight:bold;">{m['pick']}</span>
                                    <span style="font-size:0.7rem; background:#30363d; padding:2px 5px; border-radius:4px;">%{int(m['conf'])}</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
        else:
            st.warning(f"⚠️ Robot analizi için bültende yeterli maç yok. Lütfen sol menüden bülteni hasat edin.")
    else:
        st.info("🔎 Ambar dosyası boş. Lütfen sol taraftan 'BÜLTENI HASAT ET' butonuna basın.")

elif mod == "🏠 Canlı Skorlar":
    st.title("⚡ Canlı Harekat Merkezi")
    # API-Football Canlı Maçlar Endpoint'i çağrılıyor
    live_data = api_get("fixtures", params={"live": "all"})
    
    if not live_data or 'response' not in live_data or len(live_data['response']) == 0:
        st.info("📡 Şu an aktif canlı maç akışı bulunmuyor.")
    else:
        for item in live_data['response']:
            fixture = item.get("fixture", {})
            league = item.get("league", {})
            teams = item.get("teams", {})
            goals = item.get("goals", {})
            
            st.markdown(f"""
                <div class="match-card" style="border-left: 5px solid #3fb950;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span style="font-size:0.8rem;">📍 {league.get('name')} ({league.get('country')})</span>
                        <span class="live-badge">● CANLI {fixture.get('status', {}).get('elapsed', 0)}'</span>
                    </div>
                    <div style="display:flex; justify-content:space-around; align-items:center; text-align:center;">
                        <div style="width:35%;"><b>{teams.get('home',{}).get('name')}</b></div>
                        <div style="width:30%; background:#0d1117; border-radius:10px; padding:5px;">
                            <h2 style="margin:0; color:#3fb950;">{goals.get('home',0)} - {goals.get('away',0)}</h2>
                        </div>
                        <div style="width:35%;"><b>{teams.get('away',{}).get('name')}</b></div>
                    </div>
                </div>""", unsafe_allow_html=True)

elif mod == "Global AI":
    st.title("🤖 Global AI Harekat Planı")
    if os.path.exists(BULTEN_DOSYASI):
        with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
            bulten_data = json.load(f)
        st.success(f"Sistemde toplam {len(bulten_data)} analiz edilebilir maç yüklü.")
        st.dataframe(pd.DataFrame(bulten_data), use_container_width=True)
    else:
        st.warning("Lütfen önce verileri hasat edin.")

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Yapay Zeka Onur Listesi")
    st.info("Haftalık robotik başarı oranları ve geçmiş tahmin istatistikleri bu sekmede simüle edilir.")

elif mod == "📂 Veri Bankası":
    st.title("🗄️ MSI Operasyon Veri Merkezi")
    tab1, tab2 = st.tabs(["📅 Güncel Bülten", "📚 Geçmiş Arşiv"])

    with tab1:
        if os.path.exists(BULTEN_DOSYASI):
            with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info("Bülten ambarı boş.")
            
    with tab2:
        if os.path.exists(VERİ_BANKASI_DOSYASI):
            with open(VERİ_BANKASI_DOSYASI, "r", encoding="utf-8") as f:
                data_arch = json.load(f)
            st.json(data_arch[:10]) # İlk 10 satırı göster
        else:
            st.info("Geçmiş arşiv verisi henüz mühürlenmedi.")
