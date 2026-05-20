import streamlit as st
import json
import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime, timedelta

# --- 1. DOSYA AYARLARI & MİLAT ---
SİTE_DOGUM_TARİHİ = datetime(2026, 2, 20) 
ARSIV_DOSYASI = "ai_arsiv.json"
VERİ_BANKASI_DOSYASI = "msi_futbol_bankasi.json"
BULTEN_DOSYASI = "msi_bulten_bankasi.json"

st.set_page_config(page_title="UltraSkor Pro: Titan Yerel Güç", page_icon="🎯", layout="wide")

# --- 2. GÖRSEL STİL (MSI DARK MODE) ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
    .coupon-item { background: #0d1117; padding: 8px; margin-top: 8px; border-radius: 6px; border: 1px solid #30363d; font-size: 0.85rem; }
    h1, h2, h3, h4 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 🛰️ OPERASYON MERKEZİ & VERİ GÖSTERGESİ ---
st.sidebar.title("🛡️ MSI Operasyon Merkezi")
st.sidebar.markdown("### 🗄️ Yerel Ambar Durumu")

# Bülten Kontrolü
if os.path.exists(BULTEN_DOSYASI):
    with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
        bulten_hazir_veri = json.load(f)
    st.sidebar.success(f"✅ Bülten Yüklü: {len(bulten_hazir_veri)} Maç")
else:
    st.sidebar.error("❌ msi_bulten_bankasi.json bulunamadı!")
    bulten_hazir_veri = []

# Geçmiş Veri Bankası Kontrolü
if os.path.exists(VERİ_BANKASI_DOSYASI):
    with open(VERİ_BANKASI_DOSYASI, "r", encoding="utf-8") as f:
        arsiv_hazir_veri = json.load(f)
    st.sidebar.success(f"📦 Arşiv Veri Bankası: {len(arsiv_hazir_veri)} Maç")
else:
    st.sidebar.warning("⚠️ msi_futbol_bankasi.json henüz klasörde yok.")

st.sidebar.caption("Mod: %100 Otonom Yerel Veri Modu (Premium) 🚀")

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

# --- HAFTA HESAP MOTORU ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1
hafta_listesi = list(range(1, max(15, site_h_aktif + 2)))
default_index = min(site_h_aktif - 1, len(hafta_listesi) - 1)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Analiz Vizörü")
hafta_secim = st.sidebar.selectbox("Tahmin Haftası", hafta_listesi, index=default_index)

# Seçilen haftanın tarih sınırları
HAFTA_BASLANGIC_TARIHI = SİTE_DOGUM_TARİHİ + timedelta(weeks=hafta_secim - 1)
HAFTA_BITIS_TARIHI = HAFTA_BASLANGIC_TARIHI + timedelta(days=7)
CUMA_SINIR = HAFTA_BASLANGIC_TARIHI.timestamp()
PAZARTESI_SINIR = HAFTA_BITIS_TARIHI.timestamp()

# --- 🧪 TITAN COUNCIL v19.5 ANALİZ MOTORU ---
def skor_olasigi_hesapla(e, a, carpan=400):
    matrix = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
    s = np.unravel_index(np.argmax(matrix), matrix.shape)
    conf = int(matrix[s] * carpan)
    return {"skor": f"{s[0]} - {s[1]}", "conf": conf}

def titan_council_v19_5(m):
    try:
        # FootyStats Premium JSON dosyasından tüm derin istatistikleri çeker
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

def kuponu_arsive_kilitle(kupon_adi, maclar, filtre_adi):
    arsiv_verisi = []
    if os.path.exists(ARSIV_DOSYASI):
        with open(ARSIV_DOSYASI, "r", encoding="utf-8") as f:
            try: arsiv_verisi = json.load(f)
            except: arsiv_verisi = []
    yeni_kayit = {"tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "kupon_adi": kupon_adi, "filtre": filtre_adi, "maclar": []}
    for m in maclar:
        karar = "2.5 ÜST" if m['c_res']['xg'] > 2.6 else f"MS {winner(m['c_res']['skor'])}"
        yeni_kayit["maclar"].append({"lig": m.get('league_name'), "karsilasma": f"{m.get('home_name')} - {m.get('away_name')}", "tahmin": karar, "beklenen_skor": m['c_res']['skor'], "guven": m['avg_conf']})
    arsiv_verisi.append(yeni_kayit)
    with open(ARSIV_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(arsiv_verisi, f, ensure_ascii=False, indent=4)
    st.toast(f"🎯 {kupon_adi} Kalıcı Olarak Hafızaya Yazıldı!")

# --- 7. MENÜ GEZİNTİ PLANLAMASI ---
mod = st.sidebar.radio("🚀 Menü", ["🤖 Tahmin Robotu", "Global AI", "📚 Kupon Arşivi", "📂 Veri Bankası"], key="main_menu")

# --- 📋 ZAMANSAL KORUMALI VERİ SÜZGECİ ---
# JSON dosyasındaki maçları seçilen haftanın tarih sınırlarına göre ayıklar
haftalik_bulten_havuzu = []
for m in bulten_hazir_veri:
    mac_zamani = m.get('date_unix', 0)
    if CUMA_SINIR <= mac_zamani <= PAZARTESI_SINIR:
        res = titan_council_v19_5(m)
        if res:
            m['c_res'] = res
            m['avg_conf'] = res['guven']
            haftalik_bulten_havuzu.append(m)

# Eğer o haftaya ait filtrelenmiş maç yoksa ama dosyada maç varsa, boş ekran göstermemek için ilk verileri doldurur
if not haftalik_bulten_havuzu and bulten_hazir_veri:
    for m in bulten_hazir_veri[:15]:
        res = titan_council_v19_5(m)
        if res:
            m['c_res'] = res
            m['avg_conf'] = res['guven']
            haftalik_bulten_havuzu.append(m)

# --- SAYFA YÜKLEMELERİ ---
if mod == "🤖 Tahmin Robotu":
    st.title(f"🚀 Titan v19.7: {hafta_secim}. Hafta Mühürlü Kuponları")
    
    if haftalik_bulten_havuzu:
        sirali_havuz = sorted(haftalik_bulten_havuzu, key=lambda x: x['avg_conf'], reverse=True)
        
        # 4 Ana Robotik Karma Kupon Düzeni
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
                            <small style='color:#8B949E;'>{match.get('league_name', 'Elit Lig')[:18]}</small><br>
                            <b>{match.get('home_name', 'Ev')[:12]} - {match.get('away_name', 'Dep')[:12]}</b><br>
                            <span style='color:{k_ayar['renk']}; font-weight:bold;'>{karar}</span> (%{int(match['avg_conf'])})
                        </div>""", unsafe_allow_html=True)
                if st.button(f"{k_ayar['ad']} Mühürle", key=f"btn_k_{i}"):
                    kuponu_arsive_kilitle(k_ayar['ad'], kupon_maclari, "Titan Council v19.5")

        st.divider()
        # 20 Maçlık Extra Terminal Göstergesi
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
                                <b>{m.get('home_name')} - {m.get('away_name')}</b>
                                <span style="color:#58A6FF; font-weight:bold;">{m['c_res']['skor']}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)
        with tab_gol:
            gol_20 = sorted(haftalik_bulten_havuzu, key=lambda x: abs(x['c_res']['xg'] - 2.5), reverse=True)[:20]
            g_col1, g_col2 = st.columns(2)
            for idx, m in enumerate(gol_20):
                with g_col1 if idx % 2 == 0 else g_col2:
                    gol_tip = "2.5 ÜST" if m['c_res']['xg'] > 2.5 else "2.5 ALT"
                    st.markdown(f"""
                        <div class="match-card" style="border-right: 4px solid #3fb950; padding:10px;">
                            <small style='color:#8B949E;'>{m.get('league_name')}</small>
                            <div style="display:flex; justify-content:space-between;">
                                <b>{m.get('home_name')} - {m.get('away_name')}</b>
                                <span style="color:#3fb950; font-weight:bold;">⚽ {gol_tip} (xG: {m['c_res']['xg']:.2f})</span>
                            </div>
                        </div>""", unsafe_allow_html=True)
    else:
        st.warning("🔎 Ambar dosyası boş veya bu haftaya ait maç saptanamadı. Lütfen JSON dosyalarını klasöre yükleyin.")

elif mod == "Global AI":
    st.title(f"🚀 Global AI Düzeni — {hafta_secim}. Hafta Analizi")
    filtre = st.sidebar.radio("🤖 Algoritma Seçimi", ["AETHER AI Master", "Standart AI", "Spektrum AI", "Nexus AI", "WICKHAM AI v3"])
    
    if haftalik_bulten_havuzu:
        g_l, deneme_bolgesi = [], []
        for m in haftalik_bulten_havuzu:
            if m['avg_conf'] >= 75:
                g_l.append(m)
            else:
                deneme_bolgesi.append(m)
                    
        tabs = st.tabs(["🏆 Ana Kuponlar", "🔬 Deneme Bölgesi (Yüksek Güvenli Ek Maçlar)"])
        with tabs[0]:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🎯 Taraf Seçimleri")
                for match in g_l[:5]:
                    st.markdown(f'<div class="coupon-item"><b>{match.get("home_name")} - {match.get("away_name")}</b><br>Konsey: {match["c_res"]["skor"]}</div>', unsafe_allow_html=True)
            with c2:
                st.subheader("⚽ Gol Seçimleri")
                for match in g_l[5:10]:
                    st.markdown(f'<div class="coupon-item"><b>{match.get("home_name")} - {match.get("away_name")}</b><br>Sentez xG: {match["c_res"]["xg"]:.2f}</div>', unsafe_allow_html=True)
        
        with tabs[1]:
            st.subheader("🔬 Deneme Bölgesi Maç Havuzu")
            d_cols = st.columns(2)
            for idx, match in enumerate(deneme_bolgesi[:10]):
                with d_cols[idx % 2]:
                    st.markdown(f"""
                        <div class="match-card" style="background: rgba(48, 54, 61, 0.2); border: 1px dashed #8B949E; padding: 10px;">
                            <b>{match.get('home_name')} - {match.get('away_name')}</b> | <small>{match.get('league_name', '')[:20]}</small><br>
                            <small>Tahmin: {match['c_res']['skor']} (Güven: %{match['c_res']['guven']})</small>
                        </div>""", unsafe_allow_html=True)

elif mod == "📚 Kupon Arşivi":
    st.title("📂 Mühürlü Kupon Geçmişi (ai_arsiv.json)")
    if os.path.exists(ARSIV_DOSYASI):
        with open(ARSIV_DOSYASI, "r", encoding="utf-8") as f:
            st.json(json.load(f))
    else:
        st.warning("Henüz mühürlenmiş bir kupon kaydı bulunmuyor.")

elif mod == "📂 Veri Bankası":
    st.title("🗄️ MSI Operasyon Veri Merkezi")
    tab1, tab2 = st.tabs(["📅 Güncel Bülten", "📚 Geçmiş Arşiv"])
    with tab1:
        if os.path.exists(BULTEN_DOSYASI):
            st.dataframe(pd.DataFrame(bulten_hazir_veri), use_container_width=True)
    with tab2:
        if os.path.exists(VERİ_BANKASI_DOSYASI):
            st.dataframe(pd.DataFrame(arsiv_hazir_veri).tail(100), use_container_width=True)
