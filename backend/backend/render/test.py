from render import *

yaml = """
parameters:
  a:
    type: fraction
    size: small
    proper: true
    simplified: true

  b:
    type: fraction
    size: small
    proper: true
    simplified: true

question:
  text: "What is {{ a }} + {{ b }}?"

answers:
  - text: "{{ a | fraction }}"
  - text: "{{ b | fraction }}"
  - text: "{{ a + b | fraction }}"
  - text: "{{ a - b }}"
"""


# -------------------------
# TEST
# -------------------------

params = {
    "a": FractionParameter("a", {"size": "small", "proper": True}),
    "b": FractionParameter("b", {"size": "small", "proper": True})
}

renderer = Render(yaml)
result = renderer.render()

print(result["substituted_yaml"])
print(result["preview"])
