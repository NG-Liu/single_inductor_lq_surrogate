from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .geometry import (
    DELETE_KEEP_OUT_GAP,
    DELETE_WINDOW_LENGTH,
    InductorParams,
    anchor_rect_spec,
    circular_spiral_points,
    exterior_points,
    polygon_parts,
    polyline_length,
    rectangle_location_from_center,
    rotate_vector,
    rotated_rect,
    strip_from_points,
    transform_point,
    unit_from_center,
)


LAYERS_FDL = """\
MetalLayer(name='m6', zStart=742.028, thickness=1.25, er=1.0, eLossTan=0.0, RPSQ=0.032, mur=1.0, mLossTan=0.0, material='m6_3', isGND=False, isVia=False, isSheet=False, priority=1, color='#FFA07A', layernum=0)
MetalLayer(name='v5', zStart=741.158, thickness=0.87, er=1.0, eLossTan=0.0, via_resistance={'EQL': {'other': [16992.19, 's/m'], '40': 0.032}}, mur=1.0, mLossTan=0.0, material='v5_2', isGND=False, isVia=True, isSheet=False, priority=1, color='#FF4500', layernum=0)
MetalLayer(name='m5', zStart=738.158, thickness=3.0, er=1.0, eLossTan=0.0, RPSQ=0.0062, mur=1.0, mLossTan=0.0, material='m5_3', isGND=False, isVia=False, isSheet=False, priority=1, color='#2F4F4F', layernum=0)
MetalLayer(name='v4', zStart=735.158, thickness=3.0, er=1.0, eLossTan=0.0, via_resistance={'EQL': {'other': [4615384.62, 's/m'], '5': 0.026}}, mur=1.0, mLossTan=0.0, material='v4_1', isGND=False, isVia=True, isSheet=False, priority=1, color='#FFDAB9', layernum=0)
MetalLayer(name='m4', zStart=732.158, thickness=3.0, er=1.0, eLossTan=0.0, RPSQ=0.0062, mur=1.0, mLossTan=0.0, material='m4_4', isGND=False, isVia=False, isSheet=False, priority=1, color='#A52A2A', layernum=0)
MetalLayer(name='v3', zStart=729.453, thickness=2.705, er=1.0, eLossTan=0.0, via_resistance={'EQL': {'other': [1202222.22, 's/m'], '5': 0.09}}, mur=1.0, mLossTan=0.0, material='v3_1', isGND=False, isVia=True, isSheet=False, priority=1, color='#00FF7F', layernum=0)
MetalLayer(name='m3', zStart=729.258, thickness=0.195, er=1.0, eLossTan=0.0, RPSQ=0.188, mur=1.0, mLossTan=0.0, material='m3_4', isGND=False, isVia=False, isSheet=False, priority=1, color='#1E90FF')
MetalLayer(name='v2', zStart=729.158, thickness=3.0, er=1.0, eLossTan=0.0, via_resistance={'EQL': {'other': [1333333.33, 's/m'], '5': 0.09}}, mur=1.0, mLossTan=0.0, material='v2_1', isGND=False, isVia=True, isSheet=False, priority=1, color='#FFA500', layernum=0)
MetalLayer(name='m2', zStart=728.608, thickness=0.55, er=1.0, eLossTan=0.0, RPSQ=0.07, mur=1.0, mLossTan=0.0, material='m2_7', isGND=False, isVia=False, isSheet=False, priority=1, color='#CD853F', layernum=0)
MetalLayer(name='v1', zStart=725.008, thickness=3.6, er=1.0, eLossTan=0.0, conductivity=58000000.0, mur=1.0, mLossTan=0.0, material='Copper', isGND=False, isVia=True, isSheet=False, priority=1, color='#1E90FF')
MetalLayer(name='m1', zStart=725.0, thickness=0.008, er=1.0, eLossTan=0.0, conductivity=58000000.0, mur=1.0, mLossTan=0.0, material='Copper', isGND=False, isVia=False, isSheet=False, priority=1, color='#FF2B81')
MetalLayer(name='GND', zStart=0, thickness=0, er=1.0, eLossTan=0.0, conductivity=1e+30, mur=1.0, mLossTan=0.0, material='pec', isGND=True, isVia=False, isSheet=False, priority=1, layernum=0)
Layer(name='Die18', zStart=744.078, thickness='infinity', er=1.0, eLossTan=0.0, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die18_1_1')
Layer(name='Die17', zStart=743.678, thickness=0.4, er=7.0, eLossTan=0.004, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die17_1_1')
Layer(name='Die16', zStart=742.028, thickness=1.65, er=4.0, eLossTan=0.01, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die16_1_1')
Layer(name='Die15', zStart=741.628, thickness=0.4, er=7.0, eLossTan=0.004, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die15_1_1')
Layer(name='Die14', zStart=741.228, thickness=0.4, er=4.0, eLossTan=0.01, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die14_1_1')
Layer(name='Die13', zStart=741.158, thickness=0.07, er=7.0, eLossTan=0.004, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die13_1_1')
Layer(name='Die12', zStart=738.258, thickness=2.9, er=4.0, eLossTan=0.01, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die12_1_1')
Layer(name='Die11', zStart=738.158, thickness=0.1, er=7.0, eLossTan=0.004, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die11_1_1')
Layer(name='Die10', zStart=735.258, thickness=2.9, er=4.0, eLossTan=0.01, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die10_1_1')
Layer(name='Die9', zStart=735.158, thickness=0.1, er=7.0, eLossTan=0.004, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die9_1_1')
Layer(name='Die8', zStart=732.258, thickness=2.9, er=4.0, eLossTan=0.01, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die8_1_1')
Layer(name='Die7', zStart=732.158, thickness=0.1, er=7.0, eLossTan=0.004, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die7_1_1')
Layer(name='Die6', zStart=729.258, thickness=2.9, er=4.0, eLossTan=0.01, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die6_1_1')
Layer(name='Die5', zStart=729.158, thickness=0.1, er=7.0, eLossTan=0.004, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die5_2_1')
Layer(name='Die4', zStart=728.608, thickness=0.55, er=4.0, eLossTan=0.01, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die4_2_1')
Layer(name='Die3', zStart=725.008, thickness=3.6, er=4.0, eLossTan=0.01, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die3_2_1')
Layer(name='Die2', zStart=725.0, thickness=0.008, er=4.0, eLossTan=0.01, conductivity=0.0, mur=1.0, mLossTan=0.0, material='Die2_2_1')
Layer(name='Die1', zStart=0.0, thickness=725.0, er=11.9, eLossTan=0.0, resistivity=4000.0, mur=1.0, mLossTan=0.0, material='Die1_5_3_8_2_2')
"""


@dataclass(frozen=True)
class SingleInductorSpec:
    name: str = "L1"
    center: tuple[float, float] = (0.0, 0.0)
    rotation_deg: float = 0.0


def fmt_num(value: float, digits: int = 4) -> str:
    if abs(value) < 0.5 * 10 ** (-digits):
        value = 0.0
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def fmt_points(points, digits: int = 4) -> str:
    return "[" + ", ".join(f"({fmt_num(x, digits)}, {fmt_num(y, digits)})" for x, y in points) + "]"


def operation_fdl(output_name: str) -> str:
    return (
        "op_cond0 = Operation(Frequency={'Enabled': True, 'Linear': [[3.0, 'GHz'], [4.5, 'GHz'], [0.5, 'GHz']]}, "
        "AccuracyLevel='IC-Standard', MetalMode='3D', ViaMode='3D', MeshType='Triangle', "
        f"SolverType='Default', ExcitationType='Voltage', OutputfileName='{output_name}', "
        "Sweep={}, CharImpedance=(50+0j), ThreadNumber=4, Ports=[\"P1\", \"P2\"], "
        "GroundPorts=[], MeshOperation={'Value': [-1, -1, -1], 'Type': 'SegNum'}, "
        "UseCache=True, PrintCurrents=False, Tasks=4, MaxNumberofRefinement=9, SpecialViaDel=True, "
        "MeshDeltaS=0.02, RAMLimit=1.0)"
    )


def polygon_spiral_points(params: InductorParams, sides: int) -> list[tuple[float, float]]:
    steps = max(1, int(round(params.n_turns * sides)))
    b = params.pitch / (2.0 * math.pi)
    tmax = params.n_turns * 2.0 * math.pi
    pts = []
    for i in range(steps + 1):
        t = tmax * i / steps
        r = params.r0 + b * t
        pts.append((-r * math.cos(t), -r * math.sin(t)))
    circular_len = polyline_length(circular_spiral_points(params))
    poly_len = polyline_length(pts)
    if poly_len > 1e-9:
        scale = circular_len / poly_len
        pts = [(x * scale, y * scale) for x, y in pts]
    return pts


def endpoint_direction(points: list[tuple[float, float]], params: InductorParams) -> tuple[float, float]:
    frac = params.n_turns - math.floor(params.n_turns)
    if abs(frac - 0.25) < 1e-6:
        return 0.0, -1.0
    if abs(frac - 0.75) < 1e-6:
        return 0.0, 1.0
    if abs(frac - 0.5) < 1e-6:
        return 1.0, 0.0
    end = points[-1]
    prev = points[-2]
    length = math.hypot(end[0] - prev[0], end[1] - prev[1]) or 1.0
    return (end[0] - prev[0]) / length, (end[1] - prev[1]) / length


def bridge_outer_point(spec: tuple[float, float, float, float, float], outer: str = "right") -> tuple[float, float]:
    cx, cy, length, _width, angle = spec
    theta = math.radians(angle)
    sign = 1.0 if outer == "right" else -1.0
    return cx + sign * math.cos(theta) * length / 2.0, cy + sign * math.sin(theta) * length / 2.0


def add_rectangle(lines: list[str], objects: list[str], obj_index: int, name: str, layer: str, spec, width_override=None) -> int:
    cx, cy, length, width, angle = spec
    width = width_override if width_override is not None else width
    var = f"RectangleObj{obj_index}"
    rect_x, rect_y = rectangle_location_from_center(cx, cy, length, width)
    transform = "[]" if abs(angle) < 1e-9 else f"[{{'Rotate': [{angle:.4f}, ({fmt_num(cx)}, {fmt_num(cy)})]}}]"
    lines.append(
        f"{var} = Rectangle(location=({fmt_num(rect_x)}, {fmt_num(rect_y)}), width={length:.4f}, "
        f"height={width:.4f}, name='{name}', metalLayer='{layer}', pins=[], pins_location=[], vias=[], net=\"\", transform={transform})"
    )
    objects.append(var)
    return obj_index + 1


def add_pin(lines: list[str], ext_pins: list[str], name: str, point: tuple[float, float], layer: str) -> None:
    x, y = point
    half = 4.0
    lines.append(
        f"Pin(name='{name}',side='Top', location={{'Shape': 'Rectangle', 'Prop': "
        f"{{'y': {fmt_num(y - half)}, 'x': {fmt_num(x - half)}, 'width': 8.0000, 'height': 8.0000}}}}, "
        f"metalLayer='{layer}', net=\"\", transform=[], CharImpedance=50+0j)"
    )
    ext_pins.append(f"{name}:Top")


def build_geometry(params: InductorParams, spec: SingleInductorSpec, sides: int) -> dict[str, object]:
    local = polygon_spiral_points(params, sides)
    points = [transform_point(p, spec.center, spec.rotation_deg) for p in local]
    start_dir = rotate_vector(unit_from_center(local[0]), spec.rotation_deg)
    end_dir = rotate_vector(endpoint_direction(local, params), spec.rotation_deg)
    start, end = points[0], points[-1]
    delete_width = 3.0 * params.width
    keepout_width = delete_width / 2.0
    delete_spec = anchor_rect_spec(start, start_dir, DELETE_WINDOW_LENGTH, delete_width, params.width / 2.0 + DELETE_KEEP_OUT_GAP)
    keepout_spec = anchor_rect_spec(start, start_dir, params.width, keepout_width, -params.width / 2.0)
    left_bridge_spec = anchor_rect_spec(start, start_dir, params.left_bridge, params.width, -params.width / 2.0)
    right_bridge_spec = anchor_rect_spec(end, end_dir, params.right_bridge, params.width, -params.width / 2.0)
    delete_mask = rotated_rect(*delete_spec).difference(rotated_rect(*keepout_spec))
    return {
        "points": points,
        "m5_parts": polygon_parts(strip_from_points(points, params.width).difference(delete_mask)),
        "v4_parts": polygon_parts(strip_from_points(points, params.wv4).difference(delete_mask)),
        "left_bridge_spec": left_bridge_spec,
        "right_bridge_spec": right_bridge_spec,
    }


def write_fdl(output_path: Path, params: InductorParams, sides: int = 12) -> None:
    spec = SingleInductorSpec()
    geom = build_geometry(params, spec, sides)
    variables = (
        f"Variables(var=[{{'L1_r0': {params.r0:.4f}}}, {{'N1': {params.n_turns:.4f}}}, "
        f"{{'L1_sides': {float(sides):.4f}}}, {{'L1_W': {params.width:.4f}}}, "
        f"{{'L1_S': {params.spacing:.4f}}}, {{'L1_left_bridge': {params.left_bridge:.4f}}}, "
        f"{{'L1_right_bridge': {params.right_bridge:.4f}}}])"
    )
    lines = [
        "# Generated by single_inductor_lq_surrogate",
        "# Standalone polygonal inductor + left/right bridge FDL.",
        "FDL_type('UltraEM')",
        "",
        "geom_unit('um')",
        "",
        variables,
        "",
        operation_fdl(output_path.stem),
        "",
        LAYERS_FDL.rstrip(),
        "",
    ]
    objects: list[str] = []
    ext_pins: list[str] = []
    obj_index = 0
    for layer, parts in (("m5", geom["m5_parts"]), ("v4", geom["v4_parts"])):
        for part_index, poly in enumerate(parts, start=1):
            var = f"PolygonObj{obj_index}"
            lines.append(
                f"{var} = Polygon(location={fmt_points(exterior_points(poly))}, name='{spec.name}_{layer}_cut_{part_index}', "
                f"metalLayer='{layer}', pins=[], pins_location=[], vias=[], net=\"\")"
            )
            objects.append(var)
            obj_index += 1
    obj_index = add_rectangle(lines, objects, obj_index, "L1_LeftBridge_m5", "m5", geom["left_bridge_spec"], params.width)
    obj_index = add_rectangle(lines, objects, obj_index, "L1_RightBridge_m5", "m5", geom["right_bridge_spec"], params.width)
    obj_index = add_rectangle(lines, objects, obj_index, "L1_RightBridge_v4", "v4", geom["right_bridge_spec"], params.wv4)
    obj_index = add_rectangle(lines, objects, obj_index, "L1_RightBridge_m4", "m4", geom["right_bridge_spec"], params.width)
    var = f"PathObj{obj_index}"
    lines.append(
        f"{var} = Path(location={fmt_points(geom['points'])}, width={params.width:.4f}, path_type='butt', "
        "corner_type='miter', name='L1_m4_path', metalLayer='m4', pins=[], pins_location=[], vias=[], net=\"\")"
    )
    objects.append(var)
    add_pin(lines, ext_pins, "P1", bridge_outer_point(geom["left_bridge_spec"], "right"), "m5")
    add_pin(lines, ext_pins, "P2", bridge_outer_point(geom["right_bridge_spec"], "right"), "m5")
    lines.extend(["", f"Design_0 = Cell(name='single_inductor_geometry', ext_pins={ext_pins!r}, objects=[{', '.join(objects)}])", "", "run(Design_0, op_cond0)", ""])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

