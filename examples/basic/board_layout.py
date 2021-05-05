#%%
"""This script is setup with cells to be run in a jupyter notebook, if desired.
It can also be run from the command line.
"""
import dmfwizard
import dmfwizard.io
import dmfwizard.construct
import dmfwizard.kicad
import itertools
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os
import re

####
# Define the location, size and pitch of the grid
####
# Center-to-center spacing of the electrodes
PITCH = 2.45
# Size of grid to allocate
GRID_WIDTH = 11
GRID_HEIGHT = 11
GRID_SIZE = (GRID_WIDTH, GRID_HEIGHT)
# Where to place the top-left corner of the grid
GRID_ORIGIN = (-GRID_WIDTH*PITCH/2, -GRID_HEIGHT*PITCH/2)

####
# Define the crenellation parameters
####
# The clearance space between electrodes (mm)
CLEARANCE = 0.11
# Number of fingers in each crenellated edge 
NUM_DIGITS = 6
# Angle of the fingers, in radians
THETA = np.deg2rad(55)
# The amount of edge to leave un-adjusted at each end
MARGIN = PITCH * 0.12

#### 
# Define where in the kicad layout to place the board origin
####
KICAD_ORIGIN = [200, 90.75]

# Path to the kicad pcb file
PCB_PATH = 'kicad/ElectrodeBoardExample1.kicad_pcb'

#####
# Programmatically describe the board design
#####
# The board object wraps up all of the elements of the design
board = dmfwizard.BoardDesign()
# Create an electrode "grid". A board can have multiple grids, or none.
# Each grid contains square electrodes arranged on a sparsely populated
# grid of fixed pitch. 
grid = board.create_grid(GRID_ORIGIN, GRID_SIZE, PITCH)
# Create a constructor to populate electrodes. Creating electrodes is done 
# via the constructor so that it can keep track of things like assigning pin
# numbers as electrodes are added.
construct = dmfwizard.Constructor()

grid_design = """\
   XXXXX
   XXXXX
XXXXXXXXXXX
   XXXXX
   XXXXX
   XXXXX
   XXXXX
   XXXXX
XXXXXXXXXXX
   XXXXX
   XXXXX
"""
construct.fill_ascii(grid, grid_design)

# Create reservoirs
def reservoir_location(x, y):
    """Helper function to compute location of reservoir for given 
    grid column
    """
    loc = np.array((x, y+0.5)) * PITCH + GRID_ORIGIN
    return loc.tolist()

res1 = construct.add_peripheral(
    board,
    dmfwizard.io.load_peripheral('chevron1_reservoir.json'),
    reservoir_location(0, 2),
    np.deg2rad(90)
)
res2 = construct.add_peripheral(
    board,
    dmfwizard.io.load_peripheral('chevron1_reservoir.json'),
    reservoir_location(0, 8),
    np.deg2rad(90)
)
res3 = construct.add_peripheral(
    board,
    dmfwizard.io.load_peripheral('chevron1_reservoir.json'),
    reservoir_location(11, 2),
    np.deg2rad(-90)
)
res4 = construct.add_peripheral(
    board,
    dmfwizard.io.load_peripheral('chevron1_reservoir.json'),
    reservoir_location(11, 8),
    np.deg2rad(-90)
)

######
# Crenellate electrodes
######
# Create copy of the board before crenallating, so we can use the
# un-crenellated version for generating the board definition file.
original_board = board.copy()

# Crenellate the interfaces between all grid electrodes
dmfwizard.construct.crenellate_grid(grid, NUM_DIGITS, THETA, MARGIN)

# Crenellate the reservoir electrodes
dmfwizard.construct.crenellate_electrodes(
    grid.electrodes[(0, 2)],
    res1.electrode('A'),
    NUM_DIGITS,
    THETA,
    MARGIN
)
dmfwizard.construct.crenellate_electrodes(
    grid.electrodes[(0, 8)],
    res2.electrode('A'),
    NUM_DIGITS,
    THETA,
    MARGIN
)
dmfwizard.construct.crenellate_electrodes(
    grid.electrodes[(10, 2)],
    res3.electrode('A'),
    NUM_DIGITS,
    THETA,
    MARGIN
)
dmfwizard.construct.crenellate_electrodes(
    grid.electrodes[(10, 8)],
    res4.electrode('A'),
    NUM_DIGITS,
    THETA,
    MARGIN
)

######
# Plot the board
######
# Get list of all electrodes with polygons in global board coordinates
electrodes = board.all_electrodes()
print(f"Total electrodes in design: {len(electrodes)}")
fig, ax = plt.subplots(figsize=(12, 12))
# Add grid outlines for reference
def draw_grid(ax, grid):
    for col, row in itertools.product(range(grid.size[0]), range(grid.size[1])):
        ax.add_patch(patches.Rectangle(
            (grid.pitch * col + grid.origin[0], grid.pitch * row + grid.origin[1]),
            grid.pitch,
            grid.pitch,
            fill=False,
            color='yellow')
        )
draw_grid(ax, board.grids[0])
for e in electrodes:
    ax.add_patch(patches.Polygon(dmfwizard.construct.offset_polygon(e.offset_points(), -CLEARANCE/2.0), fill=True))

# Add 50x50mm border for reference, to show where edge of 50x50mm top plate would end up
ax.add_patch(patches.Rectangle((-25, -25), 50, 50, fill=False, color='green'))
ax.autoscale()
ax.axis('square')
ax.invert_yaxis()
plt.show()

# %%
#####
# Write KiCad footprints and layout.yml file for kicad
#####
projdir = path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'kicad')
dmfwizard.kicad.save_board(board, KICAD_ORIGIN, projdir, CLEARANCE)
print(f"Saved footprint information into {projdir}")

#####
# Write the board definition file
# This section will fail until all of the electrodes in the design have been 
# assigned net names in kicad.
#####
# Read the net names for all components with "E*" designators
net_table = dmfwizard.kicad.extract_electrode_nets(PCB_PATH)
try:
    # Convert the net names (strings) to pin numbers (ints). This assumes all
    # nets are of the form P{pin}, i.e. P1 through P127.
    pin_table = {}
    for refdes, net_name in net_table.items():
        match = re.match('/P(\d+)', net_name)
        if match is None:
            raise RuntimeError(f"Failed to match pin number from net '{net_name}'")
        else:
            pin = int(match.group(1))
            pin_table[refdes] = pin
    
    # Ensure all electrodes got mapped
    for e in original_board.all_electrodes():
        refdes = f"E{e.refdes}"
        if refdes not in pin_table:
            raise RuntimeError(f"No net name found for electrode {refdes}")
    # Note this only write the the `layout` property of the board definition, and
    # you will likely need to merge it with the other data, such as registration info
    layout = dmfwizard.io.create_board_definition_layout(original_board, pin_table)
    dmfwizard.io.save_board_definition_layout_json(layout, "board_definition_layout.json")
except RuntimeError as ex:
    print(ex)
    print("Failed to extract net names for all electrodes from the PCB design" \
        " so board definition layout will not be created")



# %%
