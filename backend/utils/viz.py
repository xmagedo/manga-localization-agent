# backend/utils/viz.py
from PIL import Image, ImageDraw
from pathlib import Path

def draw_boxes(image, panels, bubbles, out_path: Path):
    img = image.copy()
    d = ImageDraw.Draw(img)

    for p in panels:
        c = p["coordinates"]; x1,y1,x2,y2 = c["x1"],c["y1"],c["x2"],c["y2"]
        d.rectangle([x1,y1,x2,y2], outline=(0,255,0), width=4)
        d.text((x1+4, y1+4), f"P{p['panel_no']}", fill=(0,255,0))

    for b in bubbles:
        c = b["coordinates"]; x1,y1,x2,y2 = c["x1"],c["y1"],c["x2"],c["y2"]
        d.rectangle([x1,y1,x2,y2], outline=(255,0,0), width=2)
        d.text((x1+2, y1+2), f"B{b['bubble_no']}/P{b['panel_no']}", fill=(255,0,0))

    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
