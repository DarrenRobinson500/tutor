import sympy as sp
from math import comb, factorial, gcd, isqrt
from itertools import product
from ..maths.fractions import denominator, numerator

def evaluate_int_expression(expr, params):
    return int(evaluate_number_expression(expr, params))

def evaluate_dec_expression(expr, params, dp):
    # print("Dec calc", expr, dp)
    result = float(evaluate_number_expression(expr, params,print_details=False))
    # print("Dec calc", result)
    result = round(result, dp)
    # print("Dec calc", result)
    return round(evaluate_number_expression(expr, params), dp)

def evaluate_number_expression(expr: str, params: dict, print_details=False):
    if print_details:
        print("Eval number (pre):", expr)
    for key, val in params.items():
        expr = expr.replace(f"{{{{ {key} }}}}", str(val))
        expr = expr.replace(f"{{{{{key}}}}}", str(val))

    if print_details:
        print("Eval number (post):", expr)

    try:
        sympy_expr = sp.sympify(expr, locals=ALLOWED_FUNCS)
        if print_details:
            print("Sympy number:", sympy_expr)
        return sympy_expr
    except Exception:
        return expr

def evaluate_fraction_expression(expr: str, params: dict):
    for key, val in params.items():
        expr = expr.replace(f"{{{{ {key} }}}}", str(val))
        expr = expr.replace(f"{{{{{key}}}}}", str(val))

    try:
        sympy_expr = sp.sympify(expr, locals=ALLOWED_FUNCS)
        return sp.simplify(sympy_expr)
    except Exception:
        return expr


def surd_coeff(n):
    """Largest integer a such that a² divides n. e.g. surd_coeff(12) = 2"""
    n = int(n)
    for i in range(isqrt(n), 1, -1):
        if n % (i * i) == 0:
            return i
    return 1

def surd_radicand(n):
    """Remaining radicand after extracting perfect square. e.g. surd_radicand(12) = 3"""
    n = int(n)
    for i in range(isqrt(n), 1, -1):
        if n % (i * i) == 0:
            return n // (i * i)
    return n

def factors(n):
    """Return all factors of n as a comma-separated string, e.g. factors(10) → '1, 2, 5, 10'."""
    n = int(n)
    result = sorted(i for i in range(1, n + 1) if n % i == 0)
    return ", ".join(str(i) for i in result)

def nCr(n, r):
    return comb(n, r)

def nPr(n, r):
    return factorial(n) // factorial(n - r)

def ways_sum(dice, target):
    count = 0
    for outcome in product(range(1, 7), repeat=dice):
        if sum(outcome) == target:
            count += 1
    return count

def hypergeom(N, K, n, k):
    return comb(K, k) * comb(N - K, n - k) / comb(N, n)

ALLOWED_FUNCS = {
    "factors": factors,
    "ways_sum": ways_sum,
    "nCr": nCr,
    "nPr": nPr,
    "hypergeom": hypergeom,
    "factorial": sp.factorial,
    "gcd": gcd,
    "denominator": denominator,
    "numerator": numerator,
    "sqrt": sp.sqrt,
    "surd_coeff": surd_coeff,
    "surd_radicand": surd_radicand,
    "min": sp.Min,
    "max": sp.Max,
    "abs": sp.Abs,
}
