"""Constants for the MHD BA integration."""

from datetime import timedelta

DOMAIN = "mhd_ba"
CONF_STOP_ID = "stop_id"
CONF_MAX_DEPARTURES = "max_departures"
CONF_FILTER_LINES = "filter_lines"

# API Settings
API_URL = "https://mapa.idsbk.sk/navigation/stops"
DEPARTURES_API_ENDPOINT = API_URL + "/planned_departures"
STOP_INFO_API_ENDPOINT = API_URL + "/ids"
API_TIMEOUT = 10
DEFAULT_NAME = "MHD BA"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)  # Cloud API minimum interval

# API parameters
DEFAULT_FILTER = "urban"
DEFAULT_CITY_ID = "-1"

# Display settings
DEFAULT_MAX_DEPARTURES = 10
