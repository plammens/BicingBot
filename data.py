import pandas as pd

URL = 'https://api.bsmsa.eu/ext/api/bsm/gbfs/v2/en/station_information'

json_data: pd.DataFrame
stations: pd.DataFrame


def fetch_data():
    global json_data, stations

    json_data = pd.read_json(URL)
    stations = pd.DataFrame.from_records(data=json_data.data.stations, index='station_id')
