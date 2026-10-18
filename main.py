import os
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_live_matches():
    # Güncel ve engelsiz canlı maç veri kaynağı
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    
    first_half = []
    second_half = []

    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for ev in data.get("events", []):
                status = ev.get("status", {})
                status_type = status.get("type", {}).get("name", "")
                
                if "IN_PROGRESS" not in status_type:
                    continue
                
                clock = status.get("displayClock", "0'")
                try:
                    minute = int("".join(filter(str.isdigit, str(clock))))
                except:
                    minute = 0

                period = status.get("period", 1)
                
                competitions = ev.get("competitions", [{}])
                competitors = competitions[0].get("competitors", [])
                
                home, away = "Ev Sahibi", "Deplasman"
                for comp in competitors:
                    if comp.get("homeAway") == "home":
                        home = comp.get("team", {}).get("displayName", "Ev")
                    elif comp.get("homeAway") == "away":
                        away = comp.get("team", {}).get("displayName", "Deplasman")

                is_fh = (period == 1 and minute >= 35)
                is_sh = (period == 2 and (minute >= 70 or minute == 0 or minute >= 90))

                if is_fh:
                    first_half.append({"home": home, "away": away, "minute": f"{minute}'"})
                elif is_sh:
                    second_half.append({"home": home, "away": away, "minute": f"{minute}'"})
    except Exception as e:
        print(f"Hata: {e}")

    return first_half, second_half

def send_telegram():
    fh, sh = get_live_matches()

    if not fh and not sh:
        print("Kriterlere uyan canlı maç yok.")
        return

    msg = "🔥 **CANLI KORNER / MAÇ FIRSATLARI** 🔥\n\n"

    if fh:
        msg += "📌 **1. YARI (35+ DK)**\n"
        for m in fh:
            msg += f"⚽ **{m['home']} vs {m['away']}** | Dk: {m['minute']}\n"
            msg += "-----------------------------------\n"

    if sh:
        msg += "\n📌 **2. YARI (70+ / UZATMALAR)**\n"
        for m in sh:
            msg += f"⚽ **{m['home']} vs {m['away']}** | Dk: {m['minute']}\n"
            msg += "-----------------------------------\n"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    send_telegram()
