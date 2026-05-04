import json
import os
from backend.models import Skill

def import_skill_tree(node, parent, existing_by_code, seen_codes):
    code = node["code"]
    seen_codes.add(code)
    description = node["description"]
    years = node.get("years_practised", [])
    grades_str = ",".join(str(y) for y in years)
    detail_lines = node.get("detail", [])
    if isinstance(detail_lines, str):
        detail_lines = [l.strip() for l in detail_lines.splitlines() if l.strip()]

    skill = existing_by_code.get(code)

    if skill:
        print(f"{code} - Updating")
        skill.description = description
        skill.grades = grades_str
        skill.parent = parent
        skill.is_detail = False
        skill.save(update_fields=["description", "grades", "parent", "is_detail"])
    else:
        print(f"{code} - Importing")
        skill = Skill.objects.create(
            parent=parent,
            code=code,
            description=description,
            grades=grades_str,
            is_detail=False,
        )
        existing_by_code[code] = skill

    # Sync Skill Detail children from the detail array
    _sync_detail_children(skill, detail_lines, existing_by_code, seen_codes)

    for child in node.get("children", []):
        import_skill_tree(child, parent=skill, existing_by_code=existing_by_code, seen_codes=seen_codes)


def _sync_detail_children(skill, detail_lines, existing_by_code, seen_codes):
    """Create or update is_detail=True child Skill nodes for each detail line."""
    existing_details = list(
        Skill.objects.filter(parent=skill, is_detail=True).order_by("order_index")
    )
    # Build a map: description → existing detail skill
    existing_by_desc = {s.description: s for s in existing_details}

    kept_ids = []
    for i, line in enumerate(detail_lines):
        detail_code = f"{skill.code}-D{i + 1}"
        seen_codes.add(detail_code)

        if line in existing_by_desc:
            detail_skill = existing_by_desc[line]
            if detail_skill.order_index != i or detail_skill.code != detail_code or detail_skill.grades != skill.grades:
                detail_skill.order_index = i
                detail_skill.code = detail_code
                detail_skill.grades = skill.grades
                detail_skill.save(update_fields=["order_index", "code", "grades"])
        else:
            detail_skill = Skill.objects.create(
                parent=skill,
                code=detail_code,
                description=line,
                grades=skill.grades,
                order_index=i,
                is_detail=True,
            )
            existing_by_code[detail_code] = detail_skill

        kept_ids.append(detail_skill.id)

    # Remove stale detail children (lines removed from JSON)
    for d in existing_details:
        if d.id not in kept_ids:
            print(f"  {d.code} - Deleting stale detail skill")
            d.delete()

def import_syllabus():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "nsw_math_k10_years.json")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing_by_code = {s.code: s for s in Skill.objects.all()}
    seen_codes = set()

    for top in data:
        import_skill_tree(top, parent=None, existing_by_code=existing_by_code, seen_codes=seen_codes)

    stale_codes = set(existing_by_code) - seen_codes
    if stale_codes:
        deleted_count, _ = Skill.objects.filter(code__in=stale_codes).delete()
        for code in sorted(stale_codes):
            print(f"{code} - Deleted (not in syllabus file)")
        print(f"Deleted {deleted_count} stale skill(s).")
    else:
        print("No stale skills to delete.")
