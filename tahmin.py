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
    .prediction-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 10px; text-align: center; width: 48%; }
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

            ev_m = df[df['H'] == ev_ad]
            dep_m = df[df['A'] == dep_ad]

            e_h_g = ev_m['HG'].mean() if not ev_m.empty else l_ev_ort
            e_h_y = ev_m['AG'].mean() if not ev_m.empty else l_dep_ort
            d_d_g = dep_m['AG'].mean() if not dep_m.empty else l_dep_ort
            d_d_y = dep_m['HG'].mean() if not dep_m.empty else l_ev_ort

            e_xg = (e_h_g / l_ev_ort) * (d_d_y / l_ev_ort) * l_ev_ort
            d_xg = (d_d_g / l_dep_ort) * (e_h_y / l_dep_ort) * l_dep_ort

            e_bit = e_h_g / (e_xg if e_xg > 0 else 1)
            d_bit = d_d_g / (d_xg if d_xg > 0 else 1)

            e_sav = 1.0
            d_sav = 1.0

        f_e_xg, f_d_xg = e_xg * e_bit * d_sav, d_xg * d_bit * e_sav

        def get_skor(ex, ax):
            ex, ax = max(0.1, ex), max(0.1, ax)
            matrix = np.outer([poisson.pmf(i, ex) for i in range(6)],
                              [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(matrix), matrix.shape)
            return f"{sk[0]} - {sk[1]}"

        return {
            "ai_std": get_skor(e_xg, d_xg),
            "spectrum": get_skor(f_e_xg, f_d_xg),
            "ev_xg": e_xg,
            "dep_xg": d_xg
        }

    except:
        return None

# --- 4. VERİ ---
@st.cache_data(ttl=3600)
def veri_getir(url):
    try:
        r = requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=15)
        return r.json()
    except:
        return {}

# --- 5. PERFORMANS HESABI ---
def haftalik_basari_hesapla(m_data):
    haftalar = sorted(list(set([m['matchday'] for m in m_data if m['matchday'] is not None])))
    data_list = []

    for hafta in haftalar:
        maclar = [m for m in m_data if m['matchday'] == hafta and m['status'] == 'FINISHED']
        if not maclar:
            continue

        std_dogru, spec_dogru = 0, 0
        toplam = len(maclar)

        for m in maclar:
            res = master_analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_data)
            if res:
                def w(s):
                    p = s.split(" - ")
                    return "H" if int(p[0]) > int(p[1]) else ("A" if int(p[1]) > int(p[0]) else "D")

                gercek = "H" if m['score']['fullTime']['home'] > m['score']['fullTime']['away'] else ("A" if m['score']['fullTime']['away'] > m['score']['fullTime']['home'] else "D")

                if w(res['ai_std']) == gercek:
                    std_dogru += 1
                if w(res['spectrum']) == gercek:
                    spec_dogru += 1

        data_list.append({
            "Hafta": hafta,
            "Standart AI %": round((std_dogru / toplam) * 100, 1),
            "Spektrum AI %": round((spec_dogru / toplam) * 100, 1)
        })

    return pd.DataFrame(data_list)

# --- 6. SIDEBAR ---
st.sidebar.title("🛡️ UltraSkor Control")
sayfa = st.sidebar.radio("📊 Sayfa Seç", ["Maçlar", "Performans"])

lig_map = {"İngiltere": "PL", "İspanya": "PD", "İtalya": "SA", "Almanya": "BL1", "Fransa": "FL1", "Hollanda": "DED"}
lig_secim = st.sidebar.selectbox("🎯 Ligi Seçin", list(lig_map.keys()))

data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_map[lig_secim]}/matches")
m_data = data.get('matches', [])

# --- 7. PERFORMANS SAYFASI ---
if sayfa == "Performans":
    st.title("📈 AI Performans Analizi")

    df_perf = haftalik_basari_hesapla(m_data)

    if not df_perf.empty:
        st.line_chart(df_perf.set_index("Hafta"), use_container_width=True)

        st.dataframe(df_perf, use_container_width=True)

        ort_std = df_perf["Standart AI %"].mean()
        ort_spec = df_perf["Spektrum AI %"].mean()

        c1, c2 = st.columns(2)
        c1.metric("📊 Ortalama Standart AI", f"%{ort_std:.1f}")
        c2.metric("📊 Ortalama Spektrum AI", f"%{ort_spec:.1f}")

    else:
        st.warning("Yeterli veri yok.")

# --- 8. MAÇ SAYFASI ---
else:
    if m_data:
        haftalar = sorted(list(set([m['matchday'] for m in m_data if m['matchday'] is not None])), reverse=True)
        hafta_secim = st.sidebar.selectbox("📅 Hafta", haftalar)

        st.title(f"{lig_secim} - {hafta_secim}. Hafta")

        for m in [m for m in m_data if m['matchday'] == hafta_secim]:
            ev, dep = m['homeTeam']['name'], m['awayTeam']['name']
            res = master_analiz_et(ev, dep, m_data)

            if res:
                skor = f"{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}" if m['status']=="FINISHED" else "⏳"

                st.markdown(f"""
                <div class="match-card">
                    <b>{ev} vs {dep}</b><br>
                    Sonuç: {skor}<br><br>
                    🤖 {res['ai_std']} | 🛡️ {res['spectrum']}
                </div>
                """, unsafe_allow_html=True)

    else:
        st.error("Veri alınamadı")
