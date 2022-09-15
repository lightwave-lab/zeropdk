from tabnanny import check
from typing import Callable, List, Optional, Tuple, Union
import pya
import klayout.db as kdb

import numpy as np
from numpy import pi, sqrt
from zeropdk.layout.geometry import rotate90, rotate
from zeropdk.types import GeneralLayer, PointLike
from zeropdk.klayout_helper import as_vector
from zeropdk.layout import insert_shape


class ZeroPDKDSimplePolygon(kdb.DSimplePolygon):
    """SimplePolygon with some added functionalities:
    - transform_and_rotate
    - clip
    - layout
    - layout_drc_exclude
    - resize
    - round_corners
    """

    def transform_and_rotate(
        self,
        center: kdb.DVector,
        ex: Optional[kdb.DVector] = None,
        ey: Optional[kdb.DVector] = None,
    ):
        """Rotates the polygon by ex (changes coordinates to cartesian coordinates defined by vector ex)
        and translates it by 'center'

        Example: if current polygon is a unit square with bottom-left corner at (0,0),
        then square.transform_and_rotate(DVector(0, 1), DVector(0, 1)) will
        rotate the square by 90 degrees and translate it by 1 y-unit.
        The new square's bottom-left corner will be at (-1, 1).

        Note: ex and ey need not be unitary.
        """
        if ex is None:
            ex = kdb.DVector(1, 0)
        if ey is None:
            ey = rotate90(ex)

        polygon_dpoints_transformed = [
            center.to_p() + p.x * ex + p.y * ey for p in self.each_point()
        ]
        self.assign(ZeroPDKDSimplePolygon(polygon_dpoints_transformed))
        return self

    Bounds = Tuple[float, float]

    def clip(
        self, x_bounds: Bounds = (-np.inf, np.inf), y_bounds: Bounds = (-np.inf, np.inf)
    ) -> "ZeroPDKDSimplePolygon":
        """Clips the polygon at four possible boundaries.
        The boundaries are tuples based on absolute coordinates and cartesian axes.
        This method is very powerful when used with transform_and_rotate.
        This assumes that the output polygon is convex.
        """
        Bounds = Tuple[float, float]
        # Reorder bounds, so check_within_bounds works.
        x_bounds = (np.min(x_bounds), np.max(x_bounds))
        y_bounds = (np.min(y_bounds), np.max(y_bounds))

        check_within_bounds: Callable[[PointLike], bool] = (
            lambda p: x_bounds[0] <= p.x
            and x_bounds[1] >= p.x
            and y_bounds[0] <= p.y
            and y_bounds[1] >= p.y
        )

        bounding_box = kdb.DBox(x_bounds[0], y_bounds[0], x_bounds[1], y_bounds[1])
        if not self.touches(bounding_box):  # no overlap between polygon and bounding box.
            self.set_points([])
            return self
        # Detect if polygon is completely within bounding box and return early
        p1, p2 = self.bbox().p1, self.bbox().p2
        if check_within_bounds(p1) and check_within_bounds(p2):
            return self

        # polygon_dpoints = list(self.each_point())
        polygon_dpoints: List[kdb.DPoint] = list()
        # Detect if any polygon edge crosses the bounding box.
        # If it doesn't, then it's fully outside the bounds.
        # Returns the box in this case
        crossed = False
        for edge in self.each_edge():
            clipped_edge: Optional[kdb.DEdge] = edge.clipped(bounding_box)
            polygon_dpoints.append(edge.p1)
            if clipped_edge:
                crossed = True
                polygon_dpoints.append(clipped_edge.p1)
                polygon_dpoints.append(clipped_edge.p2)
        if not crossed:
            self.assign(ZeroPDKDSimplePolygon(bounding_box))
            return self
        assert len(polygon_dpoints) > 2

        def intersect_left_boundary(
            p1: PointLike, p2: PointLike, x_bounds: Bounds, y_bounds: Bounds
        ) -> Optional[kdb.DPoint]:
            left_most, right_most = (p1, p2) if p1.x < p2.x else (p2, p1)
            bottom_most, top_most = (p1, p2) if p1.y < p2.y else (p2, p1)
            if left_most.x <= x_bounds[0] and right_most.x >= x_bounds[0]:
                # outside the box, on the left
                y_intersect = np.interp(
                    x_bounds[0],
                    [left_most.x, right_most.x],
                    [left_most.y, right_most.y],
                )
                if y_bounds[0] <= y_intersect and y_bounds[1] >= y_intersect:
                    return kdb.DPoint(float(x_bounds[0]), float(y_intersect))
            return None

        def intersect(
            p1: kdb.DPoint, p2: kdb.DPoint, x_bounds: Bounds, y_bounds: Bounds
        ) -> Tuple[List[kdb.DPoint], Optional[int]]:
            """Check if edge defined between p1 and p2 intersects any of the bounds."""
            intersect_list: List[kdb.DPoint] = list()
            last_intersect = None

            def rotate_bounds90(x_bounds, y_bounds, i_times):
                for _ in range(i_times):
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

        def boundary_vertex(edge_from: int, edge_to: int) -> kdb.DPoint:
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
            return kdb.DPoint(x, y)

        polygon_dpoints_clipped = list()
        previous_point = polygon_dpoints[-1]
        previous_intersect = None
        for point in polygon_dpoints:
            # compute new intersecting point and add to list
            intersected_points, last_intersect = intersect(
                previous_point, point, x_bounds, y_bounds
            )
            # The following statement is true if the edge between previous_point and point
            # crosses a boundary.
            if (
                previous_intersect is not None
                and last_intersect is not None
                and last_intersect != previous_intersect
                and check_within_bounds(point)
            ):
                # this means that we are entering the box at a different edge
                # need to add the edge points

                # this assumes a certain polygon orientation (clockwise)
                # assume points go clockwise, which means that
                # from edge 0 to 2, it goes through 1

                i = previous_intersect
                while i != last_intersect:
                    if self.inside(boundary_vertex(i, i + 1)):
                        polygon_dpoints_clipped.append(boundary_vertex(i, i + 1))
                    i = (i + 1) % 4
            polygon_dpoints_clipped.extend(intersected_points)
            previous_point = point
            if check_within_bounds(point):
                polygon_dpoints_clipped.append(point)
            elif (
                last_intersect is not None
            ):  # only set previous_intersect if going from inside to outside
                previous_intersect = last_intersect
        clipped_dpoly = ZeroPDKDSimplePolygon(polygon_dpoints_clipped)
        clipped_dpoly.compress(False)
        self.assign(clipped_dpoly)
        return self

    def layout(self, cell: kdb.Cell, layer: GeneralLayer):
        """Places polygon as a shape into a cell at a particular layer."""

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

    def resize(self, dx: float, dbu: float):
        """Resizes the polygon by a positive or negative quantity dx.
        Args:
            dx: float
            dbu: typically 0.001
        """

        dpoly = kdb.DPolygon(self)
        dpoly.size(dx, 5)
        dpoly = kdb.EdgeProcessor().simple_merge_p2p([dpoly.to_itype(dbu)], False, False, 1)
        dpoly = dpoly[0].to_dtype(dbu)  # kdb.DPolygon

        # Filter edges if they are too small
        points = list(dpoly.each_point_hull())
        new_points = list([points[0]])
        for i in range(0, len(points)):
            delta = points[i] - new_points[-1]
            if delta.length() > min(10 * dbu, abs(dx)):
                new_points.append(points[i])

        sdpoly = self.__class__(new_points)  # convert to SimplePolygon
        self.assign(sdpoly)
        return self

    def round_corners(self, radius: float, N: int):
        """Rounds the corners of the polygon.
        This only works if the polygon edges are longer than the radius.
        radius: (float) corner radius.
        N: (int) number of points in a full circle polygon interpolation.
        """

        dpoly = super().round_corners(radius, radius, N)
        self.assign(dpoly)
        return self

    def moved(self, dx_or_dpoint: Union[kdb.DVector, float], dy: Optional[float] = None):
        """Returns a new DSimplePolygon with its coordinates moved by given offset.
        The offset can be given by using either signature:
        - moved(v: DVector)
        - moved(dx: float, dy: float)
        """
        if isinstance(dx_or_dpoint, (kdb.DPoint, kdb.DVector)):
            dvector = as_vector(dx_or_dpoint)
            pya_dpoly = super().moved(dvector)
        elif dy is not None:
            pya_dpoly = super().moved(dx_or_dpoint, dy)
        else:
            raise TypeError(
                "Wrong function arguments. Expected either moved(v:DVector) or moved (dx:float, dy:float)"
            )
        zeropdk_dpoly = self.__class__()
        zeropdk_dpoly.assign(pya_dpoly)
        return zeropdk_dpoly


def patch_polygon():
    kdb.DSimplePolygon = ZeroPDKDSimplePolygon
    pya.DSimplePolygon = ZeroPDKDSimplePolygon
