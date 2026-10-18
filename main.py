import os
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def check_1xbet_live_matches():
    # Alternatif mobil ve direkt canlı feed endpoint'leri
    urls = [
        "https://1xbet.com/LiveFeed/GetMatchesZenY?sport=1&isNightMode=false",
        "https://1xbet.com/LiveFeed/GetMatchesZenY?sport=1&lng=tr",
        "https://1xbet.com/LiveFeed/GetMatches?sport=1"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://1xbet.com/tr/live/football',
        'Origin': 'https://1xbet.com'
    }

    matches = []
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                matches = data.get("Value", [])
                if matches:
                    print(f"Başarılı endpoint: {url}")
                    break
            else:
                print(f"Endpoint hatası ({url}): Status {response.status_code}")
        except Exception as e:
            print(f"Bağlantı deneme hatası ({url}): {e}")

    if not matches:
        return [], []

    first_half_matches = []
    second_half_matches = []

    for m in matches:
        sc = m.get("SC", {})
        period = sc.get("CP", 0)  
        time_sec = sc.get("TS", 0)
        minute = time_sec // 60 if time_sec else 0

        is_first_half = (period == 1 and minute >= 35)
        is_second_half = (period == 2 and (minute >= 70 or minute == 0 or minute >= 90))

        if not (is_first_half or is_second_half):
            continue

        stats = sc.get("S", [])
        shots_on = 0
        shots_off = 0
        corners = 0

        for s in stats:
            stat_name = str(s.get("N", "")).lower()
            s1 = sum(s.get("S1", [0])) if isinstance(s.get("S1"), list) else (s.get("S1") if isinstance(s.get("S1"), int) else 0)
            s2 = sum(s.get("S2", [0])) if isinstance(s.get("S2"), list) else (s.get("S2") if isinstance(s.get("S2"), int) else 0)
            
            if "shots on" in stat_name or "isabetli" in stat_name:
                shots_on = s1 + s2
            elif "shots off" in stat_name or "isabetsiz" in stat_name:
                shots_off = s1 + s2
            elif "corner" in stat_name or "korner" in stat_name:
                corners = s1 + s2

        total_shots = shots_on + shots_off
        min_str = f"{minute}'" if minute > 0 else "90+'"

        home_team = str(m.get("O1", "Ev")).replace("*", "").replace("_", "")
        away_team = str(m.get("O2", "Deplasman")).replace("*", "").replace("_", "")

        match_data = {
            "id": str(m.get("I", "")),
            "home": home_team,
            "away": away_team,
            "minute": min_str,
            "total_shots": total_shots,
            "corners": corners
        }

        if is_first_half:
            first_half_matches.append(match_data)
        elif is_second_half:
            second_half_matches.append(match_data)

    first_half_matches.sort(key=lambda x: x["total_shots"], reverse=True)
    second_half_matches.sort(key=lambda x: x["total_shots"], reverse=True)

    return first_half_matches, second_half_matches

def send_telegram():
    fh_matches, sh_matches = check_1xbet_live_matches()

    if not fh_matches and not sh_matches:
        print("Uygun kriterde maç bulunamadı.")
        return

    msg = "🔥 1XBET CANLI KORNER / SUT FIRSATLARI 🔥\n\n"

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
    print(f"Telegram API Yanit Kodu: {res.status_code}")

if __name__ == "__main__":
    send_telegram()
