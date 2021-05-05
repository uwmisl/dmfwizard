from .types import Electrode
import itertools
import numpy as np
from typing import Optional, Tuple

def do_edges_overlap(line_a, line_b):
    """True if lines are co-linear and one is contained completely within the other

    :meta private:
    """

    TOL = 1e-12
    line_a = np.array(line_a)
    line_b = np.array(line_b)

    # make vectors from line_b points to both ends of line_a
    # If the cross product is zero, they are colinear
    xp0 = np.cross(line_b[0] - line_a[0], line_b[0] - line_a[1])
    xp1 = np.cross(line_b[1] - line_a[0], line_b[1] - line_a[1])
    if not np.isclose(xp0, 0.0) or not np.isclose(xp1, 0.0):
        return False

    # offset lines so origin is at line_a[0]
    line_b -= line_a[0]
    line_a -= line_a[0]
    len_a = np.linalg.norm(line_a[1])
    u = line_a[1] / np.linalg.norm(line_a[1])

    d0 = np.dot(line_b[0], u)
    d1 = np.dot(line_b[1], u)
    def inside(d):
        return d >= -TOL and d <= len_a + TOL
    def outside(d):
        return d < 0 or d > len_a
    if inside(d0) and inside(d1) or d0 <= 0 and d1 >= len_a or d0 >= len_a and d1 <= 0:
        return True
    return False

def find_overlapping_edges(a: Electrode, b: Electrode) -> Optional[Tuple[int, int]]:
    """Find a pair of edges that overlap for electrodes a and b

    For our purposes, electrodes should abutt each other, but not overlap, so
    there can only be a single overlapping edge. This functions returns the first found.

    :meta private:
    """
    for edge_a, edge_b in itertools.product(range(a.num_edges()), range(b.num_edges())):
        if do_edges_overlap(a.offset_edge(edge_a), b.offset_edge(edge_b)):
            return (edge_a, edge_b)

    return None

def are_edges_flipped(a, b):
    da = np.array(a[1]) - np.array(a[0])
    db = np.array(b[1]) - np.array(b[0])
    return np.dot(da, db) < 0.0

def crenellate_electrodes(
        a: Electrode,
        b: Electrode,
        num_digits: int,
        theta: float,
        margin:float=0.0,
        edge_a_idx: int=-1,
        edge_b_idx: int=-1
        ):
    """Create crenellation on the shared edge between a pair of electrodes

    Args:
      a: The first electrode
      b: The second electrode, which must share an edge with the other
      num_digits: The number of crenellations to create
      theta: The angle of each crenellation, in radians
      margin: The distance from the corners to begin crenellation
      edge_a_idx: Optional, provide an index indicating which edge in electrode a is to be used
      edge_b_idx: Indicates which edge in electrode b to use; must be provided if edge_a_idx is provided.
    """
    if (edge_a_idx == -1 or edge_b_idx == -1) and edge_b_idx != edge_a_idx:
        raise ValueError("If one edge is provided, the other must be also")
    if edge_a_idx == -1:
        edges = find_overlapping_edges(a, b)
        if edges is None:
            raise ValueError("No overlapping edges found to crenellate")
        edge_a_idx, edge_b_idx = edges

    edge_a = a.offset_edge(edge_a_idx)
    edge_b = b.offset_edge(edge_b_idx)
    if np.linalg.norm(edge_a) < np.linalg.norm(edge_b):
        a_is_shorter = True
        short_edge = edge_a
    else:
        a_is_shorter = False
        short_edge = edge_b

    new_points = create_crenellated_edge(short_edge[0], short_edge[1], num_digits, theta, margin)
    new_points = [tuple(p) for p in new_points]
    new_points = [tuple(short_edge[0])] + new_points + [tuple(short_edge[1])]
    if are_edges_flipped(edge_a, short_edge):
        insert_list = list(reversed(new_points))
    else:
        insert_list = new_points
    a.insert_offset_points(edge_a_idx+1, insert_list)
    if are_edges_flipped(edge_b, short_edge):
        insert_list = list(reversed(new_points))
    else:
        insert_list = new_points
    b.insert_offset_points(edge_b_idx+1, insert_list)

def create_crenellated_edge(start, end, num_digits, theta, margin):
    """Create an interleaved edge along the given line

    :meta private:

    Arguments:
      start: The (x,y) coordinate of the line start
      end: The (x,y) coordinate of the line end
      num_digits: The number of fingers or crenellations to create
      theta: The angle of one finger, in radians
      margin: The space to leave from the start and end of the line
    """

    start = np.array(start)
    end = np.array(end)
    assert(start.shape == (2,))
    assert(end.shape == (2,))

    line_length = np.linalg.norm(start - end)
    finger_width = (line_length - margin * 2) / num_digits
    finger_height = finger_width / np.tan(theta/2) / 2

    def alternating(n):
        pts = []
        for i in range(n):
            if (i % 2) == 0:
                pts.append(1.0)
            else:
                pts.append(-1.0)
        return pts

    # Construct a horizontal line starting at origin
    xpts = [margin]
    for i in range(num_digits):
        xpts.append(margin + finger_width/2 + finger_width * i)
    xpts.append(line_length - margin)
    ypts = np.array([0] + alternating(num_digits) + [0]) * finger_height
    pts = np.array([(x, y) for x,y in zip(xpts, ypts)])

    # Transform line to the one given by start and end
    u = end - start
    angle = np.arctan2(u[1], u[0])
    R = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    pts = np.dot(R, pts.T).T
    pts += start
    return pts
