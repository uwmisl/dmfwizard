import ezdxf
import shapely.ops


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

    for pl in msp.query('LWPOLYLINE'):
        for i in range(1, len(pl)):
            p0 = pl[i-1]
            p1 = pl[i]
            lines.append(((p0[0], p0[1]), (p1[0], p1[1])))
    
    # Use shapely to build polygons out of the lines
    polygons = list(shapely.ops.polygonize(lines))
    # Convert shapely Polygon objects to list of coordinate tuples
    poly_points = [list(p.exterior.coords) for p in polygons]

    return poly_points

