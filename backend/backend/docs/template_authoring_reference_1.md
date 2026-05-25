# Template Authoring Reference
## Conventions for bulk template production

---

## File format

All templates are delivered as a single `templates_[ParentSkill]_[Year].yaml` file.
The parent skill name and year is included in the filename, capitalised, e.g.
`templates_Data_Year10.yaml`, `templates_Trigonometry_Year10.yaml`.

```yaml
year: 10

templates:

  - skill_detail: "Exact skill detail text as provided"
    difficulty: easy
    yaml: |
      parameters:
        ...
      question:
        ...
      diagram: >
        ...
```

- `year` is declared once at the top and applies to every template in the file.
- `skill_detail` must match the exact text provided — this is how the system
  looks up both the skill detail and its parent skill.
- `difficulty` is one of: `easy`, `medium`, `hard`.
- Every skill detail gets exactly 3 templates (easy, medium, hard) unless a
  skill detail is unassessable (see below).

---

## Parameters

### Use `scenario` instead of `validation`

Never use multiple `choice` lists locked together with a `validation` block.
Always use a `scenario` table instead. Each row holds all correlated values
together, eliminating the need for validation.

```yaml
# ✗ Don't do this
parameters:
  angle:
    type: choice
    values: [30, 45, 60]
  func:
    type: choice
    values: [sin, cos, tan]
validation:
  - angle == 30 and func == 'sin' or ...

# ✓ Do this
parameters:
  scenario:
    type: scenario
    rows:
      - [30, sin, "1/2"]
      - [45, cos, "√2/2"]
      - [60, tan, "√3"]
  angle: scenario[0]
  func:  scenario[1]
  ans:   scenario[2]
```

Only use `validation:` for mathematical guards on computed `expr` values
(e.g. preventing `asin` domain errors), never for locking parameter combinations.

### Expressions

Use `expr:` for computed parameters. Keep pipes in solution text for correct
rendering but not in `answer:` fields.

```yaml
hyp:
  expr: (a**2 + b**2) ** 0.5
```

---

## Answer fields

### Use `answer_unit` to show units after the input box

Set `answer_unit` at the part or question level to display a unit label immediately
after the student's input box. The student sees `[   ] cm` and knows not to type
the unit themselves.

```yaml
parts:
  - text: "Find the length of the hypotenuse."
    answer: "{{ hyp }}"
    answer_format: decimal_2
    answer_unit: "cm"
```

`answer_unit` can be any string: `"cm"`, `"°"`, `"m²"`, `"km/h"`, etc.

---

### Use `answer_format` instead of `tolerance` + `format_instruction` + pipe

```yaml
# ✗ Don't do this
answer: "{{ angle | decimal(decimal_places=1) }}"
tolerance: 0.2
format_instruction: "Give the angle in degrees to 1 decimal place."

# ✓ Do this
answer: "{{ angle }}"
answer_format: decimal_1
```

Available `answer_format` values:

| Format | Use for |
|---|---|
| `integer` | Whole number answers |
| `decimal_1` | 1 decimal place |
| `decimal_2` | 2 decimal places |
| `decimal_3` | 3 decimal places |

`tolerance:` can still be added alongside `answer_format` when a range of
acceptable rounding is needed.

### Keep pipes in solution text

The pipe is dropped from the `answer:` field but kept everywhere else:

```yaml
answer: "{{ angle }}"           # no pipe
answer_format: decimal_1
solution: >
  $\theta \approx {{ angle | decimal(decimal_places=1) }}°$   # pipe kept
```

### Only include assessable answers

Only use `answer:` when the answer is:
- A computed numeric value (`{{ dist }}`, `{{ m * x + c }}`, `{{ points | length }}`)
- A short exact string that will always match (`{{ ind_var }}`, `{{ method }}` when it
  is a single word from a scenario column)

Never use `answer:` for:
- Multi-sentence prose explanations
- Descriptions of methods, hypotheses, or limitations
- Any string a student would reasonably phrase differently

### Use `choices:` for qualitative questions

All interpretation, explanation, and conceptual questions must use `choices:`.
The correct answer is one option; distractors are plausible misconceptions.

```yaml
- text: "What does the gradient represent in this context?"
  choices:
    - text: "For each additional hour of study, the exam score increases by 8%."
      correct: true
    - text: "The predicted exam score when hours studied = 0."
      correct: false
```

### Unassessable skill details — omit templates

If a skill detail requires only open-ended responses (writing hypotheses,
designing studies, describing methods) with no definitively correct answer,
do not produce templates for it. Note the omission in a comment in the file.

```yaml
# NOTE: "Plan and conduct a statistical inquiry" requires open-ended prose
# responses (hypotheses, collection methods, limitations) that cannot be
# assessed by string comparison. No templates are included for this skill detail.
```

---

## Question structure

### Put full questions in `parts`, not in `question.text`

`question.text` contains only the shared setup/context. All sub-questions
belong in `parts` with their full text there. Never put (a), (b), (c) labels
in `question.text`.

```yaml
# ✗ Don't do this
question:
  text: >
    A box has dimensions {{ a }} × {{ b }} × {{ h }} cm.
    (a) Find the space diagonal.
    (b) Find the angle with the base.
  parts:
    - text: "Find the space diagonal."

# ✓ Do this
question:
  text: >
    A box has dimensions {{ a }} × {{ b }} × {{ h }} cm.
  parts:
    - text: "Find the space diagonal of the box."
      answer: "{{ diag }}"
      answer_format: decimal_2
    - text: "Find the angle the space diagonal makes with the base."
      answer: "{{ angle }}"
      answer_format: decimal_1
```

---

## Formatting and style

### Use `| capitalize` consistently

Use `| capitalize` wherever a variable appears at the start of a sentence,
in headings, in axis labels, or where `**bold**` markdown is used.

```yaml
# ✓ Correct usage
solution: >
  **{{ direction | capitalize }}** association.
  
text: >
  The scatter plot shows **{{ x_label | capitalize }}** vs **{{ y_label | capitalize }}**.

diagram: >
  ScatterPlot(
    x_label: "{{ x_label | capitalize }}",
    y_label: "{{ y_label | capitalize }}",
  )
```

### Diagram placement and indentation

`diagram:` is a top-level key at the **same level as `question:`** and
`parameters:`. It must never be nested inside `question:`.

This error occurs inside the `yaml: |` block in the import file. The
correct indentation inside that block is:

```yaml
# ✗ Don't do this — diagram is indented under question
    yaml: |
      parameters:
        ...
      question:
        text: >
          ...
        diagram: >        # ← WRONG: nested inside question
          ScatterPlot(...)

# ✓ Do this — diagram at the same level as question
    yaml: |
      parameters:
        ...
      question:
        text: >
          ...
      diagram: >          # ← CORRECT: same level as question
        ScatterPlot(...)
```

The rule applies to all diagram types: `Triangle`, `Solid3D`,
`CircleTheorem`, `UnitCircle`, `ExactTriangle`, `ScatterPlot`,
`Cartesian`, `Graph`.

### No (a) (b) (c) in question text

Sub-question labels are implied by the `parts` structure. Never add them
to `question.text` or to `parts[].text`.

---

## Diagram types

### Available diagram types

| Type | Used for |
|---|---|
| `Triangle` | Right-angled and non-right-angled triangle problems |
| `Solid3D` | 3D geometry — prisms, pyramids, space diagonals, angles with planes |
| `CircleTheorem` | Circle geometry — chords, angles, tangents |
| `UnitCircle` | Trigonometric functions, exact values, equation solving |
| `ExactTriangle` | 30/60/90 and 45/45/90 exact value triangles |
| `ScatterPlot` | Bivariate data, lines of best fit, predictions |
| `Cartesian` | Function graphs (sin, cos, tan over 0°–360°) |
| `Graph` | Network/graph theory — vertices, edges, degrees, faces, Eulerian paths |
| `NumberLine` | Number line diagrams — marked points, arrows showing jumps or ranges |

### `Solid3D` key conventions

Points use unit-cube coordinates (0–1 on each axis), independent of dimensions:

```yaml
diagram: >
  Solid3D(
    shape: rect_prism,
    w: {{ a }}, h: {{ h }}, d: {{ b }},
    points: {A: (0,0,0), B: (1,0,0), C: (1,1,0), G: (1,1,1)},
    lines: [CG],
    dash: [AC, AB],
    highlight: [AG],
    right_angle_at: {C: [AC, CG]},
    label_angle: {A: [AG, AC], label: "{{ angle | decimal(decimal_places=1) }}°"},
    label_length: {AG: "{{ diag | decimal(decimal_places=2) }} cm"},
    label_point: {A: "A", C: "C", G: "G"}
  )
```

Shortcuts: `centre_base`, `centre_top`, `midpoint(AB)`, `foot(G, base)`.

### `UnitCircle` key conventions

```yaml
diagram: >
  UnitCircle(
    angle: {{ angle }},
    show_point: true,
    show_sin: true,
    show_cos: true,
    show_tan: false,
    show_reference_angle: true,
    show_quadrant_labels: true,
    highlight_quadrant: {{ quadrant }},
    label_point: "P",
    lock_angle: true
  )
```

Set `lock_angle: false` for interactive/exploratory questions.

### `ScatterPlot` key conventions

```yaml
diagram: >
  ScatterPlot(
    x_label: "{{ x_label | capitalize }}",
    y_label: "{{ y_label | capitalize }}",
    points: {{ points }},
    equation: "{{ m }} * x + {{ c }}",
    show_line_of_best_fit: true,
    show_gradient_annotation: true,
    show_intercept_annotation: true,
    highlight_prediction: {{ pred_x }},
    show_grid: true
  )
```

### `NumberLine` key conventions

| Parameter | Required | Description |
|---|---|---|
| `min` | No | Left bound. Inferred from dots/arrows minus 2 if omitted. |
| `max` | No | Right bound. Inferred from dots/arrows plus 2 if omitted. |
| `dots` | No | List of values to mark with a filled dot. |
| `arrows` | No | List of `(start, end)` pairs drawn as horizontal arrows above the line. |
| `pos` | No | `(x, y)` offset for placement. Defaults to `(0, 0)`. |

**Dot only:**

```yaml
diagram: >
  NumberLine(min: 0, max: 10, dots: [5])
```

**Multiple dots:**

```yaml
diagram: >
  NumberLine(min: 0, max: 10, dots: [3, 7])
```

**Arrow only** (showing a jump or range):

```yaml
diagram: >
  NumberLine(min: 0, max: 10, arrows: [(2, 7)])
```

**Dots and arrows combined:**

```yaml
diagram: >
  NumberLine(min: 0, max: 10, arrows: [(2, 7)], dots: [2, 7])
```

**Auto-inferred bounds** — omit `min`/`max` and they are calculated from the dot/arrow values with ±2 padding:

```yaml
diagram: >
  NumberLine(dots: [4, 8])
```

### `CircleTheorem` key conventions

```yaml
diagram: >
  CircleTheorem(
    radius: 5,
    points: {O: centre, A: 210, B: 330, C: 90},
    lines: [OA, OB, AC, BC],
    midpoint: {M: AB},
    highlight_arc: AB,
    right_angle_at: [M],
    label_angle: {ACB: "{{ inscribed }}°", AOB: "?"},
    label_length: {AB: "{{ chord }} cm", AM: "?"}
  )
```

Use `midpoint: {M: AB}` (not `points: {M: 270}`) to place a point at the
midpoint of a chord.

---

## Syllabus alignment

Always check skill details against the NSW Stage 5 syllabus document before
writing templates. Call out any misalignment or partial coverage:

- ✅ Full alignment — proceed
- ⚠️ Minor flag — note the gap, write templates for the intended skill
- ❌ Wrong path/year — flag clearly and suggest correction

Common flags to watch for:
- Ambiguous case of sine rule belongs in Trig D (Advanced path), not Trig C
- "Validity and reliability" language is Stage 6 — use "accuracy and bias"
  for Stage 5
- Gradient/intercept of line of best fit is in Linear Relationships strand,
  not Data strand (though appropriate as an extension)

---

## Summary checklist before submitting a template file

- [ ] Filename includes the parent skill name with capital: `templates_to_import_[ParentSkill].yaml`
- [ ] `year:` declared at top of file
- [ ] All `skill_detail:` values match exact provided text
- [ ] 3 templates per assessable skill detail (easy, medium, hard)
- [ ] Unassessable skill details noted in a comment, no templates produced
- [ ] `scenario` used everywhere instead of `choice` + `validation`
- [ ] `answer_format:` used instead of pipe on answer + `format_instruction`
- [ ] Pipes kept in `solution:` text
- [ ] No open-text prose `answer:` fields — all qualitative questions use `choices:`
- [ ] No (a)(b)(c) labels in `question.text`
- [ ] Full question text in `parts[].text`, not repeated from `question.text`
- [ ] `diagram:` at same indentation level as `question:` inside the `yaml: |` block — **not nested inside `question:`**
- [ ] `| capitalize` used in axis labels, bold text, and sentence-start variables
- [ ] Diagrams present on all Skill 2 (3D) templates using `Solid3D`
- [ ] `UnitCircle` used for unit circle and equation-solving questions
- [ ] `ScatterPlot` used for all bivariate data questions
- [ ] `Cartesian` used for graph-reading questions (sin/cos/tan graphs)
- [ ] `ExactTriangle` used for 30/45/60 exact value questions
- [ ] `Graph` used for all network/graph theory questions
