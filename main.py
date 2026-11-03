import os
import requests

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "SENIN_API_KEYIN")
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKENIN")
CHAT_ID = os.getenv("CHAT_ID", "CHAT_ID'N")

SENT_FILE = "sent_matches.txt"

def load_sent_matches():
    if not os.path.exists(SENT_FILE):
        return {}
    sent = {}
    with open(SENT_FILE, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 2:
                sent[parts[0]] = parts[1]
    return sent

def save_sent_match(fixture_id, devre):
    sent = load_sent_matches()
    sent[str(fixture_id)] = devre
    with open(SENT_FILE, "w") as f:
        for fid, dev in sent.items():
            f.write(f"{fid},{dev}\n")

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
    
    onayli_terimler = [
        'championship', 'segunda división', 'serie b', 'ligue 2', 'eerste divisie',
        'cup', 'kupa', 'copa', 'coppa', 'pokal', 'super cup', 'supercup'
    ]
    for onayli in onayli_terimler:
        if onayli in name_lower:
            return True

    yasakli_ifadeler = [
        'u17', 'u19', 'u20', 'u21', 'u23', 'youth', 'reserve', 
        'amateur', 'regional', 'division 3', 'division 4', 
        '2. division', '3. division', '4. division', 
        '2. bundesliga', 'liga 2', '2. liga', '3. liga', '4. liga', 
        '2. lig', '3. lig', '4. lig', 'tercera', 'group b', 'group c',
        '2nd division', '3rd division', '4th division', 'iv divizija', 'iii liga',
        'rfef', 'alef', 'liga alef', 'thai league 2'
    ]
    
    for yasak in yasakli_ifadeler:
        if yasak in name_lower:
            return False
            
    if ('2.' in name_lower or '3.' in name_lower or '4.' in name_lower or '2 ' in name_lower or '3 ' in name_lower or '4 ' in name_lower or 'group 2' in name_lower or 'group 3' in name_lower):
        if 'lig' in name_lower or 'div' in name_lower or 'class' in name_lower or 'group' in name_lower or 'bundesliga' in name_lower or 'rfef' in name_lower:
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
    
    sent_matches = load_sent_matches()
    
    kritik_liste = []
    tum_canli_maclar = []

    for match in matches:
        league_name = match['league']['name']
        if not is_valid_league(league_name):
            continue

        fixture_id = str(match['fixture']['id'])
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        
        fixture_status = match.get('fixture', {}).get('status', {})
        elapsed = fixture_status.get('elapsed')
        extra = fixture_status.get('extra') or 0
        
        s_home = match.get('goals', {}).get('home') or 0
        s_away = match.get('goals', {}).get('away') or 0

        if elapsed is None:
            continue

        if elapsed > 90 and extra:
            if elapsed >= (90 + extra + 4):
                continue

        devre = "1H" if elapsed <= 45 else "2H"

        if fixture_id in sent_matches and sent_matches[fixture_id] == devre:
            continue

        # Yeni esnetilmiş aralık: 
        # 1. Yarı: 35. dakikadan başlayıp devre sonuna ve uzatmalara kadar (örn. 45+4'e kadar)
        # 2. Yarı: 80. dakikadan başlayıp maç sonuna ve uzatmalara kadar (örn. 90+4'e kadar)
        is_first_half_critical = (35 <= elapsed <= (45 + 4))
        is_second_half_critical = (80 <= elapsed <= (90 + 4))

        if is_first_half_critical or is_second_half_critical:
            kritik_liste.append({'id': fixture_id, 'home': home, 'away': away, 'elapsed': elapsed, 'devre': devre, 'league': league_name, 's_home': s_home, 's_away': s_away})
        else:
            distance = (45 - elapsed) if elapsed <= 45 else (90 - elapsed)
            if 0 <= abs(distance) <= 20:
                tum_canli_maclar.append({
                    'id': fixture_id, 'home': home, 'away': away, 
                    'elapsed': elapsed, 'devre': devre, 'league': league_name, 
                    's_home': s_home, 's_away': s_away, 'distance': abs(distance)
                })

    target_list = []
    baslik = ""

    if kritik_liste:
        target_list = kritik_liste
        baslik = "🔥 *KRİTİK ANLAR (35+ / 80+ Uzatmalar Dahil)*"
    elif tum_canli_maclar:
        target_list = tum_canli_maclar
        baslik = "⏳ *DEVRE BİTİMİNE YAKIN MAÇLAR*"

    islenmis_veriler = []
    for m in target_list:
        t_shots, h_s, a_s, t_corners, h_c, a_c = get_detailed_stats(m['id'])
        
        if t_shots == 0 and t_corners == 0:
            continue

        islenmis_veriler.append({
            'id': m['id'],
            'devre': m['devre'],
            'distance': m.get('distance', 0),
            'text': (
                f"⚽ *{m['home']}* {m['s_home']} - {m['s_away']} *{m['away']}*\n"
                f"   🏆 _{m['league']}_\n"
                f"   ⏱️ ({m['devre']} - Dakika: {m['elapsed']}')\n"
                f"   🚨 *TOPLAM KORNER: {t_corners} ({h_c} - {a_c})*\n"
                f"   🎯 *TOPLAM ŞUT: {t_shots} ({h_s} - {a_s})*"
            ),
            'corners': t_corners,
            'shots': t_shots
        })

    if kritik_liste:
        islenmis_veriler.sort(key=lambda x: (x['corners'], x['shots']), reverse=True)
    else:
        islenmis_veriler.sort(key=lambda x: (x['distance'], -x['corners'], -x['shots']))

    en_iyi_uc = islenmis_veriler[:3]

    if en_iyi_uc:
        final_mesaj = baslik + "\n\n" + "\n\n".join([m['text'] for m in en_iyi_uc])
        send_telegram_message(final_mesaj)
        for m in en_iyi_uc:
            save_sent_match(m['id'], m['devre'])
    else:
        send_telegram_message("💤 Şu an kriterlere uyan ve istatistiği bulunan maç bulunmuyor.")

if __name__ == "__main__":
    check_matches()
