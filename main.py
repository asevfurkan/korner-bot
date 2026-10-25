import os
import time
import requests

API_KEY = os.environ.get("API_FOOTBALL_KEY")
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


def send_telegram_message(message):
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
  try:
    requests.post(url, json=payload)
  except Exception as e:
    print(f"Telegram mesajı gönderilemedi: {e}")


def check_matches():
  url = "https://v3.football.api-sports.io/fixtures?live=all"
  headers = {"x-apisports-key": API_KEY}

  try:
    response = requests.get(url, headers=headers)
    data = response.json()

    if "errors" in data and data["errors"]:
      print(f"API Hatası: {data['errors']}")
      return

    match_list = []

    for match in data.get("response", []):
      fixture_id = match["fixture"]["id"]
      home = match["teams"]["home"]["name"]
      away = match["teams"]["away"]["name"]
      minute = match["fixture"]["status"]["elapsed"]

      # Anlık istatistikleri çek
      stat_url = (
          f"https://v3.football.api-sports.io/fixtures/statistics?fixture="
          f"{fixture_id}"
      )
      stat_resp = requests.get(stat_url, headers=headers)
      stat_data = stat_resp.json()

      corners = {home: 0, away: 0}
      shots = {home: 0, away: 0}

      for team_stat in stat_data.get("response", []):
        team_name = team_stat["team"]["name"]
        for s in team_stat["statistics"]:
          if s["type"] == "Corner Kicks":
            val = s["value"]
            corners[team_name] = int(val) if val is not None else 0
          elif s["type"] == "Total Shots":
            val = s["value"]
            shots[team_name] = int(val) if val is not None else 0

      total_corners = corners[home] + corners[away]
      total_shots = shots[home] + shots[away]

      # Sıralama için skor hesabı (Örn: Kornerin ağırlığı fazla olsun ya da toplamı)
      # Şut ve korneri birlikte önceliklendiren bir puanlama formülü
      score = (total_corners * 2) + total_shots

      match_list.append({
          "home": home,
          "away": away,
          "minute": minute,
          "corners": total_corners,
          "home_c": corners[home],
          "away_c": corners[away],
          "shots": total_shots,
          "home_s": shots[home],
          "away_s": shots[away],
          "score": score,
      })

    # En yüksek skora (en çok korner ve şut) göre maçları büyükten küçüğe sırala
    match_list.sort(key=lambda x: x["score"], reverse=True)

    # En hareketli ilk 3 maçı seç
    top_matches = match_list[:3]

    if top_matches:
      msg = "🔥 *Canlı En Hareketli Maçlar (Korner & Şut Öncelikli)* 🔥\n\n"
      for i, m in enumerate(top_matches, 1):
        msg += (
            f"*{i}. {m['home']} vs {m['away']}* (Dakika: {m['minute']}')\n"
            f"   🔹 Toplam Korner: {m['corners']} ({m['home_c']} -"
            f" {m['away_c']})\n"
            f"   🔸 Toplam Şut: {m['shots']} ({m['home_s']} - {m['away_s']})\n\n"
        )
      send_telegram_message(msg)

  except Exception as e:
    print(f"Hata oluştu: {e}")


print("Akıllı maç takip botu çalışmaya başladı...")
check_matches()
