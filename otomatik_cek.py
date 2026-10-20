import os
import requests
from datetime import datetime

ARSIV_DIR = "bulten_arsivleri"
os.makedirs(ARSIV_DIR, exist_ok=True)

NESINE_URL = "https://cdnbulten.nesine.com/api/bulten/getprebultenfull"
NESINE_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "authorization": "Basic RDQ3MDc4RDMtNjcwQi00OUJBLTgxNUYtM0IyMjI2MTM1MTZCOkI4MzJCQjZGLTQwMjgtNDIwNS05NjFELTg1N0QxRTZEOTk0OA==",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
}

def bulten_otomatik_indir():
    try:
        print("Nesine bülteni indiriliyor...")
        resp = requests.get(NESINE_URL, headers=NESINE_HEADERS, timeout=15)
        if resp.status_code == 200 and len(resp.text) > 1000:
            tarih_etiketi = datetime.now().strftime("%Y-%m-%d_%H-%M")
            dosya_adi = os.path.join(ARSIV_DIR, f"nesine_bulten_oto_{tarih_etiketi}.json")
            with open(dosya_adi, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"✅ Başarıyla arşive kaydedildi: {dosya_adi}")
        else:
            print(f"❌ Hata: Sunucu geçerli veri döndürmedi. Kod: {resp.status_code}")
    except Exception as e:
        print(f"❌ Kritik hata: {e}")

if __name__ == "__main__":
    bulten_otomatik_indir()
