from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
from db.database import Database

class GeocoderService:
    def __init__(self, db: Database):
        self.db = db
        self.geolocator = Nominatim(user_agent="worldpulse_ai")

    def get_coordinates(self, country, city=None):
        location_name = f"{city}, {country}" if city else country
        
        # Check cache
        cached = self.db.get_geocode(location_name)
        if cached:
            return cached['lat'], cached['lon']

        try:
            location = self.geolocator.geocode(location_name, timeout=10)
            if location:
                lat, lon = location.latitude, location.longitude
                self.db.save_geocode({
                    'location_name': location_name,
                    'country': country,
                    'city': city,
                    'lat': lat,
                    'lon': lon
                })
                return lat, lon
            elif city:
                # Try country only if city fails
                return self.get_coordinates(country)
        except (GeocoderTimedOut, Exception) as e:
            print(f"Geocoding error for {location_name}: {e}")
            
        return None, None
