"""Shared evaluation context for template expressions.

This module is the single source of truth for all functions and constants
available inside {{ }} expressions and parameter expressions. Both param.py
and expr.py import from here, so any new function only needs to be registered
once.
"""

import math as _math
import re as _re
from ..maths.fractions import denominator as _denominator, numerator as _numerator


# ── Utility helpers ──────────────────────────────────────────────────────────

def _is_fraction_string(v):
    """Return True if v is a string representing a numeric fraction or integer (e.g. '3/5', '14')."""
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


def _to_python(v):
    """Convert a stored string value (e.g. '3.74', '9') to a Python int or float."""
    if isinstance(v, str):
        try:
            f = float(v)
            return int(f) if f == int(f) else f
        except (ValueError, TypeError):
            pass
    return v


# ── Math helper functions ────────────────────────────────────────────────────

def round_dp(value, places):
    """Round *value* to *places* decimal places using exact decimal arithmetic.

    Accepts numeric strings (e.g. '3.55') to avoid float representation errors.
    Example: round_dp('3.55', 1) → 3.6
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


def _lcm_expr(d1, d2, var='x'):
    """LCM of two expressions that may include a single variable.

    Accepts numeric strings or expressions with a variable (e.g. '3x', '4').
    Returns a student-typeable string.

    Examples:
      lcm_expr('4', '6')   → '12'
      lcm_expr('3x', '6')  → '6x'
      lcm_expr('3x', '4x') → '12x'
    """
    import sympy as _sp
    sym = _sp.Symbol(str(var))
    e1 = _parse_math_expr(str(d1), var)
    e2 = _parse_math_expr(str(d2), var)
    result = _sp.lcm(e1, e2, sym)
    if not result.free_symbols:
        return str(int(result))
    return _sympy_to_typed(result)


def _factorise_expr(expr_str, var='x'):
    """Factorise an algebraic expression and return a student-typeable string.

    Accepts plain math or LaTeX input (same as simplify_expr).
    Returns the fully factored form, e.g. '15x - 6' → '3(5x - 2)'.
    Uses positive GCF convention: -2(3x - 2) → 2(-3x + 2).
    If the expression is already irreducible it is returned as-is.
    """
    import sympy as _sp
    expr = _parse_math_expr(str(expr_str), var)
    factored = _sp.factor(expr)

    # Positive GCF convention: ensure the leading scalar coefficient is positive.
    # SymPy factors -6x+4 as -2*(3x-2); convert to 2*(-3x+2).
    # Only when |coeff| > 1 (coeff=-1 cases like -(x+2) stay as-is).
    coeff, rest = factored.as_coeff_Mul()
    if coeff.is_negative and abs(coeff) > 1:
        if isinstance(rest, _sp.Add):
            factored = _sp.Mul(-coeff, -rest, evaluate=False)
        elif isinstance(rest, _sp.Mul):
            args = list(rest.args)
            for i, arg in enumerate(args):
                if isinstance(arg, _sp.Add):
                    args[i] = -arg
                    factored = _sp.Mul(-coeff, *args, evaluate=False)
                    break

    return _sympy_to_typed(factored)


def _factors(n):
    """Return a sorted list of all positive factors of n."""
    n = int(abs(n))
    result = []
    for i in range(1, int(n**0.5) + 1):
        if n % i == 0:
            result.append(i)
            if i != n // i:
                result.append(n // i)
    return sorted(result)


def _simplified_ratio(a, b):
    """Return the ratio a:b reduced to lowest terms as a string. e.g. (4, 8) → '1:2'."""
    from math import gcd
    a, b = int(a), int(b)
    d = gcd(abs(a), abs(b)) or 1
    return f"{a // d}:{b // d}"


def _sympy_to_typed(expr):
    """Convert a SymPy expression to student-typeable notation.

    e.g.  3*x**2/20  →  3x^2/20,  x*y  →  xy,  15x/(16y)  →  15x/16y
    Uses grlex term ordering so highest-degree terms always come first,
    e.g. -4*x + 6 not 6 - 4*x (which SymPy's default printer would produce).
    """
    from sympy.printing import sstr
    s = sstr(expr, order='grlex')
    s = s.replace('**', '^')
    s = _re.sub(r'(\d)\*([A-Za-z])', r'\1\2', s)        # 3*x → 3x
    s = _re.sub(r'(\d)\*\(', r'\1(', s)                  # 3*( → 3(
    s = _re.sub(r'([A-Za-z])\*\(', r'\1(', s)            # x*( → x(
    s = _re.sub(r'([A-Za-z])\*([A-Za-z])', r'\1\2', s)  # x*y → xy
    s = _re.sub(r'\)\*\(', r')(', s)                      # )*( → )(
    s = _re.sub(r'\)\*([A-Za-z])', r')\1', s)            # )*x → )x
    # Remove parens from simple monomial denominators: 15x/(16y) → 15x/16y.
    # Only when content has no +, -, or nested parens (so meaning is unchanged).
    s = _re.sub(r'/\(([^()+-]+)\)', r'/\1', s)
    return s


def _latex_to_sympy_str(s):
    """Convert a simple LaTeX math expression to a SymPy-parseable string.

    Handles the subset used in algebra templates:
      \\dfrac{a}{b}  →  (a)/(b)
      \\times        →  *
      \\div          →  /
      \\cdot         →  *
      3x             →  3*x   (implicit multiplication)

    Remaining LaTeX commands (\\left, \\right, etc.) are stripped.
    """
    # Iteratively flatten nested fractions (up to 5 levels deep).
    # Wrap the whole fraction in an extra pair of parens so that operator
    # precedence is preserved: A/B / C/D  must parse as (A/B) / (C/D),
    # not the left-associative ((A/B)/C)/D.
    for _ in range(5):
        prev = s
        s = _re.sub(r'\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'((\1)/(\2))', s)
        if s == prev:
            break
    # Binary operators
    s = s.replace(r'\times', '*')
    s = s.replace(r'\div', '/')
    s = s.replace(r'\cdot', '*')
    # Strip remaining LaTeX commands (e.g. \left, \right, \displaystyle)
    s = _re.sub(r'\\[a-zA-Z]+\s*', '', s)
    # Convert LaTeX grouping braces that remain into parentheses
    s = s.replace('{', '(').replace('}', ')')
    # Insert * for implicit multiplication: 3x → 3*x,  2(x → 2*(x
    s = _re.sub(r'(\d)\s*([A-Za-z(])', r'\1*\2', s)
    return s.strip()


def _parse_math_expr(expr_str, var):
    """Parse *expr_str* to a SymPy expression, auto-detecting LaTeX input."""
    import sympy as _sp
    s = str(expr_str)
    if '\\' in s:
        s = _latex_to_sympy_str(s)
    else:
        # Normalise double signs produced by %s with negative values:
        #   (3x + -3) → (3x - 3),  (x - -2) → (x + 2)
        s = _re.sub(r'\+\s*-', '- ', s)
        s = _re.sub(r'-\s*-', '+ ', s)
        # Implicit multiplication:
        #   3x → 3*x,  -4( → -4*(,  )( → )*(
        s = _re.sub(r'(\d)\s*([A-Za-z(])', r'\1*\2', s)
        s = _re.sub(r'\)\s*\(', r')*(', s)
    try:
        return _sp.sympify(s, locals={str(var): _sp.Symbol(str(var))})
    except Exception as exc:
        raise ValueError(
            f"simplify_expr: could not parse '{expr_str}': {exc}"
        ) from exc


def _simplify_expr(expr_str, var='x'):
    """Simplify/expand an algebraic expression and return a student-typeable string.

    Accepts both plain math notation and LaTeX (\\dfrac, \\times, \\div, etc.).

    Strategy: expand first (distributes products over sums, giving the standard
    expanded polynomial form students write), then cancel common factors in any
    remaining rational expression (e.g. 6x/4 → 3x/2).

    Pure-numeric results: plain fraction notation, e.g. '9/4'.
    Symbolic results: typed-math notation, e.g. '3x^2/20', '-4x + 6'.
    Use simplify_expr_latex() for LaTeX solution display.
    """
    import sympy as _sp
    expr = _parse_math_expr(expr_str, var)
    result = _sp.cancel(_sp.expand(expr))
    if not result.free_symbols:
        r = _sp.Rational(result)
        return str(r.p) if r.q == 1 else f"{r.p}/{r.q}"
    return _sympy_to_typed(result)


def _simplify_expr_latex(expr_str, var='x'):
    """Simplify/expand an algebraic expression and return LaTeX (for solution display).

    Accepts both plain math notation and LaTeX input (same as simplify_expr).

    Example: simplify_expr_latex("(2*x/3) * (3*x/4)") → "\\\\frac{x^{2}}{2}"
    """
    import sympy as _sp
    expr = _parse_math_expr(expr_str, var)
    return _sp.latex(_sp.cancel(_sp.expand(expr)))


def _gaussian_list(mean, sd, count, sort=False):
    """Generate *count* integers drawn from N(mean, sd), adjusted to hit the exact integer mean."""
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


def _linear_factor(r):
    """Format a single linear factor (x - r) correctly for any sign of r.

    Examples:
      linear_factor(6)  → '(x - 6)'
      linear_factor(-7) → '(x + 7)'
      linear_factor(0)  → '(x)'
    """
    r = int(r) if float(r) == int(float(r)) else float(r)
    if r == 0:
        return "(x)"
    if r < 0:
        return f"(x + {abs(r)})"
    return f"(x - {r})"


def _poly_from_roots(*args):
    """Build a factored polynomial string from roots.

    Accepts either a list or individual arguments:
      poly_from_roots([-7, -5, 6])       → '(x + 7)(x + 5)(x - 6)'
      poly_from_roots(-7, -5, 6)         → '(x + 7)(x + 5)(x - 6)'
    """
    if len(args) == 1 and isinstance(args[0], list):
        roots = args[0]
    else:
        roots = list(args)
    return "".join(_linear_factor(r) for r in roots)


def _log(x, base=None):
    """Logarithm with optional base.  log(x) = natural log; log(x, base) = log base *base* of x.
    Integer results (e.g. log(8, 2) = 3) are returned as int rather than float.
    """
    result = _math.log(x) if base is None else _math.log(x) / _math.log(base)
    rounded = round(result)
    return rounded if abs(result - rounded) < 1e-9 else result


def _not_in(lst, lo=None, hi=None):
    """Return a random integer that is not in *lst*.

    Search range defaults to [min(lst)-3, max(lst)+3] so the result is
    a similarly-sized value to those already in the list.  Provide explicit
    *lo*/*hi* to override.
    """
    import random as _random
    lst_set = set(lst)
    _lo = int(lo) if lo is not None else (min(lst) - 3 if lst else -9)
    _hi = int(hi) if hi is not None else (max(lst) + 3 if lst else 9)
    candidates = [x for x in range(_lo, _hi + 1) if x not in lst_set]
    if not candidates:
        raise ValueError(f"not_in: no value available outside {lst} in range [{_lo}, {_hi}]")
    return _random.choice(candidates)


def _repeat(value, count, sep=""):
    """Repeat *value* *count* times joined by *sep*.

    Example: repeat('a', 4, ' × ') → 'a × a × a × a'
    """
    return sep.join([str(value)] * int(count))


# ── List aggregate functions ─────────────────────────────────────────────────

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
    """Return Q1 (q=1) or Q3 (q=3) using the exclusive method."""
    if q not in (1, 2, 3):
        raise ValueError(f"quartile() expects q=1, 2, or 3, got q={q}")
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


# ── Context dicts ────────────────────────────────────────────────────────────

MATH_CONTEXT = {
    # Constants
    "pi":               _math.pi,
    "e":                _math.e,
    # Arithmetic / rounding
    "round":            round,
    "round_dp":         round_dp,
    "decimal_digit":    decimal_digit,
    "abs":              abs,
    "ceil":             _math.ceil,
    "floor":            _math.floor,
    # Trigonometry
    "sin":              _math.sin,
    "cos":              _math.cos,
    "tan":              _math.tan,
    "asin":             _math.asin,
    "acos":             _math.acos,
    "atan":             _math.atan,
    "atan2":            _math.atan2,
    # Logarithms / angles
    "sqrt":             _math.sqrt,
    "log":              _log,
    "log10":            _math.log10,
    "degrees":          _math.degrees,
    "radians":          _math.radians,
    # Number theory
    "gcd":              _gcd,
    "lcm":              _lcm,
    "numerator":        _numerator,
    "denominator":      _denominator,
    "lcm_expr":         _lcm_expr,
    "factorise_expr":   _factorise_expr,
    "factors":          _factors,
    "simplified_ratio": _simplified_ratio,
    # Algebra
    "simplify_expr":        _simplify_expr,
    "simplify_expr_latex":  _simplify_expr_latex,
    # Data generation
    "gaussian_list":    _gaussian_list,
    "not_in":           _not_in,
    # Polynomial helpers
    "linear_factor":    _linear_factor,
    "poly_from_roots":  _poly_from_roots,
    # String / formatting helpers available in math expressions
    "repeat":           _repeat,
    "str":              str,
    "int":              int,
    "float":            float,
    "bool":             bool,
    "len":              len,
    "min":              min,
    "max":              max,
    "sum":              sum,
}

LIST_CONTEXT = {
    "mode":      list_mode,
    "median":    list_median,
    "mean":      list_mean,
    "range_of":  list_range,
    "quartile":  list_quartile,
    "stdev":     list_stdev,
    "pop_stdev": list_pop_stdev,
    "sorted":    sorted,
    "sum":       sum,
    "min":       min,
    "max":       max,
    "len":       len,
}

# Functions available when an expression references non-numeric string params.
def _unit_multiplier_lazy(prefix):
    from ..maths.units import unit_multiplier
    return unit_multiplier(prefix)

STRING_CONTEXT = {
    "unit_multiplier": _unit_multiplier_lazy,
    "repeat":          _repeat,
    "str":             str,
    "int":             int,
    "float":           float,
    "bool":            bool,
    "abs":             abs,
}

# Unified context: the single merged dict used in the simplified evaluator.
# Merging order: LIST → MATH → STRING (later keys win on collision).
EVAL_CONTEXT: dict = {**LIST_CONTEXT, **MATH_CONTEXT, **STRING_CONTEXT}
