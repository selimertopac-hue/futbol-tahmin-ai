import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. AYARLAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro: Success Tracker", page_icon="🏆", layout="wide")

# --- 2. GÖRSEL STİL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .match-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 15px; }
    .match-result { font-size: 1.5rem; font-weight: bold; color: #58A6FF; text-align: center; background: #21262d; border-radius: 6px; padding: 6px; border: 1px solid #30363d; min-width: 80px; }
    .success-badge { background-color: #238636; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; margin-top: 5px; }
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 10px; text-align: center; width: 48%; }
    .strategy-box { background-color: #1c2128; border-left: 4px solid #F85149; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 0.85rem; }
    h1, h2, h3 { color: #58A6FF !important; }
    .metric-card { background: #21262d; padding: 15px; border-radius: 10px; border: 1px solid #30363d; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALİZ MOTORU ---
def master_analiz_et(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED' and m['score']['fullTime']['home'] is not None]
        if not df_raw:
            e_xg, d_xg, e_bit, d_bit, e_sav, d_sav = 1.3, 1.1, 1.0, 1.0, 1.0, 1.0
        else:
            df = pd.DataFrame()
            df['H'] = [m['homeTeam']['name'] for m in df_raw]
            df['A'] = [m['awayTeam']['name'] for m in df_raw]
            df['HG'] = [int(m['score']['fullTime']['home']) for m in df_raw]
            df['AG'] = [int(m['score']['fullTime']['away']) for m in df_raw]
            l_ev_ort, l_dep_ort = df['HG'].mean(), df['AG'].mean()
            ev_m, dep_m = df[df['H'] == ev_ad], df[df['A'] == dep_ad]
            e_h_g = ev_m['HG'].mean() if not ev_m.empty else l_ev_ort
            e_h_y = ev_m['AG'].mean() if not ev_m.empty else l_dep_ort
            d_d_g = dep_m['AG'].mean() if not dep_m.empty else l_dep_ort
            d_d_y = dep_m['HG'].mean() if not dep_m.empty else l_ev_ort
            e_xg = (e_h_g / l_ev_ort) * (d_d_y / l_ev_ort) * l_ev_ort
            d_xg = (d_d_g / l_dep_ort) * (e_h_y / l_dep_ort) * l_dep_ort
            e_bit = e_h_g / (e_xg if e_xg > 0 else 1)
            d_bit = d_d_g / (d_xg if d_xg > 0 else 1)
            e_sav = e_h_y / (l_dep_ort * (e_h_y / (e_xg if e_xg > 0 else 1))) if e_xg > 0 else 1.0
            d_sav = d_d_y / (l_ev_ort * (d_d_y / (d_xg if d_xg > 0 else 1))) if d_xg > 0 else 1.0

        f_e_xg, f_d_xg = e_xg * e_bit * d_sav, d_xg * d_bit * e_sav
        def get_skor(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            matrix = np.outer([poisson.pmf(i, ex) for i in range(6)], [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(matrix), matrix.shape)
            return f"{sk[0]} - {sk[1]}"
        return {
            "ai_std": get_skor(e_xg, d_xg),
            "spectrum": get_skor(f_e_xg, f_d_xg),
            "ev_xg": e_xg, "dep_xg": d_xg,
            "ev_not": "🛡️ Katı" if e_sav < 1 else "⚠️ Kırılgan",
            "dep_not": "⚔️ Fırsatçı" if d_bit > 1.2 else "🐢 Kısır"
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

    # --- 6. BAŞARI HESAPLAMA (W/D/L Tahmini Üzerinden) ---
    def w_check(s):
        p = s.split(" - ")
        return "H" if int(p[0]) > int(p[1]) else ("A" if int(p[1]) > int(p[0]) else "D")

    haftanin_maclari = [m for m in m_data if m['matchday'] == hafta_secim]
    std_dogru, spec_dogru, toplam_biten = 0, 0, 0

    # Önce başarıyı hesapla
    for m in haftanin_maclari:
        if m['status'] == 'FINISHED':
            toplam_biten += 1
            res = master_analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_data)
            if res:
                gercek_w = "H" if m['score']['fullTime']['home'] > m['score']['fullTime']['away'] else ("A" if m['score']['fullTime']['away'] > m['score']['fullTime']['home'] else "D")
                if w_check(res['ai_std']) == gercek_w: std_dogru += 1
                if w_check(res['spectrum']) == gercek_w: spec_dogru += 1

    # --- 7. ANA EKRAN ÜST PANEL ---
    st.title(f"{lig_secim} - {hafta_secim}. Hafta")
    
    if toplam_biten > 0:
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-card'>🏟️ Biten Maç<br><h2>{toplam_biten}</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'>🤖 Standart AI<br><h2>{std_dogru}</h2>İsabet</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card' style='border-color:#58A6FF;'>🛡️ Spektrum AI<br><h2 style='color:#58A6FF;'>{spec_dogru}</h2>İsabet</div>", unsafe_allow_html=True)
        st.divider()

    # --- 8. MAÇ KARTLARI ---
    for m in haftanin_maclari:
        ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
        res = master_analiz_et(ev, dep, m_data)
        if res:
            m_saat = m['utcDate'][11:16]
            # Maç Sonucu Kontrolü (Görsel İşaret için)
            std_icon, spec_icon = "", ""
            if m['status'] == 'FINISHED':
                gercek_w = "H" if m['score']['fullTime']['home'] > m['score']['fullTime']['away'] else ("A" if m['score']['fullTime']['away'] > m['score']['fullTime']['home'] else "D")
                if w_check(res['ai_std']) == gercek_w: std_icon = " ✅"
                if w_check(res['spectrum']) == gercek_w: spec_icon = " ✅"

            orta_html = f'<div class="match-result">{m["score"]["fullTime"]["home"]} - {m["score"]["fullTime"]["away"]}</div>' if m['status']=='FINISHED' else f'<div class="match-time">🕒 {m_saat}</div>'

            st.markdown(f"""
            <div class="match-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center; width: 33%;">
                        <img src="{m['homeTeam']['crest']}" width="42"><br>
                        <b style="font-size:0.9rem;">{ev}</b><br><span style="font-size:0.65rem; color:#8B949E;">xG: {res['ev_xg']:.2f}</span>
                    </div>
                    <div style="width: 33%; text-align: center; display: flex; flex-direction: column; align-items: center;">
                        {orta_html}
                    </div>
                    <div style="text-align: center; width: 33%;">
                        <img src="{m['awayTeam']['crest']}" width="42"><br>
                        <b style="font-size:0.9rem;">{dep}</b><br><span style="font-size:0.65rem; color:#8B949E;">xG: {res['dep_xg']:.2f}</span>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                    <div class="prediction-box"><div style="font-size:0.6rem; color:#8B949E;">🤖 STANDART AI</div><div style="font-weight:bold;">{res['ai_std']}{std_icon}</div></div>
                    <div class="prediction-box" style="border-color:#58A6FF;"><div style="font-size:0.6rem; color:#58A6FF;">🛡️ SPEKTRUM AI</div><div style="font-weight:bold; color:#58A6FF;">{res['spectrum']}{spec_icon}</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.error("Veri yüklenemedi.")
