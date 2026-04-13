#!/usr/bin/env python3
"""
Smoke-test variables expected from .env: presence (non-placeholder) + live API checks.
Does not print secret values.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

ENV_VARS = [
    "DIGITRANSIT_KEY",
    "OURA_ACCESS_TOKEN",
    "OURA_REFRESH_TOKEN",
    "OURA_CLIENT_ID",
    "OURA_CLIENT_SECRET",
    "FITBIT_ACCESS_TOKEN",
    "FITBIT_REFRESH_TOKEN",
    "FITBIT_CLIENT_ID",
    "FITBIT_CLIENT_SECRET",
]


def check_present(name: str) -> tuple[bool, str]:
    v = os.getenv(name, "").strip()
    if not v:
        return False, "missing or empty"
    low = v.lower()
    if "your_" in low and "here" in low.replace(" ", ""):
        return False, "placeholder value"
    return True, "set"


def main() -> int:
    print("=== .env variable presence ===\n")
    presence_ok = True
    for name in ENV_VARS:
        ok, msg = check_present(name)
        if not ok:
            presence_ok = False
        print(f"{'OK ' if ok else 'FAIL'} {name}: {msg}")

    print("\n=== API smoke tests (no secrets printed) ===\n")
    exit_code = 0 if presence_ok else 1

    if check_present("DIGITRANSIT_KEY")[0]:
        try:
            import digitransit

            digitransit.fetch_bike_counts()
            print("OK  digitransit.fetch_bike_counts")
        except Exception as e:
            exit_code = 1
            print(f"FAIL digitransit: {e}")
        try:
            import transport

            transport.get_timetables()
            print("OK  transport.get_timetables")
        except Exception as e:
            exit_code = 1
            print(f"FAIL transport: {e}")
    else:
        print("SKIP digitransit / transport (DIGITRANSIT_KEY not set)")

    if check_present("OURA_ACCESS_TOKEN")[0]:
        try:
            import datetime

            import oura

            today = datetime.date.today()
            start = today - datetime.timedelta(days=5)
            url = f"{oura.OURA_API_URL}/daily_readiness"
            data = oura.make_request(
                url,
                params={
                    "start_date": start.isoformat(),
                    "end_date": today.isoformat(),
                },
            )
            if data is not None and "data" in data:
                print("OK  oura daily_readiness")
            else:
                exit_code = 1
                print("FAIL oura daily_readiness (empty or error)")
        except Exception as e:
            exit_code = 1
            print(f"FAIL oura daily_readiness: {e}")

        try:
            import oura

            cv = oura.get_latest_cardiovascular_age()
            if cv is not None:
                print(f"OK  oura cardiovascular_age (value present)")
            else:
                print("WARN oura cardiovascular_age: null (scope, tier, or no data)")
        except Exception as e:
            exit_code = 1
            print(f"FAIL oura cardiovascular_age: {e}")

        try:
            import oura

            m = oura.get_running_distance_this_year()
            print(f"OK  oura get_running_distance_this_year ({m:.0f} m)")
        except Exception as e:
            exit_code = 1
            print(f"FAIL oura running YTD: {e}")
    else:
        print("SKIP oura API tests (OURA_ACCESS_TOKEN not set)")

    if check_present("FITBIT_ACCESS_TOKEN")[0]:
        try:
            import fitbit

            kg = fitbit.get_latest_weight()
            if kg and kg > 0:
                print(f"OK  fitbit get_latest_weight ({kg:.1f} kg)")
            else:
                print(
                    "WARN fitbit get_latest_weight: 0 (no logs, expired token without refresh env, or API error)"
                )
        except Exception as e:
            exit_code = 1
            print(f"FAIL fitbit: {e}")
    else:
        print("SKIP fitbit (FITBIT_ACCESS_TOKEN not set)")

    try:
        import hockey

        hockey.get_rink_conditions()
        print("OK  hockey.get_rink_conditions (no env vars)")
    except Exception as e:
        exit_code = 1
        print(f"FAIL hockey: {e}")

    port = os.getenv("PORT", "8000")
    print(f"\nINFO PORT (optional): {port} (default 8000 if unset)")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
