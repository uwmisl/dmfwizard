import itertools
import math
import pyclipper
from typing import Tuple
from .types import Electrode, Grid
from .crenellation import crenellate_electrodes

def new_grid_square(size: float): 
    return [(0.,0.), (0., size), (size, size), (size, 0.)]

def reduce_board_to_electrodes(board):
    electrodes = []
    for grid in board.grids:
        for pos, e in grid.electrodes.items():
            electrodes.append(e)

            # origin = (pos[0] * grid.pitch, pos[1] * grid.pitch)
            # scaled_points = [(p[0] * grid.pitch, p[1] * grid.pitch) for p in e.points]
            # electrodes.append(Electrode(scaled_points, origin, e.refdes))
    return electrodes

def offset_polygon(poly, offset):
    pco = pyclipper.PyclipperOffset()
    pco.AddPath(pyclipper.scale_to_clipper(poly), pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)
    return pyclipper.scale_from_clipper(pco.Execute(pyclipper.scale_to_clipper(offset)))[0]

def crenellate_grid(grid, num_digits, theta, margin):
    xpts = range(grid.size[0])
    ypts = range(grid.size[1])
    for x,y in itertools.product(xpts, ypts):
        if (x,y) in grid.electrodes:
            for other in [(x+1, y), (x, y+1)]:
                if other in grid.electrodes:
                    a = grid.electrodes[(x, y)]
                    b = grid.electrodes[other]
                    print(f"Crenellating {(x, y)} with {other}")
                    try:
                        crenellate_electrodes(a, b, num_digits, theta, margin)
                    except ValueError:
                        print(f"a: {a.points}, b: {b.points}")
                        raise

class Constructor(object):
    def __init__(self):
        self.next_refdes = 1

    def get_refdes(self):
        refdes = self.next_refdes
        self.next_refdes += 1
        return refdes

    def fill(self, grid: Grid, pos: Tuple[int, int]):
        grid.electrodes[pos] = Electrode(
            points=new_grid_square(grid.pitch),
            origin=(pos[0] * grid.pitch + grid.origin[0], pos[1] * grid.pitch + grid.origin[1]),
            refdes=self.get_refdes())

    def fill_rect(self, grid: Grid, pos: Tuple[int, int], size: Tuple[int, int]):
        xpts = range(pos[0], pos[0] + size[0])
        ypts = range(pos[1], pos[1] + size[1])
        for x,y in itertools.product(xpts, ypts):
            if x < 0 or x >= grid.size[0] or y < 0 or y >= grid.size[1]:
                raise ValueError(f"Filling rectangle ({pos}/{size}) exceeds grid size ({grid.size})")
            if (x, y) not in grid.electrodes:
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

