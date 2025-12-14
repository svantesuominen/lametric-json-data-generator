#!/usr/bin/env python3
import os
from flask import Flask, jsonify
from dotenv import load_dotenv
import oura
import digitransit
import fitbit
import transport
import hockey

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
    biked_m = oura.get_cycling_distance_this_year()
    biked_km_int = int(round(biked_m / 1000))
    biked_str = f"{biked_km_int} km"
    
    sleep_data = oura.get_sleep_data() or {}
    sleep_seconds = sleep_data.get("total_sleep_duration", 0)
    sleep_seconds = sleep_data.get("total_sleep_duration", 0)
    s_hours = sleep_seconds // 3600
    s_mins = (sleep_seconds % 3600) // 60
    sleep_time_str = f"{s_hours} h {s_mins} min"
    sleep_score = sleep_data.get("score", 0)
    
    calories_burned = oura.get_activity_calories()
    calories_str = f"{int(round(calories_burned))} kcal"
    
    daily_metrics = oura.get_daily_metrics()
    
    weight_kg_val = fitbit.get_latest_weight()
    # Format: "88,5 kg" (using comma as decimal separator per user request "xy,z")
    weight_str = f"{weight_kg_val:.1f}".replace('.', ',') + " kg"
    
    timetables = transport.get_timetables()
    
    rink_conditions = hockey.get_rink_conditions()

    # TODO: replace remaining placeholder values with real sources (FatSecret, etc.)
    resp = {
        "biked_distance": biked_str,
        "pohjolankatu_alepabikes": counts["pohjolankatu_bikes"],
        "koskelantie_alepabikes": counts["koskelantie_bikes"],
        "steps": daily_metrics["steps"],
        "activity_percentage": daily_metrics["activity_score"],
        "readiness": daily_metrics["readiness_score"],
        "sleep_time": sleep_time_str,
        "sleep_score": sleep_score,
        "calories_intake": 0,  # Placeholder - requires nutrition API
        "calories_consumed": calories_str,
        "weight": weight_str,
        "tram_1_to_eira": timetables["tram_1_to_eira"],
        "bus_66_to_paloheina_ice_rink": timetables["bus_66_to_paloheina_ice_rink"],
        "kapyla_ice": rink_conditions["kapyla_ice"],
        "kapyla_ice_rink": rink_conditions["kapyla_ice_rink"],
        "ogeli_ice": rink_conditions["ogeli_ice"],
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
