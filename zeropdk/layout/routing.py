import pya
import os
import sys
import logging
from contextlib import contextmanager
# from siepic_ebeam_pdk import EBEAM_TECH
from zeropdk.layout.geometry import rotate90, \
    manhattan_intersection, \
    cluster_ports
from zeropdk.layout.waveguides import layout_waveguide

logger = logging.getLogger()


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


WAVEGUIDE_RADIUS = 10
WAVEGUIDE_WIDTH = 0.5


def layout_ebeam_waveguide_from_points(cell, points_list, radius=None, width=None):
    """ Takes a list of points and calls SiEPIC Waveguide Pcell
        The points_list should be a rough shape of the waveguide.
        The points_list must be a manhattan path!
        This function will create a smooth waveguide by rounding the trace
        at every corner with a particular radius.

        For example, if points_list has three points forming a square of size
        R, then the output will be a 90-degree arc of radius R.
    """
    from math import floor
    TECHNOLOGY = EBEAM_TECH
    if radius is None:
        radius = WAVEGUIDE_RADIUS
    if width is None:
        width = WAVEGUIDE_WIDTH
    for point in points_list:
        point.x = floor(point.x * 1000) / 1000
        point.y = floor(point.y * 1000) / 1000

    for i in range(0, len(points_list) - 1):
        """
        Calculate the x distance and the y distance to the next point.
        Get the max of the above two numbers
        Set the other number to zero
        """
        posx = abs(points_list[i + 1].x - points_list[i].x)
        posy = abs(points_list[i + 1].y - points_list[i].y)
        if abs(points_list[i + 1].x - points_list[i].x) > 0 and abs(points_list[i + 1].y - points_list[i].y) > 0:
            if posx < posy:
                points_list[i + 1].x = points_list[i].x
            else:
                points_list[i + 1].y = points_list[i].y

    wg_dpath = pya.DPath(points_list, 0.5)
    layout = cell.layout()
    with suppress_stdout():
        wg_cell = layout.create_cell("Waveguide", TECHNOLOGY['technology_name'],
                                     {"path": wg_dpath,
                                      "radius": radius,
                                      "width": width,
                                      "layers": ['Si'],
                                      "widths": [width],
                                      "offsets": [0]})

    layerSi = layout.layer(TECHNOLOGY['Si'])
    # let's just get the shapes
    cell.shapes(layerSi).insert(wg_cell.shapes(layerSi))

    layout.delete_cell(wg_cell.cell_index())

    return cell


def ensure_layer(layout, layer):
    if isinstance(layer, pya.LayerInfo):
        return layout.layer(layer)
    elif isinstance(layer, type(1)):
        return layer
    else:
        logger.error(f"{layer} not recognized")
        return


def common_layout_manhattan_traces(cell, layer1, layer2, layervia, via_cell_placer,
                                   path, ex, initiate_with_via=False):
    """ Lays out a manhattan trace, potentially with vias

        Args:
            layer1 and layer2 are given to layout.LayerInfo(layer), generally
                layer2 is on top
            via_cell_placer: returns a cell when called with
                via_cell_placer(parent_cell, pya.DPoint origin, width, layer1, layer2, layervia, ex)
            path: list of tuples containing necessary info ((x, y) or pya.DPoint, layer, width)

        Returns:
            path

        Algorithm places a via when there is a change of layers. To terminate with a via,
        have the last layer be different than the penultimate one.
    """

    assert isinstance(ex, (pya.DPoint, pya.DVector))
    ey = rotate90(ex)

    first_point, _, first_width = path[0]
    if initiate_with_via:
        via_cell_placer(cell, first_point, first_width,
                        layer1, layer2, layervia, ex)

    points_list = list()
    widths_list = list()
    _, previous_layer, _ = path[0]
    layout = cell.layout()

    for point, layer, width in path:
        if isinstance(point, tuple):  # point are (x, y) coordinates
            x, y = point
            point = x * ex + y * ey
        else:
            assert isinstance(point, (pya.DPoint, pya.DVector))
            if isinstance(point, pya.DVector):
                point = pya.DPoint(point)

        if layer == previous_layer:
            points_list.append(point)  # store points
            widths_list.append(width)
        else:  # time to place a via and layout
            points_list.append(point)
            widths_list.append(width)
            layout_waveguide(cell, ensure_layer(layout, previous_layer),
                             points_list, widths_list, smooth=True)

            via_cell_placer(cell, point, width, layer1, layer2, layervia, ex)

            # delete all but the last point
            del points_list[:-1]
            del widths_list[:-1]
        previous_layer = layer

    # layout last trace
    if len(points_list) >= 2:
        layout_waveguide(cell, ensure_layer(layout, previous_layer),
                         points_list, widths_list, smooth=True)

    return path


def layout_manhattan_traces(cell, path, ex):

    def via_cell_placer(*args, **kwargs):
        pass

    return common_layout_manhattan_traces(cell, None, None, None, via_cell_placer,
                                          path, ex, initiate_with_via=False)


def connect_ports_L(cell, cplayer, ports_from, ports_to, ex):
    ''' Connects ports ports_from to ports_to, always leaving vertically'''

    ey = rotate90(ex)
    for port_from, port_to in zip(ports_from, ports_to):
        assert port_from.direction == ey or port_from.direction == -ey
        o_y = ey if port_to.position * ey > port_from.position * ey else -ey
        o_x = ex if port_to.position * ex > port_from.position * ex else -ex

        middle_point = manhattan_intersection(port_from.position, port_to.position, ex)
        layout_waveguide(cell, ensure_layer(cell.layout(), cplayer), [
                         port_from.position, middle_point + port_to.width * 0.5 * o_y], port_from.width)
        layout_waveguide(cell, ensure_layer(cell.layout(), cplayer), [
                         middle_point - port_from.width * 0.5 * o_x, port_to.position], port_to.width)


def compute_paths_from_clusters(ports_clusters, layer, ex, pitch=None, middle_taper=False, initial_height=0):
    """
    provide a pitch for optical waveguides. electrical waveguides are figured
    out automatically.
    path: list of tuples containing necessary info (pya.DPoint, layer, width)
    """

    Z = 0
    S = 1
    ey = rotate90(ex)

    paths = []

    for ports_cluster, orientation in ports_clusters:
        assert orientation in (Z, S)

        # start from the lowest height Z trace
        height = initial_height
        if orientation == S:
            ports_iterator = list(iter(ports_cluster))
        elif orientation == Z:
            ports_iterator = list(reversed(ports_cluster))

        is_to_top = is_to_bottom = False
        # check which row is on the top:
        for port_from, port_to in ports_iterator:
            if (port_to.position - port_from.position) * ey > 0:
                is_to_top = True or is_to_top
            else:
                is_to_bottom = True or is_to_bottom

        assert not (is_to_bottom and is_to_top)  # they can't both be true

        if is_to_top:
            offset_port_from = max([port_from.position * ey for port_from, _ in ports_iterator])
        else:
            offset_port_from = min([port_from.position * ey for port_from, _ in ports_iterator])

        for port_from, port_to in ports_iterator:

            # # Make port_from be the one with largest width
            # if port_from.width < port_to.width:
            #     port_from, port_to = port_to, port_from

            P0 = port_from.position  # + port_from.direction * port_from.width / 2
            P3 = port_to.position  # + port_to.direction * port_to.width / 2

            if pitch is None:
                new_pitch = max(port_from.width, port_to.width) * 1.5
            else:
                new_pitch = max(max(port_from.width, port_to.width), pitch)

            height += new_pitch
            new_height = height + abs(offset_port_from - P0 * ey)
            paths.append(append_Z_trace_vertical([(P0, layer, port_from.width)],
                                                 (P3, layer, port_to.width),
                                                 new_height, ex, middle_taper=middle_taper))
    return paths


def bus_route_Z(cell, ports_from, ports_to, ex, pitch=WAVEGUIDE_RADIUS, radius=WAVEGUIDE_RADIUS):
    port_clusters = cluster_ports(ports_from, ports_to, ex)
    paths = compute_paths_from_clusters(port_clusters, None, ex, pitch)

    for trace_path in paths:
        path = [point for point, _, _ in trace_path]
        layout_ebeam_waveguide_from_points(cell, path, radius)


def append_Z_trace_vertical(path, new_point, height, ex, middle_layer=None, middle_taper=False):
    """ Adds new_point to the path list plus TWO Z or S manhattan interesections.
    Args:
        path: list of tuples containing necessary info (pya.DPoint, layer, width)
        new_point: tuple ((x, y) or pya.DPoint, layer, width)
        height: y-coordinate of where to place the inner point,
            from 0 to abs(new_point.y - path.y)
        ex: orientation of ports
        middle_layer (optional): layer of middle trace

    """

    assert len(path) > 0

    ey = rotate90(ex)

    P0, l0, w0 = path[-1]
    P3, l3, w3 = new_point

    height = abs(height)
    # assert height <= abs(P0 * ey - P3 * ey)

    # Invert sign of height if P3 is below P0
    if P3 * ey < P0 * ey:
        height = -height

    P1 = P0 + height * ey
    P2 = P1 * ey * ey + P3 * ex * ex

    # selecting middle_layer
    if middle_layer is None:
        l1, l2 = l0, l3
    else:
        l1 = l2 = middle_layer
    # lmid defined below

    # selecting middle widths
    w1, w2 = w0, w3
    if (P2 - P1).norm() <= w1 + w2:
        w1 = w2 = min(w1, w2)
    if w1 < w2:
        wmid = w1
        lmid = l1
    else:
        wmid = w2
        lmid = l2

    path.append((P1, l1, w1))

    # move P2 a little bit to avoid acute corners
    delta_w = (w2 - w1) / 2
    P2 += delta_w * ey

    Pmid = (P1 + P2) / 2

    if (P1 - P2).norm() <= max(w1, w2):
        if (P3 - P2) * ey > max(w1, w2) * 3:
            path.append((P2 + ey * max(w1, w2) * 3, l2, w2))
        else:
            path.append((P3 - ey * max(w1, w2) * 0.1, l3, w3))
    else:
        if middle_taper:
            path.append((Pmid, lmid, wmid))
        path.append((P2, l2, w2))
    path.append(new_point)
    return path
