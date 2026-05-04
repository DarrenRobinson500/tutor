import re as _re
from .format import *
from math import gcd
from fractions import Fraction as _Fraction

_NAMES = [
    "Emma", "Olivia", "Ava", "Isabella", "Sophia",
    "Liam", "Noah", "Oliver", "Elijah", "James",
]

class RandomParameter:
    def __init__(self, name, type_name, options):
        self.name = name
        self.type_name = type_name
        self.options = options or {}
        self.value = self.generate({})

    def __str__(self):
        return f"{self.name}: {self.value}"

    @classmethod
    def from_yaml(cls, name, spec):
        # spec may be literal, dict, or structured type
        if spec is None:
            raise ValueError(
                f"Parameter '{name}' has no value. Check indentation — its properties "
                f"(e.g. expr:, size:, min:) must be indented under '{name}:'."
            )
        if isinstance(spec, (int, float)):
            return LiteralParameter(name, spec)
        if isinstance(spec, str):
            # Bare string shorthand: if it looks like an expression, treat as expr param.
            # A plain number literal (e.g. "42") stays as a LiteralParameter.
            # A fraction literal like "9/12" is preserved as-is so formatters can render
            # it without simplifying (e.g. {{ b | fraction }} → \frac{9}{12} not \frac{3}{4}).
            if _re.fullmatch(r'-?\d+/\d+', spec.strip()):
                return FractionLiteralParameter(name, spec.strip())
            try:
                float(spec)
                return LiteralParameter(name, spec)
            except ValueError:
                # Bare string containing = (equality check) → bool parameter
                if _re.search(r'(?<![!<>=])=(?!=)', spec):
                    return BoolParameter(name, {"expr": spec})
                return ExprParameter(name, {"expr": spec})

        if "value" in spec:
            return LiteralParameter(name, spec["value"])

        param_type = spec.get("type")

        if param_type == "fraction":
            if "expr" in spec:
                return FractionFromExprParameter(name, spec)
            return FractionParameter(name, spec)
        if param_type == "fraction_expr":
            return FractionExprParameter(name, spec)
        if param_type == "decimal":
            return DecimalParameter(name, spec)
        if param_type == "dollar":
            return DollarParameter(name, spec)
        if param_type == "percent":
            return PercentParameter(name, spec)
        if param_type == "choice":
            return ChoiceParameter(name, spec)
        if param_type == "name":
            return NameParameter(name, spec)
        if param_type == "int":
            return IntParameter(name, spec)
        if param_type == "list":
            return ListParameter(name, spec)
        if param_type == "scenario":
            return ScenarioParameter(name, spec)
        if param_type == "bool":
            return BoolParameter(name, spec)

        if param_type == "case":
            return CaseParameter(name, spec)

        if "expr" in spec:
            expr_str = str(spec.get("expr", "")).strip()
            # Auto-detect Python conditional syntax (if … else …) → CaseParameter
            if _re.search(r'\bif\b', expr_str) and _re.search(r'\belse\b', expr_str):
                return CaseParameter(name, spec)
            return ExprParameter(name, spec)

        if "min" in spec and "max" in spec:
            return RangeParameter(name, spec)

        if "size" in spec:
            return RangeParameter(name, spec)

        raise ValueError(f"Unsupported parameter spec: {spec}")

    def generate(self, context):
        raise NotImplementedError

    def format(self, value):
        if not hasattr(self, "format_type") or self.format_type is None:
            return value

        formatter_cls = FORMAT_REGISTRY[self.format_type]
        formatter = formatter_cls(**self.options)
        return formatter.format(value)


class LiteralParameter(RandomParameter):
    def __init__(self, name, value):
        self._literal_value = value
        super().__init__(name, "literal", {})

    def generate(self, context):
        return self._literal_value


class FractionLiteralParameter(LiteralParameter):
    """A literal fraction like '9/12' that preserves the exact unsimplified form.

    Used when a parameter is declared as a bare fraction string, e.g.:
        parameters:
          b: 9/12

    The value is kept as a string so {{ b | fraction }} renders \\frac{9}{12}
    rather than the simplified \\frac{3}{4}. Use {{ b | fraction }} to display
    as LaTeX, or {{ b }} to get the default fraction rendering.
    """
    default_format_type = "fraction"


class RangeParameter(RandomParameter):
    SIZE_MAP = {
        "small":  (2, 5),
        "medium": (2, 10),
    }

    def __init__(self, name, options):
        super().__init__(name, "range", options)
        if options.get("brackets_when_negative"):
            self.default_format_type = "brackets"

    @staticmethod
    def _round_2_sig_figs(n):
        from math import log10, ceil
        if n == 0:
            return 0
        d = ceil(log10(abs(n) + 1e-9))
        factor = 10 ** (d - 2)
        return int(round(n / factor) * factor)

    def generate(self, context):
        size = self.options.get("size")
        if size == "large":
            value = self._round_2_sig_figs(random.randint(20, 1000))
        elif size in self.SIZE_MAP:
            lo, hi = self.SIZE_MAP[size]
            value = random.randint(lo, hi)
        else:
            lo = int(self.options["min"])
            hi = int(self.options["max"])
            step = int(self.options.get("step", 1))
            if step > 1:
                steps = list(range(lo, hi + 1, step))
                value = random.choice(steps)
            else:
                value = random.randint(lo, hi)

        sign = self.options.get("sign", "pos")
        if sign == "neg":
            value = -abs(value)
        elif sign == "pos_neg":
            if random.choice([True, False]):
                value = -abs(value)

        return value

class IntParameter(RandomParameter):
    """Generates a random integer using a named size preset or explicit min/max.

    YAML spec:
      n: { type: int, size: medium }      # small=(2,5), medium=(2,10), large=(2,20)
      n: { type: int, min: 3, max: 15 }   # explicit range
    """
    SIZE_MAP = {
        "small": (2, 5),
        "medium": (2, 10),
        "large": (2, 20),
    }

    def __init__(self, name, options):
        super().__init__(name, "int", options)

    def generate(self, context):
        print("IntParameter Context:", context)

        size = self.options.get("size")
        if size in self.SIZE_MAP:
            lo, hi = self.SIZE_MAP[size]
        else:
            lo = int(self.options.get("min", 2))
            hi = int(self.options.get("max", 10))
        return random.randint(lo, hi)


class FractionParameter(RandomParameter):
    def __init__(self, name, options):
        super().__init__(name, "fraction", options)
        self.default_format_type = "mixed_number" if options.get("mixed") else "fraction"

    def generate(self, context):
        SIZE_MAP = {
            "v_small": (2, 5),
            "small": (2, 5),
            "medium": (2, 10),
            "large": (2, 20),
        }

        size = self.options.get("size", "medium")
        sign = self.options.get("sign", "pos")
        simplified = self.options.get("simplified", True)

        den_min, den_max = SIZE_MAP.get(size, (2, 10))
        den = random.randint(den_min, den_max)

        if size == "v_small":
            num = 1
        elif self.options.get("mixed"):
            # Generate a proper fractional part, then add a whole number
            num = random.randint(1, den - 1)
            min_whole = self.options.get("min_whole", 1)
            max_whole = self.options.get("max_whole", 5)
            whole = random.randint(min_whole, max_whole)
            num = whole * den + num  # store as improper fraction
        else:
            proper = self.options.get("proper", None)
            if proper == False:
                # Improper = whole number (same size range) + proper fraction
                whole = random.randint(den_min, den_max)
                frac_num = random.randint(1, den - 1)
                num = whole * den + frac_num
            else:
                num = random.randint(1, den - 1)

        if simplified:
            g = gcd(num, den)
            num //= g
            den //= g

        if sign == "neg":
            num = -abs(num)
        elif sign == "pos_neg":
            if random.choice([True, False]):
                num = -abs(num)

        return f"{num}/{den}"


class DecimalParameter(RandomParameter):
    """Generates a decimal value with a fixed number of decimal places.

    YAML spec:
      a: { type: decimal, min: 1, max: 10, decimal_places: 1 }

    Stored as an exact fraction string (e.g. "17/5") so sympy arithmetic
    stays precise. Displayed via DecimalFormat (strips trailing zeros).
    Use {{ a | decimal(decimal_places=2) }} to override display precision.
    """
    default_format_type = "decimal"

    def __init__(self, name, options):
        super().__init__(name, "decimal", options)
        if "decimal_places" in options:
            dp = int(options["decimal_places"])
        elif "step" in options:
            # Infer dp from step: 0.05 → 2, 0.1 → 1, 0.25 → 2
            s = str(float(options["step"]))
            dp = len(s.rstrip("0").split(".")[-1]) if "." in s else 0
        else:
            dp = 1
        self.default_format_options = {"decimal_places": dp}

    SIZE_MAP = {
        "small":  (0.1, 0.9, 1),
        "medium": (0.1, 9.9, 1),
        "large":  (0.01, 9.99, 2),
    }

    def generate(self, context):
        print("DecimalParameter Context:", context)

        dp = int(self.options.get("decimal_places", 1))
        size = self.options.get("size")
        if size in self.SIZE_MAP:
            lo, hi, dp = self.SIZE_MAP[size]
        else:
            lo = float(self.options["min"])
            hi = float(self.options["max"])
        if "step" in self.options:
            step = float(self.options["step"])
            # Build list of valid values as integers to avoid float rounding errors
            scale = 10 ** dp
            steps = round((hi - lo) / step)
            idx = random.randint(0, steps)
            raw = round(lo + idx * step, dp)
        else:
            scale = 10 ** dp
            min_scaled = int(round(lo * scale))
            max_scaled = int(round(hi * scale))
            raw = round(random.randint(min_scaled, max_scaled) / scale, dp)
        return str(raw)


class DollarParameter(RandomParameter):
    """Generates a dollar amount.

    YAML spec:
      price: { type: dollar, min: 5, max: 50 }           # whole dollars (default)
      price: { type: dollar, min: 5, max: 50, cents: true } # dollars and cents

    min/max are in whole dollars. Stored as an exact fraction (e.g. "$12.50" → "25/2").
    Displayed via DollarFormat as "$12" or "$12.50".
    """
    default_format_type = "dollar"

    def __init__(self, name, options):
        super().__init__(name, "dollar", options)

    def generate(self, context):
        size = self.options.get("size")

        if size == "small":
            # Whole dollars only, $3–$8
            dollars = random.randint(
                int(self.options.get("min", 3)),
                int(self.options.get("max", 8)),
            )
            return f"{dollars}/1"

        if size == "large":
            # 2 significant figures, multiples of $10 from $10–$1000
            step = int(self.options.get("step", 10))
            lo = int(self.options.get("min", 10)) // step
            hi = int(self.options.get("max", 1000)) // step
            dollars = random.randint(lo, hi) * step
            return f"{dollars}/1"

        # If step is specified, generate a whole-dollar multiple of step
        if "step" in self.options:
            step = int(self.options["step"])
            lo = int(self.options.get("min", 0)) // step
            hi = int(self.options.get("max", 100)) // step
            dollars = random.randint(lo, hi) * step
            return f"{dollars}/1"

        # Default: whole dollars, $3–$10 (use cents: true for dollars-and-cents)
        if self.options.get("cents"):
            min_cents = int(float(self.options.get("min", 3)) * 100)
            max_cents = int(float(self.options.get("max", 10)) * 100)
            cents = random.randint(min_cents, max_cents)
            f = _Fraction(cents, 100)
            return f"{f.numerator}/{f.denominator}"
        dollars = random.randint(
            int(self.options.get("min", 3)),
            int(self.options.get("max", 10)),
        )
        return f"{dollars}/1"


class PercentParameter(RandomParameter):
    """Generates a whole-number percentage value.

    YAML spec:
      rate: { type: percent, min: 10, max: 90 }
      rate: { type: percent, size: small }   # 5% | 10% | 20%
      rate: { type: percent, size: medium }  # 2% | 5% | 10% | 20% | 25%
      rate: { type: percent, size: large }   # 1% | 2% | 5% | 20% | 25% | 50%

    Stored as a decimal proportion string (e.g. "0.35"). Displayed via PercentFormat as "35%".
    In expressions, the raw value is the decimal proportion, so
    {{ a * percentage }} gives the correct result directly.
    """
    default_format_type = "percent"
    COMMON_VALUES = [1, 5, 10, 12.5, 20, 25, 50]
    SIZE_MAP = {
        "small":  [5, 10, 20],
        "medium": [2, 5, 10, 20, 25],
        "large":  [1, 2, 5, 20, 25, 50],
    }

    def __init__(self, name, options):
        super().__init__(name, "percent", options)

    def generate(self, context):
        size = self.options.get("size")
        if size in self.SIZE_MAP:
            pct = random.choice(self.SIZE_MAP[size])
        elif self.options.get("common"):
            pct = random.choice(self.COMMON_VALUES)
        else:
            pct = random.randint(int(self.options["min"]), int(self.options["max"]))
        # Store as decimal proportion string — exact for arithmetic, readable in debug output
        val = pct / 100
        return str(int(val)) if val == int(val) else str(val)


class ChoiceParameter(RandomParameter):
    """Picks one value at random from an explicit list.

    YAML spec:
      angle:
        type: choice
        values: [10, 30, 45, 60, 80, 90]

    The chosen value is stored as-is (int or float).
    """

    def __init__(self, name, options):
        super().__init__(name, "choice", options)

    def generate(self, context):
        values = self.options.get("values", [])
        if not values:
            raise ValueError(f"ChoiceParameter '{self.name}' has an empty values list")
        return random.choice(values)


class NameParameter(RandomParameter):
    """Picks a unique child's name per render from a built-in pool of 10 names.

    YAML spec:
      student: { type: name }

    Multiple name parameters within the same template each receive a different
    name. The pool is reset at the start of every render.
    """

    _used_in_render: set = set()

    def __init__(self, name, options):
        super().__init__(name, "name", options)

    def generate(self, context):
        available = [n for n in _NAMES if n not in NameParameter._used_in_render]
        if not available:
            available = list(_NAMES)  # fallback: all 10 used, start over
        chosen = random.choice(available)
        NameParameter._used_in_render.add(chosen)
        return chosen


class ListParameter(RandomParameter):
    """Generates a list of random integers.

    YAML spec:
      data:
        type: list
        count: 5      # number of values
        min: 1        # minimum value (inclusive)
        max: 10       # maximum value (inclusive)

    The value is a Python list, e.g. [3, 5, 7, 2, 8].
    Use {{ data | sorted }} to display sorted, or {{ mode(data) }} etc.
    """

    def __init__(self, name, options):
        super().__init__(name, "list", options)

    SIZE_MAP = {
        "small":  (2, 9),
        "medium": (2, 20),
        "large":  (2, 99),
    }

    def generate(self, context):
        print("ListParameter Context:", context)
        count = int(self.options.get("count", 5))
        size = self.options.get("size")
        if size in self.SIZE_MAP:
            lo, hi = self.SIZE_MAP[size]
        else:
            lo = int(self.options.get("min", 1))
            hi = int(self.options.get("max", 10))
        values = [random.randint(lo, hi) for _ in range(count)]
        if self.options.get("order", False):
            values.sort()
        return values


class ExprParameter(RandomParameter):
    """A derived parameter whose value is computed from an expression over other parameters.

    YAML spec:
      total:
        expr: "2 * (a + b)"       # bare expression
      total:
        expr: "{{ 2 * (a + b) }}" # {{ }} wrapper also accepted

    The parameter must be defined AFTER any parameters it references so that
    their values are already available when it is resolved.
    """

    _TOKEN_RE = _re.compile(r'\{\{(.*?)\}\}')

    def __init__(self, name, options):
        # Bypass the normal super().__init__ which would call generate() immediately.
        self.name = name
        self.type_name = "expr"
        self.options = options or {}
        raw = str(options.get("expr", "0")).strip()

        # If {{ }} tokens are present AND there is literal text outside them,
        # treat this as a string template (e.g. "{{f1}}({{a1}}x + {{b1}})").
        # Pure expressions like "gcd(a*k, b*k)" have no tokens at all → not a template.
        has_tokens = bool(self._TOKEN_RE.search(raw))
        leftover = self._TOKEN_RE.sub('', raw).strip()
        self._is_template = has_tokens and bool(leftover)

        if self._is_template:
            self._template = raw
            self._expr = raw   # unused in template mode
        else:
            # Pure expression — strip a single outer {{ }} wrapper if present,
            # then strip any remaining inline {{ }} tokens.
            m = _re.match(r'^\{\{\s*(.*?)\s*\}\}$', raw)
            if m:
                raw = m.group(1).strip()
            self._expr = _re.sub(r'\{\{\s*(.*?)\s*\}\}', r'\1', raw)
            self._template = None

        self.value = None   # filled by resolve()

    def generate(self, context):
        return None   # not used; see resolve()

    def resolve(self, param_objects):
        """Evaluate the expression using already-generated param values."""
        from .expr import ExpressionNode

        if self._is_template:
            # String template: substitute each {{ expr }} token individually.
            def _subst(m):
                expr_text = m.group(1).strip()
                try:
                    node = ExpressionNode(expr_text, param_objects)
                    node.evaluate()
                    return node.format()
                except Exception:
                    return m.group(0)
            self.value = self._TOKEN_RE.sub(_subst, self._template)
            return

        try:
            node = ExpressionNode(self._expr, param_objects)
            result = node.evaluate()
            # Convert sympy types to plain Python so the value is JSON-serialisable
            try:
                f = float(result)
                self.value = int(f) if f == int(f) else f
            except (TypeError, ValueError):
                # Check for unresolved sympy symbols (undefined variables)
                try:
                    free = result.free_symbols
                    if free:
                        names = ", ".join(sorted(str(s) for s in free))
                        raise ValueError(f"Derived parameter '{self.name}': unknown variable(s): {names}")
                except AttributeError:
                    pass
                self.value = str(result)
        except Exception as e:
            raise ValueError(f"Derived parameter '{self.name}': {e}") from e


class BoolParameter(ExprParameter):
    """Evaluates a condition and stores 1 (True) or 0 (False).

    YAML spec (explicit type):
      right_angle:
        type: bool
        expr: "a ^ 2 + b ^ 2 = c ^ 2"

    Shorthand (bare string containing a single = comparison):
      right_angle: a ^ 2 + b ^ 2 = c ^ 2

    Supports ^ for exponentiation and = for equality (auto-converted to **  and ==).
    The value is 1 if the condition is true, 0 if false, and can be used in
    logic rules, answer correct expressions, and {{ }} substitutions.
    """

    # Match a lone = that isn't part of ==, !=, <=, >=
    _EQ_RE = _re.compile(r'(?<![!<>=])=(?!=)')

    def resolve(self, param_objects):
        from fractions import Fraction as _Frac

        expr = self._expr
        # Normalise ^ → ** and = → ==
        expr = expr.replace('^', '**')
        expr = self._EQ_RE.sub('==', expr)

        # Build a numeric context from resolved param values
        def _to_num(v):
            if isinstance(v, (int, float)):
                return v
            if isinstance(v, str):
                try:
                    return _Frac(v) if '/' in v else float(v)
                except (ValueError, ZeroDivisionError):
                    return v
            return v

        ctx = {name: _to_num(p.value) for name, p in param_objects.items()}
        ctx['__builtins__'] = {}

        try:
            result = eval(expr, ctx)  # noqa: S307
            self.value = 1 if result else 0
        except Exception as e:
            raise ValueError(f"Bool parameter '{self.name}': {e}") from e


class CaseParameter(ExprParameter):
    """Evaluates a Python conditional expression using already-resolved param values.

    Supports numeric and string results. String results may contain {{ token }}
    expressions which are substituted after the conditional resolves.

    YAML spec (explicit type):
      label:
        type: case
        expr: '"product" if op == "×" else "quotient"'

    Auto-triggered when an expr: spec contains Python if/else syntax:
      result:
        expr: >
          -(m + n) if case_type == "product"
          else -(m - n) if case_type == "quotient"
          else -(m * n)

    Parameters referenced in the expression MUST be declared before this one.
    A clear error is raised if a dependency has not yet been computed.
    """

    _SAFE_BUILTINS = {
        'abs': abs, 'round': round, 'min': min, 'max': max,
        'int': int, 'float': float, 'str': str, 'len': len,
        'sum': sum,
    }

    def __init__(self, name, options):
        # Bypass ExprParameter.__init__ — keep the raw expression intact for eval()
        self.name = name
        self.type_name = "case"
        self.options = options or {}
        self._expr = str(options.get("expr", "")).strip()
        self._is_template = False  # unused; resolve() handles everything
        self._template = None
        self.value = None  # filled by resolve()

    def resolve(self, param_objects):
        expr = self._expr
        # Normalise ^ → ** so exponentiation works (^ is XOR in Python)
        expr = expr.replace('^', '**')

        # Build evaluation context from already-resolved params only.
        # Params with value=None haven't been resolved yet — omit them so
        # a NameError gives us a precise "not yet computed" message.
        ctx = {'__builtins__': self._SAFE_BUILTINS}
        for pname, p in param_objects.items():
            if pname == self.name:
                continue
            if p.value is not None:
                ctx[pname] = p.value

        try:
            result = eval(expr, ctx)  # noqa: S307
        except NameError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else str(e)
            if missing in param_objects:
                raise ValueError(
                    f"Case parameter '{self.name}' references '{missing}' which has not "
                    f"been computed yet. Move '{self.name}' after '{missing}' in the "
                    f"parameters block."
                ) from e
            raise ValueError(
                f"Case parameter '{self.name}': undefined name '{missing}'. "
                f"Check spelling or add it as a parameter before '{self.name}'."
            ) from e
        except Exception as e:
            raise ValueError(f"Case parameter '{self.name}': {e}") from e

        # String result: substitute {{ token }} expressions using param values
        if isinstance(result, str):
            def _subst(m):
                token = m.group(1).strip()
                try:
                    from .expr import ExpressionNode
                    node = ExpressionNode(token, param_objects)
                    node.evaluate()
                    return node.format()
                except Exception:
                    return m.group(0)
            self.value = _re.sub(r'\{\{(.*?)\}\}', _subst, result)
        else:
            try:
                f = float(result)
                self.value = int(f) if f == int(f) else f
            except (TypeError, ValueError):
                self.value = str(result)


class FractionExprParameter(ExprParameter):
    """A derived parameter that builds a fraction string "n/d" from two expressions.

    YAML spec:
      b:
        type: fraction_expr
        numerator: num * 3
        denominator: den * 3

    Produces a value like "6/9" which the fraction formatter renders as \\frac{6}{9}.
    Supports the same {{ }} syntax as ExprParameter.
    Resolved in the same topological pass as ExprParameter.
    """

    def __init__(self, name, options):
        import re as _re
        self.name = name
        self.type_name = "fraction_expr"
        self.options = options or {}
        self.default_format_type = "fraction"

        def _strip(raw):
            raw = str(raw).strip()
            m = _re.match(r'^\{\{\s*(.*?)\s*\}\}$', raw)
            if m:
                raw = m.group(1).strip()
            return _re.sub(r'\{\{\s*(.*?)\s*\}\}', r'\1', raw)

        self._num_expr = _strip(options.get("numerator", "0"))
        self._den_expr = _strip(options.get("denominator", "1"))
        # _expr is used by the topo-sort in render.py to detect dependencies
        self._expr = f"{self._num_expr} {self._den_expr}"
        self.value = None  # filled by resolve()

    def resolve(self, param_objects):
        from .expr import ExpressionNode
        try:
            num = ExpressionNode(self._num_expr, param_objects).evaluate()
            den = ExpressionNode(self._den_expr, param_objects).evaluate()
            n = int(round(float(num)))
            d = int(round(float(den)))
            self.value = f"{n}/{d}"
        except Exception as e:
            raise ValueError(f"Derived parameter '{self.name}' (fraction_expr): {e}") from e


class FractionFromExprParameter(CaseParameter):
    """type: fraction with expr: — evaluates expr and stores result as "n/d" fraction string.

    YAML spec:
      m2:
        type: fraction
        expr: -1 / m1 if case_type == "perp" else m1 + 1
    """

    def __init__(self, name, options):
        super().__init__(name, options)
        self.type_name = "fraction"
        self.default_format_type = "fraction"

    def resolve(self, param_objects):
        super().resolve(param_objects)
        try:
            frac = _Fraction(self.value).limit_denominator(1000)
            self.value = f"{frac.numerator}/{frac.denominator}"
        except (TypeError, ValueError, ZeroDivisionError) as e:
            raise ValueError(f"Parameter '{self.name}' (fraction from expr): cannot convert {self.value!r} to fraction: {e}") from e


class ScenarioParameter(RandomParameter):
    """Picks a random row from a list of lists.

    YAML spec:
      item:
        type: scenario
        rows:
          - [a soccer pitch, m]
          - [a pencil, cm]
          - [a person, m]

    The value is a Python list. Access fields with {{ item[0] }}, {{ item[1] }}, etc.
    Use item[1] in logic rules to mark the correct answer.
    """

    def __init__(self, name, options):
        super().__init__(name, "scenario", options)

    def generate(self, context):
        rows = self.options.get("rows", [])
        if not rows:
            raise ValueError(f"ScenarioParameter '{self.name}' has no rows")
        return list(random.choice(rows))
