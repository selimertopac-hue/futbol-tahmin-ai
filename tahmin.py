import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- AYAR ---
FOOTBALL_DATA_KEY = "b900863038174d07855ace7f33c69c9b"

st.set_page_config(page_title="UltraSkor Pro", page_icon="🏆", layout="wide")

# --- ANALİZ ---
def master_analiz_et(ev_ad, dep_ad, all_matches):
    try:
        df_raw = [m for m in all_matches if m['status'] == 'FINISHED']

        df = pd.DataFrame({
            "H": [m['homeTeam']['name'] for m in df_raw],
            "A": [m['awayTeam']['name'] for m in df_raw],
            "HG": [m['score']['fullTime']['home'] for m in df_raw],
            "AG": [m['score']['fullTime']['away'] for m in df_raw],
        })

        l_ev, l_dep = df['HG'].mean(), df['AG'].mean()

        ev_m = df[df['H'] == ev_ad]
        dep_m = df[df['A'] == dep_ad]

        e_xg = ev_m['HG'].mean() if not ev_m.empty else l_ev
        d_xg = dep_m['AG'].mean() if not dep_m.empty else l_dep

        def skor(ex, ax):
            matrix = np.outer([poisson.pmf(i, ex) for i in range(6)],
                              [poisson.pmf(i, ax) for i in range(6)])
            sk = np.unravel_index(np.argmax(matrix), matrix.shape)
            return f"{sk[0]} - {sk[1]}"

        return {
            "ai_std": skor(e_xg, d_xg),
            "spectrum": skor(e_xg * 1.1, d_xg * 1.1),
        }

    except:
        return None

# --- FORM AI ---
def form_analiz(ev_ad, dep_ad, all_matches):
    try:
        df = [m for m in all_matches if m['status'] == 'FINISHED']

        ev_mac = [m for m in df if ev_ad in [m['homeTeam']['name'], m['awayTeam']['name']]][-5:]
        dep_mac = [m for m in df if dep_ad in [m['homeTeam']['name'], m['awayTeam']['name']]][-5:]

        def form(maclar, takim):
            g, y = 0, 0
            for m in maclar:
                if m['homeTeam']['name'] == takim:
                    g += m['score']['fullTime']['home']
                    y += m['score']['fullTime']['away']
                else:
                    g += m['score']['fullTime']['away']
                    y += m['score']['fullTime']['home']
            return g/len(maclar) if maclar else 1, y/len(maclar) if maclar else 1

        ev_g, ev_y = form(ev_mac, ev_ad)
        dep_g, dep_y = form(dep_mac, dep_ad)

        if ev_g/dep_y > dep_g/ev_y:
            return "2 - 1"
        elif dep_g/ev_y > ev_g/dep_y:
            return "1 - 2"
        else:
            return "1 - 1"

    except:
        return "1 - 1"

# --- VERİ ---
@st.cache_data(ttl=3600)
def veri_getir(url):
    try:
        return requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}).json()
    except:
        return {}

# --- PERFORMANS ---
def haftalik_basari(m_data):
    haftalar = sorted(set(m['matchday'] for m in m_data if m['matchday']))
    out = []

    def w(s):
        a,b = map(int, s.split(" - "))
        return "H" if a>b else "A" if b>a else "D"

    for h in haftalar:
        maclar = [m for m in m_data if m['matchday']==h and m['status']=="FINISHED"]
        if not maclar:
            continue

        s1=s2=top=0
        for m in maclar:
            top+=1
            res = master_analiz_et(m['homeTeam']['name'], m['awayTeam']['name'], m_data)
            if not res:
                continue

            real = w(f"{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}")
            if w(res['ai_std'])==real:
                s1+=1
            if w(res['spectrum'])==real:
                s2+=1

        out.append({
            "Hafta":h,
            "Standart AI %":round(s1/top*100,1),
            "Spektrum AI %":round(s2/top*100,1)
        })

    return pd.DataFrame(out)

# --- SIDEBAR ---
st.sidebar.title("🛡️ UltraSkor")
sayfa = st.sidebar.radio("Sayfa", ["Maçlar","Performans"])

lig_map = {"İngiltere":"PL","İspanya":"PD","İtalya":"SA","Almanya":"BL1","Fransa":"FL1"}
lig = st.sidebar.selectbox("Lig", list(lig_map.keys()))

data = veri_getir(f"https://api.football-data.org/v4/competitions/{lig_map[lig]}/matches")
m_data = data.get("matches", [])

# --- PERFORMANS SAYFASI ---
if sayfa=="Performans":
    st.title("📈 AI Performans")

    df = haftalik_basari(m_data)

    if not df.empty:
        st.line_chart(df.set_index("Hafta"), use_container_width=True)
        st.dataframe(df, use_container_width=True)

        c1, c2 = st.columns(2)
        c1.metric("Ortalama Standart", f"%{df['Standart AI %'].mean():.1f}")
        c2.metric("Ortalama Spektrum", f"%{df['Spektrum AI %'].mean():.1f}")
    else:
        st.warning("Veri yok")

# --- MAÇLAR ---
else:
    haftalar = sorted(set(m['matchday'] for m in m_data if m['matchday']), reverse=True)
    hafta = st.sidebar.selectbox("Hafta", haftalar)

    st.title(f"{lig} - {hafta}. Hafta")

    for m in [m for m in m_data if m['matchday']==hafta]:
        ev = m['homeTeam']['name']
        dep = m['awayTeam']['name']

        res = master_analiz_et(ev, dep, m_data)
        form_pred = form_analiz(ev, dep, m_data)

        if res:
            skor = f"{m['score']['fullTime']['home']} - {m['score']['fullTime']['away']}" if m['status']=="FINISHED" else "⏳"

            guven = "🔥 ULTRA GÜVEN" if res['ai_std']==res['spectrum']==form_pred else ""

            with st.container():
                c1, c2, c3 = st.columns([3,1,3])

                c1.subheader(ev)
                c2.markdown(f"### {skor}")
                c3.subheader(dep)

                p1, p2, p3 = st.columns(3)

                p1.metric("🤖 Standart", res['ai_std'])
                p2.metric("🛡️ Spektrum", res['spectrum'])
                p3.metric("🔥 Form AI", form_pred)

                if guven:
                    st.success(guven)

                st.divider()
