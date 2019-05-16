from typing import Dict, Iterable, Set, Tuple

import math
import networkx as nx
import pandas as pd
from haversine import haversine, Unit

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

    def __iter__(self):
        yield self.lat
        yield self.lon


class StationWrapper:
    """
    Wrapper for a Bicing station. Can be constructed from any object that has
    the same attributes as the rows in the DataFrame returned by ``fetch_data``.
    Implements some extra utilities on top of the data storage.
    """

    def __init__(self, station):
        self.__station = station

    def __getattr__(self, item):
        return getattr(self.__station, item)

    def __repr__(self):
        return repr(self.__station)

    @property
    def coord(self):
        """Get the coordinates for this station as a ``Coordinate`` object"""
        return Coordinate(self.lat, self.lon)


class BicingGraph(nx.Graph):
    def __init__(self, stations: Iterable, **attr):
        super().__init__(**attr)
        self.add_nodes_from(stations)

        # Cache grid limits:
        self._bottom_left = Coordinate(min(s.lat for s in stations), min(s.lon for s in stations))
        self._distance = None

    @staticmethod
    def from_dataframe(stations: pd.DataFrame, **kwargs) -> 'BicingGraph':
        rows = stations.itertuples(name='Station')
        return BicingGraph(tuple(map(StationWrapper, rows)), **kwargs)

    @property
    def distance(self):
        """Current distance used for geometric graph"""
        return self._distance

    @distance.setter
    def distance(self, value):
        """
        Setting a new distance for the graph triggers a re-construction
        of the geometric graph with the new distance.
        """
        self.construct_graph(dist=value)
        self._distance = value

    def construct_graph(self, dist: float):
        """
        Construct geometric graph with a new distance
        :param dist: new distance, in meters
        """
        if dist < 0:
            raise ValueError("distance should be non-negative")

        self._distance = dist
        self._add_edges_in_grid(self._make_grid())  # TODO: fix

    def _make_grid(self) -> Dict[Tuple, Set]:
        """
        Helper method for ``construct_graph``. Makes a grid of stations
        such that each pair of points within a cell is less than ``distance`` away.
        """
        cell_length = CELL_FACTOR*self._distance
        grid = {}
        for node in self.nodes:
            lat_index = int((node.lat - self._bottom_left.lat)/cell_length)
            lon_index = int((node.lon - self._bottom_left.lon)/cell_length)
            grid.setdefault((lat_index, lon_index), set()).add(node)

        return grid

    def _add_edges_in_grid(self, grid: Dict[Tuple, Set]):
        """
        Helper method for ``construct_graph``. Adds edges among neighbouring
        nodes in a pre-constructed grid.
        """
        def neighbours(cell_idx: Tuple):
            i, j = cell_idx
            indices = ((i + di, j + dj) for di in (0, -1, 1) for dj in (0, -1, 1))
            next(indices)  # discard (i + 0, j + 0)
            return indices

        for index, cell in grid.items():
            # add every edge in the Cartesian product cell x cell
            self.add_edges_from((a, b) for a in cell for b in cell if a is not b)
            # connect neighbours:
            for neighbour_index in neighbours(index):
                neighbour = grid.get(neighbour_index, tuple())  # default is empty cell
                self.add_edges_from((a, b) for a in cell for b in neighbour
                                    if distance(a, b) <= self._distance)
            # mark cell as empty (to avoid repeated calculations)
            cell.clear()


def distance(station1: StationWrapper, station2: StationWrapper) -> float:
    """Utility for the distance between two stations, in meters"""
    return haversine(tuple(station1.coord), tuple(station2.coord), unit=Unit.METERS)
