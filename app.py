#!/usr/bin/env python3
import os
import requests
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DIGITRANSIT_KEY", "").strip()
GRAPHQL_URL = "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1"

# Query two stations: Pohjolankatu (145) and Koskelantie (142)
QUERY = '''
{
  pohjolankatu: vehicleRentalStation(id: "smoove:145") {
    name
    availableVehicles { byType { count vehicleType { formFactor } } }
  }
  koskelantie: vehicleRentalStation(id: "smoove:142") {
    name
    availableVehicles { byType { count vehicleType { formFactor } } }
  }
}
'''

def sum_bicycles(section: dict) -> int:
    """Sum counts for BICYCLE formFactor from the 'byType' array."""
    total = 0
    for item in (section or {}).get("byType", []):
        vt = (item.get("vehicleType") or {}).get("formFactor")
        if vt == "BICYCLE":
            total += int(item.get("count") or 0)
    return total

def fetch_bike_counts() -> dict:
    """Fetch bike counts for the two stations; return dict with names and counts."""
    if not API_KEY:
        raise RuntimeError("Missing DIGITRANSIT_KEY in environment/.env")

    headers = {
        "Content-Type": "application/json",
        "digitransit-subscription-key": API_KEY,
    }
    r = requests.post(GRAPHQL_URL, headers=headers, json={"query": QUERY}, timeout=20)
    if r.status_code == 401:
        raise RuntimeError("Digitransit 401 Unauthorized – check DIGITRANSIT_KEY")
    r.raise_for_status()

    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL error: {payload['errors']}")

    data = payload.get("data", {})
    poh = data.get("pohjolankatu") or {}
    kos = data.get("koskelantie") or {}

    return {
        "pohjolankatu_name": poh.get("name", "Pohjolankatu"),
        "pohjolankatu_bikes": sum_bicycles((poh or {}).get("availableVehicles", {})),
        "koskelantie_name": kos.get("name", "Koskelantie"),
        "koskelantie_bikes": sum_bicycles((kos or {}).get("availableVehicles", {})),
    }

app = Flask(__name__)

# --- 1) Your custom JSON shape (for your broader dashboard needs) ---
@app.route("/")
def root_custom_json():
    try:
        counts = fetch_bike_counts()
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    # TODO: replace these placeholder values with real sources (Oura, FatSecret, etc.)
    resp = {
        "biked_km": 6.3,
        "pohjolankatu_alepabikes": counts["pohjolankatu_bikes"],
        "koskelantie_alepabikes": counts["koskelantie_bikes"],
        "steps": 7421,
        "activity_percentage": 91,
        "readiness": 83,
        "sleep_time": 7.42,
        "sleep_score": 79,
        "calories_intake": 2232,
        "calories_consumed": 2532,
    }
    return jsonify(resp)

# --- 2) Optional LaMetric-native format (handy if you also want direct My Data DIY) ---
@app.route("/lametric")
def lametric_frames():
    try:
        counts = fetch_bike_counts()
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    frames = [
        {"text": f"{counts['pohjolankatu_name']}: {counts['pohjolankatu_bikes']} 🚲", "icon": "i1234"},
        {"text": f"{counts['koskelantie_name']}: {counts['koskelantie_bikes']} 🚲", "icon": "i1234"},
    ]
    return jsonify({"frames": frames})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
