import numpy as np
from zeropdk.layout.algorithms.sampling import sample_function


def rotate(point, angle_rad):
    ''' Rotates point counter-clockwisely about its origin by an angle given in radians'''
    th = angle_rad
    x, y = point.x, point.y
    new_x = x * np.cos(th) - y * np.sin(th)
    new_y = y * np.cos(th) + x * np.sin(th)
    return point.__class__(new_x, new_y)


rotate90 = lambda point: rotate(point, np.pi / 2)


def cross_prod(p1, p2):
    return p1.x * p2.y - p1.y * p2.x


def project(v, ex, ey=None):
    ''' Compute a such that v = a * ex + b * ey '''
    if ey is None:
        ey = rotate90(ex)

    if cross_prod(ex, ey) == 0:
        raise RuntimeError('ex={} and ey={} are not orthogonal.'.format(repr(ex), repr(ey)))

    # Simple formula
    # https://math.stackexchange.com/questions/148199/equation-for-non-orthogonal-projection-of-a-point-onto-two-vectors-representing

    a = cross_prod(ey, v) / cross_prod(ey, ex)
    # b = cross_prod(ex, v) / cross_prod(ex, ey)

    # v == a * ex + b * ey
    return a


def curve_length(curve, t0=0, t1=1):
    ''' Computes the total length of a curve.

    Args:
        curve: list of Points, or
            parametric function of points, to be computed from t0 to t1.
    '''
    # TODO possible bug: if the curve is a loop, it will return 0 (BAD)
    if isinstance(curve, list):
        # assuming curve is a list of points
        scale = (curve[-1] - curve[0]).norm()
        if scale > 0:
            coords = np.array([[point.x, point.y] for point in curve]).T
            dp = np.diff(coords, axis=-1)
            ds = np.sqrt((dp**2).sum(axis=0))
            return ds.sum()
        else:
            return 0
    else:
        # assuming curve is a function.
        curve_func = curve
        scale = (curve_func(t1) - curve_func(t0)).norm()
        if scale > 0:
            coords = lambda t: np.array([curve_func(t).x, curve_func(t).y])
            _, sampled_coords = sample_function(coords, [t0, t1], tol=0.0001 / scale, min_points=100)  # 1000 times more precise than the scale
            dp = np.diff(sampled_coords, axis=-1)
            ds = np.sqrt((dp**2).sum(axis=0))
            return ds.sum()
        else:
            return 0


def manhattan_intersection(vertical_point, horizontal_point, ex):
    """ returns the point that intersects vertical_point's x coordinate
        and horizontal_point's y coordinate.

        Args: ex (Vector/Point): orientation of x axis.

        Caveat: this formula only works for orthogonal coordinate systems.
    """
    ey = rotate90(ex)
    return vertical_point * ex * ex + horizontal_point * ey * ey


def find_Z_orientation(P0, P1, ex):
    """Compute the orientation of Point P0 against Point P1
    P1 is assumed to be above P0.

    Args: ex (Vector/Point): orientation of x axis.

    Returns:
        0 for Z-oriented and 1 for S-oriented

    """
    if P1 * ex > P0 * ex:
        orient = 0  # Z-oriented
    else:
        orient = 1  # S-oriented
    return orient


def cluster_ports(ports_from, ports_to, ex):
    """Given two (equal length) port arrays, divide them into clusters
    based on the connection orientation. The idea is that each cluster
    can be routed independently with an array of Z or S traces that don't
    touch each other.

    Args: ex (Vector/Point): orientation of the axis along with the ports
    are placed.

    TODO document more.

    Returns:
        an array of k 2-tuples (port_pair_list, orientation),
            where k is the number of clusters,
            port_pair list an array of (p0, p1),
            and orientation is 0 for Z and 1 for S
    """
    orient_old = None
    port_cluster = []
    port_clusters = []
    # sort the arrays first
    proj_ex = lambda p: p.position * ex
    ports_from = sorted(ports_from, key=proj_ex)
    ports_to = sorted(ports_to, key=proj_ex)
    for port_from, port_to in zip(ports_from, ports_to):
        new_cluster = False
        orient_new = find_Z_orientation(port_from.position, port_to.position, ex)
        # first pair
        if orient_old is None:
            port_cluster.append((port_from, port_to))
        # the rest pairs
        elif orient_new == orient_old:
            # if the ports are too spaced apart, initiate new cluster
            right_port = min(port_from, port_to, key=proj_ex)
            left_port = max(port_cluster[-1], key=proj_ex)
            if proj_ex(right_port) - right_port.width > proj_ex(left_port) + left_port.width:
                new_cluster = True
            else:
                port_cluster.append((port_from, port_to))
        else:
            new_cluster = True

        if new_cluster:
            port_clusters.append((port_cluster, orient_old))
            port_cluster = []
            port_cluster.append((port_from, port_to))
        orient_old = orient_new
    port_clusters.append((port_cluster, orient_old))
    return port_clusters
