import click
import json
import os
import shapely
import string


from dmfwizard.io import read_dxf
from dmfwizard.types import Electrode, Peripheral
from dmfwizard.construct import offset_polygon


def periph_id(n):
    """Return A-Z, then AA, AB, etc.
    """
    n_chars = len(string.ascii_uppercase)
    if n < n_chars:
        return string.ascii_uppercase[n]
    elif n < n_chars*n_chars:
        return string.ascii_uppercase[int(n / n_chars) - 1] + string.ascii_uppercase[n % n_chars]
    else:
        raise ValueError(f"You can't possibly need more than {26*26} electrode IDs!!!")

def annotate_peripheral(electrodes):
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    def draw_electrodes():
        for i, e in enumerate(electrodes):
            if id_assignments[i] is None:
                color = 'gray'
            else:
                color = 'green'
            ax.add_patch(patches.Polygon(offset_polygon(e.offset_points(), -0.1)))

        ax.set_title(f'Select PAD location for electrode {periph_id(step)}')
        ax.axis('square')
        ax.invert_yaxis()
        ax.autoscale()

    def find_containing(x, y):
        point = shapely.geometry.Point(x, y)
        for i in range(len(electrodes)):
            e = electrodes[i]
            polygon = shapely.geometry.Polygon(
                [(p[0], p[1])
                for p in offset_polygon(e.offset_points(), -0.1)])

            if polygon.contains(point):
                return i
        return None

    step = 0

    id_assignments = [None] * len(electrodes)

    def onclick(event):
        nonlocal step
        ix, iy = event.xdata, event.ydata

        eidx = find_containing(ix, iy)
        if eidx is None:
            print("Your click does not appear to be inside any electrodes. Try again.")
            return


        if id_assignments[eidx] is not None:
            print("You already assigned that polygon")
            return

        id_assignments[eidx] = periph_id(step)
        electrodes[eidx].anchor_pad = (ix, iy)
        step += 1

        if step == len(electrodes):
            fig.canvas.mpl_disconnect(cid)
            plt.close(1)

        draw_electrodes()


    fig, ax = plt.subplots()
    draw_electrodes()
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    plt.ion()
    plt.show(block=True)

    if all([x is not None for x in id_assignments]):
        return id_assignments
    else:
        raise RuntimeError("Failed to annotate electrodes")

@click.group()
def main():
    pass

@main.command(name='import')
@click.option('--type', help='The unique type name of the periheral')
@click.option('--class', 'pclass', help="reservoir is currently the only supported type", default='reservoir')
@click.option('--out', '-o', help="Output path")
@click.option('--force', '-f', is_flag=True)
@click.option('--plot', is_flag=True)
@click.argument('files', nargs=-1)
def _import(type, pclass, out, files, force, plot):
    """Import geometry to a peripheral file

    Supported input formats: DXF

    If multiple input files are specified, they will be combined and electrodes
    labeled in the order provided.
    """
    polygons = []

    for fname in files:
        _, ext = os.path.splitext(fname)
        ext = ext.upper()

        if ext == '.DXF':
            polygons += read_dxf(fname)
        else:
            raise ValueError(f"Unsupport input extension: {ext}")


    electrodes = [Electrode(p) for p in polygons]
    # Interactively add anchor pad locations and assign IDs to the polygons
    id_assignments = annotate_peripheral(electrodes)

    periph = Peripheral(pclass, type)
    for id, e in zip(id_assignments, electrodes):
        periph.add_electrode(id=id, electrode=e)

    if out is not None:
        if os.path.exists(out) and not force:
            print(f"{out} already exists. Cowardly refusing to overwrite (-f).")
        with open(out, 'w') as f:
            f.write(json.dumps(periph.to_dict()))
    else:
        print(json.dumps(periph.to_dict()))

    if plot:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        fig, ax = plt.subplots()
        for item in periph.electrodes:
            id = item['id']
            e = item['electrode']
            ax.add_patch(patches.Polygon(offset_polygon(e.offset_points(), -0.1), fill=False))

        ax.autoscale()
        ax.axis('square')
        ax.invert_yaxis()
        plt.show()


if __name__ == '__main__':
    main()