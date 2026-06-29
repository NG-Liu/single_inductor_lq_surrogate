from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import LineString, box


DELETE_KEEP_OUT_GAP = 1.0
DELETE_WINDOW_LENGTH = 160.0


@dataclass(frozen=True)
class InductorParams:
    name: str
    r0: float
    n_turns: float
    width: float
    spacing: float
    left_bridge: float
    right_bridge: float

    @property
    def wv4(self) -> float:
        return self.width - 4.0

    @property
    def pitch(self) -> float:
        return self.width + self.spacing


def rotate_point(point: tuple[float, float], angle_deg: float) -> tuple[float, float]:
    x, y = point
    angle = math.radians(angle_deg)
    return x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)


def transform_point(point: tuple[float, float], center: tuple[float, float], angle_deg: float) -> tuple[float, float]:
    x, y = rotate_point(point, angle_deg)
    return x + center[0], y + center[1]


def polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(points, points[1:]))


def circular_spiral_points(params: InductorParams, samples: int | None = None) -> list[tuple[float, float]]:
    if samples is None:
        samples = max(360, int(params.n_turns * 160))
    b = params.pitch / (2.0 * math.pi)
    tmax = params.n_turns * 2.0 * math.pi
    return [
        (-(params.r0 + b * (tmax * i / (samples - 1))) * math.cos(tmax * i / (samples - 1)),
         -(params.r0 + b * (tmax * i / (samples - 1))) * math.sin(tmax * i / (samples - 1)))
        for i in range(samples)
    ]


def unit_from_center(point: tuple[float, float]) -> tuple[float, float]:
    x, y = point
    length = math.hypot(x, y)
    if length == 0:
        raise ValueError("Anchor is at the spiral center")
    return x / length, y / length


def rotate_vector(vector: tuple[float, float], angle_deg: float) -> tuple[float, float]:
    return rotate_point(vector, angle_deg)


def anchor_rect_spec(
    anchor: tuple[float, float],
    direction: tuple[float, float],
    length: float,
    width: float,
    inner_edge_offset: float = 0.0,
) -> tuple[float, float, float, float, float]:
    ax, ay = anchor
    ux, uy = direction
    cx = ax + ux * (inner_edge_offset + length / 2.0)
    cy = ay + uy * (inner_edge_offset + length / 2.0)
    angle = math.degrees(math.atan2(uy, ux))
    return cx, cy, length, width, angle


def rotated_rect(cx: float, cy: float, length: float, width: float, angle_deg: float):
    rect = box(cx - length / 2.0, cy - width / 2.0, cx + length / 2.0, cy + width / 2.0)
    if angle_deg:
        rect = affinity.rotate(rect, angle_deg, origin=(cx, cy), use_radians=False)
    return rect


def strip_from_points(points: list[tuple[float, float]], width: float):
    return LineString(points).buffer(width / 2.0, cap_style="flat", join_style="mitre", mitre_limit=5.0)


def polygon_parts(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return [p for p in geom.geoms if not p.is_empty]
    if geom.geom_type == "GeometryCollection":
        return [p for g in geom.geoms for p in polygon_parts(g)]
    return []


def exterior_points(poly) -> list[tuple[float, float]]:
    pts = list(poly.exterior.coords)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def rectangle_location_from_center(cx: float, cy: float, width: float, height: float) -> tuple[float, float]:
    return cx - width / 2.0, cy - height / 2.0

