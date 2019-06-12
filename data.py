import collections
import io
import itertools as it
from typing import Dict, Iterable, Set, Tuple

import PIL.Image
import geopy
import math
import networkx as nx
import pandas as pd
import staticmap as sm
from haversine import Unit, haversine
from haversine.haversine import _AVG_EARTH_RADIUS_KM


# ------------------------ Utility classes ------------------------

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


# ------------------------ BicingGraph ------------------------

FlowEdge = collections.namedtuple('FlowEdge', ['tail', 'head', 'flow', 'dist'])
_NODE_SCALE_FACTOR: float = 5 / 800
_FLOAT_TO_INT_FACTOR: float = 1000.0


class BicingGraph(nx.Graph):
    def __init__(self, stations: Iterable = None, **attr):
        super().__init__(**attr)
        if stations:
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

        self.remove_edges_from(tuple(self.edges))  # No method to clear all edges in networkx API
        if dist > 0:
            self._add_edges_in_grid(_DistanceGrid(self.nodes, dist), dist)
        self._distance = dist

    def _add_edges_in_grid(self, grid: '_DistanceGrid', max_distance: float):
        """
        Helper method for ``construct_graph``. Adds edges among neighbouring
        nodes in a pre-constructed grid.
        :param grid: grid such that within each cell all nodes are within `dist`
        meters apart
        :param max_distance: maximum distance for connected pairs of points
        """
        for index, cell in grid.cell_dict.items():
            # add every edge in the Cartesian product cell x neighbour if distance(·, ·) <= max_dist
            for neighbour in grid.neighbours(index):
                pairs = it.combinations(cell, r=2) if cell is neighbour else it.product(cell, neighbour)
                for a, b in pairs:
                    dist = distance(a, b)
                    if 0 < dist <= max_distance:
                        self.add_edge(a, b, distance=dist)

            # mark cell as empty (to avoid repeated computations)
            cell.clear()

    def plot(self, size: int = 800, node_col='blue', edge_col='purple'):
        """Return a static map of BCN with edges between stations drawn in red"""
        # TODO: colours for connected components?
        # TODO: top-level function
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

    def route(self, origin: Coordinate, destination: Coordinate,
              walking_speed: float = 10 / 9, biking_speed: float = 25 / 9):
        """
        Function that provides the minimum time route between two coordinates.
        Considering that the user can only use a bicycle between two nodes with an
        adjacent edge in the geometric graph.

        The walking distances are scaled by a factor to compensate for the different
        traversal speed, while maintaining the proportions between walking and cycling
        speed (to avoid having to explicitly calculate the time needed to traverse each edge).

        :param origin: Coordinate of the origin.
        :param destination: Coordinate of the destination.
        :param walking_speed: average walking speed in m/s
        :param biking_speed: average biking speed in m/s

        :returns: (path_graph, duration);
                  - path_graph: the graph that contains that contains the optimal path;
                  - duration: total amount of seconds needed to traverse the route with
                             the given speeds
        """

        # Implementation note:
        # Instead of calculating the traversal time for each edge explicitly,
        # the walking distances are scaled by a factor to compensate for the different
        # traversal speed, while maintaining the proportions between walking and cycling
        # speed, taking advantage of the already computed 'distance' attribute.

        # wrap with StationWrapper for convenience (i.e. `coords` property):
        origin, destination = map(StationWrapper, (origin, destination))

        with self._route_setup(origin, destination, biking_speed / walking_speed):
            total_distance, path = nx.single_source_dijkstra(self, origin, destination,
                                                             weight='distance')

        # construct path graph:
        path_graph = BicingGraph(path)
        path_graph.add_edges_from(e for e in zip(path, path[1:]))

        duration = total_distance / biking_speed
        return path_graph, duration

    def _route_setup(self, origin: StationWrapper, destination: StationWrapper, walk_factor: float):
        """
        Returns context manager that prepares the graph to be traversed
        by a Dijkstra search, and cleans up afterwards. To avoid copying the graph.
        """

        class RouteContextManager:
            def __init__(self, graph: nx.Graph):
                self.graph = graph

            def __enter__(self):
                g = self.graph
                g.add_node(origin)
                g.add_node(destination)

                # consider the possibility of walking end-to-end:
                g.add_edge(origin, destination, distance=distance(origin, destination) * walk_factor)
                # connect all nodes to origin and destination:
                for node in g.nodes:
                    g.add_edge(origin, node, distance=distance(origin, node) * walk_factor)
                    g.add_edge(destination, node, distance=distance(destination, node) * walk_factor)

            def __exit__(self, exc_type, exc_val, exc_tb):
                # clean up graph, restoring it to its initial state:
                g = self.graph
                g.remove_node(origin)
                g.remove_node(destination)

        return RouteContextManager(self)

    FlowDictType = Dict[StationWrapper, Dict[StationWrapper, int]]

    def distribute(self, min_bikes: int, min_free_docks: int) -> Tuple[float, FlowDictType]:
        if not isinstance(min_bikes, int) or not isinstance(min_free_docks, int) or \
                min_bikes < 0 or min_free_docks < 0:
            raise ValueError("constraints should be non-negative integers")

        self._write_bike_demands(min_bikes, min_free_docks)
        self._write_edge_costs()
        cost, flow_dict = nx.network_simplex(self.to_directed(as_view=True),
                                             demand='bike_demand', weight='distance')
        return round(cost / _FLOAT_TO_INT_FACTOR, 3), flow_dict

    def _write_bike_demands(self, min_bikes: int, min_free_docks: int):
        total_demand: int = 0

        for node, attributes in self.nodes(data=True):
            bikes, free_docks = node.num_bikes_available, node.num_docks_available
            total_docks = bikes + free_docks
            if total_docks < min_bikes + min_free_docks:
                # TODO: custom exception subclass?
                raise nx.NetworkXUnfeasible(
                    f'cannot satisfy constraints `min_bikes={min_bikes}`, `min_free_docks='
                    f'{min_free_docks}` on a station with `{total_docks}` total docks'
                )

            bike_deficit = ramp(min_bikes - bikes)
            dock_deficit = ramp(min_free_docks - free_docks)
            demand = bike_deficit or -dock_deficit
            assert bikes + demand >= min_bikes
            assert free_docks - demand >= min_free_docks

            attributes['bike_demand'] = demand
            total_demand += demand

        self._distribute_excess_demand(min_bikes, min_free_docks, total_demand)

    def _distribute_excess_demand(self, min_bikes: int, min_free_docks: int, total_demand: int):
        gen = iter(self.nodes(data=True))
        while total_demand < 0:
            # Try to find free docks in which to place surplus bikes
            node, attributes = next(gen)
            demand = attributes['bike_demand']
            free_docks = node.num_docks_available
            surplus_docks = min([free_docks - demand - min_free_docks, -total_demand])
            demand += surplus_docks

            total_demand += surplus_docks
            attributes['bike_demand'] = demand

        while total_demand > 0:
            # Try to find surplus bikes to satisfy demand
            node, attributes = next(gen)
            demand = attributes['bike_demand']
            bikes = node.num_bikes_available
            surplus_bikes = min([bikes + demand - min_bikes, total_demand])
            demand -= surplus_bikes
            total_demand -= surplus_bikes
            attributes['bike_demand'] = demand

    def _write_edge_costs(self):
        for u, v, attributes in self.edges(data=True):
            attributes['distance'] = int(_FLOAT_TO_INT_FACTOR * distance(u, v))

    def max_cost_edge(self, flow_dict: FlowDictType) -> FlowEdge:
        def gen() -> Iterable[FlowEdge]:
            for n1, n1_dict in flow_dict.items():
                for n2, flow in n1_dict.items():
                    if flow != 0:
                        dist = self.edges[n1, n2]['distance'] / _FLOAT_TO_INT_FACTOR
                        yield FlowEdge(n1, n2, flow, dist)

        return max(gen(), key=lambda e: e.flow * e.dist)


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

    def neighbours(self, index: Tuple[int, int]) -> Iterable[Tuple[int, int]]:
        """Iterator over the 8 adjacent cells to the cell with index `cell_idx`"""
        grid = self._grid
        i, j = index
        for di, dj in it.product((0, 1, -1), repeat=2):
            yield grid.get((i + di, j + dj), tuple())  # default is empty cell

    @staticmethod
    def _get_degree_side_lengths(lat: float, dist: float) -> Iterable[float]:
        """
        Calculate the (approximate) latitude/longitude degree-increments of the sides of a
        "square" on the earth's surface such that any pair of points within it is at most
        ``dist`` meters away. Here we assume the Earth is a sphere and we
        approximate great-circle distances with planar distances.

        :param lat: latitude degrees at which to perform computations
        :param dist: maximum distance between points in a single cell
        :return: the ``(latitude, longitude)`` degree increments
        """

        side_length = dist
        lat = math.radians(lat)
        latitude_radius = _AVG_EARTH_RADIUS_M * math.cos(lat)
        return map(lambda r: math.degrees(side_length / r), (_AVG_EARTH_RADIUS_M, latitude_radius))


# ------------------------ Computational utils ------------------------

_AVG_EARTH_RADIUS_M = 1000 * _AVG_EARTH_RADIUS_KM


def distance(station1: StationWrapper, station2: StationWrapper) -> float:
    """Utility for the distance between two stations, in meters"""
    return haversine(tuple(station1.coords), tuple(station2.coords), unit=Unit.METERS)


def ramp(x):
    """ReLu function; maximum between x and 0
    :param x: numeric value
    :return: max{0, x}
    """
    return x if x > 0 else 0


def address_to_coord(location: str) -> Coordinate:
    geolocator = geopy.geocoders.Nominatim(user_agent="BCNBicingBot")
    location_coord = geolocator.geocode(location + ', Barcelona')
    return Coordinate(location_coord.latitude, location_coord.longitude)


# ------------------------ Data fetching utils ------------------------

_URL_STATION_INFO = 'https://api.bsmsa.eu/ext/api/bsm/gbfs/v2/en/station_information'
_URL_STATION_STATUS = 'https://api.bsmsa.eu/ext/api/bsm/gbfs/v2/en/station_status'
_DATA_COLUMNS = ['lat', 'lon', 'num_bikes_available', 'num_docks_available']


def fetch_stations() -> pd.DataFrame:
    """Fetches Bicing station data from the official database URL"""
    info = _fetch_station_data_from_json(_URL_STATION_INFO)
    status = _fetch_station_data_from_json(_URL_STATION_STATUS)
    merged = info.join(status, how='inner')
    return merged[_DATA_COLUMNS]


def _fetch_station_data_from_json(url: str) -> pd.DataFrame:
    json_data = pd.read_json(url).data.stations
    return pd.DataFrame.from_records(data=json_data, index='station_id')


# ------------------------ Other utils ------------------------

def save_image_to_memory(image: PIL.Image.Image) -> io.BytesIO:
    """
    Saves and returns the binary image data from a PIL image object
    :param image: PIL image object to save
    """
    image_bytes = io.BytesIO()
    image.save(image_bytes, 'JPEG')
    image_bytes.seek(0)
    return image_bytes
