import os
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_real_live_matches():
    # Canlı Skor ve İstatistik API'si
    url = "https://football-api-quick.p.rapidapi.com/live" 
    # Alternatif açık canlı maç adresi
    backup_url = "https://api.sofascore.com/api/v1/sport/football/events/live"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
    }

    first_half_matches = []
    second_half_matches = []

    try:
        response = requests.get(backup_url, headers=headers, timeout=10)
        if response.status_code == 200:
            events = response.json().get("events", [])
            for ev in events:
                status = ev.get("status", {}).get("type", "")
                if status != "inprogress":
                    continue
                
                # Dakika bilgisi
                time_info = ev.get("time", {})
                played_time = time_info.get("played", 0)
                minute = played_time // 60 if played_time else 0
                
                # Periyot
                description = ev.get("status", {}).get("description", "")
                
                is_fh = ("1st" in description or minute <= 45) and minute >= 35
                is_sh = ("2nd" in description or minute > 45) and (minute >= 70 or minute >= 90)

                if not (is_fh or is_sh):
                    continue

                home = ev.get("homeTeam", {}).get("name", "Ev")
                away = ev.get("awayTeam", {}).get("name", "Deplasman")

                min_str = f"{minute}'" if minute <= 90 else "90+'"

                match_data = {
                    "home": home,
                    "away": away,
                    "minute": min_str,
                    "total_shots": 0, # Varsayılan
                    "corners": 0
                }

                if is_fh:
                    first_half_matches.append(match_data)
                elif is_sh:
                    second_half_matches.append(match_data)

    except Exception as e:
        print(f"Hata: {e}")

    return first_half_matches, second_half_matches

def send_telegram():
    fh_matches, sh_matches = get_real_live_matches()

    if not fh_matches and not sh_matches:
        print("Şu an kriterlere uyan gerçek canlı maç yok.")
        return

    msg = "🔥 **GERÇEK CANLI KORNER / MAÇ FIRSATLARI** 🔥\n\n"

    if fh_matches:
        msg += "📌 **1. YARI (35+ DK)**\n"
        for m in fh_matches:
            msg += f"⚽ **{m['home']} vs {m['away']}**\n"
            msg += f"⏱ Dk: {m['minute']}\n"
            msg += "-----------------------------------\n"

    if sh_matches:
        msg += "\n📌 **2. YARI (70+ / UZATMALAR)**\n"
        for m in sh_matches:
            msg += f"⚽ **{m['home']} vs {m['away']}**\n"
            msg += f"⏱ Dk: {m['minute']}\n"
            msg += "-----------------------------------\n"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    
    requests.post(url, json=payload)

if __name__ == "__main__":
    send_telegram()
