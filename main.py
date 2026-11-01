import os
import requests

# GitHub Secrets veya doğrudan değişkenler üzerinden bilgileri alıyoruz
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "SENIN_API_KEYIN")
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKENIN")
CHAT_ID = os.getenv("CHAT_ID", "CHAT_ID'N")

def send_telegram_message(text):
    """Telegram botu üzerinden bildirim gönderir."""
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID, 
        'text': text,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(tg_url, data=payload)
        return response.json()
    except Exception as e:
        print(f"Telegram mesajı gönderilemedi: {e}")

def check_live_matches():
    """API-Football'dan canlı maçları tek istekte çeker ve dakika kontrolü yapar."""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-rapidapi-key': API_FOOTBALL_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    
    # live=all parametresi ile o an oynayan tüm maçları tek sorguda alıyoruz
    params = {'live': 'all'}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        # API kota ve hata kontrolü
        if 'errors' in data and data['errors']:
            print(f"API Hatası: {data['errors']}")
            return

        matches = data.get('response', [])
        print(f"Anlık Canlı Maç Sayısı: {len(matches)}")

        for match in matches:
            home = match['teams']['home']['name']
            away = match['teams']['away']['name']
            
            # Maç dakikası güvenli çekme
            fixture_status = match.get('fixture', {}).get('status', {})
            elapsed = fixture_status.get('elapsed')
            
            # Skorlar
            goals = match.get('goals', {})
            s_home = goals.get('home') if goals.get('home') is not None else 0
            s_away = goals.get('away') if goals.get('away') is not None else 0
            
            # Eğer dakika tam 35 veya 82 ise bildirim gönder
            if elapsed in [35, 82]:
                devre = "1. Devre" if elapsed == 35 else "2. Devre"
                mesaj = (
                    f"🚨 *Kritik Dakika Alarmi!* ({devre} - {elapsed}')\n\n"
                    f"⚽ *{home}* {s_home} - {s_away} *{away}*"
                )
                send_telegram_message(mesaj)
                print(f"Bildirim gönderildi: {home} vs {away} ({elapsed}')")

    except Exception as e:
        print(f"Maçlar çekilirken hata oluştu: {e}")

if __name__ == "__main__":
    check_live_matches()
