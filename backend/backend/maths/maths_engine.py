import sympy as sp
from .probability import *
from .fractions import *

ALLOWED_FUNCS = {
    "ways_sum": ways_sum,
    "nCr": nCr,
    "nPr": nPr,
    "hypergeom": hypergeom,
    "factorial": sp.factorial,
    "denominator": denominator,
    "numerator": numerator,
    "lcm": sp.lcm,
    "gcd": sp.gcd,
}

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
        sympy_expr = float(sp.sympify(expr, locals=ALLOWED_FUNCS))
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


