## weather_app.py
## An example python app that illustrates a number of standard python patterns.

import argparse
from dataclasses import dataclass
import json
import logging
import os
import sys
import urllib3
import usaddress
from config import APIConfig

MAPS_API_KEY = os.environ.get('MAPS_API_KEY')

def build_url(latitude: float, longitude: float, verbose: bool=False) -> str:
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except:
        raise BuildUrlError(
            f"Lat/long must be numerical values. Received: Latitude: {latitude}, Longitude: {longitude}"
        )
    
    if latitude is None or longitude is None:
        raise BuildUrlError(
            f"Latitude and/or longitude not provided. Latitude: {latitude}, Longitude: {longitude}"
        )

    if not validate_latitude_longitude(latitude, longitude):
        raise BuildUrlError(f"Invalid lat/long provided. Latitude: {latitude}, Longitude: {longitude}")

    url = f"{APIConfig.WEATHER_BASE_URL}?latitude={latitude}&longitude={longitude}&{APIConfig.DEFAULT_PARAMS}"
    return url

def create_http_client():
    return urllib3.PoolManager(**APIConfig.HTTP_CONFIG)

def display_weather_data(response: str) -> None:
    """
    Parses and displays weather data from API response.
    Args:
        response: JSON response string from weather API
    """
    try:
        data = parse_json_response(response)
        weather_data = WeatherData.from_dict(data)

        temperature = weather_data.current.get('temperature_2m')
        wind_speed = weather_data.current.get('wind_speed_10m')
        print(f"Temperature:\t{temperature}°\nWind Speed:\t{wind_speed} MPH")
    except ValueError as e:
        logging.error(f"Failed to parse weather data: {e}")

def get_coords_from_address(address: str, verbose: bool=False) -> list[dict]:
    try:  
        url = f"{APIConfig.GEOCODE_BASE_URL}?q={address}&api_key={MAPS_API_KEY}"
        with WeatherAPI.get_instance() as weather_api:
            response = weather_api.fetch_url(url, verbose)
        coords = parse_json_response(response)

        if not coords:
            raise GetCoordsFromAddressError(
                f"No coordinates found for address: {address}. Verify that the address is valid."
            ) 

        if verbose:
            location_data = {
                'display_name': coords[0]['display_name'],
                'lat': coords[0]['lat'],
                'long': coords[0]['lon']
            }
            logging.info(f"Location data:\n{json.dumps(location_data, indent=2, sort_keys=True)}\n")
        
        return coords

    except FetchUrlDataError as e:
        raise GetCoordsFromAddressError(f"Error getting coordinates from address: {e}")

def get_weather_url(parsed_args) -> str:
    """
    Builds weather URL from either address or coordinates.
    
    Args:
        parsed_args: Parsed command line arguments containing either address or lat/long
    
    Returns:
        str: Built URL for weather API
        
    Raises:
        ParsedArgumentError: If URL cannot be built from provided arguments
    """
    if parsed_args.address:
        address = sanitize_address(parsed_args.address, parsed_args.verbose)
        coords = get_coords_from_address(address, parsed_args.verbose)
        return build_url(coords[0]['lat'], coords[0]['lon'], parsed_args.verbose)
    elif parsed_args.latitude:
        return build_url(parsed_args.latitude, parsed_args.longitude, parsed_args.verbose)
    
    raise ParsedArgumentError("Failed to build URL: No valid address / coordinates provided.")

def parse_args(args: list[str]) -> argparse.Namespace:
    """
    Parses command line arguments.
    Raises ParsedArgumentError if validation fails.
    """

    parser = argparse.ArgumentParser(description="Fetch weather data.")
    parser.add_argument('--address', type=str, required=False, help='Address of the location')
    parser.add_argument('--latitude', type=float, required=False, help='Latitude of the location')
    parser.add_argument('--longitude', type=float, required=False, help='Longitude of the location')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parsed_args = parser.parse_args(args)

    # Test to ensure that either:
    # 1. latitude and longitude are both provided
    # - or -
    # 2. address is provided
    # - and -
    # 3. Address and lat/long are not provided together

    # Check if both address and lat/long are provided
    if parsed_args.address is not None and (parsed_args.latitude is not None or parsed_args.longitude is not None):
        raise ParsedArgumentError("Address and latitude/longitude cannot be provided together.")

    # Check if lat/long are partially provided
    if (parsed_args.latitude is not None) != (parsed_args.longitude is not None):
        raise ParsedArgumentError("Both latitude and longitude must be provided together.")
        
    # Check if neither lat/long pair nor address is provided
    if parsed_args.latitude is None and parsed_args.address is None:
        raise ParsedArgumentError("Either '--latitude' and '--longitude' pair, or '--address' must be provided.")

    # Validate latitude and longitude values, if provided
    if parsed_args.latitude is not None and parsed_args.longitude is not None:
        if not validate_latitude_longitude(parsed_args.latitude, parsed_args.longitude):
            raise ParsedArgumentError("Invalid latitude and/or longitude values provided.")

    return parsed_args

def parse_json_response(response: str) -> dict:
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON response: {e}")

def sanitize_address(address: str, verbose: bool=False) -> str:
    if not address or not address.strip():
        raise ValueError(f"Missing address. Input provided: {address}")
    
    try:
        if usaddress.parse(address) is not None:
            parsed_components = usaddress.parse(address)
            sanitized = ' '.join(component for component, label in parsed_components)
        else:
            raise AddressMissingError(f"Missing address from 'usaddress'. Input provided: {address}")

        if verbose:
            logging.info(f"Sanitized address: {sanitized}\n")

        return sanitized

    except usaddress.RepeatedLabelError as e :
        raise ParseAddressError(f"Error parsing address: {e.parsed_string}, {e.original_string}")

def setup_logging(verbose: bool=False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('weather_app.log')
        ]
    )

def validate_latitude_longitude(latitude: float, longitude: float) -> bool:
    """Validates latitude and longitude values."""

    if not (-90 <= latitude <= 90):
        return False

    if not (-180 <= longitude <= 180):
        return False

    return True

@dataclass
class WeatherData:
    latitude: float
    longitude: float
    current: dict

    @classmethod
    def from_dict(cls, data: dict) -> 'WeatherData':
        if not all(key in data for key in ['latitude', 'longitude', 'current']):
            raise ValueError("Missing required fields in weather data")
        return cls(
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            current=data['current']
        )

    def __str__(self) -> str:
        return (f"WeatherData(latitude={self.latitude}, longitude={self.longitude}, "
                f"temperature={self.current.get('temperature_2m')}, "
                f"wind_speed={self.current.get('wind_speed_10m')})")

class WeatherAPI:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.http = create_http_client()
        return cls._instance

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.http.clear()

    def fetch_url(self, url: str, verbose: bool=False) -> str:
        if verbose:
            logging.info(f"Fetching data from: {url} \n")
        
        try:
            response = self.http.request('GET', url)
            if response.status != 200:
                raise FetchUrlDataError(f"Failed to fetch data: {response.status}")
            return response.data.decode('utf-8')
        except urllib3.exceptions.TimeoutError:
            raise FetchUrlDataError("Request timed out")
        except urllib3.exceptions.RequestError as e:
            raise FetchUrlDataError(f"Request failed: {str(e)}")

# Exception handlers
class BuildUrlError(Exception):
    """
    Exception raised for errors in building the url.
    """
    pass

class FetchUrlDataError(Exception):
    """
    Exception raised for errors in fetching data from remote URL.
    """
    pass

class FetchWeatherDataError(Exception):
    """
    Exception raised for errors in fetching weather data.
    """
    pass

class GetCoordsFromAddressError(Exception):
    """
    Exception raised for errors in getting coordinates from address.
    """
    pass

class ParsedArgumentError(Exception):
    """
    Exception raised for errors in the argument provided to the weather app.
    """
    pass

class AddressMissingError(Exception):
    """Exception raised when address parsing returns no results."""
    pass

class ParseAddressError(Exception):
    """Exception raised when address parsing fails."""
    pass

def main() -> None:  
  try:  
    parsed_args = parse_args(sys.argv[1:])
    setup_logging(parsed_args.verbose)

    url = get_weather_url(parsed_args)

    with WeatherAPI.get_instance() as weather_api:
        response = weather_api.fetch_url(url, parsed_args.verbose)

    # Print weather data
    display_weather_data(response)

  except (BuildUrlError, FetchUrlDataError, FetchWeatherDataError, 
          GetCoordsFromAddressError, ParsedArgumentError,
          AddressMissingError, ParseAddressError, ValueError) as e:
      logging.error(e)
      sys.exit(1)

# Check for main function
if __name__ == "__main__":
  main()