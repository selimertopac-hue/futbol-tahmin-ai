import streamlit as st
import json
import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

# --- 1. AYARLAR & API ANAHTARLARI ---
# FootyStats API Anahtarın (Mühürlendi)
FS_API_KEY = "3d8f931eb334529f5c171f08dbeed729fe2b0e7f49f717574101ff79225d4aa7"
FS_BASE_URL = "https://api.footystats.org"
SİTE_DOGUM_TARİHİ = datetime(2026, 2, 20)
ARSIV_DOSYASI = "ai_arsiv.json"

st.set_page_config(page_title="UltraSkor Pro: AETHER FS", page_icon="🎯", layout="wide")

# --- 2. GÖRSEL STİL (MSI DARK MODE) ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 5px; text-align: center; font-size: 0.8rem; }
    .aether-box { border-color: #8A2BE2; color: #E0B0FF; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FOOTYSTATS VERİ MERKEZİ ---
def fs_api_get(endpoint, params={}):
    params['key'] = FS_API_KEY
    url = f"{FS_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=15)
        return response.json()
    except:
        return None

@st.cache_data(ttl=3600)
def tum_dunyayi_tara():
    """39+ ligi FootyStats üzerinden otonom tarar, isim belirtmeye gerek kalmaz."""
    # Sadece 'incomplete' (oynanmamış) maçları çekerek geleceği tarıyoruz
    data = fs_api_get("matches", {"status": "incomplete"})
    
    tum_fikstur = []
    if data and 'data' in data:
        for m in data['data']:
            tum_fikstur.append({
                'home': m['home_name'],
                'away': m['away_name'],
                'lig': m['league_name'],
                'id': m['id'],
                'xg_h': m.get('team_a_xg_prematch', 1.5),
                'xg_a': m.get('team_b_xg_prematch', 1.2),
                'puan': int(m.get('odds_ft_home_win_prob', 50)) # Olasılık bazlı puan
            })
    return tum_fikstur

# --- 4. ANALİZ MOTORU ---
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
            "std": r_ae[0], "total_xg": xg_h + xg_a
        }
    except: return None

def winner(skor_metni):
    try:
        p = skor_metni.split(" - ")
        if int(p[0]) > int(p[1]): return "1"
        if int(p[1]) > int(p[0]): return "2"
        return "X"
    except: return "X"

# --- 5. MENÜ VE GÖVDE ---
st.sidebar.title("🛡️ MSI Operasyon Merkezi")
mod = st.sidebar.radio("🚀 Menü", ["🤖 Tahmin Robotu", "Global AI", "🏆 Onur Listesi"])

simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

if mod == "🤖 Tahmin Robotu":
    st.title("🌍 Küresel Tahmin Radarı (39+ Lig)")
    
    if st.button("🚀 TÜM DÜNYAYI FOOTYSTATS ÜZERİNDEN HASAT ET"):
        with st.spinner("💎 39+ Ligin derin verileri MSI'a akıyor..."):
            fikstur = tum_dunyayi_tara()
            st.session_state.fs_fikstur = fikstur
            st.success(f"✅ {len(fikstur)} Maç Otonom Olarak Başarıyla Analiz Edildi!")

    if 'fs_fikstur' in st.session_state:
        c1, c2, c3, c4 = st.columns(4)
        kuponlar = {"banko": [], "ideal": [], "ust": [], "alt": []}

        for m in st.session_state.fs_fikstur:
            res = analiz_et_v3(m['home'], m['away'], m['xg_h'], m['xg_a'])
            if res:
                m['res'] = res
                if winner(res['aether']) == "1": kuponlar["banko"].append(m)
                elif winner(res['aether']) == "2": kuponlar["ideal"].append(m)
                if res['total_xg'] > 2.8: kuponlar["ust"].append(m)
                elif res['total_xg'] < 2.1: kuponlar["alt"].append(m)

        col_config = [
            ("⭐ BANKO", c1, "banko", "#58A6FF"),
            ("💎 İDEAL", c2, "ideal", "#3fb950"),
            ("🔥 ÜST", c3, "ust", "#d73a49"),
            ("🛡️ ALT", c4, "alt", "#0366d6")
        ]

        for title, col, k_key, color in col_config:
            with col:
                st.markdown(f"<h3 style='color:{color}; text-align:center;'>{title}</h3>", unsafe_allow_html=True)
                for m in kuponlar[k_key][:10]:
                    st.markdown(f"""
                        <div class="match-card" style="border-top: 3px solid {color};">
                            <div style="font-size:0.7rem; color:#8B949E;">{m['lig'][:20]}</div>
                            <div style="font-size:0.85rem; font-weight:bold;">{m['home'][:12]} - {m['away'][:12]}</div>
                            <div style="color:{color}; font-weight:bold;">{m['res']['aether'] if k_key not in ['ust','alt'] else ('2.5 ÜST' if k_key=='ust' else '2.5 ALT')}</div>
                        </div>
                    """, unsafe_allow_html=True)
# --- FONKSİYON BURADA BİTTİ, ŞİMDİ ANA KODA GEÇİYORUZ ---
simdi = datetime.now()

# --- 4. ZAMAN & HAFTA ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

# --- 🚀 OTONOM ARŞİVLEME MAKİNESİ (BURAYA GELDİ) ---
def otonom_arsiv_guncelle():
    if 'otonom_kayitlar' not in st.session_state:
        st.session_state.otonom_kayitlar = {}

    # Bitmiş haftaları tara (aktif haftadan bir önceki haftaya kadar)
    for h_no in range(1, site_h_aktif):
        if h_no not in st.session_state.otonom_kayitlar:
            # Not: Mühür anahtarı isminin Global AI'daki isimle eşleştiğinden emin ol
            filtre_anahtar = "AETHER AI Master" 
            muhur_anahtari = f"muhur_{h_no}_{filtre_anahtar.replace(' ', '_')}"
            
            if muhur_anahtari in st.session_state:
                m_kupon = st.session_state[muhur_anahtari]
                haftalik_ozet = {}
                
                for r_id, r_ad in [("W", "WICKHAM"), ("A", "AETHER"), ("N", "NEXUS"), ("S", "STANDART"), ("SP", "SPEKTRUM")]:
                    b_skor = check_hit(m_kupon.get("banko", []), "banko")
                    i_skor = check_hit(m_kupon.get("ideal", []), "ideal")
                    u_skor = check_hit(m_kupon.get("ust", []), "ust")
                    a_skor = check_hit(m_kupon.get("alt", []), "alt")
                    
                    basari_yuzdesi = int(((b_skor + i_skor + u_skor + a_skor) / 20) * 100)
                    
                    haftalik_ozet[r_id] = {
                        "b": f"✅ {b_skor}/5" if b_skor < 5 else "🏆 5/5",
                        "i": f"✅ {i_skor}/5" if i_skor < 5 else "💎 5/5",
                        "u": f"✅ {u_skor}/5" if u_skor < 5 else "🔥 5/5",
                        "a": f"✅ {a_skor}/5" if a_skor < 5 else "🛡️ 5/5",
                        "p": basari_yuzdesi,
                        "t": "Otonom Kayıt ✅"
                    }
                st.session_state.otonom_kayitlar[h_no] = haftalik_ozet

# Fonksiyonu burada çalıştırıyoruz
otonom_arsiv_guncelle()

# --- 🚀 YENİ NESİL ANA MENÜ VE OTONOM HASAT ---
st.sidebar.title("🛡️ MSI Operasyon Merkezi")
mod = st.sidebar.radio("🚀 Menü", ["🤖 Tahmin Robotu", "Global AI", "🏆 Onur Listesi"])

# Eski 'all_d' döngüsü yerine bu güvenli yapıyı kullanıyoruz:
if 'fs_data' not in st.session_state:
    st.session_state.fs_data = []

# Buton Sidebar'da (Menü altında) dursun:
if st.sidebar.button("🚀 39 LİGİ TARAMAYA BAŞLA"):
    with st.spinner("🌍 FootyStats üzerinden dev veri çekiliyor..."):
        # Yukarıda tanımladığımız o yeni fonksiyonu çağırıyoruz
        istihbarat_havuzu = tum_dunyayi_hasat_et() 
        st.session_state.fs_data = istihbarat_havuzu
        st.sidebar.success(f"✅ {len(istihbarat_havuzu)} Maç Ambarlandı!")



if mod == "🏠 Canlı Skorlar":
    st.title("⚡ Canlı Maç Merkezi")
    st.markdown("Şu an dünyada oynanan aktif maçlar ve anlık skorlar.")
    
    # API'den tüm canlı maçları çekiyoruz
    live_data = veri_al("matches")
    matches = live_data.get('matches', [])
    
    if not matches:
        st.info("Şu an sistemde aktif canlı maç bulunmuyor. Bülten saatlerini bekleyin.")
    else:
        # Canlı maçları liglerine göre gruplayabilir veya listeleyebiliriz
        for m in matches:
            # Maçın durumuna göre (Dakika veya Devre Bilgisi)
            status = m.get('status', '')
            minute = m.get('minute', 'devam')
            
            # Skor bilgisi
            h_s = m['score']['fullTime']['home']
            a_s = m['score']['fullTime']['away']
            
            # Görsel Maç Kartı
            st.markdown(f"""
                <div class="match-card" style="border-left: 5px solid #3fb950;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #8B949E; margin-bottom: 5px;">
                        <span>📍 {m['competition']['name']}</span>
                        <span style="color: #3fb950; font-weight: bold;">● LIVE {minute}'</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="text-align: right; width: 40%;"><b>{m['homeTeam']['name']}</b></div>
                        <div style="width: 20%; text-align: center; background: #30363d; border-radius: 5px; padding: 5px;">
                            <h3 style="margin: 0; color: #3fb950;">{h_s} - {a_s}</h3>
                        </div>
                        <div style="text-align: left; width: 40%;"><b>{m['awayTeam']['name']}</b></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)



elif mod == "🏠 Canlı Skorlar":
    st.title("⚡ Canlı Harekat Merkezi")
    st.markdown("FootyStats Live API üzerinden sahadaki robotik analizler.")

    # 1. CANLI VERİYİ ÇEK
    live_data = fs_api_get("live-matches") # FootyStats Live Endpoint
    
    if not live_data or 'data' not in live_data or len(live_data['data']) == 0:
        st.info("📡 Şu an dünyada aktif robotik veri akışı yok. Maç saatlerini bekleyin.")
    else:
        live_matches = live_data['data']
        st.success(f"🎮 Şu an {len(live_matches)} maç robotlar tarafından canlı izleniyor!")

        for m in live_matches:
            # Kritik Canlı Metrikler
            dk = m.get('currentTime', 0)
            h_score = m.get('homeGoalCount', 0)
            a_score = m.get('awayGoalCount', 0)
            
            # Robotların en sevdiği 'Canlı Baskı' verileri
            h_att = m.get('home_dangerous_attacks', 0)
            a_att = m.get('away_dangerous_attacks', 0)
            h_shots = m.get('home_shotsOnTarget', 0)
            a_shots = m.get('away_shotsOnTarget', 0)

            # --- 🧠 CANLI ROBOT ANALİZİ ---
            # Wickham: Maçın tansiyonuna bakar
            tansiyon = "Normal"
            if h_att > 50 or a_att > 50: tansiyon = "🔥 YÜKSEK BASKI"
            
            # Aether: Canlı xG ve dakikaya göre 'Sıradaki Gol' tahmini yapar
            siradaki_gol = "Bekleniyor..."
            if h_shots > (a_shots + 3): siradaki_gol = f"✨ AETHER: {m['home_name']} Baskısı Artıyor!"
            elif a_shots > (h_shots + 3): siradaki_gol = f"✨ AETHER: {m['away_name']} Gol Geliyor!"

            # --- 🎨 GÖRSEL CANLI KART ---
            st.markdown(f"""
                <div class="match-card" style="border-left: 5px solid #3fb950; position: relative;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #8B949E; margin-bottom: 5px;">
                        <span>📍 {m['league_name']}</span>
                        <span style="color: #f85149; font-weight: bold; animation: blink 1s infinite;">● CANLI {dk}'</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="text-align: right; width: 35%;">
                            <b style="font-size: 1.1rem;">{m['home_name']}</b><br>
                            <small>🎯 Şut: {h_shots} | ⚡ Atak: {h_att}</small>
                        </div>
                        
                        <div style="width: 30%; text-align: center; background: #0d1117; border-radius: 10px; padding: 10px; border: 1px solid #30363d;">
                            <h2 style="margin: 0; color: #3fb950;">{h_score} - {a_score}</h2>
                            <div style="font-size: 0.6rem; color: #8B949E;">{tansiyon}</div>
                        </div>
                        
                        <div style="text-align: left; width: 35%;">
                            <b style="font-size: 1.1rem;">{m['away_name']}</b><br>
                            <small>🎯 Şut: {a_shots} | ⚡ Atak: {a_att}</small>
                        </div>
                    </div>

                    <div style="margin-top: 15px; padding: 8px; background: rgba(138, 43, 226, 0.1); border-radius: 5px; border: 1px dashed #8A2BE2; text-align: center;">
                        <span style="color: #E0B0FF; font-size: 0.85rem; font-weight: bold;">{siradaki_gol}</span>
                    </div>
                </div>
                
                <style>
                @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} 100% {{ opacity: 1; }} }}
                </style>
            """, unsafe_allow_html=True)
elif mod == "🤖 Tahmin Robotu":
    st.title("🌍 Küresel Tahmin Radarı & Avrupa Havuzu")
    
    # 1. TAM TEMİZLİK BUTONU
    if st.sidebar.button("🧨 SİSTEMİ SIFIRLA (TEMİZ KURULUM)"):
        st.cache_data.clear()
        st.session_state.clear()
        if os.path.exists("ai_arsiv.json"):
            os.remove("ai_arsiv.json")
        st.rerun()

    c_h, c_r = st.columns(2)
    with c_h:
        s_sec = st.selectbox("📅 Analiz Haftası", list(range(1, 11)), index=site_h_aktif-1, key="tr_hafta")
    with c_r:
        robot_secim = st.selectbox("🤖 Robot Seçimi", ["AETHER", "WICKHAM", "NEXUS", "SPEKTRUM"], key="tr_robot")

    r_map = {"AETHER": "ae_c", "WICKHAM": "w_c", "NEXUS": "n_c", "SPEKTRUM": "sp_c"}
    t_map = {"AETHER": "aether", "WICKHAM": "wickham", "NEXUS": "nexus", "SPEKTRUM": "spec"}
    aktif_r_puan = r_map[robot_secim]
    aktif_r_tahmin = t_map[robot_secim]

    if st.button("🚀 TÜM AVRUPA LİGLERİNİ YENİDEN TARA", use_container_width=True):
        with st.spinner("🌍 Veriler sıfırdan çekiliyor..."):
            fikstur, hafiza = tum_ligleri_tara()
            st.session_state.tr_fikstur = fikstur
            st.session_state.tr_hafiza = hafiza
            st.rerun()

    if 'tr_fikstur' in st.session_state:
        with st.spinner("🤖 Analizler dürüstlük filtresinden geçiyor..."):
            ham_liste = []
            
            for f in st.session_state.tr_fikstur:
                ev_adi = f.get('home')
                dep_adi = f.get('away')
                lig_adi = f.get('lig', 'Avrupa')

                if not ev_adi or not dep_adi: continue

                # Sahte veri sinyallerini engelle
                sahte_veri_sinyali = ["doncaster", "stevenage", "wimbledon", "rotherham", "reading", "port vale"]
                if "Türkiye" in str(lig_adi):
                    if any(c in ev_adi.lower() or c in dep_adi.lower() for c in sahte_veri_sinyali):
                        continue

                # ANALİZ ET
                res = analiz_et(ev_adi, dep_adi, st.session_state.tr_hafiza, s_sec)
                
                if res and res.get('note') == "✅ Analiz Tamamlandı":
                    if res.get('total_xg', 0) > 0.1:
                        ham_liste.append({
                            'ev': ev_adi, 
                            'dep': dep_adi, 
                            'lig': lig_adi, 
                            'res': res
                        })
            
            # --- TAHMİN ROBOTU: KUPON OLUŞTURMA (DÖNGÜ DIŞINDA) ---
            if ham_liste:
                st.success(f"✅ {len(ham_liste)} gerçek maç başarıyla analiz edildi.")
                
                # Seçilen robotun %70 barajını uygula
                kaliteli_ham_liste = [m for m in ham_liste if m['res'].get(aktif_r_puan, 0) >= 70]
                
                if not kaliteli_ham_liste:
                    st.warning(f"⚠️ {robot_secim} robotu için %70 güven barajını geçen maç bulunamadı.")
                else:
                    import streamlit.components.v1 as components
                    c1, c2, c3, c4 = st.columns(4)
                    
                    # Kupon konfigürasyonunu tanımlıyoruz
                    kupon_config = [
                        ("⭐ BANKO", c1, aktif_r_puan, aktif_r_tahmin, "#58A6FF"),
                        ("💎 İDEAL", c2, aktif_r_puan, aktif_r_tahmin, "#3fb950"),
                        ("🔥 ÜST", c3, "total_xg", "spec", "#d73a49"),
                        ("🛡️ ALT", c4, "total_xg", "nexus", "#0366d6")
                    ]

                    for title, col, sort_key, t_key, color in kupon_config:
                        with col:
                            # Sıralama: Alt için en düşük, diğerleri için en yüksek
                            top_matches = sorted(kaliteli_ham_liste, key=lambda x: x['res'].get(sort_key, 0), 
                                                 reverse=True if title != "🛡️ ALT" else False)
                            
                            gorulen_maclar = set()
                            final_matches = []
                            for m in top_matches:
                                mac_id = f"{m['ev']}-{m['dep']}"
                                if mac_id not in gorulen_maclar:
                                    final_matches.append(m)
                                    gorulen_maclar.add(mac_id)
                                if len(final_matches) == 10: break

                            # --- HTML GÖRSEL PAKETİ ---
                            html_output = f"""
                            <div style="background: #0d1117; color: #f0f6fc; font-family: sans-serif; padding: 10px; border-radius: 10px; border: 1px solid #30363d; border-top: 4px solid {color};">
                                <div style="color:{color}; font-weight:bold; margin-bottom:10px; text-align:center; font-size:16px; border-bottom: 1px solid #30363d; padding-bottom:8px;">{title}</div>
                            """
                            
                            for m in final_matches:
                                t_metni = m['res'].get(t_key)
                                if title == "🔥 ÜST": t_metni = "2.5 ÜST"
                                elif title == "🛡️ ALT": t_metni = "2.5 ALT"
                                
                                puan_degeri = int(m['res'].get(sort_key) if title in ["⭐ BANKO", "💎 İDEAL"] else 80)
                                
                                html_output += f"""
                                <div style="background: #161b22; padding: 8px; margin-bottom: 6px; border-radius: 6px; border: 1px solid #30363d;">
                                    <div style="color:#8b949e; font-size:10px; margin-bottom:2px;">{m['lig'][0:20]}</div>
                                    <div style="font-size: 11px; font-weight: bold; margin-bottom:4px; color:#ffffff;">{m['ev'][0:12]} - {m['dep'][0:12]}</div>
                                    <span style="color:{color}; font-weight:bold; font-size:13px;">{t_metni}</span>
                                    <span style="float:right; font-size:11px; color:#8b949e; font-weight:bold;">%{puan_degeri}</span>
                                </div>
                                """
                            
                            html_output += "</div>"
                            components.html(html_output, height=600, scrolling=True)
            else:
                st.warning("🤖 Analiz kriterlerine uyan maç bulunamadı.")
elif mod == "Global AI":
    # 1. Algoritma ve Hafta Seçimi
    filtre = st.sidebar.radio("🤖 Algoritma Seçimi", 
                               ["AETHER AI Master", "WICKHAM AI v3", "Nexus AI", "Spektrum AI"])
    
    s_sec = st.sidebar.selectbox("📅 Analiz Haftası", list(range(1, 13)), index=site_h_aktif-1, key="global_hafta_fs")

    h_baslangic = SİTE_DOGUM_TARİHİ + timedelta(weeks=s_sec - 1)
    h_bitis = h_baslangic + timedelta(days=7)

    st.title(f"🚀 {filtre} - {s_sec}. Hafta Analizi")
    st.info(f"📅 Kapsam: {h_baslangic.strftime('%d.%m')} - {h_bitis.strftime('%d.%m')} | Veri Kaynağı: FootyStats Premium")

    # 2. VERİ KONTROLÜ
    if not st.session_state.fs_data:
        st.warning("⚠️ Önce sol menüdeki '39 LİGİ TARAMAYA BAŞLA' butonuna basarak Premium verileri çekmelisiniz.")
    else:
        # Seçilen haftanın maçlarını filtrele
        haftalik_havuz = []
        for m in st.session_state.fs_data:
            # FootyStats xG verilerini analiz motoruna gönder
            res = analiz_et_v3(m['home'], m['away'], m['xg_h'], m['xg_a'])
            if res:
                # Filtreye göre puan türünü belirle
                p_key = "ae_c" if "AETHER" in filtre else "w_c" if "WICKHAM" in filtre else "n_c"
                m.update({'res': res, 'puan': res.get(p_key, 0)})
                haftalik_havuz.append(m)

        if len(haftalik_havuz) > 0:
            # --- 🛡️ MÜHÜRLEME SİSTEMİ (Premium v12) ---
            muhur_anahtari = f"muhur_fs_{s_sec}_{filtre.replace(' ', '_')}"
            
            if muhur_anahtari not in st.session_state:
                # Sadece %70 güven barajını geçen elit maçlar
                elit_havuz = [m for m in haftalik_havuz if m['puan'] >= 70]
                
                st.session_state[muhur_anahtari] = {
                    "banko": sorted([m for m in elit_havuz if winner(m['res']['aether'])=="1"], key=lambda x: x['puan'], reverse=True)[:10],
                    "ideal": sorted([m for m in elit_havuz if winner(m['res']['aether'])=="2"], key=lambda x: x['puan'], reverse=True)[:10],
                    "ust": sorted(elit_havuz, key=lambda x: x['res']['total_xg'], reverse=True)[:10],
                    "alt": sorted(elit_havuz, key=lambda x: x['res']['total_xg'], reverse=False)[:10]
                }

            m_kupon = st.session_state[muhur_anahtari]
            st.subheader(f"🎯 {filtre} Konseyi: Haftalık Elit Kuponlar")

            c1, c2, c3, c4 = st.columns(4)
            kupon_detay = [
                ("⭐ BANKO", c1, "banko", "#58A6FF"),
                ("💎 İDEAL", c2, "ideal", "#3fb950"),
                ("🔥 ÜST 10", c3, "ust", "#d73a49"),
                ("🛡️ ALT 10", c4, "alt", "#0366d6")
            ]

            for title, col, k_key, color in kupon_detay:
                with col:
                    matches = m_kupon[k_key]
                    html_kod = f"""
                    <div style="background: #0d1117; color: #c9d1d9; font-family: sans-serif; padding: 10px; border-radius: 10px; border-top: 4px solid {color}; border: 1px solid #30363d;">
                        <div style="color: {color}; font-weight: bold; font-size: 14px; text-align: center; margin-bottom: 10px; border-bottom: 1px solid #30363d; padding-bottom: 5px;">{title}</div>
                    """
                    for m in matches:
                        t_metni = m['res']['aether'] if k_key in ['banko', 'ideal'] else ('2.5 ÜST' if k_key=='ust' else '2.5 ALT')
                        html_kod += f"""
                        <div style="background: #161b22; padding: 6px; margin-top: 5px; border-radius: 5px; font-size: 11px; border: 1px solid #21262d;">
                            <b>{m['home'][:10]} - {m['away'][:10]}</b><br>
                            <span style="color: {color}; font-weight: bold;">{t_metni}</span>
                            <span style="float: right; color: #8b949e;">%{m['puan']}</span>
                        </div>
                        """
                    html_kod += "</div>"
                    st.components.v1.html(html_kod, height=500, scrolling=True)

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Yapay Zeka Onur Listesi")
    
    # Kara Kutu Verilerini Harmanla
    otonom_gelenler = {int(k): v for k, v in st.session_state.get('otonom_kayitlar', {}).items()}
    
    # Manuel Arşiv (Eski verilerin)
    manuel_veriler = {
        1: {"W": {"p": 75, "t": "Başlangıç"}, "A": {"p": 88, "t": "Stabil"}},
        3: {"W": {"p": 94, "t": "Domination"}, "A": {"p": 85, "t": "Elit"}}
    }
    
    kupon_sonuclari = {**manuel_veriler, **otonom_gelenler}
    
    secilen_h = st.select_slider("🔎 Performans İncele", options=list(range(1, site_h_aktif + 1)), value=max(1, site_h_aktif - 1))
    
    h_detay = kupon_sonuclari.get(secilen_h, {})
    
    r_config = [
        {"id": "W", "n": "WICKHAM", "c": "#d73a49", "e": "🧪"},
        {"id": "A", "n": "AETHER", "c": "#58A6FF", "e": "✨"},
        {"id": "N", "n": "NEXUS", "c": "#3fb950", "e": "🛡️"},
        {"id": "S", "n": "STANDART", "c": "#8b949e", "e": "🤖"}
    ]

    st.markdown(f"### 📊 {secilen_h}. Hafta Performans Raporu")
    cols = st.columns(4)
    for i, rb in enumerate(r_config):
        data = h_detay.get(rb["id"], {"p": 0, "t": "Bekleniyor ⏳"})
        with cols[i]:
            st.markdown(f"""
            <div style="background: rgba(22, 27, 34, 0.6); padding: 10px; border-radius: 10px; border-top: 4px solid {rb['c']}; text-align: center;">
                <h3 style="margin:0; color:{rb['c']}; font-size: 0.9rem;">{rb['e']} {rb['n']}</h3>
                <h2 style="margin:5px 0; color: white; font-size: 1.5rem;">%{data['p']}</h2>
                <div style="font-size: 0.7rem; color:{rb['c']}; font-weight: bold;">{data['t']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(data['p'] / 100)

    st.divider()
    
    # Başarı Arşivi Tablosu
    arsiv_listesi = []
    for h in range(1, site_h_aktif + 1):
        h_ozet = kupon_sonuclari.get(h, {})
        arsiv_listesi.append({
            "Hafta": f"{h}. Hafta",
            "🧪 WICKHAM": f"%{h_ozet.get('W', {}).get('p', '85')}",
            "✨ AETHER": f"%{h_ozet.get('A', {}).get('p', '88')}",
            "Durum": "✅ Tamamlandı" if h < site_h_aktif else "⏳ Analiz Sürüyor"
        })
    st.table(pd.DataFrame(arsiv_listesi).set_index("Hafta"))
    st.info("💡 FootyStats Premium verileriyle mühürlenen haftalar 'Elit' statüsünde arşivlenir.")

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Yapay Zeka Onur Listesi")
    
    # --- 1. VERİ BİRLEŞTİRME MERKEZİ ---
    # Senin manuel girdiğin geçmiş veriler
    manuel_veriler = {
        1: {
            "W": {"b": "✅ 4/5", "i": "✅ 3/5", "u": "❌ 2/5", "a": "✅ 5/5", "p": 75, "t": "Başlangıç"},
            "A": {"b": "✅ 5/5", "i": "✅ 4/5", "u": "✅ 4/5", "a": "✅ 3/5", "p": 88, "t": "Stabil"},
            "N": {"b": "✅ 3/5", "i": "✅ 4/5", "u": "❌ 2/5", "a": "🛡️ 5/5", "p": 82, "t": "Defansif"},
            "S": {"b": "✅ 4/5", "i": "✅ 3/5", "u": "✅ 4/5", "a": "✅ 3/5", "p": 80, "t": "Dengeli"},
            "SP": {"b": "✅ 2/5", "i": "✅ 3/5", "u": "🔥 5/5", "a": "❌ 2/5", "p": 70, "t": "Ofansif"}
        },
        3: {
            "W": {"b": "🏆 5/5", "i": "✅ 4/5", "u": "🔥 5/5", "a": "✅ 4/5", "p": 94, "t": "DOMİNASYON 🔥"},
            "A": {"b": "✅ 4/5", "i": "✅ 4/5", "u": "✅ 4/5", "a": "✅ 3/5", "p": 85, "t": "Stabil"},
            "N": {"b": "✅ 3/5", "i": "✅ 4/5", "u": "❌ 2/5", "a": "🛡️ 5/5", "p": 88, "t": "Duvar"},
            "S": {"b": "✅ 4/5", "i": "✅ 3/5", "u": "✅ 4/5", "a": "✅ 4/5", "p": 82, "t": "Rutin"},
            "SP": {"b": "✅ 3/5", "i": "✅ 3/5", "u": "✅ 4/5", "a": "✅ 3/5", "p": 78, "t": "Durgun"}
        }
    }

    # 🛠️ DAHİYANE DOKUNUŞ: Kara Kutu (JSON) verilerini sayısal anahtara çevirip harmanlıyoruz
    # JSON'dan gelen "1" değerini 1'e çevirerek manuel verilerle çakışmadan birleşmesini sağlar.
    otonom_gelenler = {int(k): v for k, v in st.session_state.get('otonom_kayitlar', {}).items()}
    
    # İki veri setini birleştir (Aynı hafta varsa otonom olan güncel kabul edilir)
    kupon_sonuclari = {**manuel_veriler, **otonom_gelenler}
    
    # --- 2. HAFTA SEÇİCİ ---
    secilen_h = st.select_slider(
        "🔎 İncelemek İstediğiniz Haftayı Seçin",
        options=list(range(1, site_h_aktif + 1)),
        value=max(1, site_h_aktif - 1)
    )

    # Seçilen haftanın verisini çekiyoruz
    h_detay = kupon_sonuclari.get(secilen_h, {})

    # Robot konfigürasyonu
    r_config = [
        {"id": "W", "n": "WICKHAM", "u": "Kaos Avcısı", "c": "#d73a49", "e": "🧪"},
        {"id": "A", "n": "AETHER", "u": "Matematik Prof.", "c": "#58A6FF", "e": "✨"},
        {"id": "N", "n": "NEXUS", "u": "Çelik Duvar", "c": "#3fb950", "e": "🛡️"},
        {"id": "S", "n": "STANDART", "u": "İstikrar", "c": "#8b949e", "e": "🤖"},
        {"id": "SP", "n": "SPEKTRUM", "u": "Gol Makinesi", "c": "#f1e05a", "e": "🔥"}
    ]

    st.markdown(f"### 📊 {secilen_h}. Hafta Performans Raporu")

    # --- 3. GÜVEN ENDEKSİ KARTLARI ---
    cols = st.columns(5)
    for i, rb in enumerate(r_config):
        data = h_detay.get(rb["id"], {"p": 0, "t": "Veri Bekleniyor ⏳"})
        with cols[i]:
            st.markdown(f"""
            <div style="background: rgba(22, 27, 34, 0.6); padding: 10px; border-radius: 10px; border-top: 4px solid {rb['c']}; text-align: center; height: 150px;">
                <h3 style="margin:0; color:{rb['c']}; font-size: 0.9rem;">{rb['e']} {rb['n']}</h3>
                <h2 style="margin:5px 0; color: white; font-size: 1.5rem;">%{data['p']}</h2>
                <div style="font-size: 0.7rem; color:{rb['c']}; font-weight: bold;">{data['t']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(data['p'] / 100)

    st.divider()

    # --- 4. SAVAŞ TABLOSU ---
    st.subheader(f"⚔️ {secilen_h}. Hafta Kupon Karnesi")
    
    if not h_detay:
        st.warning(f"⚠️ {secilen_h}. hafta verileri henüz mühürlenmedi veya maçlar tamamlanmadı.")
    else:
        st.markdown("""
            <div style="display: flex; background: #21262d; padding: 10px; border-radius: 8px 8px 0 0; border-bottom: 2px solid #30363d; font-weight: bold; text-align: center;">
                <div style="flex: 1.5; text-align: left;">🤖 ALGORİTMA</div>
                <div style="flex: 1;">⭐ BANKO</div>
                <div style="flex: 1;">💎 İDEAL</div>
                <div style="flex: 1;">⚽ ÜST</div>
                <div style="flex: 1;">📉 ALT</div>
            </div>
        """, unsafe_allow_html=True)

        for rb in r_config:
            res = h_detay.get(rb["id"], {"b": "-", "i": "-", "u": "-", "a": "-"})
            
            def gold_check(val):
                return "color: #f1e05a; font-weight: bold;" if "5/5" in str(val) or "🏆" in str(val) else "color: white;"

            st.markdown(f"""
                <div style="display: flex; align-items: center; padding: 12px; border-bottom: 1px solid #30363d; background: rgba(22, 27, 34, 0.4); text-align: center;">
                    <div style="flex: 1.5; text-align: left; font-weight: bold; color: {rb['c']};">
                        {rb['e']} {rb['n']}
                    </div>
                    <div style="flex: 1; {gold_check(res['b'])}">{res['b']}</div>
                    <div style="flex: 1; {gold_check(res['i'])}">{res['i']}</div>
                    <div style="flex: 1; {gold_check(res['u'])}">{res['u']}</div>
                    <div style="flex: 1; {gold_check(res['a'])}">{res['a']}</div>
                </div>
            """, unsafe_allow_html=True)

        st.caption("🏆 '5/5' ve 'FULL' yazan tahminler Altın Sarısı ile işaretlenmiştir.")
    
    st.divider()

    # --- 5. DETAYLI KUPON KARNESİ ---
    with st.expander(f"🧐 {secilen_h}. Haftanın Tüm Robot Detaylarını Gör", expanded=False):
        for rb in r_config:
            if rb["id"] in h_detay:
                st.markdown(f"#### {rb['e']} {rb['n']} Performansı")
                res = h_detay[rb["id"]]
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("⭐ Banko", res["b"])
                with c2: st.metric("💎 İdeal", res["i"])
                with c3: st.metric("⚽ Üst", res["u"])
                with c4: st.metric("📉 Alt", res["a"])
                st.write("---")

    # --- 6. TARİHSEL VERİ AKIŞI (Statik Arşiv) ---
    st.subheader("📂 Genel Başarı Arşivi")
    arsiv_listesi = []
    for h in range(1, site_h_aktif + 1):
        h_bas = SİTE_DOGUM_TARİHİ + timedelta(weeks=h-1)
        h_bit = h_bas + timedelta(days=7)
        durum = "✅ Tamamlandı" if h < site_h_aktif else "⏳ Analiz Sürüyor"
        
        # Arşiv tablosu için ortalama başarıları otonom verilerden çekmeye çalışalım
        # Eğer veri yoksa senin manuel belirlediğin aralıkları gösterir
        h_ozet = kupon_sonuclari.get(h, {})
        w_p = f"%{h_ozet.get('W', {}).get('p', '85-90')}"
        a_p = f"%{h_ozet.get('A', {}).get('p', '88-92')}"
        
        arsiv_listesi.append({
            "Hafta": f"{h}. Hafta",
            "Tarih": f"{h_bas.strftime('%d.%m')} - {h_bit.strftime('%d.%m')}",
            "🧪 WICK": w_p, "✨ AETH": a_p, "Durum": durum
        })

    st.table(pd.DataFrame(arsiv_listesi).set_index("Hafta"))
    st.info(f"💡 **Not:** Onur Listesi, Milat tarihinden ({SİTE_DOGUM_TARİHİ.strftime('%d.%m.%Y')}) itibaren otonom olarak güncellenmektedir.")
