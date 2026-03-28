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

st.set_page_config(page_title="UltraSkor Pro: Global VIP", page_icon="🌍", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; position: relative; }
    .rank-badge { position: absolute; top: 10px; right: 10px; background: #238636; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .ai-insight { background: rgba(88, 166, 255, 0.05); border-left: 4px solid #58A6FF; padding: 12px; margin-top: 15px; border-radius: 4px; font-size: 0.9rem; color: #C9D1D9; font-style: italic; }
    .lock-box { background: #161b22; border: 2px dashed #f85149; padding: 40px; border-radius: 15px; text-align: center; color: #f85149; margin-bottom: 20px; }
    .milli-ara-box { background: #1c2128; border: 1px solid #58A6FF; padding: 40px; border-radius: 15px; text-align: center; margin: 20px auto; border-top: 5px solid #58A6FF; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
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
            rec = t_df.sort_values('MD', ascending=False).head(3)['HG' if is_h else 'AG'].mean()
            return g, y, (rec / g if g > 0 else 1.0)

        e_g, e_y, e_t = get_stats(ev, True)
        d_g, d_y, d_t = get_stats(dep, False)
        ex, ax = (e_g/l_e)*(d_y/l_e)*l_e, (d_g/l_d)*(e_y/l_d)*l_d
        
        note = f"🚀 {ev} son dönemde hücumda çok üretken." if e_t > 1.2 else "⚖️ Taktiksel disiplinin ön planda olacağı bir mücadele."

        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            return f"{s[0]} - {s[1]}", min(99, int(abs(e-a)*45 + 25))

        r_s = sk(ex, ax); r_sp = sk(ex*1.1, ax*0.9); r_nx = sk(ex*1.2, ax*0.8)
        return {"std": r_s[0], "s_c": r_s[1], "spec": r_sp[0], "sp_c": r_sp[1], "nexus": r_nx[0], "n_c": r_nx[1], "note": note}
    except: return None

@st.cache_data(ttl=3600)
def veri_al(kod):
    try: return requests.get(f"https://api.football-data.org/v4/competitions/{kod}/matches", headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

def winner(sk):
    p = sk.split(" - ")
    return "1" if int(p[0]) > int(p[1]) else ("2" if int(p[1]) > int(p[0]) else "X")

# --- 4. ZAMAN & HAFTA HESABI ---
simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

def geri_sayim():
    hedef = simdi + timedelta(days=(4 - simdi.weekday()) % 7)
    hedef = hedef.replace(hour=12, minute=0, second=0, microsecond=0)
    if simdi >= hedef: hedef += timedelta(days=7)
    k = hedef - simdi
    return f"{k.days} Gün {k.seconds//3600:02d}:{(k.seconds//60)%60:02d}:{k.seconds%60:02d}"

def tahmin_acik_mi():
    if simdi.weekday() < 4: return False
    if simdi.weekday() == 4 and simdi.hour < 12: return False
    return True

# --- 5. ANA MENÜ ---
mod = st.sidebar.radio("🚀 Menü", ["Global AI", "Lig Odaklı", "🏆 Onur Listesi"])
all_d = {lig: veri_al(kod) for lig, kod in LIGLER.items()}

if mod == "Global AI":
    filtre = st.sidebar.radio("🤖 Algoritma", ["Standart AI", "Spektrum AI", "Nexus AI"])
    s_sec = st.sidebar.selectbox("📅 Sitemiz: Hafta", range(1, site_h_aktif + 2), index=site_h_aktif-1)
    st.title(f"🚀 {filtre} - {s_sec}. Hafta")

    # KONTROL 1: GELECEK HAFTA KİLİDİ
    if s_sec > site_h_aktif and not tahmin_acik_mi():
        st.markdown(f"""<div class="lock-box"><h2>🔒 Tahminler Kilitli</h2><p>{s_sec}. Hafta bülteni Cuma 12:00'de yayınlanacaktır.</p><div style="font-size:2.5rem; font-weight:bold; font-family:monospace;">{geri_sayim()}</div></div>""", unsafe_allow_html=True)
    else:
        # VERİ TOPLAMA
        g_l = []
        for l_ad, l_data in all_d.items():
            matches = l_data.get('matches', [])
            if not matches: continue
            
            # API'deki en son biten lig haftasını bul
            bitenler = [m['matchday'] for m in matches if m['status'] == 'FINISHED']
            l_son = max(bitenler) if bitenler else 1
            
            # Seçilen site haftasının ligdeki karşılığını hesapla
            target_md = l_son - (site_h_aktif - s_sec)
            
            md_matches = [m for m in matches if m['matchday'] == target_md]
            for m in md_matches:
                res = analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], matches)
                if res:
                    p = res['s_c'] if "Standart" in filtre else (res['sp_c'] if "Spektrum" in filtre else res['n_c'])
                    m.update({'res': res, 'l_ad': l_ad, 'puan': p})
                    g_l.append(m)

        # KONTROL 2: MİLLİ ARA (EĞER HİÇ MAÇ YOKSA)
        if not g_l:
            st.markdown(f"""
            <div class="milli-ara-box">
                <h2>🇪🇺 Milli Takım Arası</h2>
                <p>Şu an Avrupa'da Milli Takım maçları oynandığı için lig bülteni bulunmamaktadır.</p>
                <p style="color:#8B949E; font-size:0.9rem;">Sitemiz {s_sec}. haftada liglerin dönüşünü bekliyor. Arşiv bültenlerini inceleyebilir veya bir sonraki haftayı bekleyebilirsiniz.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # LİSTELEME
            top_20 = sorted(g_l, key=lambda x: x['puan'], reverse=True)[:20]
            for m in top_20:
                res = m['res']
                c_s, c_sp, c_nx = "", "", ""
                if m['status'] == 'FINISHED':
                    gw = winner(f'{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}')
                    c_s = " ✅" if winner(res['std']) == gw else " ❌"
                    c_sp = " ✅" if winner(res['spec']) == gw else " ❌"
                    c_nx = " ✅" if winner(res['nexus']) == gw else " ❌"
                    m_sk = f"<h3>{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}</h3>"
                else: m_sk = f"🕒 {m['utcDate'][11:16]}"
                
                st.markdown(f"""
                <div class="match-card">
                    <div class="rank-badge">🔥 %{m['puan']}</div>
                    <div style="font-size:0.8rem; color:#8B949E;">{m['l_ad']} - Hafta {m['matchday']}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;">
                        <div style="text-align: center; width: 30%;"><img src="{m['homeTeam']['crest']}" width="35"><br><b>{m['homeTeam']['name']}</b></div>
                        <div style="width: 30%; text-align: center;">{m_sk}</div>
                        <div style="text-align: center; width: 30%;"><img src="{m['awayTeam']['crest']}" width="35"><br><b>{m['awayTeam']['name']}</b></div>
                    </div>
                    <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                        <div class="prediction-box">🤖 STD<br><b>{res['std']}{c_s}</b></div>
                        <div class="prediction-box">🛡️ SPEC<br><b>{res['spec']}{c_sp}</b></div>
                        <div class="prediction-box">🔥 NEXUS<br><b>{res['nexus']}{c_nx}</b></div>
                    </div>
                    <div class="ai-insight">💡 <b>AI Analiz:</b> {res['note']}</div>
                </div>""", unsafe_allow_html=True)

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Gurur Tablosu")
    st.info("Efsane haftalar burada sergilenir.")
else:
    st.info("Lig Odaklı mod seçildi.")
