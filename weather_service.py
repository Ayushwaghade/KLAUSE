import httpx

def get_coordinates(city):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    response = httpx.get(url, params={"name": city, "count": 1}).json()
    if not response.get("results"):
        return f"City not found: {city}"
    loc = response["results"][0]
    lat, lon = loc["latitude"], loc["longitude"]
    name = f"{loc['name']}, {loc.get('admin1', '')}"
    return name, lat, lon