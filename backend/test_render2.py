import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from backend.render.render import render_template_preview
from backend.rendering import load_template_yaml

t = load_template_yaml("""
parameters:
  is_multiply:
    type: bool
  a: {min: 2, max: 6, step: 1}
  b: {min: 2, max: 6, step: 1}
  answer:
    expr: 'a * b if is_multiply else a + b'
question:
  text: 'Result?'
  answer: '{{ answer }}'
  solution: '{{ is_multiply }} -> {{ answer }}'
""")
r = render_template_preview(t)
print('keys:', list(r.keys()))
print('solution:', repr(r.get('solution')))
print('answers:', r.get('answers'))
print('question:', repr(r.get('question')))
