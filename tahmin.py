import streamlit as st
import json
import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

# --- 1. AYARLAR & API-FOOTBALL MİHRAKI ---
API_KEY = "ca7daa2cfcc7e961d66ba734bd2080d6"
BASE_URL = "https://v3.football.api-sports.io"

SİTE_DOGUM_TARİHİ = datetime(2026, 2, 20) 
ARSIV_DOSYASI = "ai_arsiv.json"
BULTEN_DOSYASI = "msi_bulten_bankasi.json"

st.set_page_config(page_title="UltraSkor Pro: AETHER Intelligence", page_icon="🎯", layout="wide")

# --- 2. API-FOOTBALL STANDART GET MOTORU ---
def api_get(endpoint, params={}):
    headers = {
        'x-apisports-key': API_KEY,
        'Accept': 'application/json'
    }
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        return {"errors": [f"HTTP {response.status_code}"]}
    except Exception as e:
        return {"errors": [str(e)]}

# --- 🛰️ OPERASYON MERKEZİ & KİMLİK DOĞRULAMA ---
st.sidebar.title("🛡️ MSI Operasyon Merkezi")
st.sidebar.markdown("### 📡 API Durum Testi")

with st.sidebar.spinner("API Sağlık Kontrolü yapılıyor..."):
    status_check = api_get("status")
    
if status_check and not status_check.get("errors"):
    account_info = status_check.get("response", {}).get("account", {})
    st.sidebar.success("✅ API Bağlantısı Başarılı!")
    st.sidebar.caption(f"Kullanıcı: {account_info.get('firstname', 'selim')} {account_info.get('lastname', 'mert')}")
    
    requests_made = status_check.get("response", {}).get("requests", {}).get("current", 0)
    requests_limit = status_check.get("response", {}).get("requests", {}).get("limit", 100)
    st.sidebar.progress(min(1.0, requests_made / max(1, requests_limit)))
    st.sidebar.caption(f"Bugünkü İstek Tüketimi: {requests_made} / {requests_limit}")
else:
    st.sidebar.error("❌ API Bağlantı Hatası!")

# --- 3. TEMEL HESAP MAKİNESİ (check_hit) ---
def check_hit(liste, tip):
    hit = 0
    for m in liste:
        if m.get('status') in ['FINISHED', 'FT']:
            h_s = m.get('home_score')
            a_s = m.get('away_score')
            if h_s is not None and a_s is not None:
                if h_s > a_s: gw = "1"
                elif a_s > h_s: gw = "2"
                else: gw = "X"
                
                if tip == "ust" and (h_s + a_s) > 2.5: hit += 1
                elif tip == "alt" and (h_s + a_s) < 2.5: hit += 1
                elif tip in ["banko", "ideal"]:
                    t_skor = m.get('pred_skor', '0 - 0')
                    p_split = t_skor.split(" - ")
                    try:
                        p_w = "1" if int(p_split[0]) > int(p_split[1]) else ("2" if int(p_split[1]) > int(p_split[0]) else "X")
                        if p_w == gw: hit += 1
                    except: pass
    return hit

# --- 4. OTONOM ARŞİVLEME & KARA KUTU MOTORU ---
def kara_kutu_oku():
    if os.path.exists(ARSIV_DOSYASI):
        with open(ARSIV_DOSYASI, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

def kara_kutu_yaz(veri):
    with open(ARSIV_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def otomatik_muhur_tetikleyici():
    simdi = datetime.now()
    if simdi.weekday() == 4 and simdi.hour >= 12:
        filtre_anahtar = "AETHER_AI_Master"
        muhur_anahtari = f"muhur_{site_h_aktif}_{filtre_anahtar}"
        
        if muhur_anahtari not in st.session_state:
            st.session_state[muhur_anahtari] = {
                "banko": st.session_state.get('son_bankolar', []),
                "ideal": st.session_state.get('son_idealler', []),
                "ust": st.session_state.get('son_ustler', []),
                "alt": st.session_state.get('son_altlar', [])
            }
            st.toast("🎯 Otomatik mühür hafızaya alındı.")

def otonom_arsiv_guncelle():
    arsiv = kara_kutu_oku()
    guncelleme_var_mi = False
    
    for h_no in range(1, site_h_aktif):
        h_key = str(h_no)
        if h_key not in arsiv:
            filtre_anahtar = "AETHER_AI_Master" 
            muhur_anahtari = f"muhur_{h_no}_{filtre_anahtar}"
            
            if muhur_anahtari in st.session_state:
                m_kupon = st.session_state[muhur_anahtari]
                haftalik_ozet = {}
                
                for r_id, r_ad in [("W", "WICKHAM"), ("A", "AETHER"), ("N", "NEXUS"), ("S", "STANDART"), ("SP", "SPEKTRUM")]:
                    b_skor = check_hit(m_kupon.get("banko", []), "banko")
                    i_skor = check_hit(m_kupon.get("ideal", []), "ideal")
                    u_skor = check_hit(m_kupon.get("ust", []), "ust")
                    a_skor = check_hit(m_kupon.get("alt", []), "alt")
                    
                    p = int(((b_skor + i_skor + u_skor + a_skor) / 20) * 100)
                    
                    haftalik_ozet[r_id] = {
                        "b": f"✅ {b_skor}/5" if b_skor < 5 else "🏆 5/5",
                        "i": f"✅ {i_skor}/5" if i_skor < 5 else "💎 5/5",
                        "u": f"✅ {u_skor}/5" if u_skor < 5 else "🔥 5/5",
                        "a": f"✅ {a_skor}/5" if a_skor < 5 else "🛡️ 5/5",
                        "p": p,
                        "t": "Kara Kutu Kaydı ✅"
                    }
                arsiv[h_key] = haftalik_ozet
                guncelleme_var_mi = True

    if guncelleme_var_mi:
        kara_kutu_yaz(arsiv)
    st.session_state.otonom_kayitlar = arsiv

simdi = datetime.now()
site_h_aktif = ((simdi - SİTE_DOGUM_TARİHİ).days // 7) + 1

# 🧠 KRİTİK DOKUNUŞ 1: selectbox çökmesini önlemek için dinamik indeks hesabı koruması
hafta_listesi = list(range(1, max(12, site_h_aktif + 2)))
default_index = min(site_h_aktif - 1, len(hafta_listesi) - 1)

otomatik_muhur_tetikleyici()
otonom_arsiv_guncelle()

# --- 5. GÖRSEL STİL (MSI DARK) ---
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
    .lock-box { background: #161b22; border: 2px dashed #f85149; padding: 40px; border-radius: 15px; text-align: center; color: #f85149; margin-bottom: 20px; }
    h1, h2, h3 { color: #58A6FF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 6. POISSON ANALİZ VE PSİKOLOJİ MOTORU ---
def analiz_et(ex, ax, ev_ad, dep_ad, league_name):
    try:
        def sk(e, a):
            m = np.outer([poisson.pmf(i, max(0.1, e)) for i in range(6)], [poisson.pmf(i, max(0.1, a)) for i in range(6)])
            s = np.unravel_index(np.argmax(m), m.shape)
            return f"{s[0]} - {s[1]}", min(99, int(abs(e-a)*45 + 25))

        st_ex, st_ax = ex * 1.05, ax * 0.95
        r_s = sk(st_ex, st_ax)

        sp_ex, sp_ax = ex, ax
        if (ex + ax) > 2.8:
            sp_ex *= 1.15; sp_ax *= 1.15
        r_sp = sk(sp_ex, sp_ax)

        nx_ex, nx_ax = ex, ax
        if abs(ex - ax) < 0.3:
            nx_ex *= 0.90; nx_ax *= 0.90
        r_nx = sk(nx_ex, nx_ax)

        wx_ex, wx_ax = ex, ax
        h_p = (ex + ax) * 25
        s_p = 100 - (ex + ax) * 15
        
        if league_name in ["Bundesliga", "Eredivisie"]:
            wx_ex *= 1.15; wx_ax *= 1.15
        r_w = sk(wx_ex, wx_ax)

        aether_ex = (st_ex * 0.3) + (sp_ex * 0.2) + (nx_ex * 0.2) + (wx_ex * 0.3)
        aether_ax = (st_ax * 0.3) + (sp_ax * 0.2) + (nx_ax * 0.2) + (wx_ax * 0.3)
        r_ae = sk(aether_ex, aether_ax)

        return {
            "std": r_s[0], "s_c": r_s[1], 
            "spec": r_sp[0], "sp_c": r_sp[1], 
            "nexus": r_nx[0], "n_c": r_nx[1], 
            "wickham": r_w[0], "w_c": r_w[1], 
            "aether": r_ae[0], "ae_c": r_ae[1], 
            "h_p": h_p, "s_p": s_p, "total_xg": ex + ax
        }
    except: return None

def bulten_hasat_et():
    today = datetime.now().strftime('%Y-%m-%d')
    res = api_get("fixtures", params={"date": today})
    if not res or "response" not in res: return []
    
    yeni_bulten = []
    for item in res["response"]:
        fix = item.get("fixture", {})
        lg = item.get("league", {})
        tms = item.get("teams", {})
        
        yeni_bulten.append({
            'id': fix.get('id'),
            'league_name': lg.get('name', 'Bilinmeyen Lig'),
            'home_name': tms.get('home', {}).get('name', 'Ev Sahibi'),
            'away_name': tms.get('away', {}).get('name', 'Deplasman'),
            'ex': 1.5, 'ax': 1.2, 
            'date_unix': fix.get('timestamp'),
            'status': fix.get('status', {}).get('short', 'NS'),
            'home_score': item.get('goals', {}).get('home'),
            'away_score': item.get('goals', {}).get('away')
        })
    if yeni_bulten:
        with open(BULTEN_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(yeni_bulten, f, ensure_ascii=False, indent=4)
    return yeni_bulten

# --- 7. MENÜ MODLARI ---
mod = st.sidebar.radio("🚀 Menü", ["🏠 Canlı Skorlar", "🤖 Tahmin Robotu", "Global AI", "💎 Value Hunter", "🏆 Onur Listesi"])

st.sidebar.markdown("---")
if st.sidebar.button("📡 BÜLTENİ HASAT ET"):
    with st.spinner("Bülten ambarı güncelleniyor..."):
        b_list = bulten_hasat_et()
        st.sidebar.success(f"✅ {len(b_list)} Maç mühürlendi!")
        st.rerun()

if mod == "🏠 Canlı Skorlar":
    st.title("⚡ Canlı Maç Merkezi")
    live_data = api_get("fixtures", params={"live": "all"})
    matches = live_data.get('response', [])
    
    if not matches:
        st.info("Şu an aktif canlı maç bulunmuyor.")
    else:
        for item in matches:
            fix = item.get("fixture", {})
            lg = item.get("league", {})
            tms = item.get("teams", {})
            gls = item.get("goals", {})
            
            st.markdown(f"""
                <div class="match-card" style="border-left: 5px solid #3fb950;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #8B949E; margin-bottom: 5px;">
                        <span>📍 {lg.get('name')}</span>
                        <span style="color: #3fb950; font-weight: bold;">● LIVE {fix.get('status', {}).get('elapsed', 0)}'</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="text-align: right; width: 40%;"><b>{tms.get('home',{}).get('name')}</b></div>
                        <div style="width: 20%; text-align: center; background: #30363d; border-radius: 5px; padding: 5px;">
                            <h3 style="margin: 0; color: #3fb950;">{gls.get('home', 0)} - {gls.get('away', 0)}</h3>
                        </div>
                        <div style="text-align: left; width: 40%;"><b>{tms.get('away',{}).get('name')}</b></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

elif mod == "🤖 Tahmin Robotu":
    st.title("🤖 Günlük Tahmin Robotu")
    if os.path.exists(BULTEN_DOSYASI):
        with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
            bulten_data = json.load(f)
            
        gunun_maclari = []
        for m in bulten_data:
            # 🧠 KRİTİK DOKUNUŞ 2: KeyError fırlamaması için .get() metoduyla güvenli veri okuma
            ex_val = m.get('ex', 1.5)
            ax_val = m.get('ax', 1.2)
            res = analiz_et(ex_val, ax_val, m.get('home_name', 'Ev'), m.get('away_name', 'Dep'), m.get('league_name', 'Lig'))
            if res:
                m['res'] = res
                gunun_maclari.append(m)
                
        if gunun_maclari:
            c1, c2, c3 = st.columns(3)
            robotlar = [("AETHER ✨", c1, "ae_c", "aether"), ("NEXUS 🛡️", c2, "n_c", "nexus"), ("WICKHAM 🧪", c3, "w_c", "wickham")]
            
            for r_ad, r_col, r_pk, r_tk in robotlar:
                with r_col:
                    st.subheader(f"{r_ad} Radarı")
                    top_r = sorted(gunun_maclari, key=lambda x: x['res'].get(r_pk, 0), reverse=True)[:3]
                    for m in top_r:
                        st.markdown(f"""
                        <div style="background:#1e222d; padding:10px; border-radius:10px; border-left:4px solid #58A6FF; margin-bottom:10px;">
                            <small>{m.get('league_name')}</small><br>
                            <b>{m.get('home_name')} - {m.get('away_name')}</b><br>
                            <span style="color:#238636;">Öneri: {m['res'][r_tk]}</span> | <small>Güven: %{int(m['res'][r_pk])}</small>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.warning("Bültende analiz edilebilir maç kalmadı.")
    else:
        st.info("Lütfen önce sol panelden bülteni hasat edin.")

elif mod == "Global AI":
    filtre = st.sidebar.radio("🤖 Algoritma Seçimi", ["AETHER AI Master", "Standart AI", "Spektrum AI", "Nexus AI", "WICKHAM AI v3"])
    
    # 🧠 selectbox'a güvenli dinamik liste ve indeks sağlandı
    s_sec = st.sidebar.selectbox("📅 Hafta", hafta_listesi, index=default_index)
    
    st.title(f"🚀 {filtre} - {s_sec}. Hafta Düzeni")
    
    if os.path.exists(BULTEN_DOSYASI):
        with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
            b_data = json.load(f)
            
        g_l = []
        for m in b_data:
            ex_val = m.get('ex', 1.5)
            ax_val = m.get('ax', 1.2)
            res = analiz_et(ex_val, ax_val, m.get('home_name', 'Ev'), m.get('away_name', 'Dep'), m.get('league_name', 'Lig'))
            if res:
                p = res['ae_c'] if "AETHER" in filtre else (res['s_c'] if "Standart" in filtre else res['w_c'])
                m.update({'res': res, 'puan': p})
                g_l.append(m)
                
        if g_l:
            muhur_anahtari = f"muhur_{s_sec}_{filtre.replace(' ', '_')}"
            if muhur_anahtari not in st.session_state:
                st.session_state[muhur_anahtari] = {
                    "banko": sorted(g_l, key=lambda x: x['puan'], reverse=True)[:5],
                    "ideal": sorted(g_l, key=lambda x: x['puan'], reverse=True)[5:10] if len(g_l) > 10 else g_l[:5],
                    "ust": sorted(g_l, key=lambda x: x['res']['total_xg'], reverse=True)[:5],
                    "alt": sorted(g_l, key=lambda x: x['res']['total_xg'], reverse=False)[:5]
                }
            
            m_kupon = st.session_state[muhur_anahtari]
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                st.markdown(f'<div class="editor-card"><div class="coupon-title">⭐ BANKO ({filtre[:3]})</div>', unsafe_allow_html=True)
                for b in m_kupon["banko"]:
                    st.markdown(f'<div class="coupon-item"><b>{b.get("home_name")} - {b.get("away_name")}</b><br>Tahmin: {b["res"]["aether"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="editor-card"><div class="coupon-title">💎 İDEAL ({filtre[:3]})</div>', unsafe_allow_html=True)
                for i in m_kupon["ideal"]:
                    st.markdown(f'<div class="coupon-item"><b>{i.get("home_name")} - {i.get("away_name")}</b><br>Tahmin: {i["res"]["wickham"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="editor-card"><div class="coupon-title">🔥 ÜST ({filtre[:3]})</div>', unsafe_allow_html=True)
                for u in m_kupon["ust"]:
                    st.markdown(f'<div class="coupon-item"><b>{u.get("home_name")} - {u.get("away_name")}</b><br>xG: {u["res"]["total_xg"]:.2f} | 2.5 ÜST</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="editor-card"><div class="coupon-title">🛡️ ALT ({filtre[:3]})</div>', unsafe_allow_html=True)
                for a in m_kupon["alt"]:
                    st.markdown(f'<div class="coupon-item"><b>{a.get("home_name")} - {a.get("away_name")}</b><br>xG: {a["res"]["total_xg"]:.2f} | 2.5 ALT</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("Gösterilecek maç bulunamadı.")
    else:
        st.info("Lütfen önce bülteni hasat edin.")

elif mod == "💎 Value Hunter":
    st.title("🎯 VALUE HUNTER: CANLI TAHMİN TERMİNALİ")
    if os.path.exists(BULTEN_DOSYASI):
        with open(BULTEN_DOSYASI, "r", encoding="utf-8") as f:
            b_data = json.load(f)
            
        g_l = []
        for m in b_data:
            ex_val = m.get('ex', 1.5)
            ax_val = m.get('ax', 1.2)
            res = analiz_et(ex_val, ax_val, m.get('home_name', 'Ev'), m.get('away_name', 'Dep'), m.get('league_name', 'Lig'))
            if res:
                m['res'] = res
                g_l.append(m)
                
        if g_l:
            v_tabs = st.tabs(["🧪 WICKHAM", "✨ AETHER", "🛡️ NEXUS"])
            rb_cfg = [("w_c", "wickham", v_tabs[0], "🧪 Wickham"), ("ae_c", "aether", v_tabs[1], "✨ Aether"), ("n_c", "nexus", v_tabs[2], "🛡️ Nexus")]
            
            for p_k, t_k, tab, name in rb_cfg:
                with tab:
                    st.markdown(f"### {name} Fırsat Akışı")
                    top_v = sorted(g_l, key=lambda x: x['res'].get(p_k, 0), reverse=True)[:10]
                    for m in top_v:
                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #30363d; background: rgba(22, 27, 34, 0.5); border-radius: 8px; margin-bottom: 5px;">
                            <div><b>{m.get('home_name')} - {m.get('away_name')}</b><br><small>📍 {m.get('league_name')}</small></div>
                            <div><span style="background:#1f6feb; color:white; padding:4px 8px; border-radius:5px; font-size:0.75rem; font-weight:bold;">{m['res'][t_k]}</span></div>
                            <div style="color:#58A6FF; font-weight:bold;">%{int(m['res'][p_k])} <br><small style="color:#8B949E;">Güven</small></div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.warning("Analiz edilecek canlı akış verisi yok.")

elif mod == "🏆 Onur Listesi":
    st.title("🏆 Yapay Zeka Onur Listesi")
    
    manuel_veriler = {
        1: {"W": {"p": 75, "t": "Başlangıç"}, "A": {"p": 88, "t": "Stabil"}, "N": {"p": 82, "t": "Defansif"}},
        3: {"W": {"p": 94, "t": "DOMİNASYON 🔥"}, "A": {"p": 85, "t": "Stabil"}, "N": {"p": 88, "t": "Duvar"}}
    }
    
    otonom = {int(k): v for k, v in st.session_state.get('otonom_kayitlar', {}).items()}
    kupon_sonuclari = {**manuel_veriler, **otonom}
    
    secilen_h = st.select_slider("⚙️ İncele", options=list(range(1, site_h_aktif + 1)), value=max(1, site_h_aktif - 1))
    h_detay = kupon_sonuclari.get(secilen_h, {})
    
    cols = st.columns(3)
    r_config = [("W", "WICKHAM", "#d73a49", "🧪"), ("A", "AETHER", "#58A6FF", "✨"), ("N", "NEXUS", "#3fb950", "🛡️")]
    
    for i, (r_id, r_name, color, emoji) in enumerate(r_config):
        data = h_detay.get(r_id, {"p": 0, "t": "İşlem Bekliyor ⏳"})
        with cols[i]:
            st.markdown(f"""
            <div style="background: rgba(22, 27, 34, 0.6); padding: 10px; border-radius: 10px; border-top: 4px solid {color}; text-align: center;">
                <h3 style="margin:0; color:{color}; font-size: 0.9rem;">{emoji} {r_name}</h3>
                <h2 style="margin:5px 0; color: white; font-size: 1.5rem;">%{data['p']}</h2>
                <div style="font-size: 0.7rem; color:{color}; font-weight: bold;">{data['t']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(data['p'] / 100)
