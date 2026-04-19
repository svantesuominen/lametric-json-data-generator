#!/usr/bin/env python3
"""
Re-authorize Oura and Fitbit OAuth tokens.

Opens a browser for each service and automatically captures the callback
on a local HTTP server (port 8080). Just click "Authorize" in each browser
tab — no URL pasting needed.
"""
from __future__ import annotations

import base64
import os
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import requests
from dotenv import load_dotenv, set_key

load_dotenv(ROOT / ".env")
ENV_PATH = str(ROOT / ".env")
REDIRECT_URI = "http://localhost:8080"
CALLBACK_TIMEOUT = 120

_captured_code: str | None = None
_server_should_stop = threading.Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _captured_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code = params.get("code", [None])[0]
        if code:
            _captured_code = code
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authorization successful! You can close this tab.</h2>")
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h2>Error: {error}</h2>".encode())
        _server_should_stop.set()

    def log_message(self, format, *args):
        pass


def _wait_for_callback() -> str | None:
    global _captured_code
    _captured_code = None
    _server_should_stop.clear()

    server = HTTPServer(("127.0.0.1", 8080), _CallbackHandler)
    server.timeout = 2

    def serve():
        while not _server_should_stop.is_set():
            server.handle_request()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    t.join(timeout=CALLBACK_TIMEOUT)
    server.server_close()
    return _captured_code


# ── Oura ──────────────────────────────────────────────────────────────

def reauth_oura() -> bool:
    client_id = (os.getenv("OURA_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("OURA_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        print("SKIP Oura: OURA_CLIENT_ID or OURA_CLIENT_SECRET not set in .env")
        return False

    auth_url = "https://cloud.ouraring.com/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "scope": "daily workout heartrate session spo2 heart_health",
        "redirect_uri": REDIRECT_URI,
        "state": "oura",
    })

    print("\n--- Oura ---")
    print("Opening browser … click 'Allow' to authorize.")
    webbrowser.open(auth_url)

    code = _wait_for_callback()
    if not code:
        print("FAIL  No authorization code received (timed out or denied).")
        return False

    print("Got code, exchanging for tokens …")
    r = requests.post("https://api.ouraring.com/oauth/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret,
    }, timeout=10)

    if r.status_code != 200:
        print(f"FAIL  Token exchange: {r.status_code} {r.text}")
        return False

    tokens = r.json()
    for key, env_key in [("access_token", "OURA_ACCESS_TOKEN"), ("refresh_token", "OURA_REFRESH_TOKEN")]:
        val = tokens.get(key)
        if val:
            set_key(ENV_PATH, env_key, val)
            os.environ[env_key] = val

    print("OK    Oura tokens saved to .env")
    return True


# ── Fitbit ────────────────────────────────────────────────────────────

def reauth_fitbit() -> bool:
    client_id = (os.getenv("FITBIT_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("FITBIT_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        print("SKIP Fitbit: FITBIT_CLIENT_ID or FITBIT_CLIENT_SECRET not set in .env")
        return False

    auth_url = "https://www.fitbit.com/oauth2/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "scope": "weight",
        "redirect_uri": REDIRECT_URI,
        "expires_in": "31536000",
    })

    print("\n--- Fitbit ---")
    print("Opening browser … click 'Allow' to authorize.")
    webbrowser.open(auth_url)

    code = _wait_for_callback()
    if not code:
        print("FAIL  No authorization code received (timed out or denied).")
        return False

    print("Got code, exchanging for tokens …")
    credential = f"{client_id}:{client_secret}".encode()
    r = requests.post("https://api.fitbit.com/oauth2/token", headers={
        "Authorization": f"Basic {base64.b64encode(credential).decode()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }, data={
        "client_id": client_id,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }, timeout=10)

    if r.status_code != 200:
        print(f"FAIL  Token exchange: {r.status_code} {r.text}")
        return False

    tokens = r.json()
    for key, env_key in [("access_token", "FITBIT_ACCESS_TOKEN"), ("refresh_token", "FITBIT_REFRESH_TOKEN")]:
        val = tokens.get(key)
        if val:
            set_key(ENV_PATH, env_key, val)
            os.environ[env_key] = val
    user_id = tokens.get("user_id")
    if user_id:
        set_key(ENV_PATH, "FITBIT_USER_ID", user_id)

    print("OK    Fitbit tokens saved to .env")
    return True


# ── Main ──────────────────────────────────────────────────────────────

def main() -> int:
    print("=== OAuth Re-Authorization ===")
    print(f"Callback server: {REDIRECT_URI}")
    print("Your browser will open twice. Just click 'Authorize' each time.\n")

    oura_ok = reauth_oura()
    fitbit_ok = reauth_fitbit()

    print("\n=== Summary ===")
    print(f"  Oura:   {'OK' if oura_ok else 'FAILED'}")
    print(f"  Fitbit: {'OK' if fitbit_ok else 'FAILED'}")

    if oura_ok or fitbit_ok:
        print("\nRun  python3 scripts/test_env.py  to verify.")
    return 0 if (oura_ok and fitbit_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
