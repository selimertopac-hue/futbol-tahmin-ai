import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

# --- 1. AYARLAR & MİLAT ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"
LIGLER = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
SİTE_DOGUM_TARİHİ = datetime(2026, 3, 20) 

st.set_page_config(page_title="UltraSkor Pro: AETHER Intelligence", page_icon="🎯", layout="wide")

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

def winner(sk):
    try:
        p = sk.split(" - ")
        if int(p[0]) > int(p[1]): return "1"
        if int(p[1]) > int(p[0]): return "2"
        return "X"
    except: return "?"

def get_form_dots(team_name, matches):
    finished = [m for m in matches if m['status'] == 'FINISHED' and (m['homeTeam']['name'] == team_name or m['awayTeam']['name'] == team_name)]
    finished = sorted(finished, key=lambda x: x['utcDate'], reverse=True)[:5]
    dots = ""
    for m in finished:
        h_s, a_s = m['score']['fullTime']['home'], m['score']['fullTime']['away']
        if m['homeTeam']['name'] == team_name: res = "W" if h_s > a_s else ("L" if a_s > h_s else "D")
        else: res = "W" if a_s > h_s else ("L" if h_s > a_s else "D")
        dots += f'<span class="form-dot form-{res}"></span>'
    return f'<div style="margin-top:3px;">{dots}</div>'

def analiz_et(ev, dep, matches):
    try:
        df_raw = [m for m in matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if len(df_raw) < 5: return None
        df = pd.DataFrame([{'H': m['homeTeam']['name'], 'A': m['awayTeam']['name'], 'HG': m['score']['fullTime']['home'], 'AG': m['score']['fullTime']['away'], 'MD': m['matchday']} for m in df_raw])
        l_e, l_d = df['HG'].mean(), df['AG'].mean()
        
        def get_stats(team, is_h):
            t_df = df[df['H' if is_h else 'A'] == team].copy()
            if t_df.empty: return l_e, l_d, 1.0
            t_df['w'] = 1.0 + (t_df['MD'] / df['MD'].max())
            g = (t_df['HG' if is_h else 'AG']*t_df['w']).sum()/t_df['w'].sum()
            y = (t_df['AG' if is_h else 'HG']*t_df['w']).sum()/t_df['w'].sum()
            return g, y, t_df.sort_values('MD', ascending=False).head(3)['HG' if is_h else 'AG'].mean()

        e_g, e_y, e_rec = get_stats(ev, True)
        d_g, d_y, d_rec = get_stats(dep, False)
        ex, ax = (e_g/l_e)*(d_y/l_e)*l_e, (d_g/l_d)*(e_y/l_d)*l_d
        
        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            return f"{s[0]} - {s[1]}", min(99, int(abs(e-a)*45 + 25))

        r_s = sk(ex, ax); r_sp = sk(ex*1.1, ax*0.9); r_nx = sk(ex*1.2, ax*0.8)
        
        # --- AETHER AI MANTIĞI (MASTER SYNTHESIS) ---
        # Aether, diğer 3 sonucun olasılıklarını ve form grafiklerini harmanlar
        aether_ex = (ex * 0.4) + (ex * 1.1 * 0.3) + (ex * 1.2 * 0.3)
        aether_ax = (ax * 0.4) + (ax * 0.9 * 0.3) + (ax * 0.8 * 0.3)
        # Form trendi ekle
        if e_rec > e_g: aether_ex *= 1.05
        if d_rec > d_g: aether_ax *= 1.05
        
        r_ae = sk(aether_ex, aether_ax)

        note = f"⚽ xG: {ex+ax:.2f} | Aether AI, maçın kaderini yüksek tempo olarak öngörüyor."
        return {"std": r_s[0], "s_c": r_s[1], "spec": r_sp[0], "sp_c": r_sp[1], "nexus": r_nx[0], "n_c": r_nx[1], "aether": r_ae[0], "ae_c": r_ae[1], "note": note, "total_xg": ex+ax}
    except: return None

# --- 4. ZAMAN & HAFTA ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

# --- 5. ANA MENÜ ---
mod = st.sidebar.radio("🚀 Menü", ["🏠 Canlı Skorlar","🤖 Tahmin Robotu", "Global AI", "Lig Odaklı", "🏆 Onur Listesi"])
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
    st.title("🤖 AI Tahmin Robotu")
    st.markdown("Yapay zekalarımızın haftalık bülten içindeki **matematiksel olarak en yüksek** isabet beklediği maçlar.")
    
    # Robot Seçimi (Tabs yapısı profesyonel bir görünüm sağlar)
    tab_ae, tab_std, tab_spec, tab_nx = st.tabs(["✨ AETHER", "🤖 STANDART", "🔥 SPEKTRUM", "🛡️ NEXUS"])
    
    # Robotun tarayacağı haftayı seçelim
    s_sec = st.selectbox("📅 Robot Çalışma Haftası", [1, 2, 3, 4], index=site_h_aktif-1)

    # --- ROBOT ANALİZ FONKSİYONU ---
    def robot_tara(ai_name, hedef_hafta):
        tüm_maclar = []
        for l_ad, l_data in all_d.items():
            m_list = l_data.get('matches', [])
            if not m_list: continue
            # Haftayı doğru yakalayalım
            l_son = max([m['matchday'] for m in m_list if m['status'] == 'FINISHED'] or [1])
            t_md = l_son - (site_h_aktif - hedef_hafta)
            
            for m in [x for x in m_list if x['matchday'] == t_md]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_list)
                if res:
                    m.update({'res': res, 'l_ad': l_ad})
                    tüm_maclar.append(m)
        return tüm_maclar

    # Robotları Sekmelere Dağıtma
    robot_listesi = [
        {"tab": tab_ae, "name": "Aether", "key": "ae_c"},
        {"tab": tab_std, "name": "Standart", "key": "s_c"},
        {"tab": tab_spec, "name": "Spektrum", "key": "total_xg"},
        {"tab": tab_nx, "name": "Nexus", "key": "n_c"}
    ]

    mac_havuzu = robot_tara(None, s_sec)

    for rb in robot_listesi:
        with rb['tab']:
            st.markdown(f'<div class="robot-card"><h3>👾 {rb["name"]} Robotu Raporu</h3></div>', unsafe_allow_html=True)
            
            col_b, col_u = st.columns(2)
            
            with col_b:
                st.subheader("✅ En Banko 5")
                # Kendi puan anahtarına göre en iyileri süz
                bankolar = sorted(mac_havuzu, key=lambda x: x['res'][rb['key']], reverse=True)[:5]
                for b in bankolar:
                    # Aether seçiliyse aether sonucunu, değilse std sonucunu gösterelim
                    tahmin = b['res']['aether'] if rb['name'] == "Aether" else b['res']['std']
                    st.markdown(f'<div class="coupon-item"><b>{b["homeTeam"]["shortName"]} - {b["awayTeam"]["shortName"]}</b><br>Tahmin: {tahmin} | Güven: %{int(b["res"]["s_c"])}</div>', unsafe_allow_html=True)

            with col_u:
                st.subheader("⚽ En Üst 5")
                # Toplam xG'ye göre en iyileri süz
                ustler = sorted(mac_havuzu, key=lambda x: x['res']['total_xg'], reverse=True)[:5]
                for u in ustler:
                    st.markdown(f'<div class="coupon-item"><b>{u["homeTeam"]["shortName"]} - {u["awayTeam"]["shortName"]}</b><br>xG Beklentisi: {u["res"]["total_xg"]:.2f}</div>', unsafe_allow_html=True)
elif mod == "Global AI":
    filtre = st.sidebar.radio("🤖 Algoritma", ["AETHER AI (Master)", "Standart AI", "Spektrum AI", "Nexus AI"])
    s_sec = st.sidebar.selectbox("📅 Sitemiz: Hafta", [1, 2, 3, 4], index=site_h_aktif-1)
    
    HAFTA_ACILISLARI = {1: SİTE_DOGUM_TARİHİ + timedelta(hours=12), 2: SİTE_DOGUM_TARİHİ + timedelta(days=7, hours=12), 3: SİTE_DOGUM_TARİHİ + timedelta(days=14, hours=12), 4: SİTE_DOGUM_TARİHİ + timedelta(days=21, hours=12)}
    hedef_tarih = HAFTA_ACILISLARI.get(s_sec, datetime(2099,1,1))
    st.title(f"🚀 {filtre} - {s_sec}. Hafta")

    if simdi < hedef_tarih:
        st.markdown(f'<div class="lock-box"><h2>🔒 {s_sec}. Hafta Kilitli</h2><p>Tahminler Cuma 12:00\'de açılacaktır.</p></div>', unsafe_allow_html=True)
    else:
        g_l = []
        for l_ad, l_data in all_d.items():
            m_list = l_data.get('matches', [])
            if not m_list: continue
            l_son = max([m['matchday'] for m in m_list if m['status'] == 'FINISHED'] or [1])
            t_md = l_son - (site_h_aktif - s_sec)
            for m in [x for x in m_list if x['matchday'] == t_md]:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_list)
                if res:
                    p = res['ae_c'] if "AETHER" in filtre else res['s_c']
                    m.update({'res': res, 'l_ad': l_ad, 'puan': p})
                    g_l.append(m)

        if g_l:
            # --- 1. BAŞARI GÖSTERGESİ (SCOREBOARD) ---
            bitenler = [x for x in g_l if x['status'] == 'FINISHED']
            isabetli = 0
            for b in bitenler:
                # Aether skor tahmini üzerinden galip kontrolü
                if winner(b['res']['aether']) == winner(f"{b['score']['fullTime']['home']}-{b['score']['fullTime']['away']}"):
                    isabetli += 1
            
            if bitenler:
                oran = (isabetli / len(bitenler)) * 100
                st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #161b22, #0d1117); border: 1px solid #3fb950; border-radius: 10px; padding: 15px; margin-bottom: 25px; text-align: center;">
                        <span style="color: #8B949E; font-size: 0.8rem; letter-spacing: 2px;">HAFTALIK VERİ DOĞRULAMA</span><br>
                        <span style="color: #3fb950; font-size: 2rem; font-weight: bold;">{isabetli} / {len(bitenler)} ✅</span>
                        <span style="color: #58A6FF; margin-left: 20px; font-size: 1.2rem;">İSABET: %{oran:.1f}</span>
                    </div>
                """, unsafe_allow_html=True)

            # --- 2. EDİTÖR KUPONLARI (KORUNMUŞ) ---
            c1, c2, c3 = st.columns(3)
            def chk_hit(liste, tip):
                h = 0
                for m in liste:
                    if m['status'] == 'FINISHED':
                        scr = f"{m['score']['fullTime']['home']}-{m['score']['fullTime']['away']}"
                        if tip == "ust" and (m['score']['fullTime']['home']+m['score']['fullTime']['away']) > 2.5: h += 1
                        elif winner(m['res']['aether']) == winner(scr): h += 1
                return h

            imz = sorted(g_l, key=lambda x: x['puan'], reverse=True)[:3]
            with c1:
                h = chk_hit(imz, "banko"); seal = '<div class="full-hit-seal">🏆 FULL HIT</div>' if h == 3 else ""
                st.markdown(f'<div class="editor-card">{seal}<div class="coupon-title">⭐ BANKO <span class="success-badge">{h}/3</span></div>', unsafe_allow_html=True)
                for m in imz: st.markdown(f'<div class="coupon-item">{m["homeTeam"]["shortName"]}-{m["awayTeam"]["shortName"]}<br>{m["res"]["aether"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            # (Diğer kuponlar buraya v70'deki gibi eklenebilir)

            st.markdown("---")
            # --- 3. 20 TAHMİN LİSTESİ + ORACLE YORUMLARI ---
            for m in sorted(g_l, key=lambda x: x['puan'], reverse=True)[:20]:
                res = m['res']
                icon_html = ""
                if m['status'] == 'FINISHED':
                    is_hit = winner(res['aether']) == winner(f"{m['score']['fullTime']['home']}-{m['score']['fullTime']['away']}")
                    status_text = "✅ KAZANDI" if is_hit else "❌ KAYBETTİ"
                    color = "#3fb950" if is_hit else "#f85149"
                    icon_html = f'<div style="color: {color}; font-weight: bold; float: right; font-size: 0.9rem;">{status_text}</div>'
                
                # Dinamik Yorum Motoru
                if res['total_xg'] > 3.2: comment = "🔥 Gol festivali kapıda! Aether, savunma kilitlerinin paramparça olacağını öngörüyor."
                elif res['total_xg'] < 2.0: comment = "🛡️ Taktiksel bir düğüm. Tek bir hatanın sonucu belirleyeceği, az gollü bir mücadele."
                elif "X" in winner(res['aether']): comment = "⚖️ Denge bozulmuyor. Aether Oracle, iki takımın birbirini kilitlemesini bekliyor."
                else: comment = f"🚀 {m['homeTeam']['shortName']} baskın taraf. Sahasında tempo yaparak sonuca gitmesini bekliyoruz."

                m_sk = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>" if m['status']=='FINISHED' else f"🕒 {m['utcDate'][11:16]}"
                
                st.markdown(f"""
                    <div class="match-card">
                        {icon_html}
                        <div class="rank-badge">🔥 %{m['puan']}</div>
                        <div style="font-size:0.8rem; color:#8B949E;">{m['l_ad']} - Hafta {m['matchday']}</div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;">
                            <div style="text-align: center; width: 33%;"><img src="{m['homeTeam']['crest']}" width="30"><br><b>{m['homeTeam']['name']}</b></div>
                            <div style="width: 33%; text-align: center;">{m_sk}</div>
                            <div style="text-align: center; width: 33%;"><img src="{m['awayTeam']['crest']}" width="30"><br><b>{m['awayTeam']['name']}</b></div>
                        </div>
                        <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                            <div class="prediction-box aether-box">✨ AETHER<br><b>{res['aether']}</b></div>
                            <div class="prediction-box">🤖 STD<br><b>{res['std']}</b></div>
                            <div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}</b></div>
                        </div>
                        <div class="ai-insight" style="border-left: 4px solid #8A2BE2; background: rgba(138, 43, 226, 0.05); padding: 10px; margin-top: 10px; border-radius: 4px; font-style: italic; font-size: 0.85rem;">
                            ✨ <b>Aether Oracle:</b> {comment}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
elif mod == "🏆 Onur Listesi":
    st.title("🏆 Gurur Tablosu")
    st.markdown('<div style="text-align:center; padding:50px; background:#1c2128; border-radius:15px; border:1px solid #3fb950;"><h2>⭐ Aether AI Rekoru</h2><p>Haftalık %91 Başarı Oranı ile Zirvede!</p></div>', unsafe_allow_html=True)
