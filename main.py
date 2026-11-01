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

def is_valid_league(league_name, league_type):
    name_lower = league_name.lower()
    yasakli_ifadeler = [
        'u17', 'u19', 'u20', 'u21', 'u23', 'youth', 'reserve', 
        'amateur', 'regional', 'division 3', 'division 4', 
        '3. division', '4. division', '3. liga', '4. liga', 
        '3. lig', '4. lig', 'tercera', 'group b', 'group c',
        '4th division', '3rd division', 'iv divizija', 'iii liga',
        'thai league 2' # Sorun çıkaran ligleri buraya ekleyebilirsin
    ]
    for yasak in yasakli_ifadeler:
        if yasak in name_lower:
            return False
    if ('3.' in name_lower or '4.' in name_lower or '3 ' in name_lower or '4 ' in name_lower):
        if 'lig' in name_lower or 'div' in name_lower or 'class' in name_lower or 'group' in name_lower:
            return False
    return True

def check_matches():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-rapidapi-key': API_FOOTBALL_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    
    # Tek ve net istek (Kotayı koruyan yöntem)
    params_live = {'live': 'all'}
    response_live = requests.get(url, headers=headers, params=params_live)
    live_data = response_live.json()
    
    matches = live_data.get('response', [])
    
    kritik_liste = []
    ara_dakika_listesi = []
    diger_canli_maclar = []

    for match in matches:
        league_name = match['league']['name']
        league_type = match['league'].get('type', '')
        
        if not is_valid_league(league_name, league_type):
            continue

        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        
        fixture_status = match.get('fixture', {}).get('status', {})
        elapsed = fixture_status.get('elapsed')
        extra = fixture_status.get('extra')
        
        goals = match.get('goals', {})
        s_home = goals.get('home') if goals.get('home') is not None else 0
        s_away = goals.get('away') if goals.get('away') is not None else 0

        if elapsed and elapsed > 90 and extra:
            if elapsed >= (90 + extra + 4):
                continue

        if elapsed in [35, 82]:
            devre = "1. Devre" if elapsed == 35 else "2. Devre"
            kritik_liste.append(
                f"🚨 *Kritik Dakika* ({devre} - {elapsed}')\n🏆 _{league_name}_\n⚽ *{home}* {s_home} - {s_away} *{away}*"
            )

        elif (15 <= elapsed <= 20) or (60 <= elapsed <= 65):
            ara_dakika_listesi.append(
                f"⏱️ *Ara Takip* ({elapsed}')\n🏆 _{league_name}_\n⚽ *{home}* {s_home} - {s_away} *{away}*"
            )

        elif elapsed is not None:
            diger_canli_maclar.append(
                f"👀 *Canlı Maç* ({elapsed}')\n🏆 _{league_name}_\n⚽ *{home}* {s_home} - {s_away} *{away}*"
            )

    final_mesaj = ""

    if kritik_liste:
        final_mesaj += "*🔥 KRİTİK ANLAR (35 ve 82. Dakika)*\n\n" + "\n\n".join(kritik_liste) + "\n\n"
    elif ara_dakika_listesi:
        final_mesaj += "*📋 ARA DAKİKA MAÇLARI*\n\n" + "\n\n".join(ara_dakika_listesi) + "\n\n"
    elif diger_canli_maclar:
        final_mesaj += "*👀 DİĞER CANLI MAÇLAR (Ön Hazırlık)*\n\n" + "\n\n".join(diger_canli_maclar[:5])
    else:
        final_mesaj = "💤 Şu an takip kriterine uyan canlı maç bulunmuyor."

    if final_mesaj:
        send_telegram_message(final_mesaj)

if __name__ == "__main__":
    check_matches()
