import networkx as nx
import pandas as pd

URL = 'https://api.bsmsa.eu/ext/api/bsm/gbfs/v2/en/station_information'


def fetch_data() -> pd.DataFrame:
    json_data = pd.read_json(URL)
    return pd.DataFrame.from_records(data=json_data.data.stations, index='station_id')


def make_graph(stations: pd.DataFrame, distance: float) -> nx.Graph:
    raise NotImplementedError



