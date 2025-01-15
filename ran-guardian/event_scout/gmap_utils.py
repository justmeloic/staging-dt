import googlemaps
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

def geocode_location(location: str) -> dict:
    result = gmaps.geocode(location)
    return result[0]["geometry"]["location"]

print(geocode_location('1600 Amphitheatre Parkway, Mountain View, CA'))

