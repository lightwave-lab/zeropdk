import pya
import klayout.db as kdb
from zeropdk import klayout_extend  # noqa

import numpy as np
from numpy import pi, sqrt
from zeropdk.layout.geometry import rotate90, rotate


def patch_simple_polygon(backend):
    class _SimplePolygon(backend.DSimplePolygon):
        """SimplePolygon with some added functionalities:
        - transform_and_rotate
        - clip
        - layout
        - layout_drc_exclude
        - resize
        - round_corners
        """

        def transform_and_rotate(self, center, ex=None):
            """Translates the polygon by 'center' and rotates by the 'ex' orientation.

            Example: if current polygon is a unit square with bottom-left corner at (0,0),
            then square.transform_and_rotate(DPoint(0, 1), DVector(0, 1)) will
            rotate the square by 90 degrees and translate it by 1 y-unit.
            The new square's bottom-left corner will be at (-1, 1).
            """
            if ex is None:
                ex = backend.DPoint(1, 0)
            ey = rotate90(ex)

            polygon_dpoints_transformed = [center + p.x * ex + p.y * ey for p in self.each_point()]
            self.assign(_SimplePolygon(polygon_dpoints_transformed))
            return self

        def clip(self, x_bounds=(-np.inf, np.inf), y_bounds=(-np.inf, np.inf)):
            """Clips the polygon at four possible boundaries.
            The boundaries are tuples based on absolute coordinates and cartesian axes.
            This method is very powerful when used with transform_and_rotate.
            """
            # Add points exactly at the boundary, so that the filter below works.
            x_bounds = (np.min(x_bounds), np.max(x_bounds))
            y_bounds = (np.min(y_bounds), np.max(y_bounds))

            check_within_bounds = (
                lambda p: x_bounds[0] <= p.x
                and x_bounds[1] >= p.x
                and y_bounds[0] <= p.y
                and y_bounds[1] >= p.y
            )

            def intersect_left_boundary(p1, p2, x_bounds, y_bounds):
                left_most, right_most = (p1, p2) if p1.x < p2.x else (p2, p1)
                bottom_most, top_most = (p1, p2) if p1.y < p2.y else (p2, p1)
                if left_most.x < x_bounds[0]:
                    # intersection only if right_most crosses x_bound[0]
                    if right_most.x > x_bounds[0]:
                        # outside the box, on the left
                        y_intersect = np.interp(
                            x_bounds[0],
                            [left_most.x, right_most.x],
                            [left_most.y, right_most.y],
                        )
                        if y_bounds[0] < y_intersect and y_bounds[1] > y_intersect:
                            return backend.DPoint(float(x_bounds[0]), float(y_intersect))
                return None

            def intersect(p1, p2, x_bounds, y_bounds):
                intersect_list = list()
                last_intersect = None

                def rotate_bounds90(x_bounds, y_bounds, i_times):
                    for i in range(i_times):
                        x_bounds, y_bounds = (
                            (-y_bounds[1], -y_bounds[0]),
                            (x_bounds[0], x_bounds[1]),
                        )
                    return x_bounds, y_bounds

                for i in range(4):
                    p1i, p2i = rotate(p1, i * pi / 2), rotate(p2, i * pi / 2)
                    x_boundsi, y_boundsi = rotate_bounds90(x_bounds, y_bounds, i)
                    p = intersect_left_boundary(p1i, p2i, x_boundsi, y_boundsi)
                    if p is not None:
                        last_intersect = i
                        intersect_list.append(rotate(p, -i * pi / 2))
                return intersect_list, last_intersect

            polygon_dpoints_clipped = list()
            polygon_dpoints = list(self.each_point())

            def boundary_vertex(edge_from, edge_to):
                # left edge:0, top edge:1, right edge:2, bottom edge:3
                # returns the vertex between two edges
                assert abs(edge_from - edge_to) == 1
                if edge_from % 2 == 0:
                    vertical_edge = edge_from
                    horizontal_edge = edge_to
                else:
                    vertical_edge = edge_to
                    horizontal_edge = edge_from
                x = x_bounds[(vertical_edge // 2) % 2]
                y = y_bounds[(1 - (horizontal_edge - 1) // 2) % 2]
                return backend.DPoint(x, y)

            # Rotate point list so we can start from a point inside
            # (helps the boundary_vertex algorithm)
            for idx, point in enumerate(polygon_dpoints):
                if check_within_bounds(point):
                    break
            else:
                # polygon was never within bounds
                # this can only happen if boundaries are finite
                # return boundary vertices
                boundary_vertices = [boundary_vertex(i, i - 1) for i in range(4, 0, -1)]
                self.assign(_SimplePolygon(boundary_vertices))
                return self

            idx += 1  # make previous_point below already be inside
            polygon_dpoints = polygon_dpoints[idx:] + polygon_dpoints[:idx]

            previous_point = polygon_dpoints[-1]
            previous_intersect = None
            for point in polygon_dpoints:
                # compute new intersecting point and add to list
                intersected_points, last_intersect = intersect(
                    previous_point, point, x_bounds, y_bounds
                )
                if (
                    previous_intersect is not None
                    and last_intersect is not None
                    and last_intersect != previous_intersect
                ):
                    if check_within_bounds(point):
                        # this means that we are entering the box at a different edge
                        # need to add the edge points

                        # this assumes a certain polygon orientation
                        # assume points go clockwise, which means that
                        # from edge 0 to 2, it goes through 1
                        i = previous_intersect
                        while i % 4 != last_intersect:
                            polygon_dpoints_clipped.append(boundary_vertex(i, i + 1))
                            i = i + 1
                polygon_dpoints_clipped.extend(intersected_points)
                if check_within_bounds(point):
                    polygon_dpoints_clipped.append(point)
                previous_point = point
                if last_intersect is not None:
                    previous_intersect = last_intersect
            self.assign(_SimplePolygon(polygon_dpoints_clipped))
            return self

        def layout(self, cell, layer):
            """ Places polygon as a shape into a cell at a particular layer."""
            from zeropdk.layout import insert_shape

            return insert_shape(cell, layer, self)

        def layout_drc_exclude(self, cell, drclayer, ex):
            """Places a drc exclude square at every corner.
            A corner is defined by an outer angle greater than 85 degrees (conservative)
            """
            from zeropdk.layout.polygons import layout_square

            if drclayer is not None:
                points = list(self.each_point())
                assert len(points) > 3
                prev_delta = points[-1] - points[-2]
                prev_angle = np.arctan2(prev_delta.y, prev_delta.x)
                for i in range(len(points)):
                    delta = points[i] - points[i - 1]
                    angle = np.arctan2(delta.y, delta.x)
                    if delta.y == 0 or delta.x == 0:
                        thresh_angle = pi / 2
                    else:
                        thresh_angle = pi * 85 / 180
                    delta_angle = angle - prev_angle
                    delta_angle = abs(((delta_angle + pi) % (2 * pi)) - pi)
                    if delta_angle > thresh_angle:
                        layout_square(cell, drclayer, points[i - 1], 0.1, ex)
                    prev_delta, prev_angle = delta, angle

        def resize(self, dx, dbu):
            """Resizes the polygon by a positive or negative quantity dx.
            Args:
                dbu: typically 0.001
            """

            # TODO Very klayout specific

            dpoly = backend.DPolygon(self)
            dpoly.size(dx, 5)
            dpoly = backend.EdgeProcessor().simple_merge_p2p([dpoly.to_itype(dbu)], False, False, 1)
            dpoly = dpoly[0].to_dtype(dbu)  # backend.DPolygon

            def norm(p):
                return sqrt(p.x ** 2 + p.y ** 2)

            # Filter edges if they are too small
            points = list(dpoly.each_point_hull())
            new_points = list([points[0]])
            for i in range(0, len(points)):
                delta = points[i] - new_points[-1]
                if norm(delta) > min(10 * dbu, abs(dx)):
                    new_points.append(points[i])

            sdpoly = self.__class__(new_points)  # convert to SimplePolygon
            self.assign(sdpoly)
            return self

        def round_corners(self, radius, N):
            """ This only works if the polygon edges are longer than the radius."""

            dpoly = super().round_corners(radius, radius, N)
            self.assign(dpoly)
            return self

        def moved(self, dx_or_dpoint, dy=None):
            if isinstance(dx_or_dpoint, (backend.DPoint, backend.DVector)):
                dx_or_dpoint = dx_or_dpoint.x
                dy = dx_or_dpoint.y
            pya_dpoly = super().moved(dx_or_dpoint, dy)
            siepic_dpoly = self.__class__()
            siepic_dpoly.__dict__.update(pya_dpoly)
            return siepic_dpoly

    backend.DSimplePolygon = _SimplePolygon


patch_simple_polygon(kdb)
patch_simple_polygon(pya)
