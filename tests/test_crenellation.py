from dmfwizard.crenellation import do_edges_overlap

def test_do_lines_overlap():    
    assert do_edges_overlap(
        [(0.0, 0.0), (0.0, 1.0)],
        [(0.0, 0.1), (0.0, 0.8)],
    )

    assert not do_edges_overlap(
        [(0.0, 0.2), (0.0, 1.0)],
        [(0.0, 0.1), (0.0, 0.8)],
    )

    assert do_edges_overlap(
        [(-2.0, 1.0), (-0.1, 1.0)],
        [(-1.0, 1.0), (-0.1, 1.0)],
    )

    assert not do_edges_overlap(
        [(-2.0, 1.0), (-0.1, 1.0)],
        [(-1.0, 1.0), (-0.1, 1.1)],
    )

    # Partially overlapping doesn't count. One must be fully contained.
    assert not do_edges_overlap(
        [(0, 0), (1, 1)],
        [(0.5, 0.5), (2, 2)]
    )

    assert not do_edges_overlap(
        [(1, 1), (0, 1)],
        [(2, 1), (1, 1)]
    )
    
    assert not do_edges_overlap(
        [(28.0, 6.0), (28.0, 0.0)],
        [(28.0, 8.0), (28.0, 8.05)]
    )

