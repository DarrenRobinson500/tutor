import random

FORMAT_REGISTRY = {}

def register_format_type(cls):
    FORMAT_REGISTRY[cls.name] = cls
    return cls

class FormatType:
    name = None  # e.g. "fraction", "number", "percentage"

    def __init__(self, **options):
        self.options = options

    def format(self, value):
        raise NotImplementedError("FormatType subclasses must implement format()")

@register_format_type
class FractionFormat(FormatType):

    name = "fraction"
    default_format_type = "fraction"


    def format(self, value):
        # value may be "3/4", "-2/7", etc.
        if isinstance(value, str) and "/" in value:
            num, den = value.split("/")
            num, den = int(num), int(den)
        else:
            # Convert sympy types, floats, etc. to a Python Fraction
            from fractions import Fraction
            frac = Fraction(float(value)).limit_denominator(1000)
            num, den = frac.numerator, frac.denominator

        if num == 0 or den == 1:
            return str(num)

        return f"\\frac{{{num}}}{{{den}}}"

@register_format_type
class ImproperFractionFormat(FormatType):
    """Displays a value as a LaTeX improper fraction when |value| > 1,
    or as a regular fraction / integer otherwise.
    e.g. 7/3 → \\frac{7}{3}, 3/4 → \\frac{3}{4}, 2 → 2, 0 → 0"""
    name = "improper"

    def format(self, value):
        if isinstance(value, str) and "/" in value:
            num, den = int(value.split("/")[0]), int(value.split("/")[1])
        else:
            from fractions import Fraction
            frac = Fraction(float(value)).limit_denominator(1000)
            num, den = frac.numerator, frac.denominator

        if num == 0 or den == 1:
            return str(num)

        return f"\\frac{{{num}}}{{{den}}}"

@register_format_type
class ProperFractionFormat(FormatType):
    """Converts an improper fraction to plain-text mixed number form for answer input.
    e.g. 7/3 → "2 1/3", 8/4 → "2", 3/4 → "3/4" (proper fractions unchanged)
    Outputs plain text (not LaTeX) so students can type it directly."""
    name = "proper_fraction"

    def format(self, value):
        if isinstance(value, str) and "/" in value:
            num, den = int(value.split("/")[0]), int(value.split("/")[1])
        else:
            from fractions import Fraction
            frac = Fraction(float(value)).limit_denominator(1000)
            num, den = frac.numerator, frac.denominator

        if den == 1 or num == 0:
            return str(num)
        whole = num // den
        remainder = num % den
        if remainder == 0:
            return str(whole)
        if whole == 0:
            return f"{num}/{den}"
        return f"{whole} {remainder}/{den}"

@register_format_type
class MixedNumberFormat(FormatType):
    name = "mixed_number"

    def format(self, value):
        if isinstance(value, str) and "/" in value:
            num, den = int(value.split("/")[0]), int(value.split("/")[1])
        else:
            from fractions import Fraction
            frac = Fraction(float(value)).limit_denominator(1000)
            num, den = frac.numerator, frac.denominator

        if num == 0:
            return "0"
        if den == 1:
            return str(num)

        sign_str = "-" if num < 0 else ""
        abs_num = abs(num)
        whole = abs_num // den
        remainder = abs_num % den

        if remainder == 0:
            return f"{sign_str}{whole}"
        if whole == 0:
            return f"{sign_str}\\frac{{{remainder}}}{{{den}}}"
        return f"{sign_str}{whole}\\frac{{{remainder}}}{{{den}}}"

@register_format_type
@register_format_type
class DecimalFormat(FormatType):
    name = "decimal"

    def format(self, value):
        dp = int(self.options.get("decimal_places", 2))
        if isinstance(value, str) and "/" in value:
            from fractions import Fraction
            value = float(Fraction(value))
        return f"{float(value):.{dp}f}"


def _decimal_alias(dp: int):
    class _Fmt(DecimalFormat):
        name = f"decimal_{dp}"
        def format(self, value, _dp=dp):
            if isinstance(value, str) and "/" in value:
                from fractions import Fraction as _F
                value = float(_F(value))
            return f"{float(value):.{_dp}f}"
    _Fmt.__name__ = f"Decimal{dp}Format"
    return _Fmt

for _i in range(1, 6):
    FORMAT_REGISTRY[f"decimal_{_i}"] = _decimal_alias(_i)

@register_format_type
class DollarFormat(FormatType):
    name = "dollar"

    def format(self, value):
        if isinstance(value, str) and "/" in value:
            num, den = value.split("/", 1)
            value = int(num) / int(den)
        result = f"{float(value):,.2f}"
        # Strip ".00" for whole dollar amounts — $5 is cleaner than $5.00
        # Use \$ so KaTeX renders a literal dollar sign rather than entering math mode
        if result.endswith(".00"):
            return f"\\${result[:-3]}"
        return f"\\${result}"

@register_format_type
class PercentFormat(FormatType):
    name = "percent"

    def format(self, value):
        if isinstance(value, str) and "/" in value:
            from fractions import Fraction
            value = float(Fraction(value))
        f = float(value) * 100
        if "decimal_places" in self.options:
            dp = int(self.options["decimal_places"])
            return f"{f:.{dp}f}%"
        if f == int(f):
            return f"{int(f)}%"
        return f"{round(f, 2):g}%"

@register_format_type
class NumberFormat(FormatType):
    name = "number"
    default_format_type = "number"

    def format(self, value):
        sig_figs = int(self.options.get("sig_figs", 3))
        return f"{value:.{sig_figs}g}"

@register_format_type
class PercentageFormat(FormatType):
    name = "percentage"

    def format(self, value):
        sig_figs = int(self.options.get("sig_figs", 3))
        return f"{value * 100:.{sig_figs}g}%"

@register_format_type
class SurdFormat(FormatType):
    """Simplifies sqrt(n) into LaTeX surd form: e.g. sqrt(12) → 2\sqrt{3}, sqrt(16) → 4."""
    name = "surd"

    def format(self, value):
        from math import isqrt
        fv = float(value)
        # If value is (approximately) a whole number it's the radicand directly (e.g. 45).
        # Otherwise it's sqrt(n) — square it to recover n (handles sympy objects and floats).
        if abs(fv - round(fv)) < 1e-6:
            n = int(round(fv))
        else:
            n = int(round(fv ** 2))
        # Extract the largest perfect square factor
        a = 1
        for i in range(isqrt(n), 1, -1):
            if n % (i * i) == 0:
                a = i
                break
        b = n // (a * a)
        if b == 1:
            return str(a)
        if a == 1:
            return f"\\sqrt{{{b}}}"
        return f"{a}\\sqrt{{{b}}}"

@register_format_type
class IntegerFormat(FormatType):
    name = "integer"

    def format(self, value):
        return str(int(value))

@register_format_type
class PronumeralFormat(FormatType):
    """Suppresses the value when it equals 1 (or -1 shows as '-'), for use as
    an algebraic coefficient.  e.g. {{ a | pronumeral }}x renders as 'x' not '1x',
    and -1 renders as '-' so '-x' is formed naturally."""
    name = "pronumeral"

    def format(self, value):
        from fractions import Fraction
        try:
            v = Fraction(value)
        except (TypeError, ValueError):
            try:
                v = Fraction(float(value))
            except Exception:
                return str(value)
        if v == 1:
            return ""
        if v == -1:
            return "-"
        return str(int(v)) if v.denominator == 1 else str(v)


@register_format_type
class BracketsFormat(FormatType):
    """Wraps the value in parentheses if negative, leaves positive values unchanged.
    e.g. -7 → (-7), 6 → 6"""
    name = "brackets"

    def format(self, value):
        n = int(value)
        if n < 0:
            return f"({n})"
        return str(n)

@register_format_type
class CommaFormat(FormatType):
    """Formats an integer with comma thousand-separators: 1234567 → 1,234,567."""
    name = "comma"

    def format(self, value):
        return f"{int(value):,}"

@register_format_type
class WordsFormat(FormatType):
    """Converts an integer to English words: 327 → 'three hundred and twenty-seven'."""
    name = "words"

    _ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
             "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
             "seventeen", "eighteen", "nineteen"]
    _tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

    def format(self, value):
        n = int(value)
        if n < 0:
            return "negative " + self.format(-n)
        return self._convert(n)

    def _convert(self, n):
        if n == 0:
            return "zero"
        if n < 20:
            return self._ones[n]
        if n < 100:
            rest = self._ones[n % 10]
            return self._tens[n // 10] + ("-" + rest if rest else "")
        if n < 1000:
            rest = n % 100
            suffix = (" and " + self._convert(rest)) if rest else ""
            return self._ones[n // 100] + " hundred" + suffix
        if n < 1_000_000:
            rest = n % 1000
            suffix = (" and " + self._convert(rest)) if rest else ""
            return self._convert(n // 1000) + " thousand" + suffix
        if n < 1_000_000_000:
            rest = n % 1_000_000
            suffix = (" and " + self._convert(rest)) if rest else ""
            return self._convert(n // 1_000_000) + " million" + suffix
        return str(n)


@register_format_type
class RatioFormat(FormatType):
    """Converts a fraction or float to ratio notation: 5/2 → '5:2', 2.5 → '5:2'."""
    name = "ratio"

    def format(self, value):
        if isinstance(value, str) and "/" in value:
            num, den = int(value.split("/")[0]), int(value.split("/")[1])
        else:
            from fractions import Fraction
            frac = Fraction(float(value)).limit_denominator(1000)
            num, den = frac.numerator, frac.denominator
        if den == 1:
            return f"{num}:1"
        return f"{num}:{den}"

@register_format_type
class SimplifiedRatioFormat(FormatType):
    """Simplifies a ratio string: '4:8' → '1:2', '6:9' → '2:3'."""
    name = "simplified"

    def format(self, value):
        from math import gcd
        s = str(value).strip()
        if ":" not in s:
            return s
        parts = s.split(":")
        if len(parts) != 2:
            return s
        try:
            a, b = int(parts[0].strip()), int(parts[1].strip())
        except ValueError:
            return s
        if a == 0 and b == 0:
            return s
        divisor = gcd(abs(a), abs(b))
        return f"{a // divisor}:{b // divisor}"

@register_format_type
class OperationFormat(FormatType):
    """Converts operator symbols to typeset characters: * → ×, / → ÷."""
    name = "operation"

    _MAP = {"*": "\\times", "/": "\\div", "+": "+", "-": "-", "×": "\\times", "÷": "\\div"}

    def format(self, value):
        return self._MAP.get(str(value).strip(), str(value))

@register_format_type
class FactorFormat(FormatType):
    """Prime factorisation: factor(12) → '2 x 2 x 3', factor(100) → '2 x 2 x 5 x 5'."""
    name = "factor"

    def format(self, value):
        n = int(value)
        if n < 2:
            return str(n)
        factors = []
        d = 2
        while d * d <= n:
            while n % d == 0:
                factors.append(str(d))
                n //= d
            d += 1
        if n > 1:
            factors.append(str(n))
        return " x ".join(factors)

def _to_superscript(s: str) -> str:
    """Convert a digit/sign string to unicode superscript characters."""
    table = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")
    return s.translate(table)

@register_format_type
class ScientificNotationFormat(FormatType):
    """Formats a number in scientific notation using unicode: 3200 → 3.2 × 10³.
    Renders correctly both inside and outside LaTeX math delimiters.
    Options:
      sig_figs (int, default 3): significant figures for the coefficient.
      strip_trailing_zeros (bool, default True): remove trailing zeros from coefficient.
    """
    name = "scientific_notation"

    def format(self, value):
        from fractions import Fraction
        import math

        if isinstance(value, str) and "/" in value:
            value = float(Fraction(value))
        v = float(value)

        if v == 0:
            return "0"

        sig_figs = int(self.options.get("sig_figs", 3))
        strip = self.options.get("strip_trailing_zeros", True)

        exp = int(math.floor(math.log10(abs(v))))
        coeff = v / (10 ** exp)

        decimal_places = sig_figs - 1
        coeff = round(coeff, decimal_places)

        # Handle rounding carry (e.g. 9.9999... → 10.0)
        if abs(coeff) >= 10:
            coeff /= 10
            exp += 1

        if strip:
            coeff_str = f"{coeff:.{decimal_places}f}".rstrip("0").rstrip(".")
        else:
            coeff_str = f"{coeff:.{decimal_places}f}"

        sup = _to_superscript(str(exp))
        return f"{coeff_str} × 10{sup}"


@register_format_type
class LowerFormat(FormatType):
    """Converts a string value to lowercase: 'Run' → 'run'."""
    name = "lower"

    def format(self, value):
        return str(value).lower()


@register_format_type
class CapitalizeFormat(FormatType):
    """Capitalizes the first letter of a string: 'students' → 'Students'."""
    name = "capitalize"

    def format(self, value):
        return str(value).capitalize()


@register_format_type
class ExprFormat(FormatType):
    """Formats an algebraic expression string for readable display.

    Transformations applied:
      - ** or ^ exponents kept as ^ (Latex component renders ^ as superscript)
      - Removes multiplication sign: 2*x → 2x
      - Collapses redundant sign pairs: + - → -, - - → +
    """

    name = "expr"

    def format(self, value):
        import re
        v = str(value)
        # Normalise Python-style ** to ^
        v = v.replace("**", "^")
        # Remove explicit multiplication sign (but not **)
        v = v.replace("*", "")
        # Collapse sign pairs (with optional surrounding spaces)
        v = re.sub(r'\+\s*-', '- ', v)
        v = re.sub(r'-\s*-', '+ ', v)
        # Remove coefficient of 1 before a variable: 1x → x, -1x → -x
        # Lookbehind prevents matching inside multi-digit numbers (e.g. 11x stays)
        v = re.sub(r'(?<!\d)1(?=[a-zA-Z])', '', v)
        # Remove zero pronumeral terms (e.g. + 0x, - 0x^2)
        v = re.sub(r'\s*[+\-]\s*0[a-zA-Z][a-zA-Z0-9^]*', '', v)   # middle
        v = re.sub(r'^0[a-zA-Z][a-zA-Z0-9^]*', '', v)               # leading
        # Remove zero constant terms (e.g. + 0, - 0, but not + 0.5 or + 0x)
        v = re.sub(r'\s*[+\-]\s*0(?![a-zA-Z0-9.])', '', v)          # middle
        v = re.sub(r'^0(?![a-zA-Z0-9.])', '', v)                     # leading
        # Clean up any leading + exposed after removing a leading zero term
        v = re.sub(r'^\s*\+\s*', '', v)
        # If everything cancelled to nothing, the expression equals zero
        if not v.strip():
            v = "0"
        # Tidy up any double spaces introduced
        v = re.sub(r'  +', ' ', v).strip()
        return v