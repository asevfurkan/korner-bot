import os
import time
import requests

# GitHub'daki secret isimlerine göre ayarlandı
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


def check_corners():
  url = "https://v3.football.api-sports.io/fixtures?live=all"
  headers = {"x-apisports-key": API_KEY}

  try:
    response = requests.get(url, headers=headers)
    data = response.json()

    if "errors" in data and data["errors"]:
      print(f"API Hatası: {data['errors']}")
      return

    for match in data.get("response", []):
      fixture_id = match["fixture"]["id"]
      home = match["teams"]["home"]["name"]
      away = match["teams"]["away"]["name"]
      minute = match["fixture"]["status"]["elapsed"]

      # Maçın anlık istatistiklerini çekiyoruz
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

      # Kriter: Toplam korner 8 veya üzeriyse bildirim gönder
      if total_corners >= 8:
        msg = (
            f"⚽ *Korner & Şut Alarmı!*\n"
            f"{home} vs {away} (Dakika: {minute}')\n\n"
            f"🔹 *Toplam Korner:* {total_corners} "
            f"({home}: {corners[home]} - {away}: {corners[away]})\n"
            f"🔸 *Toplam Şut:* {total_shots} "
            f"({home}: {shots[home]} - {away}: {shots[away]})"
        )
        send_telegram_message(msg)

  except Exception as e:
    print(f"Hata oluştu: {e}")


print("Korner ve şut takip botu çalışmaya başladı...")
check_corners()
