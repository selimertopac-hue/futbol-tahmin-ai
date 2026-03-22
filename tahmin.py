import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Time-Weighted", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; border-left: 5px solid #58A6FF; }
    .match-result { font-size: 1.5rem; font-weight: bold; color: #FFFFFF; text-align: center; background: #21262d; border-radius: 6px; padding: 6px; border: 1px solid #30363d; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 10px; text-align: center; flex: 1; margin: 0 5px; }
    .nexus-box { border: 1px solid #f85149 !important; background: rgba(248, 81, 73, 0.05); }
    .spec-box { border: 1px solid #58A6FF !important; background: rgba(88, 166, 255, 0.05); }
    .strategy-box { background-color: #1c2128; border-radius: 8px; padding: 12px; margin-top: 15px; font-size: 0.85rem; border-top: 1px solid #30363d; }
    .metric-card { background: #21262d; padding: 15px; border-radius: 10px; border: 1px solid #30363d; text-align: center; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. GELİŞMİŞ ANALİZ MOTORU (TIME-WEIGHTED SPEC) ---
def master_analiz_v2(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if len(df_raw) < 10: return None
        
        df = pd.DataFrame()
        df['H'] = [m['homeTeam']['name'] for m in df_raw]
        df['A'] = [m['awayTeam']['name'] for m in df_raw]
        df['HG'] = [int(m['score']['fullTime']['home']) for m in df_raw]
        df['AG'] = [int(m['score']['fullTime']['away']) for m in df_raw]
        df['MD'] = [int(m['matchday']) for m in df_raw]
        
        l_ev_ort, l_dep_ort = df['HG'].mean(), df['AG'].mean()
        max_md = df['MD'].max()

        # Zaman Ağırlıklı Hesaplama Fonksiyonu
        def get_weighted_stats(team_name, is_home):
            col = 'H' if is_home else 'A'
            t_df = df[df[col] == team_name].copy()
            if t_df.empty: return l_ev_ort if is_home else l_dep_ort, 1.0
            
            # Zaman Çarpanı: Son maçlar daha değerli (Lineer Decay)
            t_df['weight'] = t_df['MD'].apply(lambda x: 1.0 + (x / max_md))
            
            if is_home:
                avg_g = (t_df['HG'] * t_df['weight']).sum() / t_df['weight'].sum()
                avg_y = (t_df['AG'] * t_df['weight']).sum() / t_df['weight'].sum()
            else:
                avg_g = (t_df['AG'] * t_df['weight']).sum() / t_df['weight'].sum()
                avg_y = (t_df['HG'] * t_df['weight']).sum() / t_df['weight'].sum()
            
            return avg_g, avg_y, t_df['weight'].mean()

        # Parametreleri Çek
        e_h_g, e_h_y, e_w = get_weighted_stats(ev_ad, True)
        d_d_g, d_d_y, d_w = get_weighted_stats(dep_ad, False)

        # 1. STANDART xG
        e_xg = (e_h_g / l_ev_ort) * (d_d_y / l_ev_ort) * l_ev_ort
        d_xg = (d_d_g / l_dep_ort) * (e_h_y / l_dep_ort) * l_dep_ort

        # 2. SPEKTRUM (RAFINE EDİLMİŞ)
        # Bitiricilik ve Savunma çarpanlarını %30 oranında ortalamaya (1.0) yaklaştırıyoruz (Damping)
        e_bit = ((e_h_g / (e_xg if e_xg > 0 else 1)) * 0.7) + 0.3
        d_bit = ((d_d_g / (d_xg if d_xg > 0 else 1)) * 0.7) + 0.3
        
        # Sınırlama (0.7 - 1.4 arası)
        e_bit, d_bit = np.clip(e_bit, 0.7, 1.4), np.clip(d_bit, 0.7, 1.4)
        
        f_e_xg = e_xg * e_bit
        f_d_xg = d_xg * d_bit

        # 3. NEXUS (TREND + MOMENTUM)
        n_e_xg = f_e_xg * (1.1 if e_w > 1.5 else 0.95)
        n_d_xg = f_d_xg * (1.1 if d_w > 1.5 else 0.95)

        def get_skor(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}"

        return {
            "std": get_skor(e_xg, d_xg),
            "spec": get_skor(f_e_xg, f_d_xg),
            "nexus": get_skor(n_e_xg, n_d_xg),
            "e_xg": e_xg, "d_xg": d_xg,
            "ev_form": "🔥 Yüksek" if e_w > 1.7 else "⌛ Normal",
            "dep_form": "🔥 Yüksek" if d_w > 1.7 else "⌛ Normal"
        }
    except: return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def veri_getir(url):
    try:
        return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

# --- 5. SIDEBAR & LOGIC ---
st.sidebar.title("🛡️ UltraSkor Pro v20")
lig_map = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
lig_secim = st.sidebar.selectbox("🎯 Ligi Seçin", list(lig_map.keys()))
data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_map[lig_secim]}/matches")
m_data = data.get('matches', [])

if m_data:
    haftalar = sorted(list(set([m['matchday'] for m in m_data if m['matchday'] is not None])), reverse=True)
    mevcut_hafta = max([m['matchday'] for m in m_data if m['status'] == 'FINISHED'] or [1])
    hafta_secim = st.sidebar.selectbox("📅 Hafta Seçin", haftalar, index=haftalar.index(mevcut_hafta))

    # Başarı Takibi
    haftanin_maclari = [m for m in m_data if m['matchday'] == hafta_secim]
    biten = [m for m in haftanin_maclari if m['status'] == 'FINISHED']
    
    st.title(f"{lig_secim} - {hafta_secim}. Hafta")
    
    if biten:
        st.subheader("🏆 Haftalık Performans")
        # Basit başarı hesaplama (MS 1-0-2 bazında)
        s_d, sp_d, n_d = 0, 0, 0
        for m in biten:
            r = master_analiz_v2(m['homeTeam']['name'], m['awayTeam']['name'], m_data)
            if r:
                gw = "1" if m['score']['fullTime']['home'] > m['score']['fullTime']['away'] else ("2" if m['score']['fullTime']['away'] > m['score']['fullTime']['home'] else "X")
                def check(sk): 
                    p = sk.split(" - ")
                    return "1" if int(p[0]) > int(p[1]) else ("2" if int(p[1]) > int(p[0]) else "X")
                if check(r['std']) == gw: s_d += 1
                if check(r['spec']) == gw: sp_d += 1
                if check(r['nexus']) == gw: n_d += 1
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🤖 Standart AI", f"{s_d}/{len(biten)}")
        c2.metric("🛡️ Spektrum AI", f"{sp_d}/{len(biten)}")
        c3.metric("🔥 Nexus AI", f"{n_d}/{len(biten)}")
        st.divider()

    # Maç Listesi
    for m in haftanin_maclari:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = master_analiz_v2(ev, dep, m_data)
        if res:
            with st.container():
                st.markdown(f"""
                <div class="match-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="text-align: center; width: 30%;">
                            <img src="{m['homeTeam']['crest']}" width="45"><br><b>{ev}</b><br><small>xG: {res['e_xg']:.2f}</small>
                        </div>
                        <div style="width: 30%;">
                            {f'<div class="match-result">{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}</div>' if m['status']=='FINISHED' else f'<div style="text-align:center; font-weight:bold; color:#8B949E;">🕒 {m["utcDate"][11:16]}</div>'}
                        </div>
                        <div style="text-align: center; width: 30%;">
                            <img src="{m['awayTeam']['crest']}" width="45"><br><b>{dep}</b><br><small>xG: {res['d_xg']:.2f}</small>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                        <div class="prediction-box">🤖 <small>STD</small><br><b>{res['std']}</b></div>
                        <div class="prediction-box spec-box">🛡️ <small>SPEC</small><br><b>{res['spec']}</b></div>
                        <div class="prediction-box nexus-box">🔥 <small>NEXUS</small><br><b>{res['nexus']}</b></div>
                    </div>
                    <div class="strategy-box">
                        💡 <b>Gözlem:</b> Ev Sahibi Formu {res['ev_form']} | Deplasman Formu {res['dep_form']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

else:
    st.error("Veri çekilemedi.")
