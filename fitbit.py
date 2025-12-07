import os
import requests
import datetime

# Fitbit API documentation: https://dev.fitbit.com/build/reference/web-api/
FITBIT_API_URL = "https://api.fitbit.com/1/user/-"

def get_fitbit_headers():
    """Get authorization headers for Fitbit API."""
    token = os.getenv("FITBIT_ACCESS_TOKEN", "").strip()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}"
    }

def get_latest_weight():
    """
    Fetch the most recent weight measurement.
    Returns weight in kg, or 0 if no data available.
    """
    headers = get_fitbit_headers()
    if not headers:
        return 0.0

    # Fetch weight logs for the last 30 days
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=30)
    
    try:
        # Get weight log list
        url = f"{FITBIT_API_URL}/body/log/weight/date/{today.isoformat()}/30d.json"
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        # Get the weight logs
        weight_logs = data.get("weight", [])
        if not weight_logs:
            return 0.0
        
        # Sort by date and get the most recent
        latest = sorted(weight_logs, key=lambda x: x.get("date", ""), reverse=True)[0]
        
        # Weight is returned in kg by Fitbit API
        weight_kg = latest.get("weight", 0)
        
        return float(weight_kg) if weight_kg else 0.0
        
    except Exception as e:
        print(f"Error fetching Fitbit weight data: {e}")
        return 0.0
