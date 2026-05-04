export interface ClockDiagram {
  type: "Clock";
  time: string;
  pos: [number, number];
}


export function parseClock(line: string): ClockDiagram | null {
  const regex = /Clock\s*\(\s*time:\s*([0-9]{1,2}:[0-9]{2})\s*,\s*pos:\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*\)/;

  const match = line.match(regex);
  if (!match) return null;

  return {
    type: "Clock",
    time: match[1],
    pos: [parseInt(match[2]), parseInt(match[3])]
  };
}

export function renderClock({ time, pos }: ClockDiagram): string {
  const [hourStr, minuteStr] = time.split(":");
  const hour = parseInt(hourStr) % 12;
  const minute = parseInt(minuteStr);

  const minuteAngle = (minute / 60) * 360;
  const hourAngle = (hour / 12) * 360 + (minute / 60) * 30;

  // Clock radius in logical units
  const r = 10;

  // Position offset
  const [px, py] = pos;

  return `
    <circle cx="${px}" cy="${py}" r="${r}" stroke="black" fill="white" stroke-width="0.5" />
    <line x1="${px}" y1="${py}"
          x2="${px + (r * 0.5) * Math.sin((hourAngle * Math.PI) / 180)}"
          y2="${py - (r * 0.5) * Math.cos((hourAngle * Math.PI) / 180)}"
          stroke="black" stroke-width="0.7" />
    <line x1="${px}" y1="${py}"
          x2="${px + (r * 0.8) * Math.sin((minuteAngle * Math.PI) / 180)}"
          y2="${py - (r * 0.8) * Math.cos((minuteAngle * Math.PI) / 180)}"
          stroke="black" stroke-width="0.4" />
  `;

}