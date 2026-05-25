import re
import json
from dataclasses import dataclass
from typing import Optional

DIAGRAM_TYPE = "UnitCircle"
RENDERS_HTML = True   # tells engine.py to return this output directly, not wrap in <svg>


@dataclass
class UnitCircleDiagram:
    angle:                float
    show_point:           bool
    show_coords:          bool
    show_sin:             bool
    show_cos:             bool
    show_tan:             bool
    show_reference_angle: bool
    show_quadrant_labels: bool
    highlight_quadrant:   Optional[int]
    label_point:          str
    lock_angle:           bool


def parse(line: str) -> Optional[UnitCircleDiagram]:
    m = re.match(r'UnitCircle\s*\((.+)\)\s*$', line.strip(), re.DOTALL)
    if not m:
        return None
    inner = m.group(1)

    def get_num(key, default):
        mm = re.search(rf'\b{re.escape(key)}\s*:\s*([-\d.]+)', inner)
        return float(mm.group(1)) if mm else default

    def get_bool(key, default):
        mm = re.search(rf'\b{re.escape(key)}\s*:\s*(true|false)', inner)
        if not mm:
            return default
        return mm.group(1) == 'true'

    def get_str(key, default):
        mm = re.search(rf'\b{re.escape(key)}\s*:\s*"([^"]*)"', inner)
        return mm.group(1) if mm else default

    def get_nullable_int(key):
        mm = re.search(rf'\b{re.escape(key)}\s*:\s*(\d+|null)', inner)
        if not mm:
            return None
        v = mm.group(1)
        return None if v == 'null' else int(v)

    return UnitCircleDiagram(
        angle=get_num('angle', 0.0),
        show_point=get_bool('show_point', True),
        show_coords=get_bool('show_coords', False),
        show_sin=get_bool('show_sin', True),
        show_cos=get_bool('show_cos', True),
        show_tan=get_bool('show_tan', False),
        show_reference_angle=get_bool('show_reference_angle', False),
        show_quadrant_labels=get_bool('show_quadrant_labels', False),
        highlight_quadrant=get_nullable_int('highlight_quadrant'),
        label_point=get_str('label_point', 'P'),
        lock_angle=get_bool('lock_angle', True),
    )


# ── HTML template ─────────────────────────────────────────────────────────────
# __CONFIG__ is replaced at render time with the JSON config object literal.

_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #fff; font-family: system-ui, -apple-system, sans-serif; overflow: hidden; }
svg { display: block; }
#readout {
  padding: 5px 12px;
  font-size: 13px;
  color: #1e293b;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  text-align: center;
  letter-spacing: 0.01em;
  min-height: 28px;
}
#pt-p { cursor: grab; }
#pt-p:active { cursor: grabbing; }
.snap-flash { animation: snapflash 0.2s ease-out; }
@keyframes snapflash { 0%,100% { r: 5; } 50% { r: 8; } }
</style>
</head>
<body>
<svg id="uc" width="400" height="400" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arr" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" fill="#64748b"/>
    </marker>
  </defs>
  <!-- axes -->
  <line x1="40" y1="200" x2="366" y2="200" stroke="#64748b" stroke-width="1.5" marker-end="url(#arr)"/>
  <line x1="200" y1="362" x2="200" y2="34" stroke="#64748b" stroke-width="1.5" marker-end="url(#arr)"/>
  <!-- axis labels -->
  <text x="375" y="204" font-size="14" fill="#64748b" font-family="system-ui,sans-serif">x</text>
  <text x="196" y="28" font-size="14" fill="#64748b" font-family="system-ui,sans-serif">y</text>
  <text x="188" y="215" font-size="12" fill="#64748b" font-family="system-ui,sans-serif">O</text>
  <!-- unit circle -->
  <circle cx="200" cy="200" r="140" fill="none" stroke="#cbd5e1" stroke-width="1.5"/>
  <!-- tick marks -->
  <line x1="340" y1="195" x2="340" y2="205" stroke="#64748b" stroke-width="1"/>
  <line x1="60"  y1="195" x2="60"  y2="205" stroke="#64748b" stroke-width="1"/>
  <line x1="195" y1="60"  x2="205" y2="60"  stroke="#64748b" stroke-width="1"/>
  <line x1="195" y1="340" x2="205" y2="340" stroke="#64748b" stroke-width="1"/>
  <text x="350" y="218" font-size="11" fill="#64748b" text-anchor="middle" font-family="system-ui,sans-serif">1</text>
  <text x="50"  y="218" font-size="11" fill="#64748b" text-anchor="middle" font-family="system-ui,sans-serif">−1</text>
  <text x="213" y="52"  font-size="11" fill="#64748b" font-family="system-ui,sans-serif">1</text>
  <text x="213" y="354" font-size="11" fill="#64748b" font-family="system-ui,sans-serif">−1</text>
</svg>
<div id="readout"></div>
<script>
const CFG = __CONFIG__;

const CX = 200, CY = 200, R = 140;
const NS = 'http://www.w3.org/2000/svg';
const TWO_PI = Math.PI * 2;

/* ── Exact-value lookup ─────────────────────────────────────────────────── */
const EXACT = {
  0:   {s:'0',      c:'1',       t:'0'},
  30:  {s:'1/2',    c:'√3/2',    t:'1/√3'},
  45:  {s:'√2/2',   c:'√2/2',    t:'1'},
  60:  {s:'√3/2',   c:'1/2',     t:'√3'},
  90:  {s:'1',      c:'0',       t:null},
  120: {s:'√3/2',   c:'−1/2',    t:'−√3'},
  135: {s:'√2/2',   c:'−√2/2',   t:'−1'},
  150: {s:'1/2',    c:'−√3/2',   t:'−1/√3'},
  180: {s:'0',      c:'−1',      t:'0'},
  210: {s:'−1/2',   c:'−√3/2',   t:'1/√3'},
  225: {s:'−√2/2',  c:'−√2/2',   t:'1'},
  240: {s:'−√3/2',  c:'−1/2',    t:'√3'},
  270: {s:'−1',     c:'0',       t:null},
  300: {s:'−√3/2',  c:'1/2',     t:'−√3'},
  315: {s:'−√2/2',  c:'√2/2',    t:'−1'},
  330: {s:'−1/2',   c:'√3/2',    t:'−1/√3'},
  360: {s:'0',      c:'1',       t:'0'},
};

/* Snap targets: every 30° and 45° boundary */
const SNAP = [...new Set([...Array.from({length:12},(_,i)=>i*30),
                          ...Array.from({length:8}, (_,i)=>i*45)])].sort((a,b)=>a-b);

let angle = CFG.angle;
let snapping = false;

function rad(d) { return d * Math.PI / 180; }
function ptX(a) { return CX + R * Math.cos(rad(a)); }
function ptY(a) { return CY - R * Math.sin(rad(a)); }
function norm(a) { return ((Math.round(a) % 360) + 360) % 360; }

function fmt(type, a) {
  const n = norm(a);
  if (EXACT[n]) {
    const v = EXACT[n][type];
    return v === null ? 'undef' : v;
  }
  const r = rad(a);
  const v = type === 's' ? Math.sin(r) : type === 'c' ? Math.cos(r) : Math.tan(r);
  if (!isFinite(v) || Math.abs(v) > 999) return 'undef';
  return (v >= 0 ? '' : '−') + Math.abs(v).toFixed(2);
}

function el(tag, attrs, txt) {
  const e = document.createElementNS(NS, tag);
  if (attrs) Object.entries(attrs).forEach(([k,v]) => e.setAttribute(k, String(v)));
  if (txt !== undefined) e.textContent = txt;
  return e;
}

function txt(x, y, s, attrs) {
  return el('text', {x, y, 'font-family':'system-ui,sans-serif',
    'dominant-baseline':'middle', ...attrs}, s);
}

/* arc path, always counterclockwise (increasing angle), sweep=0 in SVG */
function arc(cx, cy, r, fromDeg, toDeg) {
  const diff = ((toDeg - fromDeg) + 360) % 360;
  if (diff < 0.1) return '';
  const x1 = cx + r*Math.cos(rad(fromDeg)), y1 = cy - r*Math.sin(rad(fromDeg));
  const x2 = cx + r*Math.cos(rad(toDeg)),   y2 = cy - r*Math.sin(rad(toDeg));
  return `M ${x1} ${y1} A ${r} ${r} 0 ${diff>180?1:0} 0 ${x2} ${y2}`;
}

function draw() {
  document.querySelectorAll('.d').forEach(e => e.remove());
  const svg = document.getElementById('uc');
  const a = angle;
  const px = ptX(a), py = ptY(a);
  const cosA = Math.cos(rad(a)), sinA = Math.sin(rad(a));
  const dispA = norm(a);

  /* helper: append with dynamic class */
  function add(node) { node.classList.add('d'); svg.appendChild(node); return node; }

  /* ── Quadrant highlight ────────────────────────────────────────────────── */
  if (CFG.hlQ) {
    const cols = {1:'#2563eb', 2:'#16a34a', 3:'#ea580c', 4:'#7c3aed'};
    const sd = (CFG.hlQ - 1) * 90, ed = CFG.hlQ * 90;
    const d = arc(CX,CY,R,sd,ed) + ` L ${CX} ${CY} Z`;
    add(el('path', {d, fill:cols[CFG.hlQ], opacity:'0.12'}));
  }

  /* ── Quadrant labels ───────────────────────────────────────────────────── */
  if (CFG.showQLbls) {
    [[45,'Q1'],[135,'Q2'],[225,'Q3'],[315,'Q4']].forEach(([ang,lbl]) => {
      const lr = R * 0.62;
      add(txt(CX + lr*Math.cos(rad(ang)), CY - lr*Math.sin(rad(ang)), lbl,
        {fill:'#94a3b8','font-size':'13','text-anchor':'middle'}));
    });
  }

  /* ── Reference angle arc ───────────────────────────────────────────────── */
  if (CFG.showRef) {
    const q = Math.floor((dispA / 90)) + 1;
    let refFrom, refTo, refAng;
    if (q === 1) { refFrom = 0;   refTo = dispA; refAng = dispA; }
    else if (q === 2) { refFrom = dispA; refTo = 180; refAng = 180 - dispA; }
    else if (q === 3) { refFrom = 180;  refTo = dispA; refAng = dispA - 180; }
    else             { refFrom = dispA; refTo = 360; refAng = 360 - dispA; }
    if (refAng > 0.5) {
      const arcR = 48;
      const d = arc(CX, CY, arcR, refFrom, refTo);
      if (d) add(el('path', {d, fill:'none', stroke:'#94a3b8',
        'stroke-width':'1.5','stroke-dasharray':'4 3'}));
      const midA = (refFrom + refTo) / 2;
      add(txt(CX+(arcR+14)*Math.cos(rad(midA)), CY-(arcR+14)*Math.sin(rad(midA)),
        Math.round(refAng)+'°',
        {fill:'#94a3b8','font-size':'11','text-anchor':'middle'}));
    }
  }

  /* ── Angle arc from 0° to angle ────────────────────────────────────────── */
  if (dispA > 0.5 && dispA < 359.5) {
    const arcR = 28;
    const d = arc(CX, CY, arcR, 0, dispA);
    if (d) add(el('path', {d, fill:'none', stroke:'#1e293b', 'stroke-width':'1.2'}));
    const midA = dispA / 2;
    add(txt(CX+(arcR+16)*Math.cos(rad(midA)), CY-(arcR+16)*Math.sin(rad(midA)),
      dispA+'°', {fill:'#1e293b','font-size':'12','text-anchor':'middle'}));
  } else {
    add(txt(CX+48, CY-10, dispA+'°', {fill:'#1e293b','font-size':'12'}));
  }

  /* ── Radius line ────────────────────────────────────────────────────────── */
  add(el('line', {x1:CX,y1:CY,x2:px,y2:py,
    stroke:'#cbd5e1','stroke-width':'2'}));

  /* ── Sin segment ────────────────────────────────────────────────────────── */
  if (CFG.showPoint) {
    const sinColor  = CFG.showSin ? '#2563eb' : '#94a3b8';
    const sinDash   = CFG.showSin ? '' : '4 3';
    if (Math.abs(sinA) > 0.005) {
      add(el('line', {x1:px, y1:CY, x2:px, y2:py,
        stroke:sinColor, 'stroke-width': CFG.showSin ? '2' : '1',
        ...(sinDash ? {'stroke-dasharray':sinDash} : {})}));
      if (CFG.showSin) {
        const side = cosA >= 0 ? 1 : -1;
        const rawLabelX = px + side * 9;
        const labelX = cosA >= 0 ? Math.min(rawLabelX, 318) : Math.max(rawLabelX, 82);
        const anchor = cosA >= 0 ? 'start' : 'end';
        add(txt(labelX, (CY+py)/2, `sin ${dispA}°`,
          {fill:'#2563eb','font-size':'12','text-anchor':anchor}));
      }
    }

    /* ── Cos segment ──────────────────────────────────────────────────────── */
    const cosColor = CFG.showCos ? '#16a34a' : '#94a3b8';
    const cosDash  = CFG.showCos ? '' : '4 3';
    if (Math.abs(cosA) > 0.005) {
      add(el('line', {x1:CX, y1:py, x2:px, y2:py,
        stroke:cosColor, 'stroke-width': CFG.showCos ? '2' : '1',
        ...(cosDash ? {'stroke-dasharray':cosDash} : {})}));
      if (CFG.showCos) {
        const labelY = py + (sinA >= 0 ? -14 : 14);
        add(txt((CX+px)/2, labelY, `cos ${dispA}°`,
          {fill:'#16a34a','font-size':'12','text-anchor':'middle'}));
      }
    }

    /* ── Coordinates label near P ─────────────────────────────────────────── */
    if (CFG.showCoords) {
      const offX = cosA >= 0 ? 16 : -16;
      const offY = sinA >= 0 ? -16 :  16;
      add(txt(px+offX, py+offY, `(${fmt('c',a)}, ${fmt('s',a)})`,
        {fill:'#1e293b','font-size':'11','text-anchor': cosA >= 0 ? 'start' : 'end'}));
    }
  }

  /* ── Tan segment ────────────────────────────────────────────────────────── */
  if (CFG.showTan) {
    const tanX = CX + R;
    if (Math.abs(cosA) < 0.01) {
      add(txt(tanX+8, CY-20, 'tan undef',
        {fill:'#ea580c','font-size':'12','text-anchor':'start'}));
    } else {
      const tanV = sinA / cosA;
      const Ty = CY - R * tanV;
      /* extended radius (dashed) */
      add(el('line', {x1:CX,y1:CY,x2:tanX,y2:Ty,
        stroke:'#2563eb','stroke-width':'1','stroke-dasharray':'4 3'}));
      /* tangent reference line at x=1 */
      const pad = 14;
      add(el('line', {x1:tanX,y1:Math.min(CY,Ty)-pad,
                      x2:tanX,y2:Math.max(CY,Ty)+pad,
        stroke:'#ea580c','stroke-width':'1','stroke-dasharray':'3 3',opacity:'0.4'}));
      /* orange segment */
      add(el('line', {x1:tanX,y1:CY,x2:tanX,y2:Ty,
        stroke:'#ea580c','stroke-width':'2.5'}));
      /* T point + label */
      add(el('circle', {cx:tanX,cy:Ty,r:'4',fill:'#ea580c'}));
      add(txt(tanX+9, Ty-8, 'T', {fill:'#ea580c','font-size':'12','text-anchor':'start'}));
      add(txt(tanX+9, (CY+Ty)/2, `tan ${dispA}° = ${fmt('t',a)}`,
        {fill:'#ea580c','font-size':'12','text-anchor':'start'}));
    }
  }

  /* ── Point P ────────────────────────────────────────────────────────────── */
  if (CFG.showPoint) {
    const ptEl = add(el('circle', {cx:px, cy:py, r:'5', fill:'#2563eb', id:'pt-p'}));
    if (snapping) {
      ptEl.classList.add('snap-flash');
      setTimeout(() => ptEl.classList.remove('snap-flash'), 220);
    }
    const lx = px + (cosA >= 0 ? 10 : -10);
    const ly = py + (sinA >= 0 ? -11 : 11);
    add(txt(lx, ly, CFG.labelP,
      {fill:'#1e293b','font-size':'13','font-weight':'bold',
       'text-anchor': cosA >= 0 ? 'start' : 'end'}));
  }

  /* ── Readout panel ──────────────────────────────────────────────────────── */
  const ro = document.getElementById('readout');
  if (!CFG.locked) {
    const sv = fmt('s',a), cv = fmt('c',a);
    let parts = `θ = ${dispA}° sin θ = ${sv} cos θ = ${cv}`;
    if (CFG.showTan) parts += ` tan θ = ${fmt('t',a)}`;
    ro.textContent = parts;
  }
}

/* ── Drag handling ──────────────────────────────────────────────────────── */
function setupDrag() {
  if (CFG.locked) return;
  const svg = document.getElementById('uc');

  function getAngle(e) {
    const rect = svg.getBoundingClientRect();
    const sx = 400 / rect.width, sy = 400 / rect.height;
    const cx = e.touches ? e.touches[0].clientX : e.clientX;
    const cy = e.touches ? e.touches[0].clientY : e.clientY;
    let a = Math.atan2(-((cy - rect.top)*sy - CY), (cx - rect.left)*sx - CX) * 180 / Math.PI;
    if (a < 0) a += 360;
    return a;
  }

  function snapTo(a) {
    let best = a, bestD = Infinity;
    for (const s of SNAP) {
      let d = Math.abs(a - s); if (d > 180) d = 360 - d;
      if (d < bestD) { bestD = d; best = s; }
    }
    return bestD < 4 ? best : a;
  }

  let dragging = false;

  function onDown(e) {
    const rect = svg.getBoundingClientRect();
    const sx = 400/rect.width, sy = 400/rect.height;
    const cx = e.touches ? e.touches[0].clientX : e.clientX;
    const cy = e.touches ? e.touches[0].clientY : e.clientY;
    const mx = (cx - rect.left)*sx, my = (cy - rect.top)*sy;
    if (Math.hypot(mx - ptX(angle), my - ptY(angle)) < 22) {
      dragging = true; e.preventDefault();
    }
  }

  function onMove(e) {
    if (!dragging) return;
    e.preventDefault();
    const raw = getAngle(e);
    const snapped = snapTo(raw);
    snapping = Math.abs(snapped - raw) < 0.1;
    angle = snapped;
    draw();
  }

  function onUp() { dragging = false; snapping = false; }

  svg.addEventListener('mousedown',  onDown);
  svg.addEventListener('touchstart', onDown, {passive:false});
  window.addEventListener('mousemove',  onMove);
  window.addEventListener('touchmove',  onMove, {passive:false});
  window.addEventListener('mouseup',    onUp);
  window.addEventListener('touchend',   onUp);
}

draw();
setupDrag();
</script>
</body>
</html>"""


def render(d: UnitCircleDiagram) -> str:
    cfg = json.dumps({
        'angle':     d.angle,
        'showPoint':  d.show_point,
        'showCoords': d.show_coords,
        'showSin':    d.show_sin,
        'showCos':   d.show_cos,
        'showTan':   d.show_tan,
        'showRef':   d.show_reference_angle,
        'showQLbls': d.show_quadrant_labels,
        'hlQ':       d.highlight_quadrant,
        'labelP':    d.label_point,
        'locked':    d.lock_angle,
    })
    return _HTML.replace('__CONFIG__', cfg)
