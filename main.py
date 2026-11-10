import html
import os
import sys
from pathlib import Path

import requests

# GitHub Actions -> Settings -> Secrets and variables -> Actions
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

API_BASE = "https://v3.football.api-sports.io"
SENT_FILE = Path("sent_matches.txt")
REQUEST_TIMEOUT = 20
MAX_MATCHES_IN_MESSAGE = 3


def require_secrets():
    missing = [
        name for name, value in (
            ("API_FOOTBALL_KEY", API_FOOTBALL_KEY),
            ("BOT_TOKEN", BOT_TOKEN),
            ("CHAT_ID", CHAT_ID),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Eksik GitHub Secrets: " + ", ".join(missing)
        )


def api_headers():
    # API-Sports / API-Football doğrudan API anahtarı.
    return {"x-apisports-key": API_FOOTBALL_KEY}


def api_get(endpoint, params):
    response = requests.get(
        f"{API_BASE}/{endpoint}",
        headers=api_headers(),
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()

    errors = payload.get("errors")
    if errors:
        raise RuntimeError(f"API-Football hatası: {errors}")

    return payload.get("response", [])


def load_sent_matches():
    sent = {}
    if not SENT_FILE.exists():
        return sent

    with SENT_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split(",", 1)
            if len(parts) == 2:
                sent[parts[0]] = parts[1]
    return sent


def save_sent_matches(sent):
    temp_file = SENT_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        for fixture_id, phase in sorted(sent.items()):
            file.write(f"{fixture_id},{phase}\n")
    temp_file.replace(SENT_FILE)


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(f"Telegram gönderim hatası: {result}")

    return True


def is_valid_league(league_name):
    name = (league_name or "").casefold()

    # Önce eleme: Örneğin "U19 Cup" yalnızca "Cup" içeriyor diye kabul edilmesin.
    banned_terms = [
        "u17", "u18", "u19", "u20", "u21", "u23",
        "youth", "reserve", "amateur", "regional",
        "division 3", "division 4",
        "2. bundesliga", "liga 2", "2. liga", "3. liga", "4. liga",
        "2. lig", "3. lig", "4. lig", "tercera",
        "group b", "group c", "2nd division", "3rd division",
        "4th division", "iv divizija", "iii liga",
        "rfef", "alef", "liga alef", "thai league 2",
    ]
    if any(term in name for term in banned_terms):
        return False

    allowed_terms = [
        "championship", "segunda división", "serie b", "ligue 2",
        "eerste divisie", "cup", "kupa", "copa", "coppa",
        "pokal", "super cup", "supercup",
    ]
    if any(term in name for term in allowed_terms):
        return True

    return True


def to_int(value):
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace("%", "").replace(",", ".")
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return 0


def get_match_stats(fixture_id, home_team_id, away_team_id):
    rows = api_get("fixtures/statistics", {"fixture": fixture_id})

    stats_by_team = {
        home_team_id: {"shots": 0, "shots_on_target": 0, "corners": 0},
        away_team_id: {"shots": 0, "shots_on_target": 0, "corners": 0},
    }

    for team_row in rows:
        team_id = (team_row.get("team") or {}).get("id")
        if team_id not in stats_by_team:
            continue

        for item in team_row.get("statistics") or []:
            stat_type = item.get("type")
            value = to_int(item.get("value"))

            if stat_type == "Total Shots":
                stats_by_team[team_id]["shots"] = value
            elif stat_type == "Shots on Goal":
                stats_by_team[team_id]["shots_on_target"] = value
            elif stat_type == "Corner Kicks":
                stats_by_team[team_id]["corners"] = value

    home = stats_by_team[home_team_id]
    away = stats_by_team[away_team_id]

    total_shots = home["shots"] + away["shots"]
    total_shots_on_target = (
        home["shots_on_target"] + away["shots_on_target"]
    )
    total_corners = home["corners"] + away["corners"]

    # İstatistik endpoint'i boş döndüyse bu maçı sıralamaya sokma.
    if not rows:
        return None

    return {
        "total_shots": total_shots,
        "shots_on_target": total_shots_on_target,
        "total_corners": total_corners,
        "home_shots": home["shots"],
        "away_shots": away["shots"],
        "home_corners": home["corners"],
        "away_corners": away["corners"],
    }


def get_phase(match):
    fixture = match.get("fixture") or {}
    status = (fixture.get("status") or {}).get("short")
    elapsed = fixture.get("status", {}).get("elapsed")

    if elapsed is None:
        return None

    # HT / FT gibi durumlar bilerek kabul edilmiyor.
    # 1H durumunda 45+ uzatma sürüyorsa maç hâlâ oynandığı için alınabilir.
    if status == "1H" and elapsed >= 35:
        return "1H"

    if status == "2H" and elapsed >= 80:
        return "2H"

    return None


def format_minute(status, elapsed, extra):
    minute = str(elapsed)
    if extra:
        minute += f"+{extra}"
    return minute


def build_message(matches):
    lines = [
        "🔥 <b>KORNER TAKİP LİSTESİ</b>",
        "<i>Sıralama: korner → toplam şut → isabetli şut</i>",
        "",
    ]

    for index, item in enumerate(matches, start=1):
        match = item["match"]
        fixture = match.get("fixture") or {}
        status_data = fixture.get("status") or {}
        elapsed = status_data.get("elapsed")
        extra = status_data.get("extra") or 0
        minute = format_minute(status_data.get("short"), elapsed, extra)

        home = html.escape(match["teams"]["home"]["name"])
        away = html.escape(match["teams"]["away"]["name"])
        league = html.escape(match["league"]["name"])
        goals = match.get("goals") or {}
        home_goals = goals.get("home")
        away_goals = goals.get("away")

        stats = item["stats"]
        phase_text = "İLK YARI" if item["phase"] == "1H" else "İKİNCİ YARI"

        lines.extend([
            f"<b>{index}. {home} {home_goals} - {away_goals} {away}</b>",
            f"🏆 {league}",
            f"⏱️ {phase_text} · {minute}. dakika",
            (
                f"🚩 <b>Korner: {stats['total_corners']}</b> "
                f"({stats['home_corners']} - {stats['away_corners']})"
            ),
            (
                f"🎯 <b>Şut: {stats['total_shots']}</b> "
                f"({stats['home_shots']} - {stats['away_shots']})"
            ),
            f"🥅 İsabetli şut: {stats['shots_on_target']}",
            "",
        ])

    lines.append(
        "<i>Bu liste istatistik sıralamasıdır; korner olacağını garanti etmez.</i>"
    )
    return "\n".join(lines)


def check_matches():
    require_secrets()

    live_matches = api_get("fixtures", {"live": "all"})
    sent = load_sent_matches()
    candidates = []

    for match in live_matches:
        league_name = (match.get("league") or {}).get("name", "")
        if not is_valid_league(league_name):
            continue

        phase = get_phase(match)
        if phase is None:
            continue

        fixture_id = str((match.get("fixture") or {}).get("id"))
        if not fixture_id or sent.get(fixture_id) == phase:
            continue

        teams = match.get("teams") or {}
        home_team_id = (teams.get("home") or {}).get("id")
        away_team_id = (teams.get("away") or {}).get("id")
        if home_team_id is None or away_team_id is None:
            continue

        try:
            stats = get_match_stats(
                fixture_id, home_team_id, away_team_id
            )
        except requests.RequestException as exc:
            print(f"{fixture_id} istatistik isteği başarısız: {exc}")
            continue
        except RuntimeError as exc:
            print(f"{fixture_id} istatistik hatası: {exc}")
            continue

        if stats is None:
            continue

        candidates.append({
            "match": match,
            "phase": phase,
            "stats": stats,
        })

    # Önce toplam korner, eşitse toplam şut, sonra isabetli şut.
    candidates.sort(
        key=lambda item: (
            item["stats"]["total_corners"],
            item["stats"]["total_shots"],
            item["stats"]["shots_on_target"],
        ),
        reverse=True,
    )

    selected = candidates[:MAX_MATCHES_IN_MESSAGE]

    if not selected:
        print("Bu kontrolde bildirilecek uygun maç bulunamadı.")
        return

    message = build_message(selected)
    send_telegram_message(message)

    # Yalnızca Telegram gönderimi başarılı olursa maçları gönderildi olarak kaydet.
    for item in selected:
        fixture_id = str(item["match"]["fixture"]["id"])
        sent[fixture_id] = item["phase"]

    save_sent_matches(sent)
    print(f"Telegram bildirimi gönderildi. Maç sayısı: {len(selected)}")


if __name__ == "__main__":
    try:
        check_matches()
    except Exception as exc:
        print(f"BOT HATASI: {exc}")
        sys.exit(1)
