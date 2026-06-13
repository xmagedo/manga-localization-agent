# backend/utils/html_viewer.py
from pathlib import Path
import json

def save_click_viewer(img_rel_path, detections, out_html):
    """
    img_rel_path: artifact-relative path to the overlay image, e.g. 'viz/5_overlay.png'
    detections: {"panels":[...], "bubbles":[...]}
    out_html: local path where we generate viewer.html (will be logged as an artifact)
    """
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)

    det_path = out_html.with_suffix(".json")
    det_path.write_text(json.dumps(detections), encoding="utf-8")

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Manga Detection Viewer</title>
<style>
  body {{ margin:0; font-family: system-ui, -apple-system, "Segoe UI"; }}
  #wrap {{ display:flex; height:100vh; }}
  #left {{ flex:1; position:relative; background:#111; overflow:auto; }}
  #right {{ width:340px; padding:12px; background:#181818; color:#eee; overflow:auto; }}
  canvas {{ position:absolute; top:0; left:0; }}
  img {{ display:none; }}
  pre {{ white-space:pre-wrap; word-break:break-word; }}
</style>
</head>
<body>
<div id="wrap">
  <div id="left">
    <img id="img" src="{img_rel_path}"/>
    <canvas id="c"></canvas>
  </div>
  <div id="right">
    <h3>Details</h3>
    <div id="info">Click a box</div>
  </div>
</div>
<script>
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const img = document.getElementById('img');
let det = null, boxes = [];

fetch('{det_path.name}').then(r=>r.json()).then(d=>{{det=d; init();}});
function init(){{
  img.onload = () => {{
    cv.width = img.naturalWidth; cv.height = img.naturalHeight;
    draw();
  }};
  img.style.display='block';
}}
function draw(hi=-1){{
  ctx.drawImage(img, 0, 0);
  boxes = [];
  (det.panels||[]).forEach((p,i)=>{{
    const c=p.coordinates; const x1=c.x1, y1=c.y1, x2=c.x2, y2=c.y2;
    boxes.push({{t:'panel',i,x1,y1,x2,y2,label:`P${{p.panel_no}}`}});
  }});
  (det.bubbles||[]).forEach((b,i)=>{{
    const c=b.coordinates; const x1=c.x1, y1=c.y1, x2=c.x2, y2=c.y2;
    boxes.push({{t:'bubble',i,x1,y1,x2,y2,label:`B${{b.bubble_no}} (P${{b.panel_no}})`}});
  }});
  boxes.forEach((b,idx)=>{{
    ctx.lineWidth=2;
    ctx.strokeStyle = b.t==='panel' ? (idx===hi?'#7CFC00':'#3cb043') : (idx===hi?'#8ecbff':'#5596ff');
    ctx.strokeRect(b.x1,b.y1,b.x2-b.x1,b.y2-b.y1);
  }});
}}
cv.addEventListener('click',(e)=>{{
  const r = cv.getBoundingClientRect(); const x=e.clientX-r.left, y=e.clientY-r.top;
  const hit = boxes.find(b=>x>=b.x1 && x<=b.x2 && y>=b.y1 && y<=b.y2);
  const info = document.getElementById('info');
  if(hit){{
    draw(boxes.indexOf(hit));
    const payload = hit.t==='panel' ? det.panels[hit.i] : det.bubbles[hit.i];
    info.innerHTML = '<pre>'+JSON.stringify(payload, null, 2)+'</pre>';
  }}
}});
</script>
</body>
</html>"""
    out_html.write_text(html, encoding="utf-8")
    return str(out_html), str(det_path)
