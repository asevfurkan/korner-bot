import os
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_live_matches_pro():
    # Dünyadaki tüm canlı maçları saniyesinde çeken açık futbol veri havuzu
    url = "https://www.thesportsdb.com/api/v1/json/3/latestsoccer.php"
    
    # Alternatif küresel canlı skor servisi
    alt_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"

    first_half_matches = []
    second_half_matches = []

    try:
        # ESPN Canlı Skor Servisini Deneyelim (Asla engellenmez, anlıktır)
        response = requests.get(alt_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])
            
            for ev in events:
                status = ev.get("status", {})
                status_type = status.get("type", {}).get("name", "")
                
                # Sadece canlı oynanan maçlar (STATUS_IN_PROGRESS)
                if "IN_PROGRESS" not in status_type:
                    continue
                
                # Maç dakikası
                minute = status.get("displayClock", "0'")
                # Dakikayı sayıya çevir (Örn: "41'" -> 41)
                try:
                    min_val = int("".join(filter(str.isdigit, str(minute))))
                except:
                    min_val = 0

                period = status.get("period", 1) # 1: İlk Yarı, 2: İkinci Yarı

                # Takım isimleri
                competitions = ev.get("competitions", [{}])
                competitors = competitions[0].get("competitors", [])
                
                home_team = "Ev Sahibi"
                away_team = "Deplasman"
                
                for comp in competitors:
                    if comp.get("homeAway") == "home":
                        home_team = comp.get("team", {}).get("displayName", "Ev")
                    elif comp.get("homeAway") == "away":
                        away_team = comp.get("team", {}).get("displayName", "Deplasman")

                # Kriter Kontrolü
                is_fh = (period == 1 and min_val >= 35)
                is_sh = (period == 2 and (min_val >= 70 or min_val == 0 or min_val >= 90))

                if not (is_fh or is_sh):
                    continue

                match_data = {
                    "home": home_team,
                    "away": away_team,
                    "minute": f"{min_val}'",
                    "total_shots": "Canlı", 
                    "corners": "Canlı"
                }

                if is_fh:
                    first_half_matches.append(match_data)
                elif is_sh:
                    second_half_matches.append(match_data)

    except Exception as e:
        print(f"Canlı maç çekme hatası: {e}")

    return first_half_matches, second_half_matches

def send_telegram():
    fh_matches, sh_matches = get_live_matches_pro()

    if not fh_matches and not sh_matches:
        print("Şu an kriterlere uyan canlı maç bulunamadı.")
        return

    msg = "🚨 **CANLI MAÇ FIRSATI YAKALANDI!** 🚨\n\n"

    if fh_matches:
        msg += "📌 **1. YARI (35+ DK)**\n"
        for m in fh_matches:
            msg += f"⚽ **{m['home']} vs {m['away']}**\n"
            msg += f"⏱ Dakika: {m['minute']}\n"
            msg += "-----------------------------------\n"

    if sh_matches:
        msg += "\n📌 **2. YARI (70+ / UZATMALAR)**\n"
        for m in sh_matches:
            msg += f"⚽ **{m['home']} vs {m['away']}**\n"
            msg += f"⏱ Dakika: {m['minute']}\n"
            msg += "-----------------------------------\n"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    
    res = requests.post(url, json=payload)
    print(f"Telegram Yanıt Kodu: {res.status_code}")

if __name__ == "__main__":
    send_telegram()
