export interface RectDiagram {
  type: "Rect";
  x: number;
  y: number;
  pos: [number, number];
}

export function parseRect(line: string): RectDiagram | null {
  const regex =
    /Rect\s*\(\s*x:\s*([^,]+)\s*,\s*y:\s*([^,]+)\s*,\s*pos:\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*\)/;

  const match = line.match(regex);
  if (!match) return null;

  return {
    type: "Rect",
    x: parseFloat(match[1].trim()),
    y: parseFloat(match[2].trim()),
    pos: [parseFloat(match[3]), parseFloat(match[4])],
  };
}


export function renderRect({ x, y, pos }: RectDiagram): string {
  const [px, py] = pos;

  // SVG <rect> uses top-left corner, so convert centre → corner
  const x0 = px - x / 2;
  const y0 = py - y / 2;

  return `
    <rect
      x="${x0}"
      y="${y0}"
      width="${x}"
      height="${y}"
      fill="none"
      stroke="black"
      stroke-width="0.5"
    />
  `;
}