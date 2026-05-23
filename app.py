#!/usr/bin/env python3
import os
import time
import threading
from flask import Flask, jsonify
from dotenv import load_dotenv
import oura
import digitransit
import fitbit
import transport
import hockey

load_dotenv()

app = Flask(__name__)

_BACKGROUND_REFRESH_INTERVAL = 4 * 3600  # check every 4 hours


def _background_token_refresh():
    """Periodically refresh tokens that are close to expiry."""
    while True:
        time.sleep(_BACKGROUND_REFRESH_INTERVAL)
        try:
            if oura._token_needs_refresh():
                print("[bg-refresh] Oura token expiring soon, refreshing...")
                oura.refresh_oura_token()
            if fitbit._token_needs_refresh():
                print("[bg-refresh] Fitbit token expiring soon, refreshing...")
                fitbit.refresh_fitbit_token()
        except Exception as e:
            print(f"[bg-refresh] Error: {e}")


def _format_sleep_debt_seconds(sec):
    h = int(sec) // 3600
    m = (int(sec) % 3600) // 60
    if h:
        return f"{h} h {m} min"
    return f"{m} min"


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

    ran_m = oura.get_running_distance_this_year()
    ran_km_int = int(round(ran_m / 1000))
    ran_str = f"{ran_km_int} km"

    debt_info = oura.get_sleep_debt_heuristic()
    sleep_debt_est_str = _format_sleep_debt_seconds(debt_info["debt_seconds"])
    cardiovascular_age = oura.get_latest_cardiovascular_age()

    sleep_data = oura.get_sleep_data() or {}
    sleep_seconds = sleep_data.get("total_sleep_duration", 0)
    s_hours = sleep_seconds // 3600
    s_mins = (sleep_seconds % 3600) // 60
    sleep_time_str = f"{s_hours} h {s_mins} min"
    sleep_score = sleep_data.get("score", 0)
    
    calories_burned = oura.get_activity_calories()
    calories_str = f"{int(round(calories_burned))} kcal"
    
    daily_metrics = oura.get_daily_metrics()
    avg_metrics = oura.get_avg_hrv_heartrate()
    workout_counts = oura.get_workout_counts_this_year()
    
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
        "running_distance": ran_str,
        "sleep_debt_est": sleep_debt_est_str,
        "sleep_debt_seconds": debt_info["debt_seconds"],
        "cardiovascular_age": cardiovascular_age,
        "pohjolankatu_alepabikes": counts["pohjolankatu_bikes"],
        "koskelantie_alepabikes": counts["koskelantie_bikes"],
        "steps": daily_metrics["steps"],
        "activity_percentage": daily_metrics["activity_score"],
        "readiness": daily_metrics["readiness_score"],
        "sleep_time": sleep_time_str,
        "sleep_score": sleep_score,
        "avg_hrv_3d": f"{avg_metrics['avg_hrv_3d']} ({avg_metrics['avg_hrv_7d']})",
        "avg_rest_hr_3d": f"{avg_metrics['avg_hr_3d']} ({avg_metrics['avg_hr_7d']})",
        "calories_intake": 0,  # Placeholder - requires nutrition API
        "calories_consumed": calories_str,
        "weight": weight_str,
        "tram_1_to_eira": timetables["tram_1_to_eira"],
        "bus_66_to_paloheina_ice_rink": timetables["bus_66_to_paloheina_ice_rink"],
        "kapyla_ice": rink_conditions["kapyla_ice"],
        "kapyla_ice_rink": rink_conditions["kapyla_ice_rink"],
        "ogeli_ice": rink_conditions["ogeli_ice"],
        "workouts_qty": workout_counts,
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
        ran_m = oura.get_running_distance_this_year()
        debt_info = oura.get_sleep_debt_heuristic()
        cv_age = oura.get_latest_cardiovascular_age()
        calories_burned = oura.get_activity_calories()
        avg_metrics = oura.get_avg_hrv_heartrate()
    except Exception as e:
        print(f"Error fetching Oura data: {e}")
        daily_metrics = {"steps": 0, "readiness_score": 0}
        sleep_data = {}
        biked_m = 0
        ran_m = 0
        debt_info = {"debt_seconds": 0}
        cv_age = None
        calories_burned = 0
        avg_metrics = {"avg_hrv_3d": 0, "avg_hrv_7d": 0, "avg_hr_3d": 0, "avg_hr_7d": 0}

    # 3. Fetch Fitbit Data
    try:
        weight_kg = fitbit.get_latest_weight()
    except Exception as e:
        print(f"Error fetching Fitbit data: {e}")
        weight_kg = 0

    # Format values
    biked_km = int(round(biked_m / 1000))
    ran_km = int(round(ran_m / 1000))
    dsec = debt_info["debt_seconds"]
    dh = dsec // 3600
    dm = (dsec % 3600) // 60
    sleep_seconds = sleep_data.get("total_sleep_duration", 0)
    s_hours = sleep_seconds // 3600
    s_mins = (sleep_seconds % 3600) // 60
    weight_str = f"{weight_kg:.1f}".replace('.', ',')
    cv_text = f"CV {cv_age}" if cv_age is not None else "CV n/a"

    frames = [
        # Health & Activity
        {"text": f"{daily_metrics['steps']} steps", "icon": "i49"},
        {"text": f"{daily_metrics['readiness_score']} readiness", "icon": "i29"},
        {"text": f"{s_hours}h {s_mins}m sleep", "icon": "i90"},
        {"text": f"{dh}h {dm}m debt est", "icon": "i90"},
        {"text": f"{int(round(calories_burned))} kcal", "icon": "i25"},
        {"text": f"{biked_km} km cycled", "icon": "i1234"},
        {"text": f"{ran_km} km run", "icon": "i1234"},
        {"text": cv_text, "icon": "i52"},
        {"text": f"{weight_str} kg", "icon": "i2110"},
        {"text": f"{avg_metrics['avg_hrv_3d']} ({avg_metrics['avg_hrv_7d']}) hrv", "icon": "i52"},
        {"text": f"{avg_metrics['avg_hr_3d']} ({avg_metrics['avg_hr_7d']}) bpm", "icon": "i31"},
        
        # Bike Stations
        {"text": f"Pohjola: {counts['pohjolankatu_bikes']} 🚲", "icon": "i1234"},
        {"text": f"Koskela: {counts['koskelantie_bikes']} 🚲", "icon": "i1234"},
    ]
    return jsonify({"frames": frames})

@app.route("/health")
def health():
    """Token status and readiness check."""
    now = int(time.time())

    def _token_status(name, token_env, expires_env):
        token = (os.getenv(token_env) or "").strip()
        expires_at = os.getenv(expires_env, "").strip()
        if not token:
            return {"status": "missing"}
        if not expires_at:
            return {"status": "ok", "expires": "unknown (no expiry tracked yet)"}
        try:
            exp = int(expires_at)
            remaining = exp - now
            if remaining <= 0:
                return {"status": "expired", "expired_ago_seconds": -remaining}
            return {"status": "ok", "expires_in_seconds": remaining,
                    "expires_in_hours": round(remaining / 3600, 1)}
        except ValueError:
            return {"status": "ok", "expires": "unparseable"}

    return jsonify({
        "oura": _token_status("oura", "OURA_ACCESS_TOKEN", "OURA_TOKEN_EXPIRES_AT"),
        "fitbit": _token_status("fitbit", "FITBIT_ACCESS_TOKEN", "FITBIT_TOKEN_EXPIRES_AT"),
    })


if __name__ == "__main__":
    t = threading.Thread(target=_background_token_refresh, daemon=True)
    t.start()
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
