"""Small dependency-free SVG generators for the hardware inspector."""
from __future__ import annotations

from xml.sax.saxutils import escape

from .mcu_db import lookup
from .pinout_db import get_board_wiring, get_pic_wiring


def _palette(theme: str):
    if theme == "light":
        return {"bg": "#f5f7fb", "panel": "#ffffff", "ink": "#182230", "muted": "#526174", "wire": "#087e8b", "warn": "#b42318", "border": "#aeb8c5"}
    if theme == "high_contrast":
        return {"bg": "#000000", "panel": "#000000", "ink": "#ffffff", "muted": "#ffffff", "wire": "#00ffff", "warn": "#ffff00", "border": "#ffffff"}
    return {"bg": "#101722", "panel": "#182231", "ink": "#edf3fa", "muted": "#a8b7c8", "wire": "#51d6c5", "warn": "#ff8a80", "border": "#46566b"}


def generate_schematic_svg(mcu_name: str, board_key: str = "uno", theme: str = "dark") -> bytes:
    dev = lookup(mcu_name)
    pic = get_pic_wiring(mcu_name)
    board = get_board_wiring(board_key)
    c = _palette(theme)
    title = escape(dev.display_name if dev else mcu_name.upper())
    verify = "Verified pin map" if pic.pinout_verified else "Pinout requires datasheet check"
    sketch = f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
<rect width="960" height="540" rx="20" fill="{c['bg']}"/>
<text x="32" y="46" fill="{c['ink']}" font-family="Segoe UI,Arial" font-size="24" font-weight="700">Programmer wiring overview</text>
<text x="32" y="72" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">{escape(board.board_name)} → {title} · {escape(verify)}</text>
<rect x="52" y="150" width="230" height="236" rx="14" fill="{c['panel']}" stroke="{c['border']}" stroke-width="2"/>
<text x="167" y="185" text-anchor="middle" fill="{c['ink']}" font-family="Segoe UI,Arial" font-size="18" font-weight="700">Arduino</text>
<text x="78" y="222" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">D2  switched +5 V VDD</text>
<text x="78" y="254" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">A1  MCLR/VPP switch control</text>
<text x="78" y="286" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">D4  PGC / clock</text>
<text x="78" y="318" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">D7  PGD / bidirectional data</text>
<text x="78" y="350" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">A5  activity LED</text>
<text x="78" y="377" fill="{c['warn']}" font-family="Segoe UI,Arial" font-size="11">A1 HIGH=reset; LOW=select external VPP</text>
<rect x="650" y="150" width="250" height="236" rx="14" fill="{c['panel']}" stroke="{c['border']}" stroke-width="2"/>
<text x="775" y="188" text-anchor="middle" fill="{c['ink']}" font-family="Segoe UI,Arial" font-size="18" font-weight="700">{title}</text>
<text x="775" y="224" text-anchor="middle" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">{escape(pic.package)}</text>
<text x="775" y="270" text-anchor="middle" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">MCLR/VPP · VDD · VSS</text>
<text x="775" y="302" text-anchor="middle" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">PGC · PGD</text>
<path d="M282 222 H610 Q630 222 650 260" fill="none" stroke="{c['wire']}" stroke-width="4"/>
<path d="M282 254 H610 Q630 254 650 280" fill="none" stroke="{c['warn']}" stroke-width="4"/>
<path d="M282 286 H610 Q630 286 650 300" fill="none" stroke="{c['wire']}" stroke-width="4"/>
<path d="M282 318 H610 Q630 318 650 320" fill="none" stroke="{c['wire']}" stroke-width="4"/>
<rect x="348" y="410" width="264" height="74" rx="12" fill="{c['panel']}" stroke="{c['border']}"/>
<text x="480" y="438" text-anchor="middle" fill="{c['ink']}" font-family="Segoe UI,Arial" font-size="13" font-weight="700">External VPP switch / power circuit</text>
<text x="480" y="462" text-anchor="middle" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="11">A1 is logic-only; switched VPP output goes to PIC MCLR</text>
<path d="M282 254 H320 V394 H390 V410" fill="none" stroke="{c['warn']}" stroke-width="3" stroke-dasharray="8 6"/>
<path d="M612 430 H630 V280 H650" fill="none" stroke="{c['warn']}" stroke-width="3"/>
<text x="480" y="516" text-anchor="middle" fill="{c['warn']}" font-family="Segoe UI,Arial" font-size="13" font-weight="700">Illustrative only — confirm every connection against the device and board datasheets.</text>
</svg>'''
    return sketch.encode("utf-8")


def generate_package_pinout_svg(mcu_name: str, board_key: str = "uno", theme: str = "dark") -> bytes:
    dev = lookup(mcu_name)
    pic = get_pic_wiring(mcu_name)
    c = _palette(theme)
    title = escape(dev.display_name if dev else mcu_name.upper())
    if not pic.pinout_verified:
        text = escape(pic.wiring_note)
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="760" height="430" viewBox="0 0 760 430">
<rect width="760" height="430" rx="20" fill="{c['bg']}"/><rect x="48" y="70" width="664" height="290" rx="18" fill="{c['panel']}" stroke="{c['warn']}" stroke-width="3"/>
<text x="380" y="130" text-anchor="middle" fill="{c['warn']}" font-family="Segoe UI,Arial" font-size="24" font-weight="700">Pinout not verified for {title}</text>
<text x="380" y="190" text-anchor="middle" fill="{c['ink']}" font-family="Segoe UI,Arial" font-size="16">{text}</text>
<text x="380" y="280" text-anchor="middle" fill="{c['muted']}" font-family="Segoe UI,Arial" font-size="14">Do not wire from a generic diagram. Check the exact package datasheet first.</text></svg>'''.encode("utf-8")

    pins = 8 if pic.package.endswith("8") else 18 if pic.package.endswith("18") else 40
    rows = pins // 2
    lines = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="760" height="600" viewBox="0 0 760 600">
<rect width="760" height="600" rx="20" fill="{c['bg']}"/><text x="380" y="42" text-anchor="middle" fill="{c['ink']}" font-family="Segoe UI,Arial" font-size="23" font-weight="700">{title} · {escape(pic.package)}</text>
<rect x="270" y="75" width="220" height="{rows * 26 + 40}" rx="22" fill="{c['panel']}" stroke="{c['border']}" stroke-width="3"/><path d="M350 75 a30 30 0 0 0 60 0" fill="{c['bg']}" stroke="{c['border']}" stroke-width="2"/>''']
    for i in range(rows):
        left = i + 1
        right = pins - i
        y = 112 + i * 26
        left_name = "MCLR/VPP" if pic.vpp_pin == left else "VDD" if left in pic.vdd_pins else "VSS" if left in pic.vss_pins else "PGC" if pic.pgc_pin == left else "PGD" if pic.pgd_pin == left else ""
        right_name = "MCLR/VPP" if pic.vpp_pin == right else "VDD" if right in pic.vdd_pins else "VSS" if right in pic.vss_pins else "PGC" if pic.pgc_pin == right else "PGD" if pic.pgd_pin == right else ""
        lines.append(f'<text x="250" y="{y}" text-anchor="end" fill="{c["ink"]}" font-family="Segoe UI,Arial" font-size="13">{left} · {escape(left_name)}</text>')
        lines.append(f'<text x="510" y="{y}" fill="{c["ink"]}" font-family="Segoe UI,Arial" font-size="13">{right} · {escape(right_name)}</text>')
    lines.append(f'<text x="380" y="560" text-anchor="middle" fill="{c["muted"]}" font-family="Segoe UI,Arial" font-size="13">Illustration is not a substitute for checking pin 1 and the device datasheet.</text></svg>')
    return "".join(lines).encode("utf-8")
