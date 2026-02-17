# Morning Update

Sends a daily Pushover push notification with:
- Today's weather (via wttr.in — no API key needed)
- Canvas LMS assignments due in the next 7 days

Runs automatically every morning via GitHub Actions.

## Setup

### 1. Pushover
1. Create an account at [pushover.net](https://pushover.net) and install the app ($5 one-time)
2. Note your **User Key** from the dashboard
3. Create a new **Application** → note the **API Token**

### 2. Canvas API Token
1. Log into Canvas → Account → Settings
2. Scroll to **Approved Integrations** → **New Access Token**
3. Give it a name (e.g. "Morning Update") and copy the token

### 3. GitHub Secrets
In your GitHub repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret name      | Value                                      |
|------------------|--------------------------------------------|
| `PUSHOVER_TOKEN` | Your Pushover app API token                |
| `PUSHOVER_USER`  | Your Pushover user key                     |
| `CANVAS_TOKEN`   | Your Canvas access token                   |
| `CANVAS_URL`     | Your school's Canvas domain (e.g. `school.instructure.com`) |
| `CITY`           | Your city name for weather (e.g. `Nashville, TN`) |

### 4. Schedule
Edit `.github/workflows/morning_update.yml` to adjust the cron time:
```
"0 12 * * *"  →  12:00 UTC = 7:00 AM Eastern
"0 13 * * *"  →  13:00 UTC = 8:00 AM Eastern
```

You can also trigger it manually from the **Actions** tab in GitHub.

## Local Testing
```bash
pip install -r requirements.txt
export PUSHOVER_TOKEN=...
export PUSHOVER_USER=...
export CANVAS_TOKEN=...
export CANVAS_URL=school.instructure.com
export CITY="Nashville, TN"
python daily_update.py
```
