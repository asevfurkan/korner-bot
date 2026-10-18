import os
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def check_1xbet_live_matches():
    # 1xbet Canlı API Adresi (Mobil API - Daha stabil ve engellere takılmaz)
    url = "https://1xbet.com/LiveFeed/GetMatchesZenY?sport=1&isNightMode=false"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"API Hatasi: Status Code {response.status_code}")
            return []
            
        data = response.json()
        matches = data.get("Value", [])

        valid_matches = []

        for m in matches:
            sc = m.get("SC", {})
            period = sc.get("CP", 0)  # 1: 1. Yarı, 2: 2. Yarı
            time_sec = sc.get("TS", 0)
            minute = time_sec // 60 if time_sec else 0

            # Dakika Filtresi: 1. Yarı 35+ veya 2. Yarı 75+ (90+ dahil)
            is_valid_time = (period == 1 and minute >= 35) or (period == 2 and minute >= 75)
            if not is_valid_time:
                continue

            # Korner Bahsi Arama (Genişletilmiş Filtre)
            has_corner_market = False
            
            # Market / Bahis seçeneklerini tara
            for sub in m.get("GE", []):
                sub_str = str(sub).lower()
                if "corner" in sub_str or "korner" in sub_str or sub.get("G") in [2, 28, 48]:
                    has_corner_market = True
                    break

            # Alt etkinliklerde (SubEvents) korner araması
            if not has_corner_market:
                for sub_event in m.get("AE", []):
                    event_name = str(sub_event.get("N", "")).lower()
                    if "corner" in event_name or "korner" in event_name:
                        has_corner_market = True
                        break

            # Eğer korner bahsi AÇIK DEĞİLSE atla
            if not has_corner_market:
                continue

            # Şut ve Korner İstatistikleri
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

            valid_matches.append({
                "home": m.get("O1", "Ev"),
                "away": m.get("O2", "Deplasman"),
                "minute": minute,
                "period": period,
                "total_shots": total_shots,
                "corners": corners
            })

        # Şuta göre sırala
        valid_matches.sort(key=lambda x: x["total_shots"], reverse=True)
        return valid_matches

    except Exception as e:
        print(f"Genel Hata: {e}")
        return []

def send_telegram():
    matches = check_1xbet_live_matches()
    if not matches:
        print("Sartlara uyan mac bulunamadi.")
        return

    msg = "🔥 **1XBET KORNERİ AÇIK MAÇLAR** 🔥\n\n"
    for m in matches[:5]:
        per_text = "1. Yarı" if m["period"] == 1 else "2. Yarı"
        msg += f"⚽ **{m['home']} vs {m['away']}**\n"
        msg += f"⏱ Dk {m['minute']} ({per_text})\n"
        msg += f"📊 Toplam Şut: {m['total_shots']} | Mevcut Korner: {m['corners']}\n"
        msg += "✅ *Korner Bahsi Aktif*\n"
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
