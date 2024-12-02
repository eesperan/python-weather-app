# Python Weather App

## Overview

This is an extremely simplistic Python app, that serves as an example implementation of a number of useful patterns / best practices in Python. The analysis of it, however, is incredibly long and verbose, since it was mainly created to cement these ideas into my brain.

## Program Flow (with annotations)

Here, we will step through the flow of the app, and highlight the various practices utlized.

### Main

```
└─ main()
```

```python
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
```

The main function implements comprehensive error handling for all possible exceptions, including address parsing errors and JSON validation failures. It uses the WeatherAPI singleton pattern with context management for proper resource cleanup.

Under `try`, we first encounter the `parsed_args` variable. This is a `argparse.Namespace` object, similar to a dict/map. Individual attributes (i.e. args) can be addressed with dot notation, e.g. `parsed_args.address`. Let's take a look at the `parse_args()` function.

```
└─ main()
    │
    └─ parse_args()
```

```python
def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch weather data.")
    parser.add_argument('--address', type=str, required=False, help='Address of the location')
    parser.add_argument('--latitude', type=float, required=False, help='Latitude of the location')
    parser.add_argument('--longitude', type=float, required=False, help='Longitude of the location')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parsed_args = parser.parse_args(args)

    Check if both address and lat/long are provided
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
```

First, we specify in the head of the function definition that the input will be a list of strings, and these will become `argparse.Namespace` items. Then, we create an `ArgumentParser` object (from the `argparse` package), and call it `parser`. We then add 4 supported arguments:

- `address` (String)
- `latitude` (Float)
- `longitude` (Float)
- `verbose` (Boolean)
  We then process the list of supplied `args`, and store the resulting `argparse.Namespace` items in `parsed_args`.

From here, we do a number of checks to ensure that the argument values are valid / complete:

- Check that only an address, **or** a lat/long pair have been supplied (since these could represent different locations)
- Check that both the latitude and longitude values are provided, if using lat/long
- Check if neither lat/long **or** address have been provided
- Check that the lat/long values, if provided, are valid (i.e. a `float` between -180/-90 and 90/180)
  - For this last check, we jump to the `validate_latitude_longitude` function, supplying it the lat/long values that have been parsed from the args. This looks like:

```
└─ main()
    │
    └─ parse_args()
        │
        └─ validate_latitude_longitude()
```

```python
def validate_latitude_longitude(latitude: float, longitude: float) -> bool:
    """Validates latitude and longitude values."""

    if not (-90 <= latitude <= 90):
        return False

    if not (-180 <= longitude <= 180):
        return False

    return True
```

As mentioned, this function expects to receive two `float` values for lat/long, and will determine if they fall within the valid ranges for each. If both values check out, it will return `True`; any other outcome produces a `False`,

With that check completed, we now return to the end of `parse_args()`, which is simply:

```
└─ main()
    │
    └─ parse_args()
```

```python
return parsed_args
```

Now we can proceed to the next step in `main()`, which is `setup_logging()`.

```
└─ main()
    │
    └─ setup_logging()
```

```python
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
```

This simple function configured logging for the remainder of the program. it supports the `verbose` boolean (as parsed by `parse_args()`), and sets up the supported values for log `level`, `format`, and the log `handlers`. For the last one, it creates a `StreamHandler` for writing messages to `STDOUT`, and a `FileHandler` for persisting log lines to a file.

The next item in `main()` is responsible for generating the URL that will be fetched to obtain the weather data, based on the values of the `args`. The function responsible for this is `get_weather_url`, which looks like this:

```
└─ main()
    │
    └─ get_weather_url()
```

```python
def get_weather_url(parsed_args) -> str:
    if parsed_args.address:
        address = sanitize_address(parsed_args.address, parsed_args.verbose)
        coords = get_coords_from_address(address, parsed_args.verbose)
        return build_url(coords[0]['lat'], coords[0]['lon'], parsed_args.verbose)
    elif parsed_args.latitude:
        return build_url(parsed_args.latitude, parsed_args.longitude, parsed_args.verbose)

    raise ParsedArgumentError("Failed to build URL: No valid address / coordinates provided.")
```

The function takes in the parsed `args`, whether they are an address or a lat/long pair. Because these inputs have been de-duped / validated in `parse_args()`, they do not need to be checked again here. The initial `if` statement handles the case where the input is an address, and handles it in two stages:

First, it passes the received `parsed_args.address` to a function, `sanitize_address`, to ensure that the address is in a valid format. That function looks like:

```
└─ main()
    │
    └─ get_weather_url()
        │
        └─ sanitize_address()
```

```python
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
```

The `sanitize_address` function receives the address string, and optionally, the `verbose` boolean. It starts by checking that an address was received at all; if not, or if the address is blank (e.g. `''`), then it will raise a `ValueError` exception. If it passes this first check, it then will use the `parse` function of `usaddress` to parse the provided address string; as long as this is successful, and not `None`, the address will be decomposed into a series of address `components`. These are simply re-assembled on the next line with `join` to produce the `sanitized` address string. If this is unsuccessful at any point, an `AddressMissingError` exception is raised, and the provided input is logged to aid in debugging.

Assuming the sanitization process was successful, the function then checks to see if the `verbose` flag was set to `True`; if so, it will log the resulting sanitized address string. Finally, it returns the `sanitized` string back to `get_weather_url()`. The function concludes with a catch-all `except`, which will capture any parsing errors encountered by `usaddress` and output debug info.

Returning to `get_weather_url()`, we are ready to take our `sanitized` address and derive lat/long coordinates from it (as our API call to obtain weather data will ultimately use lat/long no matter what). To do this, we invoke another function, `get_coords_from_address()`, which looks like:

```
└─ main()
    │
    └─ get_weather_url()
        │
        └─ get_coords_from_address()
```

```python
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
```

This function takes in the `sanitized` address string as `address`, and checks if the `verbose` flag is set. It uses the GeoCode API to take a supplied address, and return a JSON object containing - among other things - `display_name`, `lat`, and `long` keys.

First, it constructs a `url`. This is done by combining a constant from `config.py`, the supplied `address`, and a `MAPS_API_KEY` that is read from the system environment. Let's look at the constant, `GEOCODE_BASE_URL`, in `config.py`:

```python
GEOCODE_BASE_URL: str = "https://geocode.maps.co/search"
```

This is pretty straightforward. We prepend this string to the rest of the URL template, resulting in `https://geocode.maps.co/search?q={address}&api_key={MAPS_API_KEY}`. The same substitutions are done for `address` (which is the address string), and `MAPS_API_KEY` (also a string). The resulting `url` is thoughtfully url-encoded later by `urlllib3`, so we don't need to do it here.

With this `url` built, we can now make the API call to GeoCode to get the lat/long coordinates. In order to do this, we make use of the `WeatherAPI` class, which we instantiate as `weather_api`. We then use this instance's `fetch_url` method, supplying it with the `url` we constructed, and the value of `verbose`:

```
└─ main()
    │
    └─ get_weather_url()
        │
        └─ get_coords_from_address()
            │
            └─ WeatherAPI
```

```python
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
```

In the `WeatherAPI` class, we first set `_instance` as a class variable, to store the instance instance of this class. Then, in `__new__`, we ensure that only one instance is created, following the **Singleton** pattern. We then `__init__` the instance, which creates a new http client.

Next, we set up the context manager, with `__enter__` (which essentially does nothing), and `__exit__` (which ensures that the http client gets cleaned up).

Then, we encounter `fetch_url`, which does the actual work in this class. It first checks if `verbose` is set, and if so, Logs the GeoCode url being fetched. Next, we proceed with a `try`, which starts with the request itself (a `GET` to the specified `url`), and then checks if the response comes with an HTTP `200` code. If not, it raises a `FetchUrlDataError`, and logs the error code, Otherwise, it decodes the received data with UTF-8, and returns it to (in this case) `get_coords_from_address()`. If `urllib3` encounters a timeout, or some other request error, corresponding exceptions are raised. Now, we return to `get_coords_from_address()`.

```
└─ main()
    │
    └─ get_weather_url()
        │
        └─ get_coords_from_address()
```

We have received our GeoCode data in JSON format, so we process this with `parse_json_response`, and store the result in `coords`. The `parse_json_response` function is a follows:

```
└─ main()
    │
    └─ get_weather_url()
        │
        └─ parse_json_response()
```

```python
def parse_json_response(response: str) -> dict:
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON response: {e}")
```

This is an extremely simple function, that exists simply to validate that the received JSON was valid. If it was not, a `ValueError` exception is raised; otherwise, we continue on with storing the data in `coords` within `get_coords_from_address()`.

```
└─ main()
    │
    └─ get_weather_url()
        │
        └─ get_coords_from_address()
```

Returning here again, we then do some quick validation of `coords`, to ensure we were actually able to set it. If not, we raise a `GetCoordsFromAddressError` exception, and indicate that we were unable to obtain coordinate data for the supplied address.

If our coordiate data is valid and populated, we can extract elements from it in the next steps. An example of this is performed here if the `verbose` flag is enabled; the `display_name` (input address), `lat`, and `long` values are extracted and subsequently logged.

Finally, we return `coords`, with its JSON location data, beck to `get_weather_url`. Any other general errors in out `try` block's execution are captured as a `GetCoordsFromAddressError` exception.

```
└─ main()
    │
    └─ get_weather_url()
```

Back in `get_weather_url()`. Armed with our location data, stored in `coords[0]`, we do another set of key extractions, and supply the values to `build_url()`, which constructs the URL for the Open Meteo API request with our calculated lat/long values. Here is that function:

```
└─ main()
    │
    └─ get_weather_url()
        │
        └─ build_url()
```

```python
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
```

As mentioned, we supply the `latitude` and `longitude` using data extracted from `coords[0]` in the parent function. We also pass in the value of `verbose`, as usual. First, we validate that the received values are of type `float`, as we need them in this type format. If they are not, we raise a `BuildUrlError`, indicate the need for numerical values, and log the erroneous values that were provided.

Next, we check if either the `latitude` or `longitude` is `None`; if this is the case, we raise a `BuildUrlError` exception, and again log the input data (in case only one of the lat/long is missing, but the other is present).

Now, we are ready to do the finaly validation of our `latitude` and `longitude`, using a function called `validate_latitude_longitude()`. Our values are passed in, and it does the following:

```
└─ main()
    │
    └─ get_weather_url()
        │
        └─ build_url()
          │
          └─ validate_latitude_longitude()
```

```python
def validate_latitude_longitude(latitude: float, longitude: float) -> bool:
    if not (-90 <= latitude <= 90):
        return False

    if not (-180 <= longitude <= 180):
        return False

    return True
```

First, the value of `latitude` is checked to ensure it lies within the range of `-90` and `90`. Next, the `longitude` is checked to see if it falls between `-180` and `180`. If either one of these tests fail, `validate_latitude_longitude()` will return `False`.

```
└─ main()
    │
    └─ get_weather_url()
        │
        └─ build_url()
```

Returning now to `build_url()`: if the result of `validate_latitude_longitude()` was `False`, a `BuildUrlError` exception is raised, indicating that the value(s) were invalid, and logging the supplied inputs. Otherwise, we continue to the construction of the `url`.

The `url` consists of another set of substitutions, using a constant, two input values, and another constant. The constants (again, from `APIConfig` in `config.py`) are:

```
DEFAULT_PARAMS: str = "current=temperature_2m,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
WEATHER_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
```

And the input values are our validated `latitude` and `longitude`. The resulting url looks like:
`https://api.open-meteo.com/v1/forecast/?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"`.

With the `url` construction complete, the result is returned to `get_weather_url()`.

```
└─ main()
    │
    └─ get_weather_url()
```

The `get_weather_url()` function is essentially complete at this point; the `build_url` returned from `build_url()` is itself immediately returned to `main()`. The function definition concludes with a catch-all `ParsedArgumentError` if the preceding steps were unsuccessful.

```
└─ main()
```

We have finally made it back up to `main()` again. The next step is to take our constructed Open Meteo API `url`, and feed it to a new instance of the `WeatherAPI` class to retrieve the data. We use `with` here to take advantage of the Context Manager. Once again, the `WeatherAPI` instance, `weather_api`, is provided with the `url`, and the value of `verbose`.

```
└─ main()
    │
    └─ WeatherAPI
```

Just like before in `get_coords_from_address()`, we invoke the `WeatherAPI` class, and receive JSON data in response. This is stored in `response` back in `main()`.

```
└─ main()
```

We're nearly to the end now. The last function to call in `main()` is `display_weather_data()`, which takes in the data in `response`, and extracts + prints the desired data to the user. This looks like:

```
└─ main()
    │
    └─ display_weather_data()
```

```python
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
```

The function starts by using `parse_json_response()` once again to validate the input. With this successful, it then provides the data to the `WeatherData` class:

```
└─ main()
    │
    └─ display_weather_data()
        │
        └─ WeatherData
```

```python
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
```

This class uses the `@dataclass` decorator as part of its definition. It's responsible for the the final extraction of the relevant input data (`latitude`, `longitude`, `current`) from the JSON `response`, and returns the output data (`temperature`, `wind_speed`) as a `WeatherData` object. This is stored as `weather_data` in `display_weather_data()`.

```
└─ main()
   │
   └─ display_weather_data()
```

With out `weather_data` object populated, we assign the `temperature` and `wind_speed` variables values, so that we can (readably) construct the final `print()` statement. This outputs the current temp / wind speed like so:

```
Temperature:    31.3°
Wind Speed:     3.0 MPH
```

If there are any `ValueErrors` encountered in this step, an excpetion is raised, and the supplied weather data is logged.

```
└─ main()
```

Our task is now complete - we have a weather report! There are only two more things to note. First is the global exception handler in `main()`, which catches all of the defined exception types (`BuildUrlError`, `FetchUrlDataError`, `FetchWeatherDataError`, `GetCoordsFromAddressError`, `ParsedArgumentError`). These are all implemented the same way, as simple classes:

```python
class ExceptionName(Exception):
    pass
```

And lastly, the mandatory check to ensure that `main()` is `__main__`:

```python
if __name__ == "__main__":
  main()
```

That's it!

_fin_
