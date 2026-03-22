import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Nexus Mode", page_icon="🛡️", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; border-top: 3px solid #58A6FF; }
    .match-result { font-size: 1.5rem; font-weight: bold; color: #58A6FF; text-align: center; background: #21262d; border-radius: 6px; padding: 6px; border: 1px solid #30363d; min-width: 80px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; flex: 1; margin: 0 4px; }
    .nexus-box { background: linear-gradient(145deg, #1e2530, #0d1117); border: 1px solid #f85149 !important; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #58A6FF; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 0.85rem; color: #8B949E; }
    .metric-card { background: #21262d; padding: 10px; border-radius: 10px; border: 1px solid #30363d; text-align: center; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. NEXUS ANALİZ MOTORU ---
def analiz_merkezi(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if len(df_raw) < 5: return None
        
        df = pd.DataFrame()
        df['H'] = [m['homeTeam']['name'] for m in df_raw]
        df['A'] = [m['awayTeam']['name'] for m in df_raw]
        df['HG'] = [int(m['score']['fullTime']['home']) for m in df_raw]
        df['AG'] = [int(m['score']['fullTime']['away']) for m in df_raw]
        df['MD'] = [m['matchday'] for m in df_raw]
        
        l_ev_ort, l_dep_ort = df['HG'].mean(), df['AG'].mean()
        ev_m, dep_m = df[df['H'] == ev_ad], df[df['A'] == dep_ad]
        
        # 1. Standart Parametreler
        e_h_g = ev_m['HG'].mean() if not ev_m.empty else l_ev_ort
        e_h_y = ev_m['AG'].mean() if not ev_m.empty else l_dep_ort
        d_d_g = dep_m['AG'].mean() if not dep_m.empty else l_dep_ort
        d_d_y = dep_m['HG'].mean() if not dep_m.empty else l_ev_ort

        # 2. Nexus: Form Trendi (Son 5 Maç Ağırlığı)
        def get_trend(team_name):
            recent = df[(df['H'] == team_name) | (df['A'] == team_name)].sort_values('MD', ascending=False).head(5)
            if recent.empty: return 1.0
            pts = 0
            for _, r in recent.iterrows():
                if r['H'] == team_name:
                    pts += 3 if r['HG'] > r['AG'] else (1 if r['HG'] == r['AG'] else 0)
                else:
                    pts += 3 if r['AG'] > r['HG'] else (1 if r['AG'] == r['HG'] else 0)
            return 0.8 + (pts / 15) * 0.4 # 0.8 ile 1.2 arası çarpan

        e_trend = get_trend(ev_ad)
        d_trend = get_trend(dep_ad)

        # 3. Nexus: Kimlik Katsayısı (Büyük maç savunma disiplini tahmini)
        e_kimlik = 0.9 if (e_h_g < l_ev_ort and e_h_y < l_dep_ort) else 1.05
        d_kimlik = 0.85 if (d_d_g < l_dep_ort and d_d_y < l_ev_ort) else 1.0

        # Hesaplamalar
        e_xg = (e_h_g / l_ev_ort) * (d_d_y / l_ev_ort) * l_ev_ort
        d_xg = (d_d_g / l_dep_ort) * (e_h_y / l_dep_ort) * l_dep_ort
        
        # Spektrum
        e_bit = e_h_g / (e_xg if e_xg > 0 else 1)
        d_bit = d_d_g / (d_xg if d_xg > 0 else 1)
        e_sav = e_h_y / (l_dep_ort * (e_h_y / (e_xg if e_xg > 0 else 1))) if e_xg > 0 else 1.0
        d_sav = d_d_y / (l_ev_ort * (d_d_y / (d_xg if d_xg > 0 else 1))) if d_xg > 0 else 1.0

        # Nexus Final xG (Trend ve Kimlik dahil)
        n_e_xg = e_xg * e_trend * e_kimlik
        n_d_xg = d_xg * d_trend * d_kimlik

        def get_skor(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            matrix = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(matrix), matrix.shape)
            return f"{sk[0]} - {sk[1]}"

        return {
            "std": get_skor(e_xg, d_xg),
            "spec": get_skor(e_xg * e_bit * d_sav, d_xg * d_bit * e_sav),
            "nexus": get_skor(n_e_xg, n_d_xg),
            "e_xg": e_xg, "d_xg": d_xg,
            "trend": "📈 Yükselişte" if e_trend > 1.05 else "📉 Düşüşte",
            "kimlik": "🛡️ Kapalı Oyun" if d_kimlik < 1.0 else "⚔️ Açık Oyun"
        }
    except: return None

# --- 4. VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def veri_getir(url):
    try:
        r = requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15)
        return r.json()
    except: return {}

# --- 5. SIDEBAR ---
st.sidebar.title("🛡️ UltraSkor Control")
lig_map = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
lig_secim = st.sidebar.selectbox("🎯 Ligi Seçin", list(lig_map.keys()))
data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_map[lig_secim]}/matches")
m_data = data.get('matches', [])

if m_data:
    haftalar = sorted(list(set([m['matchday'] for m in m_data if m['matchday'] is not None])), reverse=True)
    mevcut_hafta = max([m['matchday'] for m in m_data if m['status'] == 'FINISHED'] or [1])
    hafta_secim = st.sidebar.selectbox("📅 Haftayı Seçin (Arşiv)", haftalar, index=haftalar.index(mevcut_hafta) if mevcut_hafta in haftalar else 0)

    # --- 6. BAŞARI SKORBORDU ---
    st.title(f"{lig_secim} - {hafta_secim}. Hafta")
    haftanin_maclari = [m for m in m_data if m['matchday'] == hafta_secim]
    
    # Başarı sayaçları
    s_dogru, sp_dogru, n_dogru, biten = 0, 0, 0, 0
    for m in haftanin_maclari:
        if m['status'] == 'FINISHED':
            biten += 1
            r = analiz_merkezi(m['homeTeam']['name'], m['awayTeam']['name'], m_data)
            if r:
                gw = "H" if m['score']['fullTime']['home'] > m['score']['fullTime']['away'] else ("A" if m['score']['fullTime']['away'] > m['score']['fullTime']['home'] else "D")
                if (lambda s: "H" if int(s[0])>int(s[4]) else ("A" if int(s[4])>int(s[0]) else "D"))(r['std']) == gw: s_dogru += 1
                if (lambda s: "H" if int(s[0])>int(s[4]) else ("A" if int(s[4])>int(s[0]) else "D"))(r['spec']) == gw: sp_dogru += 1
                if (lambda s: "H" if int(s[0])>int(s[4]) else ("A" if int(s[4])>int(s[0]) else "D"))(r['nexus']) == gw: n_dogru += 1

    if biten > 0:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏟️ Biten", biten)
        c2.metric("🤖 Std AI", f"{s_dogru}/{biten}")
        c3.metric("🛡️ Spec AI", f"{sp_dogru}/{biten}")
        c4.metric("🔥 Nexus AI", f"{n_dogru}/{biten}", delta=n_dogru - s_dogru)
        st.divider()

    # --- 7. MAÇ KARTLARI ---
    for m in haftanin_maclari:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = analiz_merkezi(ev, dep, m_data)
        if res:
            m_saat = m['utcDate'][11:16]
            orta_html = f'<div class="match-result">{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}</div>' if m['status']=='FINISHED' else f'<div class="match-time" style="text-align:center; color:#8B949E; border:1px dashed #30363d; padding:5px; border-radius:5px;">🕒 {m_saat}</div>'

            st.markdown(f"""
            <div class="match-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center; width: 30%;">
                        <img src="{m['homeTeam']['crest']}" width="45"><br>
                        <b>{ev}</b><br><span style="font-size:0.6rem; color:#8B949E;">xG: {res['e_xg']:.2f}</span>
                    </div>
                    <div style="width: 30%; text-align: center;">{orta_html}</div>
                    <div style="text-align: center; width: 30%;">
                        <img src="{m['awayTeam']['crest']}" width="45"><br>
                        <b>{dep}</b><br><span style="font-size:0.6rem; color:#8B949E;">xG: {res['d_xg']:.2f}</span>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-around; margin-top: 15px;">
                    <div class="prediction-box"><div style="font-size:0.55rem; color:#8B949E;">🤖 STD</div><b>{res['std']}</b></div>
                    <div class="prediction-box"><div style="font-size:0.55rem; color:#58A6FF;">🛡️ SPEC</div><b>{res['spec']}</b></div>
                    <div class="prediction-box nexus-box"><div style="font-size:0.55rem; color:#f85149;">🔥 NEXUS</div><b style="color:#f85149;">{res['nexus']}</b></div>
                </div>
                <div class="strategy-box">
                    💡 <b>Nexus Gözlemi:</b> Ev Sahibi {res['trend']} | Rakip {res['kimlik']} Modunda.
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.error("Veri yüklenemedi.")
