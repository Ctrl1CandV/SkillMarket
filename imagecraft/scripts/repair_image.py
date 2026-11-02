#!/usr/bin/env python3
"""Repair explicitly selected raster regions; never infer text or graph semantics.

Uses existing Pillow/numpy, plus optional OpenCV for local erasure. No downloads,
image-model calls or original-file replacement. Masks and content require review.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib import import_module
import io
import json
import math
from pathlib import Path
import re
import time


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def box(value, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4 or any(type(v) is not int for v in value):
        raise ValueError('A rectangle must contain four integer pixel coordinates')
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError('Rectangle outside the image')
    return x0, y0, x1, y1


def color(value: str) -> tuple[int, int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}', value):
        raise ValueError('Colors must be #RRGGBB')
    return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16), 255)


def repair(source: Path, spec: dict, output: Path) -> dict:
    begin = time.perf_counter()
    if not isinstance(spec, dict) or spec.get('schema') != 'imagecraft.raster-repair/1':
        raise ValueError('Unsupported repair specification')
    if any(str(path).startswith(('\\\\', '//')) for path in (source, output)):
        raise ValueError('Use local paths, not network shares')
    if not output.is_absolute() or output.exists():
        raise ValueError('Use a new absolute output directory; existing files are never overwritten')
    try:
        Image = import_module('PIL.Image')
        ImageDraw = import_module('PIL.ImageDraw')
        ImageFont = import_module('PIL.ImageFont')
        np = import_module('numpy')
    except ImportError as exc:
        raise ValueError('Use an existing interpreter with numpy and Pillow; no package is installed automatically') from exc
    if source.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Source exceeds 32 MiB')
    data = source.read_bytes()
    if sha(data) != spec.get('source_sha256'):
        raise ValueError('Source hash does not match the reviewed image')
    with Image.open(io.BytesIO(data)) as image:
        if image.format != 'PNG' or getattr(image, 'n_frames', 1) != 1:
            raise ValueError('This repair tool accepts one static, opaque PNG')
        if image.mode not in ('RGB', 'RGBA') or data[24] != 8:
            raise ValueError('Use an 8-bit RGB/RGBA PNG; normalize a copy before selecting masks')
        if any(key in image.info for key in ('icc_profile', 'gamma', 'chromaticity')):
            raise ValueError('Color-managed input is not supported; normalize a separate copy explicitly first')
        if image.width * image.height > 24_000_000:
            raise ValueError('Source exceeds 24 megapixels')
        if image.getexif().get(274, 1) != 1:
            raise ValueError('Normalize orientation before specifying pixel coordinates')
        rgba = image.convert('RGBA')
        if rgba.getextrema()[3] != (255, 255):
            raise ValueError('Transparent sources are not supported by this bounded repair tool')
        original = rgba.convert('RGB')
    width, height = original.size
    if spec.get('size') != [width, height]:
        raise ValueError('Specification size does not match the image')
    masks, texts, paths = (spec.get(key, []) for key in ('masks', 'texts', 'paths'))
    if not all(isinstance(v, list) and len(v) <= 32 for v in (masks, texts, paths)) or not (masks or texts or paths):
        raise ValueError('Require at least one explicit operation, with at most 32 per type')
    if not all(isinstance(entry, dict) for entries in (masks, texts, paths) for entry in entries):
        raise ValueError('Repair operations must be JSON objects')
    cv2 = None
    if masks:
        try:
            cv2 = import_module('cv2')
        except ImportError as exc:
            raise ValueError('Erasure needs an already installed OpenCV; text/path overlays do not') from exc
    mask = np.zeros((height, width), dtype=np.uint8)
    for entry in masks:
        x0, y0, x1, y1 = box(entry['rect'], width, height)
        mask[y0:y1, x0:x1] = 255
    mask_pixels = int(np.count_nonzero(mask))
    if mask_pixels > width * height * 0.10:
        raise ValueError('Erasure exceeds 10% of the image; review or rebuild instead of silently erasing a large area')
    # Supersample only the transparent overlay, not the source pixels.
    scale = 2
    overlay = Image.new('RGBA', (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text_checks = []
    for entry in texts:
        x0, y0, x1, y1 = box(entry['box'], width, height)
        text, font_size = entry['text'], entry['font_size']
        if not isinstance(text, str) or not 1 <= len(text) <= 200 or any(ord(char) < 32 for char in text):
            raise ValueError('Text must be a bounded, explicit single line')
        if type(font_size) is not int or not 8 <= font_size <= 160:
            raise ValueError('Font size must be an integer between 8 and 160')
        font_path = Path(entry['font_file'])
        if str(font_path).startswith(('\\\\', '//')) or not font_path.is_absolute():
            raise ValueError('Supply an absolute local font path')
        if not font_path.is_file() or font_path.suffix.lower() not in ('.ttf', '.ttc', '.otf'):
            raise ValueError('Supply an existing, licensed font file')
        font = ImageFont.truetype(str(font_path), font_size * scale)
        bounds = draw.textbbox((0, 0), text, font=font)
        tw, th = bounds[2]-bounds[0], bounds[3]-bounds[1]
        if tw > (x1-x0)*scale or th > (y1-y0)*scale:
            raise ValueError('Text does not fit its reviewed region; change the layout, do not silently shrink or clip it')
        align = entry.get('align', 'left')
        if align not in ('left', 'center'):
            raise ValueError('Text alignment must be left or center')
        x = x0*scale if align == 'left' else (x0+x1)*scale/2-tw/2
        y = (y0+y1)*scale/2-th/2
        draw.text((x-bounds[0], y-bounds[1]), text, font=font, fill=color(entry['color']))
        text_checks.append({'text': text, 'box': [x0,y0,x1,y1], 'rendered_bounds_size': [tw/scale,th/scale], 'fits': True})
    for entry in paths:
        points = entry['points']
        line_width = entry['width']
        if type(line_width) is not int or not 1 <= line_width <= 24 or not isinstance(points, list) or not 2 <= len(points) <= 16:
            raise ValueError('A connector needs 2–16 points and integer width 1–24')
        for point in points:
            if not isinstance(point, list) or len(point) != 2 or any(type(v) is not int for v in point):
                raise ValueError('Connector points must be integer coordinate pairs')
            if not (0 <= point[0] < width and 0 <= point[1] < height):
                raise ValueError('Connector point outside image')
        if any(a == b for a,b in zip(points,points[1:])):
            raise ValueError('Zero-length connector segment')
        if type(entry.get('arrow', True)) is not bool:
            raise ValueError('arrow must be a boolean')
        margin = line_width/2+2
        if any(not (margin <= x < width-margin and margin <= y < height-margin) for x,y in points):
            raise ValueError('Connector stroke may be clipped at the canvas edge')
        fill = color(entry['color'])
        scaled = [(x*scale,y*scale) for x,y in points]
        triangle = None
        if entry.get('arrow', True):
            ax,ay=points[-2]; bx,by=points[-1]
            distance=math.hypot(bx-ax,by-ay)
            length=max(14,line_width*3)
            if distance < length:
                raise ValueError('Last connector segment is too short for its arrowhead')
            ux,uy=(bx-ax)/distance,(by-ay)/distance
            half=max(7,line_width*1.6)
            base_x,base_y=bx-ux*length,by-uy*length
            scaled[-1]=(base_x*scale,base_y*scale)
            triangle=[(bx*scale,by*scale),((base_x-uy*half)*scale,(base_y+ux*half)*scale),((base_x+uy*half)*scale,(base_y-ux*half)*scale)]
            if any(not (2*scale <= x < (width-2)*scale and 2*scale <= y < (height-2)*scale) for x,y in triangle):
                raise ValueError('Arrowhead may be clipped at the canvas edge')
        draw.line(scaled, fill=fill, width=line_width*scale, joint='curve')
        r=line_width*scale/2
        for x,y in scaled[:-1]:
            draw.ellipse((x-r,y-r,x+r,y+r),fill=fill)
        if triangle:
            draw.polygon(triangle,fill=fill)
    overlay=overlay.resize((width,height),Image.Resampling.LANCZOS)
    source_pixels=np.array(original)
    stamp=time.perf_counter()
    repaired=cv2.inpaint(source_pixels,mask,3,cv2.INPAINT_TELEA) if cv2 is not None else source_pixels.copy()
    inpaint_seconds=time.perf_counter()-stamp if cv2 is not None else 0.0
    result=Image.alpha_composite(Image.fromarray(repaired).convert('RGBA'),overlay).convert('RGB')
    changed=np.any(np.array(result)!=source_pixels,axis=2)
    permitted=(mask>0)|(np.array(overlay.getchannel('A'))>0)
    outside=int(np.count_nonzero(changed & ~permitted))
    if outside:
        raise ValueError('Unexpected changes outside declared erasure/overlay pixels')
    output.mkdir(parents=True,exist_ok=False)
    result.save(output/'image.png')
    Image.fromarray(mask).save(output/'erasure-mask.png')
    overlay.save(output/'overlay.png')
    (output/'spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    receipt={'schema':'imagecraft.raster-repair-result/1','state':'repaired_visual_and_semantic_review_required',
             'source':str(source.resolve()),'source_sha256':sha(data),'output':str(output/'image.png'),
             'output_sha256':sha((output/'image.png').read_bytes()),'size':[width,height],
             'tool_sha256':sha(Path(__file__).read_bytes()),
             'mask_pixels':mask_pixels,'changed_pixels':int(np.count_nonzero(changed)),
             'changed_pixel_percent':round(float(np.count_nonzero(changed))/(width*height)*100,6),
             'changes_outside_erasure_or_overlay':outside,'texts':text_checks,'path_count':len(paths),
             'inpaint_seconds':round(inpaint_seconds,6),'repair_seconds':round(time.perf_counter()-begin,6),
             'timing_scope':'Repair function including imports, image/font IO and PNG writes; excludes deciding content, locating masks, process startup and visual/semantic review',
             'opencv_version':cv2.__version__ if cv2 is not None else None,'image_model_calls':0,
             'limits':['No OCR or guessed wording','No topology inference or automatic semantic approval','Mask placement and repair seams require actual inspection','No guarantee for complex texture, occlusion, or missing source content']}
    (output/'report.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return receipt


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if str(args.spec).startswith(('\\\\', '//')):
            raise ValueError('Use a local specification, not a network share')
        if args.spec.stat().st_size>65536:
            raise ValueError('Repair specification exceeds 64 KiB')
        receipt=repair(args.source,json.loads(args.spec.read_text(encoding='utf-8')),args.output)
        print(json.dumps(receipt,ensure_ascii=True,indent=2))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=True))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
