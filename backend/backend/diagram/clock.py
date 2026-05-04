import math
import re
from dataclasses import dataclass
from typing import Optional, Tuple

DIAGRAM_TYPE = "Clock"

# Clock(time: 10:00, pos: (0, 0))

@dataclass
class ClockDiagram:
    type: str
    time: str
    pos: Tuple[int, int]


CLOCK_REGEX = re.compile(
    r"Clock\s*\(\s*time:\s*([0-9]{1,2}:[0-9]{2})\s*,\s*pos:\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*\)"
)

def parse(line: str) -> Optional[ClockDiagram]:
    match = CLOCK_REGEX.match(line)
    if not match:
        return None

    time_str = match.group(1)
    x = int(match.group(2))
    y = int(match.group(3))

    return ClockDiagram(type="Clock", time=time_str, pos=(x, y))


def render(clock: ClockDiagram) -> str:
    hour_str, minute_str = clock.time.split(":")
    hour = int(hour_str) % 12
    minute = int(minute_str)

    minute_angle = (minute / 60) * 360
    hour_angle = (hour / 12) * 360 + (minute / 60) * 30

    r = 10
    px, py = clock.pos

    hour_rad = math.radians(hour_angle)
    minute_rad = math.radians(minute_angle)

    hour_x = px + (r * 0.5) * math.sin(hour_rad)
    hour_y = py - (r * 0.5) * math.cos(hour_rad)

    minute_x = px + (r * 0.8) * math.sin(minute_rad)
    minute_y = py - (r * 0.8) * math.cos(minute_rad)

    return f"""
    <circle cx="{px}" cy="{py}" r="{r}" stroke="black" fill="white" stroke-width="0.5" />
    <line x1="{px}" y1="{py}"
          x2="{hour_x}" y2="{hour_y}"
          stroke="black" stroke-width="0.7" />
    <line x1="{px}" y1="{py}"
          x2="{minute_x}" y2="{minute_y}"
          stroke="black" stroke-width="0.4" />
    """