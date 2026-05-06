import yaml
import yaml as _yaml
import re
from .expr import *
from .format import FORMAT_REGISTRY
from ..rendering import load_template_yaml

_DEFAULT_FORMAT_INSTRUCTIONS = {
    "percent":              "Enter as a percentage, e.g. 25%",
    "percentage":           "Enter as a percentage, e.g. 25%",
    "fraction":             "Enter as an improper fraction, e.g. 7/3",
    "integer":              "Enter a whole number, e.g. 42",
    "decimal":              "Give your answer as a decimal",
    "decimal_1":            "Give your answer to 1 decimal place",
    "decimal_2":            "Give your answer to 2 decimal places",
    "decimal_3":            "Give your answer to 3 decimal places",
    "decimal_4":            "Give your answer to 4 decimal places",
    "decimal_5":            "Give your answer to 5 decimal places",
    "ratio":                "Enter as a ratio, e.g. 1:2",
    "proper_fraction":      "Enter as a mixed number, e.g. 2 1/3",
    "scientific_notation":  "Enter in scientific notation, e.g. 3.2 × 10^3",
}

# Match {{{...}}} (LaTeX-brace-wrapped expression) before {{...}} (plain expression).
# Group 1 = triple-brace expression (result wrapped in { } for LaTeX)
# Group 2 = double-brace expression (result substituted as-is)
EXPR_PATTERN = re.compile(r"\{\{\{(.*?)\}\}\}|\{\{(.*?)\}\}")


def _inject_format_pipe(text, format_type):
    """Rewrite {{ expr }} → {{ expr | format_type }} where no pipe already exists."""
    def repl(match):
        triple = match.group(1) is not None
        expr = (match.group(1) if triple else match.group(2)).strip()
        if "|" in expr:
            return match.group(0)
        if triple:
            return "{{{" + expr + " | " + format_type + "}}}"
        return "{{ " + expr + " | " + format_type + " }}"
    return EXPR_PATTERN.sub(repl, text)

def _expand_inline_expr(yaml_text: str) -> str:
    """
    Expand the shorthand ``name: expr: "..."`` onto two lines before PyYAML sees it.

    Converts:
        q1_clean:     expr: "quartile(core_data, 1)"
    to:
        q1_clean:
          expr: "quartile(core_data, 1)"

    Only fires when ``expr:`` immediately follows a plain identifier key on the
    same line, which is otherwise a YAML scanner error.
    """
    pattern = re.compile(r'^(\s*)(\w+):\s+(expr:\s*.+)$', re.MULTILINE)

    def repl(m):
        indent, name, rest = m.group(1), m.group(2), m.group(3)
        child_indent = indent + '  '
        return f'{indent}{name}:\n{child_indent}{rest}'

    return pattern.sub(repl, yaml_text)


def _quote_bare_expressions(yaml_text: str) -> str:
    """
    Auto-quote YAML scalar values that start with {{ so the YAML parser doesn't
    mistake them for flow mappings.  Only rewrites lines of the form:
        key: {{ ... }}          →  key: "{{ ... }}"
    Skips lines where the value is already quoted or is a block scalar indicator.
    Skips continuation lines that are inside single-quoted YAML scalars (e.g. when
    PyYAML wraps a long diagram string across multiple lines).
    """
    KEY_EXPR = re.compile(r'^(\s*)([\w_]+):\s*(\{\{.*)')

    def repl(m):
        indent, key, value = m.group(1), m.group(2), m.group(3)
        if value.startswith('"') or value.startswith("'"):
            return m.group(0)
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'{indent}{key}: "{escaped}"'

    lines = yaml_text.splitlines(keepends=True)
    result = []
    in_single_quoted = False  # True while inside a multi-line single-quoted scalar

    for line in lines:
        stripped = line.rstrip('\n\r')

        if in_single_quoted:
            # Count unescaped single quotes: '' is an escaped quote in YAML single scalars.
            # An odd count means this line closes the open scalar.
            n = stripped.replace("''", "").count("'")
            if n % 2 == 1:
                in_single_quoted = False
            result.append(line)  # continuation lines are never rewritten
        else:
            # Detect whether this line opens a single-quoted scalar that isn't
            # closed on the same line (PyYAML wraps long values across lines).
            sq_open = re.match(r"^\s*[\w_]+:\s*'(.*)", stripped)
            if sq_open:
                rest = sq_open.group(1)
                n = rest.replace("''", "").count("'")
                if n % 2 == 0:   # even → no closing quote on this line → multi-line
                    in_single_quoted = True

            result.append(KEY_EXPR.sub(repl, line))

    return ''.join(result)


class Render:
    def __init__(self, yaml_text):
        self.yaml_text = _quote_bare_expressions(_expand_inline_expr(yaml_text))
        self.template = load_template_yaml(self.yaml_text)

        # Filled during rendering
        self.param_objects = {}
        self.substituted_yaml = None
        self.preview_yaml = None

    def render(self):
        self._load_parameters()
        self._substitute_expressions()
        return {
            "substituted_yaml": self.substituted_yaml,
            "preview": self.preview_yaml,
        }

    def _load_parameters(self):
        from .param import NameParameter, ExprParameter
        NameParameter._used_in_render = set()
        param_specs = self.template.get("parameters", {})
        for name, spec in param_specs.items():
            self.param_objects[name] = RandomParameter.from_yaml(name, spec)
        # Second pass: resolve derived (expr) parameters in dependency order.
        # YAML loaders may not preserve insertion order, so we do a topological
        # sort to ensure each ExprParameter is resolved after its dependencies.
        expr_names = [n for n, p in self.param_objects.items() if isinstance(p, ExprParameter)]
        all_names = set(self.param_objects)
        # Build dependency map: which other params does each expr reference?
        deps = {}
        for n in expr_names:
            expr = self.param_objects[n]._expr
            deps[n] = {p for p in all_names if p != n and re.search(rf'\b{re.escape(p)}\b', expr)}
        # Kahn's topological sort
        in_degree = {n: len(deps[n] & set(expr_names)) for n in expr_names}
        queue = [n for n in expr_names if in_degree[n] == 0]
        ordered = []
        while queue:
            node = queue.pop(0)
            ordered.append(node)
            for other in expr_names:
                if node in deps[other]:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)
        # Append any remaining (circular deps — will raise naturally on resolve)
        for n in expr_names:
            if n not in ordered:
                ordered.append(n)
        for name in ordered:
            self.param_objects[name].resolve(self.param_objects)

    def _substitute_expressions(self):
        # Deep copy the template for two different outputs
        substituted = load_template_yaml(self.yaml_text)
        preview = load_template_yaml(self.yaml_text)

        def walk(node, formatter):
            if isinstance(node, str):
                return self._process_string(node, formatter)
            if isinstance(node, list):
                return [walk(item, formatter) for item in node]
            if isinstance(node, dict):
                return {k: walk(v, formatter) for k, v in node.items()}
            return node

        self.substituted_yaml = walk(substituted, formatter="raw")
        self.preview_yaml = walk(preview, formatter="formatted")

    def _process_string(self, text, formatter):
        def repl(match):
            triple = match.group(1) is not None
            expr_text = (match.group(1) if triple else match.group(2)).strip()

            # Special function: Knowledge("title") — store ref, return sentinel
            kn_match = re.match(r'^Knowledge\s*\(\s*["\']([^"\']+)["\']\s*\)$', expr_text)
            if kn_match:
                title = kn_match.group(1)
                if not hasattr(self, '_knowledge_refs'):
                    self._knowledge_refs = []
                idx = len(self._knowledge_refs)
                self._knowledge_refs.append(title)
                return f"\u27e6KN:{idx}\u27e7"

            try:
                node = ExpressionNode(expr_text, self.param_objects)
            except Exception as e:
                raise ValueError(f"Error evaluating expression '{{{{ {expr_text} }}}}': {e}") from e
            value = node.evaluate()

            if formatter == "raw":
                try:
                    f = float(value)
                    value = int(f) if f == int(f) else round(f, 10)
                except (TypeError, ValueError):
                    # value may be a fraction string like "5/1" (DollarParameter) or
                    # "15/2" (dollar with cents). For non-fraction param types convert
                    # to a plain number; leave FractionParameter values as "n/d".
                    if isinstance(value, str) and re.fullmatch(r'-?\d+/-?\d+', value.strip()):
                        expr_bare = getattr(node, 'raw_expr', '').strip()
                        param = self.param_objects.get(expr_bare)
                        fmt_type = getattr(param.__class__, 'default_format_type', None) if param else None
                        if fmt_type in ('dollar', 'decimal', 'percent'):
                            try:
                                from fractions import Fraction as _Frac
                                frac_f = float(_Frac(value))
                                value = int(frac_f) if frac_f == int(frac_f) else round(frac_f, 10)
                            except Exception:
                                pass
                result = str(value)
            else:
                result = node.format()

            return "{" + result + "}" if triple else result

        substituted = EXPR_PATTERN.sub(repl, text)
        # Wrap negative or multi-digit values after ^ or _ in LaTeX braces.
        # e.g. $x^-4$ → $x^{-4}$, $x^12$ → $x^{12}$. Skip if already braced.
        substituted = re.sub(r'(\^|_)(?!\{)(-\d+|\d{2,})', r'\1{\2}', substituted)
        return substituted


def _evaluate_rule(expr, params):
    from math import gcd
    from fractions import Fraction
    from ..maths.fractions import denominator, numerator
    # Allow {{ a }} style in addition to bare variable names
    expr = EXPR_PATTERN.sub(lambda m: (m.group(1) or m.group(2) or "").strip(), expr)
    # Convert string fraction values (e.g. "3/5") to numeric so comparisons work
    numeric_params = {}
    for k, v in params.items():
        if isinstance(v, str):
            try:
                numeric_params[k] = Fraction(v)
            except (ValueError, ZeroDivisionError):
                numeric_params[k] = v
        else:
            numeric_params[k] = v
    from .expr import _LIST_CONTEXT, _STRING_CONTEXT
    ctx = {"__builtins__": {}, "gcd": gcd, "denominator": denominator, "numerator": numerator}
    ctx.update(_LIST_CONTEXT)
    ctx.update(_STRING_CONTEXT)
    # List parameters must be in globals (ctx), not locals, so that list
    # comprehensions inside the rule expression can access them (Python 3
    # comprehensions have their own scope and cannot see eval() locals).
    scalar_params = {}
    for k, v in numeric_params.items():
        if isinstance(v, list):
            ctx[k] = v
        else:
            scalar_params[k] = v
    return bool(eval(expr, ctx, scalar_params))


def _resolve_answer_value(raw_val: str, preview_val: str, params: dict, answer_format: str = "") -> str:
    """Resolve a single answer value for a multi-input entry.

    Priority:
      1. Bare parameter name  → look up params directly
      2. Preview value (formatted, no LaTeX backslashes) → use it
      3. Raw value as fallback
    """
    _LATEX_FMTS = {"fraction", "improper", "mixed_number", "scientific_notation"}
    s = raw_val.strip()
    # 1. Bare param name shorthand
    if s in params:
        param_val = params[s]
        if answer_format in _LATEX_FMTS:
            # Store as plain fraction string
            if isinstance(param_val, str) and "/" in param_val:
                return param_val
            try:
                from fractions import Fraction as _Frac
                frac = _Frac(float(param_val)).limit_denominator(10000)
                return str(frac.numerator) if frac.denominator == 1 else f"{frac.numerator}/{frac.denominator}"
            except Exception:
                pass
        try:
            f = float(param_val)
            if answer_format and answer_format in FORMAT_REGISTRY:
                return FORMAT_REGISTRY[answer_format]().format(f)
            return str(int(f)) if f == int(f) else f"{f:g}"
        except (TypeError, ValueError):
            return str(param_val)
    # 2. Preview value (only when it doesn't contain LaTeX)
    if preview_val and "\\" not in preview_val.replace("\\$", ""):
        if answer_format and answer_format in FORMAT_REGISTRY and answer_format not in _LATEX_FMTS:
            try:
                return FORMAT_REGISTRY[answer_format]().format(float(preview_val))
            except (TypeError, ValueError):
                pass
        return preview_val
    # 3. Raw fallback
    if answer_format and answer_format in FORMAT_REGISTRY:
        if answer_format in _LATEX_FMTS:
            # LaTeX-producing formats must store a plain "n/d" string for frontend comparison
            try:
                from fractions import Fraction as _Frac
                frac = _Frac(float(raw_val)).limit_denominator(10000)
                return str(frac.numerator) if frac.denominator == 1 else f"{frac.numerator}/{frac.denominator}"
            except (TypeError, ValueError):
                pass
        else:
            try:
                return FORMAT_REGISTRY[answer_format]().format(float(raw_val))
            except (TypeError, ValueError):
                pass
    return raw_val


def render_template_preview(parsed):
    """
    Drop-in replacement for rendering.render_template_preview.
    Uses the Render class for parameter generation and expression substitution.
    Returns: {question, answers, solution, diagram_svg, diagram_code,
               substituted_yaml, params, errors}
    """
    yaml_text = _yaml.dump(parsed, allow_unicode=True, width=float('inf'), sort_keys=False)

    validation = parsed.get("validation", {})
    if isinstance(validation, list):
        # Shorthand: validation: [expr1, expr2, ...]
        rules = [{"check": str(item), "message": f"Validation failed: {item}"} for item in validation if item]
    else:
        rules = (validation.get("rules") or []) if isinstance(validation, dict) else []

    MAX_ATTEMPTS = 10
    last_error = None
    renderer = None
    collected_errors = []

    for attempt in range(MAX_ATTEMPTS):
        renderer = Render(yaml_text)
        renderer.render()

        params = {name: p.value for name, p in renderer.param_objects.items()}

        rule_failed = False
        for rule in rules:
            check = rule.get("check")
            message = rule.get("message", "Validation rule failed")
            try:
                if not _evaluate_rule(check, params):
                    rule_failed = True
                    last_error = message
                    break
            except Exception as e:
                rule_failed = True
                last_error = f"Rule error: {e}"
                collected_errors.append(last_error)
                break

        if not rule_failed:
            break
    else:
        raise ValueError(
            f"Parameter generation failed after {MAX_ATTEMPTS} attempts: {last_error}"
        )

    preview = renderer.preview_yaml or {}
    raw_sub = renderer.substituted_yaml or {}
    params = {name: p.value for name, p in renderer.param_objects.items()}

    # Extract question and solution from formatted preview
    question_block = preview.get("question", {})
    if isinstance(question_block, dict):
        question_text = question_block.get("text", "")
    else:
        question_text = str(question_block) if question_block else ""

    solution_block = preview.get("solution", {})
    if isinstance(solution_block, dict):
        solution_text = solution_block.get("text", "")
    else:
        solution_text = str(solution_block) if solution_block else ""

    post_answer_block = preview.get("post_answer", "")
    if isinstance(post_answer_block, dict):
        post_answer_text = post_answer_block.get("text", "")
    else:
        post_answer_text = str(post_answer_block) if post_answer_block else ""

    # Resolve {{ Knowledge("title") }} sentinels: strip from text, look up DB items
    _knowledge_refs = getattr(renderer, '_knowledge_refs', [])
    inline_knowledge_list = []
    if _knowledge_refs:
        import re as _re
        from ..models import Knowledge as _Knowledge
        from ..diagram.engine import render_diagram_from_code as _rdc

        def _resolve_sentinels(text, show):
            def _repl(m):
                idx = int(m.group(1))
                if idx < len(_knowledge_refs):
                    title = _knowledge_refs[idx]
                    try:
                        k = _Knowledge.objects.filter(title=title).first()
                    except Exception:
                        k = None
                    if k:
                        k_svg = ""
                        if k.diagram and k.diagram.strip() and k.diagram.strip().lower() != "none":
                            try:
                                k_svg = _rdc(k.diagram)
                            except Exception:
                                pass
                        inline_knowledge_list.append({
                            "title": k.title,
                            "text": k.text,
                            "text_2": k.text_2,
                            "diagram_svg": k_svg,
                            "show": show,
                        })
                return ""
            return _re.sub(r'\u27e6KN:(\d+)\u27e7', _repl, text).strip()

        question_text = _resolve_sentinels(question_text, "question")
        solution_text = _resolve_sentinels(solution_text, "solution")
        post_answer_text = _resolve_sentinels(post_answer_text, "post_answer")

    # Extract answers: use formatted preview for text-format answers (so | fraction, | decimal etc.
    # are applied), and raw_sub for old type-key answers (int, dec_1, fraction key) which are
    # formatted manually below.
    # answer: (singular dict)  → single input answer, no list required
    # answers: (plural)        → list of multiple-choice dicts, or bare string shorthand
    _raw_answers_src = raw_sub.get("answers") if "answers" in raw_sub else raw_sub.get("answer")
    if _raw_answers_src is None:
        # Unified format: answer/answers inside question: block
        _q_raw = raw_sub.get("question", {})
        if isinstance(_q_raw, dict):
            _raw_answers_src = _q_raw.get("answers") if "answers" in _q_raw else _q_raw.get("answer")
    if _raw_answers_src is None:
        _raw_answers_src = []
    raw_answers = _raw_answers_src

    # answer: {multiple_answers: [r1, r2]}            →  order-insensitive multi-input (legacy)
    # answer: {multiple_answers: [{x: x0}, {y: y0}]} →  labeled multi-input (legacy)
    # answers: [{answer: v1, label: l1}, ...]         →  unified multi-input format
    _multiple_answers = None
    _LATEX_ANSWER_FORMATS = {"fraction", "improper", "mixed_number", "scientific_notation"}

    # Unified multi-input: list of {answer: ..., label: ...} dicts
    if (isinstance(raw_answers, list) and raw_answers
            and all(isinstance(item, dict) and "answer" in item for item in raw_answers)):
        _q_raw2 = raw_sub.get("question", {})
        _q_fmt2 = _q_raw2.get("answer_format") if isinstance(_q_raw2, dict) else None
        _q_tol2 = _q_raw2.get("tolerance") if isinstance(_q_raw2, dict) else None
        _prev_q2 = preview.get("question", {})
        _prev_ans_list = (_prev_q2.get("answers") or _prev_q2.get("answer")) if isinstance(_prev_q2, dict) else None
        if not isinstance(_prev_ans_list, list):
            _prev_ans_list = []
        resolved = []
        for idx, item in enumerate(raw_answers):
            prev_item = _prev_ans_list[idx] if idx < len(_prev_ans_list) and isinstance(_prev_ans_list[idx], dict) else {}
            raw_val = str(item.get("answer", ""))
            prev_val = str(prev_item.get("answer", raw_val)) if prev_item else raw_val
            fmt2 = item.get("answer_format") or _q_fmt2
            resolved_val = _resolve_answer_value(raw_val, prev_val, params, fmt2 or "")
            entry = {"value": resolved_val}
            if item.get("label"):
                entry["label"] = str(item["label"])
            if fmt2:
                entry["answer_format"] = fmt2
            tol2 = item.get("tolerance") or _q_tol2
            if tol2 is not None:
                try:
                    entry["tolerance"] = float(tol2)
                except (TypeError, ValueError):
                    pass
            resolved.append(entry)
        _multiple_answers = resolved
        raw_answers = []

    elif isinstance(raw_answers, dict) and "multiple_answers" in raw_answers:
        raw_names = raw_answers.get("multiple_answers") or []
        if isinstance(raw_names, list):
            import math as _math
            _eval_ctx = {k: getattr(_math, k) for k in dir(_math) if not k.startswith('_')}
            resolved = []
            for item in raw_names:
                # Labeled format: {label: param_name}  e.g. {x: x0}
                if isinstance(item, dict) and len(item) == 1:
                    label_key, name = next(iter(item.items()))
                    label_str = str(label_key)
                    name_str = str(name).strip()
                else:
                    label_str = None
                    name_str = str(item).strip()

                # Resolve value: direct param lookup first, then expression eval
                val = params.get(name_str)
                if val is not None:
                    try:
                        f = float(val)
                        resolved_val = str(int(f)) if f == int(f) else str(f)
                    except (TypeError, ValueError):
                        resolved_val = str(val)
                else:
                    try:
                        result = eval(name_str, {"__builtins__": {}}, _eval_ctx)  # noqa: S307
                        f = float(result)
                        resolved_val = str(int(f)) if f == int(f) else str(f)
                    except Exception:
                        resolved_val = name_str

                entry = {"value": resolved_val}
                if label_str is not None:
                    entry["label"] = label_str
                resolved.append(entry)
            _multiple_answers = resolved
        raw_answers = []

    # answer: <dict>  →  wrap in list so the rest of the pipeline is unchanged
    elif isinstance(raw_answers, dict):
        raw_answers = [raw_answers]
    # Shorthand: answers: param_name  →  a single input answer with that parameter's value
    elif isinstance(raw_answers, str):
        param_name = raw_answers.strip()
        param_val = params.get(param_name)
        if param_val is not None:
            try:
                f = float(param_val)
                text = str(int(f)) if f == int(f) else str(f)
            except (TypeError, ValueError):
                text = str(param_val)
        else:
            text = param_name
        raw_answers = [{"input": text, "correct": True}]
    elif not isinstance(raw_answers, list):
        collected_errors.append(f"Answers must be a list or dict, got: {type(raw_answers).__name__}")
        raw_answers = []

    _preview_answers_src = preview.get("answers") if "answers" in preview else preview.get("answer")
    if _preview_answers_src is None:
        _q_prev = preview.get("question", {})
        if isinstance(_q_prev, dict):
            _preview_answers_src = _q_prev.get("answers") if "answers" in _q_prev else _q_prev.get("answer")
    if _preview_answers_src is None:
        _preview_answers_src = []
    preview_answers = _preview_answers_src
    if isinstance(preview_answers, dict):
        preview_answers = [preview_answers]
    elif isinstance(preview_answers, str):
        # If raw and preview differ a pipe formatter was applied (e.g. | factor) — use the
        # formatted preview string.  If they're the same it's a plain param name like
        # `answers: ans` and raw_answers has already resolved the numeric value.
        if preview_answers != _raw_answers_src:
            preview_answers = [{"input": preview_answers, "correct": True}]
        else:
            preview_answers = raw_answers
    elif not isinstance(preview_answers, list):
        preview_answers = []

    # question-level defaults for all input answers (new unified flat format)
    _question_level_answer_format = None
    _question_level_tolerance = None
    _question_level_format_instruction = None
    _q_block = raw_sub.get("question")
    if isinstance(_q_block, dict):
        _question_level_answer_format = _q_block.get("answer_format")
        _question_level_tolerance = _q_block.get("tolerance")
        _question_level_format_instruction = _q_block.get("format_instruction")

    answers = []
    for i, ans in enumerate(raw_answers):
        if not isinstance(ans, dict):
            answers.append(ans)
            continue

        # Graph answer: answer contains a diagram spec dict or code string.
        if "diagram" in ans:
            diagram_spec = ans["diagram"]
            if isinstance(diagram_spec, dict):
                diagram_type = diagram_spec.get("type", "Cartesian")
                parts = []
                for k, v in diagram_spec.items():
                    if k == "type":
                        continue
                    parts.append(f'eq: "{v}"' if k == "eq" else f"{k}: {v}")
                code = f'{diagram_type}({", ".join(parts)})'
            else:
                code = str(diagram_spec)
            from ..diagram.engine import render_diagram_from_code
            svg = render_diagram_from_code(code, width=200)
            raw_correct = ans.get("correct", ans.get(True, False))
            if isinstance(raw_correct, str):
                try:
                    raw_correct = _evaluate_rule(raw_correct, params)
                except Exception:
                    raw_correct = False
            answers.append({"diagram_svg": svg, "correct": raw_correct})
            continue

        # New format: answer has a text field.
        # If a `format` key is present, inject it as a pipe into each {{ }} expression
        # and re-process through the renderer so the correct formatter is applied.
        # Otherwise fall back to the already-walked preview value.
        if "text" in ans:
            format_type = ans.get("format")
            raw_text = str(ans.get("text", ""))
            if format_type:
                piped = _inject_format_pipe(raw_text, format_type)
                if "{{" in piped:
                    # Expressions still present — process through renderer with pipe injected
                    formatted_text = renderer._process_string(piped, "formatted")
                else:
                    # Already substituted by walk() — apply formatter directly to the value
                    from fractions import Fraction
                    formatter_cls = FORMAT_REGISTRY.get(format_type)
                    if formatter_cls:
                        try:
                            val = Fraction(raw_text) if "/" in raw_text else float(raw_text)
                            formatted_text = formatter_cls().format(val)
                        except Exception:
                            formatted_text = raw_text
                    else:
                        formatted_text = raw_text
            else:
                preview_ans = preview_answers[i] if i < len(preview_answers) else {}
                formatted_text = str(preview_ans.get("text", raw_text)) if isinstance(preview_ans, dict) else raw_text
            raw_correct = ans.get("correct", ans.get(True, False))
            if isinstance(raw_correct, str):
                try:
                    correct = _evaluate_rule(raw_correct, params)
                except Exception:
                    correct = False
            else:
                correct = raw_correct
                if "logic" in ans:
                    try:
                        correct = correct and _evaluate_rule(ans["logic"], params)
                    except Exception:
                        correct = False
            answers.append({"text": formatted_text, "correct": correct})
            continue

        # Old format: answer value is stored under a type key; Render has already
        # substituted {{ }} expressions so the value is a number string like "12" or "3/7".
        raw_correct = ans.get("correct", ans.get(True, False))
        if isinstance(raw_correct, str):
            try:
                is_true = _evaluate_rule(raw_correct, params)
            except Exception:
                is_true = False
            answers.append({"text": ans.get("text", ""), "correct": is_true})
            continue
        if "logic" in ans:
            try:
                is_true = _evaluate_rule(ans["logic"], params)
            except Exception:
                is_true = False
            answers.append({"text": ans.get("text", ""), "correct": raw_correct and is_true})
            continue

        if "input" in ans:
            raw_input = ans["input"]
            # Support { expr: value } sub-mapping (from YAML like `input:\n  expr: "{{ a }}"`)
            if isinstance(raw_input, dict) and "expr" in raw_input:
                raw_input = raw_input["expr"]
            # If input value is a parameter name, resolve it to the actual value
            # Formats whose formatter produces LaTeX (e.g. \frac{7}{20}) rather than a
            # plain string.  These must NOT be applied to the stored answer text because
            # the frontend's answersMatch() cannot parse LaTeX — it only handles plain
            # "n/d" fraction strings.  answer_format is still forwarded to the frontend
            # for input-validation purposes; only the stored comparison text is affected.
            if isinstance(raw_input, str) and raw_input.strip() in params:
                param_name = raw_input.strip()
                param_val = params.get(param_name)
                answer_format = ans.get("answer_format") or _question_level_answer_format
                if answer_format and answer_format in FORMAT_REGISTRY and answer_format not in _LATEX_ANSWER_FORMATS:
                    try:
                        text = FORMAT_REGISTRY[answer_format]().format(param_val)
                    except Exception:
                        text = str(param_val)
                elif answer_format in _LATEX_ANSWER_FORMATS:
                    # Store as plain "n/d" fraction string so the frontend can compare
                    if isinstance(param_val, str) and "/" in param_val:
                        text = param_val
                    else:
                        try:
                            from fractions import Fraction as _Frac
                            frac = _Frac(float(param_val)).limit_denominator(10000)
                            text = str(frac.numerator) if frac.denominator == 1 else f"{frac.numerator}/{frac.denominator}"
                        except Exception:
                            try:
                                f = float(param_val)
                                text = str(int(f)) if f == int(f) else str(f)
                            except (TypeError, ValueError):
                                text = str(param_val)
                else:
                    try:
                        f = float(param_val)
                        text = str(int(f)) if f == int(f) else str(f)
                    except (TypeError, ValueError):
                        text = str(param_val)
            else:
                # Prefer the formatted (preview) value when it contains no LaTeX backslashes.
                # This ensures {{ a | proper_fraction }} compares as "2 1/3" not "7/3".
                # Dollar signs are escaped as \$ in LaTeX but are typeable as $ — normalise
                # them before the backslash check so "$8x" is accepted while "\frac{3}{4}"
                # is still rejected.
                preview_input = None
                if i < len(preview_answers) and isinstance(preview_answers[i], dict):
                    pi = preview_answers[i].get("input")
                    if pi is not None and isinstance(pi, str):
                        pi_normalised = pi.replace("\\$", "$")
                        if "\\" not in pi_normalised:
                            preview_input = pi_normalised
                text = preview_input if preview_input is not None else str(raw_input)
                # If the preview differs from the raw value only by a leading $ (dollar
                # currency formatting), use the raw value — students should not need to
                # type a dollar sign in algebraic or numeric answers.
                if text.startswith("$") and text[1:] == str(raw_input):
                    text = str(raw_input)
                # Apply answer_format to the resolved numeric value so that e.g.
                # `expr: {{ ratio }}` with `answer_format: ratio` stores "1:2" not "0.5".
                # Fall back to the question-level format (e.g. decimal_1 on the question block).
                # Skip LaTeX-producing formats — store plain fraction strings instead.
                answer_format = ans.get("answer_format") or _question_level_answer_format
                if answer_format and answer_format in FORMAT_REGISTRY and answer_format not in _LATEX_ANSWER_FORMATS:
                    try:
                        text = FORMAT_REGISTRY[answer_format]().format(float(text))
                    except Exception:
                        pass
                elif answer_format in _LATEX_ANSWER_FORMATS:
                    try:
                        from fractions import Fraction as _Frac
                        frac = _Frac(float(text)).limit_denominator(10000)
                        text = str(frac.numerator) if frac.denominator == 1 else f"{frac.numerator}/{frac.denominator}"
                    except Exception:
                        pass
            answer_obj = {"text": text, "correct": ans.get("correct", True), "input_type": "text"}
            fmt = ans.get("answer_format") or ans.get("input_format") or _question_level_answer_format
            explicit_instruction = ans.get("format_instruction") or _question_level_format_instruction
            instruction = explicit_instruction or (fmt and _DEFAULT_FORMAT_INSTRUCTIONS.get(fmt))
            if instruction:
                answer_obj["format_instruction"] = str(instruction)
            if fmt:
                answer_obj["answer_format"] = str(fmt)
            tol = ans.get("tolerance")
            if tol is None:
                tol = _question_level_tolerance
            if tol is not None:
                try:
                    answer_obj["tolerance"] = float(tol)
                except (TypeError, ValueError):
                    pass
            answers.append(answer_obj)
            continue

        if "int" in ans:
            try:
                text = str(evaluate_int_expression(str(ans["int"]), {}))
            except Exception:
                text = str(ans["int"])
            answers.append({"text": text, "correct": ans.get("correct", False)})
            continue

        if "dec_1" in ans:
            try:
                text = str(evaluate_dec_expression(str(ans["dec_1"]), {}, 1))
            except Exception:
                text = str(ans["dec_1"])
            answers.append({"text": text, "correct": ans.get("correct", False)})
            continue

        if "dec_2" in ans:
            try:
                text = str(evaluate_dec_expression(str(ans["dec_2"]), {}, 2))
            except Exception:
                text = str(ans["dec_2"])
            answers.append({"text": text, "correct": ans.get("correct", False)})
            continue

        if "fraction" in ans:
            try:
                val = evaluate_fraction_expression(str(ans["fraction"]), {})
                text = FractionFormat().format(val)
            except Exception:
                text = str(ans["fraction"])
            answers.append({"text": text, "correct": ans.get("correct", False)})
            continue

        answers.append(ans)

    seen = set()
    deduped_answers = []
    for ans in answers:
        if isinstance(ans, dict):
            # Diagram answers have no text — use a unique sentinel per index so
            # they are never collapsed by the deduplication logic.
            key = ans.get("text") if "text" in ans else id(ans)
        else:
            key = str(ans)
        if key not in seen:
            seen.add(key)
            deduped_answers.append(ans)

    # Diagram
    diagram_code = preview.get("diagram", "")
    svg = ""
    if isinstance(diagram_code, str) and diagram_code.strip() and diagram_code.strip().lower() != "none":
        try:
            from ..diagram.engine import render_diagram_from_code
            svg = render_diagram_from_code(diagram_code)
        except Exception as e:
            collected_errors.append(f"Diagram error: {e}")
            diagram_code = ""
    else:
        diagram_code = ""

    # Multi-step AlgebraTable: pre-render one SVG per blank with its highlight active
    multi_step = None
    if diagram_code and diagram_code.strip().startswith("AlgebraTable") and "blanks:" in diagram_code:
        try:
            import re as _mre
            from ..diagram import algebra_table as _at
            from ..diagram.engine import render_diagram_from_code as _rdc
            d = _at.parse(diagram_code)
            if d and d.blanks:
                # Get raw solution template (before param substitution) so we can
                # re-render it with blank_x = each step's x value.
                _raw = load_template_yaml(yaml_text)
                _sol_raw = _raw.get("solution", "")
                _sol_tmpl = (
                    _sol_raw.get("text", "") if isinstance(_sol_raw, dict)
                    else (str(_sol_raw) if _sol_raw else "")
                )

                steps = []
                for i, bx in enumerate(d.blanks):
                    # Only keep blanks from this step onward; earlier cells show their value
                    remaining = ",".join(str(b) for b in d.blanks[i:])
                    step_code = _mre.sub(r'\bblanks:\s*"[^"]*"', f'blanks: "{remaining}"', diagram_code)
                    if _mre.search(r'\bhighlight:\s*-?\d+', step_code):
                        step_code = _mre.sub(r'\bhighlight:\s*-?\d+', f'highlight: {bx}', step_code)
                    else:
                        step_code = step_code.rstrip(')') + f', highlight: {bx})'
                    step_svg = _rdc(step_code)

                    answer_val = _at._eval_expr(d.expr, bx)
                    if answer_val is None:
                        answer_str = ""
                    elif isinstance(answer_val, float) and answer_val == int(answer_val):
                        answer_str = str(int(answer_val))
                    else:
                        answer_str = str(answer_val)

                    # Render solution with blank_x substituted as a literal for this step.
                    # We inject the numeric value directly into {{ }} expressions so we
                    # don't need to mutate param objects.
                    step_solution = ""
                    if _sol_tmpl:
                        try:
                            def _inject_blank_x(tmpl, val):
                                return _mre.sub(
                                    r'\{\{(.*?)\}\}',
                                    lambda m: '{{' + _mre.sub(r'\bblank_x\b', str(val), m.group(1)) + '}}',
                                    tmpl,
                                )
                            step_solution = renderer._process_string(_inject_blank_x(_sol_tmpl, bx), "formatted")
                        except Exception as _e:
                            collected_errors.append(f"Multi-step solution error (blank_x={bx}): {_e}")
                            step_solution = ""

                    steps.append({"svg": step_svg, "answer": answer_str, "solution": step_solution, "tolerance": 0.001})
                multi_step = {"steps": steps}
        except Exception:
            pass

    # Multi-part questions via question.parts (any diagram type)
    if not multi_step:
        preview_parts = []
        if isinstance(question_block, dict):
            preview_parts = question_block.get("parts", [])
            if not isinstance(preview_parts, list):
                preview_parts = []
        # Use raw_sub for answers (unformatted, for exact comparison)
        raw_q_block = raw_sub.get("question", {})
        raw_parts = raw_q_block.get("parts", []) if isinstance(raw_q_block, dict) else []

        if preview_parts:
            part_steps = []
            for i, part in enumerate(preview_parts):
                if not isinstance(part, dict):
                    continue
                raw_part = raw_parts[i] if i < len(raw_parts) and isinstance(raw_parts[i], dict) else {}

                # Compute raw answer: prefer value from raw substitution walk.
                # Skip 'answers' if it's a list (that means it's a choices block, not a scalar answer).
                raw_ans = ""
                for _src in (raw_part, part):
                    _v = _src.get("answer")
                    if _v is not None:
                        raw_ans = str(_v)
                        break
                    _v = _src.get("answers")
                    if _v is not None and not isinstance(_v, list):
                        raw_ans = str(_v)
                        break
                # Bare param name shorthand: if the answer is just a param name, resolve it
                if raw_ans.strip() in params:
                    param_val = params.get(raw_ans.strip())
                    try:
                        _f = float(param_val)
                        raw_ans = str(int(_f)) if _f == int(_f) else f"{_f:g}"
                    except (TypeError, ValueError):
                        raw_ans = str(param_val)
                elif "{{" in raw_ans:
                    # Substitution didn't fully expand — re-process directly
                    try:
                        raw_ans = renderer._process_string(raw_ans, "raw")
                    except Exception:
                        pass
                # Normalise: convert "14.0" or sympy float strings → clean int/decimal
                try:
                    _f = float(raw_ans)
                    raw_ans = str(int(_f)) if _f == int(_f) else f"{_f:g}"
                except (ValueError, TypeError):
                    pass

                # For equation-format answers sympy returns "A**2"; convert to "A^2"
                # so it matches what the PowerInput widget produces.
                part_answer_format = str(part.get("answer_format", "") or "")
                if part_answer_format == "equation":
                    raw_ans = raw_ans.replace("**", "^")
                if part_answer_format == "ratio" and ":" not in raw_ans:
                    formatted_ans = str(part.get("answer", ""))
                    if ":" in formatted_ans:
                        raw_ans = formatted_ans
                # Apply decimal/numeric format to the stored answer value so that
                # e.g. answer_format: decimal_2 stores "9.55" not "9.55044".
                # LaTeX-producing formats (fraction, mixed_number, etc.) must store
                # a plain "n/d" string so the frontend's text comparison works.
                if part_answer_format and part_answer_format in FORMAT_REGISTRY and part_answer_format not in _LATEX_ANSWER_FORMATS:
                    try:
                        raw_ans = FORMAT_REGISTRY[part_answer_format]().format(float(raw_ans))
                    except Exception:
                        pass
                elif part_answer_format in _LATEX_ANSWER_FORMATS:
                    try:
                        from fractions import Fraction as _Frac
                        _frac = _Frac(float(raw_ans)).limit_denominator(10000)
                        raw_ans = str(_frac.numerator) if _frac.denominator == 1 else f"{_frac.numerator}/{_frac.denominator}"
                    except Exception:
                        pass

                # Per-part diagram overrides the top-level diagram for this step.
                part_diagram_code = part.get("diagram", "")
                if isinstance(part_diagram_code, str) and part_diagram_code.strip() and part_diagram_code.strip().lower() != "none":
                    try:
                        from ..diagram.engine import render_diagram_from_code as _rdc_part
                        part_svg = _rdc_part(part_diagram_code)
                    except Exception as _e:
                        collected_errors.append(f"Part {i} diagram error: {_e}")
                        part_svg = svg
                else:
                    part_svg = svg

                step = {
                    "svg": part_svg,
                    "question": str(part.get("text", "")),
                    "answer": raw_ans,
                    "solution": str(part.get("solution", "")),
                }
                if part_answer_format:
                    step["answer_format"] = part_answer_format
                _part_fi = part.get("format_instruction") or _DEFAULT_FORMAT_INSTRUCTIONS.get(part_answer_format)
                if _part_fi:
                    step["format_instruction"] = str(_part_fi)
                # choices: or answers: (list of {text, correct} dicts) both work
                # answers: [{answer: ..., label: ...}] → unified multi-input for this step
                _choices_src = part.get("choices")
                _pans = part.get("answers")
                if not _choices_src and isinstance(_pans, list) and _pans:
                    if isinstance(_pans[0], dict) and "answer" in _pans[0]:
                        # Multi-input answers for this step
                        raw_part_ans_list = raw_part.get("answers", [])
                        if not isinstance(raw_part_ans_list, list):
                            raw_part_ans_list = []
                        step_multi = []
                        for j, pans_item in enumerate(_pans):
                            if not isinstance(pans_item, dict):
                                continue
                            raw_item = raw_part_ans_list[j] if j < len(raw_part_ans_list) and isinstance(raw_part_ans_list[j], dict) else {}
                            raw_v = str(raw_item.get("answer", pans_item.get("answer", "")))
                            prev_v = str(pans_item.get("answer", raw_v))
                            fmt_item = pans_item.get("answer_format") or part_answer_format or ""
                            val = _resolve_answer_value(raw_v, prev_v, params, fmt_item)
                            entry = {"value": val}
                            if pans_item.get("label"):
                                entry["label"] = str(pans_item["label"])
                            if fmt_item:
                                entry["answer_format"] = fmt_item
                            tol_item = pans_item.get("tolerance") or part.get("tolerance")
                            if tol_item is not None:
                                try:
                                    entry["tolerance"] = float(tol_item)
                                except (TypeError, ValueError):
                                    pass
                            step_multi.append(entry)
                        if step_multi:
                            step["multiple_answers"] = step_multi
                    elif isinstance(_pans[0], dict) and "text" in _pans[0]:
                        _choices_src = _pans
                if _choices_src and isinstance(_choices_src, list):
                    def _parse_choice_correct(val):
                        if isinstance(val, bool):
                            return val
                        if isinstance(val, str):
                            try:
                                return bool(_evaluate_rule(val, params))
                            except Exception:
                                return bool(val)
                        return bool(val)
                    choices = [
                        {"text": str(c.get("text", "")), "correct": _parse_choice_correct(c.get("correct", False))}
                        for c in _choices_src if isinstance(c, dict)
                    ]
                    step["choices"] = choices
                    correct_choices = [c for c in choices if c["correct"]]
                    if correct_choices:
                        step["answer"] = correct_choices[0]["text"]
                tol = part.get("tolerance")
                if tol is not None:
                    try:
                        step["tolerance"] = float(tol)
                    except (TypeError, ValueError):
                        pass
                part_steps.append(step)
            if part_steps:
                multi_step = {"steps": part_steps}

    # Build debug substituted_yaml string — format values for readability
    def _display_param(p):
        fmt_type = getattr(p.__class__, "default_format_type", None)
        if fmt_type and fmt_type in FORMAT_REGISTRY:
            try:
                return FORMAT_REGISTRY[fmt_type]().format(p.value)
            except Exception:
                pass
        return p.value

    display_params = {name: _display_param(p) for name, p in renderer.param_objects.items()}

    def _display_answers(answers_list):
        result = []
        for ans in answers_list:
            if not isinstance(ans, dict):
                result.append(ans)
                continue
            display_ans = dict(ans)
            # PyYAML parses `true:` as the Python bool True, not the string "true"
            for key in (True, "true", "correct"):
                if key in display_ans and isinstance(display_ans[key], str):
                    try:
                        display_ans[key] = bool(_evaluate_rule(display_ans[key], params))
                    except Exception:
                        pass
            result.append(display_ans)
        return result

    debug = {
        "parameters": display_params,
        "question": question_text,
        "solution": solution_text,
        "answers": _display_answers(raw_answers),
        "diagram": preview.get("diagram", {}),
    }
    if _multiple_answers is not None:
        debug["multiple_answers"] = _multiple_answers
    if multi_step:
        def _step_debug(s):
            if s.get("multiple_answers"):
                answers = [
                    f'{a["label"]} = {a["value"]}' if a.get("label") else str(a["value"])
                    for a in s["multiple_answers"]
                ]
                return {"question": s.get("question", ""), "answers": answers}
            return {"question": s.get("question", ""), "answer": s.get("answer", "")}
        debug["multi_step_answers"] = [_step_debug(s) for s in multi_step.get("steps", [])]
    substituted_yaml = _yaml.dump(debug, sort_keys=False, allow_unicode=True)

    # Inline knowledge block (knowledge: key in YAML) — appended after any {{ Knowledge() }} refs
    knowledge_block = preview.get("knowledge")
    if knowledge_block:
        if isinstance(knowledge_block, str):
            inline_knowledge_list.append({"title": "", "text": knowledge_block, "text_2": "", "diagram_svg": "", "show": "solution"})
        elif isinstance(knowledge_block, dict):
            k_svg = ""
            k_diagram = knowledge_block.get("diagram", "")
            if k_diagram and str(k_diagram).strip() and str(k_diagram).strip().lower() != "none":
                try:
                    from ..diagram.engine import render_diagram_from_code
                    k_svg = render_diagram_from_code(str(k_diagram))
                except Exception as e:
                    collected_errors.append(f"Knowledge diagram error: {e}")
            inline_knowledge_list.append({
                "title": str(knowledge_block.get("title", "")),
                "text": str(knowledge_block.get("text", "")),
                "text_2": str(knowledge_block.get("text_2", "")),
                "diagram_svg": k_svg,
                "show": str(knowledge_block.get("show", "solution")),
            })

    return {
        "question": question_text,
        "answers": deduped_answers,
        "solution": solution_text,
        "post_answer": post_answer_text,
        "diagram_svg": svg,
        "diagram_code": diagram_code,
        "substituted_yaml": substituted_yaml,
        "params": params,
        "errors": collected_errors,
        "multi_step": multi_step,
        "inline_knowledge": inline_knowledge_list,
        "multiple_answers": _multiple_answers,
    }