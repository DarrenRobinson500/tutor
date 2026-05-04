import json
import re
import random
from datetime import datetime, timedelta, time, date
from django.utils import timezone
local_tz = timezone.get_default_timezone()

CONTENT_METADATA_KEYS = {"title", "years", "difficulty", "skill_id"}

def format_for_editor(obj: dict) -> str:
    """Convert an AI-generated template dict to canonical YAML for the render engine.
    Metadata fields (title, years, difficulty, skill_id) are intentionally excluded —
    they are saved on the Template model, not duplicated in the content."""
    import yaml

    KEY_ORDER = ["parameters", "question", "answers", "solution",
                 "diagram", "validation", "introduction", "worked_example"]

    ordered = {k: obj[k] for k in KEY_ORDER if k in obj}
    # Append any unexpected non-metadata keys at the end
    for k, v in obj.items():
        if k not in ordered and k not in CONTENT_METADATA_KEYS:
            ordered[k] = v

    return yaml.dump(ordered, allow_unicode=True, default_flow_style=False, sort_keys=False)


def generate_week(tutor_user, tutor_profile, week_start):
    week = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        week.append({
            "date": day_date,
            "availability": [],
            "blocked": False,
            "bookings": [],
            "bookable_slots": [],
            "segments": []  # for the graphical view
        })
    return week

def get_sunday_start(date):
    weekday = date.weekday()  # Monday=0 ... Sunday=6
    days_since_sunday = (weekday + 1) % 7
    return date - timedelta(days=days_since_sunday)

def format_mobile(mobile: str) -> str:
    if not mobile: return ""
    digits = "".join(filter(str.isdigit, mobile))
    if len(digits) == 10:
        return f"{digits[0:4]} {digits[4:7]} {digits[7:10]}"
    return mobile

def str_to_date(date_str):
    date_str = date_str.replace("Z", "+00:00")
    # print("Str to Date:", date_str)
    dt = datetime.fromisoformat(date_str)
    # print("Str to Date:", dt)
    if dt.tzinfo is None: dt = timezone.make_aware(dt, local_tz)
    # print("Str to Date (aware):", dt)
    dt = timezone.localtime(dt, local_tz)
    print("Str to Date (local):", dt)
    return dt


def format_sms_datetime(iso_str):
    # print("Format sms datetime (input):", iso_str)
    dt = datetime.fromisoformat(iso_str)
    weekday = dt.strftime("%a")
    day = dt.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    day_str = f"{day}{suffix}"
    month = dt.strftime("%B")
    time_str = dt.strftime("%I:%M%p").lower()
    return f"{weekday}, {day_str} {month} at {time_str}."

def format_sms_datetime_django(dt):
    weekday = dt.strftime("%a")
    day = dt.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    day_str = f"{day}{suffix}"
    month = dt.strftime("%B")
    time_str = dt.strftime("%I:%M%p").lstrip("0").lower()

    return f"{weekday}, {day_str} {month} at {time_str}."



def get_times(start_time_str, duration):
    start_time_str = start_time_str.strip()
    if len(start_time_str) == 8 and start_time_str.count(":") == 2:
        start_time_str = start_time_str[:5]
    start_time = datetime.strptime(start_time_str, "%H:%M").time()

    # Compute end time
    end_dt = datetime.combine(date.today(), start_time) + timedelta(minutes=duration)
    end_time = end_dt.time()

    return start_time, end_time


def get_datetimes(start_datetime_str, duration):
    start_dt = str_to_date(start_datetime_str)
    end_dt = start_dt + timedelta(minutes=duration)
    print("Get datetimes:", start_dt, end_dt)
    return start_dt, end_dt

def _eval_arithmetic_in_json(text: str) -> str:
    """Replace bare arithmetic expressions used as JSON values (e.g. 5 / 9) with their evaluated result."""
    def _repl(m):
        expr = m.group(0)
        try:
            result = eval(expr, {"__builtins__": {}}, {})  # noqa: S307
            return repr(float(result))
        except Exception:
            return expr
    # Match numeric arithmetic expressions: numbers combined with +, -, *, / (and optional parens)
    return re.sub(r"-?\d+(?:\s*[-+*/]\s*-?\d+)+", _repl, text)


def extract_json(text: str):
    if not text or not text.strip():
        raise ValueError("AI returned empty response")

    # Remove markdown fences
    text = text.strip()
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Retry after evaluating bare arithmetic expressions (e.g. "value": 5 / 9)
    fixed = _eval_arithmetic_in_json(text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try to extract a JSON array [...] block first, then fall back to {...}
    for candidate in (fixed, text):
        for pattern in (r"\[.*\]", r"\{.*\}"):
            match = re.search(pattern, candidate, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

    raise ValueError(f"Could not parse JSON from AI output:\n{text}")

def maths_stage(year) -> str:
    if year in ["K", "k", 0]: return "Early Stage 1"
    year = int(year)
    if year in (1, 2): return "Stage 1"
    if year in (3, 4): return "Stage 2"
    if year in (5, 6): return "Stage 3"
    if year in (7, 8): return "Stage 4"
    if year in (9, 10): return "Stage 5"
    raise ValueError("Year must be K or 1–10")

def time_diff(start_time, end_time):
    start_dt = datetime.combine(date.today(), start_time)
    end_dt = datetime.combine(date.today(), end_time)
    return end_dt - start_dt
