from copy import deepcopy
import itertools
import numpy as np
from typing import Dict, List, Tuple

def make_transform_matrix(rotation, translation):
    c = np.cos(rotation)
    s = np.sin(rotation)
    return np.array([
        [c, -s, translation[0]],
        [s, c, translation[1]],
        [0., 0., 1.]
        ])

class GeometryContainer(object):
    def __init__(self, origin: Tuple[float, float]=(0.0, 0.0), parent: 'GeometryContainer'=None, rotation: float=0.0):
        if origin is None:
            origin = (0., 0.)
        self._parent = parent
        self.origin = origin
        self.rotation = rotation

    @property
    def origin(self):
        return self._origin

    @origin.setter
    def origin(self, value):
        if len(value) != 2:
            raise ValueError("Origin must be set to a 2-tuple")
        if isinstance(value, tuple):
            self._origin = value
        elif isinstance(value, list):
            self._origin = tuple(value)
        elif isinstance(value, np.ndarray):
            self._origin = tuple(value.tolist())
        else:
            raise ValueError(f"Origin should be set to a 2-tuple, not '{value}'")

    @property
    def parent(self):
        return self._parent

    def transform_matrix(self):
        M = make_transform_matrix(self.rotation, self.origin)
        if self._parent is not None:
            M = np.dot(self._parent.transform_matrix(), M)
        return M

    def global_origin(self):
        origin = self.origin
        if self._parent is not None:
            origin = tuple(np.add(origin, self._parent.global_origin()).tolist())
        return origin
class Electrode(GeometryContainer):
    def __init__(
            self,
            points: List[Tuple[float, float]]=None,
            origin: Tuple[float, float]=(0.0, 0.0),
            refdes: int=-1,
            parent: GeometryContainer=None,
            anchor_pad: Tuple[float, float]=(0.0, 0.0)
        ):
        super().__init__(origin, parent)
        self.anchor_pad = anchor_pad
        self.refdes = refdes
        if points is None:
            self.points = []
        else:
            self.points = points

    def copy(self):
        newe = Electrode(deepcopy(self.points), self.origin, self.refdes, self.parent, self.anchor_pad)
        return newe

    def num_edges(self):
        return len(self.points)

    def point(self, n):
        return self.points[n]

    def offset_point(self, n):
        M = self.transform_matrix()
        return np.dot(M, tuple(self.points[n]) + (1.0,))[0:2]

    def offset_points(self):
        M = self.transform_matrix()
        points = np.column_stack([np.array(self.points), np.ones(len(self.points))])
        offset_points = np.dot(M, points.T).T[:, 0:2]
        return offset_points.tolist()

    def offset_edge(self, n: int):
        if n >= len(self.points):
            raise ValueError(f"Cannot get edge {n} on polygon with only {len(self.points)} edges")
        if n == len(self.points) - 1:
            return [self.offset_point(n), self.offset_point(0)]
        else:
            return [self.offset_point(n), self.offset_point(n+1)]

    def edge(self, n: int):
        if n >= len(self.points):
            raise ValueError(f"Cannot get edge {n} on polygon with only {len(self.points)} edges")
        if n == len(self.points) - 1:
            return [self.point(n), self.point(0)]
        else:
            return [self.point(n), self.point(n+1)]

    def insert_points(self, index, points, prune_duplicates=True):
        start = 0
        end = None
        if prune_duplicates and np.linalg.norm(np.array(self.points[index-1]) - np.array(points[0])) < 0.001:
            start = 1
        if index == len(self.points):
            nextidx = 0
        else:
            nextidx = index
        if prune_duplicates and np.linalg.norm(np.array(self.points[nextidx]) - np.array(points[-1])) < 0.001:
            end = -1
        self.points[index:index] = points[start:end]

    def insert_offset_points(self, index, points, prune_duplicates=True):
        """Insert points in the global coordinate system

        Subtracts origin offset for convenience
        """
        M = np.linalg.inv(self.transform_matrix())
        points = np.column_stack((np.array(points), np.ones(len(points))))
        points = np.dot(M, points.T).T[:, 0:2].tolist()
        self.insert_points(index, points, prune_duplicates)

class Peripheral(GeometryContainer):
    """A peripheral is a set of electrodes conceptually grouped together

    For example: a reservoir.
    """
    def __init__(self, peripheral_class: str, peripheral_type: str, parent=None):
        super().__init__(origin=(0.0, 0.0), rotation=0.0, parent=parent)
        self.peripheral_class = peripheral_class
        self.peripheral_type = peripheral_type
        self.id = None
        self.electrodes: List[Dict] = []

    def copy(self):
        """Returns a deep copy of object
        """
        if isinstance(self.origin, list):
            raise ValueError("Peripheral.origin must be tuple, not list")
        newperiph = Peripheral(self.peripheral_class, self.peripheral_type, self.parent)
        newperiph.origin = self.origin
        newperiph.rotation = self.rotation
        newperiph.id = self.id
        newperiph.electrodes = [{'id': e['id'], 'electrode': e['electrode'].copy()} for e in self.electrodes]
        return newperiph

    def add_electrode(self, id: str, electrode: Electrode, origin:Tuple[float, float]=(0.0, 0.0)):
        self.electrodes.append({
            'id': id,
            'electrode': electrode,
        })

    def electrode(self, id: str):
        for e in self.electrodes:
            if e['id'] == id:
                return e['electrode']
        raise IndexError(f'No electrode with id {id}')

    def to_dict(self):
        return {
            'class': self.peripheral_class,
            'type': self.peripheral_type,
            'id': self.id,
            'origin': self.origin,
            'rotation': self.rotation,
            'electrodes': [
                {
                    'id': e['id'],
                    'polygon': e['electrode'].points,
                    'origin': e['electrode'].origin,
                    'anchor_pad': e['electrode'].anchor_pad,
                }
                for e in self.electrodes
            ],
        }

class Grid(GeometryContainer):
    def __init__(self, origin: Tuple[float, float], size: Tuple[int, int], pitch: float, parent: GeometryContainer=None):
        super().__init__(origin=origin, rotation=0.0, parent=parent)
        self.size = size
        self.pitch = pitch
        self.electrodes: Dict[Tuple[int, int], Electrode] = {}

    def copy(self):
        """Create a deep copy of the grid
        """
        newgrid = Grid(self.origin, self.size, self.pitch, self.parent)
        newgrid.electrodes = {pos : e.copy() for pos, e in self.electrodes.items()}
        return newgrid

    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]

class BoardDesign(object):
    def __init__(self):
        self.grids: List[Grid] = []
        self.peripherals: List[Peripheral] = []

    def copy(self):
        """Create a deep copy of the board
        """
        newboard = BoardDesign()
        newboard.grids = [g.copy() for g in self.grids]
        newboard.peripherals = [p.copy() for p in self.peripherals]
        return newboard
