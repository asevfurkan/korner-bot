import os
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

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
            period = sc.get("CP", 0)  # 1: 1. Yarı, 2: 2. Yarı
            time_sec = sc.get("TS", 0)
            minute = time_sec // 60 if time_sec else 0

            # 1. Yarı 35+ dk VEYA 2. Yarı 75+ dk (80+ ve uzatmalar dahil)
            is_first_half = (period == 1 and minute >= 35)
            is_second_half = (period == 2 and minute >= 75)

            if not (is_first_half or is_second_half):
                continue

            # Korner Bahsi Arama
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

            if not has_corner_market:
                continue

            # İstatistikler
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
                "home": m.get("O1", "Ev"),
                "away": m.get("O2", "Deplasman"),
                "minute": minute,
                "period": period,
                "total_shots": total_shots,
                "corners": corners
            }

            if is_first_half:
                first_half_matches.append(match_data)
            elif is_second_half:
                second_half_matches.append(match_data)

        # Şuta göre azalandan artana sırala
        first_half_matches.sort(key=lambda x: x["total_shots"], reverse=True)
        second_half_matches.sort(key=lambda x: x["total_shots"], reverse=True)

        # En şutlu 3'er maçı seç
        return first_half_matches[:3], second_half_matches[:3]

    except Exception as e:
        print(f"Hata: {e}")
        return [], []

def send_telegram():
    fh_matches, sh_matches = check_1xbet_live_matches()
    
    if not fh_matches and not sh_matches:
        print("Sartlara uyan mac bulunamadi.")
        return

    msg = "🔥 **1XBET KORNERİ AÇIK MAÇLAR** 🔥\n\n"

    # 1. Yarı Maçları
    if fh_matches:
        msg += "📌 **1. YARI MAÇLARI (35+ DK)**\n"
        for m in fh_matches:
            msg += f"⚽ **{m['home']} vs {m['away']}**\n"
            msg += f"⏱ Dk {m['minute']}\n"
            msg += f"📊 Toplam Şut: {m['total_shots']} | Korner: {m['corners']}\n"
            msg += "-----------------------------------\n"

    # 2. Yarı Maçları
    if sh_matches:
        msg += "\n📌 **2. YARI MAÇLARI (75+ DK / 80+ DK)**\n"
        for m in sh_matches:
            msg += f"⚽ **{m['home']} vs {m['away']}**\n"
            msg += f"⏱ Dk {m['minute']}\n"
            msg += f"📊 Toplam Şut: {m['total_shots']} | Korner: {m['corners']}\n"
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
