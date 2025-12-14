import os
import requests
import datetime
import base64
from dotenv import load_dotenv, set_key

# Load environment variables
load_dotenv()

# Fitbit API documentation: https://dev.fitbit.com/build/reference/web-api/
FITBIT_API_URL = "https://api.fitbit.com/1/user/-"
ENV_PATH = ".env"

def save_token(access_token, refresh_token):
    """Save new tokens to environment and .env file."""
    os.environ["FITBIT_ACCESS_TOKEN"] = access_token
    os.environ["FITBIT_REFRESH_TOKEN"] = refresh_token
    
    # Persist to .env
    set_key(ENV_PATH, "FITBIT_ACCESS_TOKEN", access_token)
    set_key(ENV_PATH, "FITBIT_REFRESH_TOKEN", refresh_token)

def refresh_fitbit_token():
    """Refresh the Fitbit access token using the refresh token."""
    client_id = os.getenv("FITBIT_CLIENT_ID")
    client_secret = os.getenv("FITBIT_CLIENT_SECRET")
    refresh_token = os.getenv("FITBIT_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        print("Missing Fitbit credentials (CLIENT_ID, CLIENT_SECRET, or REFRESH_TOKEN). Cannot refresh.")
        return False
        
    token_url = "https://api.fitbit.com/oauth2/token"
    credential = f"{client_id}:{client_secret}".encode("utf-8")
    b64_cred = base64.b64encode(credential).decode("utf-8")
    
    headers = {
        "Authorization": f"Basic {b64_cred}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    try:
        r = requests.post(token_url, headers=headers, data=data)
        r.raise_for_status()
        tokens = r.json()
        
        new_access = tokens.get("access_token")
        new_refresh = tokens.get("refresh_token")
        
        if new_access and new_refresh:
            save_token(new_access, new_refresh)
            print("Successfully refreshed Fitbit token.")
            return True
    except Exception as e:
        print(f"Failed to refresh Fitbit token: {e}")
        if r.text:
            print(f"Response: {r.text}")
            
    return False

def get_fitbit_headers():
    """Get authorization headers for Fitbit API."""
    token = os.getenv("FITBIT_ACCESS_TOKEN", "").strip()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}"
    }

def make_request(url):
    """Make a GET request with auto-refresh logic."""
    headers = get_fitbit_headers()
    if not headers:
        return None
        
    try:
        r = requests.get(url, headers=headers, timeout=10)
        
        # If unauthorized, try to refresh and retry
        if r.status_code == 401:
            print("Fitbit token expired (401), attempting refresh...")
            if refresh_fitbit_token():
                # Update headers with new token
                headers = get_fitbit_headers()
                r = requests.get(url, headers=headers, timeout=10)
            else:
                print("Token refresh failed or not possible.")
                return None
                
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error making Fitbit request: {e}")
        return None

def get_latest_weight():
    """
    Fetch the most recent weight measurement.
    Returns weight in kg, or 0 if no data available.
    """
    # Fetch weight logs for the last 30 days
    today = datetime.date.today()
    
    url = f"{FITBIT_API_URL}/body/log/weight/date/{today.isoformat()}/30d.json"
    
    data = make_request(url)
    if not data:
        return 0.0
        
    try:
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
        print(f"Error parsing Fitbit weight data: {e}")
        return 0.0
