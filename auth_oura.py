import os
import sys
import webbrowser
import requests
import urllib.parse
from dotenv import load_dotenv, set_key

load_dotenv()

ENV_PATH = ".env"


def save_env_variable(key, value):
    set_key(ENV_PATH, key, value)
    os.environ[key] = value


def main():
    print("--- Oura Authorization Helper ---\n")

    client_id = os.getenv("OURA_CLIENT_ID")
    client_secret = os.getenv("OURA_CLIENT_SECRET")

    if not client_id:
        client_id = input("Enter your Oura Client ID: ").strip()
        save_env_variable("OURA_CLIENT_ID", client_id)

    if not client_secret:
        client_secret = input("Enter your Oura Client Secret: ").strip()
        save_env_variable("OURA_CLIENT_SECRET", client_secret)

    if not client_id or not client_secret:
        print("Client ID and Secret are required.")
        return

    scope = "daily workout heartrate session spo2 heart_health"
    redirect_uri = "http://localhost:8080"

    auth_params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": redirect_uri,
        "state": "oura_auth",
    }

    auth_url = "https://cloud.ouraring.com/oauth/authorize?" + urllib.parse.urlencode(auth_params)

    print(f"\nOpening browser to authorize: {auth_url}")
    webbrowser.open(auth_url)

    print("\nAfter authorizing, you will be redirected to localhost (which might fail to load, that's fine).")
    print("Copy the ENTIRE URL from your address bar and paste it here.")
    redirect_response = input("Paste URL: ").strip()

    parsed = urllib.parse.urlparse(redirect_response)
    query_params = urllib.parse.parse_qs(parsed.query)
    code = query_params.get("code", [None])[0]

    if not code:
        print("Error: Could not find 'code' in the URL.")
        return

    token_url = "https://api.ouraring.com/oauth/token"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    print("\nExchanging code for tokens...")
    try:
        r = requests.post(token_url, data=data, timeout=10)
        r.raise_for_status()
        tokens = r.json()

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        if access_token:
            print("Success! Access Token obtained.")
            save_env_variable("OURA_ACCESS_TOKEN", access_token)
        if refresh_token:
            save_env_variable("OURA_REFRESH_TOKEN", refresh_token)
            print("Refresh Token saved.")

        print("\n.env file has been updated.")
        print("You can now run the app.")

    except requests.exceptions.HTTPError as e:
        print(f"Error exchanging token: {e}")
        print(r.text)


if __name__ == "__main__":
    main()
