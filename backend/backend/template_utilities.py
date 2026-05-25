from .models import *
import yaml
import traceback as _traceback
from .render import render_template_preview
from .validation import *
from .rendering import load_template_yaml
from rest_framework.response import Response

import re as _re

def _fix_unquoted_diagram(content: str) -> str:
    """
    Quote an unquoted diagram string so YAML doesn't misparse the key: value
    pairs inside diagram command strings like Triangle(...) or Cartesian(...).

    Handles both forms:
        diagram: Triangle(a: 5, b: 5, c: 6)
        diagram:
          Triangle(a: 5, b: 5, c: 6)
    """
    def _quote(value: str) -> str:
        """Return single-quoted version of value, or the original if already safe."""
        value = value.strip()
        if value.startswith(("'", '"', '{', '|', '>')):
            return value
        if _re.match(r'[A-Z][A-Za-z]+\s*\(', value):
            return "'" + value.replace("'", "''") + "'"
        return value

    # Case 1: value on the same line — "diagram: Triangle(...)"
    def _fix_same_line(m):
        raw = m.group(2)
        quoted = _quote(raw)
        return m.group(1) + quoted if quoted != raw.strip() else m.group(0)

    content = _re.sub(
        r'^(\s*diagram:\s+)([^\n\'"\[{|>][^\n]+)$',
        _fix_same_line,
        content,
        flags=_re.MULTILINE,
    )

    # Case 2: value on the next indented line — "diagram:\n  Triangle(...)"
    def _fix_next_line(m):
        prefix = m.group(1)   # "diagram:\n"
        indent = m.group(2)   # leading whitespace of value line
        raw = m.group(3)
        quoted = _quote(raw)
        return (prefix + indent + quoted) if quoted != raw.strip() else m.group(0)

    content = _re.sub(
        r'^(\s*diagram:\s*\n)(\s+)([^\n\'"\[{|>][^\n]+)$',
        _fix_next_line,
        content,
        flags=_re.MULTILINE,
    )

    return content


_PARAM_PROPERTY_KEYS = {
    'min', 'max', 'type', 'size', 'proper', 'simplified', 'sign',
    'mixed', 'min_whole', 'max_whole', 'decimal_places', 'value',
    'min_numerator', 'max_numerator', 'min_denominator', 'max_denominator',
    'values', 'step', 'rows', 'count', 'order',
    'expr', 'brackets_when_negative',
}

_TOP_LEVEL_KEYS = {
    'title', 'years', 'difficulty', 'parameters', 'question',
    'answers', 'solution', 'diagram', 'validation', 'introduction', 'worked_example',
}


def _fix_parameters_indentation(content: str) -> str:
    """
    Detect and repair incorrectly indented parameters blocks.

    The AI sometimes emits:
        parameters:
            a:          ← 4 spaces
          min: 2        ← 2 spaces (should be 6, or at least deeper than 'a:')
          max: 5
        b:              ← 0 spaces (should be 2)
          min: 1

    Strategy:
      1. Quick-parse the YAML. If every parameter already has a non-null dict
         value, indentation is fine — return unchanged.
      2. Otherwise, scan the raw text from 'parameters:' forward, collecting
         parameter names (any key NOT in _PARAM_PROPERTY_KEYS and NOT a known
         top-level key) and their properties, then re-emit the block at the
         canonical 2-space / 4-space indentation.
    """
    try:
        parsed = load_template_yaml(content)
    except Exception:
        parsed = {}

    params = parsed.get('parameters', {})
    # If already a valid dict of dicts, nothing to fix
    if isinstance(params, dict) and params and all(
        (isinstance(v, dict) and v) or isinstance(v, (str, int, float)) for v in params.values()
    ):
        return content

    lines = content.split('\n')

    # Find the 'parameters:' line
    param_idx = next(
        (i for i, l in enumerate(lines) if _re.match(r'^parameters\s*:', l)),
        None,
    )
    if param_idx is None:
        return content

    # Scan forward, collecting (name, inline_val, {prop: raw_value}) entries
    entries = []
    current_name = None
    current_inline = None
    current_props = {}

    for line in lines[param_idx + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        m = _re.match(r'^([a-zA-Z_]\w*)\s*:\s*(.*)', stripped)
        if not m:
            continue

        key, raw_val = m.group(1), m.group(2).strip()

        # Stop when we reach the next known top-level section
        if key in _TOP_LEVEL_KEYS:
            break

        if key in _PARAM_PROPERTY_KEYS:
            if current_name is not None:
                current_props[key] = raw_val
        else:
            # New parameter name
            if current_name is not None:
                entries.append((current_name, current_inline, current_props))
            current_name = key
            current_inline = raw_val if raw_val else None
            current_props = {}

    if current_name is not None:
        entries.append((current_name, current_inline, current_props))

    if not entries:
        return content

    # Find where the old block ends in the line list
    block_end = param_idx + 1
    for i in range(param_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith('#'):
            block_end = i + 1
            continue
        m = _re.match(r'^([a-zA-Z_]\w*)\s*:', lines[i])
        if m and m.group(1) in _TOP_LEVEL_KEYS:
            break
        block_end = i + 1

    # Re-emit with canonical indentation (2 spaces / 4 spaces)
    new_block = []
    for name, inline_val, props in entries:
        if inline_val:
            # Inline scalar (e.g. `beats: rate * time`) — preserve on one line
            new_block.append(f'  {name}: {inline_val}')
        else:
            new_block.append(f'  {name}:')
            for prop_key, prop_val in props.items():
                new_block.append(f'    {prop_key}: {prop_val}' if prop_val else f'    {prop_key}:')

    new_lines = lines[:param_idx + 1] + new_block + lines[block_end:]
    return '\n'.join(new_lines)


def _fix_folded_blocks_with_tags(content: str) -> str:
    """Convert YAML `>` folded block scalars that contain {%...%} to `|` literal.

    With `>`, PyYAML joins consecutive non-blank lines with spaces, collapsing
    the newlines that a {% for %} loop needs to produce separate table rows.
    Switching to `|` (literal) preserves newlines so the expanded loop body
    lands on its own line.  Only affects blocks that actually contain {%...%};
    normal prose blocks using `>` are left unchanged.
    """
    lines = content.splitlines(keepends=True)
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect a folded block indicator: `key: >`, `key: >-`, `key: >+`, etc.
        m = _re.match(r'^(\s*\S.*?:\s*)(>[0-9+\-]*)(\s*\n)', line)
        if m and '>' in m.group(2):
            base_indent = len(line) - len(line.lstrip())
            j = i + 1
            block_lines = []
            while j < len(lines):
                bl = lines[j]
                stripped = bl.rstrip('\n\r')
                if stripped and len(stripped) - len(stripped.lstrip()) <= base_indent:
                    break
                block_lines.append(bl)
                j += 1
            if any('{%' in bl for bl in block_lines):
                # Replace `>` with `|`, keeping any modifier (+/-) and trailing whitespace
                new_indicator = m.group(2).replace('>', '|', 1)
                result.append(m.group(1) + new_indicator + m.group(3))
                result.extend(block_lines)
                i = j
                continue
        result.append(line)
        i += 1
    return ''.join(result)


def _fix_bare_expressions(content: str) -> str:
    """
    Quote any YAML scalar value that starts with {{ so the parser doesn't
    treat it as a flow mapping.  Only touches lines of the form:
        key: {{ ... }}   →   key: "{{ ... }}"
    Already-quoted values are left alone.
    Lines inside YAML block scalars (| or >) are skipped entirely.
    """
    def _repl(m):
        indent, key, value = m.group(1), m.group(2), m.group(3)
        if value.startswith('"') or value.startswith("'"):
            return m.group(0)
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'{indent}{key}: "{escaped}"'

    result = []
    in_block = False
    block_indent = -1

    for line in content.split('\n'):
        if in_block:
            # A line with no content (blank) stays in the block.
            # A non-blank line at indentation <= block_indent ends the block.
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)
            if stripped and current_indent <= block_indent:
                in_block = False
            else:
                result.append(line)
                continue

        # Detect the start of a block scalar (key: > or key: |)
        bm = _re.match(r'^(\s*)\S.*:\s*[|>][-+]?\s*$', line)
        if bm:
            in_block = True
            block_indent = len(bm.group(1))
            result.append(line)
            continue

        # Apply the bare-expression fix to non-block-scalar lines
        result.append(_re.sub(r'^(\s*)([\w_]+):\s*(\{\{.*)', _repl, line))

    return '\n'.join(result)


def generate_preview_from_content(content: str):
    # 1. Parse YAML
    # print("Generate preview from content - 1")
    content = _fix_unquoted_diagram(content)
    content = _fix_folded_blocks_with_tags(content)
    content = _fix_bare_expressions(content)
    content = _fix_parameters_indentation(content)
    try:
        parsed = load_template_yaml(content)
    except Exception as e:
        # print("Generate preview from content - 1 (failed)")
        return {
            "ok": False,
            "preview": {
                "question": "",
                "answers": [],
                "solution": "",
                "diagram_svg": "",
                "diagram_code": "",
                "substituted_yaml": content,
                "params": {},
                "errors": [f"YAML error: {str(e)}"]
            },
            "error": f"YAML error: {str(e)}"
        }

    # 2. Validate
    # print("Generate preview from content - 2")
    errors = validate_template(parsed)
    if errors:
        return {
            "ok": False,
            "preview": parsed,
            "error": errors
        }

    # 3. Render preview
    # print("Generate preview from content - 3")
    try:
        preview = render_template_preview(parsed)
        if "substituted_yaml" not in preview:
            preview["substituted_yaml"] = yaml.safe_dump(preview.get("full_yaml", parsed))
        #
        # preview["substituted_yaml"] = yaml.safe_dump(parsed)
        return {
            "ok": True,
            "preview": preview,
            "error": None
        }
    except Exception as e:
        tb = _traceback.format_exc()
        msg = f"{type(e).__name__}: {e}\n\n{tb}"
        return {
            "ok": False,
            "preview": {
                "question": "",
                "answers": [],
                "solution": "",
                "diagram_svg": "",
                "diagram_code": "",
                "substituted_yaml": content,
                "params": {},
                "errors": [msg]
            },
            "error": msg
        }


def generate_values_and_question(template_id: int):
    # 1. Load template
    template_obj = Template.objects.select_related("skill_detail").get(pk=template_id)
    print("Template object", template_obj)
    try:
        template_obj = Template.objects.select_related("skill_detail").get(pk=template_id)
    except Template.DoesNotExist:
        print("Template doesn't exist")
        return {
            "ok": False,
            "preview": None,
            "error": f"Template {template_id} not found"
        }

    content = template_obj.content
    # print("Generate values and question (content):", content)

    # Apply same preprocessing as generate_preview_from_content
    content = _fix_unquoted_diagram(content)
    content = _fix_folded_blocks_with_tags(content)
    content = _fix_bare_expressions(content)
    content = _fix_parameters_indentation(content)

    # 2. Parse YAML
    try:
        parsed = load_template_yaml(content)
    except Exception as e:
        return {
            "ok": False,
            "preview": {
                "question": "",
                "answers": [],
                "solution": "",
                "diagram_svg": "",
                "diagram_code": "",
                "substituted_yaml": content,
                "params": {},
                "errors": [f"YAML error: {str(e)}"]
            },
            "error": f"YAML error: {str(e)}"
        }

    # 3. Validate
    errors = validate_template(parsed)
    if errors:
        return {
            "ok": False,
            "preview": parsed,
            "error": errors
        }

    # 4. Render preview
    try:
        preview = render_template_preview(parsed, template_id=template_id)

        # Always include substituted YAML
        if "substituted_yaml" not in preview:
            preview["substituted_yaml"] = yaml.safe_dump(preview.get("full_yaml", parsed))

        # preview["substituted_yaml"] = yaml.safe_dump(parsed)

        # Inject metadata
        preview["skill"] = template_obj.skill.description if template_obj.skill else None
        preview["grade"] = template_obj.grade
        preview["difficulty"] = template_obj.difficulty

        # Inject linked knowledge items (rendered)
        knowledge_items = []
        for k in template_obj.knowledge_items.all():
            svg = ""
            if k.diagram and k.diagram.strip() and k.diagram.strip().lower() != "none":
                try:
                    from .diagram.engine import render_diagram_from_code
                    svg = render_diagram_from_code(k.diagram)
                except Exception:
                    pass
            knowledge_items.append({
                "id": k.id,
                "title": k.title,
                "text": k.text,
                "text_2": k.text_2,
                "diagram_svg": svg,
            })
        preview["knowledge_items"] = knowledge_items

        return {
            "ok": True,
            "preview": preview,
            "error": None
        }

    except Exception as e:
        tb = _traceback.format_exc()
        msg = f"{type(e).__name__}: {e}\n\n{tb}"
        return {
            "ok": False,
            "preview": {
                "question": "",
                "answers": [],
                "solution": "",
                "diagram_svg": "",
                "diagram_code": "",
                "substituted_yaml": content,
                "params": {},
                "errors": [msg]
            },
            "error": msg
        }


def generate_preview_from_template_id(template_id: int):
    # 1. Load template
    try:
        template_obj = Template.objects.select_related("skill_detail").get(pk=template_id)
    except Template.DoesNotExist:
        return {
            "ok": False,
            "preview": None,
            "error": f"Template {template_id} not found"
        }

    content = template_obj.content

    # 2. Parse YAML
    try:
        parsed = load_template_yaml(content)
    except Exception as e:
        return {
            "ok": False,
            "preview": {
                "question": "",
                "answers": [],
                "solution": "",
                "diagram_svg": "",
                "diagram_code": "",
                "substituted_yaml": content,
                "params": {},
                "errors": [f"YAML error: {str(e)}"]
            },
            "error": f"YAML error: {str(e)}"
        }

    # 3. Validate
    errors = validate_template(parsed)
    if errors:
        return {
            "ok": False,
            "preview": parsed,
            "error": errors
        }

    # 4. Render preview (retry loop)
    MAX_ATTEMPTS = 5
    last_error = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            preview = render_template_preview(parsed, template_id=template_obj.id)

            # Inject metadata
            preview["skill"] = template_obj.skill.description if template_obj.skill else None
            preview["grade"] = template_obj.grade
            preview["difficulty"] = template_obj.difficulty

            return {
                "ok": True,
                "preview": preview,
                "error": None
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            last_error = traceback.format_exc()

    # 5. All attempts failed
    return {
        "ok": False,
        "preview": {
            "question": "",
            "answers": [],
            "solution": "",
            "diagram_svg": "",
            "diagram_code": "",
            "substituted_yaml": content,
            "params": {},
            "errors": [f"Failed after {MAX_ATTEMPTS} attempts: {last_error}"]
        },
        "error": f"Failed after {MAX_ATTEMPTS} attempts: {last_error}"
    }

def get_translated_template(template, student):
    """Return the translated Template for this student's language preference.

    Looks up the student's UserPreference for 'language'. If it's not 'en',
    finds or creates a sister Template with the translated content.
    Falls back to the original on any error.
    """
    try:
        lang_pref = UserPreference.objects.filter(user=student, key='language').first()
        language = lang_pref.value if lang_pref else 'en'
        if not language or language == 'en':
            return template

        # Check for existing translation
        existing = Template.objects.filter(
            parent_template=template, language=language, validated=True
        ).first()
        if existing:
            return existing

        # Create via AI
        from .ai import translate_template_content
        translated_content = translate_template_content(template.content, language)

        translation = Template.objects.create(
            name=template.name,
            description=template.description,
            content=translated_content,
            topic=template.topic,
            subtopic=template.subtopic,
            grade=template.grade,
            difficulty=template.difficulty,
            tags=template.tags,
            group=template.group,
            curriculum=template.curriculum,
            skill_detail=template.skill_detail,
            validated=True,
            status=template.status,
            version=template.version,
            language=language,
            parent_template=template,
        )
        return translation
    except Exception:
        return template  # Never block a question due to translation failure


def generate_first_question(request):
    print("Generating first question")
    student_id = request.data.get("student_id")
    skill_id = request.data.get("skill_id")
    print(f"  student_id={student_id!r}  skill_id={skill_id!r}")

    # ---------------------------------------------------------
    # VALIDATE STUDENT
    # ---------------------------------------------------------
    try:
        user = User.objects.get(pk=student_id)
        student = user.get_student_profile()
    except User.DoesNotExist:
        print(f"  Student not found: {student_id!r}")
        return Response({"error": "Student not found"}, status=404)

    if student is None:
        print(f"  No student profile for user {student_id!r}")
        return Response({"error": "Student profile not found"}, status=404)

    # ---------------------------------------------------------
    # VALIDATE SKILL
    # ---------------------------------------------------------
    try:
        skill = Skill.objects.get(pk=skill_id)
    except Skill.DoesNotExist:
        print(f"  Skill not found: {skill_id!r}")
        return Response({"error": "Skill not found"}, status=404)

    print(f"  skill={skill.code!r}  year_level={student.year_level!r}")

    # ---------------------------------------------------------
    # DETERMINE DIFFICULTY FROM COMPETENCY
    # ---------------------------------------------------------
    from .competency import get_student_question_difficulty
    difficulty = get_student_question_difficulty(user, skill.code)
    print(f"  difficulty={difficulty!r}")

    # ---------------------------------------------------------
    # SELECT A TEMPLATE OF THAT DIFFICULTY
    # Templates are linked to SkillDetail children of the skill, so search
    # both directly and via children. Fall back progressively if an exact
    # difficulty match isn't available.
    # ---------------------------------------------------------
    from django.db.models import Q
    # Only English (parent) templates — exclude translated sisters so the pool
    # contains stable English IDs that get_translated_template can translate at
    # render time.  Translated templates have language != 'en'.
    base_qs = Template.objects.filter(
        Q(skill_detail=skill) | Q(skill_detail__parent=skill),
        language='en',
    )
    total = base_qs.count()
    print(f"  templates for skill: {total}")

    # Build the pool for this session: all templates at the chosen difficulty
    # (fall back progressively so we always have a pool to work from)
    pool_qs = (
        base_qs.filter(grade=student.year_level, difficulty__iexact=difficulty, validated=True)
        or base_qs.filter(grade=student.year_level, validated=True)
        or base_qs.filter(validated=True)
    )
    session_template_ids = list(pool_qs.values_list('id', flat=True))

    template = pool_qs.order_by("?").first()

    if not template:
        print(f"  No templates found for skill {skill_id!r}")
        return Response(
            {"error": f"No templates available for skill '{skill.description}'"},
            status=404
        )
    print(f"  selected template id={template.id}")
    original_template_id = template.id  # keep for session tracking

    # Translate for the student's preferred language
    template = get_translated_template(template, user)

    # ---------------------------------------------------------
    # GENERATE PREVIEW FOR THE FIRST QUESTION
    # ---------------------------------------------------------
    preview = generate_preview_from_template_id(template.id)

    if not preview["ok"]:
        return Response(
            {"error": preview["error"], "template_id": template.id},
            status=500
        )

    next_question = preview["preview"]
    next_question["template_id"] = original_template_id  # track by English ID
    next_question["skill"] = skill.description

    # ---------------------------------------------------------
    # RETURN FIRST QUESTION
    # ---------------------------------------------------------
    from .competency import get_student_question_difficulty as _gd, level_to_label as _ltl
    from .models import StudentSkillCompetency
    comp = StudentSkillCompetency.objects.filter(student=user, skill=skill).values_list('level', flat=True).first()
    comp_level = comp if comp is not None else 0
    return Response(
        {
            "ok": True,
            "template_id": original_template_id,  # always the English template ID
            "mastery": comp_level,
            "competence_label": _ltl(comp_level),
            "next_difficulty": difficulty,
            "next_question": next_question,
            "session_template_ids": session_template_ids,
        }
    )

def sanitize(obj):
    if obj is ...:
        return None
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj

def mastery_label(mastery) -> str:
    """Compatibility shim — maps the old 0–15 mastery float to the new level labels."""
    from .competency import level_to_label
    # Old mastery 0-15 → levels 0-4 (easy/med/hard thresholds)
    if mastery <= 4:
        return level_to_label(1)   # Developing
    if mastery <= 9:
        return level_to_label(3)   # Emerging
    if mastery <= 14:
        return level_to_label(4)   # Competent
    return level_to_label(6)       # Mastered
