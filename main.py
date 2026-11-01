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
                val = stat.get('value')
                if val is not None:
                    try:
                        val_int = int(val)
                    except ValueError:
                        val_int = 0
                        
                    if stat.get('type') == 'Total Shots':
                        total_shots += val_int
                    elif stat.get('type') == 'Corner Kicks':
                        total_corners += val_int
                        
        return total_shots, total_corners
    except:
        return 0, 0

def is_valid_league(league_name, league_type):
    name_lower = league_name.lower()
    yasakli_ifadeler = [
        'u17', 'u19', 'u20', 'u21', 'u23', 'youth', 'reserve', 
        'amateur', 'regional', 'division 3', 'division 4', 
        '3. division', '4. division', '3. liga', '4. liga', 
        '3. lig', '4. lig', 'tercera', 'group b', 'group c',
        '4th division', '3rd division', 'iv divizija', 'iii liga'
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
    
    # 1. İstek: Tüm canlı maçları tek sorguda alıyoruz (Kotayı koruyan temel hamle)
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

        fixture_id = match['fixture']['id']
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

        # Sadece aradığımız kriterlerdeki maçlar için istatistik isteği atıyoruz (Kota dostu)
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

        elif elapsed is not None:
            # Ön hazırlık maçları için her seferinde API şişmesin diye istatistiksiz veya direkt ekleyebiliriz
            # Kotayı korumak adına ön hazırlık maçlarında istatistik sorgusunu atlıyoruz veya isteğe bağlı tutuyoruz
            diger_canli_maclar.append({
                'text': f"👀 *Canlı Maç* ({elapsed}')\n🏆 _{league_name}_\n⚽ *{home}* {s_home} - {s_away} *{away}*",
                'corners': 0,
                'shots': 0
            })

    kritik_liste.sort(key=lambda x: (x['corners'], x['shots']), reverse=True)
    ara_dakika_listesi.sort(key=lambda x: (x['corners'], x['shots']), reverse=True)

    final_mesaj = ""

    if kritik_liste:
        final_mesaj += "*🔥 KRİTİK ANLAR (35 ve 82. Dakika)*\n" + "\n\n".join([m['text'] for m in kritik_liste]) + "\n\n"
    elif ara_dakika_listesi:
        final_mesaj += "*📋 ARA DAKİKA MAÇLARI*\n" + "\n\n".join([m['text'] for m in ara_dakika_listesi]) + "\n\n"
    elif diger_canli_maclar:
        # Ön hazırlıkta sadece ilk 5 maçı göstererek hem spamı hem aşırı istekleri engelliyoruz
        secilenler = [m['text'] for m in diger_canli_maclar[:5]]
        final_mesaj += "*👀 DİĞER CANLI MAÇLAR (Ön Hazırlık)*\n" + "\n\n".join(secilenler)
    else:
        final_mesaj = "💤 Şu an takip kriterine uyan canlı maç bulunmuyor."

    if final_mesaj:
        send_telegram_message(final_mesaj)

if __name__ == "__main__":
    check_matches()
