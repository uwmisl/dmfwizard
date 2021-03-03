import itertools
import numpy as np
from typing import Dict, List, Tuple


class Electrode(object):
    def __init__(
            self,
            points: List[Tuple[float, float]]=None,
            origin: Tuple[float, float]=(0.0, 0.0),
            refdes: int=-1
        ):
        self.origin = origin
        self.refdes = refdes
        if points is None:
            self.points = []
        else:
            self.points = points

    def num_edges(self):
        return len(self.points)

    def point(self, n):
        return self.points[n]

    def offset_point(self, n):
        return (self.points[n][0] + self.origin[0], self.points[n][1] + self.origin[1])

    def offset_points(self):
        return [(p[0] + self.origin[0], p[1] + self.origin[1]) for p in self.points]

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
        offset_points = [(p[0] - self.origin[0], p[1] - self.origin[1]) for p in points]
        self.insert_points(index, offset_points, prune_duplicates)

class Peripheral(object):
    """A peripheral is a set of electrodes conceptually grouped together

    For example: a reservoir.
    """
    def __init__(self, peripheral_class: str, peripheral_type: str):
        self.peripheral_class = peripheral_class
        self.peripheral_type = peripheral_type
        self.id = None
        self.origin = (0.0, 0.0)
        self.rotation = 0.0
        self.electrodes: List[Dict] = []
    
    def add_electrode(self, id: int, electrode: Electrode, origin:Tuple[float, float]=(0.0, 0.0)):
        self.electrodes.append({
            'id': id,
            'electrode': electrode,
            'origin': origin,
        })

    def to_dict(self):
        return {
            'class': self.peripheral_class,
            'type': self.peripheral_type,
            'id': self.id,
            'origin': self.origin,
            'rotation': self.rotation,
            'electrodes': [
                {'id': e['id'], 'polygon': e['electrode'].points, 'origin': e['origin']}
                for e in self.electrodes
            ],
        }

class Grid(object):
    def __init__(self, origin: Tuple[float, float], size: Tuple[int, int], pitch: float):
        self.size = size
        self.origin = origin
        self.pitch = pitch
        self.electrodes: Dict[Tuple[int, int], Electrode] = {}

class BoardDesign(object):
    def __init__(self):
        self.grids: List[Grid] = []