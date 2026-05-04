export interface TriangleDiagram {
  type: "Triangle";
  a: number;          // side opposite vertex A (between B and C)
  b: number;          // side opposite vertex B (between A and C)
  c: number;          // side opposite vertex C (between A and B)
  ticksA: number;     // tick marks on side a (0–3)
  ticksB: number;     // tick marks on side b (0–3)
  ticksC: number;     // tick marks on side c (0–3)
  arcsA: number;      // arc indicators at vertex A (0–3)
  arcsB: number;      // arc indicators at vertex B (0–3)
  arcsC: number;      // arc indicators at vertex C (0–3)
  pos: [number, number];
  scale: number;      // SVG units per input unit
}

// Syntax: Triangle(a: 5, b: 7, c: 6)
// Optional: ticks_a: 1, ticks_b: 2, ticks_c: 0, arcs_A: 1, arcs_B: 2, arcs_C: 1
//           pos: (0, 0), scale: 1.5
export function parseTriangle(line: string): TriangleDiagram | null {
  const getNum = (key: string): number | null => {
    const m = line.match(new RegExp(`\\b${key}:\\s*(-?[\\d.]+)`));
    return m ? parseFloat(m[1]) : null;
  };

  const posMatch = line.match(/\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)/);

  const a = getNum("a");
  const b = getNum("b");
  const c = getNum("c");

  if (a === null || b === null || c === null) return null;
  // Triangle inequality
  if (a + b <= c || a + c <= b || b + c <= a) return null;

  return {
    type: "Triangle",
    a, b, c,
    ticksA: getNum("ticks_a") ?? 0,
    ticksB: getNum("ticks_b") ?? 0,
    ticksC: getNum("ticks_c") ?? 0,
    arcsA:  getNum("arcs_A")  ?? 0,
    arcsB:  getNum("arcs_B")  ?? 0,
    arcsC:  getNum("arcs_C")  ?? 0,
    pos:    posMatch ? [parseFloat(posMatch[1]), parseFloat(posMatch[2])] : [0, 0],
    scale:  getNum("scale") ?? 1.5,
  };
}

function tickMarks(
  x1: number, y1: number,
  x2: number, y2: number,
  count: number,
  sw: number,
): string {
  if (count <= 0) return "";

  // Midpoint and direction along the side
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  // Perpendicular unit vector
  const px = -dy / len;
  const py =  dx / len;

  const half = 1.0;   // half-length of each tick mark
  const gap  = 0.55;  // spacing between multiple ticks (along the side direction)
  const ux = dx / len;
  const uy = dy / len;

  const parts: string[] = [];
  const offsets =
    count === 1 ? [0] :
    count === 2 ? [-gap / 2, gap / 2] :
    [-gap, 0, gap];

  for (const off of offsets) {
    const cx = mx + ux * off;
    const cy = my + uy * off;
    parts.push(
      `<line x1="${(cx - px * half).toFixed(3)}" y1="${(cy - py * half).toFixed(3)}" ` +
      `x2="${(cx + px * half).toFixed(3)}" y2="${(cy + py * half).toFixed(3)}" ` +
      `stroke="black" stroke-width="${sw}" stroke-linecap="round"/>`
    );
  }
  return parts.join("\n");
}

function arcIndicators(
  cx: number, cy: number,
  angleFrom: number, angleTo: number,
  count: number,
  sw: number,
): string {
  if (count <= 0) return "";

  // SVG arc from angleFrom to angleTo (both in radians, measured CCW in math coords)
  // In SVG coords y is flipped so we negate y components.
  const BASE_R  = 2.2;
  const GAP_R   = 0.9;
  const parts: string[] = [];

  // Ensure we sweep the smaller angle
  let a1 = angleFrom;
  let a2 = angleTo;
  // Normalise so a2 > a1 and sweep < π (the interior angle)
  while (a2 < a1) a2 += 2 * Math.PI;
  const sweep = a2 - a1;
  const largeArc = sweep > Math.PI ? 1 : 0;

  for (let i = 0; i < count; i++) {
    const r = BASE_R + i * GAP_R;
    const sx1 = cx + r * Math.cos(a1);
    const sy1 = cy - r * Math.sin(a1);  // SVG y-flip
    const sx2 = cx + r * Math.cos(a2);
    const sy2 = cy - r * Math.sin(a2);
    parts.push(
      `<path d="M${sx1.toFixed(3)},${sy1.toFixed(3)} ` +
      `A${r},${r} 0 ${largeArc},0 ${sx2.toFixed(3)},${sy2.toFixed(3)}" ` +
      `fill="none" stroke="black" stroke-width="${(sw * 0.7).toFixed(2)}"/>`
    );
  }
  return parts.join("\n");
}

export function renderTriangle(d: TriangleDiagram): string {
  const { a, b, c, scale } = d;
  const [cx0, cy0] = d.pos;

  // Place vertex B at origin, C along +x axis
  // Side c is between A and B, side b is between A and C, side a is between B and C
  const Bx = 0, By = 0;
  const Cx = a, Cy = 0;

  // Law of cosines to find A (angle at B)
  const cosB = (a * a + c * c - b * b) / (2 * a * c);
  const Ax = c * cosB;
  const Ay = c * Math.sqrt(1 - cosB * cosB); // positive → upward in math coords

  // Centroid for centering
  const centX = (Ax + Bx + Cx) / 3;
  const centY = (Ay + By + Cy) / 3;

  // Scale and center at pos
  const toSvg = (x: number, y: number): [number, number] => [
    cx0 + (x - centX) * scale,
    cy0 - (y - centY) * scale,  // SVG y-flip
  ];

  const [svgAx, svgAy] = toSvg(Ax, Ay);
  const [svgBx, svgBy] = toSvg(Bx, By);
  const [svgCx, svgCy] = toSvg(Cx, Cy);

  const sw = 0.4;
  const out: string[] = [];

  // ── Sides ────────────────────────────────────────────────────────────────
  out.push(`<line x1="${svgBx.toFixed(3)}" y1="${svgBy.toFixed(3)}" x2="${svgCx.toFixed(3)}" y2="${svgCy.toFixed(3)}" stroke="black" stroke-width="${sw}" stroke-linecap="round"/>`);
  out.push(`<line x1="${svgAx.toFixed(3)}" y1="${svgAy.toFixed(3)}" x2="${svgCx.toFixed(3)}" y2="${svgCy.toFixed(3)}" stroke="black" stroke-width="${sw}" stroke-linecap="round"/>`);
  out.push(`<line x1="${svgAx.toFixed(3)}" y1="${svgAy.toFixed(3)}" x2="${svgBx.toFixed(3)}" y2="${svgBy.toFixed(3)}" stroke="black" stroke-width="${sw}" stroke-linecap="round"/>`);

  // ── Tick marks ───────────────────────────────────────────────────────────
  // side a: B–C
  out.push(tickMarks(svgBx, svgBy, svgCx, svgCy, d.ticksA, sw));
  // side b: A–C
  out.push(tickMarks(svgAx, svgAy, svgCx, svgCy, d.ticksB, sw));
  // side c: A–B
  out.push(tickMarks(svgAx, svgAy, svgBx, svgBy, d.ticksC, sw));

  // ── Angle arcs ───────────────────────────────────────────────────────────
  // At vertex A: angle between sides AB and AC (math angles: CCW from +x, with SVG y-flip)
  const angAtoB = Math.atan2(-(svgBy - svgAy), svgBx - svgAx);
  const angAtoC = Math.atan2(-(svgCy - svgAy), svgCx - svgAx);
  out.push(arcIndicators(svgAx, svgAy, Math.min(angAtoB, angAtoC), Math.max(angAtoB, angAtoC), d.arcsA, sw));

  // At vertex B: angle between sides BA and BC
  const angBtoA = Math.atan2(-(svgAy - svgBy), svgAx - svgBx);
  const angBtoC = Math.atan2(-(svgCy - svgBy), svgCx - svgBx);
  out.push(arcIndicators(svgBx, svgBy, Math.min(angBtoA, angBtoC), Math.max(angBtoA, angBtoC), d.arcsB, sw));

  // At vertex C: angle between sides CA and CB
  const angCtoA = Math.atan2(-(svgAy - svgCy), svgAx - svgCx);
  const angCtoB = Math.atan2(-(svgBy - svgCy), svgBx - svgCx);
  out.push(arcIndicators(svgCx, svgCy, Math.min(angCtoA, angCtoB), Math.max(angCtoA, angCtoB), d.arcsC, sw));

  return out.filter(Boolean).join("\n");
}
