import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from backend.render.render import render_template_preview
from backend.rendering import load_template_yaml

def check(label, result, key='answers'):
    print(f"  {label}: {result.get(key, result.get('question', '?'))}")

# ── Test 1: basic arithmetic ─────────────────────────────────────────────────
t = load_template_yaml("""
parameters:
  a:
    min: 2
    max: 10
    step: 1
  b:
    min: 2
    max: 10
    step: 1
question:
  text: 'What is {{a}} + {{b}}?'
  answer: '{{ a + b }}'
  solution: '{{a}} + {{b}} = {{a + b}}'
""")
check("arithmetic", render_template_preview(t))

# ── Test 2: ternary ───────────────────────────────────────────────────────────
t = load_template_yaml("""
parameters:
  is_multiply:
    type: bool
  a:
    min: 2
    max: 6
    step: 1
  b:
    min: 2
    max: 6
    step: 1
  answer:
    expr: 'a * b if is_multiply else a + b'
question:
  text: 'Result?'
  answer: '{{ answer }}'
  solution: '{{ "multiply" if is_multiply else "add" }}: {{ answer }}'
""")
r = render_template_preview(t)
check("ternary answer", r)
check("ternary solution", r, 'solution')

# ── Test 3: simplify_expr (multiply → symbolic) ───────────────────────────────
t = load_template_yaml("""
parameters:
  a1: { min: 2, max: 6, step: 1 }
  d1: { min: 2, max: 9, step: 1 }
  a2: { min: 2, max: 6, step: 1 }
  d2: { min: 2, max: 9, step: 1 }
  is_multiply:
    type: bool
  answer:
    expr: 'simplify_expr(f"({a1}*x/{d1}) * ({a2}*x/{d2})" if is_multiply else f"({a1}*x/{d1}) / ({a2}*x/{d2})")'
question:
  text: 'Simplify'
  answer: '{{ answer }}'
  solution: '{{ "Multiply: " + str(answer) if is_multiply else "Divide: " + str(answer) }}'
""")
r = render_template_preview(t)
check("simplify_expr answer", r)
check("simplify_expr solution", r, 'solution')

# ── Test 4: fraction literal (unsimplified) ───────────────────────────────────
t = load_template_yaml("""
parameters:
  b: 9/12
question:
  text: 'Simplify'
  answer: '3/4'
  solution: '{{ b | fraction }}'
""")
r = render_template_preview(t)
check("fraction literal (should be \\frac{9}{12})", r, 'solution')

# ── Test 5: list / statistical functions ──────────────────────────────────────
t = load_template_yaml("""
parameters:
  data:
    expr: gaussian_list(20, 3, 8)
question:
  text: 'Find the mean'
  answer: '{{ mean(data) }}'
  solution: 'Mean = {{ mean(data) }}'
""")
check("list/mean", render_template_preview(t))

# ── Test 6: gcd in CaseParameter ─────────────────────────────────────────────
t = load_template_yaml("""
parameters:
  a:
    min: 2
    max: 12
    step: 1
  b:
    min: 2
    max: 12
    step: 1
  g:
    expr: 'gcd(a, b)'
question:
  text: 'GCD of {{a}} and {{b}}'
  answer: '{{ g }}'
  solution: 'gcd = {{ g }}'
""")
check("gcd", render_template_preview(t))

# ── Test 7: string concatenation with answer in ternary ───────────────────────
t = load_template_yaml("""
parameters:
  is_multiply:
    type: bool
  a1: { min: 2, max: 6, step: 1 }
  d1: { min: 2, max: 9, step: 1 }
  a2: { min: 2, max: 6, step: 1 }
  d2: { min: 2, max: 9, step: 1 }
  answer:
    expr: 'simplify_expr(f"({a1}*x/{d1}) * ({a2}*x/{d2})" if is_multiply else f"({a1}*x/{d1}) / ({a2}*x/{d2})")'
question:
  text: 'Simplify'
  answer: '{{ answer }}'
  solution: '{{ "Multiply: $" + str(answer) + "$" if is_multiply else "Divide: $" + str(answer) + "$" }}'
""")
r = render_template_preview(t)
check("str(answer) in ternary solution", r, 'solution')

print("\nAll tests passed.")
