import os
import requests

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "SENIN_API_KEYIN")
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKENIN")
CHAT_ID = os.getenv("CHAT_ID", "CHAT_ID'N")

def send_telegram_message(text):
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(tg_url, data=payload)
        return response.json()
    except Exception as e:
        print(f"Telegram mesajı gönderilemedi: {e}")

def get_match_stats(fixture_id):
    """Maça ait şut ve korner istatistiklerini çeker."""
    url = "https://v3.football.api-sports.io/fixtures/statistics"
    headers = {
        'x-rapidapi-key': API_FOOTBALL_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    try:
        response = requests.get(url, headers=headers, params={'fixture': fixture_id})
        data = response.json().get('response', [])
        
        total_shots = 0
        total_corners = 0
        
        for team_stat in data:
            for stat in team_stat.get('statistics', []):
                if stat['type'] == 'Total Shots':
                    val = stat.get('value')
                    total_shots += int(val) if val is not None else 0
                elif stat['type'] == 'Corner Kicks':
                    val = stat.get('value')
                    total_corners += int(val) if val is not None else 0
                    
        return total_shots, total_corners
    except:
        return 0, 0

def check_matches():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-rapidapi-key': API_FOOTBALL_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    
    params_live = {'live': 'all'}
    response_live = requests.get(url, headers=headers, params=params_live)
    live_data = response_live.json()
    
    matches = live_data.get('response', [])
    
    kritik_liste = []
    ara_dakika_listesi = []

    for match in matches:
        fixture_id = match['fixture']['id']
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        
        fixture_status = match.get('fixture', {}).get('status', {})
        elapsed = fixture_status.get('elapsed')
        extra = fixture_status.get('extra')
        
        goals = match.get('goals', {})
        s_home = goals.get('home') if goals.get('home') is not None else 0
        s_away = goals.get('away') if goals.get('away') is not None else 0

        # Uzatma filtresi
        if elapsed and elapsed > 90 and extra:
            if elapsed >= (90 + extra + 4):
                continue

        # 1. Kritik Dakika (35 veya 82)
        if elapsed in [35, 82]:
            shots, corners = get_match_stats(fixture_id)
            devre = "1. Devre" if elapsed == 35 else "2. Devre"
            kritik_liste.append({
                'text': f"🚨 *Kritik Dakika* ({devre} - {elapsed}')\n⚽ *{home}* {s_home} - {s_away} *{away}*\n📊 Şut: {shots} | Korner: {corners}",
                'corners': corners,
                'shots': shots
            })

        # 2. Ara Dakikalar (15-20 veya 60-65)
        elif (15 <= elapsed <= 20) or (60 <= elapsed <= 65):
            shots, corners = get_match_stats(fixture_id)
            ara_dakika_listesi.append({
                'text': f"⏱️ *Ara Takip* ({elapsed}')\n📊 *{home}* {s_home} - {s_away} *{away}*\n📊 Şut: {shots} | Korner: {corners}",
                'corners': corners,
                'shots': shots
            })

    # Çoktan aza sıralama (Önce korner sayısı, sonra şut sayısı büyükten küçüğe)
    kritik_liste.sort(key=lambda x: (x['corners'], x['shots']), reverse=True)
    ara_dakika_listesi.sort(key=lambda x: (x['corners'], x['shots']), reverse=True)

    final_mesaj = ""

    if kritik_liste:
        final_mesaj += "*🔥 KRİTİK ANLAR (Şut ve Korner Sıralı)*\n" + "\n\n".join([m['text'] for m in kritik_liste]) + "\n\n"

    if not kritik_liste and ara_dakika_listesi:
        final_mesaj += "*📋 ARA DAKİKA MAÇLARI*\n" + "\n\n".join([m['text'] for m in ara_dakika_listesi]) + "\n\n"

    # Canlı maç yoksa günün maçları
    if not matches:
        import datetime
        today_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        params_today = {'date': today_str}
        response_today = requests.get(url, headers=headers, params=params_today)
        today_data = response_today.json()
        
        today_matches = today_data.get('response', [])
        if today_matches:
            final_mesaj += f"📅 *Şu an canlı maç yok. Bugün oynanacak bazı maçlar:* katılan maç sayısı: {len(today_matches)}\n"
            for m in today_matches[:5]:
                h = m['teams']['home']['name']
                a = m['teams']['away']['name']
                time = m['fixture']['date'][11:16]
                final_mesaj += f"• {time} - {h} vs {a}\n"
        else:
            final_mesaj += "💤 Şu an oynanan canlı maç bulunmuyor."

    if final_mesaj:
        send_telegram_message(final_mesaj)

if __name__ == "__main__":
    check_matches()
