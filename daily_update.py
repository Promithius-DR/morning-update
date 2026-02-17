import os
import requests
from datetime import datetime, timezone, timedelta

PUSHOVER_TOKEN = os.environ["PUSHOVER_TOKEN"]
PUSHOVER_USER = os.environ["PUSHOVER_USER"]
CANVAS_TOKEN = os.environ["CANVAS_TOKEN"]
CANVAS_URL = os.environ["CANVAS_URL"].rstrip("/")  # e.g. school.instructure.com
CITY = os.environ.get("CITY", "New York")
DAYS_AHEAD = int(os.environ.get("DAYS_AHEAD", "7"))


# ── Weather ───────────────────────────────────────────────────────────────────

def get_weather():
    try:
        url = f"https://wttr.in/{requests.utils.quote(CITY)}?format=j1"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        current = data["current_condition"][0]
        today = data["weather"][0]

        desc = current["weatherDesc"][0]["value"]
        temp_f = current["temp_F"]
        feels_f = current["FeelsLikeF"]
        humidity = current["humidity"]
        high_f = today["maxtempF"]
        low_f = today["mintempF"]

        return (
            f"🌤 Weather in {CITY}\n"
            f"  {desc}, {temp_f}°F (feels {feels_f}°F)\n"
            f"  High {high_f}°F · Low {low_f}°F · Humidity {humidity}%"
        )
    except Exception as e:
        return f"⚠️ Weather unavailable ({e})"


# ── Canvas assignments ────────────────────────────────────────────────────────

def get_assignments():
    headers = {"Authorization": f"Bearer {CANVAS_TOKEN}"}
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=DAYS_AHEAD)

    # Pull upcoming assignments from the planner
    params = {
        "start_date": now.date().isoformat(),
        "end_date": cutoff.date().isoformat(),
        "per_page": 50,
    }
    url = f"https://{CANVAS_URL}/api/v1/planner/items"

    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        items = r.json()
    except Exception as e:
        return f"⚠️ Canvas unavailable ({e})"

    assignments = []
    for item in items:
        due_raw = item.get("plannable", {}).get("due_at") or item.get("plannable_date")
        if not due_raw:
            continue

        due_dt = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
        days_left = (due_dt.date() - now.date()).days
        title = item.get("plannable", {}).get("title", "Untitled")
        course = item.get("context_name", "")

        if days_left == 0:
            label = "TODAY"
        elif days_left == 1:
            label = "tomorrow"
        else:
            label = f"in {days_left}d"

        assignments.append((days_left, f"  • {title} [{course}] — due {label}"))

    if not assignments:
        return f"📚 No assignments due in the next {DAYS_AHEAD} days."

    assignments.sort(key=lambda x: x[0])
    lines = "\n".join(a[1] for a in assignments)
    return f"📚 Upcoming assignments\n{lines}"


# ── Send via Pushover ─────────────────────────────────────────────────────────

def send_pushover(title, message):
    r = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": PUSHOVER_TOKEN,
            "user": PUSHOVER_USER,
            "title": title,
            "message": message,
            "priority": 0,
        },
        timeout=10,
    )
    r.raise_for_status()
    print("Notification sent.")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    today_str = datetime.now().strftime("%A, %B %-d")
    weather = get_weather()
    assignments = get_assignments()

    body = f"{weather}\n\n{assignments}"
    send_pushover(f"Good morning! {today_str}", body)
    print(body)
