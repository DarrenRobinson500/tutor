
from __future__ import annotations
import os
import time
import yaml
from .utilities import *
from openai import OpenAI

_DOC_PATH = os.path.join(os.path.dirname(__file__), "Editor Documentation.txt")
with open(_DOC_PATH, encoding="utf-8") as _f:
    _EDITOR_DOCS = _f.read()

PROMPT_INSTRUCTIONS = f"""
The following documentation describes the full template format. The docs use YAML syntax
(as written in the editor); when returning templates you must use JSON syntax instead —
but all rules for parameters, expressions, answers, diagrams, and validation apply equally.

{_EDITOR_DOCS}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JSON RETURN FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each template must be returned as an item in a JSON array.

{{
  "title": "...",
  "years": <integer 1–10>,
  "difficulty": "easy" | "medium" | "hard",
  "parameters": {{ "a": {{ "size": "small" }}, "b": {{ "size": "medium" }} }},
  "question": "...",
  "answers": "answer_param",
  "solution": "...",
  "diagram": "none",
  "validation": ["a > b"]
}}

IMPORTANT: "parameters" must be a JSON object — do NOT embed YAML inside JSON:
  CORRECT: "parameters": {{ "a": {{ "size": "small" }} }}
  WRONG:   "parameters":\\n  a:\\n    min: 2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PREFERRED TEMPLATE STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use this pattern as the default style:

1. Use "size" presets ("small", "medium", "large") for parameters instead of explicit min/max wherever possible.
2. Pre-calculate the answer as a derived parameter using an expression (bare string shorthand).
3. Use the bare string shorthand for answers: "answers": "answer_param" — a single string, NOT a list.
4. Reference the answer param in the solution so students can see the working.

Answer key rules:
  "answers": "param_name"          — preferred: bare string shorthand for a single computed answer
  "answers": [{{"text": ..., "correct": ...}}]  — use ONLY for genuine multiple-choice questions
  "answer": {{"input": "{{{{ expr }}}}", "correct": true, "answer_format": "integer"}}
                                   — use when you need explicit input field options (no derived param)

Example (percentage question):
  "parameters": {{
    "a": {{ "size": "medium" }},
    "percentage": {{ "type": "percent", "size": "small" }},
    "b": "a * percentage"
  }},
  "question": "What percentage is {{ b }} of {{ a }}?",
  "answers": "percentage",
  "solution": "Divide {{ b }} by {{ a }} and multiply by 100: {{ b }} / {{ a }} × 100 = {{ percentage }}."

Example (simple arithmetic):
  "parameters": {{
    "a": {{ "size": "medium" }},
    "b": {{ "size": "small" }},
    "answer": "a + b"
  }},
  "question": "What is {{ a }} + {{ b }}?",
  "answers": "answer",
  "solution": "{{ a }} + {{ b }} = {{ answer }}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Every parameter used anywhere must be declared in the "parameters" block.
- ALWAYS use size presets for integer parameters: {{"size": "small"}}, {{"size": "medium"}}, or {{"size": "large"}}. Never write min/max unless the question specifically requires a restricted range (e.g. angles must be under 90, or a divisor must divide evenly). When in doubt, use size.
- Always pre-calculate the answer as a derived parameter (e.g. "answer": "a * b") and reference it in both "answers" and "solution".
- For a single computed answer use the bare string shorthand "answers": "param_name". Only use "answers" as a list for genuine multiple-choice questions. Use "answer" (singular, as a dict) only when you need explicit input field options without a derived parameter.
- percent parameters (type: percent) already render with a % sign (e.g. "35%"). Do NOT add a literal % after {{ rate }} in question text — write "{{ rate }} of" not "{{ rate }}% of".
- percent parameters store their value as the decimal proportion internally (35% is stored as 0.35). Do NOT divide by 100 anywhere — not in expressions, not in derived parameters, not in "expr" fields.
  CORRECT:   "total": "amount * rate"            (rate is already 0.35)
  WRONG:     "total": "amount * (rate / 100)"    (would give amount * 0.0035)
  WRONG:     "total": "amount * rate / 100"      (same mistake)
  This applies everywhere: {{ }}, "expr":, and "answers":.
- For validation, use a simple list of rule expressions: "validation": ["a > b"]. Only include validation when it is genuinely needed to avoid degenerate cases.
- Return ONLY valid JSON. No markdown fences. No commentary.
"""


chat_key=os.environ["CHAT_KEY"]

client = OpenAI(api_key=chat_key)

def _extract_existing_questions(skill) -> list[str]:
    """Return question texts from all existing templates for this skill."""
    from .models import Template
    questions = []
    qs = Template.objects.filter(skill_detail=skill).exclude(content__isnull=True).exclude(content="")
    for t in qs:
        try:
            parsed = yaml.safe_load(t.content)
            text = parsed.get("question", {}).get("text", "")
            if text:
                questions.append(text)
        except Exception:
            pass
    return questions


def generate_template_content(skill, grade) -> dict:
    existing_questions = _extract_existing_questions(skill)

    existing_section = ""
    if existing_questions:
        lines = [
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "EXISTING QUESTIONS — do not repeat these question types",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for i, q in enumerate(existing_questions, 1):
            lines.append(f"{i}. {q}")
        existing_section = "\n".join(lines) + "\n"
        print(existing_section)

    detail_items = [d.strip() for d in (skill.detail or "").split("\n") if d.strip()]

    if detail_items:
        detail_list = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(detail_items))
        n = len(detail_items)
        detail_section = (
            f"\n\nThis skill covers {n} specific learning outcomes:\n{detail_list}\n\n"
            f"Generate exactly one EASY template for EACH outcome — {n} templates total.\n"
            f"Each template must include a top-level 'subject' field set to the exact text of its outcome.\n"
            f"Work through the outcomes in order."
        )
    else:
        detail_section = ""

    prompt = (
        f"You are an expert NSW mathematics tutor. "
        f"Create structured practice templates for the skill: '{skill.description}' "
        f"and for the grade: '{grade}' which relates to '{maths_stage(grade)}'.\n"
    )
    prompt += PROMPT_INSTRUCTIONS
    prompt += (
        "\n- The \"title\" must describe what the question actually asks, not the skill name."
        "\n  Good: \"Find the gradient from two points\", \"Identify the y-intercept from an equation\"."
        "\n  Bad:  \"Gradient Question 3\", \"Understanding gradient and intercepts - Easy - 1\"."
        "\n- ALL templates must have difficulty set to \"easy\"."
        "\n- Easy means: straightforward single-step question with small numbers, testing direct recall or a simple application."
    )
    if not detail_items:
        prompt += "\n- Provide exactly 3 easy templates."
    prompt += detail_section
    prompt += existing_section

    # print(prompt)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    raw = response.choices[0].message.content
    return extract_json(raw)


def update_template(existing_yaml: str, user_instruction: str, model: str = "gpt-4o-mini") -> dict:
    """Update an existing template YAML based on a natural language instruction.
    Returns a single template dict."""
    prompt = (
        "You are an expert NSW mathematics tutor. "
        "Update the following template according to the instruction below.\n\n"
        f"INSTRUCTION: {user_instruction}\n\n"
        f"EXISTING TEMPLATE (YAML):\n{existing_yaml}\n\n"
    )
    prompt += PROMPT_INSTRUCTIONS
    prompt += (
        "\n- Return ONLY ONE template as a single JSON object (not an array)."
        "\n- Preserve all existing fields (title, years, difficulty, skill) unless the instruction requires changing them."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = response.choices[0].message.content
    result = extract_json(raw)
    if isinstance(result, list):
        return result[0]
    return result

def generate_template_from_image(image_b64: str | None, mime_type: str, skills: list, grade: str, additional_prompt: str = "") -> dict:
    """Generate a single template from an optional question screenshot using GPT-4o.
    When image_b64 is None the prompt is sent as text-only (no vision).
    skills: leaf skills already filtered to the given grade.
    grade: NSW year level string (e.g. "7") provided by the user.
    """
    skill_lines = "\n".join(
        f"  {s['id']}: {s['description']} ({s['code']})"
        for s in skills
    )

    if image_b64:
        intro = (
            "You are an expert NSW mathematics tutor. "
            "The image shows a maths question from a textbook or worksheet. "
            f"Generate ONE parameterised practice template based on this question for NSW Year {grade}.\n\n"
        )
    else:
        intro = (
            "You are an expert NSW mathematics tutor. "
            f"Generate ONE parameterised practice template for NSW Year {grade}.\n\n"
        )

    prompt = (
        intro +
        "Select the single most appropriate skill from the list below and return "
        "its numeric ID in a top-level field called 'skill_id'.\n\n"
        "Infer the difficulty ('easy', 'medium', or 'hard') from the question's complexity.\n\n"
        f"AVAILABLE SKILLS (Year {grade}):\n{skill_lines}\n\n"
    )
    prompt += PROMPT_INSTRUCTIONS
    prompt += (
        "\n- Return ONLY ONE template as a single JSON object (not an array)."
        f"\n- Set the 'years' field to {grade}."
        "\n- Include the extra field 'skill_id' (integer matching one of the skill IDs above)."
        "\n- The \"title\" must describe what the question actually asks, not the skill name."
    )
    if additional_prompt and additional_prompt.strip():
        prompt += f"\n\nAdditional instructions from the user: {additional_prompt.strip()}"

    if image_b64:
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:{mime_type};base64,{image_b64}",
                "detail": "high",
            }},
        ]
    else:
        content = prompt

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        temperature=0.4,
    )
    raw = response.choices[0].message.content
    result = extract_json(raw)
    if isinstance(result, list):
        return result[0]
    return result

def generate_single_template(skill, grade: str, difficulty: str, subject: str) -> dict:
    """Generate exactly one template for a specific skill/grade/difficulty/subject."""
    existing_questions = _extract_existing_questions(skill)
    existing_section = ""
    if existing_questions:
        lines = [
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "EXISTING QUESTIONS — do not repeat these question types",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ] + [f"{i+1}. {q}" for i, q in enumerate(existing_questions)]
        existing_section = "\n".join(lines) + "\n"

    difficulty_guidance = {
        "easy":   "straightforward single-step question with small numbers, testing direct recall or a simple application",
        "medium": "two-step question requiring the student to apply the concept in a slightly unfamiliar context",
        "hard":   "multi-step or worded problem requiring deeper reasoning, larger numbers, or combining multiple ideas",
    }
    diff_desc = difficulty_guidance.get(difficulty, difficulty)

    prompt = (
        f"You are an expert NSW mathematics tutor. "
        f"Create ONE practice template for the skill: '{skill.description}' "
        f"for Year {grade} ({maths_stage(grade)}).\n\n"
        f"DIFFICULTY: {difficulty.upper()} — {diff_desc}.\n"
        f"LEARNING OUTCOME: \"{subject}\"\n"
        f"The question must directly test this learning outcome at the specified difficulty level.\n"
        f"Set the top-level 'subject' field to exactly: \"{subject}\"\n"
    )
    prompt += PROMPT_INSTRUCTIONS
    prompt += (
        "\n- Return ONLY ONE template as a single JSON object (not an array)."
        f"\n- Set difficulty to \"{difficulty}\"."
        "\n- The \"title\" must describe what the question actually asks, not the skill name."
    )
    prompt += existing_section

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    raw = response.choices[0].message.content
    result = extract_json(raw)
    if isinstance(result, list):
        return result[0]
    return result


def align_template_subject(template_name: str, question_text: str, detail_lines: list[str]) -> str:
    """Ask the AI which detail line a template question is most associated with.
    Returns the exact text of the chosen detail line."""
    detail_list = "\n".join(f"  {i+1}. {line}" for i, line in enumerate(detail_lines))
    prompt = (
        f"A maths skill has the following specific learning outcomes:\n{detail_list}\n\n"
        f"A question template has the title: \"{template_name}\"\n"
        f"and the question text: \"{question_text}\"\n\n"
        f"Which single learning outcome from the numbered list above does this question most directly test?\n"
        f"You MUST copy one of the outcomes from the list VERBATIM — word for word, character for character.\n"
        f"Do NOT paraphrase, summarise, or reword. Do NOT add any explanation or number.\n"
        f"Your entire reply must be one of the {len(detail_lines)} lines above, copied exactly."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    result = response.choices[0].message.content.strip()
    # Validate: if the AI returned something not in the list, fall back to the closest exact match
    if result not in detail_lines:
        # Try case-insensitive match
        lower_result = result.lower()
        for line in detail_lines:
            if line.lower() == lower_result:
                return line
        # Fall back to first line rather than returning an invalid subject
        return detail_lines[0] if detail_lines else result
    return result


def generate_knowledge_from_image(image_b64: str, mime_type: str, additional_prompt: str = "") -> dict:
    """Generate a Knowledge item (title, text, diagram, text_2) from an image using GPT-4o vision."""
    prompt = (
        "You are an expert NSW mathematics tutor. "
        "The image shows a maths concept, formula, worked example, or explanation. "
        "Generate a structured knowledge item that explains the concept shown.\n\n"
        "Return a single JSON object with these fields:\n"
        "  title: short descriptive title (e.g. 'Circumference of a circle')\n"
        "  text: main explanation or formula in plain text. Use $...$ for inline LaTeX and $$...$$ for display LaTeX.\n"
        "  diagram: diagram code string using the diagram syntax from the documentation below, or 'none' if not applicable.\n"
        "  text_2: optional secondary text such as a worked example or additional notes. "
        "Use $...$ / $$...$$ for LaTeX. Leave empty string if not needed.\n\n"
        "Return ONLY valid JSON. No markdown fences. No commentary.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "DIAGRAM DOCUMENTATION\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    prompt += _EDITOR_DOCS
    if additional_prompt and additional_prompt.strip():
        prompt += f"\n\nAdditional instructions: {additional_prompt.strip()}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:{mime_type};base64,{image_b64}",
                    "detail": "high",
                }},
            ],
        }],
        temperature=0.3,
    )
    raw = response.choices[0].message.content
    result = extract_json(raw)
    if isinstance(result, list):
        return result[0]
    return result


def _fix_yaml_template_quoting(content: str) -> str:
    """Ensure YAML scalar values containing {{ }} expressions are properly quoted.

    The YAML parser treats a bare { as the start of a flow mapping, so any
    value like:  solution: {{ a }} + {{ b }} = {{ c }}
    must be quoted:  solution: "{{ a }} + {{ b }} = {{ c }}"

    Also fixes already-double-quoted values that contain unescaped inner double
    quotes, e.g. post_answer: "{{ Knowledge("key") }}" — the inner quotes from
    Knowledge() calls break double-quoted YAML strings.
    """
    import re
    fixed_lines = []
    scalar_re = re.compile(r'^(\s*[\w][\w\s]*:\s+)(.+)$')
    for line in content.split('\n'):
        m = scalar_re.match(line)
        if m and '{{' in m.group(2):
            prefix = m.group(1)
            value = m.group(2).strip()
            # Already single-quoted (complete '...' or start of multi-line '...\n  ...') — leave alone
            if value.startswith("'"):
                fixed_lines.append(line)
            # Already double-quoted (complete "..." or start of multi-line "...\n  ...") —
            # check for unescaped inner double quotes only on complete single-line values.
            elif value.startswith('"') and value.endswith('"') and value.count('"') >= 2:
                inner = value[1:-1]
                # Replace any unescaped " inside with \"
                fixed_inner = re.sub(r'(?<!\\)"', '\\"', inner)
                if fixed_inner != inner:
                    fixed_lines.append(f'{prefix}"{fixed_inner}"')
                else:
                    fixed_lines.append(line)
            else:
                # Not quoted — escape backslashes and double-quotes, then wrap
                escaped = value.replace('\\', '\\\\').replace('"', '\\"')
                fixed_lines.append(f'{prefix}"{escaped}"')
        else:
            fixed_lines.append(line)
    return '\n'.join(fixed_lines)


def translate_template_content(content: str, language: str) -> str:
    """Translate human-readable text in a YAML template to the target language.

    Preserves all {{ param }} expressions, LaTeX, numbers, and structural YAML keys
    unchanged — only translates the natural-language strings (question text, solution
    text, title, answer choice text, etc.).

    Returns the translated YAML string.
    """
    prompt = (
        "You are a professional mathematics educator and translator. "
        "Translate the human-readable text in the YAML template below into "
        f"the language with BCP-47 code: '{language}'.\n\n"
        "STRICT RULES:\n"
        "1. Preserve all {{ expr }} template parameters exactly — do NOT translate or alter them.\n"
        "2. Preserve ALL LaTeX exactly — this includes:\n"
        "   - Delimited LaTeX: $...$ and $$...$$\n"
        "   - Bare backslash commands anywhere in the text: \\times, \\div, \\cdot, \\frac, \\sqrt,\n"
        "     \\pm, \\leq, \\geq, \\neq, \\approx, \\pi, \\theta, \\alpha, \\beta, and any other \\word.\n"
        "   Do NOT translate, remove, or alter any backslash-prefixed word.\n"
        "3. Preserve all YAML keys (e.g. question:, solution:, title:, text:) exactly.\n"
        "4. Preserve all numbers, operators, and mathematical notation exactly.\n"
        "5. Preserve the 'diagram:' value exactly.\n"
        "6. Translate ONLY the natural-language text values: title, question text, solution text, "
        "answer choice text (the 'text' field inside answers lists).\n"
        "7. IMPORTANT: Any YAML value that contains {{ or }} MUST be wrapped in double quotes.\n"
        "   Example — WRONG:  solution: {{ a }} + {{ b }} = {{ c }}\n"
        "   Example — RIGHT:  solution: \"{{ a }} + {{ b }} = {{ c }}\"\n"
        "8. Return ONLY the translated YAML — no explanation, no markdown fences.\n"
        "9. Do NOT translate the string arguments inside Knowledge(...), Skill(...), or any similar "
        "function calls within {{ }} expressions — these are database references that must remain "
        "exactly as written in English. "
        "Example — WRONG:  post_answer: \"{{ Knowledge('Nhân và Chia') }}\"\n"
        "   Example — RIGHT:  post_answer: \"{{ Knowledge('Multiplying and Dividing') }}\"\n\n"
        f"TEMPLATE:\n{content}"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    translated = response.choices[0].message.content.strip()
    # Safety net: fix any values that still have unquoted {{ expressions
    return _fix_yaml_template_quoting(translated)


def generate_report_narrative(
    student_first_name: str,
    year_level,
    overall_level: str,
    coverage_percent,
    total_assessed: int,
    strengths: list,
    focus_areas: list,
) -> dict:
    """
    Generate narrative text for the parent PDF progress report.
    strengths / focus_areas: [{'skill_description': ..., 'level_label': ...}, ...]
    Returns dict with keys: summary, strength_blurbs, focus_blurbs, recommendation.
    """
    import json as _json

    yr = str(year_level) if year_level else None
    cov_str = (
        f"{coverage_percent}% of the Year {yr} Mathematics syllabus"
        if coverage_percent is not None and yr
        else f"{total_assessed} skills"
    )
    strengths_text = "\n".join(f"- {s['skill_description']} ({s['level_label']})" for s in strengths) or "None identified yet."
    focus_text = "\n".join(f"- {f['skill_description']} ({f['level_label']})" for f in focus_areas) or "None identified yet."

    user_prompt = (
        f"Student first name: {student_first_name}\n"
        f"Year level: {yr or 'not specified'}\n"
        f"Syllabus assessed: {cov_str}\n"
        f"Overall competency: {overall_level}\n\n"
        f"Strongest skills:\n{strengths_text}\n\n"
        f"Skills needing focus:\n{focus_text}\n\n"
        "Output ONLY valid JSON (no markdown, no extra text):\n"
        "{\n"
        f'  "summary": "<2-4 sentence opening paragraph. Warm and specific. Mention {student_first_name} by name. Reference year level and coverage.>",\n'
        '  "strength_blurbs": {"<skill_description>": "<one warm encouraging sentence>"},\n'
        '  "focus_blurbs": {"<skill_description>": "<one forward-looking opportunity sentence, no negatives>"},\n'
        '  "recommendation": "<one specific, actionable recommendation for the coming weeks, names the exact topic>"\n'
        "}"
    )
    system_prompt = (
        "You write warm, professional parent progress reports for a maths tutoring platform. "
        "Never use words like failed, weak, poor, struggling, or behind. "
        "Frame gaps as opportunities. Be specific and encouraging. "
        "The tone should feel like a specialist who knows this child personally."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=900,
        )
        raw = response.choices[0].message.content.strip()
        return _json.loads(raw)
    except Exception:
        return _fallback_narrative(student_first_name, yr, overall_level, cov_str, strengths, focus_areas)


def _fallback_narrative(first, yr, overall_level, cov_str, strengths, focus_areas):
    top_strength = strengths[0]['skill_description'] if strengths else None
    top_focus = focus_areas[0]['skill_description'] if focus_areas else None
    summary = (
        f"{first} has been working hard this term. "
        f"They have been assessed across {cov_str} and are performing at a {overall_level} level overall."
    )
    if top_strength:
        summary += f" {first} is showing real strength in {top_strength}."
    strength_blurbs = {
        s['skill_description']: f"{first} is performing well in this area and demonstrates solid understanding."
        for s in strengths
    }
    focus_blurbs = {
        f['skill_description']: "This is an important area to develop — focusing here will build a strong foundation for upcoming topics."
        for f in focus_areas
    }
    recommendation = (
        f"Over the coming weeks, we recommend focusing on {top_focus}. "
        f"Building confidence here will directly support {first}'s readiness for future topics."
        if top_focus else
        "Continue consolidating all assessed topics to build lasting confidence and understanding."
    )
    return {
        'summary': summary,
        'strength_blurbs': strength_blurbs,
        'focus_blurbs': focus_blurbs,
        'recommendation': recommendation,
    }
