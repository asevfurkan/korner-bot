
import html
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

API_BASE = "https://v3.football.api-sports.io"
SENT_FILE = Path("sent_matches.txt")
PENDING_FILE = Path("pending_snapshots.json")
HISTORY_FILE = Path("corner_history.json")
DIAGNOSTIC_FILE = Path("diagnostic_state.json")

REQUEST_TIMEOUT = 20
MAX_MATCHES_IN_MESSAGE = 3
DIAGNOSTIC_INTERVAL_MINUTES = 30


def now_utc():
    return datetime.now(timezone.utc)


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
        raise RuntimeError("Eksik GitHub Secrets: " + ", ".join(missing))


def api_headers():
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

    if payload.get("errors"):
        raise RuntimeError(f"API-Football hatası: {payload['errors']}")

    return payload.get("response", [])


def read_json(path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"{path} okunamadı: {exc}")
        return default


def write_json(path, data):
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    temp_path.replace(path)


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
    return not any(term in name for term in banned_terms)


def to_int(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip().replace("%", "").replace(",", ".")
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def get_match_stats(fixture_id, home_team_id, away_team_id, first_half=False):
    params = {"fixture": fixture_id}
    if first_half:
        params["half"] = "true"

    rows = api_get("fixtures/statistics", params)
    if not rows:
        return None

    stats_by_team = {
        home_team_id: {"shots": None, "shots_on_target": None, "corners": None},
        away_team_id: {"shots": None, "shots_on_target": None, "corners": None},
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

    if home["corners"] is None or away["corners"] is None:
        return None

    def sum_if_known(a, b):
        return a + b if a is not None and b is not None else None

    return {
        "total_shots": sum_if_known(home["shots"], away["shots"]),
        "shots_on_target": sum_if_known(
            home["shots_on_target"], away["shots_on_target"]
        ),
        "total_corners": home["corners"] + away["corners"],
        "home_shots": home["shots"],
        "away_shots": away["shots"],
        "home_corners": home["corners"],
        "away_corners": away["corners"],
    }


def get_phase(match):
    fixture = match.get("fixture") or {}
    status_data = fixture.get("status") or {}
    status = status_data.get("short")
    elapsed = status_data.get("elapsed")

    if elapsed is None:
        return None
    if status == "1H" and elapsed >= 35:
        return "1H"
    if status == "2H" and elapsed >= 80:
        return "2H"
    return None


def format_minute(elapsed, extra):
    minute = str(elapsed)
    if extra:
        minute += f"+{extra}"
    return minute


def diagnostic_text(counts):
    return (
        "\n\n<b>🔎 KONTROL RAPORU</b>\n"
        f"Canlı maç: {counts['live']}\n"
        f"Filtre nedeniyle elenen: {counts['league_rejected']}\n"
        f"Dakika/devre uygun değil: {counts['phase_rejected']}\n"
        f"Daha önce bildirilmiş/beklemede: {counts['already_handled']}\n"
        f"Korner verisi eksik: {counts['missing_corners']}\n"
        f"Uygun aday: {counts['candidates']}\n"
        f"Seçilen maç: {counts['selected']}"
    )


def send_diagnostic_if_due(counts):
    state = read_json(DIAGNOSTIC_FILE, {})
    last_sent = state.get("last_sent")

    if last_sent:
        try:
            last_time = datetime.fromisoformat(last_sent)
            if now_utc() - last_time < timedelta(
                minutes=DIAGNOSTIC_INTERVAL_MINUTES
            ):
                print("Tanılama raporu bekleme süresinde; Telegram mesajı gönderilmedi.")
                return
        except (TypeError, ValueError):
            pass

    message = (
        "💤 <b>Uygun maç bulunamadı.</b>\n"
        "Aşağıda son kontrolün nedeni var."
        + diagnostic_text(counts)
    )

    send_telegram_message(message)
    write_json(DIAGNOSTIC_FILE, {"last_sent": now_utc().isoformat()})
    print("Telegram tanılama raporu gönderildi.")


def build_message(matches, counts):
    lines = [
        "🔥 <b>KORNER TAKİP LİSTESİ</b>",
        "<i>Sıralama: korner → toplam şut → isabetli şut</i>",
        "",
    ]

    for index, item in enumerate(matches, start=1):
        match = item["match"]
        status_data = (match.get("fixture") or {}).get("status") or {}
        minute = format_minute(
            status_data.get("elapsed"),
            status_data.get("extra") or 0,
        )

        home = html.escape(match["teams"]["home"]["name"])
        away = html.escape(match["teams"]["away"]["name"])
        league = html.escape(match["league"]["name"])
        goals = match.get("goals") or {}
        stats = item["stats"]
        phase_text = "İLK YARI" if item["phase"] == "1H" else "İKİNCİ YARI"

        lines.extend([
            f"<b>{index}. {home} {goals.get('home')} - {goals.get('away')} {away}</b>",
            f"🏆 {league}",
            f"⏱️ {phase_text} · {minute}. dakika",
            f"🚩 <b>Korner: {stats['total_corners']}</b> "
            f"({stats['home_corners']} - {stats['away_corners']})",
            f"🎯 <b>Şut: {stats['total_shots'] if stats['total_shots'] is not None else 'Veri yok'}</b>",
            f"🥅 İsabetli şut: {stats['shots_on_target'] if stats['shots_on_target'] is not None else 'Veri yok'}",
            "",
        ])

    lines.append(
        "<i>Bu liste istatistik sıralamasıdır; korner olacağını garanti etmez.</i>"
    )
    lines.append(diagnostic_text(counts))
    return "\n".join(lines)


def create_snapshot(item):
    match = item["match"]
    fixture = match.get("fixture") or {}
    status = fixture.get("status") or {}
    teams = match.get("teams") or {}
    goals = match.get("goals") or {}

    return {
        "fixture_id": str(fixture.get("id")),
        "phase": item["phase"],
        "minute": status.get("elapsed"),
        "extra": status.get("extra") or 0,
        "home_team_id": (teams.get("home") or {}).get("id"),
        "away_team_id": (teams.get("away") or {}).get("id"),
        "home": (teams.get("home") or {}).get("name", "Ev sahibi"),
        "away": (teams.get("away") or {}).get("name", "Deplasman"),
        "league": (match.get("league") or {}).get("name", ""),
        "score": f"{goals.get('home')}-{goals.get('away')}",
        "snapshot_corners": item["stats"]["total_corners"],
        "snapshot_shots": item["stats"]["total_shots"],
        "snapshot_shots_on_target": item["stats"]["shots_on_target"],
        "created_at": now_utc().isoformat(),
    }


def is_first_half_finished(status):
    return status in {"HT", "2H", "ET", "P", "FT", "AET", "PEN"}


def is_match_finished(status):
    return status in {"FT", "AET", "PEN", "AWD", "WO"}


def finalize_pending_snapshots():
    pending = read_json(PENDING_FILE, [])
    history = read_json(HISTORY_FILE, [])

    if not pending:
        return

    still_pending = []
    completed_count = 0

    for snapshot in pending:
        fixture_id = snapshot["fixture_id"]
        phase = snapshot["phase"]

        try:
            match_rows = api_get("fixtures", {"id": fixture_id})
            if not match_rows:
                still_pending.append(snapshot)
                continue

            match = match_rows[0]
            status = (
                (match.get("fixture") or {}).get("status") or {}
            ).get("short")

            if phase == "1H" and not is_first_half_finished(status):
                still_pending.append(snapshot)
                continue
            if phase == "2H" and not is_match_finished(status):
                still_pending.append(snapshot)
                continue

            stats = get_match_stats(
                fixture_id,
                snapshot["home_team_id"],
                snapshot["away_team_id"],
                first_half=(phase == "1H"),
            )

            if stats is None:
                # Veri henüz gelmediyse geçmişe veri yok diye yazıp silme.
                still_pending.append(snapshot)
                print(f"{fixture_id}: sonuç korner verisi henüz yok, tekrar denenecek.")
                continue

            corners_after = max(
                0, stats["total_corners"] - snapshot["snapshot_corners"]
            )
            success = corners_after >= 1

            history.append({
                **snapshot,
                "result_status": "ölçüldü",
                "corners_after_alert": corners_after,
                "at_least_one_corner": success,
                "final_corners": stats["total_corners"],
                "completed_status": status,
                "completed_at": now_utc().isoformat(),
            })
            completed_count += 1

            print(
                f"Öneri sonucu: {fixture_id} / {phase} / "
                f"sonraki korner: {corners_after}"
            )

        except (requests.RequestException, RuntimeError, KeyError) as exc:
            print(f"{fixture_id} öneri sonucu kontrol edilemedi: {exc}")
            still_pending.append(snapshot)

    write_json(PENDING_FILE, still_pending)
    write_json(HISTORY_FILE, history)

    if completed_count:
        print(f"Sonucu kaydedilen öneri sayısı: {completed_count}")


def print_history_summary():
    history = read_json(HISTORY_FILE, [])
    measured = [
        item for item in history
        if item.get("result_status") == "ölçüldü"
        and item.get("at_least_one_corner") is not None
    ]

    if not measured:
        print("Henüz ölçülebilir öneri geçmişi yok.")
        return

    successes = sum(1 for item in measured if item["at_least_one_corner"])
    rate = successes / len(measured) * 100

    print(
        f"ÖNERİ İSTATİSTİĞİ: {successes}/{len(measured)} öneriden sonra "
        f"en az 1 korner geldi. Başarı oranı: %{rate:.1f}"
    )

    for phase, label in (("1H", "İlk yarı"), ("2H", "İkinci yarı")):
        group = [item for item in measured if item.get("phase") == phase]
        if group:
            wins = sum(1 for item in group if item["at_least_one_corner"])
            print(f"{label}: {wins}/{len(group)} = %{wins / len(group) * 100:.1f}")


def check_matches():
    require_secrets()
    finalize_pending_snapshots()

    live_matches = api_get("fixtures", {"live": "all"})
    sent = load_sent_matches()
    pending = read_json(PENDING_FILE, [])

    pending_keys = {
        (str(item.get("fixture_id")), item.get("phase"))
        for item in pending
    }

    counts = {
        "live": len(live_matches),
        "league_rejected": 0,
        "phase_rejected": 0,
        "already_handled": 0,
        "missing_corners": 0,
        "candidates": 0,
        "selected": 0,
    }

    candidates = []

    for match in live_matches:
        league_name = (match.get("league") or {}).get("name", "")

        if not is_valid_league(league_name):
            counts["league_rejected"] += 1
            continue

        phase = get_phase(match)
        if phase is None:
            counts["phase_rejected"] += 1
            continue

        fixture_id = str((match.get("fixture") or {}).get("id"))

        if not fixture_id:
            continue

        if sent.get(fixture_id) == phase or (fixture_id, phase) in pending_keys:
            counts["already_handled"] += 1
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
        except (requests.RequestException, RuntimeError) as exc:
            print(f"{fixture_id} istatistik isteği başarısız: {exc}")
            counts["missing_corners"] += 1
            continue

        if stats is None:
            counts["missing_corners"] += 1
            print(
                f"{fixture_id}: korner istatistiği yok. "
                "Bu maç sonraki kontrolde yeniden denenecek."
            )
            # sent veya pending listesine eklenmiyor; sonraki çalıştırma tekrar dener.
            continue

        candidates.append({
            "match": match,
            "phase": phase,
            "stats": stats,
        })

    candidates.sort(
        key=lambda item: (
            item["stats"]["total_corners"],
            item["stats"]["total_shots"] or 0,
            item["stats"]["shots_on_target"] or 0,
        ),
        reverse=True,
    )

    counts["candidates"] = len(candidates)
    selected = candidates[:MAX_MATCHES_IN_MESSAGE]
    counts["selected"] = len(selected)

    if not selected:
        print("Bu kontrolde bildirilecek uygun maç bulunamadı.")
        print(diagnostic_text(counts))
        try:
            send_diagnostic_if_due(counts)
        except (requests.RequestException, RuntimeError) as exc:
            print(f"Telegram tanılama mesajı gönderilemedi: {exc}")

        print_history_summary()
        return

    # Önce Telegram bildirimi gönderilir.
    send_telegram_message(build_message(selected, counts))

    # Gönderim başarılı olursa bildirim kayıtları kalıcılaştırılır.
    for item in selected:
        snapshot = create_snapshot(item)
        pending.append(snapshot)
        sent[snapshot["fixture_id"]] = item["phase"]

    save_sent_matches(sent)
    write_json(PENDING_FILE, pending)

    print(f"Telegram bildirimi gönderildi. Maç sayısı: {len(selected)}")
    print_history_summary()


if __name__ == "__main__":
    try:
        check_matches()
    except Exception as exc:
        print(f"BOT HATASI: {exc}")
        sys.exit(1)
