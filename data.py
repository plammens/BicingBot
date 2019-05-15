from typing import Dict, Iterable, Set, Tuple

import math
import networkx as nx
import pandas as pd

URL = 'https://api.bsmsa.eu/ext/api/bsm/gbfs/v2/en/station_information'


def fetch_data() -> pd.DataFrame:
    """Fetches Bicing station data from the official database URL"""
    json_data = pd.read_json(URL)
    return pd.DataFrame.from_records(data=json_data.data.stations, index='station_id')


# scaling factor for each box on the grid, to ensure that every pair of points within
# a square is connected
CELL_FACTOR: float = math.sqrt(2) / 2


class Coordinate:
    """Represents a geographical coordinate."""
    lat: float  # latitude
    lon: float  # longitude

    def __init__(self, latitude: float, longitude: float):
        self.lat = latitude
        self.lon = longitude


class BicingGraph(nx.Graph):
    Grid = Dict[Tuple[int, int], Set[int]]

    def __init__(self, stations: Iterable, **attr):
        super().__init__(**attr)
        self.add_nodes_from(stations)

        # Cache grid limits:
        self._bottom_left = Coordinate(min(s.lat for s in stations), min(s.lon for s in stations))
        self._distance = None

    @staticmethod
    def from_dataframe(stations: pd.DataFrame, **kwargs) -> 'BicingGraph':
        return BicingGraph(stations.iterrows(), **kwargs)

    @property
    def distance(self):
        """Current distance used for geometric graph"""
        return self._distance

    @distance.setter
    def distance(self, value):
        self.construct_graph(distance=value)
        self._distance = value

    def construct_graph(self, distance: float):
        """Construct geometric graph with a new distance"""
        if distance < 0:
            raise ValueError("distance should be non-negative")

        grid = self._make_grid(distance)


        self._distance = distance

    def _make_grid(self, distance: float) -> Grid:
        """
        Helper method for ``construct_graph``. Makes a grid of stations
        such that each pair of points within a cell is less than ``distance`` away.
        """
        cell_length = CELL_FACTOR*distance
        grid: BicingGraph.Grid = {}
        for index, node in self.nodes(data=True):
            lat_index: int = int((node['lat'] - self._bottom_left.lat)/cell_length)
            lon_index: int = int((node['lon'] - self._bottom_left.lon)/cell_length)
            cell_index = (lat_index, lon_index)
            grid.setdefault(cell_index, set()).add(index)

        return grid

    def _draw_edges(self, grid: Grid):
        """
        Helper method for ``construct_graph``. Draws edges among neighbouring
        nodes in a pre-constructed grid.
        """
        raise NotImplementedError

