"""Small offline renderer for the uncompressed diagrams.net XML used by the app.

This intentionally supports the mxGraph features present in the bundled reference
(diagram images, common electrical symbols, labels, and orthogonal wires) without
requiring diagrams.net, a browser, or network access at runtime.
"""

from __future__ import annotations

import base64
import html
import math
import re
import textwrap
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple


class DrawioRenderError(ValueError):
    """Raised when a diagrams.net file cannot be rendered as an image."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_starttag(self, tag: str, _attrs) -> None:
        if tag.lower() == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"div", "p"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(value)
        parser.close()
        raw = "".join(parser.parts)
    except Exception:
        raw = re.sub(r"<[^>]*>", " ", html.unescape(value))
    lines = [" ".join(line.split()) for line in raw.splitlines()]
    return "\n".join(line for line in lines if line)


def _style_map(style: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in style.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def _number(value: Optional[str], default: float = 0.0) -> float:
    try:
        result = float(value) if value is not None else default
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _xml_escape(value: str) -> str:
    return html.escape(value, quote=True)


def _cell_geometry(cell: ET.Element) -> Tuple[float, float, float, float]:
    geometry = cell.find("mxGeometry")
    if geometry is None:
        return 0.0, 0.0, 0.0, 0.0
    return (
        _number(geometry.get("x")),
        _number(geometry.get("y")),
        max(0.0, _number(geometry.get("width"))),
        max(0.0, _number(geometry.get("height"))),
    )


def _cell_image(style: Mapping[str, str]) -> Optional[str]:
    image = style.get("image", "")
    if image.startswith("data:image/") and "," in image:
        mime, payload = image.split(",", 1)
        if ";base64" in mime:
            encoded = payload
        else:
            # diagrams.net stores embedded images as data:image/png,<base64>.
            try:
                base64.b64decode(payload, validate=True)
            except (ValueError, base64.binascii.Error):
                return None
            encoded = f"{mime};base64,{payload}"
        return encoded
    # External image URLs are deliberately not fetched; the renderer is offline.
    return None


def _vertex_markup(cell: ET.Element, style: Mapping[str, str]) -> str:
    x, y, width, height = _cell_geometry(cell)
    value = _plain_text(cell.get("value", ""))
    shape = style.get("shape", "rectangle")
    stroke = style.get("strokeColor", "#202020")
    fill = style.get("fillColor", "#ffffff")
    stroke_width = max(1.0, min(6.0, _number(style.get("strokeWidth"), 2.0)))
    rotation = _number(style.get("rotation"))
    label_color = style.get("fontColor", "#111111")
    align = style.get("align", "center")
    anchor = "start" if align == "left" else "middle"
    text_x = x + 5 if anchor == "start" else x + width / 2
    text_y = y + height / 2

    image = _cell_image(style)
    if image and width > 0 and height > 0:
        return (
            f'<image x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
            f'href="{_xml_escape(image)}" xlink:href="{_xml_escape(image)}" '
            'preserveAspectRatio="none" />'
        )

    if shape == "image":
        # External diagrams.net toolbar/icon images are not necessary for the circuit.
        return ""

    transform = (
        f' transform="rotate({rotation:g} {x + width / 2:g} {y + height / 2:g})"'
        if rotation and width and height
        else ""
    )
    parts = [f"<g{transform}>"]
    safe_stroke = _xml_escape(stroke)
    safe_fill = _xml_escape(fill if fill != "none" else "#ffffff")
    attrs = (
        f'fill="{safe_fill}" stroke="{safe_stroke}" '
        f'stroke-width="{stroke_width:g}" stroke-linejoin="round" '
        'stroke-linecap="round"'
    )
    outline_attrs = attrs.replace(f'fill="{safe_fill}"', 'fill="none"')

    if shape.endswith("resistor_2"):
        mid = y + height / 2
        points = [x, mid, x + width * 0.18, mid]
        for i in range(1, 9):
            points.extend((x + width * (0.18 + i * 0.08), mid + (-1 if i % 2 else 1) * height * 0.38))
        points.extend((x + width * 0.9, mid, x + width, mid))
        points_text = " ".join(f"{points[i]:g},{points[i + 1]:g}" for i in range(0, len(points), 2))
        parts.append(f'<polyline points="{points_text}" {outline_attrs}/>')
    elif "capacitors." in shape:
        cx, cy = x + width / 2, y + height / 2
        parts.append(f'<line x1="{cx - width * .34:g}" y1="{cy - height * .14:g}" x2="{cx + width * .34:g}" y2="{cy - height * .14:g}" {attrs}/>')
        parts.append(f'<line x1="{cx - width * .34:g}" y1="{cy + height * .14:g}" x2="{cx + width * .34:g}" y2="{cy + height * .14:g}" {attrs}/>')
        parts.append(f'<line x1="{cx:g}" y1="{y:g}" x2="{cx:g}" y2="{cy - height * .14:g}" {attrs}/>')
        parts.append(f'<line x1="{cx:g}" y1="{cy + height * .14:g}" x2="{cx:g}" y2="{y + height:g}" {attrs}/>')
    elif "protective_earth" in shape:
        cx = x + width / 2
        parts.append(f'<line x1="{cx:g}" y1="{y:g}" x2="{cx:g}" y2="{y + height * .38:g}" {attrs}/>')
        for i, fraction in enumerate((.55, .76, .94)):
            half = width * (.35 - i * .09)
            yy = y + height * fraction
            parts.append(f'<line x1="{cx - half:g}" y1="{yy:g}" x2="{cx + half:g}" y2="{yy:g}" {attrs}/>')
    elif "opto_electronics.led" in shape:
        cx, cy, r = x + width / 2, y + height / 2, min(width, height) * .32
        parts.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" {attrs}/>')
        parts.append(f'<path d="M {cx - r * .55:g} {cy + r * .45:g} L {cx + r * .55:g} {cy - r * .45:g}" {attrs}/>')
        parts.append(f'<path d="M {cx + r * .75:g} {cy - r * .9:g} l {r * .45:g} {-r * .08:g} l {-r * .08:g} {r * .45:g}" {outline_attrs}/>')
        parts.append(f'<path d="M {cx + r * .25:g} {cy - r * 1.35:g} l {r * .45:g} {-r * .08:g} l {-r * .08:g} {r * .45:g}" {outline_attrs}/>')
    elif "transistors.npn" in shape:
        cx, cy, r = x + width / 2, y + height / 2, min(width, height) * .38
        parts.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" {outline_attrs}/>')
        parts.append(f'<line x1="{cx:g}" y1="{cy - r * .65:g}" x2="{cx:g}" y2="{cy + r * .65:g}" {attrs}/>')
        parts.append(f'<line x1="{cx - r * .75:g}" y1="{cy:g}" x2="{cx:g}" y2="{cy:g}" {attrs}/>')
        parts.append(f'<line x1="{cx:g}" y1="{cy - r * .4:g}" x2="{cx + r * .65:g}" y2="{cy - r:g}" {attrs}/>')
        parts.append(f'<line x1="{cx:g}" y1="{cy + r * .4:g}" x2="{cx + r * .65:g}" y2="{cy + r:g}" {attrs}/>')
    elif "miscellaneous.coaxial_jack" in shape:
        cy = y + height / 2
        parts.append(f'<rect x="{x + width * .18:g}" y="{y + height * .2:g}" width="{width * .64:g}" height="{height * .6:g}" rx="4" {attrs}/>')
        parts.append(f'<line x1="{x:g}" y1="{cy:g}" x2="{x + width * .18:g}" y2="{cy:g}" {attrs}/>')
        parts.append(f'<line x1="{x + width * .82:g}" y1="{cy:g}" x2="{x + width:g}" y2="{cy:g}" {attrs}/>')
    elif shape in {"ellipse", "doubleEllipse"}:
        parts.append(f'<ellipse cx="{x + width / 2:g}" cy="{y + height / 2:g}" rx="{width / 2:g}" ry="{height / 2:g}" {attrs}/>')
    elif shape == "rhombus":
        points = f"{x + width/2:g},{y:g} {x + width:g},{y + height/2:g} {x + width/2:g},{y + height:g} {x:g},{y + height/2:g}"
        parts.append(f'<polygon points="{points}" {attrs}/>')
    elif value:
        if shape not in {"", "text", "rectangle"}:
            parts.append(f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="4" {attrs}/>')
        if fill != "none" and shape in {"rectangle", "roundrect"}:
            parts.append(f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{6 if shape == "roundrect" else 0}" {attrs}/>')
        font_size = max(11.0, min(22.0, _number(style.get("fontSize"), 16.0)))
        max_chars = max(7, int(max(width - 8, 24) / (font_size * .56))) if width else 40
        lines = [
            wrapped
            for line in (value.splitlines() or [value])
            for wrapped in (textwrap.wrap(line, width=max_chars) or [""])
        ]
        start_y = text_y - (len(lines) - 1) * font_size * .6
        for index, line in enumerate(lines):
            parts.append(
                f'<text x="{text_x:g}" y="{start_y + index * font_size * 1.25:g}" '
                f'text-anchor="{anchor}" dominant-baseline="middle" '
                f'font-family="Segoe UI, Arial, sans-serif" font-size="{font_size:g}" '
                f'font-weight="{"bold" if "bold" in cell.get("value", "").lower() else "normal"}" '
                f'fill="{_xml_escape(label_color)}">{_xml_escape(line)}</text>'
            )
    elif width and height:
        # Unknown mxGraph library shapes still get a visible, labelled component box.
        parts.append(f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="3" {attrs}/>')
        name = shape.rsplit(".", 1)[-1].replace("_", " ")[:24]
        parts.append(f'<text x="{text_x:g}" y="{text_y:g}" text-anchor="{anchor}" dominant-baseline="middle" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{_xml_escape(label_color)}">{_xml_escape(name)}</text>')

    parts.append("</g>")
    return "".join(parts)


def _edge_markup(cell: ET.Element, by_id: Mapping[str, ET.Element]) -> str:
    style = _style_map(cell.get("style", ""))
    geometry = cell.find("mxGeometry")
    source = by_id.get(cell.get("source", ""))
    target = by_id.get(cell.get("target", ""))
    points: List[Tuple[float, float]] = []

    def anchor(node: Optional[ET.Element], prefix: str) -> Optional[Tuple[float, float]]:
        if node is None:
            return None
        x, y, width, height = _cell_geometry(node)
        ax = _number(style.get(prefix + "X"), .5)
        ay = _number(style.get(prefix + "Y"), .5)
        return x + width * ax, y + height * ay

    first = anchor(source, "exit")
    last = anchor(target, "entry")
    if geometry is not None:
        source_point = geometry.find("mxPoint[@as='sourcePoint']")
        target_point = geometry.find("mxPoint[@as='targetPoint']")
        if first is None and source_point is not None:
            first = (_number(source_point.get("x")), _number(source_point.get("y")))
        if last is None and target_point is not None:
            last = (_number(target_point.get("x")), _number(target_point.get("y")))
        array = geometry.find("Array[@as='points']")
        if array is not None:
            for point in array.findall("mxPoint"):
                points.append((_number(point.get("x")), _number(point.get("y"))))
    if first is not None:
        points.insert(0, first)
    if last is not None:
        points.append(last)
    if len(points) < 2:
        return ""

    color = _xml_escape(style.get("strokeColor", "#333333"))
    width = max(1.0, min(8.0, _number(style.get("strokeWidth"), 2.0)))
    dash = ' stroke-dasharray="7 5"' if style.get("dashed") == "1" else ""
    coords = " ".join(f"{x:g},{y:g}" for x, y in points)
    arrow = ' marker-end="url(#arrow)"' if style.get("endArrow", "none") != "none" else ""
    return f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width:g}" stroke-linecap="round" stroke-linejoin="round"{dash}{arrow}/>'


def drawio_to_svg(source: Path | str) -> bytes:
    """Render an uncompressed diagrams.net XML file to an offline SVG image."""
    path = Path(source)
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise DrawioRenderError(f"Cannot read circuit diagram: {exc}") from exc

    model = root.find(".//mxGraphModel")
    if model is None:
        raise DrawioRenderError("The circuit file does not contain an mxGraphModel.")
    cells = model.findall("./root/mxCell")
    if not cells:
        raise DrawioRenderError("The circuit file does not contain any diagram cells.")

    by_id = {cell.get("id", ""): cell for cell in cells}
    vertices = [cell for cell in cells if cell.get("vertex") == "1"]
    edges = [cell for cell in cells if cell.get("edge") == "1"]
    bounds: List[Tuple[float, float, float, float]] = []
    for cell in vertices:
        x, y, width, height = _cell_geometry(cell)
        if width > 0 or height > 0:
            bounds.append((x, y, x + max(width, 1), y + max(height, 1)))
    if not bounds:
        raise DrawioRenderError("The circuit file has no renderable diagram geometry.")

    margin = 28.0
    left = min(box[0] for box in bounds) - margin
    top = min(box[1] for box in bounds) - margin
    right = max(box[2] for box in bounds) + margin
    bottom = max(box[3] for box in bounds) + margin
    width = max(1.0, right - left)
    height = max(1.0, bottom - top)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width:g}" height="{height:g}" viewBox="{left:g} {top:g} {width:g} {height:g}">',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
        '<path d="M0,0 L8,4 L0,8 z" fill="#333333"/></marker></defs>',
        '<rect x="{:.3f}" y="{:.3f}" width="{:.3f}" height="{:.3f}" fill="#ffffff"/>'.format(left, top, width, height),
    ]
    for edge in edges:
        parts.append(_edge_markup(edge, by_id))
    for cell in vertices:
        parts.append(_vertex_markup(cell, _style_map(cell.get("style", ""))))
    parts.append("</svg>")
    return "".join(parts).encode("utf-8")
