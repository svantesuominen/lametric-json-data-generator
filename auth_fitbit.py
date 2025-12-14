import os
import sys
import webbrowser
import requests
import base64
import urllib.parse
from dotenv import load_dotenv, set_key

# Load existing environment variables
load_dotenv()

ENV_PATH = ".env"

def save_env_variable(key, value):
    # Use set_key to update the .env file cleanly
    set_key(ENV_PATH, key, value)
    # Also update current env for this session/script
    os.environ[key] = value

def main():
    print("--- Fitbit Authorization Helper ---\n")
    
    # 1. Get Client ID and Secret
    client_id = os.getenv("FITBIT_CLIENT_ID")
    client_secret = os.getenv("FITBIT_CLIENT_SECRET")
    
    if not client_id:
        client_id = input("Enter your Fitbit Client ID: ").strip()
        save_env_variable("FITBIT_CLIENT_ID", client_id)
        
    if not client_secret:
        client_secret = input("Enter your Fitbit Client Secret: ").strip()
        save_env_variable("FITBIT_CLIENT_SECRET", client_secret)

    if not client_id or not client_secret:
        print("Client ID and Secret are required.")
        return

    # 2. Authorization URL
    # Scope: weight
    scope = "weight"
    redirect_uri = "http://localhost:8080" # Standard local redirect
    
    auth_params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": redirect_uri,
        "expires_in": "31536000" # One year (though default access is 8h, refresh is long)
    }
    
    auth_url = "https://www.fitbit.com/oauth2/authorize?" + urllib.parse.urlencode(auth_params)
    
    print(f"\nOpening browser to authorize: {auth_url}")
    webbrowser.open(auth_url)
    
    # 3. Get Code
    print("\nAfter logging in, you will be redirected to localhost (which might fail to load, that's fine).")
    print("Copy the ENTIRE URL from your address bar and paste it here.")
    redirect_response = input("Paste URL: ").strip()
    
    parsed = urllib.parse.urlparse(redirect_response)
    query_params = urllib.parse.parse_qs(parsed.query)
    code = query_params.get("code", [None])[0]
    
    if not code:
        print("Error: Could not find 'code' in the URL.")
        return

    # 4. Exchange Code for Tokens
    token_url = "https://api.fitbit.com/oauth2/token"
    
    # Basic Authorization header: Basic Base64(client_id:client_secret)
    credential = f"{client_id}:{client_secret}".encode("utf-8")
    b64_cred = base64.b64encode(credential).decode("utf-8")
    
    headers = {
        "Authorization": f"Basic {b64_cred}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code": code
    }
    
    print("\nExchanging code for tokens...")
    try:
        r = requests.post(token_url, headers=headers, data=data)
        r.raise_for_status()
        tokens = r.json()
        
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        user_id = tokens.get("user_id")
        
        if access_token:
            print(f"Success! Access Token obtained.")
            save_env_variable("FITBIT_ACCESS_TOKEN", access_token)
        if refresh_token:
            save_env_variable("FITBIT_REFRESH_TOKEN", refresh_token)
            print("Refresh Token saved.")
        if user_id:
            save_env_variable("FITBIT_USER_ID", user_id)
            
        print("\n.env file has been updated.")
        print("You can now run the app.")
        
    except requests.exceptions.HTTPError as e:
        print(f"Error exchanging token: {e}")
        print(r.text)

if __name__ == "__main__":
    main()
