with col2:
    st.subheader("📅 Stratejik Analiz Paneli")
    if gelecek:
        for m in gelecek[:8]:
            ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
            res = analiz_et(ev, dep, m_data)
            
            with st.expander(f"🔍 {ev} - {dep} (Detaylı Analiz)"):
                # Sol: İstatistikler, Sağ: Bahis Hesaplayıcı
                c_stats, c_bet = st.columns([1.2, 1])
                
                with c_stats:
                    st.write(f"📊 **AI Tahmini:** {res['Skor']}")
                    st.write(f"🏠 Ev: %{res['Ev']:.1f} | 🤝 Ber: %{res['Ber']:.1f} | 🚀 Dep: %{res['Dep']:.1f}")
                    st.progress(res['Ev']/100)
                
                with c_bet:
                    st.markdown("🔍 **Değer Analizi Yap**")
                    oran = st.number_input(f"Oran Gir:", min_value=1.01, value=1.85, key=f"inp_{ev}")
                    
                    # ANALİZ BUTONU
                    if st.button(f"Hesapla: {ev}", key=f"btn_{ev}"):
                        avantaj = ((res['Ev'] / 100) * oran) - 1
                        
                        if avantaj > 0.15:
                            st.balloons() # Büyük fırsatta balonlar uçsun!
                            st.success(f"💎 ELMAS FIRSAT! \n\n Avantaj: %{avantaj*100:.1f}")
                            st.write("🤖 AI Notu: Bahis şirketi bu maçta ev sahibini çok küçümsemiş!")
                        elif avantaj > 0:
                            st.warning(f"✅ Değerli Bahis \n\n Avantaj: %{avantaj*100:.1f}")
                        else:
                            st.error("❌ Değer Yok \n\n Bu oran risk almaya değmez.")
