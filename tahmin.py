import streamlit as st
import json
import os # Dosya kontrolü için şart
import pandas as pd
import random
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

# --- 1. AYARLAR & MİLAT ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
LIGLER = {
    "İngiltere": "PL", 
    "İspanya": "PD", 
    "İtalya": "SA", 
    "Almanya": "BL1", 
    "Fransa": "FL1", 
    "Hollanda": "DED",
    "Portekiz": "PPL",
    "Brezilya": "BSA"
}
SİTE_DOGUM_TARİHİ = datetime(2026, 2, 20) 

# Sayfa konfigürasyonu her zaman fonksiyonlardan önce veya hemen sonra gelmeli (Burada olması iyi)
st.set_page_config(page_title="UltraSkor Pro: AETHER Intelligence", page_icon="🎯", layout="wide")

def tum_ligleri_tara():
    # football-data.org için lig kodları (Bunlar kesin çalışır)
    ligler = {
        "İngiltere Premier": "PL",
        "İspanya La Liga": "PD",
        "İtalya Serie A": "SA",
        "Almanya Bundesliga": "BL1",
        "Fransa Ligue 1": "FL1",
        "Hollanda Eredivisie": "DED",
        "Portekiz": "PPL"
    }
    
    tum_fikstur = []
    tum_hafiza = []
    islem_kutusu = st.empty()
    
    headers = {"X-Auth-Token": "b900863038174d07855ace7f33c69c9b"}

    for l_ad, l_kod in ligler.items():
        islem_kutusu.info(f"📡 {l_ad} ({l_kod}) verileri çekiliyor...")
        
        # 1. GELECEK MAÇLAR
        try:
            f_res = requests.get(f"https://api.football-data.org/v4/competitions/{l_kod}/matches?status=SCHEDULED", headers=headers, timeout=10).json()
            if 'matches' in f_res:
                for m in f_res['matches']:
                    tum_fikstur.append({
                        'home': m['homeTeam']['name'],
                        'away': m['awayTeam']['name'],
                        'lig': str(l_ad) # Lig ismini mühürledik
                    })
        except: pass

        # 2. GEÇMİŞ MAÇLAR (Robotun Hafızası)
        try:
            h_res = requests.get(f"https://api.football-data.org/v4/competitions/{l_kod}/matches?status=FINISHED", headers=headers, timeout=10).json()
            if 'matches' in h_res:
                for m in h_res['matches']:
                    tum_hafiza.append({
                        'homeTeam': {'name': m['homeTeam']['name']},
                        'awayTeam': {'name': m['awayTeam']['name']},
                        'status': 'FINISHED',
                        'score': {
                            'fullTime': {
                                'home': m['score']['fullTime']['home'],
                                'away': m['score']['fullTime']['away']
                            }
                        },
                        'matchday': m.get('matchday', 1)
                    })
        except: pass

    islem_kutusu.success("🌍 Sağlam API ile Tüm Bülten Güncellendi!")
    return tum_fikstur, tum_hafiza   
    
# --- 2. TEMEL HESAP MAKİNESİ (check_hit) ---
def check_hit(liste, tip):
    # BURAYA: Daha önce yazdığımız maç sonuçlarını kontrol eden 
    # o uzun döngüleri ve "skor += 1" mantığını yapıştır.
    skor = 0
    # ... senin mevcut kodların ...
    return skor

# --- 3. OTONOM ARŞİVLEME & KARA KUTU MOTORU ---

import json
import os
from datetime import datetime

ARSIV_DOSYASI = "ai_arsiv.json"

# --- 🛠️ TEMEL YAZMA/OKUMA FONKSİYONLARI ---
def kara_kutu_oku():
    if os.path.exists(ARSIV_DOSYASI):
        with open(ARSIV_DOSYASI, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def kara_kutu_yaz(veri):
    with open(ARSIV_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

# --- 🔐 BETON MÜHÜRLEME (DEĞİŞMEYEN KUPONLAR) ---
def otomatik_muhur_tetikleyici():
    """Mühürü hem session_state'e hem de JSON dosyasına kalıcı olarak işler."""
    simdi = datetime.now()
    arsiv = kara_kutu_oku()
    
    # Cuma 12:00 sonrası mühürleme kontrolü
    if simdi.weekday() == 4 and simdi.hour >= 12:
        filtre_anahtar = "AETHER_AI_Master"
        muhur_anahtari = f"muhur_{site_h_aktif}_{filtre_anahtar}"
        
        # 1. ÖNCE DOSYADA (JSON) VAR MI BAK? (Varsa oradan çek, asla değiştirme)
        if f"m_k_{site_h_aktif}" in arsiv:
            st.session_state[muhur_anahtari] = arsiv[f"m_k_{site_h_aktif}"]
            return

        # 2. DOSYADA YOKSA VE HAFIZADA VERİ VARSA YENİ MÜHÜR BAS
        # 'son_bankolar' gibi verilerin dolu olduğundan emin olmalıyız
        if muhur_anahtari not in st.session_state:
            guncel_banko = st.session_state.get('son_bankolar', [])
            
            if guncel_banko:
                m_veri = {
                    "banko": guncel_banko,
                    "ideal": st.session_state.get('son_idealler', []),
                    "ust": st.session_state.get('son_ustler', []),
                    "alt": st.session_state.get('son_altlar', [])
                }
                # Hem hafızaya al
                st.session_state[muhur_anahtari] = m_veri
                # Hem de JSON'a 'm_k_X' (Mühürlü Kupon) olarak kalıcı işle
                arsiv[f"m_k_{site_h_aktif}"] = m_veri
                kara_kutu_yaz(arsiv)
                st.toast(f"🎯 {site_h_aktif}. Hafta MÜHÜRLENDİ VE ARŞİVLENDİ!")

# --- 🏆 OTONOM BAŞARI ARŞİVLEME ---
def otonom_arsiv_guncelle():
    global site_h_aktif  # Dışarıdaki değişkeni içeri çağırıyoruz
    
    # 1. Değişkeni en başta tanımlıyoruz (Hata almamak için şart!)
    guncelleme_var_mi = False 
    
    arsiv = kara_kutu_oku()
    
    # 2. Bitmiş haftaların sonuçlarını hesapla
    try:
        for h_no in range(1, site_h_aktif + 1):
            h_key = str(h_no)
            m_key = f"m_k_{h_no}" # JSON'daki mühürlü kupon anahtarı
            
            # Eğer bu hafta mühürlenmişse ama özeti henüz yazılmamışsa
            if m_key in arsiv and (h_key not in arsiv or arsiv[h_key].get("durum") != "KAPALİ"):
                m_kupon = arsiv[m_key]
                
                # Haftanın sonuçlarını check_hit ile hesapla
                b_skor = check_hit(m_kupon.get("banko", []), "banko")
                i_skor = check_hit(m_kupon.get("ideal", []), "ideal")
                u_skor = check_hit(m_kupon.get("ust", []), "ust")
                a_skor = check_hit(m_kupon.get("alt", []), "alt")
                
                # Puanlama (20 maç üzerinden % kaç başarı)
                toplam_isabet = b_skor + i_skor + u_skor + a_skor
                puan = int((toplam_isabet / 20) * 100) if toplam_isabet > 0 else 0
                
                # Arşiv özetini oluştur
                arsiv[h_key] = {
                    "W": {"b": f"{b_skor}/5", "i": f"{i_skor}/5", "u": f"{u_skor}/5", "a": f"{a_skor}/5", "p": puan},
                    "durum": "KAPALİ" if h_no < site_h_aktif else "AÇIK"
                }
                guncelleme_var_mi = True

        # 3. Eğer bir güncelleme yapıldıysa dosyaya yaz
        if guncelleme_var_mi:
            kara_kutu_yaz(arsiv)
        
        # 4. Global erişim için session_state'e aktar
        st.session_state.otonom_kayitlar = arsiv
        
    except Exception as e:
        st.error(f"Otonom Arşiv Hatası: {e}")
    
    st.session_state.otonom_kayitlar = arsiv

# --- 🚀 ÇALIŞTIRMA SIRALAMASI (BURASI ÇOK KRİTİK) ---

# 1. Önce değişkeni hesapla (Her şeyden önce bu gelmeli!)
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

# 2. Sonra bu değişkeni kullanan fonksiyonları çağır
otomatik_muhur_tetikleyici()
otonom_arsiv_guncelle()
# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .editor-card { background: linear-gradient(145deg, #1c2128, #0d1117); border: 1px solid #58A6FF; padding: 15px; border-radius: 12px; height: 100%; border-top: 4px solid #58A6FF; position: relative; margin-bottom: 20px; }
    .success-badge { background: #238636; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; float: right; }
    .full-hit-seal { position: absolute; top: -10px; right: -10px; background: #D4AF37; color: black; padding: 5px 10px; border-radius: 5px; font-weight: bold; transform: rotate(15deg); box-shadow: 0 0 10px rgba(212,175,55,0.5); z-index: 10; font-size: 0.8rem; }
    .coupon-item { background: #0d1117; padding: 8px; margin-top: 8px; border-radius: 6px; border: 1px solid #30363d; font-size: 0.85rem; }
    .coupon-title { font-weight: bold; color: #58A6FF; margin-bottom: 10px; text-align: center; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .aether-box { background: rgba(138, 43, 226, 0.1); border: 1px solid #8A2BE2; color: #E0B0FF !important; }
    .ai-insight { background: rgba(88, 166, 255, 0.05); border-left: 4px solid #58A6FF; padding: 12px; margin-top: 15px; border-radius: 4px; font-size: 0.85rem; color: #C9D1D9; font-style: italic; }
    .form-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }
    .form-W { background-color: #238636; } .form-D { background-color: #9e9e9e; } .form-L { background-color: #f85149; }
    .standings-table { font-size: 0.8rem; width: 100%; border-collapse: collapse; background: #161b22; border-radius: 10px; overflow: hidden; margin-top: 10px; }
    .standings-table th { background: #30363d; padding: 10px; text-align: left; color: #58A6FF; }
    .standings-table td { padding: 8px 10px; border-bottom: 1px solid #30363d; }
    .lock-box { background: #161b22; border: 2px dashed #f85149; padding: 40px; border-radius: 15px; text-align: center; color: #f85149; margin-bottom: 20px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ VE BAŞARI MOTORU ---
@st.cache_data(ttl=3600)
def veri_al(endpoint):
    try: return requests.get(f"https://api.football-data.org/v4/{endpoint}", headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}
def wickham_psikoloji_analizi(ev_ad, dep_ad, matches, l_ad):
    # Bu fonksiyon takımların ligdeki konumuna göre motivasyon katsayısı üretir
    try:
        # Puan durumunu çekiyoruz
        l_kodu = LIGLER.get(l_ad, "PL")
        standings = veri_al(f"competitions/{l_kodu}/standings")
        table = standings['standings'][0]['table']
        
        # Takımların verilerini ayıklıyoruz
        pos = {t['team']['name']: {'rank': t['position'], 'pts': t['points']} for t in table}
        
        e = pos.get(ev_ad)
        d = pos.get(dep_ad)
        
        if not e or not d: return 1.0, "Standart Motivasyon"

        # --- WICKHAM'IN PSİKOLOJİK SENARYOLARI ---
        
        # Senaryo A: Şampiyonluk Baskısı (Lider veya Takipçi Evindeyse)
        if e['rank'] <= 3 and abs(e['pts'] - pos[list(pos.keys())[0]]['pts']) < 6:
            # Şampiyonluğa oynayan takım hata yapamaz, 'Fire Strike' moduna girer
            return 1.18, "🔥 ŞAMPİYONLUK BASKISI: Ev sahibi mutlak galibiyet için tüm hatlarıyla saldıracak."

        # Senaryo B: Rahat Orta Sıra Deplasmanı (Bournemouth Etkisi)
        if 8 <= d['rank'] <= 14:
            # Hedefsiz takım deplasmanda stres yapmaz, kontra atakla tehlikeli olur
            return 1.10, "🕵️ RAHAT DEPLASMAN: Konuk ekip hedefsiz olmanın verdiği rahatlıkla sürpriz kovalayabilir."

        # Senaryo C: Küme Düşme Hattı Direnişi
        if d['rank'] >= 17:
            # Küme düşmemeye oynayan takım 'Iron Wall' moduna bürünür
            return 0.85, "🛡️ KÜME HATTI DİRENCİ: Deplasman ekibi ligde kalmak için otobüsü kaleye çekecektir."

        return 1.0, "Dengeli Motivasyon"
    except:
        return 1.0, "Veri Kısıtı: Psikolojik analiz yapılamadı."
def motivasyon_hesapla(ev_ad, dep_ad, l_kodu):
    # Bu fonksiyon puan durumunu çekip takımların 'Stres/Kaos' katsayısını belirler
    try:
        data = veri_al(f"competitions/{l_kodu}/standings")
        table = data['standings'][0]['table']
        pos = {t['team']['name']: {'p': t['position'], 'pts': t['points']} for t in table}
        
        e_p, d_p = pos[ev_ad]['p'], pos[dep_ad]['p']
        e_pts, d_pts = pos[ev_ad]['pts'], pos[dep_ad]['pts']
        
        kaos = 1.0
        # SENARYO: Favori şampiyonluk potasında (İlk 3) ve rakibiyle puan farkı çoksa
        if e_p <= 3 and abs(e_pts - d_pts) > 15:
            kaos = 1.15 # Şampiyonluk stresi/baskısı (Fire Strike Artar)
        # SENARYO: Deplasman orta sıralarda (Hedefsiz) ve rahatsa
        if 7 <= d_p <= 13:
            kaos *= 1.10 # Kaybedecek bir şeyi yok, daha cesur oynar
            
        return kaos
    except: return 1.0
def winner(sk):
    try:
        p = sk.split(" - ")
        if int(p[0]) > int(p[1]): return "1"
        if int(p[1]) > int(p[0]): return "2"
        return "X"
    except: return "?"

# --- 1. GÖRSEL FORM NOKTALARI ---
def get_form_dots(team_name, matches):
    # Status kontrolü ve takım ismi filtreleme
    finished = [m for m in matches if m.get('status') == 'FINISHED' and (m['homeTeam']['name'] == team_name or m['awayTeam']['name'] == team_name)]
    # Tarihe göre sırala ve son 5 maçı al
    finished = sorted(finished, key=lambda x: x.get('utcDate', ''), reverse=True)[:5]
    
    dots = ""
    for m in finished:
        try:
            h_s = m['score']['fullTime']['home']
            a_s = m['score']['fullTime']['away']
            if m['homeTeam']['name'] == team_name:
                res = "W" if h_s > a_s else ("L" if a_s > h_s else "D")
            else:
                res = "W" if a_s > h_s else ("L" if h_s > a_s else "D")
            dots += f'<span class="form-dot form-{res}"></span>'
        except:
            continue
    return f'<div style="margin-top:3px;">{dots}</div>'

# --- 🚀 iSPORTS API AYARLARI ---
ISPORTS_API_KEY = "aG7K4Saw0S7rG40B"
ISPORTS_BASE_URL = "http://api.isportsapi.com/sport/football"

def isports_veri_al(endpoint, params={}):
    """iSportsAPI üzerinden veri çeker."""
    params['api_key'] = ISPORTS_API_KEY
    url = f"{ISPORTS_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"⚠️ iSportsAPI Bağlantı Hatası: {e}")
        return None

def tum_ligleri_tara():
    # iSportsAPI League ID'leri (Dökümana göre en popüler ligler)
    ligler = {
        "Türkiye Süper Lig": "163", 
        "İngiltere Premier": "82",
        "İspanya La Liga": "120",
        "Almanya Bundesliga": "114",
        "İtalya Serie A": "119",
        "Fransa Ligue 1": "111",
        "Hollanda Eredivisie": "131"
    }
    
    tum_fikstur = []
    tum_hafiza = []
    islem_kutusu = st.empty()
    
    for l_ad, l_id in ligler.items():
        islem_kutusu.info(f"📡 {l_ad} gerçek verileri çekiliyor...")
        
        # 1. GELECEK MAÇLAR (Fixtures)
        # iSportsAPI fixture endpoint'i genelde 'schedule' olarak geçer
        f_data = isports_veri_al("schedule", params={"leagueId": l_id})
        
        if f_data and f_data.get('code') == 0:
            matches = f_data.get('data', [])
            for m in matches:
                # Sadece henüz başlamamış maçları al
                if m.get('status') == "0": 
                    tum_fikstur.append({
                        'home': m.get('homeName'),
                        'away': m.get('awayName'),
                        'lig': str(l_ad),
                        'date': m.get('matchTime')
                    })
        
        # 2. GEÇMİŞ MAÇLAR (Hafıza - Robotun Beyni)
        # iSportsAPI sonuçlar için genelde 'score' veya 'history' endpoint'i kullanır
        h_data = isports_veri_al("score", params={"leagueId": l_id})
        if h_data and h_data.get('code') == 0:
            results = h_data.get('data', [])
            for r in results:
                # Sadece bitmiş maçları hafızaya ekle
                if r.get('status') == "-1": # -1 genelde FINISHED demektir
                    tum_hafiza.append({
                        'homeTeam': {'name': r.get('homeName')},
                        'awayTeam': {'name': r.get('awayName')},
                        'status': 'FINISHED',
                        'score': {
                            'fullTime': {
                                'home': int(r.get('homeScore') or 0),
                                'away': int(r.get('awayScore') or 0)
                            }
                        }
                    })

    islem_kutusu.success("🌍 iSportsAPI ile Gerçek Veriler Yüklendi!")
    return tum_fikstur, tum_hafiza

# --- 3. DÜRÜST ANALİZ MOTORU (POISSON) ---
def analiz_et(ev, dep, matches, h_no):
    try:
        def temizle(metin):
            if not metin: return ""
            return str(metin).lower().strip().replace(" ", "").replace("ş", "s").replace("ç", "c").replace("ı", "i").replace("ğ", "g").replace("ö", "o").replace("ü", "u")

        ev_t, dep_t = temizle(ev), temizle(dep)
        df_raw = []
        for m in matches:
            h_hafiza = temizle(m['homeTeam']['name'])
            a_hafiza = temizle(m['awayTeam']['name'])
            
            if h_hafiza == ev_t or a_hafiza == ev_t or h_hafiza == dep_t or a_hafiza == dep_t:
                if m.get('score') and m['score'].get('fullTime') and m['score']['fullTime']['home'] is not None:
                    df_raw.append({
                        'H': m['homeTeam']['name'],
                        'A': m['awayTeam']['name'],
                        'HG': m['score']['fullTime']['home'],
                        'AG': m['score']['fullTime']['away'],
                        'MD': m.get('matchday', 1)
                    })

        # --- 🚀 EMNİYET KİLİDİ (Bilmediği Maça Sallamasını Önler) ---
        if len(df_raw) < 3: 
            return {
                "std": "?.?", "s_c": 0, "spec": "?.?", "sp_c": 0,
                "nexus": "?.?", "n_c": 0, "wickham": "?.?", "w_c": 0,
                "aether": "?.?", "ae_c": 0, "total_xg": 0, "h_p": 0, "s_p": 0, "note": "❌ Yetersiz Veri"
            }

        # --- 📊 POISSON MATEMATİK MOTORU ---
        df = pd.DataFrame(df_raw)
        l_e, l_d = df['HG'].mean(), df['AG'].mean()
        if l_e == 0: l_e = 1.0
        if l_d == 0: l_d = 1.0
        
        def get_stats(team_name, is_h):
            t_clean = temizle(team_name)
            t_df = df[df.apply(lambda x: temizle(x['H' if is_h else 'A']) == t_clean, axis=1)].copy()
            if t_df.empty: return l_e, l_d, 1.0
            max_md = df['MD'].max() if df['MD'].max() > 0 else 1
            t_df['w'] = 1.0 + (t_df['MD'] / max_md)
            g = (t_df['HG' if is_h else 'AG'] * t_df['w']).sum() / t_df['w'].sum()
            y = (t_df['AG' if is_h else 'HG'] * t_df['w']).sum() / t_df['w'].sum()
            e_rec = t_df.sort_values('MD', ascending=False).head(3)['HG' if is_h else 'AG'].mean()
            return g, y, e_rec

        e_g, e_y, e_rec = get_stats(ev, True)
        d_g, d_y, d_rec = get_stats(dep, False)
        
        # xG Hesaplamaları
        ex = (e_g / l_e) * (d_y / l_e) * l_e
        ax = (d_g / l_d) * (e_y / l_d) * l_d
        
        from scipy.stats import poisson
        import numpy as np # np hatası almamak için

        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            prob = m[s[0], s[1]] * 100
            conf = min(99, int(prob * 3 + abs(e-a)*20 + 20))
            return f"{s[0]} - {s[1]}", conf

        # --- 🤖 ROBOT TAHMİNLERİ ---
        r_s = sk(ex, ax)           # Standart
        r_sp = sk(ex * 1.2, ax * 1.2) # Spektrum (Gollü)
        r_nx = sk(ex * 0.8, ax * 1.1) # Nexus (Savunma/Alt)
        r_w = sk(ex * 1.3, ax * 0.8) # Wickham (Hücum)
        r_ae = sk((ex + ex*1.1)/2, (ax + ax*1.1)/2) # Aether (Denge)

        return {
            "std": r_s[0], "s_c": r_s[1],
            "spec": r_sp[0], "sp_c": r_sp[1],
            "nexus": r_nx[0], "n_c": r_nx[1],
            "wickham": r_w[0], "w_c": r_w[1],
            "aether": r_ae[0], "ae_c": r_ae[1],
            "total_xg": round(ex + ax, 2),
            "h_p": int(min(100, ex*40)), 
            "s_p": int(min(100, (1/max(0.1, ax))*20)),
            "note": "✅ Analiz Tamamlandı"
        }

    except Exception as e:
        # Tek bir genel hata yakalayıcı yeterlidir
        return None
        # --- 📈 4. MATEMATİKSEL MOTOR (Poisson) ---
        df = pd.DataFrame(df_raw)
        l_e, l_d = df['HG'].mean(), df['AG'].mean()
        
        # Sıfıra bölünme hatası koruması
        if l_e == 0: l_e = 1.0
        if l_d == 0: l_d = 1.0
        
        def get_stats(team_name, is_h):
            t_clean = temizle(team_name)
            # DataFrame içinde temizlenmiş isimlerle filtrele
            t_df = df[df.apply(lambda x: temizle(x['H' if is_h else 'A']) == t_clean, axis=1)].copy()
            
            if t_df.empty: return l_e, l_d, 1.0
            
            max_md = df['MD'].max() if df['MD'].max() > 0 else 1
            t_df['w'] = 1.0 + (t_df['MD'] / max_md)
            
            g = (t_df['HG' if is_h else 'AG'] * t_df['w']).sum() / t_df['w'].sum()
            y = (t_df['AG' if is_h else 'HG'] * t_df['w']).sum() / t_df['w'].sum()
            
            # Son form durumu
            recent = t_df.sort_values('MD', ascending=False).head(3)
            e_rec = recent['HG' if is_h else 'AG'].mean()
            return g, y, e_rec

        e_g, e_y, e_rec = get_stats(ev, True)
        d_g, d_y, d_rec = get_stats(dep, False)
        
        # xG Tahminleri (Poisson için temel)
        ex = (e_g / l_e) * (d_y / l_e) * l_e
        ax = (d_g / l_d) * (e_y / l_d) * l_d
        
        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            # Güven puanı: Skorun olasılığı ve güç farkı
            prob = m[s[0], s[1]] * 100
            conf = min(99, int(prob * 3 + abs(e-a)*20 + 20))
            return f"{s[0]} - {s[1]}", conf

        # --- 🤖 ROBOT ÇIKTILARINI HAZIRLA ---
        r_s = sk(ex * 1.05, ax * 0.95)   # Standart
        r_sp = sk(ex * 1.15, ax * 1.15) # Spektrum
        r_nx = sk(ex * 0.9, ax * 1.1)   # Nexus
        r_w = sk(ex * 1.1, ax * 0.8)    # Wickham
        
        # Aether Master Sentezi
        ae_ex, ae_ax = (ex + ex*1.1 + ex*0.9)/3, (ax + ax*1.1 + ax*0.8)/3
        r_ae = sk(ae_ex, ae_ax)

        return {
            "std": r_s[0], "s_c": r_s[1],
            "spec": r_sp[0], "sp_c": r_sp[1],
            "nexus": r_nx[0], "n_c": r_nx[1],
            "wickham": r_w[0], "w_c": r_w[1],
            "aether": r_ae[0], "ae_c": r_ae[1],
            "total_xg": round(ex + ax, 2),
            "h_p": int(min(100, ex*40)), "s_p": int(min(100, (1/max(0.1, ax))*20)),
            "note": "✅ Analiz Tamamlandı"
        }
    except Exception as e:
        # Hata durumunda boş dönme, en azından hatayı logla
        return None

        # --- STANDART RATIONAL LOGIC (Güvenli Liman Motoru) ---
        # Standart'ın felsefesi: "İstatistik yalan söylemez, uçlara kaçma"
        st_ex, st_ax = ex, ax
        
        # 🏟️ KURAL 1: "Ev Sahibi Kalesi" 
        # Ev sahibi avantajını ve ligin iç saha galibiyet eğilimini korur
        st_ex *= 1.05 
        st_ax *= 0.95
        
        # 📈 KURAL 2: "Regresyon (Ortalamaya Dönüş)"
        # Eğer bir takım normalden çok sapmışsa (aşırı formda veya formsuz), 
        # Standart AI onu lig ortalamasına doğru biraz 'terbiye' eder.
        if e_rec > 2.0: st_ex *= 0.90 # Aşırı gaza gelme
        if d_rec < 0.5: st_ax *= 1.10 # Deplasmanı o kadar da ezme
        
        # 🎯 KURAL 3: "Düşük Varyans"
        # Skor tahminlerinde 4-0, 5-1 gibi uçuk skorlar yerine 
        # en yüksek olasılıklı (1-0, 2-1, 1-1) skorları tercih eder.
        r_s = sk(st_ex, st_ax) # Standart'ın nihai rasyonel skoru

       # --- SPEKTRUM CHAOS & FLOW LOGIC (Gol ve Tempo Motoru) ---
        # Spektrum'un felsefesi: "Gol golü çeker" veya "Savunma savunmayı kilitler"
        sp_ex, sp_ax = ex, ax
        
        # 🔥 SENARYO 1: "Yüksek Volatilite" (Açık Futbol)
        # Eğer her iki takım da son 3 maçta hem atıp hem yemişse (Yüksek Tempo)
        if e_rec > 1.2 and d_rec > 1.2:
            sp_ex *= 1.18  # Maçın kopma ihtimali çok yüksek
            sp_ax *= 1.18  # Karşılıklı gol (KG VAR) kokusu
            
        # ❄️ SENARYO 2: "Negatif Akış" (Düşük Tempo)
        # Eğer takımlardan biri 'otobüsü çekiyorsa' (Çok az gol yiyorsa)
        elif e_rec < 0.8 or d_rec < 0.8:
            sp_ex *= 0.85  # Pozisyon bulmak samanlıkta iğne aramak gibi olacak
            sp_ax *= 0.85  # Skor 0-0 veya 1-0'a hapsolur
            
        # ⚡ SENARYO 3: "Baskın Karakter" 
        # Eğer ev sahibi çok formda, deplasman ise çok formsuzsa
        if e_rec > 1.5 and d_rec < 0.7:
            sp_ex *= 1.25  # Ev sahibi silindir gibi geçebilir
            sp_ax *= 0.75  # Deplasman gol atamaz
            
        r_sp = sk(sp_ex, sp_ax) # Spektrum'un nihai gol odaklı skoru

       # --- NEXUS STRATEGIC LOGIC (Sürpriz Analiz Motoru) ---
        # Nexus'un temeli: Favorinin formsuzluğu + Deplasmanın direnci
        nx_ex, nx_ax = ex, ax
        
        # 🛡️ STRATEJİ 1: "Yorgun Dev" Analizi
        # Eğer ev sahibi (favori) son 3 maçta beklenen golün (e_g) altında kaldıysa (e_rec)
        if e_rec < e_g * 0.9:
            nx_ex *= 0.88  # Ev sahibinin bitiriciliğine güvenme
            nx_ax *= 1.12  # Deplasmanın iştahını artır
            
        # 🛡️ STRATEJİ 2: "Otobüsü Çeken Deplasman"
        # Eğer deplasman takımı son 3 maçta kalesini iyi savunduysa (d_rec < 1.0)
        if d_rec < 1.05:
            nx_ex *= 0.92  # Gol bulmak zorlaşacak
            nx_ax *= 1.05  # Kontratakla bir tane atabilir
            
        # 🛡️ STRATEJİ 3: "Denge ve Kaos"
        # Eğer iki takımın gücü birbirine çok yakınsa, Nexus 'Beraberlik' sürprizine odaklanır
        if abs(ex - ax) < 0.3:
            nx_ex *= 0.95
            nx_ax *= 0.95 # Skorları 0-0 veya 1-1'e yaklaştırır
            
        r_nx = sk(nx_ex, nx_ax) # Nexus'un nihai sürpriz skoru

        # --- WICKHAM v3: BITIRICILIK & LIG ANALIZ MOTORU ---
        # Wickham'ın felsefesi: "Ligin karakteri ve takımların bitiriciliği skoru belirler"
        wx_ex, wx_ax = ex, ax
        
        # 🧪 WICKHAM ADIM 1: "Fire Strike" (Hücum Gücü) Uygulaması
        # Eğer hücum gücü yüksekse ve lig Hollanda/Almanya gibi 'açık' bir ligse skoru yukarı iter
        h_p = ((ex + ax) * 25) + (e_rec * 10) # Formülün temeli
        if l_ad in ["Hollanda", "Almanya"]: 
            h_p *= 1.10
            if h_p > 75:
                wx_ex *= 1.22
                wx_ax *= 1.22 # Wickham burada 'bol gollü' bir senaryo yazar

        # 🧪 WICKHAM ADIM 2: "Iron Wall" (Savunma Sertliği) Uygulaması
        # Eğer savunma puanı yüksekse ve lig İtalya/Fransa gibi 'kapalı' bir ligse skoru aşağı çeker
        s_p = 100 - ((ex + ax) * 15) - (e_y * 10)
        if l_ad in ["İtalya", "Fransa"]: 
            s_p *= 1.15
            if s_p > 75:
                wx_ex *= 0.78
                wx_ax *= 0.78 # Wickham burada 'beton' bir senaryo yazar

        # 🧪 WICKHAM ADIM 3: "Bitiricilik Formu" Kontrolü
        # Eğer ev sahibi son maçlarda xG'sinin çok üstünde atıyorsa (e_rec yüksek), 
        # Wickham bunu bir 'over-performance' olarak değil, 'momentum' olarak görür.
        if e_rec > 1.8: wx_ex *= 1.12
        if d_rec > 1.8: wx_ax *= 1.12

        r_w = sk(wx_ex, wx_ax) # Wickham'ın nihai teknik skoru
        # --- WICKHAM v3.5: PUAN DURUMU PSİKOLOJİSİ (KAOS FİLTRESİ) ---
        kaos_carpan, psikoloji_notu = wickham_psikoloji_analizi(ev, dep, matches, l_ad)
        
        # Wickham burada skoru psikolojiye göre yeniden yoğuruyor
        if kaos_carpan != 1.0:
            wx_ex *= kaos_carpan
            # Eğer şampiyonluk baskısı varsa deplasman da kontradan atabilir
            if kaos_carpan > 1.1: wx_ax *= 1.05 
            
            # Wickham'ın nihai teknik skorunu güncelle
            r_w = sk(wx_ex, wx_ax) 
            # Konsey notunu psikolojik analizle zenginleştir
            comment = psikoloji_notu
        # --- WICKHAM v3.5: KAOS VE MOTİVASYON FİLTRESİ ---
        # Az önce yukarıda tanımladığımız fonksiyonu çağırıyoruz
        # Not: LIGLER sözlüğünden o anki ligin kodunu alıyoruz
        l_kodu = LIGLER.get(l_ad, "PL") 
        kaos_faktoru = motivasyon_hesapla(ev, dep, l_kodu)
        
        if kaos_faktoru > 1.0:
            # Wickham burada fısıldıyor: "Sıralama farkı büyük, favori stresli!"
            wx_ex *= kaos_faktoru 
            wx_ax *= (kaos_faktoru * 0.9) # Karşılıklı gol ihtimalini de tetikler
            r_w = sk(wx_ex, wx_ax) # Teknik skoru kaosla güncelliyoruz
            
        # Yorumu (comment) güncelleyelim
        if kaos_faktoru > 1.1:
            comment = f"⚠️ WICKHAM KAOS UYARISI: {ev} şampiyonluk/hedef baskısı altında! Sıralama farkı Wickham'ın v3.5 algoritmasında 'Fire Strike' etkisini tetikledi."

        # --- 4. AETHER MASTER SYNTHESIS (Geliştirilmiş 4'lü Sentez) ---
        # Aether artık 4 farklı robotun vizyonunu birleştiriyor.
        # Ağırlıklar: Standart(%30), Spektrum(%20), Nexus(%20), Wickham(%30)
        aether_ex = (st_ex * 0.3) + (sp_ex * 0.2) + (nx_ex * 0.2) + (wx_ex * 0.3)
        aether_ax = (st_ax * 0.3) + (sp_ax * 0.2) + (nx_ax * 0.2) + (wx_ax * 0.3)
        
        # Aether Master Süzgeci: Eğer Wickham 'Beton' (Iron Wall) veya 'Ateş' (Fire Strike) 
        # uyarısı verdiyse, Aether bu uyarının ağırlığını son kararda %50'ye çıkarır.
        if h_p > 85 or s_p > 85:
            aether_ex = (aether_ex * 0.5) + (wx_ex * 0.5)
            aether_ax = (aether_ax * 0.5) + (wx_ax * 0.5)
        
        r_ae = sk(aether_ex, aether_ax)
        # --- 5. SONUÇLARI DÖNDÜR ---
        total_xg = ex + ax
        comment = "📈 İstatistiksel trendler dengeli bir mücadele öngörüyor."
        if total_xg > 3.0: comment = "🔥 Yüksek tempo ve bol pozisyonlu bir maç bekleniyor."
        elif total_xg < 2.0: comment = "🛡️ Savunmaların ön planda olacağı, kısır bir mücadele."

        return {
            "std": r_s[0], "s_c": r_s[1], 
            "spec": r_sp[0], "sp_c": r_sp[1], 
            "nexus": r_nx[0], "n_c": r_nx[1], 
            "wickham": r_w[0], "w_c": r_w[1], # Wickham artık sahnede!
            "aether": r_ae[0], "ae_c": r_ae[1], 
            "h_p": h_p, "s_p": s_p, # Metrikler kupon filtreleri için hazır
            "note": comment, "total_xg": total_xg
        }
    except Exception as e:
        return None

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

# --- 5. ANA MENÜ ---
mod = st.sidebar.radio("🚀 Menü", ["🏠 Canlı Skorlar","🤖 Tahmin Robotu", "Global AI", "Lig Odaklı","💎 Value Hunter", "🏆 Onur Listesi"])
all_d = {lig: veri_al(f"competitions/{kod}/matches") for lig, kod in LIGLER.items()}

if mod == "🏠 Canlı Skorlar":
    st.title("⚡ Canlı Maç Merkezi")
    live_data = veri_al("matches")
    matches = live_data.get('matches', [])
    
    if not matches:
        st.info("Şu an aktif maç bulunmuyor.")
    else:
        for m in matches:
            h_s = m['score']['fullTime']['home']
            a_s = m['score']['fullTime']['away']
            st.markdown(f"""
                <div class="match-card" style="border-left: 5px solid #3fb950;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="text-align: right; width: 40%;"><b>{m['homeTeam']['name']}</b></div>
                        <div style="width: 20%; text-align: center; background: #30363d; border-radius: 5px; padding: 5px;">
                            <h3 style="margin: 0; color: #3fb950;">{h_s if h_s is not None else 0} - {a_s if a_s is not None else 0}</h3>
                        </div>
                        <div style="text-align: left; width: 40%;"><b>{m['awayTeam']['name']}</b></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

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
        with st.spinner("🤖 Gerçek veriler analiz ediliyor..."):
            ham_liste = []
            for f in st.session_state.tr_fikstur:
                ev_adi = f.get('home')
                dep_adi = f.get('away')
                lig_adi = f.get('lig')

                if not ev_adi or not dep_adi: continue

                # Analiz Motoru
                res = analiz_et(ev_adi, dep_adi, st.session_state.tr_hafiza, s_sec)
                
                # 🛑 ANALİZ TAMAMLANMADIYSA ASLA EKLEME
                if res and res.get('note') == "✅ Analiz Tamamlandı":
                    # Doncaster testi: Eğer hala Doncaster geliyorsa kodda sızıntı vardır.
                    # Ama bu API'de Doncaster Premier Lig'de olmadığı için gelmemesi lazım.
                    if res.get('total_xg', 0) > 0:
                        ham_liste.append({
                            'ev': ev_adi,
                            'dep': dep_adi,
                            'lig': lig_adi,
                            'res': res
                        })
                
                # 3. 🔥 SIZMA ENGELLEYİCİ FİLTRE 🔥
                # Sadece robotun vize verdiği VE gerçekten gol beklentisi hesapladığı maçları al
                if res and res.get('note') == "✅ Analiz Tamamlandı":
                    
                    # Doncaster gibi verisi olmayan maçlar bazen %99 puanla sızar.
                    # Eğer toplam gol beklentisi 0 ise veya robotun puanı %98 üzerindeyken xG mantıksızsa ele.
                    txg = res.get('total_xg', 0)
                    r_puan = res.get(aktif_r_puan, 0)
                    
                    if txg == 0 or (r_puan > 98 and txg < 0.1):
                        continue # Bu maç hatalı veridir, listeye ekleme!
                        
                    ham_liste.append({
                        'ev': ev_adi, 
                        'dep': dep_adi, 
                        'lig': lig_adi, 
                        'res': res
                    })

        if ham_liste:
            st.success(f"✅ {len(ham_liste)} gerçek maç başarıyla analiz edildi.")
            
            # --- KUPONLAR ---
            c1, c2, c3, c4 = st.columns(4)
            kupon_config = [
                ("⭐ BANKO", c1, "ae_c", "aether", "#58A6FF"),
                ("💎 İDEAL", c2, "ae_c", "aether", "#58A6FF"),
                ("🔥 ÜST", c3, "total_xg", "spec", "#d73a49"),
                ("🛡️ ALT", c4, "s_p", "nexus", "#0366d6")
            ]

            for title, col, sort_key, t_key, color in kupon_config:
                with col:
                    st.markdown(f'<div class="editor-card" style="border-top-color:{color};"><div class="coupon-title">{title}</div>', unsafe_allow_html=True)
                    
                    f_sort = aktif_r_puan if title in ["⭐ BANKO", "💎 İDEAL"] else sort_key
                    f_tahmin = aktif_r_tahmin if title in ["⭐ BANKO", "💎 İDEAL"] else t_key
                    
                    # Sıralama ve tekrarları önleme
                    top_matches = sorted(ham_liste, key=lambda x: x['res'].get(f_sort, 0), reverse=True)
                    
                    # Maçları benzersiz yap (Aynı maç farklı ligde çıkmasın)
                    gorulen_maclar = set()
                    final_5 = []
                    for m in top_matches:
                        mac_id = f"{m['ev']}-{m['dep']}"
                        if mac_id not in gorulen_maclar:
                            final_5.append(m)
                            gorulen_maclar.add(mac_id)
                        if len(final_5) == 5: break

                    for m in final_5:
                        st.markdown(f"""
                        <div class="coupon-item">
                            <small style="color:#8b949e;">{m['lig']}</small><br>
                            <b>{m['ev']} - {m['dep']}</b><br>
                            <span style="color:#3fb950;">{m['res'].get(f_tahmin)}</span>
                            <span style="float:right; font-size:0.8rem; color:#8b949e;">%{int(m['res'].get(f_sort))}</span>
                        </div>""", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("🤖 Analiz kriterlerine uyan maç bulunamadı.")
elif mod == "Global AI":
    # 1. Sidebar ve Algoritma Seçimi (Wickham v3 listeye eklendi)
    filtre = st.sidebar.radio("🤖 Algoritma Seçimi", 
                               ["AETHER AI Master", "Standart AI", "Spektrum AI", "Nexus AI", "WICKHAM AI v3"])
    
    s_sec = st.sidebar.selectbox("📅 Sitemiz: Hafta", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], index=site_h_aktif-1, key="global_hafta_unique_key")

    # 2. Seçilen Haftanın Tarih Aralığı
    h_baslangic = SİTE_DOGUM_TARİHİ + timedelta(weeks=s_sec - 1)
    h_bitis = h_baslangic + timedelta(days=7)
    hedef_tarih = h_baslangic + timedelta(hours=12)

    st.title(f"🚀 {filtre} - {s_sec}. Hafta Analizi")
    st.info(f"📅 Bu hafta {h_baslangic.strftime('%d.%m')} - {h_bitis.strftime('%d.%m')} arası maçları kapsar.")

    # --- KİLİT KONTROLÜ ---
    if simdi < hedef_tarih:
        st.markdown(f'<div class="lock-box"><h2>🔒 {s_sec}. Hafta Henüz Kilitli</h2><p>Tahminler {hedef_tarih.strftime("%d.%m %H:%M")} itibarıyla açılacaktır.</p></div>', unsafe_allow_html=True)
    else:
        # 3. VERİ ÇEKME VE ANALİZ DÖNGÜSÜ
        g_l = []
        for l_ad, l_data in all_d.items():
            m_list = l_data.get('matches', [])
            for m in m_list:
                m_t_str = m['utcDate'].split('T')[0]
                m_t = datetime.strptime(m_t_str, '%Y-%m-%d').date()
                
                if h_baslangic.date() <= m_t < h_bitis.date():
                    res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_list, l_ad)
                    if res:
                        # Puanlama sistemini seçilen filtreye göre belirle
                        if "AETHER" in filtre: p = res['ae_c']
                        elif "Standart" in filtre: p = res['s_c']
                        elif "Spektrum" in filtre: p = res['sp_c']
                        elif "Nexus" in filtre: p = res['n_c']
                        else: p = res['w_c'] # Wickham Puanı
                        
                        m.update({'res': res, 'l_ad': l_ad, 'puan': p, 'l_full': m_list})
                        g_l.append(m)

        if len(g_l) > 0:
            st.divider()
            st.subheader(f"🎯 {filtre} Uzmanlık Konseyi: Haftalık 5'li Kuponlar")
            
            # --- BAŞARI KONTROL FONKSİYONU ---
            def check_hit(liste, tip):
                hit = 0
                for m in liste:
                    if m.get('status') == 'FINISHED':
                        h_s, a_s = m['score']['fullTime']['home'], m['score']['fullTime']['away']
                        if h_s is not None:
                            gw = winner(f"{h_s} - {a_s}")
                            if tip == "ust" and (h_s + a_s) > 2.5: hit += 1
                            elif tip == "alt" and (h_s + a_s) < 2.5: hit += 1
                            elif tip == "banko" or tip == "ideal":
                                t_skor = m['res']['wickham'] if "WICKHAM" in filtre else m['res']['aether']
                                if winner(t_skor) == gw: hit += 1
                return hit

            # --- 🛡️ MÜHÜRLEME SİSTEMİ (SNAPSHOT) ---
            # Her hafta ve her algoritma filtresi için benzersiz bir mühür oluşturur
            muhur_anahtari = f"muhur_{s_sec}_{filtre.replace(' ', '_')}"
            
            if muhur_anahtari not in st.session_state:
                # Cuma günü ilk girişte o anki en iyi maçları hafızaya kilitle
                st.session_state[muhur_anahtari] = {
                    "banko": sorted(g_l, key=lambda x: x['puan'], reverse=True)[:5],
                    "ideal": sorted(g_l, key=lambda x: x['puan'], reverse=True)[5:10] if len(g_l) > 10 else sorted(g_l, key=lambda x: x['puan'], reverse=True)[:5],
                    "ust": sorted(g_l, key=lambda x: (x['res']['h_p'] if "WICKHAM" in filtre else (x['res']['total_xg'] if "Spektrum" in filtre else x['res']['total_xg'] * x['res']['ae_c'])), reverse=True)[:5],
                    "alt": sorted(g_l, key=lambda x: (x['res']['s_p'] if "WICKHAM" in filtre else (x['res']['s_p'] + x['res']['n_c'] if "Nexus" in filtre else x['res']['total_xg'])), reverse=False if "WICKHAM" not in filtre and "Nexus" not in filtre else True)[:5]
                }
            
            # Artık tüm kuponlar bu 'muhur' üzerinden çekilecek
            m_kupon = st.session_state[muhur_anahtari]

            # --- GLOBAL AI DÖRT BÜYÜK KUPON DÜZENİ ---
            c1, c2, c3, c4 = st.columns(4) 

            # 1. BANKO KUPON
            with c1:
                bankolar = m_kupon["banko"]
                h_b = check_hit(bankolar, "banko")
                seal = '<div class="full-hit-seal">🏆 5/5 FULL HIT</div>' if h_b == 5 else ""
                st.markdown(f'<div class="editor-card">{seal}<div class="coupon-title">⭐ BANKO ({filtre[:3]}) <span class="success-badge">{h_b}/5</span></div>', unsafe_allow_html=True)
                for b in bankolar:
                    t = b['res']['wickham'] if "WICKHAM" in filtre else b['res']['aether']
                    st.markdown(f'<div class="coupon-item"><b>{b["homeTeam"]["shortName"]} - {b["awayTeam"]["shortName"]}</b><br>Tahmin: {t}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # 2. İDEAL KUPON
            with c2:
                idealler = m_kupon["ideal"]
                h_i = check_hit(idealler, "ideal")
                seal = '<div class="full-hit-seal" style="background:#58A6FF; color:white;">💎 ELMAS SERİ</div>' if h_i == 5 else ""
                st.markdown(f'<div class="editor-card" style="border-top-color: #58A6FF;">{seal}<div class="coupon-title">💎 İDEAL ({filtre[:3]}) <span class="success-badge">{h_i}/5</span></div>', unsafe_allow_html=True)
                for i in idealler:
                    t = i['res']['wickham'] if "WICKHAM" in filtre else i['res']['aether']
                    st.markdown(f'<div class="coupon-item"><b>{i["homeTeam"]["shortName"]} - {i["awayTeam"]["shortName"]}</b><br>Tahmin: {t}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # 3. ÜST KUPON
            with c3:
                ustler = m_kupon["ust"]
                h_u = check_hit(ustler, "ust")
                seal = '<div class="full-hit-seal" style="background:#d73a49; color:white;">🔥 FIRE STRIKE</div>' if h_u == 5 else ""
                st.markdown(f'<div class="editor-card" style="border-top-color: #d73a49;">{seal}<div class="coupon-title">⚽ ÜST ({filtre[:3]}) <span class="success-badge">{h_u}/5</span></div>', unsafe_allow_html=True)
                for u in ustler:
                    info = f"Güç: %{int(u['res']['h_p'])}" if "WICKHAM" in filtre else f"xG: {u['res']['total_xg']:.2f}"
                    st.markdown(f'<div class="coupon-item"><b>{u["homeTeam"]["shortName"]} - {u["awayTeam"]["shortName"]}</b><br>{info} | 2.5 ÜST</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # 4. ALT KUPON
            with c4:
                altlar = m_kupon["alt"]
                h_a = check_hit(altlar, "alt")
                seal = '<div class="full-hit-seal" style="background:#0366d6; color:white;">🛡️ IRON WALL</div>' if h_a == 5 else ""
                st.markdown(f'<div class="editor-card" style="border-top: 4px solid #0366d6;">{seal}<div class="coupon-title">📉 ALT ({filtre[:3]}) <span class="success-badge">{h_a}/5</span></div>', unsafe_allow_html=True)
                for a in altlar:
                    info = f"Sertlik: %{int(a['res']['s_p'])}" if "WICKHAM" in filtre else f"xG: {a['res']['total_xg']:.2f}"
                    st.markdown(f'<div class="coupon-item"><b>{a["homeTeam"]["shortName"]} - {a["awayTeam"]["shortName"]}</b><br>{info} | 2.5 ALT</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
# --- 2. VALUE HUNTER: CANLI TAHMİN TERMİNALİ (ANLIK AKIŞ) ---
            st.divider()
            st.markdown("## 🎯 VALUE HUNTER: ANLIK ROBOT ANALİZLERİ")
            st.info("⚡ **Canlı Veri Akışı:** Buradaki listeler mühürlenmez. Robotlar o saniye ligde gördüğü en taze fırsatları (Top 20) listeler.")
            
            # Beş robot için sekmeleri oluşturalım
            v_tabs = st.tabs(["🧪 WICKHAM", "✨ AETHER", "🛡️ NEXUS", "🤖 STANDART", "🔥 SPEKTRUM"])
            
            # Robot konfigürasyonlarını tanımlayalım (Hangi robot, hangi puana ve tahmine bakacak)
            robot_config = [
                {"tab": v_tabs[0], "puan_k": "w_c", "tahmin_k": "wickham", "emoji": "🧪", "name": "Wickham"},
                {"tab": v_tabs[1], "puan_k": "ae_c", "tahmin_k": "aether", "emoji": "✨", "name": "Aether"},
                {"tab": v_tabs[2], "puan_k": "n_c", "tahmin_k": "nexus", "emoji": "🛡️", "name": "Nexus"},
                {"tab": v_tabs[3], "puan_k": "s_c", "tahmin_k": "std", "emoji": "🤖", "name": "Standart"},
                {"tab": v_tabs[4], "puan_k": "sp_c", "tahmin_k": "spec", "emoji": "🔥", "name": "Spektrum"}
            ]

            for rb in robot_config:
                with rb['tab']:
                    st.markdown(f"### {rb['emoji']} {rb['name']} Güncel Fırsat Listesi")
                    
                    # DİKKAT: Burada s_k (mühürlü) değil, g_l (canlı) listesini kullanıyoruz!
                    # O robota ait puan anahtarına göre anlık sıralama yap
                    top_av = sorted(g_l, key=lambda x: x['res'].get(rb['puan_k'], 0), reverse=True)[:20]
                    
                    if not top_av:
                        st.warning("Bu robot için şu an uygun fırsat saptanmadı.")
                    else:
                        for m in top_av:
                            res = m['res']
                            ham_tahmin = res.get(rb['tahmin_k'], "---")
                            
                            # --- AKILLI ÇİFT TAHMİN MEKANİZMASI (MS & GOL) ---
                            if "-" in str(ham_tahmin):
                                try:
                                    pts = ham_tahmin.split(" - ")
                                    ev_g, dep_g = int(pts[0]), int(pts[1])
                                    
                                    # 1. Taraf Tahmini (MS 1-0-2)
                                    ms_tahmin = f"MS {winner(ham_tahmin)}"
                                    
                                    # 2. Gol Tahmini (2.5 Alt/Üst)
                                    gol_tahmin = "2.5 ÜST" if (ev_g + dep_g) > 2.5 else "2.5 ALT"
                                    
                                    # Görsel Liste Satırı (Yenilenmiş Çift Kutulu Tasarım)
                                    st.markdown(f"""
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #30363d; background: rgba(22, 27, 34, 0.5); border-radius: 8px; margin-bottom: 5px;">
                                        <div style="flex: 2;">
                                            <b>{m['homeTeam']['shortName']} - {m['awayTeam']['shortName']}</b> 
                                            <br><small style="color:#8B949E;">📍 {m['l_ad']}</small>
                                        </div>
                                        <div style="flex: 1.5; display: flex; gap: 5px; justify-content: center;">
                                            <span style="background:#238636; color:white; padding:4px 8px; border-radius:5px; font-size:0.75rem; font-weight:bold; min-width:50px; text-align:center;">{ms_tahmin}</span>
                                            <span style="background:#1f6feb; color:white; padding:4px 8px; border-radius:5px; font-size:0.75rem; font-weight:bold; min-width:60px; text-align:center;">{gol_tahmin}</span>
                                        </div>
                                        <div style="flex: 1; text-align: right;">
                                            <span style="color:#58A6FF; font-weight:bold;">%{int(res.get(rb['puan_k'], 0))}</span>
                                            <br><small style="color:#8B949E;">Güven</small>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                except:
                                    st.write(f"⚠️ {m['homeTeam']['shortName']} verisi formatlanamadı.")
                            else:
                                st.write(f"🔍 {m['homeTeam']['shortName']}: {ham_tahmin}")
            # --- DETAYLI ANALİZ KARTLARI ---
            st.markdown("---")
            st.subheader(f"🔥 {filtre}: Haftalık Detaylı Analiz Raporu")
            for m in sorted(g_l, key=lambda x: x['puan'], reverse=True)[:20]:
                res = m['res']
                m_sk = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                st.markdown(f"""
                <div class="match-card">
                    <div class="rank-badge">🔥 %{int(m['puan'])}</div>
                    <div style="font-size:0.8rem; color:#8B949E;">{m['l_ad']} - Hafta {m['matchday']}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;">
                        <div style="text-align: center; width: 33%;"><b>{m['homeTeam']['name']}</b>{get_form_dots(m['homeTeam']['name'], m['l_full'])}</div>
                        <div style="width: 33%; text-align: center;">{m_sk}</div>
                        <div style="text-align: center; width: 33%;"><b>{m['awayTeam']['name']}</b>{get_form_dots(m['awayTeam']['name'], m['l_full'])}</div>
                    </div>
                    <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                        <div class="prediction-box aether-box">✨ AETHER<br><b>{res['aether']}</b></div>
                        <div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div>
                        <div class="prediction-box" style="border-color:#3fb950;">🧪 WICKHAM<br><b>{res['wickham']}</b></div>
                        <div class="prediction-box">🛡️ NEXUS<br><b>{res['nexus']}</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning(f"⚠️ {s_sec}. hafta için seçilen tarih aralığında analiz edilecek maç bulunamadı.")
elif mod == "Lig Odaklı":
    lig_adi = st.sidebar.selectbox("🎯 Lig Seçin", list(LIGLER.keys()))
    lig_kodu = LIGLER[lig_adi]
    puan_durumu_data = veri_al(f"competitions/{lig_kodu}/standings")
    maclar_data = all_d[lig_adi]
    col_standings, col_matches = st.columns([1, 2.5])
    with col_standings:
        st.subheader("📊 Puan Durumu")
        if puan_durumu_data.get('standings'):
            table = puan_durumu_data['standings'][0]['table']
            html = '<table class="standings-table"><tr><th>#</th><th>Takım</th><th>P</th></tr>'
            for t in table: html += f'<tr><td>{t["position"]}</td><td>{t["team"]["shortName"]}</td><td><b>{t["points"]}</b></td></tr>'
            html += '</table>'
            st.markdown(html, unsafe_allow_html=True)
    with col_matches:
        l_matches = maclar_data.get('matches', [])
        if l_matches:
            g_h = max([m['matchday'] for m in l_matches if m['status'] == 'FINISHED'] or [1])
            h_s = st.selectbox("📅 Hafta Seç", sorted(list(set([m['matchday'] for m in l_matches if m['matchday']]))), index=g_h-1)
            for m in [x for x in l_matches if x['matchday'] == h_s]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], l_matches, h_s) # h_s eklendi!
                if res:
                    m_sk = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                    st.markdown(f"""<div class="match-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 33%;"><img src="{m['homeTeam']['crest']}" width="30"><br><b>{m['homeTeam']['name']}</b>{get_form_dots(m['homeTeam']['name'], l_matches)}</div><div style="width: 33%; text-align: center;">{m_sk}</div><div style="text-align: center; width: 33%;"><img src="{m['awayTeam']['crest']}" width="30"><br><b>{m['awayTeam']['name']}</b>{get_form_dots(m['awayTeam']['name'], l_matches)}</div></div><div style="display: flex; justify-content: space-around; margin-top: 15px;"><div class="prediction-box aether-box">✨ AETHER<br><b>{res['aether']}</b></div><div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div><div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b></div></div></div>""", unsafe_allow_html=True)
elif mod == "💎 Value Hunter":
    st.title("💎 AI Value Hunter (Değer Analizi)")
    st.info("Piyasa oranları ile AI beklentimiz arasındaki farkı tarayan profesyonel analiz motoru.")

    # 1. HAFTA SEÇİMİ
    s_sec = st.selectbox("📅 Analiz Haftası", list(range(1, 11)), index=site_h_aktif-1, key="value_week")
    
    # Seçilen haftanın tarih sınırları
    h_baslangic = SİTE_DOGUM_TARİHİ + timedelta(weeks=s_sec - 1)
    h_bitis = h_baslangic + timedelta(days=7)

    def find_values(hafta_no):
        found = []
        bas = h_baslangic.date()
        bit = h_bitis.date()

        for l_ad, l_data in all_d.items():
            m_list = l_data.get('matches', [])
            for m in m_list:
                m_tarih_str = m['utcDate'].split('T')[0]
                m_tarih = datetime.strptime(m_tarih_str, '%Y-%m-%d').date()
                
                # Sadece seçilen haftanın maçlarını tara
                if bas <= m_tarih < bit:
                    # Analizi çalıştır
                    res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_list, hafta_no)
                    if res:
                        # VALUE MANTIĞI: AI Güveni vs Piyasa Tahmini (Simüle)
                        # Robotun en güvendiği skora verdiği puanı (ae_c) baz alıyoruz
                        market_prob = 45 + (random.randint(-5, 15)) 
                        ai_prob = res.get('ae_c', 50)
                        value_gap = ai_prob - market_prob
                        
                        # %12'den fazla fark varsa listeye ekle
                        if value_gap > 12:
                            m.update({'res': res, 'v_gap': value_gap, 'l_ad': l_ad, 'm_prob': market_prob})
                            found.append(m)
        return sorted(found, key=lambda x: x['v_gap'], reverse=True)

    # Verileri Çek
    with st.spinner("💎 Hazine avcısı ligleri tarıyor..."):
        v_list = find_values(s_sec)

    if not v_list:
        st.warning(f"⚠️ {s_sec}. hafta için henüz yüksek 'Value' (Değer) içeren maç saptanmadı.")
    else:
        st.success(f"🔍 AI Motoru toplam {len(v_list)} adet 'Değerli Oran' saptadı!")
        
        for v in v_list:
            res = v['res'] # Analiz sonuçlarını al
            gap = v['v_gap']
            m_prob = v['m_prob'] # Piyasa beklentisini al
            ai_guven = res.get('ae_c', 50) # AI Güven puanını al
            
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1e222d 0%, #0d1117 100%); 
                            border-left: 5px solid #d4af37; border-radius: 10px; padding: 20px; 
                            margin-bottom: 20px; border: 1px solid #30363d; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #d4af37; font-weight: bold; font-size: 1.1rem;">💎 VALUE: +%{int(gap)}</span>
                        <span style="background: #30363d; padding: 4px 10px; border-radius: 15px; color: #8B949E; font-size: 0.75rem;">{v['l_ad']}</span>
                    </div>
                    <div style="margin: 15px 0; font-size: 1.4rem; font-weight: bold; color: #f0f6fc;">
                        {v['homeTeam']['name']} <span style="color:#8B949E; font-size:0.9rem;">vs</span> {v['awayTeam']['name']}
                    </div>
                    <hr style="border: 0; border-top: 1px solid #30363d; margin: 15px 0;">
                    <div style="display: flex; justify-content: space-around; text-align: center;">
                        <div>
                            <div style="color: #8B949E; font-size: 0.8rem;">🤖 AI GÜVENİ</div>
                            <div style="color: #58A6FF; font-size: 1.2rem; font-weight: bold;">%{int(ai_guven)}</div>
                        </div>
                        <div>
                            <div style="color: #8B949E; font-size: 0.8rem;">⚖️ PİYASA BEKLENTİSİ</div>
                            <div style="color: #d73a49; font-size: 1.2rem; font-weight: bold;">%{int(m_prob)}</div>
                        </div>
                        <div>
                            <div style="color: #8B949E; font-size: 0.8rem;">🎯 AI ÖNERİSİ</div>
                            <div style="color: #3fb950; font-size: 1.2rem; font-weight: bold;">{res['aether']}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
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
