
import errno
import yaml
import math
import numpy as np
import os
from typing import Dict

from .construct import reduce_board_to_electrodes, offset_polygon

def extract_electrode_nets(pcbfile: str) -> Dict[str, int]:
    import pcbnew
    import re

    table = {}
    board = pcbnew.LoadBoard(pcbfile)
    for pad in board.GetPads():
        mod = pad.GetParent()
        refdes = mod.GetReference()
        if re.match('E\d+', refdes):
            net_name = pad.GetNet().GetNetname()
            table[refdes] = net_name
    return table

def write_silkscreen_footprint(image: np.array, pixel_size: float, footprint_name: str, output_dir: str, description: str='Silk Screen Image'):
    import KicadModTree as kmt
    kicad_mod = kmt.Footprint(footprint_name)
    kicad_mod.setDescription(description)

    kicad_mod.append(kmt.Text(type="reference", text="", at=[0, -3], layer='F.SilkS', hide=True))
    kicad_mod.append(kmt.Text(type="value", text="Fiducial", at=[1.5, 3], layer='F.Fab', hide=True))

    h, w = image.shape

    origin = np.array([-pixel_size*w/2, -pixel_size*h/2])
    threshold = image.max() / 2

    for row in range(h):
        for col in range(w):
            if image[row, col] < threshold:
                continue
            start = origin + (col * pixel_size, row * pixel_size)

            points = [
                start.tolist(),
                (start + (pixel_size, 0)).tolist(),
                (start + (pixel_size, pixel_size)).tolist(),
                (start + (0, pixel_size)).tolist(),
                ]
            kicad_mod.append(kmt.Polygon(nodes=points, layer='F.SilkS', width=0.001))

    # output kicad model
    file_handler = kmt.KicadFileHandler(kicad_mod)
    file_handler.writeFile(os.path.join(output_dir, footprint_name + ".kicad_mod"))

def write_electrode_footprint(e, library_path, footprint_name, clearance):
    import KicadModTree as kmt

    designator = f"E{e.refdes}"

    kicad_mod = kmt.Footprint(footprint_name)
    kicad_mod.setDescription(f"Autogenerated footprint for {designator}")
    kicad_mod.append(kmt.Text(type="reference", text="REF**", at=[0, 0], layer='F.SilkS', hide=True))
    kicad_mod.append(kmt.Text(type="value", text="Electrode", at=[0, 0], layer='F.Fab', hide=True))

    points = offset_polygon(e.points, -clearance/2.0)
    points = [[p[0] - e.anchor_pad[0], p[1] - e.anchor_pad[1]] for p in points]
    polygon = kmt.Polygon(nodes=points, layer='F.Cu', width=0.0001)
    pad = kicad_mod.append(kmt.Pad(
        number=1,
        type=kmt.Pad.TYPE_SMT,
        shape=kmt.Pad.SHAPE_CUSTOM,
        at=e.anchor_pad,
        size=[0.5, 0.5],
        layers=kmt.Pad.LAYERS_SMT,
        primitives=[polygon]
    ))

    file_handler = kmt.KicadFileHandler(kicad_mod)
    file_handler.writeFile(os.path.join(library_path, footprint_name + ".kicad_mod"))

def ensure_directory_exists(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def save_board(board, origin, proj_dir, clearance):
    footprint_library = os.path.join(proj_dir, "electrodes.pretty")

    ensure_directory_exists(footprint_library)
    electrodes = reduce_board_to_electrodes(board)

    layout = {
        'origin': list(origin),
        'components': {},
    }
    for e in electrodes:
        designator = f"E{e.refdes}"
        footprint_name = f'electrode_{designator}'
        write_electrode_footprint(e, footprint_library, footprint_name, clearance)
        xform = e.transform_matrix()
        location = [float(xform[0, 2]), float(xform[1, 2])]
        rotation = -1 * math.atan2(xform[1, 0], xform[0, 0])
        layout['components'][designator] = {
            'location': location,
            'rotation': float(np.rad2deg(rotation)),
            'flipped': False,
            'footprint': {
                'path': footprint_library,
                'name': footprint_name,
            },
        }

    with open('layout.yaml', 'w') as f:
        f.write(yaml.dump(layout))
