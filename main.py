import os
import requests

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

def check_matches():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-rapidapi-key': API_FOOTBALL_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    
    # 1. Önce canlı maçları çekiyoruz
    params_live = {'live': 'all'}
    response_live = requests.get(url, headers=headers, params=params_live)
    live_data = response_live.json()
    
    matches = live_data.get('response', [])
    
    kritik_bildirimler = []
    ara_dakika_listesi = []

    for match in matches:
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        
        fixture_status = match.get('fixture', {}).get('status', {})
        elapsed = fixture_status.get('elapsed')
        extra = fixture_status.get('extra') # Uzatma dakikası varsa (örn. 5)
        
        goals = match.get('goals', {})
        s_home = goals.get('home') if goals.get('home') is not None else 0
        s_away = goals.get('away') if goals.get('away') is not None else 0

        # --- UZATMA FİLTRESİ KONTROLÜ ---
        # Eğer maç 90+ dakikadaysa ve uzatmadan en az 4 dk geçildiyse pas geç
        if elapsed and elapsed > 90 and extra:
            if elapsed >= (90 + extra + 4):
                continue # Çok geç kalınmış, bahis alınmaz

        # --- 1. İSTEK: 35. ve 82. DAKİKA KONTROLÜ ---
        if elapsed in [35, 82]:
            devre = "1. Devre" if elapsed == 35 else "2. Devre"
            kritik_bildirimler.append(
                f"🚨 *Kritik Dakika* ({devre} - {elapsed}')\n⚽ *{home}* {s_home} - {s_away} *{away}*"
            )

        # --- 3. İSTEK: ARA DAKİKALAR (15-20 veya 60-65) ---
        elif (15 <= elapsed <= 20) or (60 <= elapsed <= 65):
            ara_dakika_listesi.append(
                f"⏱️ *Ara Takip* ({elapsed}')\n📊 *{home}* {s_home} - {s_away} *{away}*"
            )

    # --- MESAJLARI BİRLEŞTİRME VE GÖNDERME ---
    final_mesaj = ""

    if kritik_bildirimler:
        final_mesaj += "*🔥 KRİTİK ANLAR (35 ve 82)*\n" + "\n\n".join(kritik_bildirimler) + "\n\n"

    # Eğer kritik dakikada maç yoksa ama ara dakikalarda maç varsa onları ayrı satır olarak ekle
    if not kritik_bildirimler and ara_dakika_listesi:
        final_mesaj += "*📋 ARA DAKİKA MAÇLARI (15-20 / 60-65)*\n" + "\n\n".join(ara_dakika_listesi) + "\n\n"

    # --- 2. İSTEK: HİÇ CANLI MAÇ YOKSA GÜNÜN MAÇLARI ---
    if not matches:
        # O an canlı maç yoksa bugünün maçlarını çekelim
        import datetime
        today_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        params_today = {'date': today_str}
        response_today = requests.get(url, headers=headers, params=params_today)
        today_data = response_today.json()
        
        today_matches = today_data.get('response', [])
        if today_matches:
            final_mesaj += f"📅 *Şu an canlı maç yok. Bugün oynanacak bazı maçlar ({len(today_matches)} maç var):*\n"
            # İlk 5 maçı örnek olarak listeleyebiliriz (kotayı ve spamı önlemek için)
            for m in today_matches[:5]:
                h = m['teams']['home']['name']
                a = m['teams']['away']['name']
                time = m['fixture']['date'][11:16] # Saat bilgisi
                final_mesaj += f"• {time} - {h} vs {a}\n"
        else:
            final_mesaj += "💤 Şu an oynanan canlı maç bulunmuyor ve bugün başka maç görünmüyor."

    # Eğer gönderilecek bir şey oluştuysa Telegram'a at
    if final_mesaj:
        send_telegram_message(final_mesaj)

if __name__ == "__main__":
    check_matches()
