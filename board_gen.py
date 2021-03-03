#%%
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np

from dmfwizard.types import BoardDesign, Grid

from dmfwizard.construct import Constructor, reduce_board_to_electrodes, crenellate_grid, offset_polygon
from dmfwizard.crenellation import crenellate_electrodes

BASE_PITCH = 1.1
SMALL_PITCH = 2 * BASE_PITCH
LARGE_PITCH = 3 * BASE_PITCH
MARGIN = 0.15
NUM_DIGITS = 2
THETA = 30

board = BoardDesign()
large_grid = Grid((LARGE_PITCH * 1, 0.0), (15, 7), LARGE_PITCH)
small_grid = Grid((0.5 * (LARGE_PITCH-SMALL_PITCH), LARGE_PITCH * 7), (25, 4), SMALL_PITCH)
board.grids.append(large_grid)
board.grids.append(small_grid)
construct = Constructor()

construct.fill_horiz(small_grid, (0, 1), 24)
construct.fill_vert(small_grid, (0, 1), 3)
construct.fill_vert(small_grid, (6, 0), 4)
construct.fill_vert(small_grid, (12, 0), 4)
construct.fill_vert(small_grid, (18, 0), 4)
construct.fill_vert(small_grid, (24, 1), 3)

construct.fill_rect(large_grid, (2, 0), (11, 3))
construct.fill_rect(large_grid, (2, 3), (3, 4))
construct.fill_rect(large_grid, (6, 3), (3, 4))
construct.fill_rect(large_grid, (10, 3), (3, 4))

crenellate_grid(large_grid, NUM_DIGITS, THETA, MARGIN*LARGE_PITCH)
crenellate_grid(small_grid, NUM_DIGITS, THETA, MARGIN*SMALL_PITCH)
# Manually do the interfaces between large grid and small grid
crenellate_electrodes(
    large_grid.electrodes[(3, 6)],
    small_grid.electrodes[(6, 0)],
    NUM_DIGITS, THETA, MARGIN*SMALL_PITCH)
crenellate_electrodes(
    large_grid.electrodes[(7, 6)],
    small_grid.electrodes[(12, 0)],
    NUM_DIGITS, THETA, MARGIN*SMALL_PITCH)
crenellate_electrodes(
    large_grid.electrodes[(11, 6)],
    small_grid.electrodes[(18, 0)],
    NUM_DIGITS, THETA, MARGIN*SMALL_PITCH)
electrodes = reduce_board_to_electrodes(board)

fig, ax = plt.subplots(figsize=(10, 10))
for e in electrodes:
    ax.add_patch(Polygon(offset_polygon(e.offset_points(), -0.06), fill=False))
ax.autoscale()
ax.axis('square')
ax.invert_yaxis()
plt.show()

# %%
