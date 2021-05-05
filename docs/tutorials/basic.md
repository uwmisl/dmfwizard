# Basic electrode board design tutorial

## Introduction

This will walk through the process of designing a custom electrode board using
the dmfwizard library and KiCad. It is assumed that you have some familiarity
already with the basics of PCB layout and using KiCad. Check out the
[KiCad docs](https://docs.kicad.org/#_getting_started) if you need to brush up.

It's tested on KiCad v5.10. The upcoming 6.x release of KiCad will likely break
some of the APIs and require some updates, but this is TBD.

This process can be done on any operating system, as long as you have KiCad and
a working python development environment setup.

## Setup

### Install KiCad

If you haven't already, install KiCad: <https://www.kicad.org/download/>

### Install the KiCad template

A template project for kicad can be found at <https://github.com/uwmisl/electrode_board_template_100x74>.

Download the template, and place it into your KiCad templates directory. 
To see where this is set to, you can go to "Preferences->Configure Paths...", and
find the value for KICAD_USER_TEMPLATE_DIR. 

### Install the component layout plugin

To install the plugin, simply place the `component_layout_plugin.py` file from the
[kicad_component_layout](https://github.com/mcbridejc/kicad_component_layout)
project into your kicad plugins search path. 
For example, on linux you can place it at `~/.config/kicad/scripting`.

To figure out where your KiCad installation is searching, you can launch the scripting console in pcbnew, and run this command:
`import pcbnew; print(pcbnew.PLUGIN_DIRECTORIES_SEARCH)`

Example install on linux:

```
mkdir -p ~/.config/kicad/scripting
wget -O ~/.config/kicad/scripting/component_layout_plugin.py https://raw.githubusercontent.com/mcbridejc/kicad_component_layout/master/component_layout_plugin.py
```

### Install dmfwizard

You can get the dmfwizard package from the github repository at <https://github.com/uwmisl/dmfwizard>. 

One quick way to install the latest version straight from github is to run the following command:

`pip3 install git+https://github.com/uwmisl/dmfwizard`

### Create a KiCad project

Create a new directory, anywhere you like, for your board. 

Inside that directory, create a directory named `kicad`.

Now, in kicad, go to `File->New->Project from Template...`, select the "User Templates"
tab, and choose the electrode_board_100x74 template. Uncheck the "createa a new
directory for the project" checkbox, and save the new project to the kicad
directory you just created using any name you prefer.

Now you have a basic project with the board outline, connector
positions, and mounting holes all ready. The schematic has all 127
electrodes on it, but none of them are connected yet.

Your directory sctructure should now look something like:

```
yourproject 
  \
    kicad
    \
      CustomElectrodeBoard.sch
      CustomElectrodeBoard.kicad_pcb
      <various other kicad files>
```

### Import peripheral definition from DXF

It's often useful to define multiple electrodes that go together, and then repeat
that pattern in multiple places on the board. This is 
where the concept of a peripheral comes in. A peripheral is a set of electrodes
with polygon definitions which can be placed onto the board at a particular 
location and rotation.

Although it's possible to define a peripheral by manually computing the polygon
vertices, perhaps with a small script to generate them, it can also be convenient
to design them in a parametric CAD package. An electrode design can be exported
to a DXF file, and the `dmfwizard import` command will help with reading the 
DXF, labeling the polygons (e.g. A, B, C, etc), and storing it into the JSON 
format used by dmfwizard. 

For this tutorial, we will use a DXF file, `chevron1_reservoir.dxf` as the
template for our reservoir peripherals.

To run the import tool, execute this command: 

`dmfwizard import --type chevron1 --class reservoir -o chevron1_reservoir.json dxf/chevron_reservoir_v2.dxf`

It will display a rendering of the detected polygons. First inspect to make 
sure your shapes were imported correctly. Then you can click on each electrode
in the order you wish them to be labeled.

```{raw} html
<video width="400" controls="" class="align-center">
    <source src="../_static/import_electrode_marking.webm">
</video>
```

By default, electrodes are labeled with letters ('A', 
'B', 'C' and so on). These are the labels which will be written to the board
definition file to be used later by control software. If you want to name them
differently, you can do so by editing the JSON file after it is created.

````{note}
When created DXF files with reservoir definitions, you should pay attention to
where you place the origin in your DXF. Although not strictly necessary, it
will be easier if you place it at a point that is conceptually convenient for
attaching the reservoir to grid electrodes.

After importing a DXF file, you can offset all of the electrodes together to
shift the origin by adjusting the "origin" attribute in the peripheral JSON
file.

```{image} images/reservoir_origin.png
:align: center
:width: 150
```
````

## Writing the code

Now we can get into the task of defining the custom layout. To create the board
design, we will write a python script. To start off, this script will let us 
describe the board, and then display a visualization of our design in a figure.
You will probably need to iterate on this loop a number of times, tweaking the 
design until you get it how you want it. 

The second half of the script will write out data based on the design:

1. It will write footprints into `kicad/electrodes.pretty`; one footprint for each electrode.
2. It will write layout information into `kicad/layout.yaml`; this has all the information used by the component layout plugin to position the electrodes in your PCB design.
3. It will write the 'layout' section for a board description file, needed by purpledrop control software.

So let's start walking through the python script. 

### Imports and Execution

```python
# %%
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
```

First we import all the stuff we will be using. It can be very convenient to
run this as a jupyter (formerly IPython) notebook. Several IDEs, such as Visual Studio Code, will
support executing cells (defined by the `# %%` boundaries) and displaying 
figures interactively. If that sounds interesting, but you're not sure what it's about, check out instructions for [VS Code](https://code.visualstudio.com/docs/python/jupyter-support-py) or for 
[Jupyter Lab](https://jupyterlab.readthedocs.io/en/stable/getting_started/overview.html).

Of course, you can run it from the command line, e.g. `python3 board_layout.py`. 

```{figure} images/board_plot_screenshot.png
:align: center
:width: 80%

Running as an interactive notebook in VS Code allows quick iteration of the design
```

### Configuration Options

```python
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
```

Next comes some configuration constants. These are options you'll likely want to
customize for your board. 

### Describing electrode locations

```python
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
```

Here we get to the core of the layout definition. First we create a
BoardDefinition, and give it one grid. Then we define which locations in the
grid will have electrodes. Finally, we add four reservoirs, using the peripheral
JSON file we created via the `dmfwizard import` command previously.

There are a number of ways to add electrodes to a grid using the constructor.
The `fill`, `fill_rect`, `fill_horiz`, `fill_vert` methods allow filling in 
shapes. However, for this tutorial, we're going to define the grid in the 
most visual way: `fill_ascii`. Here, the grid is defined as a string, with
each row in the grid represented by a line in the string. If any character
is present, that marks a spot where an electrode is to be populated. A space
denotes a spot in the grid where no electrode is to be populated.

### Crenellating electrode interfaces

```python
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
```

At this point, we have a a board with square electrodes. When designing the
board, no gap is left between electrodes. Neighboring electrode should have 
overlapping edges. The edges will be pulled back later as needed to create
clearance between neighbors. 

It is common for DMF electrodes to be created with jagged edges, so that it is easier
for a drop to transition from one electrode to its neighbor. In dmfwizard, this
is called "crenellation". The crenellation algorithm is able find the shared
edge for any two electrodes (they must have a shared edge), and it inserts new
points on that edge to create the interleaved points. 

For the grid, all of the shared edges can be crenellated in one function call. 
For other cases, you must identify which electrodes are to have their interface
crenellated. In this design, we have to separately call out the interface between
the "A" electrode of each reservoir, and the grid location it connects to.

```{figure} images/crenellated_electrodes_figure.png
:align: center
:width: 80%

Crenellation creates the jagged edges along edges shared by electrodes
```

### Displaying the design with matplotlib

```python
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
```

Here, we simply display the board design in a matplotlib figure. Each electrode
polygon is displayed, along with a set of yelow squares showing empty grid
locations. A green outline is overlayed to show a 50x50mm glass plate, for 
reference, as this design is intended to fit undernearth such a plate, and it
needs to be designed so that the reservoirs reach just outside the edges of the
plate.

### Saving the footprints

```python
#####
# Write KiCad footprints and layout.yml file for kicad
#####
projdir = path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'kicad')
dmfwizard.kicad.save_board(board, KICAD_ORIGIN, projdir, CLEARANCE)
print(f"Saved footprint information into {projdir}")
```

Once you are satisfied with your layout, this code section writes it out to the 
kicad project. Electrode footprints are saved into tge `kicad/electrodes.pretty/` directory, and the
layout information is written to `{projdir}/layout.yaml`. 

### Creating the board definition file

```python
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
```

The final step in the script is to save a board definition file to be used by
PurpleDrop software later. This step cannot actually be run until the PCB is
finishied in KiCad though, because it needs to know which pins the electrodes
get connected to. At first, this section will fail and print an error message.
You can come back and re-run it after routing the PCB.

## Update the board layout in KiCad

Once you've generated the footprints and layout.yaml file, you can head back to KiCad and open the PCB. 

### Update from Schematic 

First, choose "Tools->Update PCB from Schematic" to pull in the electrodes. 

```{note}
You'll probably get a couple errors here like "Cannot add G1 (no footprint assigned)."
This is fine for now. We'll come back to that later.
```

```{image} images/after_electrode_import_screenshot.png
:align: center
:width: 80%
```

You should get a bunch of default electrodes imported to the design. You
may wait to place these outside the edge of the board; our design isn't going 
to use all of them, and we haven't deleted the extras yet, so we want to keep
them out of the way. You could just delete the extras at this stage, but I find
it's easier to hold off, as we may yet end up modifying the design to add more
electrodes before it's done.

### Run component layout

Now run the component layout plugin. If your plugin was installed correction,
you should get an icon for it added to the pcbnew toolbar:

```{image} images/component_layout_button_screenshot.png
:align: center
:width: 300
```

Running the plugin will move all of the electrodes -- or at least the ones used in your design --
to their positions and update the footprints with the correct footrint for each.

```{raw} html
    <video class="align-center" width="500" controls="">
        <source src="../_static/component_layout.webm"/>
    </video>
```

### Route the connections

So here's some bad news: dmfwizard doesn't do anything to help you with routing
the connections between the connectors and the electrodes. That means now you
have some work to do.

You can connect the electrodes to any connector pin; the only constraint is that
the top plate pin can't be moved. So what I recommend is to just begin by fanning
out traces from the connectors to just underneath pads, until you have a trace
run to every electrode. 

Then, you have to assign the net names in the schematic. Once again, this is a
labor-intesive process. It requires going through and placing the net name on each
electrode to match the trace you routed underneath it.

Once you've done that, you can pull in the changes from the schematic -- note that
you should choose "Re-associate footprints by reference" and uncheck the 
"Update footprints" option -- and you should get the rats nest wires showing 
connections between traces and pads. 

Now you can drop a via in the middle of each electrode, and finish connecting the
traces to the vias.

Don't forget to use the DRC tool in KiCad to check for any rules violations and
make sure that all of your nets are connected.

### Create silkscreen fiducials

The script below will download april tags and generate footprints for you. 

Adjust the FIDUCIAL_IDS and SIZE for your own board. You can get by with two 
fiducials, but you can get much more reliable results -- especially for small
fiducials -- if you can add three and spread them out. 
In other words, don't put all three on the same line.

The smallest fiducial we've successfully used is 6mm. If you have room, 8mm 
(or more) is ideal.

```python
"""Creates a silkscreen footprints with no pads, from small images. 

White pixels in the image are silkscreened, and black pixels are left blank. 
It's intended that the silkscreen be placed on a dark soldermask.

April tags are downloaded from: https://github.com/AprilRobotics/apriltag-imgs/tree/master/tag36h11.
"""
import cv2
import numpy as np
import requests
from tempfile import NamedTemporaryFile
from dmfwizard.kicad import write_silkscreen_footprint

# List of fiducial codes to create footprints for
OUTPUT_DIR = 'kicad/PurpleDrop.pretty'
FIDUCIAL_IDS = [9, 10, 11]
SIZE = 8 # mm
BORDER = 1 # px

for fid in FIDUCIAL_IDS:
    tag_name = 'tag36_11_%05d' % fid
    footprint_name = f'{tag_name}_%.2fmm' % SIZE
    download_url = f'https://github.com/AprilRobotics/apriltag-imgs/raw/master/tag36h11/{tag_name}.png'
    tempfile = NamedTemporaryFile('wb')
    r = requests.get(download_url)
    r.raise_for_status()
    tempfile.write(r.content)
    tempfile.flush()
    
    image = cv2.imread(tempfile.name)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    w = image.shape[1] + BORDER * 2
    h = image.shape[0] + BORDER * 2
    borderimage = np.ones((h, w)) * 255
    borderimage[BORDER:h-BORDER, BORDER:w-BORDER] = image

    pixel_size = SIZE / w
    write_silkscreen_footprint(borderimage, pixel_size, footprint_name, OUTPUT_DIR, f"Fiducial Tag {fid}")
```

After that's done, edit the fiducial (Gx) components in eeschema to change the footprints to the new ones. Then import changes from the schematic in pcbnew, and place your fiducials where you would like them.

There is a large soldermap relief, removing solder mask from the entire top of the board.
You will need to add a zone cutout to the zone for each fiducial in order to leave solder
mask underneath for the silk screen. You should also remove copper from underneath the
fiducial by adding zone cutouts to the top copper pour. This helps to lower the height
of the fiducial. Even so, the soldermask + silkscreen can be a bit thicker than the
copper, so it's a good idea to keep some margin between electrodes and the fiducials.