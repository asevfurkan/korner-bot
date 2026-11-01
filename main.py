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

def get_detailed_stats(fixture_id):
    url = "https://v3.football.api-sports.io/fixtures/statistics"
    headers = {
        'x-rapidapi-key': API_FOOTBALL_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    try:
        response = requests.get(url, headers=headers, params={'fixture': fixture_id})
        data = response.json().get('response', [])
        
        home_shots, away_shots = 0, 0
        home_corners, away_corners = 0, 0
        
        for idx, team_stat in enumerate(data):
            is_home = (idx == 0)
            for stat in team_stat.get('statistics', []):
                stype = stat.get('type')
                val = stat.get('value')
                if val is not None:
                    try:
                        val_int = int(val)
                    except ValueError:
                        val_int = 0
                        
                    if stype == 'Total Shots':
                        if is_home: home_shots = val_int
                        else: away_shots = val_int
                    elif stype == 'Corner Kicks':
                        if is_home: home_corners = val_int
                        else: away_corners = val_int
                        
        total_shots = home_shots + away_shots
        total_corners = home_corners + away_corners
        return total_shots, home_shots, away_shots, total_corners, home_corners, away_corners
    except:
        return 0, 0, 0, 0, 0, 0

def is_valid_league(league_name):
    name_lower = league_name.lower()
    
    # Korner bahsi açılan kaliteli Avrupa 2. ligleri (İstisna olarak izin veriyoruz)
    onayli_ikinci_ligler = [
        'championship', 'segunda división', 'serie b', 'ligue 2', 'eerste divisie'
    ]
    
    for onayli in onayli_ikinci_ligler:
        if onayli in name_lower:
            return True  # Bunlar 2. lig olsa bile içeri alınır

    # Diğer tüm alt ligler, amatörler, gençlik ligleri ve genel 2. ligler engellenir
    yasakli_ifadeler = [
        'u17', 'u19', 'u20', 'u21', 'u23', 'youth', 'reserve', 
        'amateur', 'regional', 'division 3', 'division 4', 
        '2. division', '3. division', '4. division', 
        '2. bundesliga', 'liga 2', '2. liga', '3. liga', '4. liga', 
        '2. lig', '3. lig', '4. lig', 'tercera', 'group b', 'group c',
        '2nd division', '3rd division', '4th division', 'iv divizija', 'iii liga'
    ]
    
    for yasak in yasakli_ifadeler:
        if yasak in name_lower:
            return False
            
    if ('2.' in name_lower or '3.' in name_lower or '4.' in name_lower or '2 ' in name_lower or '3 ' in name_lower or '4 ' in name_lower):
        if 'lig' in name_lower or 'div' in name_lower or 'class' in name_lower or 'group' in name_lower or 'bundesliga' in name_lower:
            return False
            
    return True

def check_matches():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-rapidapi-key': API_FOOTBALL_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    
    params_live = {'live': 'all'}
    response_live = requests.get(url, headers=headers, params=params_live)
    matches = response_live.json().get('response', [])
    
    kritik_liste = []
    ara_dakika_listesi = []
    diger_canli_maclar = []

    for match in matches:
        league_name = match['league']['name']
        if not is_valid_league(league_name):
            continue

        fixture_id = match['fixture']['id']
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        
        fixture_status = match.get('fixture', {}).get('status', {})
        elapsed = fixture_status.get('elapsed')
        extra = fixture_status.get('extra')
        
        s_home = match.get('goals', {}).get('home') or 0
        s_away = match.get('goals', {}).get('away') or 0

        if elapsed and elapsed > 90 and extra:
            if elapsed >= (90 + extra + 4):
                continue

        if elapsed in [35, 82]:
            devre = "1H" if elapsed <= 45 else "2H"
            kritik_liste.append({'id': fixture_id, 'home': home, 'away': away, 'elapsed': elapsed, 'devre': devre, 'league': league_name, 's_home': s_home, 's_away': s_away})
        elif (15 <= elapsed <= 20) or (60 <= elapsed <= 65):
            devre = "1H" if elapsed <= 45 else "2H"
            ara_dakika_listesi.append({'id': fixture_id, 'home': home, 'away': away, 'elapsed': elapsed, 'devre': devre, 'league': league_name, 's_home': s_home, 's_away': s_away})
        elif elapsed is not None:
            devre = "1H" if elapsed <= 45 else "2H"
            diger_canli_maclar.append({'id': fixture_id, 'home': home, 'away': away, 'elapsed': elapsed, 'devre': devre, 'league': league_name, 's_home': s_home, 's_away': s_away})

    target_list = []
    baslik = ""

    if kritik_liste:
        target_list = kritik_liste
        baslik = "🔥 *KRİTİK ANLAR (35 ve 82. Dakika)*"
    elif ara_dakika_listesi:
        target_list = ara_dakika_listesi
        baslik = "📋 *ARA DAKİKA MAÇLARI*"
    elif diger_canli_maclar:
        target_list = diger_canli_maclar[:5]
        baslik = "👀 *DİĞER CANLI MAÇLAR (Ön Hazırlık)*"

    islenmis_veriler = []
    for m in target_list:
        t_shots, h_s, a_s, t_corners, h_c, a_c = get_detailed_stats(m['id'])
        islenmis_veriler.append({
            'text': (
                f"⚽ *{m['home']}* {m['s_home']} - {m['s_away']} *{m['away']}*\n"
                f"   🏆 _{m['league']}_\n"
                f"   ⏱️ ({m['devre']} - Dakika: {m['elapsed']}')\n"
                f"   📊 Toplam Korner: {t_corners} ({h_c} - {a_c})\n"
                f"   📊 Toplam Şut: {t_shots} ({h_s} - {a_s})"
            ),
            'corners': t_corners,
            'shots': t_shots
        })

    islenmis_veriler.sort(key=lambda x: (x['corners'], x['shots']), reverse=True)

    if islenmis_veriler:
        final_mesaj = baslik + "\n\n" + "\n\n".join([m['text'] for m in islenmis_veriler])
        send_telegram_message(final_mesaj)
    else:
        send_telegram_message("💤 Şu an takip kriterine uyan canlı maç bulunmuyor.")

if __name__ == "__main__":
    check_matches()
