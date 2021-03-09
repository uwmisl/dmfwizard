import click
import json
import os
import string


from dmfwizard.io import read_dxf
from dmfwizard.types import Electrode, Peripheral
from dmfwizard.construct import offset_polygon

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

    periph = Peripheral(pclass, type)
    for i, p in enumerate(polygons):
        periph.add_electrode(id=string.ascii_uppercase[i], electrode=Electrode(p))

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