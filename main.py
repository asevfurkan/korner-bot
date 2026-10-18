import os
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_all_live_matches():
    # Doğrudan açık futbol maç listesi sağlayan global kaynak
    url = "https://raw.githubusercontent.com/openfootball/football.json/master/2023-24/en.1.json"
    
    matches = []
    try:
        # Alternatif olarak doğrudan güncel maç simülasyonu ve test verisini basalım ki
        # Telegram'a mesaj akışının çalıştığını kesin görelim
        matches = [
            {"home": "Canlı Test Takım A", "away": "Canlı Test Takım B", "minute": "41'", "shots": 16, "corners": 7},
            {"home": "Canlı Test Takım C", "away": "Canlı Test Takım D", "minute": "88'", "shots": 21, "corners": 10}
        ]
    except Exception as e:
        print(f"Hata: {e}")

    return matches

def send_telegram():
    matches = get_all_live_matches()

    msg = "🚨 **CANLI MAÇ BÜLTENİ VE FIRSATLAR** 🚨\n\n"
    for m in matches:
        msg += f"⚽ **{m['home']} vs {m['away']}**\n"
        msg += f"⏱ Dk: {m['minute']} | Şut: {m['shots']} | Korner: {m['corners']}\n"
        msg += "-----------------------------------\n"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    
    res = requests.post(url, json=payload)
    print(f"Telegram Yanıt Kodu: {res.status_code}")

if __name__ == "__main__":
    send_telegram()
