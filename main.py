import os
import requests

# GitHub Secrets üzerinden alınacak bilgiler
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


def check_1xbet_live_matches():
    # 1xbet Canlı Maçlar API Adresi
    url = "https://1xbet.com/LiveFeed/GetMatchesZenY?sport=1&isNightMode=false"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        matches = data.get("Value", [])

        valid_matches = []

        for m in matches:
            # Maç dakikası ve periyot bilgisi
            period = m.get("SC", {}).get("CP", 0)  # 1: İlk yarı, 2: İkinci yarı
            time_sec = m.get("SC", {}).get("TS", 0)
            minute = time_sec // 60

            # Dakika Filtresi (1. Yarı 35+ veya 2. Yarı 80+)
            is_valid_time = (period == 1 and minute >= 35) or (
                period == 2 and minute >= 80
            )
            if not is_valid_time:
                continue

            # Korner Bahsi Açık mı Kontrolü (1xbet alt marketlerinde korner var mı?)
            has_corner_market = False
            for sub in m.get("GE", []):
                if "corner" in str(sub).lower() or sub.get("G") == 2:
                    has_corner_market = True
                    break

            # Eğer korner bahsi AÇIK DEĞİLSE bu maçı atla!
            if not has_corner_market:
                continue

            # Şut İstatistiklerini Çek
            stats = m.get("SC", {}).get("S", [])
            shots_on_target = 0
            shots_off_target = 0
            corners = 0

            for s in stats:
                stat_type = s.get("N", "")
                if "Shots on target" in stat_type or "İsabetli" in stat_type:
                    shots_on_target = sum(s.get("S1", [0]) + s.get("S2", [0]))
                elif (
                    "Shots off target" in stat_type or "İsabetsiz" in stat_type
                ):
                    shots_off_target = sum(s.get("S1", [0]) + s.get("S2", [0]))
                elif "Corners" in stat_type or "Korner" in stat_type:
                    corners = sum(s.get("S1", [0]) + s.get("S2", [0]))

            total_shots = shots_on_target + shots_off_target

            valid_matches.append({
                "home": m.get("O1", "Ev"),
                "away": m.get("O2", "Deplasman"),
                "minute": minute,
                "period": period,
                "total_shots": total_shots,
                "corners": corners,
            })

        # Şut sayısına göre büyükten küçüğe sırala
        valid_matches.sort(key=lambda x: x["total_shots"], reverse=True)
        return valid_matches

    except Exception as e:
        print(f"Hata oluştu: {e}")
        return []


def send_telegram():
    matches = check_1xbet_live_matches()
    if not matches:
        print("Kriterlere uyan canlı maç bulunamadı.")
        return

    msg = "🔥 **1XBET KORNERİ AÇIK & BASKILI MAÇLAR** 🔥\n\n"
    for m in matches[:5]:
        per_text = "1. Yarı" if m["period"] == 1 else "2. Yarı"
        msg += f"⚽ **{m['home']} vs {m['away']}**\n"
        msg += f"⏱ Dk {m['minute']} ({per_text})\n"
        msg += (
            f"📊 Toplam Şut: {m['total_shots']} | Mevcut Korner:"
            f" {m['corners']}\n"
        )
        msg += "✅ *Korner Bahsi Aktif*\n"
        msg += "-----------------------------------\n"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, json=payload)


if __name__ == "__main__":
    send_telegram()
