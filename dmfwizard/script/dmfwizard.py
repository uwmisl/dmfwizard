import click
import json
import os
import string


from dmfwizard.io import read_dxf
from dmfwizard.types import Electrode, Peripheral

@click.group()
def main():
    pass

@main.command(name='import')
@click.option('--type', help='The unique type name of the periheral')
@click.option('--class', 'pclass', help="reservoir is currently the only supported type", default='reservoir')
@click.option('--out', '-o', help="Output path")
@click.option('--force', '-f', is_flag=True)
@click.argument('filename')
def _import(type, pclass, out, filename, force):
    """Import geometry to a peripheral file
    
    Supported input formats: DXF
    """
    # 'import' is keyword; workaround
    _, ext = os.path.splitext(filename)
    ext = ext.upper()

    if ext == '.DXF':
        polygons = read_dxf(filename)
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

if __name__ == '__main__':
    main()