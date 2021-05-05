import ezdxf
import math
import numpy as np
import json
import shapely.ops
import sys
from typing import Dict

from .types import BoardDesign, Electrode, Peripheral


def load_peripheral(filename: str) -> Peripheral:
    """Read a peripheral definition from JSON file

    Args:
        filename (str): The path to the peripheral definition file
    """
    with open(filename, 'r') as f:
        data = json.loads(f.read())

    p = Peripheral(data['class'], data['type'])
    for e in data['electrodes']:
        p.add_electrode(
            e['id'],
            Electrode(
                e['polygon'],
                anchor_pad=e.get('anchor_pad', (0.0, 0.0)),
                parent=p
            )
        )

    return p

def approximate_arc(center, radius, start_angle, end_angle, segment_angle):
    num_segments = int(abs((start_angle - end_angle)) / segment_angle)
    theta = np.linspace(start_angle, end_angle, num_segments)
    x = center[0] + radius * np.cos(np.deg2rad(theta))
    y = center[1] + radius * np.sin(np.deg2rad(theta))
    return [(x, y) for x,y in zip(x, y)]

def read_dxf(filename: str):
    """Load polygons from a DXF file

    For reliable polygon detection, all lines in your DXF should form closed
    polygons, and each line end should be coincident with another. DXF units
    must be mm.

    `shapely.ops.polygonize_full` is used for detecting polygons in the shapes.

    Args:
        filename (str): The path to the DXF file to be read
    """

    doc = ezdxf.readfile(filename)
    msp = doc.modelspace()
    # DXF files can have a few different varieties of lines
    # This isn't extensively researched or tested, and may need expansion

    def reduce_line(line):
        return (
            (line.dxf.start[0], line.dxf.start[1]),
            (line.dxf.end[0],   line.dxf.end[1])
        )
    lines = [reduce_line(e) for e in msp.query('LINE')]

    lines = []

    for e in msp.query():
        if isinstance(e, ezdxf.entities.LWPolyline):
            for i in range(0, len(e)):
                if i == 0:
                    p0 = e[-1]
                else:
                    p0 = e[i-1]
                p1 = e[i]
                lines.append(((p0[0], p0[1]), (p1[0], p1[1])))
        elif isinstance(e, ezdxf.entities.Line):
            lines.append(reduce_line(e))
        elif isinstance(e, ezdxf.entities.Arc):
            line_segments = approximate_arc(
                e.dxf.center,
                e.dxf.radius,
                e.dxf.start_angle,
                e.dxf.end_angle,
                20)
            for i in range(1, len(line_segments)):
                p0 = line_segments[i-1]
                p1 = line_segments[i]
                lines.append(((p0[0], p0[1]), (p1[0], p1[1])))

    # Scale to fixed point to avoid floating point rounding issues
    SCALE_FACTOR = 1e6
    lines = np.round((np.array(lines) * SCALE_FACTOR)).astype(np.int32).tolist()

    # import matplotlib.pyplot as plt
    # fig, ax = plt.subplots()
    # for l in lines:
    #     #l = list(l.coords)
    #     ax.plot([l[0][0], l[1][0]], [l[0][1], l[1][1]])
    # plt.show()

    # Use shapely to build polygons out of the lines
    polygons, dangles, cuts, invalids = shapely.ops.polygonize_full(lines)

    if len(dangles) > 0 or len(cuts) > 0 or len(invalids) > 0:
        sys.stderr.write("WARNING: There was unused geometry from the DXF. Some features may be missing:\n" + \
            f"    polygons: {len(polygons)}, dangles: {len(dangles)}, cuts: {len(cuts)}, invalids: {len(invalids)}\n")

    # Convert shapely Polygon objects to list of coordinate tuples
    poly_points = [list(p.exterior.coords) for p in polygons]
    poly_points = [(np.array(p).astype(np.float) / SCALE_FACTOR).tolist() for p in poly_points]
    return poly_points

def create_board_definition_layout(board: BoardDesign, pin_table: Dict[str, int]) -> Dict:
    """Create a layout for board definition file from a BoardDesign

    Board definition files are used by the purpledrop software to describe
    electrode boards. This helper function creates the data for this file from
    a board designed with dmfwizard. Note that only the `layout` section of the
    definition is created here; the full board definition can have additional
    data, and it may be necessary to manually merge the layout with other data.

    Args:
        board: A BoardDesign object with all electrodes and peripherals added
        pin_table: A lookup table which provides the pin number (int) for each
            electrode designator.

    Here's an example pin_table:

    .. code-block:: python

        {
            "E1": 2,
            "E2": 5,
            "E3": 101
        }

    """
    def create_grid_dict(grid):
        ret = {}
        ret['origin'] = grid.origin
        ret['pitch'] = grid.pitch
        ret['pins'] = [[None] * grid.width for _ in range(grid.height)]
        for pos, electrode in grid.electrodes.items():
            ret['pins'][pos[1]][pos[0]] = pin_table[f'E{electrode.refdes}']
        return ret

    def create_periph_dict(periph):
        return {
            'class': periph.peripheral_class,
            'type': periph.peripheral_type,
            'id': periph.id,
            'origin': periph.global_origin(),
            'rotation': np.rad2deg(periph.rotation),
            'electrodes': [
                {
                    'id': e['id'],
                    'pin': pin_table[f"E{e['electrode'].refdes}"],
                    'polygon': e['electrode'].points,
                    'origin': e['electrode'].origin,
                }
                for e in periph.electrodes
            ],
        }

    return {
        "layout": {
            'grids': [create_grid_dict(g) for g in board.grids],
            'peripherals': [create_periph_dict(p) for p in board.peripherals],
        }
    }

class PrettyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to print more readable board definition files

    :meta private:
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.indentation_level = 0

    def encode(self, o):
        """Encode JSON object *o* with respect to single line lists."""

        if isinstance(o, (list, tuple)):
            if self._is_single_line_list(o):
                return "[" + ", ".join(json.dumps(el) for el in o) + "]"
            else:
                self.indentation_level += 1
                output = [self.indent_str + self.encode(el) for el in o]
                self.indentation_level -= 1
                return "[\n" + ",\n".join(output) + "\n" + self.indent_str + "]"

        elif isinstance(o, dict):
            self.indentation_level += 1
            output = [self.indent_str + f"{json.dumps(k)}: {self.encode(v)}" for k, v in o.items()]
            self.indentation_level -= 1
            return "{\n" + ",\n".join(output) + "\n" + self.indent_str + "}"

        else:
            return json.dumps(o)

    def _is_single_line_list(self, o):
        if isinstance(o, (list, tuple)):
            return not any(isinstance(el, (list, tuple, dict)) for el in o)\
                   and len(o) <= 2\
                   and len(str(o)) - 2 <= 60

    @property
    def indent_str(self) -> str:
        return " " * self.indentation_level

def save_board_definition_layout_json(layout: Dict, file: str):
    """Save layout to a JSON file

    This method allows writing the JSON with a custom encoder for more human
    readability. Otherwise, it's functionally equivalent to:

        .. code-block:: python

            with open(file, 'w') as f:
                f.write(json.dumps(layout))

    Args:
        layout: The dict for layout, e.g. as returned by `create_board_definition_layout`.
        file: The path to the file to which JSON will be written.
    """

    with open(file, 'w') as f:
        f.write(json.dumps(layout, cls=PrettyJSONEncoder))
