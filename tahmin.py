import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Ranking", page_icon="🎯", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; }
    .rank-badge { background: #238636; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: bold; float: right; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 10px; text-align: center; flex: 1; margin: 0 5px; }
    .active-box { border: 1.5px solid #58A6FF !important; background: rgba(88, 166, 255, 0.1); }
    h1, h2, h3 { color: #58A6FF !important; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; transition: 0.3s; }
    .stButton>button:hover { border-color: #58A6FF; color: #58A6FF; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
def master_analiz_v3(ev_ad, dep_ad, all_matches):
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

        def get_weighted_stats(team_name, is_home):
            col = 'H' if is_home else 'A'
            t_df = df[df[col] == team_name].copy()
            if t_df.empty: return l_ev_ort, 1.0, 1.0
            t_df['weight'] = 1.0 + (t_df['MD'] / max_md)
            if is_home:
                g, y = (t_df['HG']*t_df['weight']).sum()/t_df['weight'].sum(), (t_df['AG']*t_df['weight']).sum()/t_df['weight'].sum()
            else:
                g, y = (t_df['AG']*t_df['weight']).sum()/t_df['weight'].sum(), (t_df['HG']*t_df['weight']).sum()/t_df['weight'].sum()
            return g, y, t_df['weight'].mean()

        e_h_g, e_h_y, e_w = get_weighted_stats(ev_ad, True)
        d_d_g, d_d_y, d_w = get_weighted_stats(dep_ad, False)

        e_xg = (e_h_g / l_ev_ort) * (d_d_y / l_ev_ort) * l_ev_ort
        d_xg = (d_d_g / l_dep_ort) * (e_h_y / l_dep_ort) * l_dep_ort

        e_bit = np.clip(((e_h_g / (e_xg if e_xg > 0 else 1)) * 0.7) + 0.3, 0.7, 1.4)
        d_bit = np.clip(((d_d_g / (d_xg if d_xg > 0 else 1)) * 0.7) + 0.3, 0.7, 1.4)
        
        f_e_xg, f_d_xg = e_xg * e_bit, d_xg * d_bit
        n_e_xg, n_d_xg = f_e_xg * (1.1 if e_w > 1.5 else 0.95), f_d_xg * (1.1 if d_w > 1.5 else 0.95)

        def get_skor(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            m = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(m), m.shape)
            return f"{sk[0]} - {sk[1]}"

        # GÜVEN PUANI HESAPLAMA (0-100 ARASI)
        def calc_confidence(ex, ax):
            diff = abs(ex - ax)
            return min(100, int(diff * 40 + 20))

        return {
            "std": get_skor(e_xg, d_xg), "std_conf": calc_confidence(e_xg, d_xg),
            "spec": get_skor(f_e_xg, f_d_xg), "spec_conf": calc_confidence(f_e_xg, f_d_xg),
            "nexus": get_skor(n_e_xg, n_d_xg), "nexus_conf": calc_confidence(n_e_xg, n_d_xg),
            "e_xg": e_xg, "d_xg": d_xg
        }
    except: return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def veri_getir(url):
    try: return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15).json()
    except: return {}

# --- 5. SIDEBAR & RANKING BUTTONS ---
st.sidebar.title("🛡️ UltraSkor Pro v21")
lig_map = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
lig_secim = st.sidebar.selectbox("🎯 Ligi Seçin", list(lig_map.keys()))
data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_map[lig_secim]}/matches")
m_data = data.get('matches', [])

if m_data:
    haftalar = sorted(list(set([m['matchday'] for m in m_data if m['matchday'] is not None])), reverse=True)
    mevcut_hafta = max([m['matchday'] for m in m_data if m['status'] == 'FINISHED'] or [1])
    hafta_secim = st.sidebar.selectbox("📅 Hafta Seçin", haftalar, index=haftalar.index(mevcut_hafta))

    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Tahmin Sıralama")
    filtre = st.sidebar.radio("Sıralama Algoritması:", ["Normal (Varsayılan)", "Standart AI", "Spektrum AI", "Nexus AI"])

    # --- 6. MAÇLARI ANALİZ ET VE SIRALA ---
    haftanin_maclari = [m for m in m_data if m['matchday'] == hafta_secim]
    analizli_maclar = []
    
    for m in haftanin_maclari:
        res = master_analiz_v3(m['homeTeam']['name'], m['awayTeam']['name'], m_data)
        if res:
            m['analiz'] = res
            # Filtreye göre güven puanını ata
            if filtre == "Standart AI": m['sort_val'] = res['std_conf']
            elif filtre == "Spektrum AI": m['sort_val'] = res['spec_conf']
            elif filtre == "Nexus AI": m['sort_val'] = res['nexus_conf']
            else: m['sort_val'] = 0
            analizli_maclar.append(m)

    # Sıralama: Güven puanına göre büyükten küçüğe
    if filtre != "Normal (Varsayılan)":
        analizli_maclar = sorted(analizli_maclar, key=lambda x: x['sort_val'], reverse=True)

    # --- 7. ANA EKRAN ---
    st.title(f"{lig_secim} - {hafta_secim}. Hafta")
    st.caption(f"Şu an şuna göre sıralanıyor: **{filtre}**")

    for m in analizli_maclar:
        res = m['analiz']
        with st.container():
            # Güven Rozeti
            badge = f'<div class="rank-badge">🔥 Güven: %{m["sort_val"]}</div>' if filtre != "Normal (Varsayılan)" else ""
            
            st.markdown(f"""
            <div class="match-card">
                {badge}
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top:10px;">
                    <div style="text-align: center; width: 30%;">
                        <img src="{m['homeTeam']['crest']}" width="40"><br><b>{m['homeTeam']['name']}</b>
                    </div>
                    <div style="width: 30%; text-align: center;">
                        {f'<div class="match-result">{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}</div>' if m['status']=='FINISHED' else f'<div style="color:#8B949E; font-weight:bold;">🕒 {m["utcDate"][11:16]}</div>'}
                    </div>
                    <div style="text-align: center; width: 30%;">
                        <img src="{m['awayTeam']['crest']}" width="40"><br><b>{m['awayTeam']['name']}</b>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-around; margin-top: 20px;">
                    <div class="prediction-box {'active-box' if filtre=='Standart AI' else ''}">🤖 <small>STD</small><br><b>{res['std']}</b></div>
                    <div class="prediction-box {'active-box' if filtre=='Spektrum AI' else ''} " style="border-color:#58A6FF;">🛡️ <small>SPEC</small><br><b>{res['spec']}</b></div>
                    <div class="prediction-box nexus-box {'active-box' if filtre=='Nexus AI' else ''}">🔥 <small>NEXUS</small><br><b>{res['nexus']}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.error("Veri çekilemedi.")
