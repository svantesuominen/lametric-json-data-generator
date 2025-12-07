
import os
import requests
import datetime

# Documentation: https://cloud.ouraring.com/docs/
OURA_API_URL = "https://api.ouraring.com/v2/usercollection"

def get_oura_headers():
    token = os.getenv("OURA_ACCESS_TOKEN", "").strip()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}"
    }

def get_sleep_data():
    """
    Fetch the most recent daily sleep document.
    Returns a dict with 'total_sleep_duration' (seconds) and 'score' (0-100), or None if failed.
    """
    headers = get_oura_headers()
    if not headers:
        return None

    # Get sleep documents for the last few days to ensure we have the latest
    # (Adjust start_date as needed, e.g. last 7 days)
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    
    params = {
        "start_date": last_week.isoformat(), 
        "end_date": today.isoformat()
    }
    
    try:
        # Fetch sleep sessions for duration
        url_sleep = f"{OURA_API_URL}/sleep"
        r_sleep = requests.get(url_sleep, headers=headers, params=params, timeout=10)
        r_sleep.raise_for_status()
        sleep_data = r_sleep.json()
        
        # Fetch daily sleep for score
        url_daily = f"{OURA_API_URL}/daily_sleep"
        r_daily = requests.get(url_daily, headers=headers, params=params, timeout=10)
        r_daily.raise_for_status()
        daily_data = r_daily.json()
        
        # Get latest sleep session for duration
        sleep_docs = sleep_data.get("data", [])
        daily_docs = daily_data.get("data", [])
        
        if not sleep_docs:
            return None
            
        latest_sleep = sorted(sleep_docs, key=lambda x: x.get("day", ""), reverse=True)[0]
        
        # Try to find matching daily sleep for score
        sleep_day = latest_sleep.get("day")
        score = 0
        for daily in daily_docs:
            if daily.get("day") == sleep_day:
                score = daily.get("score", 0)
                break
        
        result = {
            "total_sleep_duration": latest_sleep.get("total_sleep_duration", 0),
            "score": score,
            "day": sleep_day
        }
        return result
        
    except Exception as e:
        print(f"Error fetching Oura sleep data: {e}")
        return None

def get_cycling_distance_this_year():
    """
    Sum distance for 'cycling' workouts for the current year.
    Returns total distance in meters.
    """
    headers = get_oura_headers()
    if not headers:
        return 0.0

    today = datetime.date.today()
    start_of_year = datetime.date(today.year, 1, 1)
    
    params = {
        "start_date": start_of_year.isoformat(),
        "end_date": today.isoformat()
    }
    
    try:
        url = f"{OURA_API_URL}/workout"
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        workout_data = r.json()
        
        total_distance = 0.0
        for w in workout_data.get("data", []):
            # Check workout type
            if w.get("activity") == "cycling":
                distance = w.get("distance")
                if distance is not None:
                    total_distance += float(distance)
                
        return total_distance

    except Exception as e:
        print(f"Error fetching Oura workout data: {e}")
        return 0.0

def get_activity_calories():
    """
    Fetch the most recent daily activity calories.
    Returns total_calories (active + resting) from the latest daily activity data.
    """
    headers = get_oura_headers()
    if not headers:
        return 0

    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    
    params = {
        "start_date": last_week.isoformat(),
        "end_date": today.isoformat()
    }
    
    try:
        url = f"{OURA_API_URL}/daily_activity"
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        # Get latest activity document
        docs = data.get("data", [])
        if not docs:
            return 0
            
        latest = sorted(docs, key=lambda x: x.get("day", ""), reverse=True)[0]
        
        # total_calories includes both active and resting calories
        return latest.get("total_calories", 0)
        
    except Exception as e:
        print(f"Error fetching Oura activity data: {e}")
        return 0

def get_daily_metrics():
    """
    Fetch the most recent daily readiness and activity metrics.
    Returns dict with 'readiness_score', 'steps', and 'activity_score'.
    """
    headers = get_oura_headers()
    if not headers:
        return {"readiness_score": 0, "steps": 0, "activity_score": 0}

    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    
    params = {
        "start_date": last_week.isoformat(),
        "end_date": today.isoformat()
    }
    
    result = {"readiness_score": 0, "steps": 0, "activity_score": 0}
    
    try:
        # Fetch readiness
        url_readiness = f"{OURA_API_URL}/daily_readiness"
        r_readiness = requests.get(url_readiness, headers=headers, params=params, timeout=10)
        r_readiness.raise_for_status()
        readiness_data = r_readiness.json()
        
        readiness_docs = readiness_data.get("data", [])
        if readiness_docs:
            latest_readiness = sorted(readiness_docs, key=lambda x: x.get("day", ""), reverse=True)[0]
            result["readiness_score"] = latest_readiness.get("score", 0)
        
        # Fetch activity for steps - look for today's data specifically
        url_activity = f"{OURA_API_URL}/daily_activity"
        r_activity = requests.get(url_activity, headers=headers, params=params, timeout=10)
        r_activity.raise_for_status()
        activity_data = r_activity.json()
        
        activity_docs = activity_data.get("data", [])
        if activity_docs:
            # Try to find today's data first
            today_str = today.isoformat()
            today_activity = None
            for doc in activity_docs:
                if doc.get("day") == today_str:
                    today_activity = doc
                    break
            
            # If today's data exists, use it; otherwise fall back to latest
            if today_activity:
                result["steps"] = today_activity.get("steps", 0)
                result["activity_score"] = today_activity.get("score", 0)
            else:
                latest_activity = sorted(activity_docs, key=lambda x: x.get("day", ""), reverse=True)[0]
                result["steps"] = latest_activity.get("steps", 0)
                result["activity_score"] = latest_activity.get("score", 0)
        
        return result
        
    except Exception as e:
        print(f"Error fetching Oura daily metrics: {e}")
        return result



