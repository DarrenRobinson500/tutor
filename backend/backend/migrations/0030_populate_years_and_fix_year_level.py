from django.db import migrations

INITIAL_YEARS = [
    (0,  "K",  "Kindergarten"),
    (1,  "1",  "Year 1"),
    (2,  "2",  "Year 2"),
    (3,  "3",  "Year 3"),
    (4,  "4",  "Year 4"),
    (5,  "5",  "Year 5"),
    (6,  "6",  "Year 6"),
    (7,  "7",  "Year 7"),
    (8,  "8",  "Year 8"),
    (9,  "9",  "Year 9"),
    (10, "10", "Year 10"),
]

# Converts old label-style values to codes: "Year 7" -> "7", "Year K" -> "K"
def label_to_code(value):
    if value is None:
        return value
    if isinstance(value, int):
        return str(value)
    v = str(value).strip()
    if v.startswith("Year "):
        return v[5:]
    return v


def populate_years(apps, schema_editor):
    Year = apps.get_model("backend", "Year")
    for order, code, label in INITIAL_YEARS:
        Year.objects.get_or_create(code=code, defaults={"label": label, "order": order})


def fix_student_year_levels(apps, schema_editor):
    StudentProfile = apps.get_model("backend", "StudentProfile")
    for profile in StudentProfile.objects.all():
        if profile.year_level:
            fixed = label_to_code(profile.year_level)
            if fixed != profile.year_level:
                profile.year_level = fixed
                profile.save(update_fields=["year_level"])


def fix_tutor_year_levels(apps, schema_editor):
    TutorProfile = apps.get_model("backend", "TutorProfile")
    for profile in TutorProfile.objects.all():
        if profile.tutor_year_levels:
            fixed = [label_to_code(y) for y in profile.tutor_year_levels]
            if fixed != profile.tutor_year_levels:
                profile.tutor_year_levels = fixed
                profile.save(update_fields=["tutor_year_levels"])


def run_all(apps, schema_editor):
    populate_years(apps, schema_editor)
    fix_student_year_levels(apps, schema_editor)
    fix_tutor_year_levels(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0029_year_model"),
    ]

    operations = [
        migrations.RunPython(run_all, migrations.RunPython.noop),
    ]
