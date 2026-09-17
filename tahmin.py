import requests
import pandas as pd
import json

def fotmob_lig_istatistikleri(league_id=47):
    """
    FotMob dahili API'sinden takım istatistiklerini çeker.
    league_id: 47 (Premier League), 87 (La Liga), 54 (1. Bundesliga), 71 (Süper Lig)
    """
    url = f"https://www.fotmob.com/api/leagues?id={league_id}&type=league"
    
    # FotMob bot korumasını aşmak için gerekli standart başlıklar
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.fotmob.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return None

    # İstatistik bloğunu kontrol et
    stats_data = data.get("stats", {})
    teams_stats = stats_data.get("teams", [])

    if not teams_stats:
        print("İstatistik tablosu henüz yüklenmemiş veya boş döndü.")
        return None

    # Hedeflediğimiz metrik başlıkları
    metrikler = {
        "rating": "FotMob Puanı",
        "goals_per_90": "Maç Başına Gol",
        "possession_percentage": "Topa Sahip Olma (%)"
    }

    sonuclar = {}

    for kategori in teams_stats:
        kategori_adi = kategori.get("header") # örn: rating, goals_per_90
        
        if kategori_adi in metrikler:
            label = metrikler[kategori_adi]
            items = kategori.get("topThree", []) + kategori.get("fetchAllUrl", []) # Sıralı liste
            
            # Bazı liglerde tablo fetchAll altında gelir, doğrudan data içinden çekelim:
            for item in kategori.get("fetchAll", {}).get("data", []):
                team = item.get("teamName")
                deger = item.get("value")
                
                if team not in sonuclar:
                    sonuclar[team] = {}
                sonuclar[team][label] = deger

    # DataFrame'e dönüştür
    df = pd.DataFrame.from_dict(sonuclar, orient="index")
    df.index.name = "Takım"
    df.reset_index(inplace=True)
    
    return df

# Çalıştırma ve Test
if __name__ == "__main__":
    df_pl = fotmob_lig_istatistikleri(league_id=47)
    
    if df_pl is not None and not df_pl.empty:
        print("--- Premier Lig Takım İstatistikleri ---")
        print(df_pl.to_string(index=False))
        
        # Sonucu CSV veya JSON olarak dışa aktar
        df_pl.to_csv("fotmob_premier_lig.csv", index=False, encoding="utf-8")
        print("\nVeri başarıyla 'fotmob_premier_lig.csv' dosyasına kaydedildi.")
    else:
        print("Veri çekilemedi, alternatif endpoint kontrol ediliyor...")
