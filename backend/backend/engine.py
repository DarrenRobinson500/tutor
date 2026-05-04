import time
import random
import yaml
from svg import *


class PreviewContext:
    def __init__(self, template_raw, seed=None):
        self.template_raw = template_raw
        self.template = None

        self.seed = seed or random.randint(1, 10**9)
        self.rng = random.Random(self.seed)

        self.parameters = {}
        self.question_latex = ""
        self.answer_latex = ""
        self.solution_latex = ""
        self.diagram_spec = None

        self.question_html = ""
        self.answer_html = ""
        self.solution_html = ""
        self.diagram_svg = ""

        self.errors = []
        self.warnings = []
        self.logs = []
        self.metrics = {}

    def log(self, msg):
        self.logs.append(msg)

    def error(self, type_, message, **kwargs):
        self.errors.append({"type": type_, "message": message, **kwargs})

    def warn(self, type_, message, **kwargs):
        self.warnings.append({"type": type_, "message": message, **kwargs})

class PreviewEngine:

    MAX_PARAM_ATTEMPTS = 20

    def run(self, template_raw, seed=None):
        ctx = PreviewContext(template_raw, seed)
        start = time.time()

        try:
            self.parse_template(ctx)
            self.initial_sanity_checks(ctx)
            self.generate_parameters(ctx)
            self.evaluate_constraints(ctx)
            self.evaluate_expressions(ctx)
            self.render_latex(ctx)
            self.render_diagram(ctx)

        except Exception as e:
            ctx.error("internal_error", str(e))

        ctx.metrics["generation_time_ms"] = int((time.time() - start) * 1000)

        return self.build_response(ctx)

    def parse_template(self, ctx):
        ctx.log("Parsing template...")
        try:
            ctx.template = yaml.safe_load(ctx.template_raw)
        except Exception as e:
            ctx.error("yaml_syntax", f"YAML parse error: {e}")
            raise

        if not isinstance(ctx.template, dict):
            ctx.error("invalid_template", "Template root must be a mapping")
            raise ValueError("Invalid template")

    def initial_sanity_checks(self, ctx):
        ctx.log("Running initial sanity checks...")

        required = ["question", "answer"]
        for field in required:
            if field not in ctx.template:
                ctx.error("missing_field", f"Missing required field '{field}'")

    def generate_parameters(self, ctx):
        ctx.log("Generating parameters...")

        params = ctx.template.get("parameters", {})
        attempts = 0

        while attempts < self.MAX_PARAM_ATTEMPTS:
            attempts += 1
            ctx.parameters = {}

            for name, spec in params.items():
                ctx.parameters[name] = self.generate_single_parameter(ctx, name, spec)

            # Constraints checked later
            return

        ctx.error("parameter_generation_error", "Could not generate valid parameters")
        raise ValueError("Parameter generation failed")

    def generate_single_parameter(self, ctx, name, spec):
        t = spec.get("type", "int")

        if t == "int":
            return ctx.rng.randint(spec["min"], spec["max"])

        if t == "float":
            return ctx.rng.uniform(spec["min"], spec["max"])

        if t == "choice":
            return ctx.rng.choice(spec["values"])

        ctx.warn("unknown_parameter_type", f"Unknown type '{t}' for parameter '{name}'")
        return None

    def evaluate_constraints(self, ctx):
        ctx.log("Evaluating constraints...")

        constraints = ctx.template.get("constraints", [])

        for c in constraints:
            expr = c.get("expr")
            try:
                if not eval(expr, {}, ctx.parameters):
                    ctx.error("constraint_failed", f"Constraint failed: {expr}")
                    raise ValueError("Constraint failed")
            except Exception as e:
                ctx.error("constraint_error", f"Error evaluating constraint '{expr}': {e}")
                raise

    def evaluate_expressions(self, ctx):
        ctx.log("Evaluating expressions...")

        def replace_expr(text):
            import re
            pattern = r"\{\{(.*?)\}\}"

            def repl(match):
                expr = match.group(1).strip()
                try:
                    return str(eval(expr, {}, ctx.parameters))
                except Exception as e:
                    ctx.error("expression_error", f"Error in expression '{expr}': {e}")
                    raise

            return re.sub(pattern, repl, text)

        q = ctx.template["question"]["text"]
        a = ctx.template["answer"]["text"]
        s = ctx.template.get("solution", {}).get("text", "")

        ctx.question_latex = replace_expr(q)
        ctx.answer_latex = replace_expr(a)
        ctx.solution_latex = replace_expr(s)

    def render_latex(self, ctx):
        ctx.log("Rendering LaTeX...")

        # Placeholder — integrate KaTeX/MathJax later
        ctx.question_html = f"<p>{ctx.question_latex}</p>"
        ctx.answer_html = f"<p>{ctx.answer_latex}</p>"
        ctx.solution_html = f"<p>{ctx.solution_latex}</p>"

    def render_diagram(self, ctx):
        ctx.log("Rendering diagram...")

        diagram = ctx.template.get("diagram")
        if not diagram:
            return

        # Placeholder — real SVG engine later
        ctx.diagram_svg = "<svg><!-- diagram placeholder --></svg>"

        renderer = SVGRenderingEngine()
        result = renderer.render(ctx.diagram_spec)
        ctx.diagram_svg = result["svg"]
        ctx.warnings.extend(result["warnings"])


    def build_response(self, ctx):
        if ctx.errors:
            return {
                "success": False,
                "errors": ctx.errors,
                "warnings": ctx.warnings,
                "logs": ctx.logs,
                "seed": ctx.seed,
                "metrics": ctx.metrics
            }

        return {
            "success": True,
            "question": {
                "html": ctx.question_html,
                "latex": ctx.question_latex
            },
            "answer": {
                "html": ctx.answer_html,
                "latex": ctx.answer_latex
            },
            "solution": {
                "html": ctx.solution_html,
                "latex": ctx.solution_latex
            },
            "diagram": {
                "svg": ctx.diagram_svg,
                "raw": ctx.diagram_svg
            },
            "parameters": ctx.parameters,
            "seed": ctx.seed,
            "warnings": ctx.warnings,
            "errors": ctx.errors,
            "logs": ctx.logs,
            "metrics": ctx.metrics
        }


class ValidationContext:
    def __init__(self, template_raw):
        self.template_raw = template_raw
        self.template = None

        self.errors = []
        self.warnings = []
        self.logs = []
        self.metrics = {}

    def log(self, msg):
        self.logs.append(msg)

    def error(self, type_, message, **kwargs):
        self.errors.append({"type": type_, "message": message, **kwargs})

    def warn(self, type_, message, **kwargs):
        self.warnings.append({"type": type_, "message": message, **kwargs})

class ValidationEngine:
    def run(self, template_raw):
        ctx = ValidationContext(template_raw)
        start = time.time()

        try:
            self.parse_template(ctx)
            self.schema_validation(ctx)
            self.parameter_validation(ctx)
            self.constraint_validation(ctx)
            self.expression_validation(ctx)
            self.latex_validation(ctx)
            self.diagram_validation(ctx)
            self.semantic_validation(ctx)

        except Exception as e:
            ctx.error("internal_error", str(e))

        ctx.metrics["validation_time_ms"] = int((time.time() - start) * 1000)
        return self.build_response(ctx)

    def parse_template(self, ctx):
        ctx.log("Parsing template...")

        try:
            ctx.template = yaml.safe_load(ctx.template_raw)
        except Exception as e:
            ctx.error("yaml_syntax", f"YAML parse error: {e}")
            raise

        if not isinstance(ctx.template, dict):
            ctx.error("invalid_template", "Template root must be a mapping")
            raise ValueError("Invalid template")

    def schema_validation(self, ctx):
        ctx.log("Validating schema...")

        required = ["question", "answer"]
        for field in required:
            if field not in ctx.template:
                ctx.error("schema_missing_field", f"Missing required field '{field}'")

        # Optional: enforce types
        if "parameters" in ctx.template and not isinstance(ctx.template["parameters"], dict):
            ctx.error("schema_type_error", "Parameters must be a mapping")

    def parameter_validation(self, ctx):
        ctx.log("Validating parameters...")

        params = ctx.template.get("parameters", {})

        for name, spec in params.items():
            if "type" not in spec:
                ctx.error("parameter_missing_type", f"Parameter '{name}' missing type")

            t = spec.get("type")

            if t == "int":
                if "min" not in spec or "max" not in spec:
                    ctx.error("parameter_range_error", f"Parameter '{name}' missing min/max")

            elif t == "choice":
                if "values" not in spec or not isinstance(spec["values"], list):
                    ctx.error("parameter_choice_error", f"Parameter '{name}' must define 'values'")

            else:
                ctx.warn("unknown_parameter_type", f"Unknown parameter type '{t}' for '{name}'")

    def constraint_validation(self, ctx):
        ctx.log("Validating constraints...")

        params = ctx.template.get("parameters", {})
        constraints = ctx.template.get("constraints", [])

        for c in constraints:
            expr = c.get("expr")
            if not expr:
                ctx.error("constraint_missing_expr", "Constraint missing 'expr'")
                continue

            # Check references
            for name in params.keys():
                pass  # optional: static analysis

            try:
                compile(expr, "<constraint>", "eval")
            except Exception as e:
                ctx.error("constraint_syntax_error", f"Invalid constraint '{expr}': {e}")

    def expression_validation(self, ctx):
        ctx.log("Validating expressions...")

        import re
        pattern = r"\{\{(.*?)\}\}"

        def check(text, field_name):
            for match in re.finditer(pattern, text):
                expr = match.group(1).strip()
                try:
                    compile(expr, "<expr>", "eval")
                except Exception as e:
                    ctx.error("expression_syntax_error",
                              f"Invalid expression in {field_name}: '{expr}' ({e})")

        q = ctx.template.get("question", {}).get("text", "")
        a = ctx.template.get("answer", {}).get("text", "")
        s = ctx.template.get("solution", {}).get("text", "")

        check(q, "question")
        check(a, "answer")
        check(s, "solution")

    def latex_validation(self, ctx):
        ctx.log("Validating LaTeX...")

        # Simple check: unbalanced braces
        def check_balance(text, field):
            if text.count("{") != text.count("}"):
                ctx.error("latex_brace_mismatch", f"Unbalanced braces in {field}")

        q = ctx.template.get("question", {}).get("text", "")
        a = ctx.template.get("answer", {}).get("text", "")
        s = ctx.template.get("solution", {}).get("text", "")

        check_balance(q, "question")
        check_balance(a, "answer")
        check_balance(s, "solution")

    def diagram_validation(self, ctx):
        ctx.log("Validating diagram...")

        diagram = ctx.template.get("diagram")
        if not diagram:
            return

        if "elements" not in diagram:
            ctx.error("diagram_missing_elements", "Diagram missing 'elements' list")
            return

        if not isinstance(diagram["elements"], list):
            ctx.error("diagram_type_error", "'elements' must be a list")

    def semantic_validation(self, ctx):
        ctx.log("Running semantic checks...")

        params = set(ctx.template.get("parameters", {}).keys())
        used = set()

        import re
        pattern = r"\{\{(.*?)\}\}"

        def scan(text):
            for match in re.finditer(pattern, text):
                expr = match.group(1).strip()
                for p in params:
                    if p in expr:
                        used.add(p)

        scan(ctx.template.get("question", {}).get("text", ""))
        scan(ctx.template.get("answer", {}).get("text", ""))
        scan(ctx.template.get("solution", {}).get("text", ""))

        unused = params - used
        for p in unused:
            ctx.warn("unused_parameter", f"Parameter '{p}' is never used")

    def build_response(self, ctx):
        return {
            "valid": len(ctx.errors) == 0,
            "summary": {
                "errors": len(ctx.errors),
                "warnings": len(ctx.warnings)
            },
            "errors": ctx.errors,
            "warnings": ctx.warnings,
            "logs": ctx.logs,
            "metrics": ctx.metrics
        }