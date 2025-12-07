#!/usr/bin/env python3
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DIGITRANSIT_KEY", "").strip()
GRAPHQL_URL = "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1"

# GraphQL query to fetch stop times by gtfsId
STOP_TIMES_QUERY = '''
query GetStopTimes($stopId: String!) {
  stop(id: $stopId) {
    name
    code
    stoptimesWithoutPatterns(numberOfDepartures: 10) {
      scheduledDeparture
      realtimeDeparture
      realtime
      trip {
        route {
          shortName
          longName
        }
        tripHeadsign
      }
    }
  }
}
'''

def get_next_departure_minutes(stop_gtfs_id: str, route_number: str, destination_keyword: str) -> int:
    """
    Fetch the next departure time in minutes for a specific route and destination.
    
    Args:
        stop_gtfs_id: Full GTFS ID (e.g., "HSL:1040282")
        route_number: Route number (e.g., "1", "66")
        destination_keyword: Keyword to match in trip headsign (e.g., "Eira", "Paloheinä")
    
    Returns:
        Minutes until next departure, or 0 if no matching departures found
    """
    if not API_KEY:
        return 0

    headers = {
        "Content-Type": "application/json",
        "digitransit-subscription-key": API_KEY,
    }
    
    variables = {"stopId": stop_gtfs_id}
    
    try:
        r = requests.post(
            GRAPHQL_URL,
            headers=headers,
            json={"query": STOP_TIMES_QUERY, "variables": variables},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        
        if "errors" in data:
            print(f"GraphQL error for {stop_gtfs_id}: {data['errors']}")
            return 0
        
        stop_data = data.get("data", {}).get("stop")
        if not stop_data:
            print(f"No stop found for {stop_gtfs_id}")
            return 0
        
        stop_times = stop_data.get("stoptimesWithoutPatterns", [])
        
        # Get current time in seconds since midnight
        now = datetime.now()
        current_seconds = now.hour * 3600 + now.minute * 60 + now.second
        
        # Filter for matching route and destination
        for stop_time in stop_times:
            trip = stop_time.get("trip", {})
            route = trip.get("route", {})
            
            # Check if route matches
            if route.get("shortName") != route_number:
                continue
            
            # Check if destination matches
            headsign = trip.get("tripHeadsign", "")
            if destination_keyword.lower() not in headsign.lower():
                continue
            
            # Use realtime departure if available, otherwise scheduled
            departure_time = stop_time.get("realtimeDeparture") or stop_time.get("scheduledDeparture")
            
            if departure_time is None:
                continue
            
            # Calculate minutes until departure
            time_diff = departure_time - current_seconds
            
            # If negative, it means the departure is tomorrow (past midnight)
            if time_diff < 0:
                time_diff += 24 * 3600
            
            minutes = int(time_diff / 60)
            
            # Return the first matching departure
            if minutes >= 0:
                return minutes
        
        return 0
        
    except Exception as e:
        print(f"Error fetching stop times for {stop_gtfs_id}: {e}")
        return 0

def get_timetables():
    """
    Fetch next departures for configured tram and bus routes.
    
    Returns:
        dict with keys:
            - tram_1_to_eira: minutes until next tram 1 to Eira
            - bus_66_to_paloheina_ice_rink: minutes until next bus 66 to Paloheinä
    """
    # Tram stop to Eira - Route 1
    # https://reittiopas.hsl.fi/pysakit/HSL:1250428
    tram_minutes = get_next_departure_minutes("HSL:1250428", "1", "Eira")
    
    # Bus stop to Paloheinä ice hockey rink - Route 66
    # https://reittiopas.hsl.fi/pysakit/HSL:1250103
    bus_minutes = get_next_departure_minutes("HSL:1250103", "66", "Paloheinä")
    
    return {
        "tram_1_to_eira": tram_minutes,
        "bus_66_to_paloheina_ice_rink": bus_minutes
    }
