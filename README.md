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
| `weight` | Fitbit | Latest weight measurement (kg) |
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

Edit `.env` and add your API keys:
```
DIGITRANSIT_KEY=your_digitransit_api_key
OURA_ACCESS_TOKEN=your_oura_personal_access_token
FITBIT_ACCESS_TOKEN=your_fitbit_access_token
```

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

### Oura API
1. Go to [Oura Cloud](https://cloud.ouraring.com/personal-access-tokens)
2. Generate a Personal Access Token
3. Add to `.env` as `OURA_ACCESS_TOKEN`

### Fitbit API
1. Register your app at [Fitbit Developer Console](https://dev.fitbit.com/apps)
2. Use OAuth 2.0 flow to get an access token (see [Fitbit OAuth docs](https://dev.fitbit.com/build/reference/web-api/oauth2/))
3. Add to `.env` as `FITBIT_ACCESS_TOKEN`
4. Note: Access tokens expire after 8 hours

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
  "weight": 88.0,
  "kapyla_ice": "Closed",
  "kapyla_ice_rink": "Closed",
  "ogeli_ice": "Ice-covered"
}
```

