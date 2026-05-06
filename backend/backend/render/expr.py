import re
from .param import *
from .engine import *
from ..maths.units import unit_multiplier


def _is_fraction_string(v):
    """Return True if v is a string that represents a numeric value or fraction (e.g. '3/5', '14')."""
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        pass
    parts = v.split('/')
    if len(parts) == 2:
        try:
            int(parts[0].strip())
            int(parts[1].strip())
            return True
        except (ValueError, TypeError):
            pass
    return False


# Functions available in expressions that reference non-numeric string params.

def _repeat(value, count, sep=""):
    """Repeat *value* *count* times, joined by *sep*.

    Example: repeat(A, n, '×') with A='a', n=4  →  'a×a×a×a'
    Useful for index-notation questions:
        question: Write in index notation: {{ repeat(A, n, ' × ') }}
        answer: {{ A }}^{{ n }}
    """
    return sep.join([str(value)] * int(count))


_STRING_CONTEXT = {
    "unit_multiplier": unit_multiplier,
    "repeat": _repeat,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "abs": abs,
}


# ── Maths helper functions ───────────────────────────────────────────────────

def round_dp(value, places):
    """Round *value* to *places* decimal places.

    Uses decimal arithmetic when the input is a string to avoid floating-point
    representation errors (e.g. '3.55' rounded to 1dp gives 3.6, not 3.5).
    Example: round_dp('3.55', 1) → 3.6,  round_dp(3.74, 1) → 3.7
    """
    from decimal import Decimal, ROUND_HALF_UP
    places = int(places)
    if isinstance(value, str):
        try:
            d = Decimal(value.strip())
            quant = Decimal('1.' + '0' * places) if places > 0 else Decimal('1')
            return float(d.quantize(quant, rounding=ROUND_HALF_UP))
        except Exception:
            pass
    return round(float(value), places)


def decimal_digit(value, position):
    """Return the digit at decimal *position* (1 = tenths, 2 = hundredths, …).

    Works with numeric strings (e.g. '3.74' from DecimalParameter).
    Example: decimal_digit(3.74, 2) → 4
    """
    s = f"{float(value):.{int(position)}f}"
    parts = s.split(".")
    if len(parts) < 2 or int(position) > len(parts[1]):
        return 0
    return int(parts[1][int(position) - 1])


def _gcd(a, b):
    from math import gcd
    return gcd(int(a), int(b))

def _lcm(a, b):
    from math import gcd
    a, b = int(a), int(b)
    return a * b // gcd(a, b)

def _simplified_ratio(a, b):
    """Return the ratio a:b in simplified form as a string, e.g. simplified_ratio(4, 8) → '1:2'."""
    from math import gcd
    a, b = int(a), int(b)
    divisor = gcd(abs(a), abs(b)) or 1
    return f"{a // divisor}:{b // divisor}"

def _gaussian_list(mean, sd, count, sort=False):
    """Generate a list of *count* integers drawn from N(mean, sd), adjusted to hit the exact integer mean.

    Example: gaussian_list(20, 2, 8) → [17, 19, 20, 21, 22, 20, 18, 23]
    Use {{ data | sorted }} to display in order.
    """
    import random as _random
    mean, sd, count = float(mean), float(sd), int(count)
    values = [round(_random.gauss(mean, sd)) for _ in range(count)]
    target_sum = round(mean * count)
    for _ in range(200):
        diff = target_sum - sum(values)
        if diff == 0:
            break
        i = _random.randrange(count)
        values[i] += 1 if diff > 0 else -1
    if sort:
        values.sort()
    return values

import math as _math

_MATH_CONTEXT = {
    "pi":              _math.pi,
    "e":               _math.e,
    "sqrt":            _math.sqrt,
    "ceil":            _math.ceil,
    "floor":           _math.floor,
    "sin":             _math.sin,
    "cos":             _math.cos,
    "tan":             _math.tan,
    "asin":            _math.asin,
    "acos":            _math.acos,
    "atan":            _math.atan,
    "atan2":           _math.atan2,
    "log":             _math.log,
    "log10":           _math.log10,
    "degrees":         _math.degrees,
    "radians":         _math.radians,
    "round":           round,
    "round_dp":        round_dp,
    "decimal_digit":   decimal_digit,
    "gcd":             _gcd,
    "lcm":             _lcm,
    "simplified_ratio": _simplified_ratio,
    "gaussian_list":   _gaussian_list,
    "repeat":          _repeat,
}


def _to_python(v):
    """Convert a stored value (possibly a numeric string like '3.74') to a Python number."""
    if isinstance(v, str):
        try:
            f = float(v)
            return int(f) if f == int(f) else f
        except (ValueError, TypeError):
            pass
    return v


# ── List helper functions ────────────────────────────────────────────────────
# Exported so render.py can include them in validation rule contexts.

def list_mode(lst):
    """Return the most frequent value; first encountered on a tie."""
    counts = {}
    for v in lst:
        counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)

def list_median(lst):
    """Return the median; returns a float for even-length lists."""
    s = sorted(lst)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2

def list_mean(lst):
    from fractions import Fraction
    return Fraction(sum(lst), len(lst))

def list_range(lst):
    return max(lst) - min(lst)

def list_quartile(lst, q):
    """Return Q1 (q=1) or Q3 (q=3) using the exclusive method.

    The list is sorted and split at the median; for odd-length lists the
    median value itself is excluded from both halves.
    Q1 = median of the lower half, Q3 = median of the upper half.
    """
    if q not in (1, 2, 3):
        raise ValueError(f"quartile() expects q=1, q=2, or q=3, got q={q}")
    if q == 2:
        return list_median(lst)
    s = sorted(lst)
    n = len(s)
    mid = n // 2
    lower = s[:mid]
    upper = s[mid + 1:] if n % 2 else s[mid:]
    return list_median(lower if q == 1 else upper)

def list_stdev(lst):
    """Sample standard deviation (divides by n−1)."""
    n = len(lst)
    if n < 2:
        raise ValueError("stdev requires at least 2 values")
    m = sum(lst) / n
    return _math.sqrt(sum((x - m) ** 2 for x in lst) / (n - 1))

def list_pop_stdev(lst):
    """Population standard deviation (divides by n)."""
    n = len(lst)
    m = sum(lst) / n
    return _math.sqrt(sum((x - m) ** 2 for x in lst) / n)

_LIST_CONTEXT = {
    "mode":      list_mode,
    "median":    list_median,
    "mean":      list_mean,
    "range_of":  list_range,
    "quartile":  list_quartile,
    "stdev":     list_stdev,
    "pop_stdev": list_pop_stdev,
    "sorted":   sorted,
    "sum":      sum,
    "min":      min,
    "max":      max,
    "len":      len,
}

class ExpressionNode:
    def __init__(self, raw_expr, params=None):
        self.original_expr = raw_expr.strip()
        self.params = params or {}  # dict of RandomParameter objects

        self.raw_expr = None
        self.format_type = None
        self.format_options = {}

        self._parse()
        self.evaluate()
        self.output = self.format()

    def __str__(self):
        return f"{self.original_expr} -> {self.output}"

    def _parse(self):
        expr = self.original_expr

        if "|" in expr:
            expr_part, format_part = map(str.strip, expr.split("|", 1))
        else:
            expr_part = expr
            format_part = None

        self.raw_expr = expr_part
        self.format_type, self.format_options = self._parse_format(format_part)

    @staticmethod
    def _parse_format(format_part):
        if not format_part:
            return None, {}

        if "(" not in format_part:
            return format_part, {}

        name, args = format_part.split("(", 1)
        name = name.strip()
        args = args.rstrip(")")

        options = {}
        for item in args.split(","):
            key, val = map(str.strip, item.split("="))
            options[key] = val

        return name, options

    def evaluate(self):
        # 1. Generate values from parameter objects
        value_map = {}
        for name, param in self.params.items():
            value_map[name] = param.value

        # 1b. Bare fraction variable — preserve string form so formatters render unsimplified.
        # e.g. b: 9/12 stored as "9/12"; {{ b | fraction }} → \frac{9}{12} not \frac{3}{4}.
        bare = self.raw_expr.strip()
        if bare in self.params:
            pv = self.params[bare].value
            if isinstance(pv, str) and "/" in pv and _is_fraction_string(pv):
                self.evaluated_value = pv
                return self.evaluated_value

        # Normalise ^ → ** so exponentiation works across all eval paths.
        self.raw_expr = self.raw_expr.replace('^', '**')

        # 2. If any referenced variable is a list, use Python eval with list functions
        list_vars = {k for k, v in value_map.items() if isinstance(v, list)}
        if list_vars and any(re.search(rf'\b{re.escape(k)}\b', self.raw_expr) for k in list_vars):
            ctx = dict(_LIST_CONTEXT)
            ctx.update(_MATH_CONTEXT)
            ctx["__builtins__"] = {}
            ctx.update(value_map)
            self.evaluated_value = eval(self.raw_expr, ctx)
            return self.evaluated_value

        # 2b. If any referenced variable is a non-numeric string (e.g. unit prefix, name),
        #     use Python eval so string values and utility functions are available.
        # Exclude operator strings like "+", "-", "*", "/" — these are substituted
        # directly into the expression in step 3 so sympy can evaluate them.
        def _is_operator_string(v):
            return isinstance(v, str) and v.strip() in ('+', '-', '*', '/', '^', '**', '×', '÷')
        str_vars = {k for k, v in value_map.items()
                    if isinstance(v, str) and not _is_fraction_string(v) and not _is_operator_string(v)}
        if str_vars and any(re.search(rf'\b{re.escape(k)}\b', self.raw_expr) for k in str_vars):
            ctx = dict(_LIST_CONTEXT)
            ctx.update(_STRING_CONTEXT)
            ctx.update(_MATH_CONTEXT)
            ctx["__builtins__"] = {}
            ctx.update(value_map)
            self.evaluated_value = eval(self.raw_expr, ctx)  # noqa: S307
            return self.evaluated_value

        # 2c. Python ternary (expr if cond else expr) — use Python eval with Fraction comparison
        if ' if ' in self.raw_expr and ' else ' in self.raw_expr:
            from fractions import Fraction as _Frac
            def _to_frac_or_python(v):
                if isinstance(v, str) and '/' in v and _is_fraction_string(v):
                    try:
                        return _Frac(v)
                    except (ValueError, ZeroDivisionError):
                        pass
                return _to_python(v)
            ctx = dict(_LIST_CONTEXT)
            ctx.update(_MATH_CONTEXT)
            ctx.update(_STRING_CONTEXT)
            ctx['Fraction'] = _Frac
            ctx['__builtins__'] = {}
            ctx.update({k: _to_frac_or_python(v) for k, v in value_map.items()})
            self.evaluated_value = eval(self.raw_expr, ctx)  # noqa: S307
            return self.evaluated_value

        # 2d. Math helper functions (round_dp, decimal_digit, …) — use Python eval
        # Keep decimal strings as strings so round_dp/decimal_digit can use
        # exact Decimal arithmetic rather than lossy float conversion.
        if any(fn + "(" in self.raw_expr for fn in _MATH_CONTEXT):
            def _to_python_preserve_decimal(v):
                if isinstance(v, str):
                    s = v.strip()
                    # Keep decimal strings (e.g. '8.45') as-is so callers like
                    # round_dp can use Decimal arithmetic and avoid float errors.
                    if re.fullmatch(r'-?\d+\.\d+', s):
                        return s
                return _to_python(v)
            ctx = {}
            ctx.update(_LIST_CONTEXT)
            ctx["__builtins__"] = {}
            ctx.update({k: _to_python_preserve_decimal(v) for k, v in value_map.items()})
            # Math functions go in last so parameter names can never shadow them
            ctx.update(_MATH_CONTEXT)
            self.evaluated_value = eval(self.raw_expr, ctx)  # noqa: S307
            return self.evaluated_value

        # 3. Substitute into expression
        # Wrap fraction values in parentheses so that e.g. a / b with a=23/4, b=11/5
        # becomes (23/4) / (11/5) rather than 23/4 / 11/5 (which parses incorrectly).
        substituted = self.raw_expr
        for key, val in value_map.items():
            val_str = str(val)
            # Wrap in parens when the value could be misread without them:
            #   • fraction strings  e.g. "23/4"  →  "(23/4)"
            #   • negative numbers  e.g. "-9"    →  "(-9)"
            # This prevents ambiguous expressions like "3 + -9 * 4" or "a / 3/4".
            # Don't wrap bare operator strings like "+" or "/" (len == 1 or pure op).
            needs_parens = ("/" in val_str and _is_fraction_string(val_str)) or \
                           (val_str.startswith("-") and len(val_str) > 1)
            if needs_parens:
                val_str = f"({val_str})"
            # Use a lambda so re.sub never interprets backslashes in val_str as
            # replacement-template escapes (e.g. \s from a resolved surd string).
            substituted = re.sub(rf'\b{re.escape(key)}\b', lambda _m, v=val_str: v, substituted)

        # 4. Evaluate using maths engine
        self.evaluated_value = evaluate_number_expression(substituted, value_map)
        return self.evaluated_value

    @staticmethod
    def _is_numeric(value):
        """Return True if value can be safely passed to a formatter (is a number, sympy numeric, or fraction string like '5/2')."""
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            s = value.strip()
            # Simple fraction: "5/2" or "-3/4"
            if re.fullmatch(r'-?\d+/-?\d+', s):
                return True
            # Plain number string
            try:
                float(s)
                return True
            except (TypeError, ValueError):
                return False
        # Sympy numeric types and anything else that converts cleanly to float
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    def format(self):
        # 0. List values — format as comma-separated; | sorted sorts first
        if isinstance(self.evaluated_value, list):
            vals = sorted(self.evaluated_value) if self.format_type == "sorted" else self.evaluated_value
            return ", ".join(str(int(v) if isinstance(v, float) and v == int(v) else v) for v in vals)

        # 1. Explicit format type always wins
        if self.format_type is not None:
            formatter_cls = FORMAT_REGISTRY[self.format_type]
            formatter = formatter_cls(**self.format_options)
            return formatter.format(self.evaluated_value)

        expr = self.raw_expr.strip()

        # 2. Single variable → use its default format
        if expr in self.params:
            param = self.params[expr]
            if hasattr(param, "default_format_type") and param.default_format_type:
                formatter_cls = FORMAT_REGISTRY[param.default_format_type]
                fmt_opts = getattr(param, "default_format_options", {})
                formatter = formatter_cls(**fmt_opts)
                if self._is_numeric(self.evaluated_value):
                    return formatter.format(self.evaluated_value)

        # 3. Multi-variable: check if all variables share the same default format
        vars_in_expr = [name for name in self.params if name in expr]

        if vars_in_expr:
            default_types = {
                self.params[name].default_format_type
                for name in vars_in_expr
                if hasattr(self.params[name], "default_format_type")
            }

            # If all default types are the same and not None
            if len(default_types) == 1:
                fmt = default_types.pop()
                if fmt and self._is_numeric(self.evaluated_value):
                    formatter_cls = FORMAT_REGISTRY[fmt]
                    formatter = formatter_cls()
                    return formatter.format(self.evaluated_value)

        # 4. Fallback: plain string — convert sympy/float to a clean representation
        from fractions import Fraction as _Frac
        if isinstance(self.evaluated_value, _Frac):
            return str(self.evaluated_value)  # "2/3" form
        try:
            f = float(self.evaluated_value)
            if f == int(f):
                return str(int(f))
            return f"{f:g}"
        except (TypeError, ValueError):
            return str(self.evaluated_value)
