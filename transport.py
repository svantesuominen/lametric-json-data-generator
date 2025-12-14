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

def get_next_departures_formatted(stop_gtfs_id: str, route_number: str, destination_keyword: str = None, limit: int = 3) -> str:
    """
    Fetch the next departure times (HH:MM) for a specific route and destination.
    
    Args:
        stop_gtfs_id: GTFS stop ID
        route_number: Route short name (checked via startswith, e.g. "1" matches "1T")
        destination_keyword: Optional keyword to filter headsign (case-insensitive)
        limit: Max departures to return
        
    Returns:
        Comma-separated departure times
    """
    if not API_KEY:
        return ""

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
            return ""
        
        stop_data = data.get("data", {}).get("stop")
        if not stop_data:
            print(f"No stop found for {stop_gtfs_id}")
            return ""
        
        stop_times = stop_data.get("stoptimesWithoutPatterns", [])
        
        # Get current time in seconds since midnight for filtering past departures (if any)
        now = datetime.now()
        current_seconds = now.hour * 3600 + now.minute * 60 + now.second
        
        departures = []
        
        for stop_time in stop_times:
            trip = stop_time.get("trip", {})
            route = trip.get("route", {})
            
            # Check route (allow "1" to match "1T")
            current_route = route.get("shortName", "")
            if not current_route.startswith(route_number):
                continue
            
            # Check destination if provided
            if destination_keyword:
                headsign = trip.get("tripHeadsign", "")
                if destination_keyword.lower() not in headsign.lower():
                    continue
            
            departure_time = stop_time.get("realtimeDeparture") or stop_time.get("scheduledDeparture")
            if departure_time is None:
                continue
            
            # Use buffer of -300s (5 mins ago) to allow slightly delayed updates to still show? 
            # Or just strictly future.
            # Let's show everything the API returns as "next departures", assuming API does the job.
            
            # Format HH:MM
            hours = (departure_time // 3600) % 24
            minutes = (departure_time % 3600) // 60
            time_str = f"{hours:02}:{minutes:02}"
            
            departures.append(time_str)
            
            if len(departures) >= limit:
                break
                
        return ", ".join(departures)
        
    except Exception as e:
        print(f"Error fetching stop times for {stop_gtfs_id}: {e}")
        return ""

def get_timetables():
    """
    Fetch next departures for configured tram and bus routes.
    
    Returns:
        dict with keys:
            - tram_1_to_eira: string of next 3 departure times (e.g. "15:45, 16:01")
            - bus_66_to_paloheina_ice_rink: string of next 3 departure times
    """
    # Tram stop to Eira - Route 1 (or 1T)
    # Stop is likely directional so we can relax destination check
    tram_times = get_next_departures_formatted("HSL:1250428", "1", None)
    
    # Bus stop to Paloheinä ice hockey rink - Route 66
    bus_times = get_next_departures_formatted("HSL:1250103", "66", "Paloheinä")
    
    return {
        "tram_1_to_eira": tram_times,
        "bus_66_to_paloheina_ice_rink": bus_times
    }
