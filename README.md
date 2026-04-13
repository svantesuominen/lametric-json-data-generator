# lametric-json-data-generator

A Flask service that aggregates health and activity data from multiple sources for LaMetric display.

## Features

### Data Sources
- **Oura Ring** - Sleep, activity, readiness, cycling, and calorie data
- **Digitransit** - Live Helsinki bike station availability and public transport timetables
- **Fitbit** - Weight tracking
- **Helsinki Service Map** - Real-time ice rink conditions

### Endpoints
- `GET /` - Returns JSON with all metrics
- `GET /lametric` - Returns LaMetric-compatible frame format

### Metrics Provided
| Metric | Source | Description |
|--------|--------|-------------|
| `biked_distance` | Oura | Total cycling distance for current year (e.g. "1234 km") |
| `sleep_time` | Oura | Latest sleep duration (e.g. "7 h 45 min") |
| `sleep_score` | Oura | Latest sleep quality score (0-100) |
| `steps` | Oura | Today's step count |
| `activity_percentage` | Oura | Today's activity score (0-100) |
| `readiness` | Oura | Latest readiness score (0-100) |
| `calories_consumed` | Oura | Total calories burned today (e.g. "2500 kcal") |
| `weight` | Fitbit | Latest weight measurement (e.g. "88,5 kg") |
| `running_distance` | Oura | Running distance YTD (e.g. "42 km") |
| `sleep_debt_est` / `sleep_debt_seconds` | Oura | Heuristic debt from `daily_sleep.sleep_need` vs actual sleep |
| `cardiovascular_age` | Oura | Latest `vascular_age` from Oura (null if unavailable or unauthorized) |
| `avg_hrv_3d` | Oura | Average Heart Rate Variability for the last 3 days |
| `avg_rest_hr_3d` | Oura | Average Resting Heart Rate for the last 3 days |
| `tram_1_to_eira` | Digitransit | Next 3 departures (HH:MM, ...) for Tram 1 |
| `bus_66_to_paloheina_ice_rink` | Digitransit | Next 3 departures (HH:MM, ...) for Bus 66 |
| `calories_intake` | Placeholder | Food calories (requires nutrition API) |
| `pohjolankatu_alepabikes` | Digitransit | Available bikes at Pohjolankatu station |
| `koskelantie_alepabikes` | Digitransit | Available bikes at Koskelantie station |
| `kapyla_ice` | Service Map | Condition of Käpylä artificial ice rink |
| `kapyla_ice_rink` | Service Map | Condition of Käpylä ice hockey rink |
| `ogeli_ice` | Service Map | Condition of Oulunkylä artificial ice rink |

## Setup

### 1. Clone and Install
```bash
git clone <repo-url>
cd lametric-json-data-generator
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` using [`.env.example`](.env.example) as a template. You need **all** variables your integrations use; Fitbit weight refresh requires **four** Fitbit OAuth variables (access + refresh + client id + secret).

### 3. Run
```bash
python app.py
```

Server runs on `http://localhost:8000`

## API Keys

### Digitransit API
1. Register at [Digitransit Developer Portal](https://portal-api.digitransit.fi/)
2. Create an API key
3. Add to `.env` as `DIGITRANSIT_KEY`

### Oura API (OAuth2)
Personal Access Tokens are deprecated for new integrations. Use an [Oura OAuth application](https://cloud.ouraring.com/oauth/applications).

1. Create an app and note **Client ID** and **Client Secret**.
2. Authorize with a **space-separated scope** list that includes at least:
   - **`daily`** — sleep, readiness, daily summaries, **cardiovascular age**, sleep debt heuristic (`daily_sleep`), etc.
   - **`workout`** — cycling and running distance from workouts.
3. Exchange the authorization code for **`access_token`** and **`refresh_token`** and add to `.env` (`OURA_ACCESS_TOKEN`, `OURA_REFRESH_TOKEN`, plus client id/secret).

If logs show **HTTP 401 on `daily_cardiovascular_age` even after a successful token refresh**, the access token is valid but **not allowed** to read that resource: re-authorize and ensure the **`daily`** scope is granted, confirm your ring/tier supports Cardiovascular Age in the Oura app, and check membership status. The API response body is printed to logs for detail.

### Fitbit API
1. Register your app at [Fitbit Developer Console](https://dev.fitbit.com/apps)
   - Set "Redirect URL" to `http://localhost:8080`
2. Run the helper script to authenticate:
   ```bash
   python3 auth_fitbit.py
   ```
3. Ensure `.env` contains **`FITBIT_ACCESS_TOKEN`**, **`FITBIT_REFRESH_TOKEN`**, **`FITBIT_CLIENT_ID`**, and **`FITBIT_CLIENT_SECRET`**. Without the client id, secret, and refresh token, **token refresh fails** and weight falls back to `"0,0 kg"` when the access token expires.

### Deploying on Render (or similar hosts)
1. In the service **Environment** tab, set **every** variable from [`.env.example`](.env.example) that you use locally. Common production gaps: missing **`FITBIT_CLIENT_ID`**, **`FITBIT_CLIENT_SECRET`**, **`FITBIT_REFRESH_TOKEN`**, or Oura **`daily`** scope after re-auth.
2. **Token refresh persistence:** `save_token` in this app updates `os.environ` and writes `.env` on disk. On Render the filesystem is ephemeral and **dashboard env vars are not updated** by the app. Refreshed tokens apply to **that process only**. With **multiple Gunicorn workers**, workers that did not refresh may still use the old access token until you **redeploy** or **paste new tokens into the dashboard**. Prefer **`gunicorn -w 1`** (single worker) unless you use external token storage.
3. Cold starts and many upstream API calls can make **`GET /`** slow; use health checks with a generous timeout or hit `/` once to wake the service.

## Project Structure
```
├── app.py              # Flask application and routes
├── oura.py             # Oura API integration
├── digitransit.py      # Digitransit bike stations
├── transport.py        # Public transport timetables
├── fitbit.py           # Fitbit API integration
├── hockey.py           # Ice rink conditions (Service Map API)
├── requirements.txt    # Python dependencies
└── .env               # Environment variables (not in git)
```

## Example Response
```json
{
  "activity_percentage": 77,
  "biked_distance": "1234 km",
  "bus_66_to_paloheina_ice_rink": "15:45, 16:01, 16:24",
  "calories_consumed": "2753 kcal",
  "calories_intake": 0,
  "koskelantie_alepabikes": 0,
  "pohjolankatu_alepabikes": 0,
  "readiness": 81,
  "sleep_score": 80,
  "sleep_time": "7 h 48 min",
  "steps": 6493,
  "tram_1_to_eira": "15:42, 16:51, 16:00",
  "weight": "88,5 kg",
  "kapyla_ice": "Closed",
  "kapyla_ice_rink": "Closed",
  "ogeli_ice": "Ice-covered"
}
```

