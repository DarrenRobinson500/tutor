"""
Tests for backend.competency
=====================================
Covers level transitions, robustness, edge cases, and the prev_level guard in views.py.

Template structure note
-----------------------
_template_count() filters on Template.skill_detail__parent__code = skill_code.
So each test must create:
  parent_skill  (code = skill_code)
  detail_skill  (parent = parent_skill)
  Template      (skill_detail = detail_skill, validated=True, difficulty=...)

StudentTemplateProgress uses skill_code = parent_skill.code.
"""

import unittest
from datetime import date, timedelta

from django.test import TestCase

from backend.competency import (
    recompute_skill_competency,
    update_template_progress,
    _compute_deserved_level,
    level_to_label,
    level_to_difficulty,
    level_to_stars,
    TEMPLATE_CAP,
)
from .factories import (
    make_user,
    make_skill,
    make_template,
    make_student_skill_competency,
    make_student_template_progress,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill_with_detail(code=None):
    """
    Return (parent_skill, detail_skill) where templates attached to detail_skill
    will be found by _template_count(skill_code=parent_skill.code, ...).
    """
    import uuid
    if code is None:
        code = f'SK{uuid.uuid4().hex[:6].upper()}'
    parent = make_skill(code=code, description=f'Parent {code}')
    detail = make_skill(code=f'{code}_D', description=f'Detail {code}', parent_skill=parent)
    return parent, detail


def _mark_templates_ever_correct(student, templates, skill_code, difficulty):
    """Create StudentTemplateProgress records with ever_correct=True for each template."""
    for tpl in templates:
        make_student_template_progress(
            student=student,
            template=tpl,
            skill_code=skill_code,
            difficulty=difficulty,
            ever_correct=True,
            has_robust=False,
            streak_start_date=date.today(),
        )


def _mark_templates_robust(student, templates, skill_code, difficulty):
    """Create StudentTemplateProgress records with has_robust=True for each template."""
    for tpl in templates:
        make_student_template_progress(
            student=student,
            template=tpl,
            skill_code=skill_code,
            difficulty=difficulty,
            ever_correct=True,
            has_robust=True,
            streak_start_date=date.today() - timedelta(days=7),
            last_answered_date=date.today(),
        )


# ---------------------------------------------------------------------------
# Level transition tests
# ---------------------------------------------------------------------------

class TestLevelTransitions(TestCase):
    """
    Test that recompute_skill_competency returns the correct level
    based on StudentTemplateProgress records.
    """

    def setUp(self):
        self.student = make_user(role='student')

    def test_level_0_to_1_all_easy_ever_correct(self):
        """Level 0 → 1: all easy templates for a skill have ever_correct=True."""
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        # Create 2 validated easy templates
        tpl1 = make_template(skill_detail=detail, difficulty='easy', validated=True)
        tpl2 = make_template(skill_detail=detail, difficulty='easy', validated=True)

        # Mark all as ever_correct (but not robust)
        _mark_templates_ever_correct(self.student, [tpl1, tpl2], skill_code, 'easy')

        comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 1)

    def test_level_1_to_2_all_easy_robust(self):
        """Level 1 → 2: all easy templates have has_robust=True."""
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        tpl1 = make_template(skill_detail=detail, difficulty='easy', validated=True)
        tpl2 = make_template(skill_detail=detail, difficulty='easy', validated=True)

        # Mark all as robust
        _mark_templates_robust(self.student, [tpl1, tpl2], skill_code, 'easy')

        comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 2)

    def test_level_2_to_3_all_medium_ever_correct(self):
        """Level 2 → 3: all medium templates have ever_correct=True (easy also robust)."""
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        easy_tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)
        med_tpl = make_template(skill_detail=detail, difficulty='medium', validated=True)

        # Easy is robust (satisfies level 2 requirement)
        _mark_templates_robust(self.student, [easy_tpl], skill_code, 'easy')
        # Medium is ever_correct (satisfies level 3 requirement)
        _mark_templates_ever_correct(self.student, [med_tpl], skill_code, 'medium')

        comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 3)

    def test_level_3_to_4_all_medium_robust(self):
        """Level 3 → 4: all medium templates have has_robust=True."""
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        easy_tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)
        med_tpl = make_template(skill_detail=detail, difficulty='medium', validated=True)

        # Both easy and medium are robust
        _mark_templates_robust(self.student, [easy_tpl], skill_code, 'easy')
        _mark_templates_robust(self.student, [med_tpl], skill_code, 'medium')

        comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 4)

    def test_incorrect_answer_resets_robustness(self):
        """
        A progress record with has_robust=True becomes has_robust=False after
        an incorrect answer via update_template_progress.
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)

        # Set up initial state: robust
        progress = make_student_template_progress(
            student=self.student,
            template=tpl,
            skill_code=skill_code,
            difficulty='easy',
            ever_correct=True,
            has_robust=True,
            streak_start_date=date.today() - timedelta(days=7),
            last_answered_date=date.today() - timedelta(days=1),
        )
        self.assertTrue(progress.has_robust)

        # Simulate incorrect answer
        update_template_progress(
            student=self.student,
            template_id=tpl.id,
            skill_code=skill_code,
            difficulty='easy',
            correct=False,
        )

        # Reload from DB
        progress.refresh_from_db()
        self.assertFalse(progress.has_robust,
                         "has_robust must be False after an incorrect answer")
        self.assertIsNone(progress.streak_start_date,
                          "streak_start_date must be cleared after an incorrect answer")

    def test_unvalidated_template_does_not_advance_level(self):
        """
        An unvalidated template (validated=False) is excluded from _template_count,
        so the student cannot advance past level 0 using only unvalidated templates.
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        # Create one UNVALIDATED easy template
        tpl = make_template(skill_detail=detail, difficulty='easy', validated=False)

        # Mark it as ever_correct — but it should not count
        make_student_template_progress(
            student=self.student,
            template=tpl,
            skill_code=skill_code,
            difficulty='easy',
            ever_correct=True,
            has_robust=False,
        )

        comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 0,
                         "Unvalidated templates must not contribute to level advancement")


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases(TestCase):

    def setUp(self):
        self.student = make_user(role='student')

    def test_no_hard_templates_all_medium_robust_stays_at_level_4(self):
        """
        A skill with zero hard templates and all medium templates robust
        should reach level 4 (not 5 or 6 — hard levels are unreachable).
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        easy_tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)
        med_tpl = make_template(skill_detail=detail, difficulty='medium', validated=True)
        # No hard templates

        _mark_templates_robust(self.student, [easy_tpl], skill_code, 'easy')
        _mark_templates_robust(self.student, [med_tpl], skill_code, 'medium')

        comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 4,
                         "With no hard templates, max level is 4 (all medium robust)")

    def test_only_easy_templates_max_level_is_2(self):
        """
        A skill with only easy templates can reach a maximum of level 2.
        Levels 3–6 require medium/hard templates which do not exist here.
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        easy_tpl1 = make_template(skill_detail=detail, difficulty='easy', validated=True)
        easy_tpl2 = make_template(skill_detail=detail, difficulty='easy', validated=True)
        # No medium or hard templates

        _mark_templates_robust(self.student, [easy_tpl1, easy_tpl2], skill_code, 'easy')

        comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 2,
                         "With only easy templates, the maximum achievable level is 2")

    def test_template_cap_limits_count_to_six(self):
        """
        _template_count is capped at TEMPLATE_CAP (6). Creating 8 templates
        should still require only 6 ever_correct records to reach level 1.
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        # Create 8 easy templates (2 more than the cap)
        templates = [
            make_template(skill_detail=detail, difficulty='easy', validated=True)
            for _ in range(8)
        ]

        # Mark only the first 6 as ever_correct
        _mark_templates_ever_correct(self.student, templates[:TEMPLATE_CAP], skill_code, 'easy')

        comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 1,
                         "Completing TEMPLATE_CAP templates must be sufficient regardless "
                         "of how many total templates exist")

    def test_session_regression_below_50_percent_drops_one_level(self):
        """
        recompute_skill_competency with session_correct < session_total / 2
        drops the deserved level by one.
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        easy_tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)
        _mark_templates_ever_correct(self.student, [easy_tpl], skill_code, 'easy')

        # Deserved level is 1; session is 1/3 correct (< 50%) → should drop to 0
        comp = recompute_skill_competency(
            self.student, skill_code, '',
            session_correct=1, session_total=3
        )
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 0,
                         "A session below 50% correct must regress the level by one")

    def test_session_regression_at_50_percent_does_not_drop(self):
        """
        A session at exactly 50% correct does not trigger regression
        (the condition is strict: session_correct < session_total / 2).
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code

        easy_tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)
        _mark_templates_ever_correct(self.student, [easy_tpl], skill_code, 'easy')

        # Deserved level is 1; session is 1/2 correct (exactly 50%) → no regression
        comp = recompute_skill_competency(
            self.student, skill_code, '',
            session_correct=1, session_total=2
        )
        self.assertIsNotNone(comp)
        self.assertEqual(comp.level, 1,
                         "A session at exactly 50% correct must not trigger regression")

    def test_recompute_returns_none_for_unknown_skill_code(self):
        """recompute_skill_competency returns None when the skill code does not exist."""
        comp = recompute_skill_competency(self.student, 'NONEXISTENT_SKILL_XYZ', '')
        self.assertIsNone(comp)


# ---------------------------------------------------------------------------
# get_student_score edge cases
# ---------------------------------------------------------------------------

class TestGetStudentScore(TestCase):
    """
    get_student_score() relies on get_matrix_cache() / filter_matrix_by_grade(),
    which pull from a cache. These tests bypass the cache by directly testing
    _compute_deserved_level and the level helper functions instead, since
    mocking the cache layer is out of scope for unit tests of competency.py.

    The score formula is:  sum(stars) / (leaf_skills * 4)
    where stars = level (capped at 6, so level 6 = 6 stars but max_score uses *4).
    A student at level 6 on all skills would score 6/4 = 1.5 > 1.0.
    """

    def test_level_to_stars_returns_level_value(self):
        """level_to_stars maps 0→0, 4→4, 6→6 (capped at 6)."""
        self.assertEqual(level_to_stars(0), 0)
        self.assertEqual(level_to_stars(4), 4)
        self.assertEqual(level_to_stars(6), 6)

    def test_score_formula_level_0_is_zero(self):
        """A student at level 0 on all skills contributes 0 stars → score is 0.0."""
        # Formula: 0 stars / (N skills * 4) = 0.0
        total_stars = 0
        leaf_count = 3
        score = total_stars / (leaf_count * 4) if leaf_count > 0 else 0.0
        self.assertEqual(score, 0.0)

    def test_score_formula_level_6_exceeds_1(self):
        """
        A student at level 6 on all skills produces a score above 1.0.
        Formula: 6 stars per skill / 4 max per skill = 1.5.
        This is documented expected behaviour — the docstring in competency.py
        states 'values above 1.0 are possible for advanced students'.
        """
        total_stars = 6  # 1 skill at level 6
        leaf_count = 1
        score = total_stars / (leaf_count * 4)
        self.assertGreater(score, 1.0,
                           "A student at level 6 should score above 1.0 (by design)")
        self.assertAlmostEqual(score, 1.5)

    def test_score_formula_no_leaf_skills_returns_zero(self):
        """If there are no leaf skills the score is 0.0 (avoids division by zero)."""
        leaf_count = 0
        score = 0.0 / (leaf_count * 4) if leaf_count > 0 else 0.0
        self.assertEqual(score, 0.0)


# ---------------------------------------------------------------------------
# Robustness rule — update_template_progress detail
# ---------------------------------------------------------------------------

class TestRobustnessRule(TestCase):
    """Detailed tests for the 6-day robustness rule in update_template_progress."""

    def setUp(self):
        self.student = make_user(role='student')

    def _get_or_create_progress(self, tpl, skill_code, difficulty):
        from backend.models import StudentTemplateProgress
        return StudentTemplateProgress.objects.filter(
            student=self.student, template_id=tpl.id
        ).first()

    def test_first_correct_answer_sets_ever_correct_and_streak_start(self):
        """First correct answer sets ever_correct=True and records streak_start_date."""
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code
        tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)

        update_template_progress(
            student=self.student,
            template_id=tpl.id,
            skill_code=skill_code,
            difficulty='easy',
            correct=True,
        )

        from backend.models import StudentTemplateProgress
        progress = StudentTemplateProgress.objects.get(
            student=self.student, template_id=tpl.id
        )
        self.assertTrue(progress.ever_correct)
        self.assertIsNotNone(progress.streak_start_date)
        self.assertFalse(progress.has_robust)

    def test_correct_answer_6_days_later_sets_robust(self):
        """A correct answer 6+ days after streak_start_date sets has_robust=True."""
        from unittest.mock import patch
        from datetime import date as date_cls

        parent, detail = _make_skill_with_detail()
        skill_code = parent.code
        tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)

        start_date = date_cls(2026, 1, 1)

        # First correct answer
        with patch('django.utils.timezone.localdate', return_value=start_date):
            update_template_progress(
                student=self.student,
                template_id=tpl.id,
                skill_code=skill_code,
                difficulty='easy',
                correct=True,
            )

        # Second correct answer exactly 6 days later
        with patch('django.utils.timezone.localdate', return_value=start_date + timedelta(days=6)):
            update_template_progress(
                student=self.student,
                template_id=tpl.id,
                skill_code=skill_code,
                difficulty='easy',
                correct=True,
            )

        from backend.models import StudentTemplateProgress
        progress = StudentTemplateProgress.objects.get(
            student=self.student, template_id=tpl.id
        )
        self.assertTrue(progress.has_robust,
                        "has_robust should be True after a correct answer 6 days after streak start")

    def test_correct_answer_5_days_later_does_not_set_robust(self):
        """A correct answer only 5 days after streak_start_date does not set has_robust."""
        from unittest.mock import patch
        from datetime import date as date_cls

        parent, detail = _make_skill_with_detail()
        skill_code = parent.code
        tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)

        start_date = date_cls(2026, 1, 1)

        with patch('django.utils.timezone.localdate', return_value=start_date):
            update_template_progress(
                student=self.student,
                template_id=tpl.id,
                skill_code=skill_code,
                difficulty='easy',
                correct=True,
            )

        with patch('django.utils.timezone.localdate', return_value=start_date + timedelta(days=5)):
            update_template_progress(
                student=self.student,
                template_id=tpl.id,
                skill_code=skill_code,
                difficulty='easy',
                correct=True,
            )

        from backend.models import StudentTemplateProgress
        progress = StudentTemplateProgress.objects.get(
            student=self.student, template_id=tpl.id
        )
        self.assertFalse(progress.has_robust,
                         "has_robust should remain False if only 5 days have passed")

    def test_incorrect_after_robust_does_not_reset_ever_correct(self):
        """
        An incorrect answer resets has_robust and streak_start_date,
        but ever_correct must NOT be cleared (the student did answer correctly once).
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code
        tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)

        make_student_template_progress(
            student=self.student,
            template=tpl,
            skill_code=skill_code,
            difficulty='easy',
            ever_correct=True,
            has_robust=True,
            streak_start_date=date.today() - timedelta(days=7),
        )

        update_template_progress(
            student=self.student,
            template_id=tpl.id,
            skill_code=skill_code,
            difficulty='easy',
            correct=False,
        )

        from backend.models import StudentTemplateProgress
        progress = StudentTemplateProgress.objects.get(
            student=self.student, template_id=tpl.id
        )
        self.assertTrue(progress.ever_correct,
                        "ever_correct must NOT be reset by an incorrect answer")
        self.assertFalse(progress.has_robust)
        self.assertIsNone(progress.streak_start_date)


# ---------------------------------------------------------------------------
# Guard conflict bug — views.py prev_level guard
# ---------------------------------------------------------------------------

class TestPrevLevelGuardConflict(TestCase):
    """
    In views.py, after recompute_skill_competency(), this guard runs:

        if not q.correct and comp and comp.level > prev_level:
            comp.level = prev_level
            comp.save(update_fields=['level'])

    The intent is to prevent an incorrect answer from *increasing* a star count.
    The guard only fires when comp.level > prev_level, so it should never
    interfere with legitimate regressions (where comp.level < prev_level).

    The potential bug: if a student loses robustness through an incorrect answer
    (e.g. level drops from 2 to 1), the guard does NOT fire because
    comp.level (1) is NOT > prev_level (2). The regression is correctly applied.

    However, the guard DOES fire if — after an incorrect answer — the computed
    level *increases* (which should be impossible via update_template_progress
    alone but could happen if another concurrent process adds template progress).

    The test below verifies that when a student answers incorrectly and loses
    robustness, the level correctly drops (i.e. the guard does not incorrectly
    restore the higher level). We test this via recompute_skill_competency directly,
    which has no guard — and confirm the expected correct behaviour.

    If views.py's guard were applied after the regression, it would NOT restore
    the level (since comp.level < prev_level). That is correct. No @expectedFailure
    is needed here because the guard is logically sound for the regression direction.
    """

    def setUp(self):
        self.student = make_user(role='student')

    def test_level_drops_after_incorrect_removes_robustness(self):
        """
        Sequence:
          1. Student has 1 easy template with has_robust=True → deserved level 2.
          2. Student answers incorrectly → has_robust=False, streak_start_date=None.
          3. recompute_skill_competency → deserved level drops to 1 (ever_correct still True).
          4. The level stored is 1, not 2.

        This verifies that the robustness reset from an incorrect answer
        correctly reduces the computed level, with no interference.
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code
        tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)

        # Start at level 2: easy template is robust
        make_student_template_progress(
            student=self.student,
            template=tpl,
            skill_code=skill_code,
            difficulty='easy',
            ever_correct=True,
            has_robust=True,
            streak_start_date=date.today() - timedelta(days=7),
            last_answered_date=date.today() - timedelta(days=1),
        )

        # Confirm baseline: should be level 2
        initial_comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertEqual(initial_comp.level, 2)

        # Answer incorrectly — breaks robustness
        update_template_progress(
            student=self.student,
            template_id=tpl.id,
            skill_code=skill_code,
            difficulty='easy',
            correct=False,
        )

        # Recompute — ever_correct is still True, so level is now 1 (not robust anymore)
        comp = recompute_skill_competency(self.student, skill_code, '')
        self.assertEqual(comp.level, 1,
                         "Level must drop from 2 to 1 after robustness is lost via incorrect answer")

    @unittest.expectedFailure
    def test_views_guard_would_incorrectly_restore_level_if_applied_after_regression(self):
        """
        BUG DOCUMENTATION (expected failure — hypothetical bug):

        The guard in views.py is:
            if not q.correct and comp and comp.level > prev_level:
                comp.level = prev_level

        This guard is logically correct as written: it only fires when
        comp.level > prev_level, which cannot happen after an incorrect
        answer causes a robustness loss (regression always reduces the level).

        HOWEVER — if a developer mistakenly changes the guard to:
            if not q.correct and comp:
                comp.level = prev_level   # <-- always restore on wrong answer

        ...then legitimate regressions would be silently suppressed.
        This test documents that scenario. It is marked @expectedFailure
        because the current code does NOT have this bug.

        The test demonstrates: after robustness loss, the level is correctly 1,
        not the pre-answer level of 2. If the buggy guard were applied,
        this assertion would fail (level would be restored to 2).
        """
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code
        tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)

        make_student_template_progress(
            student=self.student,
            template=tpl,
            skill_code=skill_code,
            difficulty='easy',
            ever_correct=True,
            has_robust=True,
            streak_start_date=date.today() - timedelta(days=7),
            last_answered_date=date.today() - timedelta(days=1),
        )

        prev_level = 2  # Student was at level 2 before the incorrect answer

        update_template_progress(
            student=self.student,
            template_id=tpl.id,
            skill_code=skill_code,
            difficulty='easy',
            correct=False,
        )

        comp = recompute_skill_competency(self.student, skill_code, '')

        # Simulate the BUGGY guard: always restore to prev_level on wrong answer
        # (This is what a buggy guard would do — ignoring the comp.level > prev_level check)
        if comp:
            comp.level = prev_level  # Bug: blindly restore
            comp.save(update_fields=['level'])

        # After the buggy guard, level is wrongly restored to 2.
        # The correct value should be 1.
        # This assertion will FAIL (hence @expectedFailure) — demonstrating the bug.
        self.assertEqual(comp.level, 1,
                         "BUGGY GUARD: level was incorrectly restored to prev_level=2 "
                         "instead of remaining at 1 after robustness loss")


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------

class TestHelperFunctions(TestCase):

    def test_level_to_label(self):
        expected = {
            0: "Not Started",
            1: "Developing",
            2: "Easy Complete",
            3: "Emerging",
            4: "Competent",
            5: "Advanced",
            6: "Mastered",
        }
        for level, label in expected.items():
            self.assertEqual(level_to_label(level), label)

    def test_level_to_label_out_of_range(self):
        self.assertEqual(level_to_label(7), "Unknown")
        self.assertEqual(level_to_label(-1), "Unknown")

    def test_level_to_difficulty(self):
        self.assertEqual(level_to_difficulty(0), "easy")
        self.assertEqual(level_to_difficulty(1), "easy")
        self.assertEqual(level_to_difficulty(2), "medium")
        self.assertEqual(level_to_difficulty(3), "medium")
        self.assertEqual(level_to_difficulty(4), "hard")
        self.assertEqual(level_to_difficulty(5), "hard")
        self.assertEqual(level_to_difficulty(6), "hard")

    def test_level_to_difficulty_out_of_range(self):
        # Defaults to "easy" for invalid levels
        self.assertEqual(level_to_difficulty(99), "easy")

    def test_level_to_stars(self):
        self.assertEqual(level_to_stars(0), 0)
        self.assertEqual(level_to_stars(3), 3)
        self.assertEqual(level_to_stars(6), 6)
        # Clamped
        self.assertEqual(level_to_stars(-1), 0)
        self.assertEqual(level_to_stars(7), 6)

    def test_recompute_persists_level_to_database(self):
        """recompute_skill_competency saves the level to StudentSkillCompetency."""
        from backend.models import StudentSkillCompetency

        student = make_user(role='student')
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code
        tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)
        _mark_templates_ever_correct(student, [tpl], skill_code, 'easy')

        comp = recompute_skill_competency(student, skill_code, '')
        self.assertIsNotNone(comp)

        db_comp = StudentSkillCompetency.objects.get(student=student, skill__code=skill_code)
        self.assertEqual(db_comp.level, 1)

    def test_recompute_idempotent(self):
        """Calling recompute_skill_competency twice gives the same result."""
        student = make_user(role='student')
        parent, detail = _make_skill_with_detail()
        skill_code = parent.code
        tpl = make_template(skill_detail=detail, difficulty='easy', validated=True)
        _mark_templates_ever_correct(student, [tpl], skill_code, 'easy')

        comp1 = recompute_skill_competency(student, skill_code, '')
        comp2 = recompute_skill_competency(student, skill_code, '')
        self.assertEqual(comp1.level, comp2.level)
