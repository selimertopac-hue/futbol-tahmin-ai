import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import os
import glob
import json
import re
import requests
import subprocess
import io
from datetime import datetime
from difflib import get_close_matches

st.set_page_config(page_title="UltraSkor Pro: Global Titan Terminali", page_icon="🌐", layout="wide")

DATA_DIR = "footystats_data"
ARSIV_DIR = "bulten_arsivleri"
os.makedirs(ARSIV_DIR, exist_ok=True)

# --- NESİNE API SABİTLERİ (GLOBAL) ---
NESINE_URL = "https://cdnbulten.nesine.com/api/bulten/getprebultenfull"
NESINE_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "authorization": "Basic RDQ3MDc4RDMtNjcwQi00OUJBLTgxNUYtM0IyMjI2MTM1MTZCOkI4MzJCQjZGLTQwMjgtNDIwNS05NjFELTg1N0QxRTZEOTk0OA==",
    "content-type": "application/json; charset=utf-8",
    "origin": "https://www.nesine.com",
    "priority": "u=1, i",
    "referer": "https://www.nesine.com/",
    "sec-ch-ua": '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
}

# ==========================================
# 1. OTOMATİK LİG KEŞİF VE ARŞİVLEME MOTORU
# ==========================================
@st.cache_data
def ligleri_ve_dosyalari_tara():
    lig_rehberi = {}
    if not os.path.exists(DATA_DIR):
        return {}

    alt_klasorler = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
    
    for klasor in sorted(alt_klasorler):
        klasor_yolu = os.path.join(DATA_DIR, klasor)
        csv_ler = glob.glob(os.path.join(klasor_yolu, "*.csv"))
        
        matches_csv = next((f for f in csv_ler if "matches" in os.path.basename(f).lower()), None)
        teams_csv = next((f for f in csv_ler if "teams-" in os.path.basename(f).lower() and "teams2" not in os.path.basename(f).lower()), None)
        teams2_csv = next((f for f in csv_ler if "teams2" in os.path.basename(f).lower()), None)
        
        if matches_csv and teams_csv:
            temiz_lig_adi = klasor.replace("-league", "").replace("-", " ").title()
            lig_rehberi[temiz_lig_adi] = {
                "matches": matches_csv,
                "teams": teams_csv,
                "teams2": teams2_csv
            }
            
    return lig_rehberi

LIG_REHBERI = ligleri_ve_dosyalari_tara()

@st.cache_data
def lig_verisi_oku(matches_path, teams_path, teams2_path):
    try:
        df_matches = pd.read_csv(matches_path)
        df_teams = pd.read_csv(teams_path)
        
        if teams2_path and os.path.exists(teams2_path):
            df_teams2 = pd.read_csv(teams2_path)
            df_teams_full = pd.merge(df_teams, df_teams2, on="common_name", suffixes=('', '_derin'))
        else:
            df_teams_full = df_teams
            
        return df_matches, df_teams_full
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return None, None

# ==========================================
# 2. GELİŞMİŞ ANALİZ, TREND VE BACKTEST MOTORLARI
# ==========================================
def dinamik_trend_hesapla(takim_adi, df_matches, is_home=True):
    """Takımın son maçlarındaki xG/gol üretim ivmesini hesaplar."""
    if df_matches is None or df_matches.empty:
        return 1.00
    completed = df_matches[df_matches['status'] == 'complete'].copy()
    if 'date_GMT' in completed.columns:
        completed = completed.sort_values(by='date_GMT', ascending=False)
        
    if is_home:
        son = completed[completed['home_team_name'] == takim_adi].head(5)
        if len(son) < 3: return 1.00
        ort = son['home_team_goal_count'].mean()
    else:
        son = completed[completed['away_team_name'] == takim_adi].head(5)
        if len(son) < 3: return 1.00
        ort = son['away_team_goal_count'].mean()
        
    if ort >= 2.0: return 1.10
    elif ort <= 0.7: return 0.90
    return 1.00

def gelismis_poisson_analizi(ev_takim, dep_takim, df_teams, df_league=None, df_matches=None):
    lig_ev_ort = float(df_league['average_scored_home_team'].values[0]) if df_league is not None else 1.60
    lig_dep_ort = float(df_league['average_scored_away_team'].values[0]) if df_league is not None else 1.29

    h_row = df_teams[(df_teams['common_name'] == ev_takim) | (df_teams['team_name'] == ev_takim)]
    a_row = df_teams[(df_teams['common_name'] == dep_takim) | (df_teams['team_name'] == dep_takim)]

    if h_row.empty or a_row.empty:
        return None

    h_xg_for = float(h_row['xg_for_avg_home'].values[0]) if not pd.isna(h_row['xg_for_avg_home'].values[0]) else lig_ev_ort
    h_xg_against = float(h_row['xg_against_avg_home'].values[0]) if not pd.isna(h_row['xg_against_avg_home'].values[0]) else lig_dep_ort
    a_xg_for = float(a_row['xg_for_avg_away'].values[0]) if not pd.isna(a_row['xg_for_avg_away'].values[0]) else lig_dep_ort
    a_xg_against = float(a_row['xg_against_avg_away'].values[0]) if not pd.isna(a_row['xg_against_avg_away'].values[0]) else lig_ev_ort

    # Dinamik Trend Çarpanı Entegrasyonu
    trend_ev = dinamik_trend_hesapla(ev_takim, df_matches, is_home=True) if df_matches is not None else 1.0
    trend_dep = dinamik_trend_hesapla(dep_takim, df_matches, is_home=False) if df_matches is not None else 1.0

    lambda_ev = ((h_xg_for * a_xg_against) / lig_ev_ort) * trend_ev
    lambda_dep = ((a_xg_for * h_xg_against) / lig_dep_ort) * trend_dep

    max_gol = 6
    ev_olasiliklar = [poisson.pmf(i, max(0.2, lambda_ev)) for i in range(max_gol)]
    dep_olasiliklar = [poisson.pmf(j, max(0.2, lambda_dep)) for j in range(max_gol)]
    
    matris = np.outer(ev_olasiliklar, dep_olasiliklar)

    prob_ms1 = float(np.sum(np.tril(matris, -1)))
    prob_msx = float(np.sum(np.diag(matris)))
    prob_ms2 = float(np.sum(np.triu(matris, 1)))

    prob_alt25 = sum(matris[i, j] for i in range(max_gol) for j in range(max_gol) if i + j < 2.5)
    prob_ust25 = 1.0 - prob_alt25
    prob_kg_var = 1.0 - (ev_olasiliklar[0] + dep_olasiliklar[0] - matris[0, 0])

    skor_indeks = np.unravel_index(np.argmax(matris), matris.shape)

    return {
        "lambda_ev": round(lambda_ev, 2),
        "lambda_dep": round(lambda_dep, 2),
        "tahmin_skor": f"{skor_indeks[0]} - {skor_indeks[1]}",
        "skor_ihtimali": round(matris[skor_indeks] * 100, 1),
        "prob_ms1": round(prob_ms1 * 100, 1),
        "prob_msx": round(prob_msx * 100, 1),
        "prob_ms2": round(prob_ms2 * 100, 1),
        "prob_ust25": round(prob_ust25 * 100, 1),
        "prob_kg_var": round(prob_kg_var * 100, 1)
    }

def basari_orani_backtest(df_matches, df_teams):
    completed = df_matches[df_matches['status'] == 'complete'].copy()
    if completed.empty:
        return {"toplam": 0, "basarili": 0, "oran": 0.0, "detaylar": []}
        
    test_ornekleri = completed.tail(50)
    dogru_tahmin = 0
    toplam_test = 0
    detaylar = []
    
    for _, r in test_ornekleri.iterrows():
        ev, dep = r['home_team_name'], r['away_team_name']
        gercek_ev_gol = int(r.get('home_team_goal_count', 0) or 0)
        gercek_dep_gol = int(r.get('away_team_goal_count', 0) or 0)
        gercek_sonuc = "MS 1" if gercek_ev_gol > gercek_dep_gol else ("MS 2" if gercek_dep_gol > gercek_ev_gol else "MS X")
        
        res = gelismis_poisson_analizi(ev, dep, df_teams, df_matches=df_matches)
        if res:
            toplam_test += 1
            if res["prob_ms1"] >= 48: tahmin_tercih = "MS 1"
            elif res["prob_ms2"] >= 48: tahmin_tercih = "MS 2"
            else: tahmin_tercih = "MS X"
                
            tutru = (tahmin_tercih == gercek_sonuc)
            if tutru: dogru_tahmin += 1
                
            detaylar.append({
                "Maç": f"{ev} - {dep}",
                "Gerçek Skor": f"{gercek_ev_gol} - {gercek_dep_gol}",
                "Model Tahmin": tahmin_tercih,
                "Durum": "✅ Başarılı" if tutru else "❌ Yanlış"
            })
            
    basari_yuzdesi = round((dogru_tahmin / max(1, toplam_test)) * 100, 1)
    return {"toplam": toplam_test, "basarili": dogru_tahmin, "oran": basari_yuzdesi, "detaylar": detaylar}

def besli_kupon_olustur(havuz, tercih_adi, sira_anahtari="ihtimal"):
    filtreli = [m for m in havuz if m["tercih"] == tercih_adi]
    sirali = sorted(filtreli, key=lambda x: x[sira_anahtari], reverse=True)
    return sirali[:5], sirali[5:10]

def robot_alt_ust_uzmani(res, ust_esik=62.0, alt_esik=60.0):
    if not res: return None
    toplam_xg = round(res["lambda_ev"] + res["lambda_dep"], 2)
    prob_ust = res["prob_ust25"]
    prob_alt = round(100.0 - prob_ust, 1)
    if prob_ust >= ust_esik and toplam_xg >= 2.70:
        return {"tercih": "2.5 ÜST", "guven": prob_ust, "detay": f"xG: {toplam_xg} | Üst: %{prob_ust}"}
    elif prob_alt >= alt_esik and toplam_xg <= 2.20:
        return {"tercih": "2.5 ALT", "guven": prob_alt, "detay": f"xG: {toplam_xg} | Alt: %{prob_alt}"}
    return None

def robot_taraf_avcisi(res, ms_esik=52.0):
    if not res: return None
    ms1, ms2, msx = res["prob_ms1"], res["prob_ms2"], res["prob_msx"]
    if ms1 >= ms_esik and (ms1 - ms2) >= 15.0:
        return {"tercih": "MS 1", "guven": ms1, "detay": f"MS1: %{ms1} (Fark: +%{round(ms1 - ms2, 1)})"}
    elif ms2 >= ms_esik and (ms2 - ms1) >= 15.0:
        return {"tercih": "MS 2", "guven": ms2, "detay": f"MS2: %{ms2} (Fark: +%{round(ms2 - ms1, 1)})"}
    elif msx >= 32.0 and abs(ms1 - ms2) <= 5.0:
        return {"tercih": "MS X", "guven": msx, "detay": f"Kilit Maç | MSX: %{msx}"}
    return None

def kuponu_metne_cevir(mac_listesi):
    metin = "=== ULTRASKOR PRO ROBOTİK KUPON RAPORU ===\n"
    metin += f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    metin += "-" * 40 + "\n\n"
    for i, m in enumerate(mac_listesi, 1):
        mac_adi = m.get("Maç") or m.get("mac") or "-"
        lig = m.get("Lig") or m.get("lig") or "-"
        tercih = m.get("Tercih") or m.get("Robot Tercihi") or m.get("Tahmin") or "-"
        guven = m.get("Güven") or m.get("İhtimal") or "-"
        metin += f"{i}. Maç: {mac_adi}\n   Lig: {lig} | Tercih: {tercih} | Güven: {guven}\n"
        metin += "-" * 40 + "\n"
    return metin

# ==========================================
# 3. ARAYÜZ VE MENÜLER
# ==========================================
st.title("🌐 UltraSkor Pro: Küresel Futbol İstihbarat Merkezi")

if not LIG_REHBERI:
    st.warning("⚠️ `footystats_data` klasöründe taranacak lig klasörü bulunamadı.")
    st.stop()

st.sidebar.title("🎛️ Operasyon Vizörü")
mod_secimi = st.sidebar.radio(
    "Operasyon Modu Seçin:",
    [
        "🏆 Tek Lig Detay Analizi",
        "⚡ Tüm Dünyadan Karma Kuponlar",
        "🤖 Özel Robotlar Laboratuvarı",
        "💰 Nesine & Oran Kıyaslama"
    ]
)

# --- MOD 1 ---
if mod_secimi == "🏆 Tek Lig Detay Analizi":
    secilen_lig = st.sidebar.selectbox("🎯 Analiz Edilecek Lig:", list(LIG_REHBERI.keys()))
    lig_bilgisi = LIG_REHBERI[secilen_lig]
    df_matches, df_teams = lig_verisi_oku(lig_bilgisi["matches"], lig_bilgisi["teams"], lig_bilgisi["teams2"])
    
    if df_matches is not None and df_teams is not None:
        st.subheader(f"📌 {secilen_lig}")
        tab_gelecek, tab_puan, tab_biten, tab_backtest = st.tabs([
            "🚀 Gelecek Maçlar & Robot Tahmini", 
            "📊 Takım xG Güç Tablosu", 
            "📜 Sonuçlanmış Maçlar",
            "🧪 Geriye Dönük Backtest"
        ])
        
        with tab_gelecek:
            gelecek = df_matches[df_matches['status'] == 'incomplete'].copy()
            if gelecek.empty:
                st.info("Bu lig için oynanacak maç bulunamadı.")
            else:
                haftalar = sorted([int(x) for x in gelecek['Game Week'].dropna().unique()])
                secilen_hafta = st.selectbox("Hafta Seç:", haftalar, index=0) if haftalar else None
                secili_maclar = gelecek[gelecek['Game Week'] == secilen_hafta] if secilen_hafta else gelecek.head(10)
                
                tahminler = []
                for _, r in secili_maclar.iterrows():
                    ev, dep = r['home_team_name'], r['away_team_name']
                    res = gelismis_poisson_analizi(ev, dep, df_teams, df_matches=df_matches)
                    if res:
                        if res["prob_ust25"] >= 60: tercih = "2.5 ÜST"
                        elif (100 - res["prob_ust25"]) >= 60: tercih = "2.5 ALT"
                        elif res["prob_ms1"] > res["prob_ms2"] and res["prob_ms1"] > 45: tercih = "MS 1"
                        elif res["prob_ms2"] > res["prob_ms1"] and res["prob_ms2"] > 45: tercih = "MS 2"
                        else: tercih = "MS X"

                        tahminler.append({
                            "Tarih": r.get('date_GMT', '-'),
                            "Ev Sahibi": ev,
                            "Deplasman": dep,
                            "Tahmin Skor": res["tahmin_skor"],
                            "Öneri": tercih,
                            "Toplam xG": round(res["lambda_ev"] + res["lambda_dep"], 2),
                            "MS1 / MSX / MS2": f"%{res['prob_ms1']} / %{res['prob_msx']} / %{res['prob_ms2']}",
                            "2.5 Üst": f"%{res['prob_ust25']}",
                            "KG Var": f"%{res['prob_kg_var']}"
                        })
                st.dataframe(pd.DataFrame(tahminler), use_container_width=True)
                
        with tab_puan:
            cols = [c for c in ['common_name', 'matches_played', 'wins', 'draws', 'losses', 'xg_for_avg_home', 'xg_for_avg_away', 'seasonAVG_overall'] if c in df_teams.columns]
            st.dataframe(df_teams[cols], use_container_width=True)

        with tab_biten:
            biten = df_matches[df_matches['status'] == 'complete'][['Game Week', 'date_GMT', 'home_team_name', 'away_team_name', 'home_team_goal_count', 'away_team_goal_count']].copy()
            biten['Skor'] = biten['home_team_goal_count'].astype(str) + " - " + biten['away_team_goal_count'].astype(str)
            st.dataframe(biten[['Game Week', 'date_GMT', 'home_team_name', 'away_team_name', 'Skor']], use_container_width=True)

        with tab_backtest:
            st.subheader("🧪 Model Geriye Dönük Başarı Testi (Backtesting)")
            if st.button("🚀 Geçmiş Sezonu Simüle Et"):
                with st.spinner("Geçmiş maçlar taranıyor..."):
                    sonuc_test = basari_orani_backtest(df_matches, df_teams)
                    if sonuc_test["toplam"] > 0:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Test Edilen", sonuc_test["toplam"])
                        c2.metric("Doğru", sonuc_test["basarili"])
                        c3.metric("Başarı Oranı", f"%{sonuc_test['oran']}")
                        st.dataframe(pd.DataFrame(sonuc_test["detaylar"]), use_container_width=True, hide_index=True)
                    else:
                        st.info("Test edilecek maç bulunamadı.")

# --- MOD 2 ---
elif mod_secimi == "⚡ Tüm Dünyadan Karma Kuponlar":
    st.subheader("🌍 Tüm Elit Ligler Taranıyor: En Yüksek Güvenli Seçimler")
    if st.button("🚀 Tüm Dünyayı Tara ve Elmas Kuponu Oluştur"):
        elmas_havuz = []
        bar = st.progress(0)
        lig_list = list(LIG_REHBERI.items())
        for idx, (lig_ad, paths) in enumerate(lig_list):
            m_df, t_df = lig_verisi_oku(paths["matches"], paths["teams"], paths["teams2"])
            if m_df is not None and t_df is not None:
                for _, r in m_df[m_df['status'] == 'incomplete'].head(6).iterrows():
                    ev, dep = r['home_team_name'], r['away_team_name']
                    res = gelismis_poisson_analizi(ev, dep, t_df, df_matches=m_df)
                    if res:
                        if res["prob_ust25"] >= 65: tercih, guven = "2.5 ÜST", res["prob_ust25"]
                        elif res["prob_ms1"] >= 55: tercih, guven = "MS 1", res["prob_ms1"]
                        elif res["prob_ms2"] >= 55: tercih, guven = "MS 2", res["prob_ms2"]
                        else: tercih, guven = "Denge / Pas", res["skor_ihtimali"]
                        
                        if guven >= 60:
                            elmas_havuz.append({"Lig": lig_ad, "Tarih": r.get('date_GMT', '-'), "Maç": f"{ev} - {dep}", "Tahmin": tercih, "Skor": res["tahmin_skor"], "Güven Oranı": f"%{guven}", "_sira": guven})
            bar.progress((idx + 1) / len(lig_list))
            
        if elmas_havuz:
            df_elmas = pd.DataFrame(elmas_havuz).sort_values(by="_sira", ascending=False).drop(columns=["_sira"])
            st.success(f"💎 Toplam {len(df_elmas)} yüksek olasılıklı maç bulundu!")
            st.dataframe(df_elmas.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("Kriterleri aşan maç bulunamadı.")

# --- MOD 3 ---
elif mod_secimi == "🤖 Özel Robotlar Laboratuvarı":
    st.title("🤖 Özel Algoritmik Robotlar Merkezi")
    col_ayar1, col_ayar2 = st.columns(2)
    with col_ayar1: min_ust_guven = st.slider("⚽ Robot 1 (Gol) Minimum Güven (%):", 55, 80, 62)
    with col_ayar2: min_taraf_guven = st.slider("🎯 Robot 2 (Taraf) Minimum Güven (%):", 45, 75, 52)
        
    if st.button("🚀 İki Robotu Aynı Anda Sahaya Sür"):
        robot_gol_havuzu, robot_taraf_havuzu = [], []
        progress_bar = st.progress(0)
        lig_listesi = list(LIG_REHBERI.items())
        yasakli = ["champions", "europa", "conference", "cup", "kupa", "pokal", "copa", "coppa"]

        for idx, (lig_ad, paths) in enumerate(lig_listesi):
            if any(y in lig_ad.lower() for y in yasakli):
                progress_bar.progress((idx + 1) / len(lig_listesi))
                continue

            m_df, t_df = lig_verisi_oku(paths["matches"], paths["teams"], paths["teams2"])
            if m_df is not None and t_df is not None:
                for _, r in m_df[m_df['status'] == 'incomplete'].head(8).iterrows():
                    ev, dep = r['home_team_name'], r['away_team_name']
                    res = gelismis_poisson_analizi(ev, dep, t_df, df_matches=m_df)
                    if res:
                        gol_karar = robot_alt_ust_uzmani(res, ust_esik=min_ust_guven, alt_esik=min_ust_guven)
                        if gol_karar:
                            robot_gol_havuzu.append({"lig": lig_ad, "tarih": r.get('date_GMT', '-'), "mac": f"{ev} - {dep}", "tercih": gol_karar["tercih"], "skor": res["tahmin_skor"], "ihtimal": gol_karar["guven"], "detay": gol_karar["detay"]})
                        taraf_karar = robot_taraf_avcisi(res, ms_esik=min_taraf_guven)
                        if taraf_karar:
                            robot_taraf_havuzu.append({"lig": lig_ad, "tarih": r.get('date_GMT', '-'), "mac": f"{ev} - {dep}", "tercih": taraf_karar["tercih"], "skor": res["tahmin_skor"], "ihtimal": taraf_karar["guven"], "detay": taraf_karar["detay"]})
            progress_bar.progress((idx + 1) / len(lig_listesi))
            
        st.divider()
        tab_robot_gol, tab_robot_taraf, tab_kuponlar = st.tabs(["⚽ Robot 1: Alt / Üst Radarı", "🎯 Robot 2: Maç Sonucu Avcısı", "📋 Robotik 5'er Maçlık Kuponlar"])
        
        with tab_robot_gol:
            if robot_gol_havuzu: st.dataframe(pd.DataFrame(robot_gol_havuzu).sort_values(by="ihtimal", ascending=False), use_container_width=True)
            else: st.info("Gol maçı bulunamadı.")
        with tab_robot_taraf:
            if robot_taraf_havuzu: st.dataframe(pd.DataFrame(robot_taraf_havuzu).sort_values(by="ihtimal", ascending=False), use_container_width=True)
            else: st.info("Taraf maçı bulunamadı.")

        with tab_kuponlar:
            st.subheader("🎯 En Yüksek İhtimalli 5'er Maçlık Robotik Paketler")
            ust_banko, ust_ideal = besli_kupon_olustur(robot_gol_havuzu, "2.5 ÜST")
            alt_banko, alt_ideal = besli_kupon_olustur(robot_gol_havuzu, "2.5 ALT")
            ms1_banko, ms1_ideal = besli_kupon_olustur(robot_taraf_havuzu, "MS 1")
            ms2_banko, ms2_ideal = besli_kupon_olustur(robot_taraf_havuzu, "MS 2")

            def kupon_goster(baslik, mac_listesi, renk="#58A6FF"):
                st.markdown(f"<h4 style='color:{renk};'>{baslik} ({len(mac_listesi)}/5)</h4>", unsafe_allow_html=True)
                if mac_listesi:
                    tablo = [{"Maç": m["mac"], "Lig": m["lig"], "Tercih": m["tercih"], "Tahmin Skor": m["skor"], "Güven": f"%{m['ihtimal']}"} for m in mac_listesi]
                    st.dataframe(pd.DataFrame(tablo), hide_index=True, use_container_width=True)
                else: st.caption("Yeterli maç yok.")

            kupon_goster("🔥 2.5 Üst Banko", ust_banko, "#2ea043")
            
            # Tek Tıkla Dışa Aktarma (TXT & Excel)
            if ust_banko:
                txt_data = kuponu_metne_cevir(ust_banko)
                df_exp = pd.DataFrame(ust_banko)
                col_ex1, col_ex2 = st.columns(2)
                with col_ex1:
                    st.download_button("📄 Kuponu TXT İndir", data=txt_data, file_name="banko_ust_kupon.txt", mime="text/plain", use_container_width=True)
                with col_ex2:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df_exp.to_excel(writer, index=False, sheet_name='Kupon')
                    st.download_button("📊 Kuponu Excel İndir", data=buffer.getvalue(), file_name="banko_ust_kupon.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

# ==========================================
# --- MOD 4: NESİNE ORAN ARALIĞI & EĞİLİM ANALİZİ ---
# ==========================================
elif mod_secimi == "💰 Nesine & Oran Kıyaslama":
    st.title("💰 Nesine Oran Aralığı & İstatistiksel Eğilim Analiz Merkezi")
    st.markdown("""
    Bu modül, Nesine bültenindeki maçları **takım ismi eşleştirmesi yapmadan** doğrudan **açılan oranlara (MS1, MSX, MS2, Alt/Üst)** göre tarar. 
    İstediğiniz oran aralıklarındaki maçları filtreleyerek piyasa eğilimlerini analiz eder!
    """)

    tab_arsiv, tab_oran_analiz = st.tabs(["📦 Bülten Oto-Arşivleyici", "📊 Oran Aralığı Eğilim Analizörü"])

    with tab_arsiv:
        st.subheader("📦 Otomatik Bülten İndirme ve Saklama Servisi")
        if st.button("📥 Nesine Bültenini Şimdi İndir ve Arşivle", use_container_width=True):
            with st.spinner("Bülten indiriliyor..."):
                try:
                    resp = requests.get(NESINE_URL, headers=NESINE_HEADERS, timeout=12)
                    if resp.status_code == 200 and len(resp.text) > 1000:
                        tarih_etiketi = datetime.now().strftime("%Y-%m-%d_%H-%M")
                        dosya_adi = os.path.join(ARSIV_DIR, f"nesine_bulten_{tarih_etiketi}.json")
                        with open(dosya_adi, "w", encoding="utf-8") as f:
                            f.write(resp.text)
                        st.success(f"✅ Bülten arşive kaydedildi: `{dosya_adi}`")
                        st.session_state["nesine_json_hafiza"] = resp.text
                    else:
                        st.error("❌ Veri boş döndü.")
                except Exception as e:
                    st.error(f"Hata: {e}")

        mevcut_arsivler = glob.glob(os.path.join(ARSIV_DIR, "*.json"))
        if mevcut_arsivler:
            secilen_arsiv = st.selectbox("Arşivden Bir Bülten Seçin:", sorted(mevcut_arsivler, reverse=True))
            if secilen_arsiv and st.button("📂 Seçilen Arşivi Yükle"):
                with open(secilen_arsiv, "r", encoding="utf-8") as f:
                    st.session_state["nesine_json_hafiza"] = f.read()
                st.success("✅ Arşiv belleğe yüklendi!")

    with tab_oran_analiz:
        st.subheader("📊 Nesine Oran Filtreleme ve Eğilim Süzgeci")
        
        with st.expander("📋 Ham JSON / Bülten Verisi Giriş Kutusu", expanded=False):
            manuel_giris = st.text_area("JSON Yanıtı:", value=st.session_state.get("nesine_json_hafiza", ""), height=100)
            if manuel_giris.strip():
                st.session_state["nesine_json_hafiza"] = manuel_giris.strip()

        st.markdown("#### 🎛️ Oran Aralıklarını Belirleyin")
        c1, c2, c3 = st.columns(3)
        with c1:
            ms1_min, ms1_max = st.slider("🏠 MS 1 Oran Aralığı:", 1.01, 10.0, (1.40, 2.50))
        with c2:
            ms2_min, ms2_max = st.slider("✈️ MS 2 Oran Aralığı:", 1.01, 10.0, (1.50, 4.00))
        with c3:
            ust_min, ust_max = st.slider("⚽ 2.5 Üst Oran Aralığı:", 1.10, 5.0, (1.40, 2.20))

        def nesine_tum_oranlari_coz(ham_metin):
            mac_listesi = []
            if not ham_metin: return mac_listesi
            try:
                veri = json.loads(ham_metin)
            except:
                return mac_listesi

            events = veri.get("EA") or (veri.get("sg", {}).get("EA", [])) if isinstance(veri, dict) else veri

            for ev_obj in events:
                if not isinstance(ev_obj, dict): continue
                if ev_obj.get("TYPE", -1) != 1: continue # Sadece futbol

                ev = ev_obj.get("HN")
                dep = ev_obj.get("AN")
                etkinlik_adi = ev_obj.get("ENN", "")
                tarih = ev_obj.get("D", "-")
                saat = ev_obj.get("T", "-")

                if not (ev and dep) and " - " in etkinlik_adi:
                    p = etkinlik_adi.split(" - ", 1)
                    ev, dep = p[0].strip(), p[1].strip()

                if ev and dep:
                    ms1, msx, ms2, ust, alt, kg_var, kg_yok = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    for m in ev_obj.get("MA", []):
                        if not isinstance(m, dict): continue
                        mtid = m.get("MTID") or m.get("MT")
                        sov = float(str(m.get("SOV", 0.0)).replace(",", "."))
                        m_ad = str(m.get("MN") or m.get("N") or "").lower()
                        secimler = m.get("OCA", [])
                        
                        # 1: Maç Sonucu (1X2)
                        if mtid == 1 or (len(secimler) == 3 and sov == 0.0 and ms1 == 0.0 and "karşılıklı" not in m_ad):
                            for s in secimler:
                                if not isinstance(s, dict): continue
                                no = s.get("NO") or s.get("N")
                                oran = float(str(s.get("O", 0)).replace(",", "."))
                                if no == 1: ms1 = oran
                                elif no == 2: msx = oran
                                elif no == 3: ms2 = oran

                        # 2.5 Alt / Üst (SOV değeri tam 2.50 olan pazar)
                        if sov == 2.50 and len(secimler) >= 2:
                            for s in secimler:
                                if not isinstance(s, dict): continue
                                no = s.get("NO") or s.get("N")
                                oran = float(str(s.get("O", 0)).replace(",", "."))
                                if no == 1: alt = oran
                                elif no == 2: ust = oran

                        # Karşılıklı Gol (KG Var / Yok) - Sadece gerçek KG pazarları (Genellikle MTID 38 veya adı geçenler)
                        if mtid == 38 or "karşılıklı" in m_ad or m_ad == "kg":
                            if len(secimler) == 2: # KG pazarı tam olarak 2 seçeneklidir (Var / Yok)
                                for s in secimler:
                                    if not isinstance(s, dict): continue
                                    no = s.get("NO") or s.get("N")
                                    secim_ad = str(s.get("ON") or s.get("N") or "").lower()
                                    oran = float(str(s.get("O", 0)).replace(",", "."))
                                    
                                    if no == 1 or "var" in secim_ad:
                                        kg_var = oran
                                    elif no == 2 or "yok" in secim_ad:
                                        kg_yok = oran

                    if ms1 > 1.0:
                        mac_listesi.append({
                            "tarih": f"{tarih} {saat}",
                            "mac": f"{ev} - {dep}",
                            "ms1": ms1, "msx": msx, "ms2": ms2,
                            "ust": ust, "alt": alt, 
                            "kg_var": kg_var, "kg_yok": kg_yok
                        })
            return mac_listesi

        if st.button("🚀 Bülteni Tara ve Belirtilen Oran Aralığındaki Maçları Listele", use_container_width=True):
            aktif_veri = st.session_state.get("nesine_json_hafiza", "")
            if not aktif_veri:
                st.error("❌ Önce bülten yükleyin veya indirin.")
            else:
                tum_maclar = nesine_tum_oranlari_coz(aktif_veri)
                if not tum_maclar:
                    st.warning("⚠️ Bültrnde maç bulunamadı.")
                else:
                    filtrelenmis = []
                    for m in tum_maclar:
                        # Kullanıcının seçtiği oran filtreleri
                        match_ms1 = ms1_min <= m["ms1"] <= ms1_max
                        match_ms2 = ms2_min <= m["ms2"] <= ms2_max
                        match_ust = ust_min <= m["ust"] <= ust_max

                        if match_ms1 or match_ms2 or match_ust:
                            # Oranlara göre piyasa beklentisi (İstatistiksel Eğilim Sinyali)
                            if m["ust"] > 0 and m["ust"] < 1.65:
                                egilim = "🔥 Piyasa Beklentisi: YÜKSEK ÜST"
                            elif m["ms1"] > 1.0 and m["ms1"] < 1.60:
                                egilim = "🏠 Piyasa Beklentisi: NET FAVORİ (MS1)"
                            elif m["ms2"] > 1.0 and m["ms2"] < 2.00:
                                egilim = "✈️ Piyasa Beklentisi: DEPLASMAN FAVORİ"
                            else:
                                egilim = "⚖️ Denge / Sürpriz Oran Seti"

                            filtrelenmis.append({
                                "Tarih": m["tarih"],
                                "Maç": m["mac"],
                                "MS1": m["ms1"],
                                "MSX": m["msx"],
                                "MS2": m["ms2"],
                                "2.5 Üst": m["ust"],
                                "2.5 Alt": m["alt"] if m["alt"] > 0 else "-",
                                "KG Var": m["kg_var"] if m["kg_var"] > 0 else "-",
                                "KG Yok": m["kg_yok"] if m["kg_yok"] > 0 else "-",
                                "Piyasa Sinyali": egilim
                            })

                    if filtrelenmis:
                        df_filt = pd.DataFrame(filtrelenmis)
                        st.success(f"🎯 Belirttiğiniz oran aralığına uyan **{len(df_filt)}** maç bulundu!")
                        st.dataframe(df_filt, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Girdiğiniz oran aralıklarında eşleşen maç bulunamadı. Aralıkları biraz genişletebilirsiniz.")
