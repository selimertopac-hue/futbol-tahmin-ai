import streamlit as st
import json
import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

# --- 1. AYARLAR & FOOTYSTATS PREMIUM MİHRAKI ---
FS_API_KEY = "3d8f931eb334529f5c171f08dbeed729fe2b0e7f49f717574101ff79225d4aa7"
FS_BASE_URL = "https://api.football-data-api.com"

SİTE_DOGUM_TARİHİ = datetime(2026, 2, 20) 
ARSIV_DOSYASI = "ai_arsiv.json"
VERİ_BANKASI_DOSYASI = "msi_futbol_bankasi.json"
BULTEN_DOSYASI = "msi_bulten_bankasi.json"

st.set_page_config(page_title="UltraSkor Pro: Titan Sentez Lab", page_icon="🔬", layout="wide")

# --- 2. GÖRSEL STİL (MSI DARK MODE) ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; position: relative; }
    .coupon-item { background: #0d1117; padding: 8px; margin-top: 8px; border-radius: 6px; border: 1px solid #30363d; font-size: 0.85rem; }
    .stat-box { background: #21262d; padding: 10px; border-radius: 8px; border: 1px solid #30363d; text-align: center; }
    h1, h2, h3, h4 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FOOTYSTATS STANDART GET MOTORU ---
def fs_api_get(endpoint, params={}):
    params['key'] = FS_API_KEY
    url = f"{FS_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 🏗️ YARDIMCI ARAÇLAR ---
def winner(skor_metni):
    try:
        if not skor_metni or " - " not in skor_metni: return "X"
        parcalar = skor_metni.split(" - ")
        ev, dep = int(parcalar[0]), int(parcalar[1])
        if ev > dep: return "1"
        if dep > ev: return "2"
        return "X"
    except: return "X"

# --- 🏆 50 ELİT & PROFESYONEL LİG: KESİN GÜMRÜK LİSTESİ ---
HEDEF_LIGLER = [
    "Austria Bundesliga", "Austria 2. Liga", "Belgium Pro League", "Belgium First Division B",
    "Bosnia and Herzegovina Premier League", "Bosnia and Herzegovina First League", "China Chinese Super League", 
    "Croatia Prva HNL", "Czech Republic First League", "Czech Republic FNL", "Denmark Superliga", "Denmark 1st Division",
    "England Premier League", "England Championship", "England EFL League One", "England EFL League Two",
    "Finland Veikkausliiga", "Finland Ykkösliiga", "France Ligue 1", "France Ligue 2", "Germany Bundesliga", "Germany 2. Bundesliga",
    "Hungary NB I", "Italy Serie A", "Italy Serie B", "Netherlands Eredivisie", "Netherlands Eerste Divisie",
    "Norway Eliteserien", "Norway First Division", "Poland Ekstraklasa", "Poland 1. Liga", "Portugal Liga NOS", "Portugal LigaPro",
    "Romania Liga I", "Scotland Premiership", "Serbia SuperLiga", "Slovakia Super Liga", "Slovakia 2. Liga",
    "Slovenia PrvaLiga", "Slovenia 2. SNL", "Spain La Liga", "Spain Segunda División", "Sweden Allsvenskan", "Sweden Superettan",
    "Switzerland Super League", "Switzerland Challenge League", "Turkey Süper Lig", "Turkey 1. Lig", "USA MLS", "USA USL Championship"
]

def lig_bilgi_bankasi_olustur():
    res = fs_api_get("league-list")
    if not res or not res.get('success'): return {}
    ligler = {}
    for lig in res.get('data', []):
        c_ad = lig.get('country', '')
        l_ad = lig.get('league_name') or lig.get('name', '')
        tam_ad = f"{c_ad} {l_ad}"
        if any(hedef.lower() in tam_ad.lower() for hedef in HEDEF_LIGLER):
            if 'season' in lig and len(lig['season']) > 0:
                ligler[str(lig['season'][-1]['id'])] = tam_ad
    return ligler

# --- HAFTA HESAP MOTORU ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1
hafta_listesi = list(range(1, max(15, site_h_aktif + 2)))
default_index = min(site_h_aktif - 1, len(hafta_listesi) - 1)

st.sidebar.title("🛡️ MSI Operasyon Merkezi")
st.sidebar.subheader("📅 Analiz Vizörü")
hafta_secim = st.sidebar.selectbox("Tahmin Haftası", hafta_listesi, index=default_index)

HAFTA_BASLANGIC_TARIHI = SİTE_DOGUM_TARİHİ + timedelta(weeks=hafta_secim - 1)
HAFTA_BITIS_TARIHI = HAFTA_BASLANGIC_TARIHI + timedelta(days=7)
CUMA_SINIR = HAFTA_BASLANGIC_TARIHI.timestamp()
PAZARTESI_SINIR = HAFTA_BITIS_TARIHI.timestamp()

# --- 🔬 DEEP DATA HARVESTER ---
def derin_bulten_hasat_et():
    lig_sozlugu = lig_bilgi_bankasi_olustur()
    if not lig_sozlugu: return []
    
    yeni_bulten = []
    for s_id, l_tam_ad in lig_sozlugu.items():
        res = fs_api_get("league-matches", params={'league_id': s_id, 'status': 'incomplete'})
        if res and 'data' in res:
            for m in res['data']:
                mac_tarihi = int(m.get('date_unix', 0))
                if CUMA_SINIR <= mac_tarihi <= PAZARTESI_SINIR:
                    yeni_bulten.append({
                        'id': m.get('id'),
                        'home_name': m.get('home_name'),
                        'away_name': m.get('away_name'),
                        'league_name': l_tam_ad,
                        'date_unix': mac_tarihi,
                        'team_a_xg_prematch': float(m.get('team_a_xg_prematch', 1.5)),
                        'team_b_xg_prematch': float(m.get('team_b_xg_prematch', 1.2)),
                        'pre_match_teamA_overall_ppg': float(m.get('pre_match_teamA_overall_ppg', 1.0)),
                        'pre_match_teamB_overall_ppg': float(m.get('pre_match_teamB_overall_ppg', 1.0)),
                        'shot_conversion_rate_home': float(m.get('shot_conversion_rate_home', 10.0)),
                        'shot_conversion_rate_away': float(m.get('shot_conversion_rate_away', 10.0)),
                        'homeAttackAdvantagePercentage': float(m.get('homeAttackAdvantagePercentage', 0.0)),
                        'homeDefenceAdvantagePercentage': float(m.get('homeDefenceAdvantagePercentage', 0.0)),
                        'points_dropped_from_winning_positions_home': m.get('points_dropped_from_winning_positions_home', 0),
                        'seasonAVG_away': float(m.get('seasonAVG_away', 1.0)),
                        'seasonConcededAVG_away': float(m.get('seasonConcededAVG_away', 1.0)),
                        'o15_potential': int(m.get('o15_potential', 50)),
                        'o25_potential': int(m.get('o25_potential', 50)),
                        'btts_potential': int(m.get('btts_potential', 50)),
                        'corners_potential': float(m.get('corners_potential', 9.0)),
                        'cards_potential': float(m.get('cards_potential', 4.0)),
                        'fhg_o05_potential': int(m.get('fhg_o05_potential', 40)),
                        'status': 'incomplete'
                    })
    if yeni_bulten:
        with open(BULTEN_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(yeni_bulten, f, ensure_ascii=False, indent=4)
    return yeni_bulten

def derin_gecmis_hasat_et():
    lig_sozlugu = lig_bilgi_bankasi_olustur()
    if not lig_sozlugu: return 0
    mevcut_arsiv = []
    if os.path.exists(VERİ_BANKASI_DOSYASI):
        with open(VERİ_BANKASI_DOSYASI, "r", encoding="utf-8") as f:
            try: mevcut_arsiv = json.load(f)
            except: mevcut_arsiv = []
    kayitli_idlar = {m.get('id') for m in mevcut_arsiv}
    yeni_sayac = 0
    for s_id, l_tam_ad in lig_sozlugu.items():
        res = fs_api_get("league-matches", params={'league_id': s_id, 'status': 'complete'})
        if res and 'data' in res:
            for m in res['data']:
                if m.get('id') not in kayitli_idlar:
                    # Gelişmiş veri analizi uyumluluğu için veri türlerini normalize ediyoruz
                    m['league_name'] = l_tam_ad
                    m['team_a_xg_prematch'] = float(m.get('team_a_xg_prematch' or 1.5))
                    m['team_b_xg_prematch'] = float(m.get('team_b_xg_prematch' or 1.2))
                    m['homeGoalCount'] = int(m.get('homeGoalCount' or 0))
                    m['awayGoalCount'] = int(m.get('awayGoalCount' or 0))
                    m['btts_potential'] = int(m.get('btts_potential' or 50))
                    m['o25_potential'] = int(m.get('o25_potential' or 50))
                    m['shot_conversion_rate_home'] = float(m.get('shot_conversion_rate_home' or 10.0))
                    m['seasonConcededAVG_away'] = float(m.get('seasonConcededAVG_away' or 1.2))
                    mevcut_arsiv.append(m)
                    kayitli_idlar.add(m.get('id'))
                    yeni_sayac += 1
    if yeni_sayac > 0:
        with open(VERİ_BANKASI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(mevcut_arsiv, f, ensure_ascii=False, indent=4)
    return yeni_sayac

# --- 🧪 TITAN COUNCIL v19.5 ANALİZ MOTORU ---
def skor_olasigi_hesapla(e, a, carpan=400):
    matrix = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
    s = np.unravel_index(np.argmax(matrix), matrix.shape)
    conf = int(matrix[s] * carpan)
    return {"skor": f"{s[0]} - {s[1]}", "conf": conf}

def titan_council_v19_5(m):
    try:
        h_xg = float(m.get('team_a_xg_prematch') or 1.45)
        a_xg = float(m.get('team_b_xg_prematch') or 1.15)
        h_ppg = float(m.get('pre_match_teamA_overall_ppg') or 1.2)
        h_conv = float(m.get('shot_conversion_rate_home') or 10.0)
        h_att_adv = float(m.get('homeAttackAdvantagePercentage') or 5.0)

        st_h = h_xg * (1 + (h_att_adv / 150)) * h_ppg
        st_a = a_xg * 0.95
        res_st = skor_olasigi_hesapla(st_h, st_a, 380)

        sp_h, sp_a = h_xg, a_xg
        if (h_xg + a_xg) > 2.7: sp_h *= 1.22; sp_a *= 1.18
        res_sp = skor_olasigi_hesapla(sp_h, sp_a, 350)

        nx_h, nx_a = h_xg, a_xg
        if h_ppg > 1.9: nx_h *= 0.88; nx_a *= 1.15
        res_nx = skor_olasigi_hesapla(nx_h, nx_a, 360)

        wx_h = (h_xg * (15 / max(5, h_conv)))
        wx_a = a_xg
        res_wx = skor_olasigi_hesapla(wx_h, wx_a, 420)

        ae_h = (st_h * 0.30) + (wx_h * 0.40) + (sp_h * 0.15) + (nx_h * 0.15)
        ae_a = (st_a * 0.30) + (wx_a * 0.40) + (sp_a * 0.15) + (nx_a * 0.15)
        res_ae = skor_olasigi_hesapla(ae_h, ae_a, 400)

        return {
            "skor": res_ae['skor'], "guven": res_ae['conf'], "xg": ae_h + ae_a,
            "ae_res": res_ae, "st_res": res_st, "sp_res": res_sp, "nx_res": res_nx, "wx_res": res_wx
        }
    except: return None

if 'bulten_verileri' not in st.session_state:
    if os.path.exists(BULTEN_DOSYASI):
        with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
            try: st.session_state.bulten_verileri = json.load(f)
            except: st.session_state.bulten_verileri = []
    else: st.session_state.bulten_verileri = []

# --- 5. NAVİGASYON PANELİ ---
mod = st.sidebar.radio("🚀 Menü", ["🤖 Tahmin Robotu", "Global AI", "🔬 Titan Sentez Laboratuvarı", "📚 Kupon Arşivi", "📂 JSON Veri Merkezi"], key="main_menu")

# --- 6. SENSEZ SAYFA MODLARI TASARIMI ---

if mod == "🤖 Tahmin Robotu":
    st.title(f"🚀 Titan v19.7: {hafta_secim}. Hafta Mühürlü Kuponları")
    bulten_havuzu = []
    for m in st.session_state.bulten_verileri:
        res = titan_council_v19_5(m)
        if res:
            m['c_res'] = res
            m['avg_conf'] = res['guven']
            bulten_havuzu.append(m)
            
    if bulten_havuzu:
        sirali_havuz = sorted(bulten_havuzu, key=lambda x: x['avg_conf'], reverse=True)
        k_cols = st.columns(4)
        kupon_tipleri = [
            {"ad": "💎 ELMAS KUPON", "renk": "#FFD700"}, {"ad": "🥇 ALTIN KUPON", "renk": "#C0C0C0"},
            {"ad": "🥈 GÜMÜŞ KUPON", "renk": "#CD7F32"}, {"ad": "🎖️ BRONZ KUPON", "renk": "#8A2BE2"}
        ]
        for i, k_ayar in enumerate(kupon_tipleri):
            with k_cols[i]:
                st.markdown(f"<h4 style='color:{k_ayar['renk']}; text-align:center;'>{k_ayar['ad']}</h4>", unsafe_allow_html=True)
                kupon_maclari = sirali_havuz[i*5 : (i+1)*5] if len(sirali_havuz) >= 20 else sirali_havuz
                for match in kupon_maclari:
                    karar = "2.5 ÜST" if match['c_res']['xg'] > 2.6 else f"MS {winner(match['c_res']['skor'])}"
                    st.markdown(f"""
                        <div class="match-card" style="border-right: 4px solid {k_ayar['renk']}; padding:10px; margin-bottom:5px; font-size:0.8rem; background:#0d1117;">
                            <small style='color:#8B949E;'>{match.get('league_name', '')[:18]}</small><br>
                            <b>{match['home_name'][:12]} - {match['away_name'][:12]}</b><br>
                            <span style='color:{k_ayar['renk']}; font-weight:bold;'>{karar}</span> (%{int(match['avg_conf'])})
                        </div>""", unsafe_allow_html=True)
                if st.button(f"Mühürle", key=f"btn_k_{i}"):
                    pass

        st.divider()
        st.subheader("🌐 Konsey Ortak Karar Terminali (En İyi 20 Fırsat)")
        tab_taraf, tab_gol = st.tabs(["🎯 En İyi 20 Taraf Bahsi (1X2)", "⚽ En İyi 20 Alt/Üst Bahsi"])
        with tab_taraf:
            taraf_20 = sirali_havuz[:20]
            t_col1, t_col2 = st.columns(2)
            for idx, m in enumerate(taraf_20):
                with t_col1 if idx % 2 == 0 else t_col2:
                    st.markdown(f"""
                        <div class="match-card" style="border-left: 4px solid #58A6FF; padding:10px;">
                            <small style='color:#8B949E;'>{m.get('league_name')}</small>
                            <div style="display:flex; justify-content:space-between;">
                                <b>{m['home_name']} - {m['away_name']}</b>
                                <span style="color:#58A6FF; font-weight:bold;">{m['c_res']['skor']}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)
        with tab_gol:
            gol_20 = sorted(bulten_havuzu, key=lambda x: abs(x['c_res']['xg'] - 2.5), reverse=True)[:20]
            g_col1, g_col2 = st.columns(2)
            for idx, m in enumerate(gol_20):
                with g_col1 if idx % 2 == 0 else g_col2:
                    gol_tip = "2.5 ÜST" if m['c_res']['xg'] > 2.5 else "2.5 ALT"
                    st.markdown(f"""
                        <div class="match-card" style="border-right: 4px solid #3fb950; padding:10px;">
                            <small style='color:#8B949E;'>{m.get('league_name')}</small>
                            <div style="display:flex; justify-content:space-between;">
                                <b>{m['home_name']} - {m['away_name']}</b>
                                <span style="color:#3fb950; font-weight:bold;">⚽ {gol_tip} (xG: {m['c_res']['xg']:.2f})</span>
                            </div>
                        </div>""", unsafe_allow_html=True)
    else:
        st.warning("🔎 Ambar boş. Lütfen 'JSON Veri Merkezi' sekmesinden bülteni hasat edin.")

elif mod == "Global AI":
    st.title(f"🚀 Global AI Düzeni — {hafta_secim}. Hafta Analizi")
    filtre = st.sidebar.radio("🤖 Algoritma Seçimi", ["AETHER AI Master", "Standart AI", "Spektrum AI", "Nexus AI", "WICKHAM AI v3"])
    if st.session_state.bulten_verileri:
        g_l, deneme_bolgesi = [], []
        for m in st.session_state.bulten_verileri:
            res = titan_council_v19_5(m)
            if res:
                m_copy = m.copy()
                m_copy['res'] = res
                if res['guven'] >= 75: g_l.append(m_copy)
                else: deneme_bolgesi.append(m_copy)
        tabs = st.tabs(["🏆 Ana Kuponlar", "🔬 Deneme Bölgesi (Yüksek Güvenli Ek Maçlar)"])
        with tabs[0]:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🎯 Taraf Seçimleri")
                for match in g_l[:5]:
                    st.markdown(f'<div class="coupon-item"><b>{match.get("home_name")} - {match.get("away_name")}</b><br>Konsey: {match["res"]["skor"]}</div>', unsafe_allow_html=True)
            with c2:
                st.subheader("⚽ Gol Seçimleri")
                for match in g_l[5:10]:
                    st.markdown(f'<div class="coupon-item"><b>{match.get("home_name")} - {match.get("away_name")}</b><br>Sentez xG: {match["res"]["xg"]:.2f}</div>', unsafe_allow_html=True)
        with tabs[1]:
            st.subheader("🔬 Deneme Bölgesi Maç Havuzu")
            d_cols = st.columns(2)
            for idx, match in enumerate(deneme_bolgesi[:10]):
                with d_cols[idx % 2]:
                    st.markdown(f"""
                        <div class="match-card" style="background: rgba(48, 54, 61, 0.2); border: 1px dashed #8B949E; padding: 10px;">
                            <b>{match['home_name']} - {match['away_name']}</b> | <small>{match.get('league_name')[:20]}</small><br>
                            <small>Tahmin: {match['res']['skor']} (Güven: %{match['res']['guven']})</small>
                        </div>""", unsafe_allow_html=True)

# --- 🔬 ENTEGRE EDİLEN YENİ "TİTAN SENTEZ LABORATUVARI" ---
elif mod == "🔬 Titan Sentez Laboratuvarı":
    st.title("🔬 Titan Sentez Laboratuvarı v1.0")
    st.subheader("🕵️ Özelleştirilmiş Matematiksel Korelasyon Odası")
    st.caption("Geçmiş veri bankasındaki binlerce bitmiş maçı filtreleyerek kendi teorilerini test et ve simülasyona zemin hazırla.")

    if not os.path.exists(VERİ_BANKASI_DOSYASI):
        st.warning("⚠️ Laboratuvarın çalışması için geçmiş maç verisi gerekiyor. Lütfen önce JSON Veri Merkezi'nden 'Pazartesi Hasadı' yapın.")
    else:
        with open(VERİ_BANKASI_DOSYASI, "r", encoding="utf-8") as f:
            arsiv_verileri = json.load(f)
            
        df_arsiv = pd.DataFrame(arsiv_verileri)
        
        # Kullanılabilir benzersiz lig listesini gümrük listesine göre ayıkla
        mevcut_ligler = sorted(list(df_arsiv['league_name'].unique()))
        
        st.markdown("### 🗺️ Sentez Filtre Paneli")
        
        # --- LİG SEÇİM PANELİ (Ayrı ayrı, kimisini ya da hepsini seçme altyapısı) ---
        lig_secim_modu = st.radio("Lig Filtreleme Düzeni", ["Tüm Elit Ligleri Kapsa", "Özel Lig Grupları Seç"], horizontal=True)
        if lig_secim_modu == "Özel Lig Grupları Seç":
            secilen_ligler = st.multiselect("Analiz Edilecek Ligleri Seçin", mevcut_ligler, default=mevcut_ligler[:3])
        else:
            secilen_ligler = mevcut_ligler

        st.write("---")
        c_filt1, c_filt2, c_filt3 = st.columns(3)
        
        with c_filt1:
            st.markdown("##### 📈 Hücum ve Maç Öncesi xG Sınırları")
            min_home_xg = st.slider("Minimum Ev Sahibi xG (Pre-Match)", 0.0, 3.5, 1.8, step=0.1)
            max_away_xg = st.slider("Maksimum Deplasman xG (Pre-Match)", 0.0, 3.5, 1.3, step=0.1)
            
        with c_filt2:
            st.markdown("##### ⚽ Yüzdesel İhtimal ve Baremler")
            min_btts_pot = st.slider("Minimum KG Var Potansiyeli (%)", 0, 100, 65, step=5)
            min_o25_pot = st.slider("Minimum 2.5 Üst Potansiyeli (%)", 0, 100, 60, step=5)
            
        with c_filt3:
            st.markdown("##### 🧪 Ekstrem Performans Kriterleri")
            min_home_conv = st.slider("Min Ev Şut/Gol Dönüşüm Oranı (%)", 0.0, 25.0, 11.5, step=0.5)
            max_away_conceded = st.slider("Max Dep Gol Yeme Ortalaması", 0.0, 3.5, 1.4, step=0.1)

        # --- VERİ BAĞLAMA VE SORGULAMA MOTORU ---
        # Seçilen lig filtrelemesi
        df_filtreli = df_arsiv[df_arsiv['league_name'].isin(secilen_ligler)]
        
        # Rakamsal koşulları birbirine 'AND' mantığıyla bağlıyoruz
        df_filtreli = df_filtreli[
            (df_filtreli['team_a_xg_prematch'] >= min_home_xg) &
            (df_filtreli['team_b_xg_prematch'] <= max_away_xg) &
            (df_filtreli['btts_potential'] >= min_btts_pot) &
            (df_filtreli['o25_potential'] >= min_o25_pot) &
            (df_filtreli['shot_conversion_rate_home'] >= min_home_conv) &
            (df_filtreli['seasonConcededAVG_away'] >= max_away_conceded)
        ]
        
        st.divider()
        st.markdown("### 📊 Sentez Sonuç Karnesi")
        
        toplam_eslesen = len(df_filtreli)
        
        if toplam_eslesen == 0:
            st.info("🔎 Girdiğiniz ağır teorik kriterlere uyan geçmiş maç bulunamadı. Sürgüleri biraz esnetmeyi deneyin.")
        else:
            # İstatistiksel başarı oranlarının otonom hesabı
            btts_count = len(df_filtreli[(df_filtreli['homeGoalCount'] > 0) & (df_filtreli['awayGoalCount'] > 0)])
            o25_count = len(df_filtreli[(df_filtreli['homeGoalCount'] + df_filtreli['awayGoalCount']) > 2.5])
            ms1_count = len(df_filtreli[df_filtreli['homeGoalCount'] > df_filtreli['awayGoalCount']])
            
            p_btts = (btts_count / toplam_eslesen) * 100
            p_o25 = (o25_count / toplam_eslesen) * 100
            p_ms1 = (ms1_count / toplam_eslesen) * 100
            
            c_res1, c_res2, c_res3, c_res4 = st.columns(4)
            with c_res1:
                st.metric("📋 Eşleşen Maç Sayısı", toplam_eslesen)
            with c_res2:
                st.metric("🔥 2.5 Üst Başarısı", f"%{p_o25:.1f}", f"{o25_count} Maç")
            with c_res3:
                st.metric("⚽ KG Var Başarısı", f"%{p_btts:.1f}", f"{btts_count} Maç")
            with c_res4:
                st.metric("🎯 MS 1 (Ev Sahibi)", f"%{p_ms1:.1f}", f"{ms1_count} Maç")
                
            st.write("---")
            st.markdown("##### 🗂️ Bu Kriterlere Uyan Örnek Geçmiş Maçlar ve Skorları")
            
            # Sonuçları ekranda şık bir tablo düzeninde listele
            df_display = df_filtreli[['league_name', 'home_name', 'away_name', 'homeGoalCount', 'awayGoalCount', 'team_a_xg_prematch', 'team_b_xg_prematch']].copy()
            df_display.columns = ['Lig', 'Ev Sahibi', 'Deplasman', 'Ev Gol', 'Dep Gol', 'Ev xG', 'Dep xG']
            st.dataframe(df_display.tail(30), use_container_width=True)
            
            # İleride kuracağımız Simülasyon Motoru için veri iskeleti hazırlandı
            st.caption("💡 Titan Notu: Yukarıdaki istatistiksel karne, bir sonraki aşamada kuracağımız Simülasyon Motoru'nun algoritma ağırlıklarını (weight) otomatik belirleyecektir.")

elif mod == "📚 Kupon Arşivi":
    st.title("📂 Mühürlü Kupon Geçmişi (ai_arsiv.json)")
    if os.path.exists(ARSIV_DOSYASI):
        with open(ARSIV_DOSYASI, "r", encoding="utf-8") as f:
            st.json(json.load(f))
    else:
        st.warning("Henüz mühürlenmiş bir kupon kaydı bulunmuyor.")

elif mod == "📂 JSON Veri Merkezi":
    st.title("🗄️ JSON Veri Merkezi Operasyon Üssü")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📅 Gelecek Fikstür Ambarı")
        if st.button("📡 BÜLTENİ HASAT ET (Gelecek)"):
            with st.spinner("Hasat ediliyor..."):
                st.session_state.bulten_verileri = derin_bulten_hasat_et()
                st.success("Bülten güncellendi!")
                st.rerun()
    with c2:
        st.markdown("### 📚 Geçmiş Maç Veri Bankası")
        if st.button("💾 PAZARTESİ HASADI (Geçmiş)"):
            with st.spinner("Arşivleniyor..."):
                sayi = derin_gecmis_hasat_et()
                st.success(f"{sayi} Maç eklendi!")
