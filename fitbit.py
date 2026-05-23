import os
import time
import threading
import requests
import datetime
import base64
from dotenv import load_dotenv, set_key

load_dotenv()

FITBIT_API_URL = "https://api.fitbit.com/1/user/-"
ENV_PATH = ".env"

_REFRESH_MARGIN_SECONDS = 3600
_refresh_lock = threading.Lock()


def save_token(access_token, refresh_token, expires_in=None):
    """Save new tokens to environment and .env file, including expiry timestamp."""
    os.environ["FITBIT_ACCESS_TOKEN"] = access_token
    os.environ["FITBIT_REFRESH_TOKEN"] = refresh_token

    set_key(ENV_PATH, "FITBIT_ACCESS_TOKEN", access_token)
    set_key(ENV_PATH, "FITBIT_REFRESH_TOKEN", refresh_token)

    if expires_in:
        expires_at = str(int(time.time()) + int(expires_in))
        os.environ["FITBIT_TOKEN_EXPIRES_AT"] = expires_at
        set_key(ENV_PATH, "FITBIT_TOKEN_EXPIRES_AT", expires_at)


def _token_needs_refresh():
    """Return True if the access token is missing or will expire within the margin."""
    token = (os.getenv("FITBIT_ACCESS_TOKEN") or "").strip()
    if not token:
        return True
    expires_at = os.getenv("FITBIT_TOKEN_EXPIRES_AT", "").strip()
    if not expires_at:
        return False
    try:
        return time.time() > (int(expires_at) - _REFRESH_MARGIN_SECONDS)
    except ValueError:
        return False


def refresh_fitbit_token():
    """Refresh the Fitbit access token using the refresh token (thread-safe)."""
    with _refresh_lock:
        if not _token_needs_refresh():
            return True

        client_id = (os.getenv("FITBIT_CLIENT_ID") or "").strip()
        client_secret = (os.getenv("FITBIT_CLIENT_SECRET") or "").strip()
        refresh_token = (os.getenv("FITBIT_REFRESH_TOKEN") or "").strip()

        if not all([client_id, client_secret, refresh_token]):
            print("Missing Fitbit credentials (CLIENT_ID, CLIENT_SECRET, or REFRESH_TOKEN). Cannot refresh.")
            return False

        token_url = "https://api.fitbit.com/oauth2/token"
        credential = f"{client_id}:{client_secret}".encode("utf-8")
        b64_cred = base64.b64encode(credential).decode("utf-8")

        headers = {
            "Authorization": f"Basic {b64_cred}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        r = None
        try:
            r = requests.post(token_url, headers=headers, data=data, timeout=10)
            r.raise_for_status()
            tokens = r.json()

            new_access = tokens.get("access_token")
            new_refresh = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in")

            if new_access and new_refresh:
                save_token(new_access, new_refresh, expires_in)
                print("Successfully refreshed Fitbit token.")
                return True
        except Exception as e:
            print(f"Failed to refresh Fitbit token: {e}")
            if r is not None and getattr(r, "text", None):
                print(f"Response: {r.text}")

        return False


def get_fitbit_headers():
    token = os.getenv("FITBIT_ACCESS_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def make_request(url):
    """Make a GET request with proactive + reactive token refresh."""
    if _token_needs_refresh():
        refresh_fitbit_token()

    headers = get_fitbit_headers()
    if not headers:
        return None

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code == 401:
            print("Fitbit token expired (401), attempting refresh...")
            if refresh_fitbit_token():
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

def _weight_entry_sort_key(entry):
    """Sort key: chronological order (date + time of day)."""
    d = entry.get("date") or ""
    t = entry.get("time") or "00:00:00"
    return (d, t)


def get_latest_weight():
    """
    Fetch the most recent weight measurement from Fitbit body logs.
    Returns weight in the user's unit system (see Fitbit localization), or 0 if unavailable.
    """
    today = datetime.date.today()

    # The Fitbit weight-log endpoint caps date ranges at 31 days.
    # Walk backwards in 30-day windows (up to ~1 year) to find the latest entry.
    window = datetime.timedelta(days=30)
    end = today
    for _ in range(12):
        start = end - window
        url = (
            f"{FITBIT_API_URL}/body/log/weight"
            f"/date/{start.isoformat()}/{end.isoformat()}.json"
        )
        data = make_request(url)
        if not data:
            return 0.0

        try:
            weight_logs = data.get("weight") or []
            if weight_logs:
                latest = sorted(weight_logs, key=_weight_entry_sort_key, reverse=True)[0]
                weight_kg = latest.get("weight", 0)
                if weight_kg:
                    return float(weight_kg)
        except Exception as e:
            print(f"Error parsing Fitbit weight data: {e}")
            return 0.0

        end = start

    return 0.0
