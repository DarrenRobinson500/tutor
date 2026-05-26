import re
from .param import *
from .engine import *
from .context import (
    MATH_CONTEXT, LIST_CONTEXT, STRING_CONTEXT, EVAL_CONTEXT,
    _is_fraction_string, _to_python,
    round_dp, decimal_digit, list_mode, list_median, list_mean,
    list_range, list_quartile, list_stdev, list_pop_stdev,
)

def _replace_caret_outside_strings(expr: str) -> str:
    """Replace ^ with ** only when outside string literals."""
    result = []
    i = 0
    n = len(expr)
    while i < n:
        ch = expr[i]
        if ch in ('"', "'"):
            quote = ch
            result.append(ch)
            i += 1
            # Triple-quoted string
            if expr[i:i+2] == quote * 2:
                result.append(quote)
                result.append(quote)
                i += 2
                end = quote * 3
                while i < n:
                    if expr[i] == '\\' and i + 1 < n:
                        result.append(expr[i])
                        result.append(expr[i + 1])
                        i += 2
                    elif expr[i:i+3] == end:
                        result.append(end)
                        i += 3
                        break
                    else:
                        result.append(expr[i])
                        i += 1
            else:
                # Single-quoted string
                while i < n:
                    if expr[i] == '\\' and i + 1 < n:
                        result.append(expr[i])
                        result.append(expr[i + 1])
                        i += 2
                    elif expr[i] == quote:
                        result.append(expr[i])
                        i += 1
                        break
                    else:
                        result.append(expr[i])
                        i += 1
        elif ch == '^':
            result.append('**')
            i += 1
        else:
            result.append(ch)
            i += 1
    return ''.join(result)


# Back-compat aliases used by render.py and tests
_MATH_CONTEXT = MATH_CONTEXT
_LIST_CONTEXT = LIST_CONTEXT
_STRING_CONTEXT = STRING_CONTEXT


class ExpressionNode:
    """Evaluate a single {{ expression }} from a template.

    Resolution order:
    1. Bare FractionLiteralParameter → keep string form so formatters render
       it unsimplified (e.g. '9/12' → \\frac{9}{12}, not \\frac{3}{4}).
    2. Unified Python eval using EVAL_CONTEXT + coerced parameter values.
       Handles lists, strings, booleans, ternary, math functions — everything.
    3. Sympy text-substitution fallback for expressions that contain operator-
       string parameters (e.g. op = "+") or that Python cannot evaluate.
    """

    def __init__(self, raw_expr, params=None):
        self.original_expr = raw_expr.strip()
        self.params = params or {}

        self.raw_expr = None
        self.format_type = None
        self.format_options = {}

        self._parse()
        self.evaluate()
        self.output = self.format()

    def __str__(self):
        return f"{self.original_expr} -> {self.output}"

    # ── Parsing ──────────────────────────────────────────────────────────────

    def _parse(self):
        expr = self.original_expr
        if "|" in expr:
            expr_part, format_part = map(str.strip, expr.split("|", 1))
        else:
            expr_part, format_part = expr, None

        self.raw_expr = expr_part
        self.format_type, self.format_options = self._parse_format(format_part)

    @staticmethod
    def _parse_format(format_part):
        if not format_part:
            return None, {}
        if "(" not in format_part:
            return format_part.strip(), {}
        name, rest = format_part.split("(", 1)
        name = name.strip()
        args_str = rest.rstrip(")")
        # Split on commas that are not inside quotes
        parts, current, in_quote = [], [], None
        for ch in args_str:
            if ch in ("'", '"') and in_quote is None:
                in_quote = ch
                current.append(ch)
            elif ch == in_quote:
                in_quote = None
                current.append(ch)
            elif ch == ',' and in_quote is None:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(ch)
        if current:
            parts.append(''.join(current).strip())
        options = {}
        positional = []
        for item in parts:
            if not item:
                continue
            if "=" in item and not (item.startswith("'") or item.startswith('"')):
                key, val = item.split("=", 1)
                options[key.strip()] = val.strip().strip("'\"")
            else:
                positional.append(item.strip("'\""))
        if positional:
            options.setdefault("sep", positional[0])
        return name, options

    # ── Value coercion ───────────────────────────────────────────────────────

    @staticmethod
    def _coerce(v, param):
        """Prepare a parameter value for the unified Python eval context.

        Rules (applied in order):
        - Lists stay as lists.
        - Operator strings (+, -, ×, …) stay as strings; the sympy fallback
          handles them via text substitution.
        - CaseParameter / ExprParameter string results stay as strings —
          they may be algebraic (e.g. '3x^2/20') or answer strings ('9/4').
        - Decimal strings (e.g. '3.74') stay as strings so round_dp can
          use exact Decimal arithmetic.
        - Plain numeric fraction strings (e.g. '9/4') become Fraction so
          arithmetic and comparisons work correctly.
        - Everything else is converted to int/float where possible.
        """
        from fractions import Fraction as _Frac

        if isinstance(v, list):
            return v
        if not isinstance(v, str):
            return v  # int, float, bool — already native Python

        # Operator strings are only meaningful after text substitution
        if v.strip() in ('+', '-', '*', '/', '^', '**', '×', '÷'):
            return v

        # Expr/CaseParameter produce strings intentionally — keep them
        if isinstance(param, (ExprParameter, CaseParameter)):
            return v

        # Decimal strings: keep for round_dp / decimal_digit precision
        if re.fullmatch(r'-?\d+\.\d+', v.strip()):
            return v

        # Pure numeric fraction strings → Fraction for arithmetic
        if '/' in v and _is_fraction_string(v):
            try:
                return _Frac(v)
            except (ValueError, ZeroDivisionError):
                pass

        return _to_python(v)

    # ── Evaluation ───────────────────────────────────────────────────────────

    def evaluate(self):
        value_map = {name: param.value for name, param in self.params.items()}

        # 1. Bare FractionLiteralParameter: preserve string so formatter renders
        #    it unsimplified (e.g. {{ b | fraction }} → \frac{9}{12} not \frac{3}{4}).
        bare = self.raw_expr.strip()
        if bare in self.params and isinstance(self.params[bare], FractionLiteralParameter):
            self.evaluated_value = value_map[bare]
            return self.evaluated_value

        # Normalise ^ → ** so exponentiation works in Python eval,
        # but skip ^ characters that appear inside string literals.
        self.raw_expr = _replace_caret_outside_strings(self.raw_expr)

        # 2. Unified Python eval.
        from fractions import Fraction as _Frac
        ctx = dict(EVAL_CONTEXT)
        ctx['Fraction'] = _Frac
        ctx['__builtins__'] = {}
        ctx.update({k: self._coerce(v, self.params.get(k)) for k, v in value_map.items()})

        try:
            self.evaluated_value = eval(self.raw_expr, ctx)  # noqa: S307
            return self.evaluated_value
        except (TypeError, SyntaxError):
            # TypeError/SyntaxError are the expected failures when an operator-string
            # param (e.g. op = "+") appears as an infix — fall through to sympy substitution.
            pass

        # 3. Sympy text-substitution fallback.
        #    Substitute variable values as text, then evaluate with the maths engine.
        #    This handles templates like {{ a op b }} where op is "+" or "-".
        substituted = self.raw_expr
        for key, val in value_map.items():
            val_str = str(val)
            needs_parens = ('/' in val_str and _is_fraction_string(val_str)) or \
                           (val_str.startswith('-') and len(val_str) > 1)
            if needs_parens:
                val_str = f"({val_str})"
            substituted = re.sub(
                rf'\b{re.escape(key)}\b',
                lambda _m, v=val_str: v,
                substituted,
            )

        self.evaluated_value = evaluate_number_expression(substituted, value_map)
        return self.evaluated_value

    # ── Numeric check ─────────────────────────────────────────────────────────

    @staticmethod
    def _is_numeric(value):
        """Return True if value is a number or a plain fraction string like '5/2'."""
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            s = value.strip()
            if re.fullmatch(r'-?\d+/-?\d+', s):
                return True
            try:
                float(s)
                return True
            except (TypeError, ValueError):
                return False
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    # ── Formatting ───────────────────────────────────────────────────────────

    def format(self):
        # | length — returns count of items in a list (or characters in a string)
        if self.format_type == "length":
            try:
                return str(len(self.evaluated_value))
            except TypeError:
                return "0"

        # Lists — handle special list pipes before the generic renderer
        if isinstance(self.evaluated_value, list):
            def _fmt_num(v):
                return str(int(v) if isinstance(v, float) and v == int(v) else v)

            if self.format_type == "join":
                sep = self.format_options.get("sep", ", ")
                return sep.join(_fmt_num(v) for v in self.evaluated_value)

            if self.format_type == "max_abs":
                result = max(self.evaluated_value, key=abs)
                return _fmt_num(result)

            vals = sorted(self.evaluated_value) if self.format_type == "sorted" \
                   else self.evaluated_value
            return ", ".join(_fmt_num(v) for v in vals)

        # Explicit format type always wins
        if self.format_type is not None:
            formatter_cls = FORMAT_REGISTRY[self.format_type]
            formatter = formatter_cls(**self.format_options)
            return formatter.format(self.evaluated_value)

        expr = self.raw_expr.strip()

        # Single variable → use its default format
        if expr in self.params:
            param = self.params[expr]
            if hasattr(param, "default_format_type") and param.default_format_type:
                formatter_cls = FORMAT_REGISTRY[param.default_format_type]
                fmt_opts = getattr(param, "default_format_options", {})
                formatter = formatter_cls(**fmt_opts)
                if self._is_numeric(self.evaluated_value):
                    return formatter.format(self.evaluated_value)

        # Multi-variable: if all referenced params share a default format, apply it
        vars_in_expr = [name for name in self.params if name in expr]
        if vars_in_expr:
            default_types = {
                self.params[name].default_format_type
                for name in vars_in_expr
                if hasattr(self.params[name], "default_format_type")
            }
            if len(default_types) == 1:
                fmt = default_types.pop()
                if fmt and self._is_numeric(self.evaluated_value):
                    formatter_cls = FORMAT_REGISTRY[fmt]
                    return formatter_cls().format(self.evaluated_value)

        # Fallback: plain string representation
        from fractions import Fraction as _Frac
        if isinstance(self.evaluated_value, _Frac):
            return str(self.evaluated_value)
        try:
            f = float(self.evaluated_value)
            return str(int(f)) if f == int(f) else f"{f:g}"
        except (TypeError, ValueError):
            return str(self.evaluated_value)
