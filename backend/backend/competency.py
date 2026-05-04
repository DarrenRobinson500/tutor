"""
Student Competency System
=========================
7-level (0–6) per-skill competency based on template completion history.

Level | Label         | Difficulty served | Requirement
------+---------------+-------------------+----------------------------------------------
  0   | Not Started   | easy              | No correct answers yet
  1   | Developing    | easy              | All easy templates answered correctly once
  2   | Easy Complete | medium            | All easy templates robust (6-day gap)
  3   | Emerging      | medium            | All medium templates answered correctly once
  4   | Competent     | hard              | All medium templates robust (6-day gap)
  5   | Advanced      | hard              | All hard templates answered correctly once
  6   | Mastered      | hard              | All hard templates robust (6-day gap)

Template counts are capped at TEMPLATE_CAP (6) per skill/difficulty.
Total score = sum(stars) / (skills × 4)  — can exceed 100 % at levels 5–6.
"""

from datetime import timedelta

TEMPLATE_CAP = 6  # maximum templates counted per skill/difficulty

# (level, label, difficulty_to_serve)
LEVEL_DATA = [
    (0, "Not Started",    "easy"),
    (1, "Developing",     "easy"),
    (2, "Easy Complete",  "medium"),
    (3, "Emerging",       "medium"),
    (4, "Competent",      "hard"),
    (5, "Advanced",       "hard"),
    (6, "Mastered",       "hard"),
]


def level_to_label(level: int) -> str:
    if 0 <= level <= 6:
        return LEVEL_DATA[level][1]
    return "Unknown"


def level_to_difficulty(level: int) -> str:
    if 0 <= level <= 6:
        return LEVEL_DATA[level][2]
    return "easy"


def level_to_stars(level: int) -> int:
    return max(0, min(6, level))


# ---------------------------------------------------------------------------
# Template-progress update (called per answered question)
# ---------------------------------------------------------------------------

def update_template_progress(student, template_id: int, skill_code: str,
                              difficulty: str, correct: bool) -> None:
    """
    Update StudentTemplateProgress after a student answers a template.

    Robust rule: the student must answer the template correctly in two separate
    sessions at least 6 days apart, with no incorrect answers in between.
    """
    from django.utils import timezone
    from .models import StudentTemplateProgress

    today = timezone.localdate()

    progress, _ = StudentTemplateProgress.objects.get_or_create(
        student=student,
        template_id=template_id,
        defaults={'skill_code': skill_code, 'difficulty': difficulty.lower()},
    )

    if correct:
        if not progress.ever_correct:
            # First-ever correct answer — start the robustness streak
            progress.ever_correct = True
            progress.streak_start_date = today
        elif progress.streak_start_date is not None and not progress.has_robust:
            # Streak is active — check if 6+ days have passed
            if today >= progress.streak_start_date + timedelta(days=6):
                progress.has_robust = True
        # If has_robust is already True, another correct answer doesn't change anything
    else:
        # Incorrect — break the streak; must start over to earn robustness
        progress.streak_start_date = None
        progress.has_robust = False

    progress.last_answered_date = today
    progress.save()


# ---------------------------------------------------------------------------
# Helpers: counting template evidence
# ---------------------------------------------------------------------------

def _template_count(skill_code: str, difficulty: str, grade: str) -> int:
    """Validated templates for a skill/difficulty/grade, capped at TEMPLATE_CAP."""
    from .models import Template
    count = Template.objects.filter(
        skill_detail__parent__code=skill_code,
        difficulty__iexact=difficulty,
        validated=True,
    ).count()
    return min(count, TEMPLATE_CAP)


def _robust_count(student, skill_code: str, difficulty: str) -> int:
    from .models import StudentTemplateProgress
    return StudentTemplateProgress.objects.filter(
        student=student,
        skill_code=skill_code,
        difficulty__iexact=difficulty,
        has_robust=True,
    ).count()


def _ever_correct_count(student, skill_code: str, difficulty: str) -> int:
    from .models import StudentTemplateProgress
    return StudentTemplateProgress.objects.filter(
        student=student,
        skill_code=skill_code,
        difficulty__iexact=difficulty,
        ever_correct=True,
    ).count()


# ---------------------------------------------------------------------------
# Level computation
# ---------------------------------------------------------------------------

def _compute_deserved_level(student, skill_code: str, grade: str) -> int:
    """Return the level (0–6) the student has earned based on template progress."""
    hard_total  = _template_count(skill_code, 'hard',   grade)
    med_total   = _template_count(skill_code, 'medium', grade)
    easy_total  = _template_count(skill_code, 'easy',   grade)

    # Check from highest to lowest.
    # Odd levels (1, 3, 5) require ALL templates at that difficulty answered
    # correctly at least once (capped at TEMPLATE_CAP).
    # Even levels (2, 4, 6) additionally require the robust (6-day) condition.
    if hard_total > 0:
        if _robust_count(student, skill_code, 'hard') >= hard_total:
            return 6
        if _ever_correct_count(student, skill_code, 'hard') >= hard_total:
            return 5

    if med_total > 0:
        if _robust_count(student, skill_code, 'medium') >= med_total:
            return 4
        if _ever_correct_count(student, skill_code, 'medium') >= med_total:
            return 3

    if easy_total > 0:
        if _robust_count(student, skill_code, 'easy') >= easy_total:
            return 2
        if _ever_correct_count(student, skill_code, 'easy') >= easy_total:
            return 1

    return 0


def recompute_skill_competency(student, skill_code: str, grade: str,
                                session_correct: int = None,
                                session_total: int = None):
    """
    Recompute and save the student's competency level for a skill.

    If session_correct / session_total are supplied and the ratio is < 50 %,
    the student regresses one level (minimum 0).

    Returns the updated StudentSkillCompetency instance, or None if the skill
    cannot be found.
    """
    from .models import Skill, StudentSkillCompetency

    skill = Skill.objects.filter(code=skill_code).first()
    if not skill:
        return None

    deserved = _compute_deserved_level(student, skill_code, grade)

    # Regression: < 50 % session performance → drop one level
    if (session_correct is not None and session_total is not None
            and session_total > 0
            and session_correct < session_total / 2):
        deserved = max(0, deserved - 1)

    comp, _ = StudentSkillCompetency.objects.get_or_create(
        student=student, skill=skill, defaults={'level': 0}
    )
    comp.level = deserved
    comp.save(update_fields=['level', 'updated_at'])
    return comp


# ---------------------------------------------------------------------------
# Public helpers used by views
# ---------------------------------------------------------------------------

def get_student_question_difficulty(student, skill_code: str) -> str:
    """Return the difficulty to serve next for a student/skill combination."""
    from .models import StudentSkillCompetency
    level = (
        StudentSkillCompetency.objects
        .filter(student=student, skill__code=skill_code)
        .values_list('level', flat=True)
        .first()
    )
    return level_to_difficulty(level if level is not None else 0)


def get_student_score(student, grade: str) -> float:
    """
    Total score = sum(stars) / (skills × 4).
    Returns a float ≥ 0.0; values above 1.0 are possible for advanced students.
    """
    from .cache import get_matrix_cache, filter_matrix_by_grade
    from .models import StudentSkillCompetency

    matrix = get_matrix_cache()
    leaf_skills = [s for s in filter_matrix_by_grade(matrix, grade)
                   if s['children_count'] == 0]
    if not leaf_skills:
        return 0.0

    skill_ids = [s['id'] for s in leaf_skills]
    comp_map = {
        c.skill_id: c.level
        for c in StudentSkillCompetency.objects.filter(
            student=student, skill_id__in=skill_ids
        )
    }

    total_stars = sum(comp_map.get(sid, 0) for sid in skill_ids)
    max_score = len(leaf_skills) * 4
    return total_stars / max_score if max_score > 0 else 0.0
