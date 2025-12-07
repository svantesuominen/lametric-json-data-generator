#!/usr/bin/env python3
import os
from flask import Flask, jsonify
from dotenv import load_dotenv
import oura
import digitransit

load_dotenv()

app = Flask(__name__)

# --- 1) Your custom JSON shape (for your broader dashboard needs) ---
@app.route("/")
def root_custom_json():
    try:
        counts = digitransit.fetch_bike_counts()
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    # Fetch Oura data
    biked_m = oura.get_cycling_distance_this_year()
    biked_km = round(biked_m / 1000, 1)
    
    sleep_data = oura.get_sleep_data() or {}
    sleep_seconds = sleep_data.get("total_sleep_duration", 0)
    sleep_hours = round(sleep_seconds / 3600, 2)
    sleep_score = sleep_data.get("score", 0)
    
    calories_burned = oura.get_activity_calories()
    
    daily_metrics = oura.get_daily_metrics()

    # TODO: replace remaining placeholder values with real sources (FatSecret, etc.)
    resp = {
        "biked_km": biked_km,
        "pohjolankatu_alepabikes": counts["pohjolankatu_bikes"],
        "koskelantie_alepabikes": counts["koskelantie_bikes"],
        "steps": daily_metrics["steps"],
        "activity_percentage": daily_metrics["activity_score"],
        "readiness": daily_metrics["readiness_score"],
        "sleep_time": sleep_hours,
        "sleep_score": sleep_score,
        "calories_intake": 2232,  # Placeholder - requires nutrition API
        "calories_consumed": calories_burned,
    }
    return jsonify(resp)

# --- 2) Optional LaMetric-native format (handy if you also want direct My Data DIY) ---
@app.route("/lametric")
def lametric_frames():
    try:
        counts = digitransit.fetch_bike_counts()
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
