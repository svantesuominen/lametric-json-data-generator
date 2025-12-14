import requests

# Mapping of internal keys to Unit IDs
RINKS = {
    "kapyla_ice": 42185,      # Käpylä tekojää
    "kapyla_ice_rink": 41770, # Käpylä kaukalo
    "ogeli_ice": 78564        # Ogeli tekojää
}

BASE_URL = "https://api.hel.fi/servicemap/v2/unit"

def get_condition(unit_id):
    """
    Fetches the condition of a specific unit (ice rink) by its ID.
    Returns the condition description in English, or None if not found.
    """
    url = f"{BASE_URL}/{unit_id}/?include=observations"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        observations = data.get("observations", [])
        if not observations:
            return "Unknown"
        
        # Look for the primary observation or the latest one
        # The API seems to return a list, usually with one relevant 'ice_skating_field_condition'
        for obs in observations:
            if obs.get("property") == "ice_skating_field_condition":
                # Prefer English name, fallback to value or quality
                name_dict = obs.get("name", {})
                condition = name_dict.get("en") or name_dict.get("fi") or obs.get("value")
                return condition
        
        return "Unknown"
        
    except Exception as e:
        print(f"Error fetching condition for unit {unit_id}: {e}")
        return "Error"

def get_rink_conditions():
    """
    Fetches conditions for all configured rinks.
    Returns a dictionary with keys matching the rink keys and values being the condition strings.
    """
    results = {}
    for key, unit_id in RINKS.items():
        results[key] = get_condition(unit_id)
    return results
