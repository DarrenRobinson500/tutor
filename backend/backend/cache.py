from .models import *


# ----------- STUDENTS ------------------

STUDENTS_CACHE = {}

def build_student_summary(student):
    profile = student.get_student_profile()

    return {
        "user_id": student.id,
        "profile_id": profile.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "active": student.active,
        "email": student.email,
        "year_level": profile.year_level,
        "area_of_study": profile.area_of_study,
        "next_ad_hoc_booking": student.next_ad_hoc_booking(),
        "next_weekly_booking": student.next_weekly_booking(),
    }


def get_cached_students_for_tutor(tutor):
    global STUDENTS_CACHE
    tutor_id = tutor.id

    # Build fresh if missing
    if tutor_id not in STUDENTS_CACHE:
        links = TutorStudent.objects.filter(tutor=tutor).select_related(
            "student__student_profile"
        )

        data = []
        for link in links:
            student = link.student
            summary = student.to_dict()
            data.append(summary)

        STUDENTS_CACHE[tutor_id] = data

    return STUDENTS_CACHE[tutor_id]

def update_student_cache(student):
    global STUDENTS_CACHE

    profile = student.get_student_profile()
    tutor = student.get_tutor()
    if tutor is None:
        return
    updated_summary = profile.to_dict()

    # Only update if the tutor's list is already cached; otherwise let it be
    # built fresh on the next request (avoids a partial cache entry).
    if tutor.id not in STUDENTS_CACHE:
        return

    students = STUDENTS_CACHE[tutor.id]

    for i, entry in enumerate(students):
        if entry["user_id"] == student.id:
            students[i] = updated_summary
            return

    students.append(updated_summary)


def invalidate_students_cache_for_tutor(tutor_id):
    global STUDENTS_CACHE
    print("Invalidating student cache for tutor:", tutor_id)
    # STUDENTS_CACHE = {}
    if tutor_id in STUDENTS_CACHE:
        del STUDENTS_CACHE[tutor_id]


# ------------AD HOC SLOTS -------------

ADHOC_SLOTS_CACHE = {}
ADHOC_BOOKINGS_CACHE = {}

from datetime import date, timedelta

def get_availability_adhoc(tutor, week_start):
    tutor_id = tutor.id
    key = (tutor_id, week_start)
    start_date = date.fromisoformat(week_start)

    if key not in ADHOC_SLOTS_CACHE:
        dates = [start_date + timedelta(days=i) for i in range(7)]
        weekly_slots = get_weekly_slots(tutor)
        slots = tutor.booking_slots_adhoc(weekly_slots, dates)
        ADHOC_SLOTS_CACHE[key] = slots

    return ADHOC_SLOTS_CACHE[key]

def get_adhoc_bookings(tutor, week_start):
    tutor_id = tutor.id
    key = (tutor_id, week_start)

    if key not in ADHOC_BOOKINGS_CACHE:
        start_date = date.fromisoformat(week_start)
        dates = [start_date + timedelta(days=i) for i in range(7)]
        bookings = tutor.booking_list_adhoc(dates)
        ADHOC_BOOKINGS_CACHE[key] = bookings

    return ADHOC_BOOKINGS_CACHE[key]

def invalidate_availability_adhoc(tutor_id):
    global ADHOC_SLOTS_CACHE
    today = date.today()

    ADHOC_SLOTS_CACHE = {
        key: value
        for key, value in ADHOC_SLOTS_CACHE.items()
        if key[0] != tutor_id and date.fromisoformat(key[1]) >= today
    }

def invalidate_adhoc_bookings(tutor_id):
    global ADHOC_BOOKINGS_CACHE
    today = date.today()

    ADHOC_BOOKINGS_CACHE = {
        key: value
        for key, value in ADHOC_BOOKINGS_CACHE.items()
        if key[0] != tutor_id and date.fromisoformat(key[1]) >= today
    }

def mask_availability_adhoc(bookings_by_date, student_id):
    import copy
    safe = copy.deepcopy(bookings_by_date)

    for day_str, bookings in safe.items():
        for b in bookings:
            b["status"] = "booked_self" if b.get("student_id") == student_id else "booked_other"
            b.pop("student_name", None)
            b.pop("student_id", None)

    return safe

def mask_adhoc_bookings(bookings, student_id):
    import copy
    safe = copy.deepcopy(bookings)

    for day_str, items in safe.items():
        for b in items:
            b["status"] = "booked_self" if b.get("student_id") == student_id else "booked_other"
            b.pop("student_name", None)
            b.pop("student_id", None)

    return safe


# ------------ WEEKLY BOOKING AVAILABILITY -------------

WEEKLY_SLOTS_CACHE = {}
WEEKLY_BOOKINGS_CACHE = {}

def get_weekly_slots(tutor):
    tutor_id = tutor.id
    if tutor_id not in WEEKLY_SLOTS_CACHE:
        WEEKLY_SLOTS_CACHE[tutor_id] = tutor.booking_slots_weekly()
    return WEEKLY_SLOTS_CACHE[tutor_id]

def get_weekly_bookings(tutor):
    tutor_id = tutor.id
    if tutor_id not in WEEKLY_BOOKINGS_CACHE:
        WEEKLY_BOOKINGS_CACHE[tutor_id] = tutor.booking_list_weekly()
    return WEEKLY_BOOKINGS_CACHE[tutor_id]

def invalidate_weekly_slots(tutor_id):
    WEEKLY_SLOTS_CACHE.pop(tutor_id, None)

def invalidate_weekly_bookings(tutor_id):
    WEEKLY_BOOKINGS_CACHE.pop(tutor_id, None)

def mask_weekly_bookings(weekly_bookings, student_id):
    import copy
    safe = copy.deepcopy(weekly_bookings)

    for weekday, bookings in safe.items():
        for b in bookings:
            # Mark whether the booking belongs to the student
            if b.get("student_id") == student_id:
                b["status"] = "booked_self"
            else:
                b["status"] = "booked_other"

            b.pop("student_name", None)
            b.pop("student_id", None)

    return safe

# ---------- COMBINED BOOKINGS ---------------

def update_booking_confirmed_in_cache(tutor_id, booking_id, booking_type, new_value):
    if booking_type in ("weekly", "weekly_paused"):
        weekly = WEEKLY_BOOKINGS_CACHE.get(tutor_id)
        if not weekly:
            return
        for weekday, bookings in weekly.items():
            for b in bookings:
                if b.get("id") == booking_id:
                    b["confirmed"] = new_value
                    return
        return

    if booking_type == "adhoc":
        for (tid, week_start), bookings_by_date in ADHOC_BOOKINGS_CACHE.items():
            if tid != tutor_id:
                continue
            for day_str, bookings in bookings_by_date.items():
                for b in bookings:
                    if b.get("id") == booking_id:
                        b["confirmed"] = new_value
                        return
        return

def update_booking_caches(booking, action):
    tutor = booking.tutor
    tutor_id = tutor.id

    is_weekly = isinstance(booking, BookingWeekly)
    is_adhoc = isinstance(booking, BookingAdhoc)

    # ---------------------------------------------------
    # WEEKLY BOOKINGS
    # ---------------------------------------------------
    if is_weekly:
        weekly = WEEKLY_BOOKINGS_CACHE.get(tutor_id)

        if weekly:
            # Remove old entry
            for weekday, items in weekly.items():
                weekly[weekday] = [b for b in items if b.get("id") != booking.id]

            # Reinsert unless deleted
            if action != "delete":
                weekday = booking.weekday
                weekly.setdefault(weekday, [])
                weekly[weekday].append(booking.to_dict())

        # Only invalidate slots for time-changing actions
        if action not in ("confirm"):
            WEEKLY_SLOTS_CACHE.pop(tutor_id, None)

        return

    # ---------------------------------------------------
    # ADHOC BOOKINGS
    # ---------------------------------------------------
    if is_adhoc:
        # Find all cached weeks for this tutor
        keys = [(tid, week_start)
                for (tid, week_start) in ADHOC_BOOKINGS_CACHE.keys()
                if tid == tutor_id]

        for key in keys:
            bookings_by_date = ADHOC_BOOKINGS_CACHE[key]

            # Remove old entry
            for day_str, items in bookings_by_date.items():
                bookings_by_date[day_str] = [b for b in items if b.get("id") != booking.id]

            # Reinsert unless deleted
            if action != "delete":
                booking_dict = booking.to_dict()
                day_str = booking_dict["day_str"]  # local date, not UTC
                bookings_by_date.setdefault(day_str, [])
                bookings_by_date[day_str].append(booking_dict)

        # Only invalidate slots for time-changing actions
        if action not in ("confirm"):
            for key in keys:
                ADHOC_SLOTS_CACHE.pop(key, None)

        return

# ----------SKILLS ---------------


MATRIX_CACHE = None
# Fallback used only if the Year table is empty or unavailable
GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]


def get_grades():
    """Return active year codes from the Year model, falling back to the hardcoded list."""
    try:
        codes = list(Year.objects.filter(active=True).order_by("order").values_list("code", flat=True))
        return codes if codes else GRADES
    except Exception:
        return GRADES

def flatten_skills(skills, children_map, depth=0):
    flat = []
    for skill in skills:
        flat.append((skill, depth))
        children = children_map.get(skill.id, [])
        flat.extend(flatten_skills(children, children_map, depth + 1))
    return flat


def build_matrix():
    grades = get_grades()

    skills = list(
        Skill.objects.all()
        .select_related("parent")
        .order_by("id")
    )

    # Template counts grouped by parent Skill (Skill-level node), not detail node.
    # Templates are linked to skill_detail; we roll up via skill_detail__parent_id.
    template_counts = {
        (parent_id, grade): count
        for parent_id, grade, count in Template.objects
        .filter(skill_detail__isnull=False)
        .values_list("skill_detail__parent_id", "grade")
        .annotate(count=Count("id"))
    }

    validated_counts = {
        (parent_id, grade): count
        for parent_id, grade, count in Template.objects
        .filter(skill_detail__isnull=False, validated=True)
        .values_list("skill_detail__parent_id", "grade")
        .annotate(count=Count("id"))
    }

    unvalidated_counts = {
        (parent_id, grade): count
        for parent_id, grade, count in Template.objects
        .filter(skill_detail__isnull=False, validated=False)
        .values_list("skill_detail__parent_id", "grade")
        .annotate(count=Count("id"))
    }

    # Build children map
    children_map = {}
    for skill in skills:
        parent_id = skill.parent_id
        children_map.setdefault(parent_id, []).append(skill)

    # Get top-level skills and flatten — skip is_detail nodes entirely
    top_level = [s for s in children_map.get(None, []) if not s.is_detail]
    flat = flatten_skills(top_level, children_map)

    # Build rows — skip detail-level nodes
    rows = []
    for skill, depth in flat:
        if skill.is_detail:
            continue

        grade_list = [str(g) for g in skill.get_grade_list()]

        cells = {}
        for g in grades:
            g_str = str(g)
            colour = "covered" if g_str in grade_list else "empty"
            cells[g_str] = {
                "colour": colour,
                "count": template_counts.get((skill.id, g_str), 0),
                "validated": validated_counts.get((skill.id, g_str), 0),
                "unvalidated": unvalidated_counts.get((skill.id, g_str), 0),
            }

        # children_count counts only non-detail children so that Skill-level nodes
        # (whose only children are detail nodes) appear as leaves (children_count=0).
        non_detail_children = [c for c in children_map.get(skill.id, []) if not c.is_detail]

        rows.append({
            "id": skill.id,
            "parent_id": skill.parent_id,
            "code": skill.code,
            "description": skill.description,
            "depth": depth,
            "is_detail": False,
            "children_count": len(non_detail_children),
            "validated_count": sum(
                validated_counts.get((skill.id, g_str), 0) for g_str in grades
            ),
            "unvalidated_count": sum(
                unvalidated_counts.get((skill.id, g_str), 0) for g_str in grades
            ),
            "cells": cells,
        })

    return {
        "grades": grades,
        "skills": rows
    }


def update_matrix_cache_for_count(skill_id):
    """Update cached counts for a Skill-level node (parent of skill_detail nodes).
    Call with the Skill-level node ID whenever a template under it changes."""
    global MATRIX_CACHE
    if MATRIX_CACHE is None:
        return

    # Recompute counts for this Skill-level node, rolling up from its detail children
    total_counts = {
        grade: count
        for grade, count in Template.objects
            .filter(skill_detail__parent_id=skill_id)
            .values_list("grade")
            .annotate(count=Count("id"))
    }

    validated_counts = {
        grade: count
        for grade, count in Template.objects
            .filter(skill_detail__parent_id=skill_id, validated=True)
            .values_list("grade")
            .annotate(count=Count("id"))
    }

    unvalidated_counts = {
        grade: count
        for grade, count in Template.objects
            .filter(skill_detail__parent_id=skill_id, validated=False)
            .values_list("grade")
            .annotate(count=Count("id"))
    }

    for row in MATRIX_CACHE["skills"]:
        if row["id"] == skill_id:
            for g in GRADES:
                g_str = str(g)
                row["cells"][g_str]["count"] = total_counts.get(g_str, 0)
                row["cells"][g_str]["validated"] = validated_counts.get(g_str, 0)
                row["cells"][g_str]["unvalidated"] = unvalidated_counts.get(g_str, 0)
            break

def get_matrix_cache():
    global MATRIX_CACHE
    if MATRIX_CACHE is None:
        MATRIX_CACHE = build_matrix()   # heavy work
    return MATRIX_CACHE

def filter_matrix_by_grade(matrix, grade):
    grade_str = str(grade)
    rows = matrix["skills"]

    # 1. Find covered leaf skills for this grade
    covered_leaf_ids = {
        r["id"]
        for r in rows
        if r["children_count"] == 0
        and r["cells"][grade_str]["colour"] == "covered"
    }

    # 2. Build parent lookup
    parent_map = {r["id"]: r.get("parent_id") for r in rows}

    # 3. Collect ancestors
    visible_ids = set()

    def add_ancestors(skill_id):
        if skill_id in visible_ids:
            return
        visible_ids.add(skill_id)
        parent_id = parent_map.get(skill_id)
        if parent_id:
            add_ancestors(parent_id)

    for leaf_id in covered_leaf_ids:
        add_ancestors(leaf_id)

    # 4. Filter rows
    return [r for r in rows if r["id"] in visible_ids]

