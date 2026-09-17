import requests
import pandas as pd

def fotmob_detayli_istatistikler(league_id=47):
    """
    FotMob'un kategori bazlı veri ucundan (leagueTeamStats)
    belirtilen metriklerin 20 takımlık tam listesini çeker.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://www.fotmob.com/leagues/{league_id}/stats"
    }

    # Çekmek istediğimiz 3 ana metrik (FotMob API key isimleri)
    metrikler = {
        "rating": "FotMob Puanı",
        "goals_per_90": "Maç Başına Gol",
        "possession_percentage": "Topa Sahip Olma (%)"
    }

    tablo = {}

    for stat_name, etiket in metrikler.items():
        # Her kategori için tam listeyi veren doğrudan endpoint
        url = f"https://www.fotmob.com/api/leagueTeamStats?leagueId={league_id}&stat={stat_name}"
        
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                # Takım listesini al (genellikle 'stats' veya 'topLists' altında döner)
                takimlar = data.get("stats", []) or data.get("topLists", [])
                
                for row in takimlar:
                    # Takım adı ve değer anahtarlarını kontrol et
                    takim_adi = row.get("teamName") or row.get("name")
                    deger = row.get("value") or row.get("statValue")

                    if takim_adi:
                        if takim_adi not in tablo:
                            tablo[takim_adi] = {}
                        tablo[takim_adi][etiket] = deger
            else:
                print(f"Uyarı: {stat_name} verisi alınamadı (HTTP {res.status_code})")
        except Exception as e:
            print(f"Hata ({stat_name}): {e}")

    if not tablo:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(tablo, orient="index")
    df.index.name = "Takım"
    df.reset_index(inplace=True)
    return df

if __name__ == "__main__":
    print("FotMob üzerinden veriler çekiliyor...")
    df = fotmob_detayli_istatistikler(league_id=47)
    
    if not df.empty:
        print("\n--- PREMİER LİG TAKIM İSTATİSTİKLERİ ---")
        print(df.to_string(index=False))
        df.to_csv("fotmob_premier_lig.csv", index=False, encoding="utf-8")
        print("\nSonuçlar 'fotmob_premier_lig.csv' dosyasına yazıldı.")
    else:
        print("Hata: Tablo boş döndü. IP kısıtlaması veya endpoint yanıt yapısı değişmiş olabilir.")
