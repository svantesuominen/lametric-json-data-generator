
import os
import requests
import datetime
from dotenv import load_dotenv, set_key

# Load environment variables
load_dotenv()

# Documentation: https://cloud.ouraring.com/docs/
OURA_API_URL = "https://api.ouraring.com/v2/usercollection"
ENV_PATH = ".env"

def save_token(access_token, refresh_token):
    """Save new tokens to environment and .env file."""
    os.environ["OURA_ACCESS_TOKEN"] = access_token
    os.environ["OURA_REFRESH_TOKEN"] = refresh_token
    
    # Persist to .env
    set_key(ENV_PATH, "OURA_ACCESS_TOKEN", access_token)
    set_key(ENV_PATH, "OURA_REFRESH_TOKEN", refresh_token)

def refresh_oura_token():
    """Refresh the Oura access token using the refresh token."""
    client_id = os.getenv("OURA_CLIENT_ID")
    client_secret = os.getenv("OURA_CLIENT_SECRET")
    refresh_token = os.getenv("OURA_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        print("Missing Oura credentials (CLIENT_ID, CLIENT_SECRET, or REFRESH_TOKEN). Cannot refresh.")
        return False
        
    token_url = "https://api.ouraring.com/oauth/token"
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        r = requests.post(token_url, data=data, timeout=10)
        r.raise_for_status()
        tokens = r.json()
        
        new_access = tokens.get("access_token")
        new_refresh = tokens.get("refresh_token")
        
        if new_access and new_refresh:
            save_token(new_access, new_refresh)
            print("Successfully refreshed Oura token.")
            return True
    except Exception as e:
        print(f"Failed to refresh Oura token: {e}")
        try:
            if r.text:
                print(f"Response: {r.text}")
        except:
            pass
            
    return False

def get_oura_headers():
    token = os.getenv("OURA_ACCESS_TOKEN", "").strip()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}"
    }

def make_request(url, params=None):
    """Make a GET request with auto-refresh logic."""
    headers = get_oura_headers()
    if not headers:
        return None
        
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        
        # If unauthorized, try to refresh and retry
        if r.status_code == 401:
            print("Oura token expired (401), attempting refresh...")
            if refresh_oura_token():
                # Update headers with new token
                headers = get_oura_headers()
                r = requests.get(url, headers=headers, params=params, timeout=10)
            else:
                print("Token refresh failed or not possible.")
                return None
                
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error making Oura request: {e}")
        return None

def get_sleep_data():
    """
    Fetch the most recent daily sleep document.
    Returns a dict with 'total_sleep_duration' (seconds) and 'score' (0-100), or None if failed.
    """
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    
    params = {
        "start_date": last_week.isoformat(), 
        "end_date": today.isoformat()
    }
    
    # Fetch sleep sessions for duration
    url_sleep = f"{OURA_API_URL}/sleep"
    sleep_data = make_request(url_sleep, params=params)
    if not sleep_data:
        return None
        
    # Fetch daily sleep for score
    url_daily = f"{OURA_API_URL}/daily_sleep"
    daily_data = make_request(url_daily, params=params)
    if not daily_data:
        # If sleep_data exists but daily_data fails, we can still return partial but let's be strict
        return None
    
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

def get_cycling_distance_this_year():
    """
    Sum distance for 'cycling' workouts for the current year.
    Returns total distance in meters.
    """
    today = datetime.date.today()
    start_of_year = datetime.date(today.year, 1, 1)
    
    params = {
        "start_date": start_of_year.isoformat(),
        "end_date": today.isoformat()
    }
    
    url = f"{OURA_API_URL}/workout"
    workout_data = make_request(url, params=params)
    if not workout_data:
        return 0.0
    
    total_distance = 0.0
    for w in workout_data.get("data", []):
        # Check workout type
        if w.get("activity") == "cycling":
            distance = w.get("distance")
            if distance is not None:
                total_distance += float(distance)
            
    return total_distance

def get_activity_calories():
    """
    Fetch the most recent daily activity calories.
    Returns total_calories (active + resting) from the latest daily activity data.
    """
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    
    params = {
        "start_date": last_week.isoformat(),
        "end_date": today.isoformat()
    }
    
    url = f"{OURA_API_URL}/daily_activity"
    data = make_request(url, params=params)
    if not data:
        return 0
    
    # Get latest activity document
    docs = data.get("data", [])
    if not docs:
        return 0
        
    latest = sorted(docs, key=lambda x: x.get("day", ""), reverse=True)[0]
    
    # total_calories includes both active and resting calories
    return latest.get("total_calories", 0)

def get_daily_metrics():
    """
    Fetch the most recent daily readiness and activity metrics.
    Returns dict with 'readiness_score', 'steps', and 'activity_score'.
    """
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    
    params = {
        "start_date": last_week.isoformat(),
        "end_date": today.isoformat()
    }
    
    result = {"readiness_score": 0, "steps": 0, "activity_score": 0}
    
    # Fetch readiness
    url_readiness = f"{OURA_API_URL}/daily_readiness"
    readiness_data = make_request(url_readiness, params=params)
    
    if readiness_data:
        readiness_docs = readiness_data.get("data", [])
        if readiness_docs:
            latest_readiness = sorted(readiness_docs, key=lambda x: x.get("day", ""), reverse=True)[0]
            result["readiness_score"] = latest_readiness.get("score", 0)
    
    # Fetch activity for steps
    url_activity = f"{OURA_API_URL}/daily_activity"
    activity_data = make_request(url_activity, params=params)
    
    if activity_data:
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



