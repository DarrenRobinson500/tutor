export interface AngleDiagram {
  type: "Angle";
  deg: number;
  pos: [number, number];
  size: number;
  displayLabel: boolean;
}

// Syntax: Angle(deg: 65)
// Optional: pos: (0, 0), size: 12, display_label: false
export function parseAngle(line: string): AngleDiagram | null {
  const degMatch   = line.match(/\bdeg:\s*([\d.]+)/);
  const posMatch   = line.match(/\bpos:\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)/);
  const sizeMatch  = line.match(/\bsize:\s*([\d.]+)/);
  const labelMatch = line.match(/\bdisplay_label:\s*(true|false)/);

  if (!degMatch) return null;
  const deg = parseFloat(degMatch[1]);
  if (deg <= 0 || deg >= 360) return null;

  return {
    type: "Angle",
    deg,
    pos:          posMatch   ? [parseFloat(posMatch[1]), parseFloat(posMatch[2])] : [0, 0],
    size:         sizeMatch  ? parseFloat(sizeMatch[1]) : 12,
    displayLabel: labelMatch ? labelMatch[1] === "true" : true,
  };
}

export function renderAngle({ deg, pos, size, displayLabel }: AngleDiagram): string {
  const [cx, cy] = pos;
  const rad    = (deg * Math.PI) / 180;
  const arcR   = size * 0.3;
  const labelR = arcR + 2.8;
  const sw     = 0.5;

  // Ray 1: horizontal right
  const r1x = cx + size;

  // Ray 2: deg° counterclockwise from Ray 1 (SVG y is flipped, so negate sin)
  const r2x = cx + size * Math.cos(rad);
  const r2y = cy - size * Math.sin(rad);

  // Arc end point at the same radius along Ray 2
  const axEnd    = cx + arcR * Math.cos(rad);
  const ayEnd    = cy - arcR * Math.sin(rad);
  const largeArc = deg > 180 ? 1 : 0;

  // Label at the angle bisector
  const bisRad = (deg / 2) * (Math.PI / 180);
  const lx = cx + labelR * Math.cos(bisRad);
  const ly = cy - labelR * Math.sin(bisRad);

  const parts = [
    `<line x1="${cx}" y1="${cy}" x2="${r1x}" y2="${cy}" stroke="black" stroke-width="${sw}" stroke-linecap="round"/>`,
    `<line x1="${cx}" y1="${cy}" x2="${r2x.toFixed(3)}" y2="${r2y.toFixed(3)}" stroke="black" stroke-width="${sw}" stroke-linecap="round"/>`,
    `<path d="M${cx + arcR},${cy} A${arcR},${arcR} 0 ${largeArc},0 ${axEnd.toFixed(3)},${ayEnd.toFixed(3)}" fill="none" stroke="black" stroke-width="${(sw * 0.65).toFixed(2)}"/>`,
  ];

  if (displayLabel) {
    parts.push(
      `<text x="${lx.toFixed(3)}" y="${ly.toFixed(3)}" text-anchor="middle" dominant-baseline="middle" font-size="2.8" font-family="sans-serif" fill="black">${deg}°</text>`
    );
  }

  return parts.join("\n  ");
}
