import { parseClock, renderClock } from "./clock";
import { parseRect, renderRect } from "./rect";
import { parseCartesian, renderCartesian } from "./cartesian";
import { parseAngle, renderAngle } from "./angle";
import { parseTriangle, renderTriangle } from "./triangle";


export function renderDiagramFromCode(code: string): string {
  const lines = code.split("\n").map(l => l.trim()).filter(Boolean);

  const fragments: string[] = [];

  for (const line of lines) {
    if (line.startsWith("Clock")) {
      const parsed = parseClock(line);
      if (parsed) fragments.push(renderClock(parsed));
      continue;
    }

    if (line.startsWith("Rect")) {
      const parsed = parseRect(line);
      if (parsed) fragments.push(renderRect(parsed));
      continue;
    }

    if (line.startsWith("Cartesian")) {
      const parsed = parseCartesian(line);
      if (parsed) fragments.push(renderCartesian(parsed));
      continue;
    }

    if (line.startsWith("Angle")) {
      const parsed = parseAngle(line);
      if (parsed) fragments.push(renderAngle(parsed));
      continue;
    }

    if (line.startsWith("Triangle")) {
      const parsed = parseTriangle(line);
      if (parsed) fragments.push(renderTriangle(parsed));
      continue;
    }

    // future diagram types go here
  }

  // Wrap all fragments in one SVG
  return `
<svg width="400" height="240" viewBox="-25 -15 50 30" xmlns="http://www.w3.org/2000/svg">
  ${fragments.join("\n")}
</svg>
  `;
}