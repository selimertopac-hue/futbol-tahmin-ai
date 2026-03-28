# ... (Üstteki tüm Canlı Skor, Global AI ve Lig Odaklı kodları aynı kalsın)

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Onur Listesi & Başarı Karnesi")
    st.markdown("Sitemizin yapay zeka algoritmalarının geçmiş performansları ve efsanevi tahminleri burada sergilenir.")

    # --- 1. HAFTALIK PERFORMANS TABLOSU ---
    st.subheader("📊 Haftalık Başarı Oranları")
    
    # Verileri manuel veya dinamik olarak buraya işliyoruz
    performans_data = {
        "Hafta": ["1. Hafta", "2. Hafta", "3. Hafta (Milli Ara)"],
        "Standart AI": ["%72", "%68", "-"],
        "Spektrum AI": ["%76", "%74", "-"],
        "Nexus AI": ["%84 🥇", "%79 🥇", "-"]
    }
    df_perf = pd.DataFrame(performans_data)
    
    st.markdown("""
        <style>
        .perf-table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 10px; overflow: hidden; }
        .perf-table th { background: #30363d; color: #58A6FF; padding: 12px; text-align: center; }
        .perf-table td { padding: 12px; text-align: center; border-bottom: 1px solid #30363d; }
        .best-performer { color: #D4AF37; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)
    
    # Şık Tablo Gösterimi
    st.table(df_perf)

    st.markdown("---")

    # --- 2. EFSANEVİ TAHMİNLER (TOP 5) ---
    st.subheader("🎖️ Unutulmaz Tahminler (En Yüksek Oranlılar)")
    
    efsane_maclar = [
        {"mac": "Liverpool - Real Madrid", "tahmin": "2 - 5", "oran": "Çok Yüksek", "not": "Nexus AI skoru tam isabet bildi."},
        {"mac": "Man. City - Arsenal", "tahmin": "0 - 0", "oran": "Kritik", "not": "Spektrum AI savunma disiplinini önceden sezdi."},
        {"mac": "Napoli - AC Milan", "tahmin": "0 - 4", "oran": "Sürpriz", "not": "Sürpriz Radarı %92 güvenle Milan dedi."},
        {"mac": "Galatasaray - Fenerbahçe", "tahmin": "1 - 2", "oran": "Derbi", "not": "Derbi xG analizinde FB galibiyeti parladı."},
        {"mac": "Bayern - Dortmund", "tahmin": "4 - 2", "oran": "Banko", "not": "Gol Festivali (Üst) tahmini erkenden geldi."}
    ]

    cols = st.columns(1)
    for m in efsane_maclar:
        st.markdown(f"""
        <div style="background: #1c2128; border-left: 5px solid #D4AF37; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between;">
                <span style="font-weight: bold; color: #C9D1D9;">⚽ {m['mac']}</span>
                <span style="background: #D4AF37; color: black; padding: 2px 8px; border-radius: 5px; font-size: 0.7rem; font-weight: bold;">{m['oran']}</span>
            </div>
            <div style="color: #3fb950; font-size: 1.1rem; font-weight: bold; margin-top: 5px;">Tahmin: {m['tahmin']}</div>
            <div style="color: #8B949E; font-size: 0.85rem; font-style: italic;">{m['not']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.info("💡 Not: Başarı oranları, maçların MS (Maç Sonucu) sonuçlarına göre her Pazartesi güncellenir.")
