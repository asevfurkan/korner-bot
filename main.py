import os
import requests

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "SENIN_API_KEYIN")
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKENIN")
CHAT_ID = os.getenv("CHAT_ID", "CHAT_ID'N")

ONAYLI_LIG_IDLERI = [2, 3, 39, 61, 78, 135, 140, 203, 204]

def send_telegram_message(text):
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(tg_url, data=payload)
        return response.json()
    except Exception as e:
        print(f"Telegram mesajı gönderilemedi: {e}")

def get_match_stats(fixture_id):
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
        league_id = match['league']['id']
        league_name = match['league']['name']
        
        if league_id not in ONAYLI_LIG_IDLERI:
            continue

        fixture_id = match['fixture']['id']
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        
        fixture_status = match.get('fixture', {}).get('status', {})
        elapsed = fixture_status.get('elapsed')
        extra = fixture_status.get('extra')
        
        goals = match.get('goals', {})
        # Düzeltilen kısım (köşeli parantezler doğrulandı)
        s_home = goals.get('home') if goals.get('home') is not None else 0
        s_away = goals.get('away') if goals.get('away') is not None else 0

        if elapsed and elapsed > 90 and extra:
            if elapsed >= (90 + extra + 4):
                continue

        if elapsed in [35, 82]:
            shots, corners = get_match_stats(fixture_id)
            devre = "1. Devre" if elapsed == 35 else "2. Devre"
            kritik_liste.append({
                'text': f"🚨 *Kritik Dakika* ({devre} - {elapsed}')\n🏆 _{league_name}_\n⚽ *{home}* {s_home} - {s_away} *{away}*\n📊 Şut: {shots} | Korner: {corners}",
                'corners': corners,
                'shots': shots
            })

        elif (15 <= elapsed <= 20) or (60 <= elapsed <= 65):
            shots, corners = get_match_stats(fixture_id)
            ara_dakika_listesi.append({
                'text': f"⏱️ *Ara Takip* ({elapsed}')\n🏆 _{league_name}_\n⚽ *{home}* {s_home} - {s_away} *{away}*\n📊 Şut: {shots} | Korner: {corners}",
                'corners': corners,
                'shots': shots
            })

    kritik_liste.sort(key=lambda x: (x['corners'], x['shots']), reverse=True)
    ara_dakika_listesi.sort(key=lambda x: (x['corners'], x['shots']), reverse=True)

    final_mesaj = ""

    if kritik_liste:
        final_mesaj += "*🔥 KRİTİK ANLAR (Büyük Ligler)*\n" + "\n\n".join([m['text'] for m in kritik_liste]) + "\n\n"

    if not kritik_liste and ara_dakika_listesi:
        final_mesaj += "*📋 ARA DAKİKA MAÇLARI (Büyük Ligler)*\n" + "\n\n".join([m['text'] for m in ara_dakika_listesi]) + "\n\n"

    if not matches or (not kritik_liste and not ara_dakika_listesi):
        final_mesaj += "💤 Şu an büyük liglerde takip kriterine uyan canlı maç bulunmuyor."

    if final_mesaj:
        send_telegram_message(final_mesaj)

if __name__ == "__main__":
    check_matches()
