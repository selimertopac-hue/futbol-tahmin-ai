import streamlit as st
import json
import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

# --- 1. AYARLAR & API ANAHTARLARI ---
FS_API_KEY = "3d8f931eb334529f5c171f08dbeed729fe2b0e7f49f717574101ff79225d4aa7"
FS_BASE_URL = "https://api.football-data-api.com"
SİTE_DOGUM_TARİHİ = datetime(2026, 2, 20)
ARSIV_DOSYASI = "ai_arsiv.json"
VERİ_BANKASI_DOSYASI = "msi_futbol_bankasi.json"

st.set_page_config(page_title="UltraSkor Pro: AETHER FS", page_icon="🎯", layout="wide")

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

# --- 3. FOOTYSTATS VERİ MERKEZİ ---
def fs_api_get(endpoint, params={}):
    params['key'] = FS_API_KEY
    url = f"{FS_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=15)
        return response.json()
    except Exception as e:
        st.error(f"📡 API Hatası: {e}")
        return None

def pazartesi_hasadi():
    """Biten maçların TÜM verilerini (xG, Korner, Kart vb.) MSI Bankasına mühürler."""
    # 1. Önce Yetkili Ligleri Al
    lig_res = fs_api_get("league-list")
    if not lig_res or 'data' not in lig_res:
        return 0

    ham_ligler = lig_res['data']
    sezon_idleri = []
    
    # Dokümana göre Sezon ID'lerini ayıkla
    if isinstance(ham_ligler, list):
        for lig in ham_ligler:
            if 'season' in lig and len(lig['season']) > 0:
                # En güncel sezonun ID'sini alıyoruz
                sezon_idleri.append(str(lig['season'][-1]['id']))

    # 2. Mevcut Arşivi Dosyadan Oku (Belleği korumak için sadece ID'leri tut)
    if os.path.exists(VERİ_BANKASI_DOSYASI):
        with open(VERİ_BANKASI_DOSYASI, "r", encoding="utf-8") as f:
            try: mevcut_arsiv = json.load(f)
            except: mevcut_arsiv = []
    else:
        mevcut_arsiv = []

    kayitli_idlar = {m.get('id') for m in mevcut_arsiv}
    yeni_eklenen_sayisi = 0
    
    p_bar = st.sidebar.progress(0)
    st.sidebar.info(f"📦 {len(sezon_idleri)} lig derin analize alındı...")

    # 3. Her Sezon İçin Bitmiş Maçları Derinlemesine Çek
    for index, s_id in enumerate(sezon_idleri):
        # 'status=complete' ile bitmiş maçların tüm Premium verilerini istiyoruz
        params = {'key': FS_API_KEY, 'league_id': s_id, 'status': 'complete'}
        url = f"{FS_BASE_URL}/league-matches"
        
        try:
            res = requests.get(url, params=params, timeout=10).json()
            if res and 'data' in res and isinstance(res['data'], list):
                for m in res['data']:
                    # Tekilleştirme Kontrolü
                    if m.get('id') not in kayitli_idlar:
                        # 💡 BURADA HİÇBİR VERİYİ SİLMİYORUZ! 
                        # Dokümandaki tüm 200 değişken (xG, Korner vb.) JSON'a gidiyor.
                        mevcut_arsiv.append(m)
                        kayitli_idlar.add(m.get('id'))
                        yeni_eklenen_sayisi += 1
        except:
            continue
            
        p_bar.progress((index + 1) / len(sezon_idleri))

    # 4. MSI Laptopuna Kalıcı Mühür
    if yeni_eklenen_sayisi > 0:
        with open(VERİ_BANKASI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(mevcut_arsiv, f, ensure_ascii=False, indent=4)
            
    return yeni_eklenen_sayisi
BULTEN_DOSYASI = "msi_bulten_bankasi.json"

def tum_dunyayi_hasat_et():
    """Bülten maçlarını (incomplete) doğrudan JSON'a mühürler."""
    url = f"{FS_BASE_URL}/league-list"
    params = {'key': FS_API_KEY}
    
    try:
        res = requests.get(url, params=params, timeout=15).json()
        if not res.get('success'):
            st.sidebar.error("❌ API Erişimi Başarısız!")
            return []
            
        ham_veri = res['data']
        guncel_sezon_idleri = []

        # En güncel sezonları ayıkla
        for lig in ham_veri:
            if 'season' in lig and len(lig['season']) > 0:
                en_son_sezon = lig['season'][-1] 
                guncel_sezon_idleri.append({'id': str(en_son_sezon['id'])})

        st.sidebar.info(f"📡 {len(guncel_sezon_idleri)} lig taranıyor...")
        
        yeni_bulten = []
        p_bar = st.sidebar.progress(0)
        
        for index, sezon in enumerate(guncel_sezon_idleri):
            mac_url = f"{FS_BASE_URL}/league-matches"
            # 'status': 'incomplete' ile sadece gelecek maçları alıyoruz
            mac_params = {'key': FS_API_KEY, 'league_id': sezon['id'], 'status': 'incomplete'}
            
            try:
                m_res = requests.get(mac_url, params=mac_params, timeout=10).json()
                if m_res and 'data' in m_res:
                    for m in m_res['data']:
                        # Belleği korumak için sadece gerekli verileri JSON'a mühürleyelim
                        min_mac = {
                            'home_name': m.get('home_name'),
                            'away_name': m.get('away_name'),
                            'league_name': m.get('league_name'),
                            'team_a_xg_prematch': m.get('team_a_xg_prematch', 1.5),
                            'team_b_xg_prematch': m.get('team_b_xg_prematch', 1.2),
                            'date_unix': m.get('date_unix'),
                            'id': m.get('id')
                        }
                        yeni_bulten.append(min_mac)
            except:
                continue
            p_bar.progress((index + 1) / len(guncel_sezon_idleri))

        # 💾 DOĞRUDAN JSON'A KAYDET (Ambar Kapaklarını Kapat)
        if yeni_bulten:
            with open(BULTEN_DOSYASI, "w", encoding="utf-8") as f:
                json.dump(yeni_bulten, f, ensure_ascii=False, indent=4)
            st.sidebar.success(f"✅ {len(yeni_bulten)} Maç Bültene Mühürlendi!")
        
        return yeni_bulten

    except Exception as e:
        st.sidebar.error(f"📡 Bağlantı Hatası: {e}")
        return []
# --- 4. ANALİZ MOTORU & YARDIMCILAR ---
def analiz_et_v3(ev, dep, xg_h, xg_a):
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

# --- 5. ZAMAN VE HAFTA HESABI ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

# --- 🚀 ANA SIDEBAR (MENÜ GÜNCELLEME) ---
st.sidebar.title("🛡️ MSI Operasyon Merkezi")
# Buraya "📂 Veri Bankası" seçeneğini ekledik:
mod = st.sidebar.radio("🚀 Menü", ["🤖 Tahmin Robotu", "🏠 Canlı Skorlar", "Global AI", "🏆 Onur Listesi", "📂 Veri Bankası"], key="main_menu")

if 'fs_data' not in st.session_state:
    st.session_state.fs_data = []

# --- VERİ İSTİHBARAT BUTONLARI ---
st.sidebar.markdown("---")
st.sidebar.subheader("📦 Veri İstihbaratı")

if st.sidebar.button("📡 BÜLTENİ HASAT ET (Gelecek)"):
    with st.spinner("🌍 FootyStats Ambarı Boşaltılıyor..."):
        st.session_state.fs_data = tum_dunyayi_hasat_et()
        st.sidebar.success(f"✅ {len(st.session_state.fs_data)} Maç Mühürlendi!")

if st.sidebar.button("💾 PAZARTESİ HASADI (Geçmiş)"):
    with st.spinner("📥 Biten maçlar MSI Bankasına aktarılıyor..."):
        sayi = pazartesi_hasadi()
        st.sidebar.success(f"📦 {sayi} Yeni Maç Arşivlendi!")

# --- 6. SAYFA MODLARI ---

if mod == "🤖 Tahmin Robotu":
    st.title("🌍 Küresel Tahmin Radarı (39+ Lig)")
    if not st.session_state.fs_data:
        st.info("Lütfen sol menüdeki 'BÜLTENİ HASAT ET' butonuna basarak Premium verileri çekin.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        kuponlar = {"banko": [], "ideal": [], "ust": [], "alt": []}
        
        for m in st.session_state.fs_data:
            # 💡 KRİTİK TAMİR: API'den gelen anahtar isimlerini (home_name, away_name) kullanıyoruz
            ev_adi = m.get('home_name', 'Bilinmeyen Ev')
            dep_adi = m.get('away_name', 'Bilinmeyen Deplasman')
            # xG verileri için de API anahtarlarını kontrol edelim
            xg_h = m.get('team_a_xg_prematch', 1.5)
            xg_a = m.get('team_b_xg_prematch', 1.2)
            
            res = analiz_et_v3(ev_adi, dep_adi, xg_h, xg_a)
            
            if res:
                m['res'] = res
                # Analiz motoruna gönderdiğimiz isimleri m içine de mühürleyelim ki kartlarda hata çıkmasın
                m['home_display'] = ev_adi
                m['away_display'] = dep_adi
                
                if winner(res['aether']) == "1": kuponlar["banko"].append(m)
                elif winner(res['aether']) == "2": kuponlar["ideal"].append(m)
                
                if res['total_xg'] > 2.8: kuponlar["ust"].append(m)
                elif res['total_xg'] < 2.1: kuponlar["alt"].append(m)

        col_cfg = [("⭐ BANKO", c1, "banko", "#58A6FF"), ("💎 İDEAL", c2, "ideal", "#3fb950"), 
                   ("🔥 ÜST", c3, "ust", "#d73a49"), ("🛡️ ALT", c4, "alt", "#0366d6")]

        for title, col, k_key, color in col_cfg:
            with col:
                st.markdown(f"<h3 style='color:{color}; text-align:center;'>{title}</h3>", unsafe_allow_html=True)
                for m in kuponlar[k_key][:10]:
                    t_val = m['res']['aether'] if k_key in ['banko', 'ideal'] else ('2.5 ÜST' if k_key=='ust' else '2.5 ALT')
                    st.markdown(f"""<div class="match-card" style="border-top: 3px solid {color};">
                        <div style="font-size:0.7rem; color:#8B949E;">{m.get('league_name', 'Lig')}</div>
                        <div style="font-size:0.85rem; font-weight:bold;">{m['home_display'][:12]} - {m['away_display'][:12]}</div>
                        <div style="color:{color}; font-weight:bold;">{t_val}</div></div>""", unsafe_allow_html=True)

elif mod == "🏠 Canlı Skorlar":
    st.title("⚡ Canlı Harekat Merkezi")
    live_data = fs_api_get("live-matches")
    if not live_data or 'data' not in live_data or len(live_data['data']) == 0:
        st.info("📡 Şu an dünyada aktif robotik veri akışı yok.")
    else:
        for m in live_data['data']:
            st.markdown(f"""
                <div class="match-card" style="border-left: 5px solid #3fb950;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span style="font-size:0.8rem;">📍 {m['league_name']}</span>
                        <span class="live-badge">● CANLI {m.get('currentTime', 0)}'</span>
                    </div>
                    <div style="display:flex; justify-content:space-around; align-items:center; text-align:center;">
                        <div style="width:35%;"><b>{m['home_name']}</b><br><small>🎯 Şut: {m.get('home_shotsOnTarget',0)}</small></div>
                        <div style="width:30%; background:#0d1117; border-radius:10px; padding:5px;">
                            <h2 style="margin:0; color:#3fb950;">{m.get('homeGoalCount',0)} - {m.get('awayGoalCount',0)}</h2>
                        </div>
                        <div style="width:35%;"><b>{m['away_name']}</b><br><small>🎯 Şut: {m.get('away_shotsOnTarget',0)}</small></div>
                    </div>
                </div>""", unsafe_allow_html=True)

elif mod == "Global AI":
    st.title("🤖 Global AI Harekat Planı")
    
    if os.path.exists(BULTEN_DOSYASI):
        with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
            bulten_data = json.load(f)
            
        # --- 1. ALGORİTMİK SÜZGEÇ (GÜVEN EŞİĞİ %75) ---
        kuponlar = {"Banko (MS1)": [], "İdeal (MS2)": [], "2.5 Üst": [], "2.5 Alt": []}
        deneme_bolgesi = []
        
        for m in bulten_data:
            # Robotların analizi
            res = analiz_et_v3(m['home_name'], m['away_name'], m['team_a_xg_prematch'], m['team_b_xg_prematch'])
            if res:
                m['res'] = res
                eklendi = False
                
                # Güven skoru kontrolü (Her robotun kendi uzmanlık alanı)
                # Aether (Banko/İdeal), Wickham (Üst/Kaos), Nexus (Alt/Defans)
                
                # MS1 - Banko (Aether Güveni > 75)
                if winner(res['aether']) == "1" and res['ae_c'] >= 75 and len(kuponlar["Banko (MS1)"]) < 10:
                    kuponlar["Banko (MS1)"].append(m)
                    eklendi = True
                
                # MS2 - İdeal (Aether Güveni > 75)
                elif winner(res['aether']) == "2" and res['ae_c'] >= 75 and len(kuponlar["İdeal (MS2)"]) < 10:
                    kuponlar["İdeal (MS2)"].append(m)
                    eklendi = True
                
                # 2.5 ÜST (Wickham Güveni > 75)
                elif res['total_xg'] > 2.8 and res['w_c'] >= 75 and len(kuponlar["2.5 Üst"]) < 10:
                    kuponlar["2.5 Üst"].append(m)
                    eklendi = True
                
                # 2.5 ALT (Nexus Güveni > 75)
                elif res['total_xg'] < 2.2 and res['n_c'] >= 75 and len(kuponlar["2.5 Alt"]) < 10:
                    kuponlar["2.5 Alt"].append(m)
                    eklendi = True
                
                # DENEME BÖLGESİ (Kuponlara sığmayan ama %75+ güvenli maçlar)
                elif (res['ae_c'] >= 75 or res['w_c'] >= 75 or res['n_c'] >= 75) and len(deneme_bolgesi) < 20:
                    deneme_bolgesi.append(m)

        # --- 2. GÖRSELLEŞTİRME (KUPONLAR) ---
        cols = st.columns(4)
        renkler = ["#58A6FF", "#3fb950", "#d73a49", "#0366d6"]
        
        for i, (k_ad, k_maclar) in enumerate(kuponlar.items()):
            with cols[i]:
                st.markdown(f"<h3 style='color:{renkler[i]}; text-align:center;'>{k_ad}</h3>", unsafe_allow_html=True)
                for m in k_maclar:
                    tahmin_ozet = m['res']['aether'] if "MS" in k_ad else ("2.5 ÜST" if "Üst" in k_ad else "2.5 ALT")
                    st.markdown(f"""
                        <div class="match-card" style="border-left: 3px solid {renkler[i]}; padding:10px; margin-bottom:5px;">
                            <small>{m['league_name'][:15]}</small><br>
                            <b>{m['home_name'][:12]} - {m['away_name'][:12]}</b><br>
                            <span style="color:{renkler[i]};">🎯 {tahmin_ozet}</span>
                        </div>
                    """, unsafe_allow_html=True)
        
        # --- 3. DENEME BÖLGESİ ---
        st.divider()
        st.subheader("🔬 Deneme Bölgesi (Yüksek Güvenli Ek Maçlar)")
        d_cols = st.columns(2)
        for idx, m in enumerate(deneme_bolgesi):
            with d_cols[idx % 2]:
                st.markdown(f"""
                    <div class="match-card" style="background: rgba(48, 54, 61, 0.3); border: 1px dashed #8B949E;">
                        <b>{m['home_name']} - {m['away_name']}</b> | {m['league_name']} <br>
                        <small>Aether: %{m['res']['ae_c']} | Wickham: %{m['res']['w_c']} | Nexus: %{m['res']['n_c']}</small>
                    </div>
                """, unsafe_allow_html=True)
                
    else:
        st.warning("⚠️ Önce bülteni hasat etmelisiniz.")

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Yapay Zeka Onur Listesi")
    # Arşiv verilerini birleştirme
    otonom = {int(k): v for k, v in st.session_state.get('otonom_kayitlar', {}).items()}
    manuel = {1: {"W": {"p": 75, "t": "Başlangıç"}, "A": {"p": 88, "t": "Stabil"}},
              3: {"W": {"p": 94, "t": "Domination"}, "A": {"p": 85, "t": "Elit"}}}
    final_arsiv = {**manuel, **otonom}
    
    sec_h = st.select_slider("🔎 İncele", options=list(range(1, site_h_aktif + 1)), value=max(1, site_h_aktif - 1))
    h_data = final_arsiv.get(sec_h, {})
    
    cols = st.columns(4)
    r_cfg = [("W", "WICKHAM", "#d73a49", "🧪"), ("A", "AETHER", "#58A6FF", "✨"), ("N", "NEXUS", "#3fb950", "🛡️"), ("S", "STANDART", "#8b949e", "🤖")]
    for i, (rid, name, color, emoji) in enumerate(r_cfg):
        d = h_data.get(rid, {"p": 0, "t": "⏳"})
        with cols[i]:
            st.markdown(f'<div style="background:rgba(22,27,34,0.6); padding:10px; border-radius:10px; border-top:4px solid {color}; text-align:center;">'
                        f'<h3 style="margin:0; color:{color}; font-size:0.9rem;">{emoji} {name}</h3>'
                        f'<h2 style="margin:5px 0; color:white;">%{d["p"]}</h2>'
                        f'<div style="font-size:0.7rem; color:{color}; font-weight:bold;">{d["t"]}</div></div>', unsafe_allow_html=True)
            st.progress(d['p'] / 100)

    st.divider()
    arsiv_tablo = []
    for h in range(1, site_h_aktif + 1):
        ozet = final_arsiv.get(h, {})
        arsiv_tablo.append({"Hafta": f"{h}. Hafta", "🧪 WICK": f"%{ozet.get('W',{}).get('p','85')}", "✨ AETH": f"%{ozet.get('A',{}).get('p','88')}", "Durum": "✅ Tamam" if h < site_h_aktif else "⏳ Sürüyor"})
    st.table(pd.DataFrame(arsiv_tablo).set_index("Hafta"))
elif mod == "📂 Veri Bankası":
    st.title("🗄️ MSI Operasyon Veri Merkezi")
    
    tab1, tab2 = st.tabs(["📅 Güncel Bülten", "📚 Geçmiş Arşiv"])

    with tab1:
        st.subheader("Taze Hasat Edilen Maçlar")
        if os.path.exists(BULTEN_DOSYASI):
            with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
                bulten_verisi = json.load(f)
            st.metric("📦 Bülten Maç Sayısı", len(bulten_verisi))
            st.dataframe(pd.DataFrame(bulten_verisi), use_container_width=True)
        else:
            st.warning("Henüz bülten hasat edilmedi.")

    with tab2:
        st.subheader("Geçmiş Veri Bankası (Pazartesi Hasadı)")
        if os.path.exists(VERİ_BANKASI_DOSYASI):
            with open(VERİ_BANKASI_DOSYASI, "r", encoding="utf-8") as f:
                arsiv_verisi = json.load(f)
            st.metric("📦 Arşivdeki Toplam Maç", len(arsiv_verisi))
            st.dataframe(pd.DataFrame(arsiv_verisi).tail(100), use_container_width=True)
            
            st.download_button("📥 Arşivi İndir", 
                               data=json.dumps(arsiv_verisi, indent=4), 
                               file_name="msi_futbol_bankasi.json")
