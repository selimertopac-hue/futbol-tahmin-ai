import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import json
import requests
import subprocess
import io
from datetime import datetime

st.set_page_config(page_title="UltraSkor Pro: Nesine Oran İstihbarat Terminali", page_icon="💰", layout="wide")

ARSIV_DIR = "bulten_arsivleri"
os.makedirs(ARSIV_DIR, exist_ok=True)

# Nesine API Sabitleri
NESINE_URL = "https://cdnbulten.nesine.com/api/bulten/getprebultenfull"
NESINE_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "authorization": "Basic RDQ3MDc4RDMtNjcwQi00OUJBLTgxNUYtM0IyMjI2MTM1MTZCOkI4MzJCQjZGLTQwMjgtNDIwNS05NjFELTg1N0QxRTZEOTk0OA==",
    "content-type": "application/json; charset=utf-8",
    "origin": "https://www.nesine.com",
    "priority": "u=1, i",
    "referer": "https://www.nesine.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
}

# ==========================================
# 1. NESİNE BÜLTEN ÇÖZÜCÜ MOTORU (TÜM ORANLAR)
# ==========================================
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
        if ev_obj.get("TYPE", -1) != 1: continue # Sadece futbol maçları

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

                # Karşılıklı Gol (KG Var / Yok)
                if mtid == 38 or "karşılıklı" in m_ad or m_ad == "kg":
                    if len(secimler) == 2:
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

def kuponu_metne_cevir(mac_listesi):
    metin = "=== NESİNE KOMBİNASYON ORAN ANALİZ RAPORU ===\n"
    metin += f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    metin += "-" * 40 + "\n\n"
    for i, m in enumerate(mac_listesi, 1):
        metin += f"{i}. Maç: {m['Maç']}\n"
        metin += f"   MS1: {m['MS1']} | MSX: {m['MSX']} | MS2: {m['MS2']}\n"
        metin += f"   Alt: {m['2.5 Alt']} | Üst: {m['2.5 Üst']} | KG Var: {m['KG Var']} | KG Yok: {m['KG Yok']}\n"
        metin += f"   Sinyal: {m['Piyasa Sinyali']}\n"
        metin += "-" * 40 + "\n"
    return metin

# ==========================================
# 2. ARAYÜZ VE MODÜLLER
# ==========================================
st.title("🌐 UltraSkor Pro: Nesine Oran Analiz & Arşiv Terminali")

st.sidebar.title("🎛️ Operasyon Vizörü")
mod_secimi = st.sidebar.radio(
    "Operasyon Modu Seçin:",
    [
        "📦 Bülten Arşivi & Oto-İndirici",
        "📊 Kombinasyon Panoraması & Filtreleme"
    ]
)

# --- MOD 1: BÜLTEN ARŞİVİ & OTO İNDİRİCİ ---
if mod_secimi == "📦 Bülten Arşivi & Oto-İndirici":
    st.subheader("📦 Salı & Perşembe Otomatik Bülten Arşivi")
    st.markdown(f"GitHub Actions tarafından otomatik olarak indirilen veya manuel çektiğiniz bültenler `/{ARSIV_DIR}` klasöründe saklanır.")

    if st.button("📥 Nesine Bültenini Şimdi İndir ve Arşivle", use_container_width=True):
        with st.spinner("Bülten indiriliyor ve arşive kaydediliyor..."):
            try:
                resp = requests.get(NESINE_URL, headers=NESINE_HEADERS, timeout=12)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    tarih_etiketi = datetime.now().strftime("%Y-%m-%d_%H-%M")
                    dosya_adi = os.path.join(ARSIV_DIR, f"nesine_bulten_{tarih_etiketi}.json")
                    with open(dosya_adi, "w", encoding="utf-8") as f:
                        f.write(resp.text)
                    st.success(f"✅ Bülten başarıyla indirildi ve arşive kaydedildi!\nDosya: `{dosya_adi}`")
                    st.session_state["nesine_json_hafiza"] = resp.text
                else:
                    st.error("❌ Bülten verisi boş döndü.")
            except Exception as e:
                st.error(f"Bağlantı hatası: {e}")

    mevcut_arsivler = glob.glob(os.path.join(ARSIV_DIR, "*.json"))
    if mevcut_arsivler:
        st.markdown("### 📂 Arşivdeki Bültenler")
        secilen_arsiv = st.selectbox("Arşivden Tekil Bülten Yükle:", sorted(mevcut_arsivler, reverse=True))
        if secilen_arsiv and st.button("📂 Seçilen Arşiv Bültenini Yükle"):
            with open(secilen_arsiv, "r", encoding="utf-8") as f:
                st.session_state["nesine_json_hafiza"] = f.read()
            st.success(f"✅ `{secilen_arsiv}` arşivi belleğe yüklendi!")

# --- MOD 2: KOMBİNASYON PANORAMASI & FİLTRELEME ---
elif mod_secimi == "📊 Kombinasyon Panoraması & Filtreleme":
    st.title("📊 Nesine Çoklu Bülten & Detaylı Kombinasyon Filtreleme Merkezi")
    st.markdown("""
    Arşivden dilediğiniz bültenleri seçip ortak havuz oluşturun. Aşağıdan **istediğiniz oran seçeneklerini tek tek seçip (VE mantığıyla)** çapraz arama yapın!
    """)

    mevcut_arsivler = glob.glob(os.path.join(ARSIV_DIR, "*.json"))

    st.markdown("#### 📂 Veri Kaynağı ve Karma Analiz Modu")
    veri_kaynagi = st.radio(
        "Analiz edilecek bülten kaynağını seçin:",
        ["Aktif Bellekteki / Yüklenen Tek Bülten", "Arşivden Çoklu Bülten Seç (Karma Analiz)", "Tüm Arşivdeki Bültenleri Birleştir (Global Karma Analiz)"],
        horizontal=False
    )

    secilen_maclar_ham = []

    if veri_kaynagi == "Aktif Bellekteki / Yüklenen Tek Bülten":
        with st.expander("📋 Ham JSON / Bülten Verisi Giriş Kutusu", expanded=False):
            manuel_giris = st.text_area("JSON Yanıtı:", value=st.session_state.get("nesine_json_hafiza", ""), height=100)
            if manuel_giris.strip():
                st.session_state["nesine_json_hafiza"] = manuel_giris.strip()
        secilen_maclar_ham = nesine_tum_oranlari_coz(st.session_state.get("nesine_json_hafiza", ""))

    elif veri_kaynagi == "Arşivden Çoklu Bülten Seç (Karma Analiz)":
        if not mevcut_arsivler:
            st.warning("⚠️ Arşiv klasöründe hiç JSON bülteni bulunamadı.")
        else:
            secilen_dosyalar = st.multiselect(
                "Analize dahil etmek istediğiniz bültenleri seçin:",
                sorted(mevcut_arsivler, reverse=True)
            )
            for dosya in secilen_dosyalar:
                with open(dosya, "r", encoding="utf-8") as f:
                    secilen_maclar_ham.extend(nesine_tum_oranlari_coz(f.read()))

    elif veri_kaynagi == "Tüm Arşivdeki Bültenleri Birleştir (Global Karma Analiz)":
        if not mevcut_arsivler:
            st.warning("⚠️ Arşivde bülten bulunamadı.")
        else:
            for dosya in mevcut_arsivler:
                with open(dosya, "r", encoding="utf-8") as f:
                    secilen_maclar_ham.extend(nesine_tum_oranlari_coz(f.read()))

    # Mükerrer maçları temizleme (Deduplication)
    gorulen_maclar = set()
    benzersiz_maclar = []
    for m in secilen_maclar_ham:
        kimlik = (m["mac"], m["ms1"], m["ms2"])
        if kimlik not in gorulen_maclar:
            gorulen_maclar.add(kimlik)
            benzersiz_maclar.append(m)

    st.divider()
    st.markdown(f"📊 **Toplam Havuzdaki Benzersiz Maç Sayısı:** {len(benzersiz_maclar)}")

    st.markdown("### 🎛️ Bağımsız Seçenekli Kombinasyon Filtre Paneli")
    st.markdown("İstediğiniz oran türünü ayrı ayrı işaretleyin. İşaretlenen tüm filtreler **birlikte (VE / AND)** aranacaktır.")

    # 1. Satır: Maç Sonucu Seçenekleri (MS1, MSX, MS2)
    st.markdown("#### 🏠 Maç Sonucu (1X2) Filtreleri")
    c_ms1, c_msx, c_ms2 = st.columns(3)
    with c_ms1:
        f_ms1 = st.checkbox("MS 1 Filtrele", value=False)
        ms1_min, ms1_max = st.slider("MS 1 Aralığı:", 1.01, 10.0, (1.30, 3.00), disabled=not f_ms1)
    with c_msx:
        f_msx = st.checkbox("MS X Filtrele", value=False)
        msx_min, msx_max = st.slider("MS X Aralığı:", 2.00, 6.0, (2.80, 3.60), disabled=not f_msx)
    with c_ms2:
        f_ms2 = st.checkbox("MS 2 Filtrele", value=False)
        ms2_min, ms2_max = st.slider("MS 2 Aralığı:", 1.01, 10.0, (1.50, 4.50), disabled=not f_ms2)

    st.divider()

    # 2. Satır: Gol Alt / Üst Seçenekleri (2.5 Üst, 2.5 Alt)
    st.markdown("#### ⚽ Gol Alt / Üst Filtreleri")
    c_ust, c_alt = st.columns(2)
    with c_ust:
        f_ust = st.checkbox("2.5 Üst Filtrele", value=False)
        ust_min, ust_max = st.slider("2.5 Üst Aralığı:", 1.10, 5.0, (1.40, 2.30), disabled=not f_ust)
    with c_alt:
        f_alt = st.checkbox("2.5 Alt Filtrele", value=False)
        alt_min, alt_max = st.slider("2.5 Alt Aralığı:", 1.10, 5.0, (1.40, 2.30), disabled=not f_alt)

    st.divider()

    # 3. Satır: Karşılıklı Gol Seçenekleri (KG Var, KG Yok)
    st.markdown("#### 🥅 Karşılıklı Gol (KG) Filtreleri")
    c_kgv, c_kgy = st.columns(2)
    with c_kgv:
        f_kgv = st.checkbox("KG Var Filtrele", value=False)
        kgv_min, kgv_max = st.slider("KG Var Aralığı:", 1.20, 3.5, (1.50, 2.10), disabled=not f_kgv)
    with c_kgy:
        f_kgy = st.checkbox("KG Yok Filtrele", value=False)
        kgy_min, kgy_max = st.slider("KG Yok Aralığı:", 1.20, 3.5, (1.50, 2.10), disabled=not f_kgy)

    if st.button("🚀 Kombinasyon Filtresini Çalıştır ve Eşleşenleri Listele", use_container_width=True):
        if not benzersiz_maclar:
            st.error("❌ Analiz edilecek bülten verisi veya maçı bulunamadı.")
        else:
            filtrelenmis = []
            for m in benzersiz_maclar:
                match_uyuyor = True

                # Her bir seçeneği bağımsız ve kümülatif (VE) olarak test et
                if f_ms1 and not (ms1_min <= m["ms1"] <= ms1_max): match_uyuyor = False
                if f_msx and not (msx_min <= m["msx"] <= msx_max): match_uyuyor = False
                if f_ms2 and not (ms2_min <= m["ms2"] <= ms2_max): match_uyuyor = False
                
                if f_ust and (m["ust"] == 0 or not (ust_min <= m["ust"] <= ust_max)): match_uyuyor = False
                if f_alt and (m["alt"] == 0 or not (alt_min <= m["alt"] <= alt_max)): match_uyuyor = False
                
                if f_kgv and (m["kg_var"] == 0 or not (kgv_min <= m["kg_var"] <= kgv_max)): match_uyuyor = False
                if f_kgy and (m["kg_yok"] == 0 or not (kgy_min <= m["kg_yok"] <= kgy_max)): match_uyuyor = False

                if match_uyuyor:
                    if m["ust"] > 0 and m["ust"] < 1.65:
                        egilim = "🔥 Piyasa Beklentisi: YÜKSEK ÜST"
                    elif m["ms1"] > 1.0 and m["ms1"] < 1.55:
                        egilim = "🏠 Piyasa Beklentisi: NET FAVORİ (MS1)"
                    elif m["ms2"] > 1.0 and m["ms2"] < 1.85:
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
                st.success(f"🎯 Kombinasyon kriterlerinize uyan **{len(df_filt)}** maç bulundu!")
                st.dataframe(df_filt, use_container_width=True, hide_index=True)

                # Dışa Aktarma Butonları
                st.divider()
                st.subheader("📤 Filtrelenen Sonuçları Dışa Aktar")
                txt_ciktisi = kuponu_metne_cevir(filtrelenmis)
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.download_button(
                        label="📄 Liste Olarak (.txt) İndir",
                        data=txt_ciktisi,
                        file_name="kombinasyon_oran_analiz.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                with col_d2:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df_filt.to_excel(writer, sheet_name='KombinasyonAnaliz', index=False)
                    st.download_button(
                        label="📊 Excel Olarak (.xlsx) İndir",
                        data=buffer.getvalue(),
                        file_name="kombinasyon_oran_analiz.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.warning("Seçtiğiniz kriterlerin tamamını aynı anda sağlayan maç bulunamadı. Kriterleri veya oran aralıklarını esnetebilirsiniz.")
