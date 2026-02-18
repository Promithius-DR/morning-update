import os
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

PUSHOVER_TOKEN = os.environ["PUSHOVER_TOKEN"]
PUSHOVER_USER = os.environ["PUSHOVER_USER"]
CANVAS_TOKEN = os.environ["CANVAS_TOKEN"]
CANVAS_URL = os.environ["CANVAS_URL"].rstrip("/")  # e.g. school.instructure.com
CITY = os.environ.get("CITY", "New York")
DAYS_AHEAD = int(os.environ.get("DAYS_AHEAD", "7"))


# ── Weather ───────────────────────────────────────────────────────────────────

# WMO Weather interpretation codes → human-readable description
_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ heavy hail",
}


def _fetch(url, **kwargs):
    """GET with 3 attempts and a 10-second timeout."""
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=10, **kwargs)
            r.raise_for_status()
            return r
        except requests.exceptions.Timeout:
            if attempt == 2:
                raise
    return r  # unreachable, but satisfies linters


def get_weather():
    try:
        # Step 1: geocode city name → lat/lon
        geo = _fetch(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": CITY, "count": 1, "language": "en", "format": "json"},
        ).json()
        if not geo.get("results"):
            return f"⚠️ Weather unavailable (city not found: {CITY})"
        result = geo["results"][0]
        lat, lon = result["latitude"], result["longitude"]

        # Step 2: fetch current conditions + today's high/low
        wx = _fetch(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min",
                "temperature_unit": "fahrenheit",
                "timezone": "auto",
                "forecast_days": 1,
            },
        ).json()

        cur = wx["current"]
        daily = wx["daily"]
        desc = _WMO_CODES.get(cur["weather_code"], f"Code {cur['weather_code']}")
        temp_f = round(cur["temperature_2m"])
        feels_f = round(cur["apparent_temperature"])
        humidity = cur["relative_humidity_2m"]
        high_f = round(daily["temperature_2m_max"][0])
        low_f = round(daily["temperature_2m_min"][0])

        return (
            f"🌤 <b>{CITY}</b> — {desc}, {temp_f}°F (feels {feels_f}°F)\n"
            f"High {high_f}° · Low {low_f}° · Humidity {humidity}%"
        )
    except Exception as e:
        return f"⚠️ Weather unavailable ({e})"


# ── Canvas assignments ────────────────────────────────────────────────────────

def get_assignments():
    headers = {"Authorization": f"Bearer {CANVAS_TOKEN}"}
    central = ZoneInfo("America/Chicago")
    now = datetime.now(central)
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

        due_dt = datetime.fromisoformat(due_raw.replace("Z", "+00:00")).astimezone(central)
        days_left = (due_dt.date() - now.date()).days
        title = item.get("plannable", {}).get("title", "Untitled")
        course = item.get("context_name", "")

        # Strip instructor surname from course name (e.g. "Adult Health II-Mondragon")
        parts = course.rsplit("-", 1)
        short_course = parts[0].strip() if len(parts) == 2 and " " not in parts[1].strip() else course

        if days_left == 0:
            label = "<b>TODAY</b>"
        elif days_left == 1:
            label = "<b>tomorrow</b>"
        else:
            label = f"in {days_left}d"

        assignments.append((days_left, f"• {label} — {title}\n  <i>{short_course}</i>"))

    if not assignments:
        return f"📚 No assignments due in the next {DAYS_AHEAD} days."

    assignments.sort(key=lambda x: x[0])
    lines = "\n".join(a[1] for a in assignments)
    return f"📚 <b>Upcoming assignments</b>\n{lines}"


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
            "html": 1,
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
