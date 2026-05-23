from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from svgpathtools import CubicBezier, Line, QuadraticBezier, parse_path


CODEPOINT = 0x20C3
GLYPH_NAME = "uni20C3"
FAMILY_NAME = "UaeDirhamFallback"
VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"


def font_name(font: TTFont, name_id: int) -> str:
    for record in font["name"].names:
        if record.nameID == name_id:
            try:
                return record.toUnicode()
            except Exception:
                pass
    return ""


def read_svg(svg_path: Path):
    root = ET.parse(svg_path).getroot()
    min_x, min_y, width, height = [float(v) for v in root.attrib["viewBox"].split()]
    path_el = next(el for el in root.iter() if el.tag.endswith("path"))
    return (min_x, min_y, width, height), path_el.attrib["d"]


def read_metrics(reference_font_path: Path):
    font = TTFont(reference_font_path)
    head = font["head"]
    hhea = font["hhea"]
    os2 = font["OS/2"]
    return {
        "reference_family": font_name(font, 1),
        "reference_subfamily": font_name(font, 2),
        "reference_full_name": font_name(font, 4),
        "reference_postscript": font_name(font, 6),
        "units_per_em": head.unitsPerEm,
        "ascent": hhea.ascent,
        "descent": hhea.descent,
        "line_gap": hhea.lineGap,
        "typo_ascent": os2.sTypoAscender,
        "typo_descent": os2.sTypoDescender,
        "typo_line_gap": os2.sTypoLineGap,
        "win_ascent": os2.usWinAscent,
        "win_descent": os2.usWinDescent,
        "cap_height": getattr(os2, "sCapHeight", int(head.unitsPerEm * 0.63)),
        "x_height": getattr(os2, "sxHeight", int(head.unitsPerEm * 0.45)),
    }


def style_from_metrics(metrics) -> str:
    return metrics["reference_subfamily"] or "Regular"


def detect_style(style_name: str, source_path: Path, units_per_em: int):
    source = f"{style_name} {source_path.stem}".lower().replace("_", " ").replace("-", " ")
    tokens = set(source.split())

    is_italic = "italic" in tokens or "oblique" in tokens
    weight_name = "Regular"
    weight = 400

    if "thin" in tokens or "hairline" in tokens:
        weight_name = "Thin"
        weight = 100
    elif (
        "extralight" in tokens
        or "ultralight" in tokens
        or ("extra" in tokens and "light" in tokens)
        or ("ultra" in tokens and "light" in tokens)
    ):
        weight_name = "ExtraLight"
        weight = 200
    elif "light" in tokens:
        weight_name = "Light"
        weight = 300
    elif "medium" in tokens:
        weight_name = "Medium"
        weight = 500
    elif (
        "semibold" in tokens
        or "demibold" in tokens
        or ("semi" in tokens and "bold" in tokens)
        or ("demi" in tokens and "bold" in tokens)
    ):
        weight_name = "SemiBold"
        weight = 600
    elif "extrabold" in tokens or "ultrabold" in tokens or ("extra" in tokens and "bold" in tokens) or ("ultra" in tokens and "bold" in tokens):
        weight_name = "ExtraBold"
        weight = 800
    elif "black" in tokens or "heavy" in tokens:
        weight_name = "Black"
        weight = 900
    elif "bold" in tokens:
        weight_name = "Bold"
        weight = 700

    style_name_parts = [weight_name]
    file_suffix_parts = [weight_name.lower()]
    if is_italic:
        style_name_parts.append("Italic")
        file_suffix_parts.append("italic")

    style_name = " ".join(style_name_parts)
    file_suffix = "-".join(file_suffix_parts)
    css_style = "italic" if is_italic else "normal"

    scale = units_per_em / 1000
    embolden_by_weight = {
        100: 0.0,
        200: 0.0,
        300: 0.0,
        400: 0.0,
        500: 22.0 * scale,
        600: 34.0 * scale,
        700: 50.0 * scale,
        800: 62.0 * scale,
        900: 74.0 * scale,
    }

    return {
        "style_name": style_name,
        "file_suffix": file_suffix,
        "css_style": css_style,
        "slant": 0.18 if is_italic else 0.0,
        "embolden": embolden_by_weight[weight],
        "weight": weight,
    }


def transform_point(point, min_x, min_y, scale, cap_height, side_bearing, slant):
    y = cap_height - ((point.imag - min_y) * scale)
    x = side_bearing + ((point.real - min_x) * scale) + (slant * y)
    return (x, y)


def draw_subpath(out, subpath, min_x, min_y, scale, cap_height, side_bearing, slant):
    out.moveTo(*transform_point(subpath[0].start, min_x, min_y, scale, cap_height, side_bearing, slant))
    for segment in subpath:
        if isinstance(segment, Line):
            out.lineTo(*transform_point(segment.end, min_x, min_y, scale, cap_height, side_bearing, slant))
        elif isinstance(segment, CubicBezier):
            out.cubicTo(
                *transform_point(segment.control1, min_x, min_y, scale, cap_height, side_bearing, slant),
                *transform_point(segment.control2, min_x, min_y, scale, cap_height, side_bearing, slant),
                *transform_point(segment.end, min_x, min_y, scale, cap_height, side_bearing, slant),
            )
        elif isinstance(segment, QuadraticBezier):
            out.quadTo(
                *transform_point(segment.control, min_x, min_y, scale, cap_height, side_bearing, slant),
                *transform_point(segment.end, min_x, min_y, scale, cap_height, side_bearing, slant),
            )
        else:
            raise TypeError(f"Unsupported SVG segment: {type(segment).__name__}")
    out.close()


def build_symbol_path(svg_path: Path, metrics, side_bearing=70, slant=0.0):
    (min_x, min_y, svg_width, svg_height), path_d = read_svg(svg_path)
    scale = metrics["cap_height"] / svg_height
    advance_width = round((svg_width * scale) + (slant * metrics["cap_height"]) + (side_bearing * 2))

    full_path = pathops.Path()
    embolden_source = pathops.Path()
    for subpath in parse_path(path_d).continuous_subpaths():
        if not subpath:
            continue
        draw_subpath(full_path, subpath, min_x, min_y, scale, metrics["cap_height"], side_bearing, slant)
        if subpath.area() < 0:
            draw_subpath(embolden_source, subpath, min_x, min_y, scale, metrics["cap_height"], side_bearing, slant)

    return full_path, embolden_source, advance_width


def embolden_path(path, source_path, width):
    if width <= 0:
        return path

    stroked = pathops.Path()
    stroked.addPath(source_path)
    stroked.stroke(width, pathops.LineCap.BUTT_CAP, pathops.LineJoin.ROUND_JOIN, 4)
    stroked.convertConicsToQuads()

    out = pathops.Path()
    pathops.union([path, stroked], out.getPen())
    return out


def path_to_glyph(path):
    tt_pen = TTGlyphPen(None)
    pen = Cu2QuPen(tt_pen, max_err=1.0)
    path.draw(pen)
    glyph = tt_pen.glyph()
    glyph.recalcBounds(None)
    return glyph


def build_symbol_glyph(svg_path: Path, metrics, slant=0.0, embolden=0.0):
    path, embolden_source, advance_width = build_symbol_path(svg_path, metrics, slant=slant)
    path = embolden_path(path, embolden_source, embolden)
    glyph = path_to_glyph(path)
    if embolden > 0:
        advance_width += round(embolden)
    return glyph, advance_width


def build_notdef():
    return TTGlyphPen(None).glyph()


def make_font(svg_path: Path, reference_font_path: Path, output_path: Path):
    metrics = read_metrics(reference_font_path)
    detected_style = style_from_metrics(metrics)
    adaptation = detect_style(detected_style, reference_font_path, metrics["units_per_em"])
    style_name = adaptation["style_name"]
    ps_style = style_name.replace(" ", "")
    ps_name = f"{FAMILY_NAME}-{ps_style}"

    symbol_glyph, symbol_advance = build_symbol_glyph(
        svg_path,
        metrics,
        slant=adaptation["slant"],
        embolden=adaptation["embolden"],
    )

    fb = FontBuilder(metrics["units_per_em"], isTTF=True)
    fb.setupGlyphOrder([".notdef", GLYPH_NAME])
    fb.setupCharacterMap({CODEPOINT: GLYPH_NAME})
    fb.setupGlyf({".notdef": build_notdef(), GLYPH_NAME: symbol_glyph})
    fb.setupHorizontalMetrics({".notdef": (500, 0), GLYPH_NAME: (symbol_advance, 70)})
    fb.setupHorizontalHeader(
        ascent=metrics["ascent"],
        descent=metrics["descent"],
        lineGap=metrics["line_gap"],
    )
    fb.setupOS2(
        sTypoAscender=metrics["typo_ascent"],
        sTypoDescender=metrics["typo_descent"],
        sTypoLineGap=metrics["typo_line_gap"],
        usWinAscent=metrics["win_ascent"],
        usWinDescent=metrics["win_descent"],
        sCapHeight=metrics["cap_height"],
        sxHeight=metrics["x_height"],
        usWeightClass=adaptation["weight"],
        usWidthClass=5,
    )
    fb.setupNameTable(
        {
            "familyName": FAMILY_NAME,
            "styleName": style_name,
            "uniqueFontIdentifier": f"{FAMILY_NAME} {style_name} 1.000",
            "fullName": f"{FAMILY_NAME} {style_name}",
            "psName": ps_name,
            "version": "Version 1.000",
        }
    )
    fb.setupPost(italicAngle=-12.0 if adaptation["css_style"] == "italic" else 0.0)
    fb.setupMaxp()
    fb.setupHead(unitsPerEm=metrics["units_per_em"], created=0, modified=0)
    fb.save(output_path)

    return {
        "path": output_path,
        "style": style_name,
        "css_style": adaptation["css_style"],
        "weight": adaptation["weight"],
        "source": reference_font_path.name,
        "units_per_em": metrics["units_per_em"],
        "cap_height": metrics["cap_height"],
        "slant": adaptation["slant"],
        "embolden": adaptation["embolden"],
    }


def inspect_contains_codepoint(path: Path) -> bool:
    font = TTFont(path)
    cmap = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)
    return cmap.get(CODEPOINT) == GLYPH_NAME


def find_inputs():
    svgs = sorted(INPUT_DIR.glob("*.svg"))
    fonts = sorted([*INPUT_DIR.glob("*.ttf"), *INPUT_DIR.glob("*.otf")])

    if len(svgs) != 1:
        raise SystemExit(f"Expected exactly one SVG in {INPUT_DIR}. Found {len(svgs)}.")
    if not fonts:
        raise SystemExit(f"Expected one or more .ttf/.otf files in {INPUT_DIR}.")

    return svgs[0], fonts


def render_preview(results):
    if not results:
        return

    preview_path = OUTPUT_DIR / "dirham-font-variants-preview.png"
    row_height = 145
    image = Image.new("RGB", (1200, 70 + (row_height * len(results))), "white")
    draw = ImageDraw.Draw(image)
    label_font = ImageFont.truetype(str(results[0]["source_path"]), 22)

    for index, result in enumerate(results):
        app_font = ImageFont.truetype(str(result["source_path"]), 74)
        symbol_font = ImageFont.truetype(str(result["path"]), 74)
        y = 34 + (index * row_height)
        baseline = y + 95
        label = f"{result['style']} fallback + {result['source']} digits"
        draw.text((70, y), label, font=label_font, fill=(95, 95, 95))
        draw.line((70, baseline, 1130, baseline), fill=(220, 60, 60), width=1)
        draw.text((70, baseline), "\u20C3", font=symbol_font, fill=(18, 18, 18), anchor="ls")
        x = 70 + draw.textlength("\u20C3", font=symbol_font) + 18
        draw.text((x, baseline), "123.45", font=app_font, fill=(18, 18, 18), anchor="ls")

    image.save(preview_path)


def main():
    print(f"UAE Dirham Fallback Font Generator v{VERSION}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    svg_path, font_paths = find_inputs()

    results = []
    for font_path in font_paths:
        metrics = read_metrics(font_path)
        style = detect_style(style_from_metrics(metrics), font_path, metrics["units_per_em"])
        file_style = style["file_suffix"]
        output_path = OUTPUT_DIR / f"{FAMILY_NAME}-{file_style}.ttf"
        result = make_font(svg_path, font_path, output_path)
        result["source_path"] = font_path
        result["contains_u20c3"] = inspect_contains_codepoint(output_path)
        results.append(result)
        print(f"Generated {output_path.name} from {font_path.name}")
        print(f"  style: {result['style']}")
        print(f"  contains U+20C3: {result['contains_u20c3']}")
        print(f"  unitsPerEm: {result['units_per_em']}")
        print(f"  capHeight: {result['cap_height']}")
        print(f"  slant: {result['slant']}")
        print(f"  embolden: {result['embolden']}")

    render_preview(results)
    print(f"Preview PNG: {OUTPUT_DIR / 'dirham-font-variants-preview.png'}")


if __name__ == "__main__":
    main()
