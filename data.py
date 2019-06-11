from typing import Dict, Iterable, Set, Tuple

import math
import networkx as nx
import pandas as pd
import staticmap as sm
from haversine import Unit, haversine
from haversine.haversine import _AVG_EARTH_RADIUS_KM

# Constants
_AVG_EARTH_RADIUS_M = 1000 * _AVG_EARTH_RADIUS_KM

_URL = 'https://api.bsmsa.eu/ext/api/bsm/gbfs/v2/en/station_information'

_NODE_SCALE_FACTOR: float = 5 / 800


def fetch_stations() -> pd.DataFrame:
    """Fetches Bicing station data from the official database URL"""
    json_data = pd.read_json(_URL)
    return pd.DataFrame.from_records(data=json_data.data.stations, index='station_id')


class Coordinate:
    """Represents a geographical coordinate."""
    __slots__ = 'lat', 'lon'
    lat: float  # latitude
    lon: float  # longitude

    def __init__(self, latitude: float, longitude: float):
        self.lat = latitude
        self.lon = longitude

    def __iter__(self):
        yield self.lat
        yield self.lon

    def __repr__(self):
        return f'({self.lat}, {self.lon})'

    def __str__(self):
        return f'({self.lat}º N, {self.lon}º E)'


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
    def coords(self):
        """Get the coordinates for this station as a ``Coordinate`` object"""
        return Coordinate(self.lat, self.lon)


class BicingGraph(nx.Graph):
    def __init__(self, stations: Iterable, **attr):
        super().__init__(**attr)
        self.add_nodes_from(stations)
        self._distance: float = 0.0

    @classmethod
    def from_dataframe(cls, stations: pd.DataFrame, **kwargs) -> 'BicingGraph':
        rows = stations.itertuples(name='Station')
        return cls(tuple(map(StationWrapper, rows)), **kwargs)

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

    @property
    def components(self) -> int:
        return nx.algorithms.number_connected_components(self)

    def construct_graph(self, dist: float):
        """
        Construct geometric graph with a new distance
        :param dist: new distance, in meters
        """
        if dist < 0:
            raise ValueError("distance should be non-negative")

        self.remove_edges_from(tuple(self.edges))  # No method to clear all edges in networkx's API
        if dist > 0:
            self._add_edges_in_grid(_DistanceGrid(self.nodes, dist), dist)
        self._distance = dist

    def _add_edges_in_grid(self, grid: '_DistanceGrid', dist: float):
        """
        Helper method for ``construct_graph``. Adds edges among neighbouring
        nodes in a pre-constructed grid.
        :param grid: grid such that within each cell all nodes are within `dist`
        meters apart
        :param dist: distance
        """

        def neighbours(cell_idx: Tuple):
            i, j = cell_idx
            indices = ((i + di, j + dj) for di in (0, -1, 1) for dj in (0, -1, 1))
            next(indices)  # discard (i + 0, j + 0)
            return indices

        grid_dict = grid.cell_dict
        for index, cell in grid_dict.items():
            # add every edge in the Cartesian product cell x cell
            self.add_edges_from((a, b) for a in cell for b in cell if a is not b and distance(a, b) <= dist)
            # connect neighbours:
            for neighbour_index in neighbours(index):
                neighbour = grid_dict.get(neighbour_index, tuple())  # default is empty cell
                self.add_edges_from((a, b) for a in cell for b in neighbour
                                    if distance(a, b) <= dist)
            # mark cell as empty (to avoid repeated computations)
            cell.clear()

    def plot(self, size: int = 800, node_col='blue', edge_col='purple'):
        """Return a static map of BCN with edges between stations drawn in red"""
        static_map = sm.StaticMap(size, size, padding_x=20, padding_y=20)
        node_size: int = max(3, int(_NODE_SCALE_FACTOR * size))
        edge_width: int = max(2, node_size - 2)

        def circle_marker(node) -> sm.CircleMarker:
            return sm.CircleMarker((node.lon, node.lat), node_col, node_size)

        def line(u, v) -> sm.Line:
            return sm.Line([(u.lon, u.lat), (v.lon, v.lat)], edge_col, edge_width)

        static_map.markers.extend(circle_marker(u) for u in self.nodes)
        static_map.lines.extend(line(u, v) for u, v in self.edges)
        return static_map.render()


class _DistanceGrid:
    """
    Helper class for the construction of a geometric graph; specifically, for
    ``BicingGraph.construct_graph``. Represents a grid of geographical locations
    such that each pair of points within a cell is less than a certain distance apart.
    """

    def __init__(self, nodes: Iterable, dist: float):
        """Construct a grid with the given distance
        :param nodes: iterable of geographical location objects (with 'lat' and 'lon' attributes)
        :param dist: maximum distance between points in a single cell
        """
        bottom_left = Coordinate(min(n.lat for n in nodes), min(n.lon for n in nodes))

        delta_lat, delta_lon = self._get_degree_side_lengths(bottom_left.lat, dist)
        grid = {}
        for node in nodes:
            lat_index = int((node.lat - bottom_left.lat) / delta_lat)
            lon_index = int((node.lon - bottom_left.lon) / delta_lon)
            grid.setdefault((lat_index, lon_index), set()).add(node)

        self._grid: Dict[Tuple[int, int], Set] = grid

    @property
    def cell_dict(self) -> Dict[Tuple[int, int], Set]:
        return self._grid

    @staticmethod
    def _get_degree_side_lengths(lat: float, dist: float) -> Tuple[float, float]:
        """
        Calculate the (approximate) latitude/longitude degree-increments of the sides of a
        "square" on the earth's surface such that any pair of points within it is at most
        ``dist`` meters away. Here we assume the Earth is a sphere and we
        approximate great-circle distances with planar distances.

        :param lat: latitude degrees at which to perform computations
        :param dist: maximum distance between points in a single cell
        :return: the ``(latitude, longitude)`` degree increments
        """

        # Scale the distance so that every pair of points in a (planar) square with this
        # side length is at most ``self._distance`` meters apart:
        side_length = dist

        lat = math.radians(lat)
        latitude_radius = _AVG_EARTH_RADIUS_M * math.cos(lat)
        return math.degrees(side_length / _AVG_EARTH_RADIUS_M), \
               math.degrees(side_length / latitude_radius)


def distance(station1: StationWrapper, station2: StationWrapper) -> float:
    """Utility for the distance between two stations, in meters"""
    return haversine(tuple(station1.coords), tuple(station2.coords), unit=Unit.METERS)
