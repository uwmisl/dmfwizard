"""Contains tools for defining the electrode board layout
"""
import itertools
import math
import numpy as np
import pyclipper
from typing import List, Sequence, Tuple
from .types import BoardDesign, Electrode, Grid, Peripheral
from .crenellation import crenellate_electrodes

def new_grid_square(size: float):
    return [(0.,0.), (0., size), (size, size), (size, 0.)]

def transform_points(points, xy, rot):
    c = math.cos(rot)
    s = math.sin(rot)
    R = np.array([[c, -s], [s, c]])
    points = np.dot(R, np.array(points).T).T
    points += np.array(xy)
    return list(map(tuple, points)) # convert to list of 2-tuples

def reduce_board_to_electrodes(board):
    electrodes = []
    for grid in board.grids:
        for pos, e in grid.electrodes.items():
            electrodes.append(e)

    for periph in board.peripherals:
        for e in periph.electrodes:
            electrodes.append(e['electrode'])

    return electrodes

def offset_polygon(poly: Sequence[Tuple[float, float]], offset: float) -> List[Tuple[float, float]]:
    """Offset a polygon by given amount

    This can be used to pull back polygons to create clearance gap between
    them, by providing a negative offset.
    """
    pco = pyclipper.PyclipperOffset()
    pco.AddPath(pyclipper.scale_to_clipper(poly), pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)
    return pyclipper.scale_from_clipper(pco.Execute(pyclipper.scale_to_clipper(offset)))[0]

def crenellate_grid(grid: Grid, num_digits: int, theta: float, margin: float):
    """Crenellate all of the electrode interfaces in a grid of electrodes

    This will modify the polygons of electrodes in place.

    Args:
        grid: The grid whose electrodes will be modified
        num_digits: crenellation parameter (see :py:meth:`dmfwizard.crenellation.crenellate_electrodes`)
        theta: crenellation parameter (see :py:meth:`dmfwizard.crenellation.crenellate_electrodes`)
        margin: crenellation parameter (see :py:meth:`dmfwizard.crenellation.crenellate_electrodes`)
    """

    xpts = range(grid.size[0])
    ypts = range(grid.size[1])
    for x,y in itertools.product(xpts, ypts):
        if (x,y) in grid.electrodes:
            for other in [(x+1, y), (x, y+1)]:
                if other in grid.electrodes:
                    a = grid.electrodes[(x, y)]
                    b = grid.electrodes[other]
                    try:
                        crenellate_electrodes(a, b, num_digits, theta, margin)
                    except ValueError:
                        print(f"a: {a.points}, b: {b.points}")
                        raise

class Constructor(object):
    """Class to add electrodes to a design

    All electrodes for a board should be added via the same Constructor object,
    as it keeps track of IDs and electrode designators
    """
    def __init__(self):
        self.next_refdes = 1
        self.next_periph_id = 1

    def get_refdes(self) -> int:
        """Allocate and return a new reference designator for an electrode

        :meta private:
        """
        refdes = self.next_refdes
        self.next_refdes += 1
        return refdes

    def get_periph_id(self):
        id = self.next_periph_id
        self.next_periph_id += 1
        return id

    def add_peripheral(
            self,
            board: BoardDesign,
            peripheral: Peripheral,
            position: Tuple[float, float],
            rotation: float):
        peripheral.id = self.get_periph_id()
        for e in peripheral.electrodes:
            e['electrode'].refdes = self.get_refdes()
        peripheral.origin = position
        peripheral.rotation = rotation
        board.peripherals.append(peripheral)
        return peripheral

    def fill(self, grid: Grid, pos: Tuple[int, int]):
        """Fill electrode at a single grid location
        """
        if pos in grid.electrodes:
            # Location already filled
            return
        grid.electrodes[pos] = Electrode(
            points=new_grid_square(grid.pitch),
            anchor_pad=(grid.pitch/2.0, grid.pitch/2.0),
            origin=(pos[0] * grid.pitch, pos[1] * grid.pitch),
            refdes=self.get_refdes(),
            parent=grid)

    def fill_rect(self, grid: Grid, pos: Tuple[int, int], size: Tuple[int, int]):
        """Fill in a rectangle with electrodes

        Args:
            grid: The Grid object to fill
            pos: The position of the top-left electrode in the rectangle
            size: The size of the rectangle, (width, height), in electrodes
        """
        xpts = range(pos[0], pos[0] + size[0])
        ypts = range(pos[1], pos[1] + size[1])
        for x,y in itertools.product(xpts, ypts):
            if x < 0 or x >= grid.size[0] or y < 0 or y >= grid.size[1]:
                raise ValueError(f"Filling rectangle ({pos}/{size}) exceeds grid size ({grid.size})")
            self.fill(grid, (x, y))

    def fill_vert(self, grid: Grid, start: Tuple[int, int], distance: int):
        """Fill a vertical line

        Arguments:
          - start: (x,y) position of start of line
          - distance: Length of line. Positive is down, negative up.
        """
        for i in range(0, distance, int(math.copysign(1, distance))):
            x = start[0]
            y = start[1] + i

            if x < 0 or x >= grid.size[0] or y < 0 or y >= grid.size[1]:
                raise ValueError(f"Filling line ({start}/{distance}) exceeds grid size ({grid.size})")
            self.fill(grid, (x, y))

    def fill_horiz(self, grid: Grid, start: Tuple[int, int], distance: int):
        """Fill a horizontal line in a grid

        Arguments:
          - start: (x,y) position of start of line
          - distance: Length of line. Positive is right, negative left.
        """
        for i in range(0, distance, int(math.copysign(1, distance))):
            x = start[0] + i
            y = start[1]

            if x < 0 or x >= grid.size[0] or y < 0 or y >= grid.size[1]:
                raise ValueError(f"Filling line ({start}/{distance}) exceeds grid size ({grid.size})")
            self.fill(grid, (x, y))

    def fill_ascii(self, grid: Grid, diagram: str):
        """Fill in the grid based on ASCII art

        Each line in the input string describes a row in the grid; Any character except
        spaces or underscores denote a filled location. The first string with
        non-white-space characters will be interpreted as the first row. If you
        wish to leave empty rows at the top, you can denote an empty row with
        an underscore, '_'.

        Args:
            grid: The grid in which electrodes will be created
            diagram: The ascii art string describing the electrodes to add
        """

        # Remove any blank lines at the start of the string
        lines = []
        found_non_blank = False
        for line in diagram.splitlines():
            if not found_non_blank and line.isspace():
                continue
            lines.append(line)
        for row, line in enumerate(lines):
            for i, ch in enumerate(line):
                if ch != '_' and ch != ' ':
                    self.fill(grid, (i, row))




