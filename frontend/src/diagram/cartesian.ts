export interface CartesianDiagram {
  type: "Cartesian";
  xmin: number;
  xmax: number;
  ymin: number;
  ymax: number;
  eq: string;           // JS math expression with x as variable, e.g. "x**2" or "sin(x)"
  pos: [number, number]; // centre of the diagram in SVG logical units
  w: number;             // width in SVG logical units
  h: number;             // height in SVG logical units
  square: boolean;       // when true, x range is derived so 1 unit = same physical length on both axes
}

// Syntax: Cartesian(xmin: -5, xmax: 5, ymin: -4, ymax: 4, eq: "x**2")
// Optional: pos: (0, 0), w: 44, h: 26, square: true
export function parseCartesian(line: string): CartesianDiagram | null {
  const getNum = (key: string): number | null => {
    const m = line.match(new RegExp(`\\b${key}:\\s*(-?[\\d.]+)`));
    return m ? parseFloat(m[1]) : null;
  };

  // eq must be quoted to handle expressions containing commas or parens
  const eqMatch    = line.match(/\beq:\s*"([^"]+)"/);
  const posMatch   = line.match(/\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)/);
  const squareMatch = line.match(/\bsquare:\s*(true|false)/);

  const xmin = getNum("xmin");
  const xmax = getNum("xmax");
  const ymin = getNum("ymin");
  const ymax = getNum("ymax");
  const w = getNum("w");
  const h = getNum("h");
  const eq = eqMatch?.[1];
  const pos: [number, number] = posMatch
    ? [parseFloat(posMatch[1]), parseFloat(posMatch[2])]
    : [0, 0];

  if (xmin === null || xmax === null || ymin === null || ymax === null || !eq) return null;

  return {
    type: "Cartesian",
    xmin, xmax, ymin, ymax, eq,
    pos,
    w: w ?? 44,
    h: h ?? 26,
    square: squareMatch ? squareMatch[1] === "true" : false,
  };
}

// Choose a human-friendly step size for ~n divisions
function niceStep(approx: number): number {
  if (approx <= 0) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(approx)));
  const norm = approx / mag;
  if (norm < 1.5) return mag;
  if (norm < 3.5) return 2 * mag;
  if (norm < 7.5) return 5 * mag;
  return 10 * mag;
}

function fmtTick(n: number): string {
  if (Math.abs(n) < 1e-9) return "0";
  // Remove trailing zeros after decimal
  return parseFloat(n.toPrecision(4)).toString();
}

export function renderCartesian({
  xmin: xminIn, xmax: xmaxIn, ymin, ymax, eq, pos, w, h, square,
}: CartesianDiagram): string {
  // In square mode derive x range from y scale so 1 unit is equal length on both axes
  const xmin = square ? (xminIn + xmaxIn) / 2 - (w * (ymax - ymin)) / (2 * h) : xminIn;
  const xmax = square ? (xminIn + xmaxIn) / 2 + (w * (ymax - ymin)) / (2 * h) : xmaxIn;

  const [cx, cy] = pos;
  const L = cx - w / 2;  // SVG left edge
  const R = cx + w / 2;  // SVG right edge
  const T = cy - h / 2;  // SVG top edge
  const B = cy + h / 2;  // SVG bottom edge

  // Map math coords → SVG coords (y is flipped)
  const toSvgX = (x: number) => L + ((x - xmin) / (xmax - xmin)) * w;
  const toSvgY = (y: number) => B - ((y - ymin) / (ymax - ymin)) * h;

  // Axis lines in SVG space, clamped to plot area
  const axisY = Math.max(T, Math.min(B, toSvgY(0))); // horizontal (y=0) line
  const axisX = Math.max(L, Math.min(R, toSvgX(0))); // vertical  (x=0) line

  const sw = 0.25;
  const tickLen = 0.8;
  const fontSize = 1.8;
  const xStep = niceStep((xmax - xmin) / 8);
  const yStep = niceStep((ymax - ymin) / 6);
  const xGridStart = Math.ceil(xmin / xStep) * xStep;
  const yGridStart = Math.ceil(ymin / yStep) * yStep;

  // Unique clip-path id based on position (no special chars)
  const clipId = `cc${String(cx).replace(/[^a-z0-9]/gi, "_")}${String(cy).replace(/[^a-z0-9]/gi, "_")}`;

  const out: string[] = [];

  // ── Clip path ────────────────────────────────────────────────────────────
  out.push(
    `<defs><clipPath id="${clipId}">` +
    `<rect x="${L}" y="${T}" width="${w}" height="${h}"/>` +
    `</clipPath></defs>`
  );

  // ── Background ───────────────────────────────────────────────────────────
  out.push(
    `<rect x="${L}" y="${T}" width="${w}" height="${h}" fill="white" stroke="#aaa" stroke-width="${sw}"/>`
  );

  // ── Grid lines ───────────────────────────────────────────────────────────
  for (let x = xGridStart; x <= xmax + xStep * 0.01; x += xStep) {
    const sx = toSvgX(x);
    out.push(`<line x1="${sx}" y1="${T}" x2="${sx}" y2="${B}" stroke="#e0e0e0" stroke-width="${sw}"/>`);
  }
  for (let y = yGridStart; y <= ymax + yStep * 0.01; y += yStep) {
    const sy = toSvgY(y);
    out.push(`<line x1="${L}" y1="${sy}" x2="${R}" y2="${sy}" stroke="#e0e0e0" stroke-width="${sw}"/>`);
  }

  // ── Axes ─────────────────────────────────────────────────────────────────
  const axSw = sw * 1.5;
  out.push(`<line x1="${L}" y1="${axisY}" x2="${R}" y2="${axisY}" stroke="black" stroke-width="${axSw}"/>`);
  out.push(`<line x1="${axisX}" y1="${T}" x2="${axisX}" y2="${B}" stroke="black" stroke-width="${axSw}"/>`);

  // Arrowheads at positive ends
  const aw = 0.7, ah = 1.2;
  out.push(`<polygon points="${R},${axisY} ${R - ah},${axisY - aw / 2} ${R - ah},${axisY + aw / 2}" fill="black"/>`);
  out.push(`<polygon points="${axisX},${T} ${axisX - aw / 2},${T + ah} ${axisX + aw / 2},${T + ah}" fill="black"/>`);

  // Axis labels
  out.push(`<text x="${R + 0.3}" y="${axisY + fontSize * 0.4}" font-size="${fontSize}" font-family="serif" font-style="italic" fill="black">x</text>`);
  out.push(`<text x="${axisX - fontSize * 0.3}" y="${T - 0.5}" text-anchor="middle" font-size="${fontSize}" font-family="serif" font-style="italic" fill="black">y</text>`);

  // ── Tick marks & labels ──────────────────────────────────────────────────
  const labelOffset = tickLen + fontSize * 0.85;

  // X-axis ticks
  for (let x = xGridStart; x <= xmax + xStep * 0.01; x += xStep) {
    if (Math.abs(x) < xStep * 0.01) continue; // skip origin
    const sx = toSvgX(x);
    out.push(`<line x1="${sx}" y1="${axisY - tickLen / 2}" x2="${sx}" y2="${axisY + tickLen / 2}" stroke="black" stroke-width="${sw}"/>`);
    out.push(`<text x="${sx}" y="${axisY + labelOffset}" text-anchor="middle" font-size="${fontSize}" font-family="sans-serif" fill="#333">${fmtTick(x)}</text>`);
  }

  // Y-axis ticks
  for (let y = yGridStart; y <= ymax + yStep * 0.01; y += yStep) {
    if (Math.abs(y) < yStep * 0.01) continue; // skip origin
    const sy = toSvgY(y);
    out.push(`<line x1="${axisX - tickLen / 2}" y1="${sy}" x2="${axisX + tickLen / 2}" y2="${sy}" stroke="black" stroke-width="${sw}"/>`);
    out.push(`<text x="${axisX - tickLen - 0.3}" y="${sy + fontSize * 0.35}" text-anchor="end" font-size="${fontSize}" font-family="sans-serif" fill="#333">${fmtTick(y)}</text>`);
  }

  // Origin label (only when both axes are inside the plot)
  if (xmin < 0 && xmax > 0 && ymin < 0 && ymax > 0) {
    out.push(`<text x="${axisX - 0.4}" y="${axisY + labelOffset}" text-anchor="end" font-size="${fontSize}" font-family="sans-serif" fill="#333">0</text>`);
  }

  // ── Plot equation ────────────────────────────────────────────────────────
  try {
    // Replace ^ with ** so teachers can write x^2 instead of x**2
    const normalised = eq.replace(/\^/g, "**");
    // Use with(Math) so sin/cos/sqrt etc. work without Math. prefix
    // eslint-disable-next-line no-new-func
    const evalFn = new Function("x", `with(Math){ return (${normalised}); }`) as (x: number) => number;

    const STEPS = 400;
    const paths: string[][] = [];
    let current: string[] = [];

    for (let i = 0; i <= STEPS; i++) {
      const x = xmin + (xmax - xmin) * (i / STEPS);
      let y: number;
      try {
        y = evalFn(x);
      } catch {
        if (current.length > 1) paths.push(current);
        current = [];
        continue;
      }

      if (!isFinite(y) || isNaN(y)) {
        if (current.length > 1) paths.push(current);
        current = [];
        continue;
      }

      const sx = toSvgX(x).toFixed(3);
      const sy = toSvgY(y).toFixed(3);
      current.push(current.length === 0 ? `M${sx},${sy}` : `L${sx},${sy}`);
    }
    if (current.length > 1) paths.push(current);

    for (const seg of paths) {
      out.push(
        `<path d="${seg.join(" ")}" fill="none" stroke="#2563eb" stroke-width="${sw * 2.5}" stroke-linejoin="round" clip-path="url(#${clipId})"/>`
      );
    }
  } catch {
    // Invalid equation — omit curve silently
  }

  return out.join("\n");
}
