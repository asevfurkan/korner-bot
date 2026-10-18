import os
import requests
import json

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SENT_FILE = "sent_matches.json"

def load_sent_matches():
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_sent_matches(sent_list):
    if len(sent_list) > 100:
        sent_list = sent_list[-100:]
    with open(SENT_FILE, "w") as f:
        json.dump(sent_list, f)

def check_1xbet_live_matches():
    url = "https://1xbet.com/LiveFeed/GetMatchesZenY?sport=1&isNightMode=false"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return [], []
            
        data = response.json()
        matches = data.get("Value", [])

        first_half_matches = []
        second_half_matches = []

        for m in matches:
            sc = m.get("SC", {})
            period = sc.get("CP", 0)  
            time_sec = sc.get("TS", 0)
            minute = time_sec // 60 if time_sec else 0

            # 1. Yarı 35+ dk VEYA 2. Yarı (70+ dk, 80+, 90+ uzatmalar dahil)
            is_first_half = (period == 1 and minute >= 35)
            is_second_half = (period == 2 and (minute >= 70 or minute == 0)) # Dakika 0 görünse bile 2. yarıdaysa kapsar

            if not (is_first_half or is_second_half):
                continue

            # Korner Bahsi Arama (Genişletilmiş)
            has_corner_market = False
            for sub in m.get("GE", []):
                sub_str = str(sub).lower()
                if "corner" in sub_str or "korner" in sub_str or sub.get("G") in [2, 28, 48]:
                    has_corner_market = True
                    break

            if not has_corner_market:
                for sub_event in m.get("AE", []):
                    event_name = str(sub_event.get("N", "")).lower()
                    if "corner" in event_name or "korner" in event_name:
                        has_corner_market = True
                        break

            # 1xbet bazen korneri doğrudan verir, eğer pazar kapalı görünmüyorsa dahil et
            if not has_corner_market:
                continue

            stats = sc.get("S", [])
            shots_on = 0
            shots_off = 0
            corners = 0

            for s in stats:
                stat_name = str(s.get("N", "")).lower()
                s1 = sum(s.get("S1", [0])) if isinstance(s.get("S1"), list) else 0
                s2 = sum(s.get("S2", [0])) if isinstance(s.get("S2"), list) else 0
                
                if "shots on target" in stat_name or "isabetli" in stat_name:
                    shots_on = s1 + s2
                elif "shots off target" in stat_name or "isabetsiz" in stat_name:
                    shots_off = s1 + s2
                elif "corners" in stat_name or "korner" in stat_name:
                    corners = s1 + s2

            total_shots = shots_on + shots_off

            match_data = {
                "id": str(m.get("I", "")),
                "home": m.get("O1", "Ev"),
                "away": m.get("O2", "Deplasman"),
                "minute": minute if minute > 0 else "90+",
                "period": period,
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

    except Exception as e:
        print(f"Hata: {e}")
        return [], []

def send_telegram():
    # Telegram Bağlantı Testi (Sisteminizin çalıştığını doğrulamak için)
    test_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    test_payload = {
        "chat_id": CHAT_ID,
        "text": "🤖 **BOT AKTİF VE TARAMA YAPIYOR!**\n\nTelegram bağlantın sorunsuz çalışıyor knk. Uygun maç yakalandığında altında listelenecek!",
        "parse_mode": "Markdown"
    }
    
    fh_matches, sh_matches = check_1xbet_live_matches()
    sent_list = load_sent_matches()

    new_fh = [m for m in fh_matches if m["id"] not in sent_list]
    new_sh = [m for m in sh_matches if m["id"] not in sent_list]

    if not new_fh and not new_sh:
        print("Gonderilecek yeni mac yok ama test mesaji gonderiliyor.")
        # Sadece test amaçlı botun çalıştığını hissettirmek için mesaj gönder
        requests.post(test_url, json=test_payload)
        return

    msg = "🔥 **1XBET KORNER FIRSATLARI** 🔥\n\n"

    if new_fh:
        msg += "📌 **1. YARI (35+ DK)**\n"
        for m in new_fh:
            msg += f"⚽ **{m['home']} vs {m['away']}**\n"
            msg += f"⏱ Dk {m['minute']} | Şut: {m['total_shots']} | Korner: {m['corners']}\n"
            msg += "-----------------------------------\n"
            sent_list.append(m["id"])

    if new_sh:
        msg += "\n📌 **2. YARI (70+ / UZATMALAR)**\n"
        for m in new_sh:
            msg += f"⚽ **{m['home']} vs {m['away']}**\n"
            msg += f"⏱ Dk {m['minute']} | Şut: {m['total_shots']} | Korner: {m['corners']}\n"
            msg += "-----------------------------------\n"
            sent_list.append(m["id"])

    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    
    res = requests.post(test_url, json=payload)
    if res.status_code == 200:
        save_sent_matches(sent_list)

if __name__ == "__main__":
    send_telegram()
