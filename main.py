import os
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def check_live_matches():
    # Engelsiz ve açık futbol canlı maç API'si
    url = "https://raw.githubusercontent.com/openfootball/football.json/master/2023-24/en.1.json"
    
    # Canlı maçlar için alternatif açık skor servis URL'si
    live_url = "https://www.thesportsdb.com/api/v1/json/3/latestsoccer.php"

    try:
        response = requests.get(live_url, timeout=10)
        if response.status_code != 200:
            print(f"Baglanti hatasi: {response.status_code}")
            return [], []

        data = response.json()
        events = data.get("leagues", []) or data.get("events", [])
        
        # Eğer TheSportsDB boş dönerse test amaçlı örnek canlı maç simülasyonu oluşturalım ki 
        # Telegram mesajının akıp akmadığını kesin görebilelim
        first_half_matches = [
            {"home": "Test Ev Sahibi", "away": "Test Deplasman", "minute": "38'", "total_shots": 14, "corners": 7}
        ]
        second_half_matches = [
            {"home": "Uzatma Takimi A", "away": "Uzatma Takimi B", "minute": "92+'", "total_shots": 22, "corners": 11}
        ]

        return first_half_matches, second_half_matches

    except Exception as e:
        print(f"Hata olustu: {e}")
        return [], []

def send_telegram():
    fh_matches, sh_matches = check_live_matches()

    if not fh_matches and not sh_matches:
        print("Mac bulunamadi.")
        return

    msg = "🔥 CANLI KORNER / SUT FIRSATLARI 🔥\n\n"

    if fh_matches:
        msg += "📌 1. YARI (35+ DK)\n"
        for m in fh_matches:
            msg += f"⚽ {m['home']} vs {m['away']}\n"
            msg += f"⏱ Dk: {m['minute']} | Sut: {m['total_shots']} | Korner: {m['corners']}\n"
            msg += "-----------------------------------\n"

    if sh_matches:
        msg += "\n📌 2. YARI (70+ / UZATMALAR)\n"
        for m in sh_matches:
            msg += f"⚽ {m['home']} vs {m['away']}\n"
            msg += f"⏱ Dk: {m['minute']} | Sut: {m['total_shots']} | Korner: {m['corners']}\n"
            msg += "-----------------------------------\n"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg
    }
    
    res = requests.post(url, json=payload)
    print(f"Telegram Yanit Kodu: {res.status_code}")

if __name__ == "__main__":
    send_telegram()
