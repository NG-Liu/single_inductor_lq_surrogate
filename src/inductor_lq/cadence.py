from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from shapely.affinity import rotate as shp_rotate
from shapely.geometry import LineString, MultiPolygon, Polygon


CADENCE_LAYER_MAP = {
    "m1": "M1",
    "m2": "M2",
    "m3": "M3",
    "m4": "M4",
    "m5": "M5",
    "m6": "M6",
    "v1": "V1",
    "v2": "V2",
    "v3": "V3",
    "v4": "V4",
    "v5": "V5",
}


@dataclass
class Shape:
    layer: str
    points: list[tuple[float, float]]


@dataclass
class Pin:
    name: str
    layer: str
    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.width / 2.0, self.y + self.height / 2.0


def _literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_literal(item) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_literal(item) for item in node.elts)
    if isinstance(node, ast.Dict):
        return {_literal(key): _literal(value) for key, value in zip(node.keys, node.values)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_literal(node.operand)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _literal(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _literal(node.left) + _literal(node.right)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
        return _literal(node.left) - _literal(node.right)
    if isinstance(node, ast.Name):
        if node.id == "True":
            return True
        if node.id == "False":
            return False
        if node.id == "None":
            return None
        return node.id
    raise ValueError(f"Unsupported literal node: {ast.dump(node, include_attributes=False)}")


def _call_name(node: ast.Call) -> str | None:
    return node.func.id if isinstance(node.func, ast.Name) else None


def _strip_closing(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return points[:-1] if len(points) > 1 and points[0] == points[-1] else points


def _rect_points(location: tuple[float, float], width: float, height: float) -> list[tuple[float, float]]:
    x0, y0 = location
    return [(x0, y0), (x0 + width, y0), (x0 + width, y0 + height), (x0, y0 + height)]


def _rotate_points(points: list[tuple[float, float]], angle: float, origin: tuple[float, float]) -> list[tuple[float, float]]:
    rotated = shp_rotate(Polygon(points), angle, origin=origin, use_radians=False)
    return _strip_closing([(float(x), float(y)) for x, y in rotated.exterior.coords])


def _apply_transforms(points: list[tuple[float, float]], transforms: list[dict[str, Any]]) -> list[tuple[float, float]]:
    current = points
    for transform in transforms:
        if "Rotate" not in transform:
            raise ValueError(f"Unsupported transform: {transform!r}")
        angle, origin = transform["Rotate"]
        current = _rotate_points(current, float(angle), (float(origin[0]), float(origin[1])))
    return current


def _iter_polygons(geom: Polygon | MultiPolygon) -> Iterable[Polygon]:
    if isinstance(geom, Polygon):
        yield geom
    else:
        yield from geom.geoms


def _path_to_polygons(points: list[tuple[float, float]], width: float) -> list[list[tuple[float, float]]]:
    geom = LineString(points).buffer(width / 2.0, cap_style=2, join_style=2)
    return [_strip_closing([(float(x), float(y)) for x, y in poly.exterior.coords]) for poly in _iter_polygons(geom)]


def parse_fdl_layout(path: Path) -> tuple[list[Shape], list[Pin]]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source, filename=str(path))
    shapes: list[Shape] = []
    pins: list[Pin] = []
    for node in tree.body:
        call = node.value if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) else None
        call = node.value if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) else call
        if call is None:
            continue
        name = _call_name(call)
        kwargs = {kw.arg: _literal(kw.value) for kw in call.keywords if kw.arg}
        if name == "Polygon":
            shapes.append(Shape(str(kwargs["metalLayer"]), [(float(x), float(y)) for x, y in kwargs["location"]]))
        elif name == "Rectangle":
            points = _rect_points(tuple(float(v) for v in kwargs["location"]), float(kwargs["width"]), float(kwargs["height"]))
            shapes.append(Shape(str(kwargs["metalLayer"]), _apply_transforms(points, kwargs.get("transform", []))))
        elif name == "Path":
            for polygon in _path_to_polygons([(float(x), float(y)) for x, y in kwargs["location"]], float(kwargs["width"])):
                shapes.append(Shape(str(kwargs["metalLayer"]), polygon))
        elif name == "Pin":
            prop = kwargs["location"]["Prop"]
            pins.append(Pin(str(kwargs["name"]), str(kwargs["metalLayer"]), float(prop["x"]), float(prop["y"]), float(prop["width"]), float(prop["height"])))
    if not shapes:
        raise ValueError(f"No layout shapes found in {path}")
    return shapes, pins


def _fmt_num(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-9):
        return str(int(round(value)))
    return f"{value:.6f}".rstrip("0").rstrip(".").replace("-0", "0")


def _fmt_point(point: tuple[float, float]) -> str:
    return f"{_fmt_num(point[0])}:{_fmt_num(point[1])}"


def _fmt_bbox(x0: float, y0: float, x1: float, y1: float) -> str:
    return f"list({_fmt_point((x0, y0))} {_fmt_point((x1, y1))})"


def _skill_points(points: list[tuple[float, float]]) -> str:
    return "list(" + " ".join(_fmt_point(point) for point in points) + ")"


def _bounds(shapes: list[Shape], pins: list[Pin]) -> tuple[float, float, float, float]:
    xs = [x for shape in shapes for x, _ in shape.points]
    ys = [y for shape in shapes for _, y in shape.points]
    for pin in pins:
        xs.extend([pin.x, pin.x + pin.width])
        ys.extend([pin.y, pin.y + pin.height])
    return min(xs), min(ys), max(xs), max(ys)


def build_skill(shapes: list[Shape], pins: list[Pin], *, lib_name: str, lib_path: str, tech_lib: str, cell_name: str) -> str:
    min_x, min_y, max_x, max_y = _bounds(shapes, pins)
    margin = 20.0
    lines = [
        "; Auto-generated by single_inductor_lq_surrogate",
        "",
        "procedure(CDX_makeFdlLayout()",
        "  let((libObj cv net term fig pinObj)",
        f'    libObj = ddGetObj("{lib_name}")',
        "    unless(libObj",
        f'      libObj = ddCreateLib("{lib_name}" "{lib_path}")',
        "    )",
        f'    techBindTechFile(libObj "{tech_lib}")',
        f'    cv = dbOpenCellViewByType("{lib_name}" "{cell_name}" "layout" "maskLayout" "w")',
        "    unless(cv",
        f'      error("Failed to open {lib_name}/{cell_name}/layout")',
        "    )",
        "    foreach(fig cv~>shapes dbDeleteObject(fig))",
        "    foreach(term cv~>terminals dbDeleteObject(term))",
        "    foreach(net cv~>nets dbDeleteObject(net))",
        f'    dbCreateRect(cv list("BORDER" "drawing") {_fmt_bbox(min_x - margin, min_y - margin, max_x + margin, max_y + margin)})',
    ]
    for shape in shapes:
        layer = CADENCE_LAYER_MAP.get(shape.layer.lower(), shape.layer)
        lines.append(f'    dbCreatePolygon(cv list("{layer}" "drawing") {_skill_points(shape.points)})')
    for pin in pins:
        layer = CADENCE_LAYER_MAP.get(pin.layer.lower(), pin.layer)
        x0, y0, x1, y1 = pin.x, pin.y, pin.x + pin.width, pin.y + pin.height
        cx, cy = pin.center
        label_x = x0 if cx < (min_x + max_x) / 2.0 else x1
        lines.extend(
            [
                f'    net = dbMakeNet(cv "{pin.name}")',
                f'    term = dbCreateTerm(net "{pin.name}" "inputOutput")',
                f'    fig = dbCreateRect(cv list("{layer}" "drawing") {_fmt_bbox(x0, y0, x1, y1)})',
                "    dbAddFigToNet(fig net)",
                f'    pinObj = dbCreatePin(net fig "{pin.name}" term)',
                "    when(pinObj",
                '      dbReplaceProp(pinObj "accessDir" "string" "bidirectional")',
                "    )",
                f'    dbCreateLabel(cv list("{layer}TXT" "drawing") {_fmt_point((label_x, cy))} "{pin.name}" "centerCenter" "R0" "roman" 8.0)',
            ]
        )
    lines.extend(["", "    dbSave(cv)", "    dbClose(cv)", f'    printf("CREATED={lib_name}/{cell_name}/layout\\n")', f'    printf("SHAPES={len(shapes)} PINS={len(pins)}\\n")', "  )", ")", "", "CDX_makeFdlLayout()", "exit()", ""])
    return "\n".join(lines)


def fdl_to_skill(fdl_path: Path, skill_path: Path, *, lib_name: str, lib_path: str, tech_lib: str, cell_name: str) -> None:
    shapes, pins = parse_fdl_layout(fdl_path)
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(build_skill(shapes, pins, lib_name=lib_name, lib_path=lib_path, tech_lib=tech_lib, cell_name=cell_name), encoding="ascii", newline="\n")

