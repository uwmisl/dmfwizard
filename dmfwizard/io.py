import ezdxf
import math
import numpy as np
import json
import shapely.ops
import sys

from .types import Electrode, Peripheral


def load_peripheral(filename) -> Peripheral:
    """Read a peripheral definition from JSON file
    """
    with open(filename, 'r') as f:
        data = json.loads(f.read())

    p = Peripheral(data['class'], data['type'])
    for e in data['electrodes']:
        p.add_electrode(e['id'], Electrode(e['polygon'], parent=p))

    return p

def approximate_arc(center, radius, start_angle, end_angle, segment_angle):
    num_segments = int(abs((start_angle - end_angle)) / segment_angle)
    theta = np.linspace(start_angle, end_angle, num_segments)
    x = center[0] + radius * np.cos(np.deg2rad(theta))
    y = center[1] + radius * np.sin(np.deg2rad(theta))
    return [(x, y) for x,y in zip(x, y)]

def read_dxf(filename):
    """Load polygons from a DXF file
    
    For reliable polygon detection, all lines in your DXF should form closed
    polygons, and each line end should be coincident with another.
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
            for i in range(1, len(e)):
                p0 = e[i-1]
                p1 = el[i]
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
    lines = np.array(lines)
    lines = np.round((lines * SCALE_FACTOR)).astype(np.int32).tolist()
    
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
