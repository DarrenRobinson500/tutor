import sympy as sp


def denominator(x):
    """Return the denominator of a fraction value.

    Works with sympy Rationals (have .q), Python Fractions (have .denominator),
    integers, and floats.
    """
    # sympy Rational: has .q attribute
    if hasattr(x, 'q'):
        return int(x.q)
    # Python fractions.Fraction or int: has .denominator attribute
    if hasattr(x, 'denominator'):
        return int(x.denominator)
    # String like "3/4" (as stored in param.value during validation)
    if isinstance(x, str):
        from fractions import Fraction as _F
        return _F(x).denominator
    # Fallback: convert via nsimplify (handles floats etc.)
    r = sp.nsimplify(x)
    if hasattr(r, 'q'):
        return int(r.q)
    return 1


def numerator(x):
    """Return the numerator of a fraction value (after simplification).

    E.g. numerator(3/4) → 3, numerator(6) → 6.
    """
    # sympy Rational: has .p attribute
    if hasattr(x, 'p'):
        return int(x.p)
    # Python fractions.Fraction or int: has .numerator attribute
    if hasattr(x, 'numerator'):
        return int(x.numerator)
    # String like "3/4" (as stored in param.value during validation)
    if isinstance(x, str):
        from fractions import Fraction as _F
        return _F(x).numerator
    # Fallback: convert via nsimplify
    r = sp.nsimplify(x)
    if hasattr(r, 'p'):
        return int(r.p)
    return int(x)
