# config.py
from dataclasses import dataclass
import urllib3

@dataclass
class APIConfig:
    DEFAULT_PARAMS: str = "current=temperature_2m,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
    GEOCODE_BASE_URL: str = "https://geocode.maps.co/search"
    HTTP_CONFIG = {
        'timeout': urllib3.Timeout(connect=2.0, read=5.0),
        'retries': urllib3.Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        ),
        'maxsize': 10,
        'cert_reqs': 'CERT_REQUIRED'
    }
    WEATHER_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
