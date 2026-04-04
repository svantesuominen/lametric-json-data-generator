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
        print(f"Error fetching bike counts: {e}")
        counts = {"pohjolankatu_bikes": 0, "koskelantie_bikes": 0}

    # Fetch Oura data
    biked_m = oura.get_cycling_distance_this_year()
    biked_km_int = int(round(biked_m / 1000))
    biked_str = f"{biked_km_int} km"
    
    sleep_data = oura.get_sleep_data() or {}
    sleep_seconds = sleep_data.get("total_sleep_duration", 0)
    s_hours = sleep_seconds // 3600
    s_mins = (sleep_seconds % 3600) // 60
    sleep_time_str = f"{s_hours} h {s_mins} min"
    sleep_score = sleep_data.get("score", 0)
    
    calories_burned = oura.get_activity_calories()
    calories_str = f"{int(round(calories_burned))} kcal"
    
    daily_metrics = oura.get_daily_metrics()
    avg_metrics = oura.get_avg_hrv_heartrate(3)
    
    weight_kg_val = fitbit.get_latest_weight()
    # Format: "88,5 kg" (using comma as decimal separator per user request "xy,z")
    weight_str = f"{weight_kg_val:.1f}".replace('.', ',') + " kg"
    
    try:
        timetables = transport.get_timetables()
    except Exception as e:
        print(f"Error fetching timetables: {e}")
        timetables = {"tram_1_to_eira": "N/A", "bus_66_to_paloheina_ice_rink": "N/A"}
        
    try:
        rink_conditions = hockey.get_rink_conditions()
    except Exception as e:
        print(f"Error fetching hockey info: {e}")
        rink_conditions = {"kapyla_ice": "N/A", "kapyla_ice_rink": "N/A", "ogeli_ice": "N/A"}

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
        "avg_hrv_3d": avg_metrics["avg_hrv"],
        "avg_rest_hr_3d": avg_metrics["avg_heart_rate"],
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
    # 1. Fetch Bike Data
    try:
        counts = digitransit.fetch_bike_counts()
    except Exception as e:
        print(f"Error fetching bike counts: {e}")
        counts = {"pohjolankatu_bikes": 0, "koskelantie_bikes": 0}

    # 2. Fetch Oura Data
    try:
        daily_metrics = oura.get_daily_metrics()
        sleep_data = oura.get_sleep_data() or {}
        biked_m = oura.get_cycling_distance_this_year()
        calories_burned = oura.get_activity_calories()
        avg_metrics = oura.get_avg_hrv_heartrate(3)
    except Exception as e:
        print(f"Error fetching Oura data: {e}")
        daily_metrics = {"steps": 0, "readiness_score": 0}
        sleep_data = {}
        biked_m = 0
        calories_burned = 0
        avg_metrics = {"avg_hrv": 0, "avg_heart_rate": 0}

    # 3. Fetch Fitbit Data
    try:
        weight_kg = fitbit.get_latest_weight()
    except Exception as e:
        print(f"Error fetching Fitbit data: {e}")
        weight_kg = 0

    # Format values
    biked_km = int(round(biked_m / 1000))
    sleep_seconds = sleep_data.get("total_sleep_duration", 0)
    s_hours = sleep_seconds // 3600
    s_mins = (sleep_seconds % 3600) // 60
    weight_str = f"{weight_kg:.1f}".replace('.', ',')

    frames = [
        # Health & Activity
        {"text": f"{daily_metrics['steps']} steps", "icon": "i49"},
        {"text": f"{daily_metrics['readiness_score']} readiness", "icon": "i29"},
        {"text": f"{s_hours}h {s_mins}m sleep", "icon": "i90"},
        {"text": f"{int(round(calories_burned))} kcal", "icon": "i25"},
        {"text": f"{biked_km} km cycled", "icon": "i1234"},
        {"text": f"{weight_str} kg", "icon": "i2110"},
        {"text": f"{avg_metrics['avg_hrv']} hrv (3d)", "icon": "i52"},
        {"text": f"{avg_metrics['avg_heart_rate']} bpm (3d)", "icon": "i31"},
        
        # Bike Stations
        {"text": f"Pohjola: {counts['pohjolankatu_bikes']} 🚲", "icon": "i1234"},
        {"text": f"Koskela: {counts['koskelantie_bikes']} 🚲", "icon": "i1234"},
    ]
    return jsonify({"frames": frames})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
