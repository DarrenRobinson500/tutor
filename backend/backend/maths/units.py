"""
Unit prefix conversion utilities.

unit_multiplier(input_prefix, output_prefix) returns the multiplier M such that:

    quantity_in_input_unit * M = quantity_in_output_unit

Examples:
    unit_multiplier('k', 'c')  -> 100000   (1 km = 100 000 cm)
    unit_multiplier('k', '')   -> 1000     (1 km = 1 000 m)
    unit_multiplier('c', 'k')  -> 0.00001  (1 cm = 0.00001 km)
    unit_multiplier('',  'c')  -> 100      (1 m  = 100 cm)
    unit_multiplier('M', 'k')  -> 1000     (1 Mm = 1 000 km)

Returns an int when the multiplier is >= 1 (whole number), otherwise a float.
"""

# SI prefix -> power of 10
_PREFIX_EXPONENT: dict = {
    'T':  12,   # tera
    'G':   9,   # giga
    'M':   6,   # mega
    'k':   3,   # kilo
    'h':   2,   # hecto
    'da':  1,   # deca
    '':    0,   # base unit
    'd':  -1,   # deci
    'c':  -2,   # centi
    'm':  -3,   # milli
    'u':  -6,   # micro (ASCII fallback for μ)
    'μ':  -6,   # micro
    'n':  -9,   # nano
    'p': -12,   # pico
}


def unit_multiplier(input_prefix: str, output_prefix: str):
    """
    Return the multiplier to convert a quantity from input_prefix to output_prefix.

    Raises ValueError if either prefix is unrecognised.
    Returns an int when the result is a whole number, otherwise a float.
    """
    if input_prefix not in _PREFIX_EXPONENT:
        raise ValueError(f"Unknown unit prefix: {input_prefix!r}")
    if output_prefix not in _PREFIX_EXPONENT:
        raise ValueError(f"Unknown unit prefix: {output_prefix!r}")

    exp = _PREFIX_EXPONENT[input_prefix] - _PREFIX_EXPONENT[output_prefix]

    if exp >= 0:
        return 10 ** exp        # int
    else:
        return 10.0 ** exp      # float


if __name__ == "__main__":
    tests = [
        ('k',  'c',  100000),
        ('k',  '',   1000),
        ('',   'c',  100),
        ('M',  'k',  1000),
        ('G',  'M',  1000),
        ('',   '',   1),
        ('c',  'k',  1e-5),
        ('m',  '',   1e-3),
        ('',   'k',  1e-3),
    ]
    for inp, out, expected in tests:
        result = unit_multiplier(inp, out)
        status = "OK" if abs(result - expected) < 1e-15 else f"FAIL (got {result})"
        print(f"unit_multiplier({inp!r:4}, {out!r:4}) = {str(result):15}  {status}")
