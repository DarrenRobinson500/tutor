"""PDF Parent Progress Report — SubjectMatter."""
from io import BytesIO
import re
from collections import Counter

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Flowable, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, KeepTogether,
)


# ── Colours ───────────────────────────────────────────────────────────────────
BRAND       = HexColor('#1A5276')
BRAND_MID   = HexColor('#2980B9')
BRAND_LIGHT = HexColor('#EBF5FB')
GREEN       = HexColor('#1A7A43')
GREEN_LIGHT = HexColor('#EAFAF1')
AMBER       = HexColor('#B7770D')
AMBER_LIGHT = HexColor('#FEF9E7')
GREY        = HexColor('#95A5A6')
GREY_LIGHT  = HexColor('#F4F6F7')
GREY_TEXT   = HexColor('#5D6D7E')
DARK        = HexColor('#1C2833')
BORDER      = HexColor('#D5D8DC')
WHITE       = colors.white

PAGE_W, PAGE_H = A4
MARGIN   = 1.8 * cm
USABLE_W = PAGE_W - 2 * MARGIN

# ── Competency scale ──────────────────────────────────────────────────────────
LEVELS = ['none', 'easy', 'medium', 'hard', 'mastered']
LEVEL_LABEL = {
    'none':     'Untested',
    'easy':     'Developing',
    'medium':   'Proficient',
    'hard':     'Advanced',
    'mastered': 'Advanced',
}
LEVEL_INDEX = {l: i for i, l in enumerate(LEVELS)}
LEVEL_COLOUR = {
    'none':     GREY,
    'easy':     HexColor('#E67E22'),
    'medium':   BRAND_MID,
    'hard':     GREEN,
    'mastered': BRAND,
}
LEVEL_HEX = {
    'none':     '#95A5A6',
    'easy':     '#E67E22',
    'medium':   '#2980B9',
    'hard':     '#1A7A43',
    'mastered': '#1A5276',
}

# Dot colours — left to right, each dot represents one level step
_DOT_COLOURS = [
    HexColor('#E67E22'),  # step 1 (Beginning)
    BRAND_MID,            # step 2 (Developing)
    GREEN,                # step 3 (Proficient)
    BRAND,                # step 4 (Advanced/Mastered)
]


# ── Custom Flowables ──────────────────────────────────────────────────────────
class DotScale(Flowable):
    """Four filled/hollow dots visualising competency (0–4 filled)."""
    DOT_R   = 4.5
    SPACING = 13.0

    def __init__(self, level_index):
        super().__init__()
        self.level_index = min(max(int(level_index), 0), 4)
        self.hAlign = 'CENTER'
        self._w = 4 * self.SPACING + self.DOT_R * 2
        self._h = self.DOT_R * 2 + 4

    def wrap(self, aw, ah):
        return self._w, self._h

    def draw(self):
        c = self.canv
        r = self.DOT_R
        y = self._h / 2
        for i in range(4):
            x = i * self.SPACING + r
            if i < self.level_index:
                fc = _DOT_COLOURS[i]
                c.setFillColor(fc)
                c.setStrokeColor(fc)
                c.circle(x, y, r, fill=1, stroke=0)
            else:
                c.setFillColor(HexColor('#E8EAED'))
                c.setStrokeColor(HexColor('#BDC3C7'))
                c.circle(x, y, r, fill=1, stroke=1)


class HProgressBar(Flowable):
    """Horizontal rounded-cap progress bar."""
    def __init__(self, percent, width, height=8):
        super().__init__()
        self.percent = min(max(float(percent), 0), 100)
        self._w = float(width)
        self._h = float(height)
        self.hAlign = 'CENTER'

    def wrap(self, aw, ah):
        return self._w, self._h

    def draw(self):
        c = self.canv
        w, h = self._w, self._h
        radius = h / 2
        c.setFillColor(HexColor('#E8EAED'))
        c.roundRect(0, 0, w, h, radius, fill=1, stroke=0)
        fw = w * self.percent / 100
        if fw > 0:
            c.setFillColor(BRAND_MID)
            c.roundRect(0, 0, max(fw, radius * 2), h, radius, fill=1, stroke=0)


# ── Styles ────────────────────────────────────────────────────────────────────
def _styles():
    base = ParagraphStyle('_base', fontName='Helvetica', fontSize=9.5, leading=14, textColor=DARK)
    return {
        'base':        base,
        'small':       ParagraphStyle('_small', parent=base, fontSize=8.5, textColor=GREY_TEXT),
        'header_left': ParagraphStyle('_hl', fontName='Helvetica-Bold', fontSize=17, textColor=WHITE, leading=21),
        'header_right':ParagraphStyle('_hr', fontName='Helvetica', fontSize=10, textColor=HexColor('#AECDE8'), leading=13, alignment=TA_RIGHT),
        'student_name':ParagraphStyle('_sn', fontName='Helvetica-Bold', fontSize=15, textColor=DARK, leading=19),
        'student_sub': ParagraphStyle('_ss', fontName='Helvetica', fontSize=9.5, textColor=GREY_TEXT, leading=13),
        'date_right':  ParagraphStyle('_dr', fontName='Helvetica', fontSize=9.5, textColor=GREY_TEXT, leading=13, alignment=TA_RIGHT),
        'summary':     ParagraphStyle('_su', fontName='Helvetica', fontSize=10, textColor=DARK, leading=15),
        'h2':          ParagraphStyle('_h2', fontName='Helvetica-Bold', fontSize=12, textColor=BRAND, leading=15, spaceBefore=2),
        'card_title':  ParagraphStyle('_ct', fontName='Helvetica-Bold', fontSize=9.5, textColor=DARK, leading=12),
        'card_body':   ParagraphStyle('_cb', fontName='Helvetica', fontSize=9, textColor=GREY_TEXT, leading=12),
        'snap_big':    ParagraphStyle('_sb', fontName='Helvetica-Bold', fontSize=20, textColor=BRAND, leading=24, alignment=TA_CENTER),
        'snap_level':  ParagraphStyle('_sl', fontName='Helvetica-Bold', fontSize=12, textColor=BRAND, leading=15, alignment=TA_CENTER),
        'snap_label':  ParagraphStyle('_sk', fontName='Helvetica', fontSize=8, textColor=GREY_TEXT, leading=10, alignment=TA_CENTER),
        'table_hdr':   ParagraphStyle('_th', fontName='Helvetica-Bold', fontSize=8.5, textColor=WHITE, leading=11),
        'table_cell':  ParagraphStyle('_tc', fontName='Helvetica', fontSize=8.5, textColor=DARK, leading=11),
        'rec':         ParagraphStyle('_rc', fontName='Helvetica', fontSize=9.5, textColor=DARK, leading=14),
        'rec_title':   ParagraphStyle('_rt', fontName='Helvetica-Bold', fontSize=10, textColor=BRAND, leading=13, spaceAfter=3),
        'footer':      ParagraphStyle('_ft', fontName='Helvetica', fontSize=7.5, textColor=GREY, leading=10, alignment=TA_CENTER),
    }


# ── Helper: competency data ───────────────────────────────────────────────────
def _overall_level(results):
    """Modal level across all results (excluding 'none')."""
    assessed = [r.highest_difficulty_reached for r in results if r.highest_difficulty_reached != 'none']
    if not assessed:
        return 'none'
    return Counter(assessed).most_common(1)[0][0]


def _strengths_and_focus(results):
    """Return (top-3 strengths, top-3 focus areas) as lists of results."""
    assessed = [r for r in results if r.highest_difficulty_reached != 'none']
    by_level = sorted(assessed, key=lambda r: LEVEL_INDEX.get(r.highest_difficulty_reached, 0))
    strengths = list(reversed(by_level))[:3]
    focus_candidates = [r for r in by_level if r.highest_difficulty_reached in ('easy', 'medium')]
    focus = focus_candidates[:3] if focus_candidates else by_level[:3]
    return strengths, focus


def _compute_coverage(session, results):
    """Return (pct_or_None, assessed_count, total_or_None).

    Coverage is derived from the star system: sum of capped competency levels
    (max 4 per leaf skill) divided by 4 × total leaf skills, matching what the
    student home page displays under 'Your Syllabus'.
    """
    from .models import Skill, StudentSkillCompetency
    from django.db.models import Count, Q as _Q

    assessed = len(results)
    try:
        profile = session.student.student_profile
        year_level = profile.year_level
    except Exception:
        year_level = None

    grade_num = None
    if year_level:
        m = re.search(r'\d+', str(year_level))
        if m:
            grade_num = m.group()

    if not grade_num:
        return None, assessed, None

    try:
        leaf_skill_ids = list(
            Skill.objects
            .filter(is_detail=False, grades__icontains=grade_num)
            .annotate(non_detail_children=Count('children', filter=_Q(children__is_detail=False)))
            .filter(non_detail_children=0)
            .values_list('id', flat=True)
        )
        total = len(leaf_skill_ids)
        if not total:
            return None, assessed, None

        competencies = StudentSkillCompetency.objects.filter(
            student=session.student,
            skill_id__in=leaf_skill_ids,
        ).values_list('level', flat=True)

        star_sum = sum(min(lvl, 4) for lvl in competencies)
        pct = round(star_sum / (4 * total) * 100)
    except Exception:
        return None, assessed, None

    return pct, assessed, total


# ── Card builder ──────────────────────────────────────────────────────────────
def _skill_card(title, level, desc, accent, bg, s):
    """Returns a card-style Table with a coloured left accent strip."""
    hex_col = LEVEL_HEX.get(level, '#95A5A6')
    inner_w = USABLE_W - 4 * mm - 18   # right cell width minus padding
    body = Table(
        [[Paragraph(title, s['card_title'])],
         [Paragraph(f'<font color="{hex_col}"><b>{LEVEL_LABEL.get(level, level)}</b></font>', s['card_body'])],
         [Paragraph(desc, s['card_body'])]],
        colWidths=[inner_w],
    )
    body.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
    ]))
    card = Table([['', body]], colWidths=[4 * mm, USABLE_W - 4 * mm])
    card.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg),
        ('BACKGROUND',    (0, 0), (0, -1), accent),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (0, -1), 0),
        ('BOTTOMPADDING', (0, 0), (0, -1), 0),
        ('LEFTPADDING',   (0, 0), (0, -1), 0),
        ('RIGHTPADDING',  (0, 0), (0, -1), 0),
        ('LEFTPADDING',   (1, 0), (1, -1), 9),
        ('RIGHTPADDING',  (1, 0), (1, -1), 8),
    ]))
    return card


# ── Main ──────────────────────────────────────────────────────────────────────
def generate_test_report(session) -> bytes:
    from .ai import generate_report_narrative

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    s = _styles()
    elements = []

    # ── Gather data ───────────────────────────────────────────────────────────
    results = list(session.skill_results.all())

    # Untested skills (present in skill_codes but no TestSkillResult)
    from .models import Skill as _Skill
    tested_codes = {r.skill_code for r in results}
    all_codes = session.skill_codes or []
    untested_codes = [c for c in all_codes if c not in tested_codes]
    untested_desc = {}
    if untested_codes:
        for sk in _Skill.objects.filter(code__in=untested_codes).values('code', 'description'):
            untested_desc[sk['code']] = sk['description']

    proportion_tested = len(tested_codes) / len(all_codes) if all_codes else 1.0
    quit_early = session.status == 'abandoned' and len(untested_codes) > 0
    student = session.student
    student_name = student.get_full_name() or student.username
    first_name = (student.first_name or student_name.split()[0]).strip()

    try:
        profile = student.student_profile
        year_level = profile.year_level
    except Exception:
        year_level = None

    yr_num = None
    if year_level:
        _m = re.search(r'\d+', str(year_level))
        if _m:
            yr_num = int(_m.group())

    if yr_num and 7 <= yr_num <= 12:
        quit_threshold    = 0.50 + (yr_num - 7) * 0.10   # 50 % … 100 %
        sitting_questions = 10  + (yr_num - 7) * 10       # 10 … 60
    else:
        quit_threshold    = 0.50
        sitting_questions = 10

    attn_text = ''
    if quit_early and proportion_tested < quit_threshold:
        attn_text = (
            f"{first_name} completed {len(tested_codes)} of {len(all_codes)} skills "
            f"({round(proportion_tested * 100)}%) before ending the test early. "
            f"{first_name} should work towards being able to complete "
            f"{sitting_questions} questions in a sitting."
        )

    tutor = student.get_tutor()
    tutor_name = tutor.get_full_name() if tutor else None

    # Coverage % — use the same calculation as the student home page so the
    # figure in the report matches what the student sees.
    grade_key = str(year_level).strip().lower().replace("year", "").strip() if year_level else None
    coverage_pct = None
    if grade_key:
        try:
            from .competency import get_student_score as _gss
            coverage_pct = round(_gss(student, grade_key) * 100)
        except Exception:
            pass

    assessed_count = len(results)
    overall_lvl   = _overall_level(results)
    overall_label = LEVEL_LABEL[overall_lvl]
    strengths_rs, focus_rs = _strengths_and_focus(results)

    strengths_data = [
        {'skill_description': r.skill_description or r.skill_code,
         'level_label': LEVEL_LABEL[r.highest_difficulty_reached]}
        for r in strengths_rs
    ]
    focus_data = [
        {'skill_description': r.skill_description or r.skill_code,
         'level_label': LEVEL_LABEL[r.highest_difficulty_reached]}
        for r in focus_rs
    ]

    # All leaf skills for the year, in syllabus order, with current competency levels.
    # Used in the syllabus breakdown table.
    all_year_skills = []  # list of (description, comp_level)
    if grade_key:
        try:
            from .cache import get_matrix_cache, filter_matrix_by_grade
            from .models import StudentSkillCompetency as _SSC
            _matrix = get_matrix_cache()
            _year_leaves = [s for s in filter_matrix_by_grade(_matrix, grade_key) if s['children_count'] == 0]
            _skill_ids = [s['id'] for s in _year_leaves]
            _comp_map = {c.skill_id: c.level for c in _SSC.objects.filter(
                student=student, skill_id__in=_skill_ids
            )}
            all_year_skills = [
                (s['description'], _comp_map.get(s['id'], 0))
                for s in _year_leaves
            ]
        except Exception:
            pass

    try:
        student_gender = student.student_profile.gender or ""
    except Exception:
        student_gender = ""

    narrative = generate_report_narrative(
        student_first_name=first_name,
        year_level=year_level,
        overall_level=overall_label,
        coverage_percent=coverage_pct,
        total_assessed=assessed_count,
        strengths=strengths_data,
        focus_areas=focus_data,
        gender=student_gender,
    )

    from django.utils import timezone as _tz
    d = _tz.localtime(session.started_at)
    date_str = f"{d.day} {d.strftime('%B %Y')}"
    yr_str = f"Year {year_level} Mathematics" if year_level else "Mathematics"

    # ── HEADER BAND ───────────────────────────────────────────────────────────
    header = Table(
        [[Paragraph('<font color="#FFFFFF">Subject</font><font name="Helvetica" color="#FF8C42">Matter</font>', s['header_left']),
          Paragraph(yr_str, s['header_right'])]],
        colWidths=[USABLE_W * 0.6, USABLE_W * 0.4],
    )
    header.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BRAND),
        ('TOPPADDING',    (0, 0), (-1, -1), 13),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 13),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 0.35 * cm))

    # ── STUDENT INFO ROW ──────────────────────────────────────────────────────
    info_left = Table(
        [[Paragraph(student_name, s['student_name'])],
         [Paragraph(f"{yr_str}  ·  Progress Report", s['student_sub'])]],
        colWidths=[USABLE_W * 0.65],
    )
    info_left.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
    ]))

    right_rows = [[Paragraph(date_str, s['date_right'])]]
    if tutor_name:
        right_rows.append([Paragraph(f"Tutor: {tutor_name}", s['date_right'])])
    info_right = Table(right_rows, colWidths=[USABLE_W * 0.35])
    info_right.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
    ]))

    info_row = Table([[info_left, info_right]], colWidths=[USABLE_W * 0.65, USABLE_W * 0.35])
    info_row.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_row)
    elements.append(Spacer(1, 0.3 * cm))

    # ── SUMMARY CARD ─────────────────────────────────────────────────────────
    summary_text = narrative.get('summary', '')
    combined_summary = summary_text
    if attn_text:
        combined_summary = (f"{summary_text}<br/><br/>{attn_text}" if summary_text else attn_text)
    if combined_summary:
        summary_card = Table(
            [[Paragraph(combined_summary, s['summary'])]],
            colWidths=[USABLE_W],
        )
        summary_card.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), BRAND_LIGHT),
            ('TOPPADDING',    (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING',   (0, 0), (-1, -1), 14),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
            ('LINEBEFORE',    (0, 0), (0, -1), 3, BRAND_MID),
        ]))
        elements.append(summary_card)
        elements.append(Spacer(1, 0.35 * cm))

    # ── SNAPSHOT ROW ─────────────────────────────────────────────────────────
    cell_w = USABLE_W / 2 - 6   # leave a little gap between cells via outer padding

    # Cell 1 — Coverage
    if coverage_pct is not None:
        big_text = f"{coverage_pct}%"
        sub_text = f"of Year {year_level} curriculum" if year_level else "coverage"
    else:
        big_text = str(assessed_count)
        sub_text = f"skill{'s' if assessed_count != 1 else ''} assessed"

    bar_w = cell_w - 20
    snap1_rows = [
        [Paragraph(big_text, s['snap_big'])],
        [HProgressBar(coverage_pct or 0, bar_w)],
        [Paragraph(sub_text, s['snap_label'])],
    ]

    # Cell 2 — Skills count
    snap2_rows = [
        [Paragraph(str(assessed_count), s['snap_big'])],
        [Spacer(1, 8)],   # align height with bar row
        [Paragraph(f"skill{'s' if assessed_count != 1 else ''} assessed", s['snap_label'])],
    ]

    snap_style = [
        ('BACKGROUND',    (0, 0), (-1, -1), GREY_LIGHT),
        ('TOPPADDING',    (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]

    def _snap(rows):
        t = Table(rows, colWidths=[cell_w])
        t.setStyle(TableStyle(snap_style))
        return t

    snap_outer = Table(
        [[_snap(snap1_rows), _snap(snap2_rows)]],
        colWidths=[USABLE_W / 2] * 2,
    )
    snap_outer.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(snap_outer)
    elements.append(Spacer(1, 0.4 * cm))

    # ── STRENGTHS ─────────────────────────────────────────────────────────────
    if strengths_data:
        elements.append(Paragraph("Strengths", s['h2']))
        elements.append(Spacer(1, 2 * mm))
        strength_blurbs = narrative.get('strength_blurbs', {})
        cards = []
        for r, d in zip(strengths_rs, strengths_data):
            blurb = strength_blurbs.get(d['skill_description'],
                                        f"{first_name} is performing well in this area.")
            cards.append(_skill_card(d['skill_description'], r.highest_difficulty_reached, blurb, GREEN, GREEN_LIGHT, s))
            cards.append(Spacer(1, 2 * mm))
        elements.append(KeepTogether(cards))
        elements.append(Spacer(1, 0.3 * cm))

    # ── FOCUS AREAS ───────────────────────────────────────────────────────────
    if focus_data:
        focus_blurbs = narrative.get('focus_blurbs', {})
        cards = [Paragraph("Areas for Focus", s['h2']), Spacer(1, 2 * mm)]
        for r, d in zip(focus_rs, focus_data):
            blurb = focus_blurbs.get(d['skill_description'],
                                     "Focusing on this area will build confidence for upcoming topics.")
            cards.append(_skill_card(d['skill_description'], r.highest_difficulty_reached, blurb, AMBER, AMBER_LIGHT, s))
            cards.append(Spacer(1, 2 * mm))
        elements.append(KeepTogether(cards))
        elements.append(Spacer(1, 0.4 * cm))

    # ── SYLLABUS BREAKDOWN ────────────────────────────────────────────────────
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=0.25 * cm))
    elements.append(Paragraph("Syllabus Breakdown", s['h2']))
    elements.append(Spacer(1, 2 * mm))

    _LEVEL_TO_DIFF = {0: 'none', 1: 'easy', 2: 'medium', 3: 'hard', 4: 'hard', 5: 'hard', 6: 'hard'}

    tbl_data = [[
        Paragraph("Skill", s['table_hdr']),
        Paragraph("Level", s['table_hdr']),
    ]]
    rows_source = all_year_skills or [(r.skill_description or r.skill_code, None) for r in results]
    for skill_desc, comp_level in rows_source:
        if comp_level is None:
            diff_key = 'none'
        else:
            diff_key = _LEVEL_TO_DIFF.get(min(int(comp_level), 6), 'none')
        lvl_label = LEVEL_LABEL.get(diff_key, 'Untested')
        lvl_hex = LEVEL_HEX.get(diff_key, '#95A5A6')
        tbl_data.append([
            Paragraph(skill_desc, s['table_cell']),
            Paragraph(f'<font color="{lvl_hex}"><b>{lvl_label}</b></font>', s['table_cell']),
        ])

    col_widths = [USABLE_W * 0.73, USABLE_W * 0.27]
    tbl_styles = [
        ('BACKGROUND',    (0, 0), (-1, 0), BRAND),
        ('FONTSIZE',      (0, 0), (-1, -1), 8.5),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.3, BORDER),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]
    for i in range(1, len(tbl_data)):
        tbl_styles.append(('BACKGROUND', (0, i), (-1, i), GREY_LIGHT if i % 2 == 0 else WHITE))

    skill_tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)
    skill_tbl.setStyle(TableStyle(tbl_styles))
    elements.append(skill_tbl)
    elements.append(Spacer(1, 0.45 * cm))

    # ── RECOMMENDATION ────────────────────────────────────────────────────────
    rec_text = narrative.get('recommendation', '')
    if rec_text:
        rec_card = Table(
            [[Paragraph("Recommended Focus", s['rec_title'])],
             [Paragraph(rec_text, s['rec'])]],
            colWidths=[USABLE_W],
        )
        rec_card.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), BRAND_LIGHT),
            ('TOPPADDING',    (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
            ('LEFTPADDING',   (0, 0), (-1, -1), 14),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
            ('LINEBEFORE',    (0, 0), (0, -1), 3, BRAND),
        ]))
        elements.append(rec_card)
        elements.append(Spacer(1, 0.35 * cm))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=3))
    footer_parts = ['SubjectMatter']
    if tutor_name:
        footer_parts.append(f"Tutor: {tutor_name}")
    footer_parts.append("Aligned to the NSW K–10 Mathematics Syllabus")
    elements.append(Paragraph("  ·  ".join(footer_parts), s['footer']))

    doc.build(elements)
    return buffer.getvalue()
