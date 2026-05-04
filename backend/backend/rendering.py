import re
import random
from math import gcd
import yaml as _yaml
from .diagram.engine import *
from .maths.maths_engine import *


def _escape_backslashes_in_dq_strings(text: str) -> str:
    """Pre-process YAML text so that backslashes inside double-quoted strings
    are escaped before yaml.safe_load runs.  This prevents YAML from treating
    LaTeX commands such as \\times, \\alpha, \\frac etc. as escape sequences
    (e.g. \\t → tab, \\a → bell).

    Rules applied inside each "…" scalar:
      \\\\  (already-escaped backslash) — left unchanged
      \\"   (escaped quote)            — left unchanged
      \\X   (any other single char)    — doubled to \\\\X so YAML keeps it literal
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != '"':
            out.append(ch)
            i += 1
            continue
        # Enter double-quoted scalar
        out.append('"')
        i += 1
        while i < n:
            ch = text[i]
            if ch == '\\' and i + 1 < n:
                nxt = text[i + 1]
                if nxt in ('"', '\\'):
                    # Keep \" and \\ exactly as-is
                    out.append('\\')
                    out.append(nxt)
                    i += 2
                else:
                    # Single backslash before a regular char — escape it
                    out.append('\\\\')
                    out.append(nxt)
                    i += 2
            elif ch == '"':
                out.append('"')
                i += 1
                break
            else:
                out.append(ch)
                i += 1
    return ''.join(out)


def load_template_yaml(text: str) -> dict:
    """Parse template YAML, preserving LaTeX backslash commands in double-quoted strings."""
    return _yaml.safe_load(_escape_backslashes_in_dq_strings(text)) or {}

def render_fraction_latex(value: str):
    if isinstance(value, str) and "/" in value:
        parts = value.split("/")
        if len(parts) == 2:
            num, den = parts
            return f"\\frac{{{num}}}{{{den}}}"
    return value


def evaluate_expression(expr: str, params=None):
    return evaluate_int_expression(expr, params or {})

def substitute_params_and_expressions(text, params):
    pattern = r"\{\{\s*(.*?)\s*\}\}"

    def repl(match):
        expr = match.group(1).strip()

        # Step 1: Replace identifiers with param values
        substituted_expr = expr
        for key, val in params.items():
            substituted_expr = re.sub(rf"\b{key}\b", str(val), substituted_expr)

        # Step 2: Evaluate the substituted expression
        try:
            # If the substituted expression is a simple fraction like "1/8", return it unchanged
            if "/" in substituted_expr and substituted_expr.replace("/", "").isdigit():
                print("Substitute (found /):", substituted_expr)
                return substituted_expr

            # Otherwise evaluate normally
            value = evaluate_number_expression(substituted_expr, {})
            print("Substitute (didn't find /)", substituted_expr, str(value))
            return str(value)

        except Exception:
            return f"{{{{ {expr} }}}}"

    result = re.sub(pattern, repl, text)
    return result

def generate_param_values(params):
    """Generate numeric or fraction values for params based on YAML structure."""
    generated = {}

    for key, spec in params.items():

        # Case 1: literal values (int, float, str)
        if isinstance(spec, (int, float, str)):
            generated[key] = spec
            continue

        # Case 2: random range { min: X, max: Y }
        if isinstance(spec, dict) and "min" in spec and "max" in spec:
            generated[key] = random.randint(spec["min"], spec["max"])
            continue

        # Case 3: expression-based value { type: int, value: "{{ a * c }}" }
        if isinstance(spec, dict) and "value" in spec and spec.get("type") == "int":
            raw_expr = spec["value"]
            substituted = substitute_params_and_expressions(raw_expr, generated)
            try:
                generated[key] = evaluate_expression(substituted)
            except Exception:
                generated[key] = None
            continue

        # Case X: Structured FRACTION type with constraints
        if isinstance(spec, dict) and spec.get("type") == "fraction":
            # 1. Generate numerator and denominator
            num = random.randint(spec.get("min_numerator", 1), spec.get("max_numerator", 9))
            den = random.randint(spec.get("min_denominator", 2), spec.get("max_denominator", 12))

            # 2. Enforce proper/improper if specified
            if spec.get("proper") is True and num >= den:
                num, den = den - 1, den  # simple correction; could retry instead
            if spec.get("proper") is False and num <= den:
                num, den = den + 1, den

            # 3. Simplify if required
            if spec.get("simplified", True):
                g = gcd(num, den)
                num //= g
                den //= g

            # 4. Store as "num/den"
            generated[key] = f"{num}/{den}"
            continue
        continue

        # Case 5: unsupported → None
        generated[key] = None

    # debug_print_params(generated)
    # print("Generated params:", generated)
    return generated

def evaluate_rule_expression(expr, params):
    # Evaluate rule like "b != 0" or "c != d"
    # Only allow access to params, nothing else
    safe_locals = dict(params)
    return bool(eval(expr, {"__builtins__": {}}, safe_locals))

def render_template_preview(parsed):
    # print("Rendering template preview")
    """
    1. Generate parameters
    2. Substitute ALL {{ ... }} in the entire YAML
    3. Reload substituted YAML
    4. Render question, answers, solution, diagram, etc.
    """

    # 1. Generate parameters + enforce validation rules
    collected_errors = []
    params = parsed.get("parameters", {})
    validation = parsed.get("validation", {})
    rules = validation.get("rules", [])

    MAX_ATTEMPTS = 10
    last_error = None

    for attempt in range(MAX_ATTEMPTS):
        generated_params = generate_param_values(params)

        rule_failed = False
        for rule in rules:
            expr = rule.get("check")
            message = rule.get("message", "Validation rule failed")

            try:
                if not evaluate_rule_expression(expr, generated_params):
                    rule_failed = True
                    last_error = message
                    break
            except Exception as e:
                rule_failed = True
                last_error = f"Rule error: {str(e)}"
                collected_errors.append(f"{last_error}")
                break

        if not rule_failed:
            break
    else:
        collected_errors.append(f"Parameter generation failed after {MAX_ATTEMPTS} attempts: {last_error}")
        raise ValueError(
            f"Parameter generation failed after {MAX_ATTEMPTS} attempts: {last_error}"
        )


    # 2. Substitute parameters
    # print("Substituting parameters")

    original_yaml_text = _yaml.dump(parsed, allow_unicode=True)
    substituted_yaml_text = substitute_params_and_expressions(original_yaml_text, generated_params)
    # print("Substituted yaml text:", substituted_yaml_text)

    result = {
        "substituted_yaml": substituted_yaml_text,
        "params": generated_params,
    }

    # 3. Reload substituted YAML
    substituted = load_template_yaml(substituted_yaml_text)

    # 4. Extract substituted fields
    try:
        question_text = substituted.get("question", {}).get("text", "")
    except Exception as e:
        question_text = f"[ERROR extracting question: {e}]"
        collected_errors.append(question_text)

    solution_block = substituted.get("solution", {})
    if isinstance(solution_block, dict):
        solution_text = solution_block.get("text", "")
    else:
        solution_text = f"[ERROR: solution must be a mapping, got {type(solution_block).__name__}]"
        collected_errors.append(solution_text)

    raw_answers = substituted.get("answers")
    # print("Render template preview (raw answers):", raw_answers)

    if isinstance(raw_answers, dict):
        raw_answers = raw_answers.get("text", [])

    if not isinstance(raw_answers, list):
        collected_errors.append(f"Answers must be a list, got: {type(raw_answers).__name__}")
        raw_answers = []

    answers = []

    for ans in raw_answers:
        print("Render template preview (raw answers):", raw_answers)

        # New unified format: text + format + correct
        if "text" in ans and "format" in ans:
            format_type = ans["format"]
            raw_text = str(ans.get("text", ""))
            substituted_text = substitute_params_and_expressions(raw_text, generated_params)
            # Apply the named formatter from the format registry
            from .render.format import FORMAT_REGISTRY
            formatter_cls = FORMAT_REGISTRY.get(format_type)
            if formatter_cls:
                try:
                    from fractions import Fraction
                    val = Fraction(substituted_text).limit_denominator(1000) if "/" in substituted_text else float(substituted_text)
                    text = formatter_cls().format(val)
                except Exception:
                    text = substituted_text
            else:
                text = substituted_text
            answers.append({"text": text, "correct": ans.get("correct", False)})
            continue

        if "logic" in ans:
            condition = ans["logic"]
            print("Condition:", condition)
            print("Generated params:", generated_params)
            try:
                is_true = evaluate_rule_expression(condition, generated_params)
            except Exception:
                is_true = False

            # Mark correct only if BOTH:
            # 1. YAML says correct: true
            # 2. Condition evaluates to true
            answers.append({
                "text": ans.get("text", ""),
                "correct": ans.get("correct", False) and is_true
            })
            continue

        if "int" in ans:
            answers.append({"text": str(evaluate_int_expression(ans["int"], generated_params)),"correct": ans.get("correct", False)})
            continue
        if "dec_1" in ans:
            answers.append({"text": str(evaluate_dec_expression(ans["dec_1"], generated_params, 1)),"correct": ans.get("correct", False)})
            continue
        if "dec_2" in ans:
            print("Render template preview (ans):", ans["dec_2"])
            answers.append({"text": str(evaluate_dec_expression(ans["dec_2"], generated_params, 2)),"correct": ans.get("correct", False)})
            continue

        if "fraction" in ans:
            expr = ans["fraction"]
            print("Render template preview:", expr)
            value = evaluate_fraction_expression(expr, generated_params)
            answers.append({
                "text": render_fraction_latex(str(value)),
                "correct": ans.get("correct", False)
            })
            continue

        answers.append(ans)

    seen = set()
    deduped_answers = []
    for ans in answers:
        text = ans.get("text")
        if text not in seen:
            seen.add(text)
            deduped_answers.append(ans)

    # Diagram SVG + code (already substituted)
    # print("Rendering (substituted parameters for diagram):", substituted["diagram"])

    diagram_code = substituted.get("diagram", "")

    svg = ""
    if isinstance(diagram_code, str) and diagram_code.strip():
        svg = render_diagram_from_code(diagram_code)
    else:
        # print("Failed to svg render:", diagram_code, isinstance(diagram_code, str))
        diagram_code = ""

    substituted = build_debug_yaml(parsed, generated_params, substituted)
    substituted = substituted.replace("\\n", "\n")

    try:                    result['question'] = render_fraction_latex(question_text)
    except Exception as e:  result['question'] = f"[ERROR: {e}]"

    try:                    result['answers'] = deduped_answers
    except Exception as e:  result['answers'] = f"[ERROR: {e}]"

    try:                    result['params'] = generated_params
    except Exception as e:  result['params'] = f"[ERROR: {e}]"

    try:                    result['solution'] = render_fraction_latex(solution_text)
    except Exception as e:  result['solution'] = f"[ERROR: {e}]"

    try:                    result['diagram_svg'] = svg
    except Exception as e:  result['diagram_svg'] = f"[ERROR: {e}]"

    try:                    result['diagram_code'] = diagram_code
    except Exception as e:  result['diagram_code'] = f"[ERROR: {e}]"

    try:                    result['substituted_yaml'] = substituted
    except Exception as e:  result[''] = f"[ERROR: {e}]"

    result['errors'] = collected_errors

    return result

def debug_print_params(params: dict):
    print("Generated Parameters:")
    max_len = max(len(k) for k in params.keys()) if params else 0
    for key, value in params.items():
        print(f"  {key.ljust(max_len)} : {value}")

def build_debug_yaml(parsed, generated_params, substituted):
    debug = {}

    debug["parameters"] = generated_params
    debug["question"] = substituted.get("question", {}).get("text", "")
    debug["solution"] = substituted.get("solution", {}).get("text", "")
    debug["answers"] = substituted.get("answers", [])
    debug["diagram"] = substituted.get("diagram", {})

    return _yaml.dump(debug, sort_keys=False, allow_unicode=True)