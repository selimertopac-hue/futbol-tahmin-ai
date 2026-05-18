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
BULTEN_DOSYASI = "msi_bulten_bankasi.json"

st.set_page_config(page_title="UltraSkor Pro: Titan v19.7", page_icon="🎯", layout="wide")

# --- 🏗️ YARDIMCI ARAÇLAR ---
def winner(skor_metni):
    """Skor metnini analiz edip kazananı döndürür (1, X, 2)."""
    try:
        if not skor_metni or " - " not in skor_metni: return "X"
        parcalar = skor_metni.split(" - ")
        ev, dep = int(parcalar[0]), int(parcalar[1])
        if ev > dep: return "1"
        if dep > ev: return "2"
        return "X"
    except: return "X"

# --- ⚡ HIZLANDIRILMIŞ AMBAR KONTROLÜ (Nitro) ---
if 'bulten_hazir' not in st.session_state:
    if os.path.exists(BULTEN_DOSYASI):
        with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
            try:
                st.session_state.fs_data = json.load(f)
                st.session_state.bulten_hazir = True
            except:
                st.session_state.fs_data = []
    else:
        st.session_state.fs_data = []

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

# --- 🏆 50 ELİT & PROFESYONEL LİG: KESİN LİSTE ---
HEDEF_LIGLER = [
    "Austria Bundesliga", "Austria 2. Liga", 
    "Belgium Pro League", "Belgium First Division B",
    "Bosnia and Herzegovina Premier League", "Bosnia and Herzegovina First League",
    "China Chinese Super League", 
    "Croatia Prva HNL", 
    "Czech Republic First League", "Czech Republic FNL",
    "Denmark Superliga", "Denmark 1st Division",
    "England Premier League", "England Championship", "England EFL League One", "England EFL League Two",
    "Finland Veikkausliiga", "Finland Ykkösliiga",
    "France Ligue 1", "France Ligue 2",
    "Germany Bundesliga", "Germany 2. Bundesliga",
    "Hungary NB I", 
    "Italy Serie A", "Italy Serie B",
    "Netherlands Eredivisie", "Netherlands Eerste Divisie",
    "Norway Eliteserien", "Norway First Division",
    "Poland Ekstraklasa", "Poland 1. Liga",
    "Portugal Liga NOS", "Portugal LigaPro",
    "Romania Liga I", 
    "Scotland Premiership", 
    "Serbia SuperLiga", 
    "Slovakia Super Liga", "Slovakia 2. Liga",
    "Slovenia PrvaLiga", "Slovenia 2. SNL",
    "Spain La Liga", "Spain Segunda División",
    "Sweden Allsvenskan", "Sweden Superettan",
    "Switzerland Super League", "Switzerland Challenge League",
    "Turkey Süper Lig", "Turkey 1. Lig",
    "USA MLS", "USA USL Championship"
]

def lig_bilgi_bankasi_olustur():
    url = f"{FS_BASE_URL}/league-list"
    params = {'key': FS_API_KEY}
    try:
        res = requests.get(url, params=params, timeout=15).json()
        if not res or not res.get('success'): return {}
        ligler = {}
        for lig in res['data']:
            c_ad = lig.get('country', '')
            l_ad = lig.get('league_name') or lig.get('name', '')
            tam_ad = f"{c_ad} {l_ad}"
            if any(hedef.lower() in tam_ad.lower() for hedef in HEDEF_LIGLER):
                if 'season' in lig and len(lig['season']) > 0:
                    en_son = lig['season'][-1]
                    s_id = str(en_son['id'])
                    ligler[s_id] = tam_ad
        return ligler
    except: return {}

def pazartesi_hasadi():
    lig_sozlugu = lig_bilgi_bankasi_olustur() 
    if not lig_sozlugu: return 0
    if os.path.exists(VERİ_BANKASI_DOSYASI):
        with open(VERİ_BANKASI_DOSYASI, "r", encoding="utf-8") as f:
            try: mevcut_arsiv = json.load(f)
            except: mevcut_arsiv = []
    else: mevcut_arsiv = []
    kayitli_idlar = {m.get('id') for m in mevcut_arsiv}
    yeni_eklenen_sayisi = 0
    p_bar = st.sidebar.progress(0)
    for index, (s_id, l_tam_ad) in enumerate(lig_sozlugu.items()):
        yasakli = ["women", "u19", "u21", "u23", "youth", "reserve", "kadın", "friendly", "cup", "kupa"]
        if any(y in l_tam_ad.lower() for y in yasakli): continue
        if not any(hedef.lower() in l_tam_ad.lower() for hedef in HEDEF_LIGLER): continue
        params = {'key': FS_API_KEY, 'league_id': s_id, 'status': 'complete'}
        try:
            res = requests.get(f"{FS_BASE_URL}/league-matches", params=params, timeout=10).json()
            if res and 'data' in res:
                for m in res['data']:
                    if m.get('id') not in kayitli_idlar:
                        m_arsiv = {
                            'id': m.get('id'),
                            'home_name': m.get('home_name'),
                            'away_name': m.get('away_name'),
                            'league_name': l_tam_ad,
                            'date_unix': m.get('date_unix'),
                            'result': f"{m.get('homeGoalCount')} - {m.get('awayGoalCount')}",
                            'team_a_xg_prematch': m.get('team_a_xg_prematch'),
                            'team_b_xg_prematch': m.get('team_b_xg_prematch'),
                            'shot_conversion_rate_home': m.get('shot_conversion_rate_home'),
                            'shot_conversion_rate_away': m.get('shot_conversion_rate_away'),
                            'homeAttackAdvantagePercentage': m.get('homeAttackAdvantagePercentage'),
                            'homeDefenceAdvantagePercentage': m.get('homeDefenceAdvantagePercentage'),
                            'points_dropped_from_winning_positions_home': m.get('points_dropped_from_winning_positions_home'),
                            'seasonAVG_away': m.get('seasonAVG_away'),
                            'seasonConcededAVG_away': m.get('seasonConcededAVG_away'),
                            'pre_match_teamA_overall_ppg': m.get('pre_match_teamA_overall_ppg'),
                            'pre_match_teamB_overall_ppg': m.get('pre_match_teamB_overall_ppg'),
                            'actual_home_goals': m.get('homeGoalCount'),
                            'actual_away_goals': m.get('awayGoalCount'),
                            'total_goals': (m.get('homeGoalCount', 0) or 0) + (m.get('awayGoalCount', 0) or 0),
                            'actual_btts': (m.get('homeGoalCount', 0) > 0 and m.get('awayGoalCount', 0) > 0),
                            'total_shots_on_target': (m.get('home_shotsOnTarget', 0) or 0) + (m.get('away_shotsOnTarget', 0) or 0)
                        }
                        mevcut_arsiv.append(m_arsiv)
                        kayitli_idlar.add(m.get('id'))
                        yeni_eklenen_sayisi += 1
        except: continue
        p_bar.progress((index + 1) / len(lig_sozlugu))
    if yeni_eklenen_sayisi > 0:
        with open(VERİ_BANKASI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(mevcut_arsiv, f, ensure_ascii=False, indent=4)
    return yeni_eklenen_sayisi

# --- AYARLAR & ZAMAN MOTORU (v18.0) ---
def hafta_bilgisi_getir(hafta_kaydirma=0):
    tarih = datetime.now() + timedelta(weeks=hafta_kaydirma)
    bugun_no = tarih.weekday() 
    cuma = tarih - timedelta(days=bugun_no - 4)
    cuma = cuma.replace(hour=0, minute=0, second=0, microsecond=0)
    pazartesi = cuma + timedelta(days=3, hours=23, minutes=59, seconds=59)
    return cuma.timestamp(), pazartesi.timestamp(), cuma.strftime("%d %b")

# --- SIDEBAR HAFTA SEÇİCİ ---
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Analiz Vizörü")
hafta_secim = st.sidebar.selectbox("Tahmin Haftası", ["Bu Hafta (Cuma-Paz)", "Gelecek Hafta", "Tüm Maçları Göster"], index=0)

if hafta_secim == "Bu Hafta (Cuma-Paz)":
    CUMA_SINIR, PAZARTESI_SINIR, HAFTA_ETIKET = hafta_bilgisi_getir(0)
elif hafta_secim == "Gelecek Hafta":
    CUMA_SINIR, PAZARTESI_SINIR, HAFTA_ETIKET = hafta_bilgisi_getir(1)
else:
    CUMA_SINIR, PAZARTESI_SINIR = 0, 4000000000

def tum_dunyayi_hasat_et():
    lig_sozlugu = lig_bilgi_bankasi_olustur()
    if not lig_sozlugu:
        st.sidebar.error("❌ Elit lig listesi alınamadı!")
        return []
    yeni_bulten = []
    p_bar = st.sidebar.progress(0)
    yasakli = ["women", "u19", "u21", "u23", "youth", "reserve", "kadın", "friendly", "cup", "kupa"]
    for index, (s_id, l_tam_ad) in enumerate(lig_sozlugu.items()):
        if any(y in l_tam_ad.lower() for y in yasakli): continue
        if not any(hedef.lower() in l_tam_ad.lower() for hedef in HEDEF_LIGLER): continue
        url = f"{FS_BASE_URL}/league-matches"
        params = {'key': FS_API_KEY, 'league_id': s_id, 'status': 'incomplete'}
        try:
            response = requests.get(url, params=params, timeout=12)
            m_res = response.json()
            if m_res and 'data' in m_res:
                for m in m_res['data']:
                    mac_tarihi = m.get('date_unix', 0)
                    if CUMA_SINIR <= mac_tarihi <= PAZARTESI_SINIR:
                        yeni_bulten.append({
                            'id': m.get('id'),
                            'home_name': m.get('home_name'),
                            'away_name': m.get('away_name'),
                            'league_name': l_tam_ad,
                            'date_unix': mac_tarihi,
                            'team_a_xg_prematch': m.get('team_a_xg_prematch'),
                            'team_b_xg_prematch': m.get('team_b_xg_prematch'),
                            'pre_match_teamA_overall_ppg': m.get('pre_match_teamA_overall_ppg'),
                            'pre_match_teamB_overall_ppg': m.get('pre_match_teamB_overall_ppg'),
                            'shot_conversion_rate_home': m.get('shot_conversion_rate_home'),
                            'homeAttackAdvantagePercentage': m.get('homeAttackAdvantagePercentage'),
                            'seasonConcededAVG_away': m.get('seasonConcededAVG_away'),
                            'o25_potential': m.get('o25_potential'),
                            'btts_potential': m.get('btts_potential')
                        })
        except: continue
        p_bar.progress((index + 1) / len(lig_sozlugu))
    if yeni_bulten:
        with open(BULTEN_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(yeni_bulten, f, ensure_ascii=False, indent=4)
    return yeni_bulten

# --- 🏗️ TITAN COUNCIL v19.5 ---
def skor_olasigi_hesapla(e, a, carpan=400):
    matrix = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
    s = np.unravel_index(np.argmax(matrix), matrix.shape)
    conf = int(matrix[s] * carpan)
    return {"skor": f"{s[0]} - {s[1]}", "conf": conf}

@st.cache_data(ttl=3600)
def titan_council_v19_5(m):
    try:
        h_xg = float(m.get('team_a_xg_prematch') or 1.45)
        a_xg = float(m.get('team_b_xg_prematch') or 1.15)
        h_ppg = float(m.get('pre_match_teamA_overall_ppg') or 1.2)
        a_ppg = float(m.get('pre_match_teamB_overall_ppg') or 1.1)
        h_conv = float(m.get('shot_conversion_rate_home') or 10.0)
        h_att_adv = float(m.get('homeAttackAdvantagePercentage') or 5.0)
        a_conceded = float(m.get('seasonConcededAVG_away') or 1.3)
        yorgunluk_h = 0.92 if m.get('is_fatigued_home') else 1.0

        st_h = h_xg * (1 + (h_att_adv / 150)) * h_ppg
        st_a = a_xg * 0.95
        res_st = skor_olasigi_hesapla(st_h, st_a, 380)

        sp_h, sp_a = h_xg, a_xg
        if (h_xg + a_xg) > 2.7: sp_h *= 1.22; sp_a *= 1.18
        res_sp = skor_olasigi_hesapla(sp_h, sp_a, 350)

        nx_h, nx_a = h_xg, a_xg
        if h_ppg > 1.9: nx_h *= 0.88; nx_a *= 1.15
        res_nx = skor_olasigi_hesapla(nx_h, nx_a, 360)

        wx_h = (h_xg * (15 / max(5, h_conv))) * yorgunluk_h
        wx_a = a_xg * (a_ppg / 1.1)
        res_wx = skor_olasigi_hesapla(wx_h, wx_a, 420)

        ae_h = (st_h * 0.30) + (wx_h * 0.40) + (sp_h * 0.15) + (nx_h * 0.15)
        ae_a = (st_a * 0.30) + (wx_a * 0.40) + (sp_a * 0.15) + (nx_a * 0.15)
        res_ae = skor_olasigi_hesapla(ae_h, ae_a, 400)

        return {
            "skor": res_ae['skor'], "guven": res_ae['conf'], "xg": ae_h + ae_a,
            "st_res": res_st, "sp_res": res_sp, "nx_res": res_nx, "wx_res": res_wx, "ae_res": res_ae,
            "o25_pot": float(m.get('o25_potential') or 50.0), "btts_pot": float(m.get('btts_potential') or 50.0)
        }
    except: return None

# --- MÜHÜRLENEN KUPONLARI DOSYAYA YAZMA FONKSİYONU ---
def kuponu_arsive_kilitle(kupon_adi, maclar, filtre_adi):
    arsiv_verisi = []
    if os.path.exists(ARSIV_DOSYASI):
        with open(ARSIV_DOSYASI, "r", encoding="utf-8") as f:
            try: arsiv_verisi = json.load(f)
            except: arsiv_verisi = []
            
    yeni_kayit = {
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "kupon_adi": kupon_adi,
        "filtre": filtre_adi,
        "maclar": []
    }
    for m in maclar:
        karar = "2.5 ÜST" if m['c_res']['xg'] > 2.6 else f"MS {winner(m['c_res']['skor'])}"
        yeni_kayit["maclar"].append({
            "lig": m.get('league_name'),
            "karsilasma": f"{m.get('home_name')} - {m.get('away_name')}",
            "tahmin": karar,
            "beklenen_skor": m['c_res']['skor'],
            "guven": m['avg_conf']
        })
    arsiv_verisi.append(yeni_kayit)
    with open(ARSIV_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(arsiv_verisi, f, ensure_ascii=False, indent=4)
    st.toast(f"🎯 {kupon_adi} Başarıyla ai_arsiv.json Dosyasına Mühürlendi!")

# --- 5. ZAMAN VE HAFTA HESABI ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

# --- 🚀 ANA SIDEBAR ---
mod = st.sidebar.radio("🚀 Menü", ["🤖 Tahmin Robotu", "🏠 Canlı Skorlar", "Global AI", "📚 Kupon Arşivi", "📂 Veri Bankası"], key="main_menu")

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
    st.title("🚀 Titan v19.7: Konsey Mühürlü Kuponlar")
    if hafta_secim == "Bu Hafta (Cuma-Paz)": BAS_L, BIT_L, _ = hafta_bilgisi_getir(0)
    elif hafta_secim == "Gelecek Hafta": BAS_L, BIT_L, _ = hafta_bilgisi_getir(1)
    else: BAS_L, BIT_L = 0, 4000000000

    bulten = st.session_state.fs_data if st.session_state.get('fs_data') else []
    if bulten:
        konsey_havuzu = []
        for m in bulten:
            lig_adi = m.get('league_name', '')
            if not any(hedef.lower() in lig_adi.lower() for hedef in HEDEF_LIGLER): continue
            mac_zamani = m.get('date_unix', 0)
            if BAS_L <= mac_zamani <= BIT_L:
                res = titan_council_v19_5(m)
                if res:
                    m['c_res'] = res
                    m['avg_conf'] = res['guven']
                    konsey_havuzu.append(m)

        if konsey_havuzu:
            sirali_havuz = sorted(konsey_havuzu, key=lambda x: x['avg_conf'], reverse=True)
            
            # --- 🏆 A. ROBOTİK KARMA KUPONLAR (5 ELEMANLI 4 KESİN KUPON) ---
            st.subheader("📋 Robotik Karma Kuponlar (5'er Maçlık)")
            k_cols = st.columns(4)
            kupon_tipleri = [
                {"ad": "💎 ELMAS KUPON", "renk": "#FFD700"},
                {"ad": "🥇 ALTIN KUPON", "renk": "#C0C0C0"},
                {"ad": "🥈 GÜMÜŞ KUPON", "renk": "#CD7F32"},
                {"ad": "🎖️ BRONZ KUPON", "renk": "#8A2BE2"}
            ]
            for i, k_ayar in enumerate(kupon_tipleri):
                with k_cols[i]:
                    st.markdown(f"<h4 style='color:{k_ayar['renk']}; text-align:center;'>{k_ayar['ad']}</h4>", unsafe_allow_html=True)
                    kupon_maclari = sirali_havuz[i*5 : (i+1)*5]
                    for match in kupon_maclari:
                        karar = "2.5 ÜST" if match['c_res']['xg'] > 2.6 else f"MS {winner(match['c_res']['skor'])}"
                        st.markdown(f"""
                            <div class="match-card" style="border-right: 4px solid {k_ayar['renk']}; padding:10px; margin-bottom:5px; font-size:0.8rem; background:#0d1117;">
                                <small style='color:#8B949E;'>{match.get('league_name', '')[:18]}</small><br>
                                <b>{match['home_name'][:12]} - {match['away_name'][:12]}</b><br>
                                <span style='color:{k_ayar['renk']}; font-weight:bold;'>{karar}</span> (%{int(match['avg_conf'])})
                            </div>
                        """, unsafe_allow_html=True)
                    # MÜHÜRLEME BUTONU AKTİFLEŞTİRİLDİ (JSON'a Kalıcı Yazar)
                    if st.button(f"{k_ayar['ad']} Mühürle", key=f"btn_k_{i}"):
                        kuponu_arsive_kilitle(k_ayar['ad'], kupon_maclari, "Titan Council v19.5")

            st.divider()

            # --- 📊 B. GLOBAL COUNCİL LİSTELERİ (20 MAÇ TERMİNALİ MANTIĞI) ---
            st.subheader("🌐 Konsey Ortak Karar Terminali (Top 20 Fırsat)")
            tab_taraf, tab_gol = st.tabs(["🎯 En İyi 20 Taraf Bahsi (1X2)", "⚽ En İyi 20 Alt/Üst Bahsi"])

            with tab_taraf:
                taraf_20 = sorted(konsey_havuzu, key=lambda x: x['avg_conf'], reverse=True)[:20]
                t_col1, t_col2 = st.columns(2)
                for idx, m in enumerate(taraf_20):
                    with t_col1 if idx % 2 == 0 else t_col2:
                        ms_karar = winner(m['c_res']['skor'])
                        st.markdown(f"""
                            <div class="match-card" style="border-left: 4px solid #58A6FF; padding:10px;">
                                <small style='color:#8B949E;'>{m.get('league_name')}</small>
                                <div style="display:flex; justify-content:space-between; margin-top:2px;">
                                    <b>{m['home_name']} - {m['away_name']}</b>
                                    <span style="color:#58A6FF; font-weight:bold;">{m['c_res']['skor']}</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                                    <span style="font-size:0.9rem; font-weight:bold; background:rgba(88,166,255,0.1); padding:2px 6px; border-radius:4px; color:#58A6FF;">🎯 MS {ms_karar}</span>
                                    <small style="color:#8B949E;">Konsey Güven Endeksi: %{int(m['avg_conf'])}</small>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

            with tab_gol:
                gol_20 = sorted(konsey_havuzu, key=lambda x: abs(x['c_res']['xg'] - 2.5), reverse=True)[:20]
                g_col1, g_col2 = st.columns(2)
                for idx, m in enumerate(gol_20):
                    with g_col1 if idx % 2 == 0 else g_col2:
                        gol_tip = "2.5 ÜST" if m['c_res']['xg'] > 2.5 else "2.5 ALT"
                        g_renk = "#3fb950" if "ÜST" in gol_tip else "#d73a49"
                        st.markdown(f"""
                            <div class="match-card" style="border-right: 4px solid {g_renk}; padding:10px;">
                                <small style='color:#8B949E;'>{m.get('league_name')}</small>
                                <div style="display:flex; justify-content:space-between; margin-top:2px;">
                                    <b>{m['home_name']} - {m['away_name']}</b>
                                    <span style="color:{g_renk}; font-weight:bold;">xG: {m['c_res']['xg']:.2f}</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                                    <span style="color:{g_renk}; font-weight:bold;">⚽ {gol_tip}</span>
                                    <small style="color:#8B949E;">Konsey Önerisi: {m['c_res']['skor']}</small>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Seçili vizörde elit lig maçı bulunamadı.")
    else:
        st.info("🔎 Ambar dosyası bulunamadı. Lütfen önce hasat yapın.")

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
                        <span style="font-size:0.8rem;">📍 {m.get('league_name', 'Bilinmeyen Lig')}</span>
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
    st.title("🤖 Titan Konseyi: Global Harekat Planı v19.6")
    bulten_kaynagi = st.session_state.fs_data if st.session_state.get('fs_data') else []
    
    if bulten_kaynagi:
        robot_isimleri = ["💎 AETHER", "📊 STANDART", "🔥 SPEKTRUM", "🛡️ NEXUS", "🧪 WICKHAM"]
        robot_ayarlar = [
            {"key": "ae_res", "renk": "#FFD700"},
            {"key": "st_res", "renk": "#58A6FF"},
            {"key": "sp_res", "renk": "#FF7B72"},
            {"key": "nx_res", "renk": "#79C0FF"},
            {"key": "wx_res", "renk": "#D2A8FF"}
        ]
        
        tabs = st.tabs(robot_isimleri)
        for i, r_info in enumerate(robot_ayarlar):
            with tabs[i]:
                r_key = r_info["key"]
                r_renk = r_info["renk"]
                
                analizli_bulten = []
                deneme_bolgesi = [] # --- DENEME BÖLGESİ LİSTESİ ---
                
                if hafta_secim == "Bu Hafta (Cuma-Paz)": BAS_L, BIT_L, _ = hafta_bilgisi_getir(0)
                elif hafta_secim == "Gelecek Hafta": BAS_L, BIT_L, _ = hafta_bilgisi_getir(1)
                else: BAS_L, BIT_L = 0, 4000000000

                for m in bulten_kaynagi:
                    lig_adi = m.get('league_name', '')
                    if not any(hedef.lower() in lig_adi.lower() for hedef in HEDEF_LIGLER): continue
                    mac_zamani = m.get('date_unix', 0)
                    
                    if BAS_L <= mac_zamani <= BIT_L:
                        res = titan_council_v19_5(m)
                        if res:
                            m_copy = m.copy()
                            m_copy['tmp_res'] = res[r_key]
                            m_copy['tmp_xg'] = res['xg']
                            m_copy['full_res'] = res
                            
                            # Güven barajı %75+ olanları süz
                            if res[r_key]['conf'] >= 75:
                                analizli_bulten.append(m_copy)
                            else:
                                # Ana kuponlara giremeyen ama yüksek potansiyelli ek maçları havuza at
                                deneme_bolgesi.append(m_copy)

                if analizli_bulten or deneme_bolgesi:
                    # --- A. EN İYİ 10 TARAF BAHSİ ---
                    st.subheader(f"🏆 {robot_isimleri[i]} - Ana 1X2 Taraf Tahminleri")
                    taraf_listesi = sorted(analizli_bulten, key=lambda x: x['tmp_res']['conf'], reverse=True)[:10]
                    
                    if taraf_listesi:
                        col1, col2 = st.columns(2)
                        for idx, match in enumerate(taraf_listesi):
                            with col1 if idx % 2 == 0 else col2:
                                t_ms = winner(match['tmp_res']['skor'])
                                st.markdown(f"""
                                    <div class="match-card" style="border-left: 4px solid {r_renk}; padding:10px; margin-bottom:10px;">
                                        <div style="display:flex; justify-content:space-between;">
                                            <b>{match['home_name']} - {match['away_name']}</b>
                                            <span style="color:{r_renk}; font-weight:bold;">{match['tmp_res']['skor']}</span>
                                        </div>
                                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                                            <span style="font-size:0.9rem; color:#58A6FF; font-weight:bold;">🎯 MS {t_ms}</span>
                                            <span style="background:{r_renk}33; color:{r_renk}; padding:2px 8px; border-radius:5px; font-weight:bold;">%{match['tmp_res']['conf']}</span>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.info("Bu robot için %75 güven barajını geçen ana taraf bahsi bulunamadı.")

                    st.divider()

                    # --- B. EN İYİ 10 GOL BAHSİ ---
                    st.subheader(f"⚽ {robot_isimleri[i]} - Ana Alt/Üst Tahminleri")
                    gol_listesi = sorted(analizli_bulten, key=lambda x: abs(x['tmp_xg'] - 2.5), reverse=True)[:10]
                    
                    if gol_listesi:
                        col3, col4 = st.columns(2)
                        for idx, match in enumerate(gol_listesi):
                            with col3 if idx % 2 == 0 else col4:
                                t_gol = "2.5 ÜST" if match['tmp_xg'] > 2.5 else "2.5 ALT"
                                g_renk = "#3fb950" if "ÜST" in t_gol else "#d73a49"
                                st.markdown(f"""
                                    <div class="match-card" style="border-right: 4px solid {g_renk}; padding:10px; margin-bottom:10px;">
                                        <div style="display:flex; justify-content:space-between;">
                                            <b>{match['home_name']} - {match['away_name']}</b>
                                            <small style="color:#8B949E;">xG: {match['tmp_xg']:.2f}</small>
                                        </div>
                                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                                            <span style="color:{g_renk}; font-weight:bold;">🔥 {t_gol}</span>
                                            <span style="font-size:0.8rem; background:#30363d; padding:2px 6px; border-radius:4px;">Skor: {match['tmp_res']['skor']}</span>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.info("Bu robot için ana gol tahmini saptanamadı.")

                    # --- 🔬 C. ENTEGRE EDİLEN DENEME BÖLGESİ (EK MAÇLAR) ---
                    st.divider()
                    st.subheader(f"🔬 Deneme Bölgesi ({robot_isimleri[i]} Ek Maç Havuzu)")
                    
                    ek_maclar = sorted(deneme_bolgesi, key=lambda x: x['tmp_res']['conf'], reverse=True)[:10]
                    if ek_maclar:
                        d_cols = st.columns(2)
                        for idx, match in enumerate(ek_maclar):
                            with d_cols[idx % 2]:
                                st.markdown(f"""
                                    <div class="match-card" style="background: rgba(48, 54, 61, 0.2); border: 1px dashed #8B949E; padding: 10px;">
                                        <div style="display:flex; justify-content:space-between;">
                                            <b>{match['home_name']} - {match['away_name']}</b>
                                            <small style="color:#8B949E;">{match.get('league_name')[:20]}</small>
                                        </div>
                                        <div style="margin-top:5px; font-size:0.75rem; color:#C9D1D9;">
                                            Aether: {match['full_res']['ae_res']['skor']} (%{match['full_res']['ae_res']['conf']}) | 
                                            Wickham: {match['full_res']['wx_res']['skor']} (%{match['full_res']['wx_res']['conf']}) | 
                                            Nexus: {match['full_res']['nx_res']['skor']} (%{match['full_res']['nx_res']['conf']})
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.caption("Filtrelere takılan ek deneme maçı bulunmuyor.")
                else:
                    st.info(f"{robot_isimleri[i]} vizöründe bu hafta elit lig maçı bulunamadı.")
    else:
        st.warning("⚠️ Ambar boş. Lütfen önce hasat yapın.")

elif mod == "📚 Kupon Arşivi":
    st.title("📂 Mühürlü Kupon Geçmişi")
    if os.path.exists(ARSIV_DOSYASI):
        with open(ARSIV_DOSYASI, "r", encoding="utf-8") as f:
            arsiv_verisi = json.load(f)
        st.info("Daha önce 'Mühürle' dediğin tüm kuponlar burada saklanır.")
        st.json(arsiv_verisi) 
    else:
        st.warning("Henüz mühürlenmiş bir kupon bulunamadı.")

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
            st.download_button("📥 Arşivi İndir", data=json.dumps(arsiv_verisi, indent=4), file_name="msi_futbol_bankasi.json")
