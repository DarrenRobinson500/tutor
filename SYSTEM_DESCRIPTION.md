# Tutor Platform — System Description for Test Planning

---

## 1. System Overview

### Purpose and Domain

This is a private tutoring platform operating in Australia (timezone: Australia/Sydney). It connects professional tutors with school-aged students (K–12) and their parents. The platform manages the complete lifecycle of private tutoring: account creation and onboarding, booking weekly or one-off sessions, delivering live online tutoring sessions with real-time question practice, tracking student competency across a skills-based mathematics curriculum, handling post-session tutor review and parent messaging, and processing payments via Stripe. A separate teacher-facing channel allows school classroom teachers to run assessments for their class groups and track student results.

### User Roles

Six distinct roles exist, stored as a single string in `User.role`:

**admin** — Full platform oversight. Receives `AdminJob` tasks for approving distributors, approving tutors, reviewing failed or overdue payments, investigating low session ratings, setting up bank details, handling removed tutors, and calling tutors with overdue reviews. Can send email records via `AdminEmailRecord`. Responds to parent feedback (`ParentFeedback`). Has no dedicated profile model beyond the base `User` record. Automatically assigned when a Django superuser (`is_superuser=True`) logs in via the JWT path.

**tutor** — The core service provider. Has a `TutorProfile` (branding, bio, qualifications, Stripe Connect account). Sets weekly availability (`TutorAvailability`) and blocked days (`TutorBlockedDay`). Has a roster of assigned students (`TutorStudent`). Hosts live `TutoringSession` records. Receives `TutorJob` tasks for post-tuition review, send progress message, review focus areas, review available hours, set up weekly session, set fee, payment failure and overdue notifications, confirm payment receipt. Writes `BookingOutcome` records after each session. Sends SMS messages to students/parents via `SMSConversation`/`SMSMessage`. Requires admin approval (`TutorProfile.approved=False` by default; `User.active=False` until approved).

**parent** — The payer and guardian. Linked to one or more children via `ParentChild`. Has a `ParentPaymentProfile` storing Stripe customer ID and saved card. Pays `SessionPayment` invoices. Can pause/unpause sessions indirectly (`ParentChild.sessions_paused` is set by the system when payment is 14+ days overdue). Receives `ParentJob` tasks for `payment_due`, `payment_failed`, `payment_overdue_7`, and `payment_overdue_14`. Submits `ParentFeedback`. Can launch a child's class assessment via a short-lived `AssessmentToken` without the child needing to know their password.

**student** — The learner. Has a `StudentProfile` (year level, school, hourly rate, gender, etc.). Linked to a tutor via `TutorStudent`. Books weekly (`BookingWeekly`) and ad-hoc (`BookingAdhoc`) sessions. Participates in live `TutoringSession` records. Answers `Question` records generated from `Template` records. Progress is tracked per skill via `StudentSkillCompetency`, `StudentTemplateProgress`, and `StudentFocusArea`. Takes adaptive `TestSession` records. Can join a teacher's class via `TeacherClassStudent` and sit `ClassAssessment` events.

**distributor** — A referral/channel partner. Has a `DistributorProfile` with a unique `referral_code` and Stripe account ID. Linked to referred parents via `DistributorParent`. Receives a share of session payments (`distributor_amount` in `SessionPayment` and `Payment`). Requires admin approval (`DistributorProfile.approved=False` by default). Receives `AdminJob` tasks for approval.

**teacher** — A school classroom teacher. Has a `TeacherProfile` (`school_name`, `approved=True` by default — teachers are auto-approved unlike tutors and distributors). Creates `TeacherClass` records (a named class with a year level and a unique join code). Enrols students via `TeacherClassStudent`. Runs `ClassAssessment` events for a class and views `AssessmentStudentResult` data per student.

### Core End-to-End Workflows

**Student joins the platform:**
1. Admin or tutor creates a `User` with `role="student"`.
2. A `StudentProfile` is created (get_or_create pattern in `get_student_profile()`).
3. The tutor is linked to the student via a `TutorStudent` record.
4. A parent `User` with `role="parent"` is created and linked to the student via `ParentChild`.
5. The parent sets up their payment method — a `ParentPaymentProfile` is created with the Stripe customer ID and card details.
6. A welcome email is sent; `User.welcome_email_sent` flips to `True`.

**Student books a session:**
- *Weekly booking:* `booking_create_weekly()` on the `User` model looks up the assigned tutor, calculates `end_time` from `tutor.default_session_minutes`, checks for duplicate and overlapping `BookingWeekly` records (no database lock), and creates a `BookingWeekly` row (`weekday` integer 0–6, `start_time`, `end_time`, `confirmed=False`). The booking can be paused by setting `start_date` to a future date via the `skip()` method.
- *Ad-hoc booking:* `booking_create_adhoc()` is called with a specific start datetime. It computes available slots by intersecting `TutorAvailability` windows with existing `BookingAdhoc` records and `TutorBlockedDay` records, then creates a `BookingAdhoc` row if the slot is free. Students have a cancellation window controlled by `GlobalSetting cancellation_notice_hours` (default 24 hours); `student_can_edit()` enforces this.

**Session runs:**
1. A `TutoringSession` record is created with a unique `room_name` (format `t{tutor_id}-s{student_id}`). Tutor and student join the LiveKit video room.
2. `session_state` (JSONField) holds real-time state. `active_template` tracks the current question template. `session_mode` can be `'focus_area'` or `'assessment'`.
3. During the session the tutor selects focus areas (`StudentFocusArea`) and the student answers `Question` records generated from `Template` records. Each answer is recorded as a `QuestionAttempt`.
4. `TestSession` records are used for adaptive skill testing within the session, tracking `skill_codes`, `current_difficulty`, `correct_streak`, `incorrect_count`, and `used_template_ids`. `TestSkillResult` and `TestQuestionResult` rows are appended as the student progresses.
5. When the session ends, a `SessionSkillSnapshot` is written per skill to record the student's competency level at that point.

**Payment processed:**
1. A `TutorJob` of type `'post_tuition_review'` is created referencing the session via `booking_ref`.
2. The tutor completes the review, writing a `BookingOutcome` (date, time, parent_message, focus_areas M2M, focus_areas_next M2M, notes).
3. A `SessionPayment` record is created with `status='pending'`. Amounts are split: `tutor_amount`, `platform_amount` (default $6.50), `distributor_amount`, `total_amount`.
4. A `ParentJob` of type `'payment_due'` is created for the parent.
5. Stripe authorises the payment (`stripe_payment_intent_id` stored, `status` → `'authorised'`, `authorised_at` set).
6. Payment is captured (`status` → `'paid'`, `paid_at` set).
7. Tutor confirms receipt (`status` → `'confirmed'`, `confirmed_at` set). A `TutorJob` of type `'confirm_payment_receipt'` drives this step.
8. If payment fails: `status` → `'failed'`. `TutorJob 'payment_failed'` and `ParentJob 'payment_failed'` are created. If still unpaid after 7 days: `status` → `'overdue_7'`. After 14 days: `status` → `'overdue_14'` and sessions are paused (`ParentChild.sessions_paused=True`). `AdminJob` rows are also created to flag the overdue payment.
9. After payment, the parent can rate the session (`SessionPayment.rating` 1–5 and `rating_comment`). A rating of 2 or below triggers an `AdminJob` of type `'low_session_rating'`.
10. A legacy `Payment` model also exists (created in migration 0046) for a simpler manual record-keeping flow: it stores `amount_paid`, amount splits, account references, `date_tuition`, `date_debit`, `date_credit`, and is linked from `BookingOutcome.payment`.

---

## 2. Database Schema

### Year

Purpose: Reference table for school year levels; acts as the single source of truth for valid year values used across the platform.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| code | CharField(10) | no | — | unique=True; e.g. "K", "1", "10", "11std" |
| label | CharField(50) | no | — | Display name e.g. "Kindergarten", "Year 1" |
| order | PositiveIntegerField | no | — | Sort order |
| active | BooleanField | no | True | Show in dropdowns |
| stage | CharField(20) | no | "k10" | blank=True; values: "k10" or "s6" |

Meta: `ordering = ["order"]`. No relationships. No soft-delete. No audit fields.

---

### User (extends AbstractUser)

Purpose: Central account model for all platform participants; `role` field determines which features and views are accessible.

Inherited AbstractUser fields:

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| password | CharField(128) | no | — | Hashed via Django |
| last_login | DateTimeField | yes | null | |
| is_superuser | BooleanField | no | False | |
| username | CharField(150) | no | — | unique=True |
| first_name | CharField(150) | no | "" | blank=True |
| last_name | CharField(150) | no | "" | blank=True |
| email | EmailField(254) | no | "" | blank=True |
| is_staff | BooleanField | no | False | |
| is_active | BooleanField | no | True | Django built-in active flag |
| date_joined | DateTimeField | no | timezone.now | |
| groups | M2M → auth.Group | — | — | |
| user_permissions | M2M → auth.Permission | — | — | |

Custom fields added:

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| role | CharField(20) | no | — | choices: student, tutor, parent, admin, distributor, teacher |
| default_session_minutes | IntegerField | no | 60 | |
| buffer_minutes | IntegerField | no | 15 | Gap around bookings |
| active | BooleanField | no | True | Platform-level active flag (distinct from is_active) |
| account_details | CharField(500) | no | "" | blank=True; free-text bank/account info |
| welcome_email_sent | BooleanField | no | False | |

`role` enum values: `"student"`, `"tutor"`, `"parent"`, `"admin"`, `"distributor"`, `"teacher"`.

Note: Two separate boolean active flags exist — the inherited `is_active` (Django auth) and the custom `active` (platform-level soft-disable). Both must be `True` for a user to function normally.

A `SuperuserRoleSerializer` on the JWT login path auto-upgrades `is_superuser=True` Django superusers to `role='admin'` on first login.

No `created_at`/`updated_at` audit fields on User directly (`date_joined` is the creation timestamp). No `is_deleted` field; soft-disable via `active=False`.

---

### BookingWeekly

Purpose: Represents a recurring weekly tutoring session on a fixed weekday and time.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| tutor | FK → User | yes | null | blank=True; CASCADE; related_name="appointment_tutor_weekly" |
| student | FK → User | yes | null | blank=True; CASCADE; related_name="student_weekly" |
| weekday | IntegerField | no | — | 0=Monday … 6=Sunday |
| start_time | TimeField | no | — | |
| end_time | TimeField | no | — | Computed as start + tutor.default_session_minutes |
| start_date | DateField | yes | null | blank=True; when set and in future, booking is paused until this date |
| confirmed | BooleanField | no | False | |

No soft-delete field. No audit timestamps. No status enum. No database unique constraint on (tutor, weekday, start_time).

---

### BookingAdhoc

Purpose: Represents a single one-off tutoring appointment at a specific datetime.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| tutor | FK → User | no | — | CASCADE; related_name="appointment_tutor" |
| student | FK → User | no | — | CASCADE; related_name="student" |
| start_datetime | DateTimeField | no | — | |
| end_datetime | DateTimeField | no | — | |
| confirmed | BooleanField | no | False | |
| status | CharField(20) | no | — | No choices defined in model; free-text status string |
| created_by | FK → User | yes | null | blank=True; SET_NULL; related_name="appointments_created" |
| created_at | DateTimeField | no | auto_now_add | |

Note: The initial migration named this model "Appointment"; it was renamed to BookingAdhoc. No soft-delete. No `updated_at`. No database unique constraint on (tutor, start_datetime).

---

### ParentChild

Purpose: Links a parent user to their child (student) user, and records whether the child's sessions are currently paused.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| parent | FK → User | no | — | CASCADE; related_name="children" |
| child | FK → User | no | — | CASCADE; related_name="parents" |
| sessions_paused | BooleanField | no | False | Set True when payment is 14+ days overdue |

Meta: `unique_together = ("parent", "child")`. No audit fields.

---

### TutorStudent

Purpose: The many-to-many assignment linking a tutor to each of their students.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| tutor | FK → User | no | — | CASCADE; related_name="students" |
| student | FK → User | no | — | CASCADE; related_name="tutors" |

Meta: `unique_together = ("tutor", "student")`. No audit fields.

---

### StudentProfile

Purpose: Extended profile data for a student user, including year level, school, hourly rate, and competency rollup.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| user | OneToOne → User | no | — | CASCADE; related_name="student_profile" |
| year_level | CharField(50) | yes | null | blank=True; e.g. "7", "10", "K" |
| area_of_study | TextField | yes | null | blank=True |
| mobile | CharField(20) | yes | "0493461541" | blank=True; default is a placeholder number |
| address | CharField(255) | yes | null | blank=True |
| school_name | CharField(200) | yes | null | blank=True |
| hourly_rate | DecimalField(8,2) | no | 70 | Per-student override rate |
| plain_password | CharField(50) | yes | null | blank=True; stores cleartext password (security concern — see Risk 2) |
| min_questions_per_skill | IntegerField | no | 0 | |
| gender | CharField(20) | yes | null | blank=True |

No soft-delete. No audit timestamps.

---

### UserPreference

Purpose: Key-value store for per-user application preferences (e.g. UI settings).

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| user | FK → User | no | — | CASCADE; related_name="preferences" |
| key | CharField(100) | no | — | |
| value | JSONField | no | — | |
| updated_at | DateTimeField | no | auto_now | |

Meta: `unique_together = ("user", "key")`. No `created_at`.

---

### TutorProfile

Purpose: Extended profile for a tutor user, holding branding, billing, availability settings, qualifications, and Stripe Connect details.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| tutor | FK → User | no | — | CASCADE; related_name="tutor" |
| logo | ImageField | yes | null | blank=True; upload_to='branding/' |
| color_scheme | CharField(20) | yes | null | blank=True |
| welcome_message | TextField | yes | null | blank=True |
| token | CharField(64) | yes | null | blank=True; unique=True; used for student invite links |
| created_at | DateTimeField | no | auto_now_add | |
| mobile | CharField(20) | yes | "0493461541" | blank=True; placeholder default |
| address | CharField(255) | yes | null | blank=True |
| default_session_minutes | IntegerField | no | 60 | |
| buffer_minutes | IntegerField | no | 15 | |
| default_hourly_rate | DecimalField(8,2) | no | 70 | |
| qualification | CharField(255) | yes | null | blank=True |
| university | CharField(255) | yes | null | blank=True |
| tutor_year_levels | JSONField | no | list | Year levels the tutor teaches |
| bio | TextField | yes | null | blank=True |
| approved | BooleanField | no | False | Requires admin approval |
| looking_for_students | BooleanField | no | True | |
| edit_syllabus | BooleanField | no | False | Permission to edit syllabus content |
| stripe_account_id | CharField(200) | yes | null | blank=True; Stripe Connect account |

No soft-delete. No `updated_at` (only `created_at`).

---

### Skill

Purpose: Hierarchical curriculum skill node; can be a parent category or a leaf "detail" skill linked to question templates.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| parent | FK → Skill (self) | yes | null | blank=True; CASCADE; related_name="children"; null = top-level |
| code | CharField(100) | no | — | e.g. "MA3-1WM" |
| description | TextField | no | — | Human-readable description |
| grades | CharField(50) | yes | null | blank=True; comma-separated e.g. "3,4,5" or "K" |
| order_index | IntegerField | no | 0 | Sort order |
| is_detail | BooleanField | no | False | True = leaf node with templates attached |

No soft-delete. No audit fields.

---

### StudentSkillMatrix

Purpose: Legacy tracking model. Tracks a student's mastery and confidence per skill using floating-point scores. Replaced in active code by `StudentSkillCompetency`.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| student | FK → User | no | — | CASCADE |
| skill | FK → Skill | no | — | CASCADE |
| mastery | FloatField | no | 0.0 | 0–1 scale |
| evidence_count | IntegerField | no | 0 | |
| recent_correct_rate | FloatField | no | 0.0 | |
| confidence | FloatField | no | 0.0 | |
| last_updated | DateTimeField | no | auto_now | |

Meta: `unique_together = ("student", "skill")`.

---

### StudentTemplateProgress

Purpose: Tracks per-template correctness and "robustness" (streak of correct answers) for the competency system.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| student | FK → User | no | — | CASCADE; related_name="template_progress" |
| template_id | IntegerField | no | — | Stores the PK of Template directly (not a FK) |
| skill_code | CharField(100) | no | — | |
| difficulty | CharField(10) | no | — | "easy", "medium", or "hard" |
| ever_correct | BooleanField | no | False | |
| streak_start_date | DateField | yes | null | blank=True; date of first correct in current robustness attempt |
| has_robust | BooleanField | no | False | True = student has demonstrated robust mastery |
| last_answered_date | DateField | yes | null | blank=True |

Meta: `unique_together = ('student', 'template_id')`. Index on `(student, skill_code, difficulty)`.

---

### StudentSkillCompetency

Purpose: 7-level (0–6) competency score per student per skill; the active replacement for `StudentSkillMatrix`.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| student | FK → User | no | — | CASCADE; related_name="skill_competency" |
| skill | FK → Skill | no | — | CASCADE |
| level | IntegerField | no | 0 | Range: 0–6 |
| updated_at | DateTimeField | no | auto_now | |

Meta: `unique_together = ('student', 'skill')`.

---

### StudentFocusArea

Purpose: Records which skills are in a student's current focus for tutoring, with weekly tracking of learning and tutoring completion.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| student | FK → User | no | — | CASCADE; related_name="focus_areas" |
| skill | FK → Skill | no | — | CASCADE |
| added_by | FK → User | yes | null | blank=True; SET_NULL; related_name="focus_areas_added" |
| order | PositiveIntegerField | no | 0 | Display order |
| created_at | DateTimeField | no | auto_now_add | |
| learning_done_week | DateField | yes | null | blank=True; Monday date of the week learning was last completed |
| tutoring_done_week | DateField | yes | null | blank=True; Monday date of the week tutoring was last completed |
| level_before_learning | IntegerField | yes | null | blank=True; competency level at start of learning session |
| level_after_learning | IntegerField | yes | null | blank=True; competency level at end of learning session |

Meta: `unique_together = ('student', 'skill')`. `ordering = ['order', 'id']`.

---

### SessionSkillSnapshot

Purpose: Records a student's competence level per skill at the end of each tutoring session.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| session | FK → TutoringSession | no | — | CASCADE; related_name="skill_snapshots" |
| student | FK → User | no | — | CASCADE |
| skill | FK → Skill | no | — | CASCADE |
| mastery | FloatField | no | — | |
| competence_label | CharField(20) | no | — | e.g. "developing", "proficient" |
| recorded_at | DateTimeField | no | auto_now_add | |

Meta: `unique_together = ('session', 'skill')`. `ordering = ['recorded_at']`.

---

### WeeklyProgressSnapshot

Purpose: Periodic snapshot of a student's overall syllabus progress score, used to power the progress chart.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| student | FK → User | no | — | CASCADE; related_name="weekly_progress_snapshots" |
| score | FloatField | no | — | 0–100+ percentage (can exceed 100 at levels 5–6) |
| recorded_at | DateTimeField | no | auto_now_add | |
| source | CharField(20) | no | — | choices: "post_session", "scheduled" |

`source` enum values: `"post_session"` (Post Session), `"scheduled"` (Scheduled). Meta: `ordering = ['recorded_at']`.

---

### TutorJob

Purpose: Task queue for actions the tutor must complete, ordered by trigger time, with expiry and show-from scheduling.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| tutor | FK → User | no | — | CASCADE; related_name="tutor_jobs" |
| student | FK → User | yes | null | blank=True; CASCADE; related_name="student_jobs" |
| job_type | CharField(50) | no | — | choices (see below) |
| session | FK → TutoringSession | yes | null | blank=True; SET_NULL; related_name="jobs" |
| booking_ref | CharField(80) | yes | null | blank=True; e.g. "adhoc_42" or "weekly_7_2026-04-14"; dedup key |
| booking_outcome | OneToOne → BookingOutcome | yes | null | blank=True; SET_NULL; related_name="job" |
| triggered_at | DateTimeField | no | auto_now_add | |
| expires_at | DateTimeField | no | — | |
| completed_at | DateTimeField | yes | null | blank=True; null = incomplete |
| show_from | DateTimeField | yes | null | blank=True; job hidden until this time |

`job_type` enum values:
- `"post_tuition_review"` — Post Tuition Review
- `"send_progress_message"` — Send Progress Message
- `"review_focus_area"` — Review Focus Area
- `"review_available_hours"` — Review My Available Hours
- `"setup_weekly_session"` — Set Up Weekly Session
- `"set_fee"` — Set Your Tutoring Fee
- `"payment_failed"` — Payment Failed
- `"payment_overdue_7"` — Payment Overdue — 7 Days
- `"payment_overdue_14"` — Payment Overdue — 14 Days — Sessions Paused
- `"confirm_payment_receipt"` — Confirm Payment Receipt

Meta: `ordering = ['triggered_at']`.

---

### AdminJob

Purpose: Task queue for actions the platform admin must complete.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| job_type | CharField(50) | no | — | choices (see below) |
| subject | FK → User | yes | null | blank=True; CASCADE; related_name="admin_jobs"; the user the job concerns |
| notes | TextField | yes | null | blank=True |
| triggered_at | DateTimeField | no | auto_now_add | |
| completed_at | DateTimeField | yes | null | blank=True |

`job_type` enum values:
- `"approve_distributor"` — Approve Distributor
- `"approve_tutor"` — Approve Tutor
- `"payment_failed"` — Payment Failed
- `"payment_overdue_7"` — Payment Overdue — 7 Days
- `"payment_overdue_14"` — Payment Overdue — 14 Days
- `"low_session_rating"` — Low Session Rating
- `"setup_bank_details"` — Setup Bank Details
- `"tutor_removed"` — Tutor Removed
- `"call_tutor_overdue_review"` — Call Tutor — Overdue Review

Meta: `ordering = ['triggered_at']`.

---

### TutorAvailability

Purpose: Defines a recurring weekly time window during which the tutor is available to accept bookings.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| tutor | FK → User | no | — | CASCADE (no related_name defined) |
| weekday | IntegerField | no | — | 0=Monday … 6=Sunday |
| start_time | TimeField | no | — | |
| end_time | TimeField | no | — | |

No uniqueness constraints — a tutor can have multiple overlapping windows per day. No soft-delete. No audit fields.

---

### TutorBlockedDay

Purpose: Marks a specific calendar date as unavailable for a tutor (e.g. holiday, sick day).

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| tutor | FK → User | no | — | CASCADE (no related_name) |
| date | DateField | no | — | |

No soft-delete. No audit fields.

---

### Notification

Purpose: Simple in-platform notification record sent to a user.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| recipient | FK → User | no | — | CASCADE (no related_name) |
| message | TextField | no | — | |
| sent_at | DateTimeField | no | auto_now_add | |

---

### TemplateGroup

Purpose: Groups multiple difficulty variants of the same question concept (easy/medium/hard) under one parent.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| name | CharField(200) | yes | null | blank=True |
| skill_detail | FK → Skill | yes | null | blank=True; SET_NULL; related_name="template_groups" |
| grade | CharField(10) | yes | null | blank=True |

No soft-delete. No audit fields. Reverse: templates (FK from Template.group).

---

### Template

Purpose: A parameterised question template (stored as YAML/JSON) that can generate randomised question instances for students.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| name | CharField(200) | yes | null | blank=True |
| description | TextField | no | "" | blank=True |
| content | TextField | yes | null | blank=True; raw YAML/JSON template definition |
| topic | CharField(100) | no | "" | blank=True |
| subtopic | CharField(100) | no | "" | blank=True |
| grade | CharField(10) | yes | null | blank=True |
| difficulty | CharField(50) | no | "" | blank=True; "easy", "medium", or "hard" |
| tags | JSONField | no | list | blank=True |
| group | FK → TemplateGroup | yes | null | blank=True; SET_NULL; related_name="templates" |
| curriculum | JSONField | no | list | blank=True |
| skill_detail | FK → Skill | yes | null | blank=True; SET_NULL; related_name="templates" |
| validated | BooleanField | no | False | Only validated=True templates are served to students |
| status | CharField(20) | no | "draft" | choices: "draft", "validated", "published" |
| version | IntegerField | no | 1 | |
| created_by | FK → User | yes | null | SET_NULL; related_name="templates_created" |
| updated_by | FK → User | yes | null | SET_NULL; related_name="templates_updated" |
| created_at | DateTimeField | no | auto_now_add | |
| updated_at | DateTimeField | no | auto_now | |
| has_preview | BooleanField | no | False | Set True once preview successfully generated |
| last_validated_at | DateTimeField | yes | null | blank=True |
| knowledge_items | M2M → Knowledge | — | — | blank=True; related_name="templates" |
| language | CharField(10) | no | "en" | |
| parent_template | FK → Template (self) | yes | null | blank=True; SET_NULL; related_name="translations" |

`status` enum values: `"draft"` (Draft), `"validated"` (Validated), `"published"` (Published).

Computed property `skill`: returns `self.skill_detail.parent` (the parent Skill of the leaf `skill_detail`).

Note: The `validated` boolean field (not `status`) is the operative gate — only `Template.objects.filter(validated=True)` records are served to students in the competency system.

---

### TutoringSession

Purpose: Tracks an active or completed live online tutoring session between a tutor and a student.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| room_name | CharField(100) | no | — | unique=True; format: `t{tutor_id}-s{student_id}` |
| tutor | FK → User | no | — | CASCADE; related_name="tutoring_sessions_tutor" |
| student | FK → User | no | — | CASCADE; related_name="tutoring_sessions_student" |
| active_template | FK → Template | yes | null | blank=True; SET_NULL; related_name="+" (no reverse) |
| session_mode | CharField(20) | yes | null | blank=True; values: 'focus_area' or 'assessment' |
| session_state | JSONField | no | dict | blank=True; real-time state bag |
| created_at | DateTimeField | no | auto_now_add | |
| last_called_at | DateTimeField | yes | null | blank=True; set when tutor joins |
| student_joined_at | DateTimeField | yes | null | blank=True; set when student joins |

---

### Knowledge

Purpose: A reusable knowledge item (formula, rule, definition) shown to students alongside question solutions.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| title | CharField(200) | no | — | |
| text | TextField | no | "" | blank=True |
| diagram | TextField | no | "" | blank=True; SVG or diagram spec |
| text_2 | TextField | no | "" | blank=True; supplementary text |
| skills | M2M → Skill | — | — | blank=True; related_name="knowledge_items" |
| created_at | DateTimeField | no | auto_now_add | |
| updated_at | DateTimeField | no | auto_now | |

---

### TemplateDiagram

Purpose: Stores an SVG diagram specification associated with a template.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| template | FK → Template | no | — | CASCADE (no related_name) |
| svg_spec | TextField | no | — | |

---

### TemplateSkill

Purpose: Explicit many-to-many join between a template and one or more skills (separate from the `skill_detail` FK).

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| template | FK → Template | no | — | CASCADE |
| skill | FK → Skill | no | — | CASCADE |

Meta: `unique_together = ("template", "skill")`.

---

### Question

Purpose: A rendered question instance generated from a Template for a specific student, with the student's answer recorded.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| template | FK → Template | no | — | CASCADE |
| student | FK → User | no | — | CASCADE; related_name="question_instances" |
| params | JSONField | no | — | Randomised parameter values used to render this instance |
| question_text | TextField | no | — | Rendered question text |
| correct_answer | TextField | no | — | |
| help_requested | BooleanField | no | False | |
| created_at | DateTimeField | no | auto_now_add | |
| selected_answer | TextField | yes | null | Student's chosen answer |
| correct | BooleanField | no | True | Whether the student answered correctly |
| time_taken_ms | IntegerField | yes | null | blank=True |

---

### QuestionAttempt

Purpose: Records every individual attempt by a student on a question, used for competency analytics.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| question | FK → Question | yes | null | CASCADE |
| student | FK → User | yes | null | CASCADE |
| template | FK → Template | yes | null | CASCADE |
| skills | JSONField | yes | null | Skill codes associated with this attempt |
| selected_answer | TextField | yes | null | |
| correct | BooleanField | no | True | |
| time_taken_ms | IntegerField | yes | null | blank=True |
| attempted_at | DateTimeField | yes | auto_now_add | |

---

### Task

Purpose: A bundle of questions assigned to a student at a point in time.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| student | FK → User | no | — | CASCADE |
| assigned_at | DateTimeField | no | auto_now_add | |

---

### TaskItem

Purpose: Links a specific `Question` instance to a `Task`.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| task | FK → Task | no | — | CASCADE |
| question | FK → Question | yes | null | CASCADE |

---

### SyllabusMapping

Purpose: Maps a Template to a regional syllabus outcome code.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| template | FK → Template | no | — | CASCADE |
| region | CharField(50) | no | — | e.g. "NSW", "VIC" |
| outcome_code | CharField(50) | no | — | e.g. "MA3-1WM" |

---

### Note

Purpose: Free-text notes authored by a user, optionally linked to a Template.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| author | FK → User | yes | null | blank=True; CASCADE; related_name="notes" |
| template | FK → Template | yes | null | blank=True; SET_NULL; related_name="notes" |
| text | TextField | no | — | |
| created_at | DateTimeField | no | auto_now_add | |
| category | CharField(50) | yes | null | blank=True |

---

### GlobalSetting

Purpose: Key-value table for runtime platform configuration.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| key | CharField(100) | no | — | unique=True |
| value | CharField(500) | no | — | |

Known keys in use: `cancellation_notice_hours` (default 24), `platform_fee_per_hour` (default 5), `distributor_fee_per_hour` (default 5), `sms_send` (bool feature flag), `sms_pause` (debounce minutes, default 10), `global_settings_cache_min`. Accessed via `get_bool()`, `get_int()`, `get_decimal()` helper functions which cache values for a configurable number of minutes.

---

### SMSConversation

Purpose: A persistent two-party SMS thread between one tutor and one student.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| tutor | FK → User | no | — | CASCADE; related_name="sms_conversations_as_tutor" |
| student | FK → User | no | — | CASCADE; related_name="sms_conversations_as_student" |
| created_at | DateTimeField | no | auto_now_add | |
| last_message_at | DateTimeField | no | auto_now | |

---

### SMSMessage

Purpose: A single SMS message within a conversation, inbound or outbound.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| direction | CharField(10) | no | — | choices: "outbound", "inbound" |
| conversation | FK → SMSConversation | no | — | CASCADE; related_name="messages" |
| body | TextField | no | — | |
| phone_number | CharField(20) | yes | null | blank=True |
| provider_message_id | CharField(100) | yes | null | blank=True; ClickSend message ID |
| status | CharField(20) | no | "queued" | Free-text; expected values: "queued", "sent", "delivered", "failed" |
| created_at | DateTimeField | no | auto_now_add | |
| sent_at | DateTimeField | yes | null | blank=True |
| delivered_at | DateTimeField | yes | null | blank=True |

`direction` enum values: `"outbound"` (Outbound), `"inbound"` (Inbound).

---

### SMSSendJob

Purpose: Scheduled outbound SMS job; allows messages to be queued for future delivery with retry support.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| conversation | FK → SMSConversation | yes | null | blank=True; CASCADE; related_name="jobs" |
| to_number | CharField(20) | yes | null | blank=True; used when there is no conversation |
| message_type | CharField(60) | yes | null | blank=True; deduplication key (e.g. "reminder_24h_adhoc_42") |
| body | TextField | no | — | |
| scheduled_for | DateTimeField | no | — | |
| created_at | DateTimeField | no | auto_now_add | |
| cancelled | BooleanField | no | False | True = sent or permanently abandoned |
| last_error | TextField | yes | null | blank=True |
| last_attempt_at | DateTimeField | yes | null | blank=True |
| retry_count | IntegerField | no | 0 | Jobs with retry_count >= 3 are skipped permanently |

---

### AdminEmailRecord

Purpose: Audit log of every email sent by the admin panel.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| to_email | EmailField | no | — | |
| to_name | CharField(255) | no | "" | blank=True |
| subject | CharField(255) | no | — | |
| body | TextField | no | — | |
| sent_at | DateTimeField | no | auto_now_add | |
| sent_by | FK → User | yes | null | blank=True; SET_NULL; related_name="sent_admin_emails" |
| status | CharField(20) | no | "sent" | Values: "sent", "failed" |
| error | TextField | no | "" | blank=True |

Meta: `ordering = ['-sent_at']`.

---

### ParentFeedback

Purpose: Stores feedback submitted by parents, with an optional admin response.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| parent | FK → User | no | — | CASCADE; related_name="feedback_submitted" |
| body | TextField | no | — | |
| created_at | DateTimeField | no | auto_now_add | |
| admin_response | TextField | yes | null | blank=True |
| responded_at | DateTimeField | yes | null | blank=True |
| responded_by | FK → User | yes | null | blank=True; SET_NULL; related_name="feedback_responses" |

Meta: `ordering = ['-created_at']`.

---

### TestSession

Purpose: An adaptive question testing session for a student, supporting multiple modes: legacy adaptive, fixed-difficulty, and learning loops.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| student | FK → User | no | — | CASCADE; related_name="test_sessions" |
| started_at | DateTimeField | no | timezone.now | |
| completed_at | DateTimeField | yes | null | blank=True |
| status | CharField(20) | no | "active" | choices: "active", "completed", "abandoned" |
| skill_codes | JSONField | no | list | Ordered list of skill codes to test |
| current_skill_index | IntegerField | no | 0 | |
| current_difficulty | CharField(10) | no | "easy" | |
| correct_streak | IntegerField | no | 0 | |
| incorrect_count | IntegerField | no | 0 | |
| used_template_ids | JSONField | no | list | Prevents repeating the same template |
| test_type | CharField(10) | no | "" | blank=True; choices: "easy", "medium", "hard"; empty = legacy adaptive |
| mode | CharField(20) | no | "" | blank=True; values: "test", "learning", or "" (legacy) |
| mode_state | JSONField | no | dict | State machine data for learning mode |
| linked_focus_area | FK → StudentFocusArea | yes | null | blank=True; SET_NULL; related_name="learning_sessions" |
| linked_tutoring_focus_area | FK → StudentFocusArea | yes | null | blank=True; SET_NULL; related_name="tutoring_learning_sessions" |

`status` enum values: `"active"`, `"completed"`, `"abandoned"`. `test_type` enum values: `"easy"`, `"medium"`, `"hard"`, or `""` (legacy). `mode` values: `"test"`, `"learning"`, `""` (legacy adaptive). Meta: `ordering = ['-started_at']`.

---

### TestSkillResult

Purpose: Summary of performance on a single skill within a TestSession.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| session | FK → TestSession | no | — | CASCADE; related_name="skill_results" |
| skill_code | CharField(100) | no | — | |
| skill_description | CharField(255) | no | "" | blank=True |
| highest_difficulty_reached | CharField(10) | no | "none" | Values: "none", "easy", "medium", "hard" |
| questions_asked | IntegerField | no | 0 | |
| questions_correct | IntegerField | no | 0 | |
| completed_at | DateTimeField | no | timezone.now | |

---

### TestQuestionResult

Purpose: Records every individual question answered in a TestSession.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| session | FK → TestSession | no | — | CASCADE; related_name="question_results" |
| template_id | IntegerField | no | — | Stores PK directly, not a FK |
| skill_code | CharField(100) | no | — | |
| correct | BooleanField | no | — | |
| time_taken_ms | IntegerField | yes | null | blank=True |
| answered_at | DateTimeField | no | auto_now_add | |

Meta: `ordering = ['answered_at']`.

---

### DistributorProfile

Purpose: Extended profile for a distributor user, including referral code and Stripe Connect details.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| user | OneToOne → User | no | — | CASCADE; related_name="distributor_profile" |
| mobile | CharField(20) | yes | null | blank=True |
| university | CharField(255) | yes | null | blank=True |
| bio | TextField | yes | null | blank=True |
| referral_code | CharField(16) | no | auto-generated | unique=True; 8-char hex generated in save() |
| approved | BooleanField | no | False | Requires admin approval |
| created_at | DateTimeField | no | auto_now_add | |
| stripe_account_id | CharField(200) | yes | null | blank=True |

No soft-delete. No `updated_at`.

---

### DistributorParent

Purpose: Records which distributor referred a given parent to the platform.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| distributor | FK → User | no | — | CASCADE; related_name="referred_parents" |
| parent | OneToOne → User | no | — | CASCADE; related_name="referred_by" |
| created_at | DateTimeField | no | auto_now_add | |

Meta: `unique_together = ("distributor", "parent")`.

---

### Payment

Purpose: A simple manual payment record for tuition fees with allocation across parties; the legacy payment model predating `SessionPayment`.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| student | FK → User | yes | null | blank=True; SET_NULL; related_name="payments_as_student" |
| tutor | FK → User | yes | null | blank=True; SET_NULL; related_name="payments_as_tutor" |
| distributor | FK → User | yes | null | blank=True; SET_NULL; related_name="payments_as_distributor" |
| amount_paid | DecimalField(10,2) | no | — | Total amount paid |
| amount_platform | DecimalField(10,2) | no | 0 | Platform's share |
| amount_distributor | DecimalField(10,2) | no | 0 | Distributor's share |
| amount_tutor | DecimalField(10,2) | no | 0 | Tutor's share |
| account_paid | CharField(255) | no | "" | blank=True |
| account_platform | CharField(255) | no | "" | blank=True |
| account_distributor | CharField(255) | no | "" | blank=True |
| account_tutor | CharField(255) | no | "" | blank=True |
| date_tuition | DateField | yes | null | blank=True; date of the session |
| date_debit | DateField | yes | null | blank=True; date payment debited |
| date_credit | DateField | yes | null | blank=True; date payment credited |
| focus_area | TextField | no | "" | blank=True |
| notes | TextField | no | "" | blank=True |
| created_at | DateTimeField | no | auto_now_add | |
| updated_at | DateTimeField | no | auto_now | |

Meta: `ordering = ["-date_tuition", "-created_at"]`.

---

### BookingOutcome

Purpose: Records the tutor's post-session review: what was covered, a parent message, and links to payment and next focus areas.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| tutor | FK → User | yes | null | blank=True; SET_NULL; related_name="booking_outcomes_as_tutor" |
| student | FK → User | yes | null | blank=True; SET_NULL; related_name="booking_outcomes_as_student" |
| date | DateField | no | — | Date the session took place |
| time | TimeField | no | — | Time the session took place |
| parent_message | TextField | no | "" | blank=True |
| focus_areas | M2M → Skill | — | — | blank=True; related_name="booking_outcomes_current" |
| focus_areas_next | M2M → Skill | — | — | blank=True; related_name="booking_outcomes_next" |
| payment | FK → Payment | yes | null | blank=True; SET_NULL; related_name="booking_outcomes"; nullable FK, no unique constraint |
| notes | TextField | no | "" | blank=True; private tutor notes |
| created_at | DateTimeField | no | auto_now_add | |
| updated_at | DateTimeField | no | auto_now | |

Meta: `ordering = ['-date', '-time']`.

---

### TeacherProfile

Purpose: Extended profile for a teacher user.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| user | OneToOne → User | no | — | CASCADE; related_name="teacher_profile" |
| school_name | CharField(200) | no | "" | blank=True |
| approved | BooleanField | no | True | Auto-approved (unlike tutors/distributors) |
| created_at | DateTimeField | no | auto_now_add | |

---

### TeacherClass

Purpose: A named class group created by a teacher, identified by a unique join code.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| teacher | FK → User | no | — | CASCADE; related_name="teacher_classes" |
| name | CharField(100) | no | — | e.g. "7M", "Year 10 Advanced" |
| year_level | CharField(10) | no | — | e.g. "7", "10" |
| code | CharField(8) | no | `_generate_class_code` | unique=True; 6-char uppercase alphanumeric auto-generated |
| created_at | DateTimeField | no | auto_now_add | |

---

### TeacherClassStudent

Purpose: Many-to-many enrolment of a student in a teacher's class.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| teacher_class | FK → TeacherClass | no | — | CASCADE; related_name="memberships" |
| student | FK → User | no | — | CASCADE; related_name="class_memberships" |
| joined_at | DateTimeField | no | auto_now_add | |

Meta: `unique_together = ('teacher_class', 'student')`.

---

### ClassAssessment

Purpose: A class-wide assessment event created by a teacher.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| teacher_class | FK → TeacherClass | no | — | CASCADE; related_name="assessments" |
| status | CharField(10) | no | "active" | choices: "active", "ended" |
| skill_ids | JSONField | no | list | Ordered list of Skill PKs |
| started_at | DateTimeField | no | auto_now_add | |
| ended_at | DateTimeField | yes | null | blank=True |

`status` enum values: `"active"`, `"ended"`.

---

### AssessmentStudentResult

Purpose: Records the correct/incorrect question tally for one student in a ClassAssessment.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| assessment | FK → ClassAssessment | no | — | CASCADE; related_name="results" |
| student | FK → User | no | — | CASCADE; related_name="assessment_results" |
| correct | IntegerField | no | 0 | |
| incorrect | IntegerField | no | 0 | |
| absent | BooleanField | no | False | |
| joined_at | DateTimeField | yes | null | blank=True |

Meta: `unique_together = ('assessment', 'student')`.

---

### AssessmentToken

Purpose: Short-lived UUID token allowing a parent to launch a child's class assessment without the child's password.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| student | FK → User | no | — | CASCADE; related_name="assessment_tokens" |
| token | UUIDField | no | uuid.uuid4 | unique=True; editable=False |
| created_at | DateTimeField | no | auto_now_add | |
| expires_at | DateTimeField | no | — | `is_valid()` checks `timezone.now() < expires_at` |

---

### SessionPayment

Purpose: Stripe-integrated payment record for a completed tutoring session, tracking the full lifecycle from pending through confirmed, with rating.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| session | OneToOne → TutoringSession | yes | null | blank=True; CASCADE; related_name="session_payment" |
| student | FK → User | yes | null | blank=True; SET_NULL; related_name="session_payments_as_student" |
| parent | FK → User | no | — | CASCADE; related_name="session_payments_as_parent" |
| tutor | FK → User | no | — | CASCADE; related_name="session_payments_as_tutor" |
| distributor | FK → User | yes | null | blank=True; SET_NULL; related_name="session_payments_as_distributor" |
| tutor_amount | DecimalField(8,2) | no | — | |
| platform_amount | DecimalField(8,2) | no | 6.50 | |
| distributor_amount | DecimalField(8,2) | no | 0.00 | |
| total_amount | DecimalField(8,2) | no | — | |
| status | CharField(20) | no | "pending" | choices (see below) |
| stripe_payment_intent_id | CharField(200) | yes | null | blank=True |
| stripe_customer_id | CharField(200) | yes | null | blank=True |
| created_at | DateTimeField | no | auto_now_add | |
| authorised_at | DateTimeField | yes | null | blank=True |
| paid_at | DateTimeField | yes | null | blank=True |
| confirmed_at | DateTimeField | yes | null | blank=True |
| expected_settlement_date | DateField | yes | null | blank=True |
| rating | IntegerField | yes | null | blank=True; 1–5 star rating from parent |
| rating_comment | TextField | yes | null | blank=True |

`status` enum values: `"pending"`, `"authorised"`, `"paid"`, `"confirmed"`, `"failed"`, `"overdue_7"`, `"overdue_14"`. Meta: `ordering = ['-created_at']`.

---

### ParentPaymentProfile

Purpose: Stores the parent's Stripe customer ID and saved payment method.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| parent | OneToOne → User | no | — | CASCADE; related_name="payment_profile" |
| stripe_customer_id | CharField(200) | yes | null | blank=True |
| stripe_pm_id | CharField(200) | yes | null | blank=True; Stripe PaymentMethod ID |
| card_last4 | CharField(4) | yes | null | blank=True |
| card_brand | CharField(20) | yes | null | blank=True; e.g. "visa", "mastercard" |
| setup_complete | BooleanField | no | False | |
| created_at | DateTimeField | no | auto_now_add | |
| updated_at | DateTimeField | no | auto_now | |

---

### ParentJob

Purpose: Task queue for actions the parent must complete, driven by the payment lifecycle.

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | BigAutoField (PK) | no | auto | |
| parent | FK → User | no | — | CASCADE; related_name="parent_jobs" |
| payment | FK → SessionPayment | no | — | CASCADE; related_name="parent_jobs" |
| job_type | CharField(50) | no | — | choices (see below) |
| created_at | DateTimeField | no | auto_now_add | |
| completed_at | DateTimeField | yes | null | blank=True |

`job_type` enum values:
- `"payment_due"` — Payment Due
- `"payment_failed"` — Payment Failed — Update Card
- `"payment_overdue_7"` — Payment Overdue — 7 Days
- `"payment_overdue_14"` — Payment Overdue — Sessions Paused

Meta: `ordering = ['created_at']`.

---

## 3. Role and Permission Model

### How Roles Are Defined and Stored

Roles are stored on the custom `User` model (`AUTH_USER_MODEL = "backend.User"`) in a single `CharField(20)` field named `role`. The accepted string values are: `"admin"`, `"tutor"`, `"student"`, `"parent"`, `"distributor"`, `"teacher"`.

Multi-role users are not structurally supported. The `role` field stores a single string. There is no many-to-many roles relationship. A `SuperuserRoleSerializer` on the JWT login path auto-upgrades Django `is_superuser=True` accounts to `role='admin'` on first login.

The `User.active` field (custom, separate from Django's `is_active`) is set to `False` for new tutor and distributor applicants until an admin approves them. This effectively blocks their access to any authenticated endpoint.

### How Permissions Are Enforced

There is no dedicated `permissions.py` file with DRF permission class subclasses. Enforcement is entirely inline in views:

1. **DRF global default** — `settings.py` sets `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`, so all views require a valid JWT unless overridden.

2. **Per-ViewSet `AllowAny` override** — ViewSets that want unauthenticated access set `permission_classes = [AllowAny]` at the class level or per `@action`. This is notably used on `TemplateViewSet`, `SkillViewSet`, `StudentViewSet`, and `YearViewSet`, making those entire ViewSets publicly accessible without a token.

3. **In-view role checks** — After the DRF permission layer passes, views do manual `if request.user.role != "..."` guards and return `Response({'error': 'Forbidden'}, status=403)`.

4. **Owner checks** — Several views also verify `request.user.id == subject.id` (e.g. `DistributorViewSet.retrieve`, `TeacherViewSet._get_teacher`).

### Role-to-Endpoint Access Map

**admin endpoints (IsAuthenticated + role == 'admin'):**
- `AdminJobViewSet` — `list`, `approve`, `dismiss`, `bank_details`, `save_bank_details`, `payments`
- `AdminEmailViewSet` — `list_emails`, `send` (bulk email to all parents/tutors/students)
- `ParentFeedbackViewSet.respond` — reply to parent feedback
- `TutorViewSet.admin_sms` / `admin_sms_conversation` — view all SMS conversations
- `GET/POST /admin/variables/` — read/write `GlobalSetting` records
- `GET /admin/activity/` — new user signups, tutor removals
- `GET /payments/admin-feedback/` — all parent ratings
- `GET /payments/<pk>/` — can access any payment (role checked alongside parent/tutor check)
- `GET /parents/<pk>/payments/` — can access any parent's payment history

**tutor endpoints:**
- `TutorViewSet` — `home`, `payments`, `feedback`, `toggle_looking`, `students`, `booking`, `edit`, `sms`, `sms_conversation`, `sms_activity`, `templates`, `availability`, `add_availability`, `remove_availability`, `block_day`, `unblock_day`, `session_settings`, `booking_action`, `visited_schedule`, `available_slots`
- `TutorJobViewSet` — `list` (own jobs only), `progress_message`, `save_progress_message`, `send_progress_message`, `payment_summary`, `apply_payment`, `complete`
- `TutoringSessionViewSet` — `token`, `set_template`, `state`, `next_question`, `end_session`, `student_skills`, `learn_mode`, `incoming_call`
- `GET /payments/tutor-billing/`
- `POST /payments/<pk>/confirm/`
- `TestViewSet` — `start`, `answer`, `report`, `abandon`, `quit_early`, `past`

**parent endpoints:**
- `AuthViewSet` — `parent_payments`, `parent_home`, `select_tutor`, `remove_tutor`, `request_tutor_mobile`, `launch_assessment`, `add_child`
- `ParentFeedbackViewSet` — `list` (own feedback), `create`
- `POST /payments/setup-intent/`, `POST /payments/save-payment-method/`, `GET /payments/pending/`
- `POST /payments/<pk>/authorise/`
- `POST /payments/<pk>/retry/`
- `GET /payments/<pk>/` (own payments only)
- `GET /parents/<pk>/payments/` (own history only)

**student endpoints:**
- `QuestionViewSet.record` — submit answers, get next question
- `TestViewSet` — `start`, `answer`, `report`, `abandon`, `quit_early`, `past`
- `TutoringSessionViewSet` — `token` (own room only), `incoming_call`
- `StudentViewSet` — `home`, `edit`, `progress`, `booking`, `set_language`
- `FocusAreaViewSet` — read/write own focus areas
- `AssessmentViewSet` — `active`, `join`, `record_answer`
- `AuthViewSet.exchange_token` (public)

**teacher endpoints:**
- `TeacherViewSet` — `home`, `create_class`, `import_students`, `email_credentials`, `reset_student_password`, `class_detail`, `gap_report`, `class_add_focus`, `class_remove_focus`, `start_assessment`, `end_assessment`, `assessment_dashboard`, `mark_absent`

**distributor endpoints:**
- `DistributorViewSet.retrieve` — own record only (`request.user.id == dist_user.id` or `is_staff`)

### Truly Public (AllowAny) Endpoints

The following endpoints have `permission_classes = [AllowAny]` and bypass JWT entirely:

- `POST /auth/jwt/login/`, `POST /auth/jwt/refresh/`
- `POST /auth/login/`, `POST /auth/register/`, `POST /auth/register_parent/`, `POST /auth/register_tutor/`, `POST /auth/register_distributor/`, `POST /auth/register_teacher/`
- `GET /auth/resolve_referral/` — referral code lookup
- `POST /auth/exchange_token/` — one-time assessment token to JWT
- `POST /auth/dev_login/`, `POST /auth/dev_switch_to_parent/` — **development backdoors with no password check** (see Risk 1)
- All of `templates/*` — full CRUD, `AllowAny` class-level
- All of `skills/*` — full CRUD, `AllowAny` class-level
- All of `students/*` — full list and CRUD, `AllowAny` class-level
- All of `years/*` — `AllowAny` class-level
- `GET /settings/` — returns platform fee and dev user credentials

### Key Restricted Endpoints

| Endpoint | Enforcement |
|---|---|
| `admin-jobs/*` | `IsAuthenticated` + `role != 'admin'` → 403 |
| `admin-emails/*` | `IsAuthenticated` + `role != 'admin'` → 403 |
| `admin/variables/` | `IsAuthenticated` + `role != 'admin'` → 403 |
| `admin/activity/` | `IsAuthenticated` + `role != 'admin'` → 403 |
| `payments/admin-feedback/` | `IsAuthenticated` + `role != 'admin'` → 403 |
| `tutors/<pk>/admin_sms*` | `IsAuthenticated` + `role != 'admin'` → 403 |
| `auth/add_child` | `IsAuthenticated` + `role != 'parent'` → 403 |
| `auth/select_tutor` | `IsAuthenticated` + `role != 'parent'` → 403 |
| `payments/<pk>/authorise/` | `IsAuthenticated` + `payment.parent != request.user` → 403 |
| `payments/<pk>/confirm/` | `IsAuthenticated` + `payment.tutor != request.user` → 403 |
| `sessions/token/` | `IsAuthenticated` + `user.id not in (tutor_id, student_id)` → 403 |
| `distributors/<pk>/` | `IsAuthenticated` + `request.user.id != dist_user.id and not is_staff` → 403 |
| `teachers/<pk>/*` | `IsAuthenticated` + `request.user.pk != teacher.pk and role != 'admin'` → 403 |
| `auth/dev_login` | `AllowAny` — no password required (dev backdoor) |
| `auth/dev_switch_to_parent` | `AllowAny` — accepts student_id, returns parent JWT |

---

## 4. Job Queue Design

### Queue System

The platform uses Celery with Redis as both broker and result backend.

- **Broker URL**: `REDIS_URL` env var (default `redis://localhost:6379/0`)
- **Result backend**: same Redis URL
- **Beat scheduler**: `django_celery_beat.schedulers:DatabaseScheduler` (schedules stored in DB, synced from `CELERY_BEAT_SCHEDULE` in settings)
- **Timezone**: `Australia/Sydney`, UTC disabled (`CELERY_ENABLE_UTC = False`)

No custom retry configuration is defined on any Celery task. Exceptions propagate as task failures logged in Celery's Redis result backend. There are no `autoretry_for` or `max_retries` decorators anywhere.

### Celery Tasks (backend/tasks.py)

**`run_sms_jobs`**
- Schedule: every 60 seconds
- Action: calls `process_sms_jobs()` from `message.py`. Queries all `SMSSendJob` records where `scheduled_for <= now`, `cancelled=False`, `retry_count < 3`. For each, resolves the destination mobile number (checks `to_number` first, then conversation student/tutor mobile based on `message_type` prefix), sends via ClickSend API, creates an `SMSMessage` outbound record, marks the job `cancelled=True`. On send failure, increments `retry_count`, records `last_error` and `last_attempt_at`. After 3 failures the job is skipped permanently.

**`create_post_session_jobs`**
- Schedule: every 300 seconds (5 minutes)
- Action: finds `BookingAdhoc` and `BookingWeekly` occurrences that ended within the last 24 hours. For each, uses `get_or_create` with `booking_ref` (e.g. `adhoc_42`, `weekly_7_2026-04-14`) to create a `TutorJob` of type `post_tuition_review` with `expires_at = now + 14 days`. Also creates a linked `BookingOutcome` record with a snapshot of the student's current `StudentFocusArea` skills. On first creation, calls `_snapshot_student_progress(student, 'post_session')` to write a `WeeklyProgressSnapshot`.

**`record_weekly_progress_snapshots`**
- Schedule: Sunday at 12:00 UTC (= 10pm AEST Sunday)
- Action: for every active student (`role='student'`, `active=True`), checks if a `WeeklyProgressSnapshot` has been recorded since Monday of the current week. If not, calls `_snapshot_student_progress(student, 'scheduled')`.

**`flag_overdue_tutor_reviews`**
- Schedule: daily at 08:00 UTC (= 6pm AEST)
- Action: finds all incomplete `TutorJob` records of type `post_tuition_review` triggered more than 2 days ago. For each, checks whether an `AdminJob` of type `call_tutor_overdue_review` already exists with a matching `tutor_job_id:<id>` tag in notes. If not, creates one with a note identifying the tutor and student.

**`send_session_reminders`**
- Schedule: every 1800 seconds (30 minutes)
- Action: finds `BookingAdhoc` and `BookingWeekly` occurrences whose start time falls between 23 and 25 hours from now (the 24-hour reminder window). Deduplicates via `SMSSendJob.message_type` (e.g. `reminder_24h_adhoc_42`, `reminder_24h_weekly_7_2026-04-14`). If no duplicate exists and the student has a mobile number, creates an `SMSSendJob` addressed to the student with a reminder message.

**`create_weekly_session_jobs`**
- Schedule: daily at 20:00 UTC (= 6am AEST)
- Action: iterates all `TutorStudent` links where the student is active. If the pair has a `BookingWeekly`, completes any open `setup_weekly_session` TutorJob. If no weekly booking exists, uses `get_or_create` with `booking_ref = setup_weekly_{tutor_id}_{student_id}` to ensure exactly one open `setup_weekly_session` TutorJob exists (expires in 365 days).

### Scheduled/Cron Jobs Summary

| Task name | Schedule | AEST equivalent |
|---|---|---|
| `run_sms_jobs` | Every 60 s | Continuous |
| `create_post_session_jobs` | Every 300 s | Every 5 minutes |
| `send_session_reminders` | Every 1800 s | Every 30 minutes |
| `flag_overdue_tutor_reviews` | Daily 08:00 UTC | Daily 6pm AEST |
| `create_weekly_session_jobs` | Daily 20:00 UTC | Daily 6am AEST |
| `record_weekly_progress_snapshots` | Sunday 12:00 UTC | Sunday 10pm AEST |
| `check_payment_escalation` | External cron — not in Celery beat | Must be invoked separately |

Note: `check_payment_escalation` is a Django management command (`backend/management/commands/check_payment_escalation.py`), not a Celery task. It has no entry in `CELERY_BEAT_SCHEDULE` and must be run via `python manage.py check_payment_escalation` or an external cron.

### Job Model Details

**TutorJob — creator and completion matrix:**

| job_type | Created by | Completed by |
|---|---|---|
| `post_tuition_review` | `create_post_session_jobs` Celery task | Tutor submits review via `complete` endpoint |
| `send_progress_message` | Not found in current code scan (defined but no trigger) | — |
| `review_focus_area` | Not found in current code scan | — |
| `review_available_hours` | Tutor registration (views.py line 489); `visited_schedule` endpoint creates a deferred one 3 weeks after each visit | `visited_schedule` endpoint completes existing one |
| `setup_weekly_session` | `create_weekly_session_jobs` Celery task | `create_weekly_session_jobs` auto-completes when BookingWeekly exists |
| `set_fee` | Tutor registration (views.py line 484) | — |
| `payment_failed` | `_create_payment_failed_jobs()` helper on Stripe failure | — |
| `payment_overdue_7` | `check_payment_escalation` management command (7-day threshold) | — |
| `payment_overdue_14` | `check_payment_escalation` management command (14-day threshold) | — |
| `confirm_payment_receipt` | `payment_mark_paid` view (views.py line 7729) when parent marks payment as paid | `payment_confirm_receipt` view (line 7792) when tutor confirms |

**AdminJob — creator matrix:**

| job_type | Created by |
|---|---|
| `approve_tutor` | Tutor registration (views.py 481); admin jobs list view re-creates if missing |
| `approve_distributor` | Distributor registration (views.py 547); admin jobs list view re-creates if missing |
| `payment_failed` | `_create_payment_failed_jobs()` |
| `payment_overdue_7` | `check_payment_escalation` management command |
| `payment_overdue_14` | `check_payment_escalation` management command |
| `low_session_rating` | `payment_mark_paid` view when `rating <= 2` |
| `setup_bank_details` | Admin jobs list view if bank BSB/account not in GlobalSettings |
| `tutor_removed` | `remove_tutor` view (line 969) |
| `call_tutor_overdue_review` | `flag_overdue_tutor_reviews` Celery task |

AdminJobs have no auto-complete mechanism in tasks — completed manually by admin users through the UI.

**ParentJob — creator matrix:**

| job_type | Created by |
|---|---|
| `payment_due` | Defined in model; no creator found in visible code |
| `payment_failed` | `_create_payment_failed_jobs()` |
| `payment_overdue_7` | `check_payment_escalation` management command |
| `payment_overdue_14` | `check_payment_escalation` management command |

### Job Failure Handling

**Celery task failures:** No `autoretry_for` or `max_retries` on any task. `run_sms_jobs` wraps `process_sms_jobs()` in try/except, prints the error, and re-raises. Other tasks have no explicit exception handling — unhandled exceptions are captured by Celery and written to Redis results. No alert is generated for Celery task failures; they are only visible in Celery worker logs or via monitoring tools.

**SMS send failures (`SMSSendJob`):** On ClickSend API failure, `retry_count` is incremented and `last_error` is written. After 3 failures (`retry_count >= 3`), the job is permanently skipped by the `process_sms_jobs` query filter. No alert is generated for SMS failures — they are only visible by querying `SMSSendJob` records with `retry_count >= 3` and `cancelled=False`.

---

## 5. External Integrations

### 5.1 Stripe

**Purpose:** Card payment collection for tutoring sessions. Supports: SetupIntent to collect and store a card, off-session PaymentIntent charges (card-not-present billing after the session), and Stripe Connect transfers to distribute funds to tutors and distributors.

**Models involved:**
- `ParentPaymentProfile` — `stripe_customer_id`, `stripe_pm_id`, `card_last4`, `card_brand`, `setup_complete`
- `SessionPayment` — `stripe_payment_intent_id`, `stripe_customer_id`, `status`, `total_amount`, `tutor_amount`, `platform_amount`, `distributor_amount`
- `TutorProfile.stripe_account_id` — Stripe Connect destination for tutor payouts
- `DistributorProfile.stripe_account_id` — Stripe Connect destination for distributor commissions

**Views/functions that call Stripe:**

| View | URL | Stripe calls |
|---|---|---|
| `payment_setup_intent` | `POST /api/payments/setup-intent/` | `stripe.Customer.create`, `stripe.SetupIntent.create` |
| `payment_save_method` | `POST /api/payments/save-payment-method/` | `stripe.PaymentMethod.attach`, `stripe.Customer.modify`, `stripe.PaymentMethod.retrieve` |
| `_run_charge` (internal) | called from `payment_authorise`, `payment_retry` | `stripe.PaymentIntent.create`, `stripe.Transfer.create` |
| `payment_retry` | `POST /api/payments/<pk>/retry/` | re-attaches card if new `payment_method_id` provided, then calls `_run_charge` |

**Failure handling:**
- `_run_charge` catches `stripe.error.CardError` (returns `error_code='card_declined'`) and bare `Exception` (returns `error_code='stripe_error'`). Both return `(False, code, message)` to the caller.
- On failure, the caller calls `_create_payment_failed_jobs` which creates `ParentJob('payment_failed')`, `TutorJob('payment_failed')`, and `AdminJob('payment_failed')`.
- Stripe Connect transfers (tutor and distributor) are attempted after a successful charge. Transfer failures are silently logged via `logging.warning()` — the charge is not rolled back; money arrives at the platform but the sub-account transfer fails quietly with no user notification.

**Webhook endpoints:** None. There is no `/api/stripe/webhook/` in the URL configuration. `STRIPE_WEBHOOK_SECRET` is defined in settings but never consumed.

**Secret/key management:**

| Env var | Purpose |
|---|---|
| `STRIPE_SECRET_KEY` | Server-side secret (default placeholder `sk_test_placeholder`) |
| `STRIPE_PUBLISHABLE_KEY` | Baked into the CRA frontend bundle at Docker build time |
| `STRIPE_WEBHOOK_SECRET` | Defined in settings, never consumed |

`_get_stripe()` sets `stripe.api_key` from `settings.STRIPE_SECRET_KEY` at call time (not at import time).

---

### 5.2 LiveKit (Video Calling)

**Purpose:** Provides real-time video/audio rooms used during tutoring sessions. The backend mints short-lived JWT access tokens; the React frontend connects directly to the LiveKit server.

**Models involved:**
- `TutoringSession` — `room_name` (unique, format `t{tutor_id}-s{student_id}`), `last_called_at`, `student_joined_at`, `active_template`, `session_state`

**View:** `TutoringSessionViewSet.join` at `POST /api/sessions/join/`

**Token generation:**
```python
from livekit.api import AccessToken, VideoGrants
token = (
    AccessToken(api_key, api_secret)
    .with_identity(str(user.id))
    .with_name(user.get_full_name())
    .with_grants(VideoGrants(room_join=True, room=room_name))
    .to_jwt()
)
```
Returns `token`, `livekit_url`, `room_name`, and `active_template_id` to the frontend.

**Failure handling:**
- If any of `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL` are missing, returns HTTP 500 `{"error": "Livekit not configured on server"}`.
- Token generation exceptions return HTTP 500 `{"error": "Token generation failed: <exc>"}`.
- User must be either the tutor or the student in the room; otherwise HTTP 403.

**Env vars** (read via `os.environ.get(...)` directly at request time, not cached in settings):

| Env var | Purpose |
|---|---|
| `LIVEKIT_API_KEY` | JWT signing key |
| `LIVEKIT_API_SECRET` | JWT signing secret |
| `LIVEKIT_URL` | WebSocket URL returned to the frontend |

No webhook endpoint. No LiveKit event handler exists in the codebase.

---

### 5.3 ClickSend (SMS)

**Purpose:** Sends outbound SMS notifications: booking reminders, booking change notifications, payment notifications, and account approval messages. No inbound SMS handling.

**Models involved:** `SMSSendJob` (queue), `SMSMessage` (permanent record), `SMSConversation` (logical thread)

**Code:** `backend/backend/clicksend.py` contains `clicksend_send_sms(to_number, body)`. This calls `POST https://rest.clicksend.com/v3/sms/send` with HTTP Basic auth. `message.py` contains `process_sms_jobs()` and `sms_enqueue()`.

**Failure handling:**
- `clicksend_send_sms` raises `Exception` if `resp.status_code != 200` or `data["http_code"] != 200`.
- `process_sms_jobs` catches the exception, writes it to `job.last_error`, increments `job.retry_count`. After `retry_count >= 3`, job is permanently skipped.
- If no phone number can be resolved, the job is immediately marked `cancelled=True` with `last_error="No phone number"`.
- `GlobalSetting("sms_send")` (cached 2 min) gates live sends — if false, a fake send is logged with `provider_message_id = "FAKE-SEND"` and ClickSend is not contacted.

**Env vars:**

| Env var | Purpose |
|---|---|
| `CLICKSEND_USERNAME` | HTTP Basic auth username |
| `CLICKSEND_API_KEY` | HTTP Basic auth password |
| `CLICKSEND_FROM_NUMBER` | Shared sender number for all outbound SMS |
| `SMS_SEND` (also `GlobalSetting("sms_send")`) | Toggle — must be truthy to send live |

No inbound or delivery-report webhook.

---

### 5.4 Email (SMTP / SendGrid)

**Purpose:** Django's email framework sends welcome emails on registration and notification emails for tutoring-related events.

**Email sends:**
- `_send_tutor_welcome_email(tutor)` — called in a daemon thread from `register_tutor`; uses `EmailMultiAlternatives` with `backend/emails/welcome_tutor.html`
- `_send_parent_welcome_emails(parent, children_data)` — called in a daemon thread from `parent_home` on first visit (gated by `user.welcome_email_sent == False`); uses `backend/emails/welcome_parent.html`; sends plain text to each child
- `_send_emails()` inline in `select_tutor` and `request_tutor_mobile` — plain text only, `fail_silently=True`
- `AdminEmailViewSet.send` — manual admin-triggered bulk emails, recorded in `AdminEmailRecord`
- `ParentFeedbackViewSet.respond` — sends `backend/emails/parent_feedback_response.html`; records result in `AdminEmailRecord`

**Infrastructure:** Configured in `config/settings.py`. Default backend is `django.core.mail.backends.smtp.EmailBackend`. If `SENDGRID_API_KEY` env var is non-empty, backend switches to `anymail.backends.sendgrid.EmailBackend`.

**Env vars:**

| Env var | Default | Purpose |
|---|---|---|
| `EMAIL_HOST` | smtp.gmail.com | (project memory notes Zoho: smtp.zoho.com.au port 587) |
| `EMAIL_PORT` | 587 | |
| `EMAIL_HOST_USER` | (empty) | |
| `EMAIL_HOST_PASSWORD` | (empty) | App password |
| `DEFAULT_FROM_EMAIL` | SubjectMatter <noreply@subjectmatter.app> | |
| `SENDGRID_API_KEY` | (empty) | If set, switches to SendGrid backend |

**Failure handling:** Most transactional emails use `fail_silently=True` or bare `except Exception: pass`. Only emails sent via `AdminEmailRecord` flow have an audit trail of success/failure. No retry mechanism exists for failed emails.

---

## 6. State Machines and Business Logic

### SessionPayment Status Lifecycle

The `SessionPayment.status` field follows this progression:

```
pending → authorised → paid → confirmed
        → failed
        → overdue_7  (from pending/failed after 7 days)
        → overdue_14 (from overdue_7 after 14 days)
```

**Transition details:**

- `'pending'`: Created in `apply_payment` view (views.py line 3805) when the tutor submits the post-session review. A `Payment` record is also created at this point and `BookingOutcome.payment` is linked.
- `'authorised'`: Parent explicitly authorises the charge on their saved card. `authorised_at` is set.
- `'paid'`: Payment has been captured/charged. `paid_at` is set. `payment_summary` view checks `sp_obj.status == 'paid'` and sets `pending_confirmation = True` to indicate the tutor needs to confirm receipt.
- `'confirmed'`: Tutor confirms receipt of funds. `confirmed_at` is set. A `TutorJob` of type `'confirm_payment_receipt'` is created when transitioning to `'paid'` and completed when tutor confirms.
- `'failed'`: Charge attempt failed. `_create_payment_failed_jobs()` creates `TutorJob('payment_failed')`, `ParentJob('payment_failed')`, and `AdminJob('payment_failed')`.
- `'overdue_7'`: 7 days past due (set by `check_payment_escalation` management command). Creates `TutorJob('payment_overdue_7')`, `ParentJob('payment_overdue_7')`, `AdminJob('payment_overdue_7')`.
- `'overdue_14'`: 14 days past due (set by `check_payment_escalation`). Creates `TutorJob('payment_overdue_14')`, `ParentJob('payment_overdue_14')`, `AdminJob('payment_overdue_14')`. Sets `ParentChild.sessions_paused = True`.

### Payment Split Calculation

Performed in `apply_payment` view (lines 3664–3677 and 3765–3772):

```
amount_tutor       = hourly_rate × session_minutes / 60
                     (from StudentProfile.hourly_rate)
amount_platform    = platform_fee_per_hour × session_minutes / 60
                     (from GlobalSetting 'platform_fee_per_hour', default 5)
amount_distributor = distributor_fee_per_hour × session_minutes / 60
                     (from GlobalSetting 'distributor_fee_per_hour', default 5)
                   = 0.00 if no distributor linked
amount_paid (total) = amount_tutor + amount_platform + amount_distributor
```

All amounts are quantized to 2 decimal places using `Decimal.quantize`. The platform and distributor fees are **added on top** of the tutor's rate — the parent pays more than the tutor earns; the tutor receives the full hourly rate.

Distributor presence is determined by: student → `ParentChild.parent` → `DistributorParent.distributor`. If no `DistributorParent` row exists for the parent, `distributor=None` and `amount_distributor=0.00`.

The entire multi-record creation (both `Payment` and `SessionPayment`) is not wrapped in `transaction.atomic()`. There is no database unique constraint preventing duplicate `Payment` records for the same `BookingOutcome` (see Risk 4).

### Booking State

**BookingWeekly** has no status field — its only state is `confirmed` (Boolean, default `False`). Pausing is handled by `start_date`:
- `skip(weeks)` sets `start_date = now + timedelta(weeks=weeks)`.
- `remove_skip()` clears `start_date` to null.
- `next_occurrence()` computes the next real date dynamically. **Known bug:** `next_occurrence()` references module-level `today` set at import time, which stays frozen in long-running processes (see Risk 6).

**BookingAdhoc** has a `status` CharField with no enforced enum. The key lifecycle events are:
- Created via `booking_create_adhoc()` — no status explicitly set (defaults to empty string `''`).
- Set `confirmed=True` in `select_tutor` when a parent connects a child to a tutor and creates the weekly booking in one step.
- Hard-deleted when a student's tutor is removed (`remove_tutor` action).
- Replaced via `replace_this_weeks_adhoc()` when a student reschedules this week's session.

Cancellation for both types is implemented as hard deletion — there is no soft-cancel status field. The `student_can_edit()` method checks `cancellation_notice_hours` GlobalSetting (default 24 hours) and is exposed as `"student_can_edit"` in the API response.

**Double-booking prevention:** Existence checks in `booking_create_weekly()` (lines 324–330) and `booking_create_adhoc()` (lines 333–359) are not wrapped in `select_for_update()` or `transaction.atomic()`. No database-level unique constraints on `(tutor, weekday, start_time)` or `(tutor, start_datetime)` exist (see Risk 3).

### Competency System (7 Levels)

The active competency model uses `StudentSkillCompetency.level` (0–6) and `StudentTemplateProgress` per student per skill. The legacy `StudentSkillMatrix` model exists but is not used in active code.

**Level definitions and requirements:**

| Level | Label | Difficulty Served | Requirement |
|---|---|---|---|
| 0 | Not Started | easy | No correct answers yet |
| 1 | Developing | easy | All easy templates answered correctly at least once (`ever_correct` count >= template count) |
| 2 | Easy Complete | medium | All easy templates are "robust" (`has_robust` count >= template count) |
| 3 | Emerging | medium | All medium templates answered correctly at least once |
| 4 | Competent | hard | All medium templates are robust |
| 5 | Advanced | hard | All hard templates answered correctly at least once |
| 6 | Mastered | hard | All hard templates are robust |

Template counts are capped at `TEMPLATE_CAP = 6` per skill/difficulty.

**Difficulty mapping from level:**
- Levels 0–1: serve `'easy'`
- Levels 2–3: serve `'medium'`
- Levels 4–6: serve `'hard'`

**Robustness rule** (`update_template_progress`, competency.py lines 56–91):
A template is "robust" when the student answers it correctly in two separate sessions at least 6 days apart with no incorrect answer in between. Specifically:
- First correct answer: `ever_correct=True`, `streak_start_date=today`.
- Subsequent correct answer after 6+ days from `streak_start_date`: `has_robust=True`.
- Any incorrect answer resets: `streak_start_date=None`, `has_robust=False`.

**Level computation** (`_compute_deserved_level`, competency.py lines 133–161): Checks from level 6 down to 0. Odd levels (1, 3, 5) require `ever_correct_count >= template_count`. Even levels (2, 4, 6) require `robust_count >= template_count`. Only `Template.objects.filter(validated=True)` templates are counted.

**Regression on poor performance** (`recompute_skill_competency`, competency.py lines 164–195): If `session_correct / session_total < 50%`, the deserved level is reduced by 1 (minimum 0).

**Incorrect-answer guard** (views.py lines 1269–1271): After computing the new competency level, if the answer was incorrect and the new level is somehow higher than `prev_level` (captured before `update_template_progress` is called), it is clamped back to `prev_level`. Note: this guard can interfere with regression logic (see Risk 8).

**Overall score calculation** (`get_student_score`, competency.py lines 214–238):
- Fetches all leaf skills (no children) for the given grade from the matrix cache.
- Sums `level` values from `StudentSkillCompetency` for those skills (missing records count as 0).
- Returns `total_stars / (len(leaf_skills) * 4)`. Can exceed 1.0 for students at levels 5–6 (no cap applied).

**When snapshots are taken:**
- `StudentTemplateProgress` — updated after every answered question (`QuestionViewSet.record`).
- `StudentSkillCompetency` — recomputed immediately after each answered question.
- `SessionSkillSnapshot` — written per skill at the end of each tutoring session.
- `WeeklyProgressSnapshot` — written on post-session review (source='post_session') and Sunday evening (source='scheduled').
- `StudentFocusArea.level_before_learning` / `level_after_learning` — snapshotted when a learning `TestSession` starts and ends.

### TestSession State Machine

```
active → completed
       → abandoned
```

- Created as `'active'` (default).
- `'active'` → `'abandoned'`: When a new learning session starts for the same student, any existing active learning `TestSession` records are set to `'abandoned'` (views.py line 5310).
- `'active'` → `'completed'`: Set by the question engine when the session pool is exhausted or all skills are processed. If no templates are available at start, status is set to `'completed'` immediately (views.py lines 5326–5327).
- On completion, `TestSession.completed_at` is set, and `linked_focus_area.learning_done_week` / `linked_tutoring_focus_area.tutoring_done_week` are marked with the Monday date of the current week.

**Learning mode loop** (`_advance_to_question_learning_mode`, views.py ~line 5755):
State is tracked in `TestSession.mode_state` as: `loop` (1 or 2), `loop_remaining` (list of template IDs), `loop1_correct`, `loop1_total`, `skill_code`.
- Loop 1: all templates shown once. If all correct → promote difficulty for loop 2. If < 50% correct → demote difficulty for loop 2.
- Loop 2: templates shown at the adjusted difficulty.

### Template Status

`Template.status` enum values: `"draft"`, `"validated"`, `"published"`.

The `validated` boolean field (separate from `status`) is the operative gate — only `Template.objects.filter(validated=True)` records are served to students. The `toggle_validated` action (views.py line 1612) flips `template.validated`. No view directly writes `"validated"` or `"published"` to `status` via API. Templates are always created as `status="draft"`.

### Question Engine

**Template selection criteria:**
- `skill_detail__parent` (Skill-level node) matching the student's current skill
- `grade` matching the student's year level
- `difficulty__iexact` matching the difficulty derived from the student's competency level
- `validated=True` — only validated templates are served
- `language='en'` (or the student's configured language)

**Session pool:** The `record` endpoint tracks `seen_template_ids` and `session_template_ids`. `remaining_ids = [tid for tid in session_ids if tid not in seen_ids]`. Next template is selected with `.order_by("?")` (random). When `remaining_ids` is empty, `loop_complete=True` is returned.

**Template generation:** Uses `PreviewEngine` (engine.py): parse YAML → generate parameters (int/float/choice types) → evaluate constraints via `eval(expr, {}, ctx.parameters)` → substitute `{{expr}}` placeholders → render LaTeX as HTML. Up to 3 attempts are made to generate a valid question from a template before flagging it with an `auto_error` note. The `maths_engine.py` provides expression evaluators using SymPy with allowed functions: `nCr`, `nPr`, `hypergeom`, `factorial`, `lcm`, `gcd`, and fraction helpers.

**Known engine bug:** The constraint generation loop in `generate_parameters` (engine.py lines 90–101) contains a `return` statement on line 98 that exits unconditionally on the first iteration, making the retry loop dead code. Constraint violations on the first attempt will not be retried.

### ClassAssessment Status

`ClassAssessment.status` enum values: `"active"`, `"ended"`.

No automatic transition code was found in the reviewed files. Transitions are triggered by teacher-facing views (`start_assessment`, `end_assessment` actions on `TeacherViewSet`). When `status` → `"ended"`, `ended_at` is set.

---

## 7. API Surface

### REST Framework Configuration

Pure REST using Django REST Framework. All API endpoints are mounted at `/api/`. DRF `DefaultRouter` with trailing slash. Authentication: JWT via `rest_framework_simplejwt`. Access tokens expire after 24 hours; refresh tokens after 7 days with rotation and blacklisting on rotation. Tokens issued at `auth/jwt/login/` as `access` + `refresh` in the response body. Subsequent requests use `Authorization: Bearer <token>`.

**No throttle classes are configured.** `REST_FRAMEWORK` settings contain only `DEFAULT_AUTHENTICATION_CLASSES` and `DEFAULT_PERMISSION_CLASSES`. No `DEFAULT_THROTTLE_CLASSES`. No `DATA_UPLOAD_MAX_MEMORY_SIZE` override.

### Router-Registered ViewSets

| ViewSet | URL prefix | Notable actions |
|---|---|---|
| `QuestionViewSet` | `questions/` | `record` (submit answer / get next question) |
| `TemplateViewSet` | `templates/` | `list`, `retrieve`, `create`, `update`, `destroy`, `preview`, `generate`, `autosave`, `export_all`, `import_bulk`, `toggle_validated`, `flag_faulty`, `delete_all` |
| `SkillViewSet` | `skills/` | Full CRUD, `matrix`, `import_bulk`, `load_syllabus`, `export_all` |
| `TutorViewSet` | `tutors/` | Full ModelViewSet + `home`, `payments`, `feedback`, `toggle_looking`, `students`, `booking`, `edit`, `sms`, `sms_conversation`, `sms_activity`, `templates`, `availability`, `add_availability`, `remove_availability`, `block_day`, `unblock_day`, `session_settings`, `booking_action`, `visited_schedule`, `available_slots`, `admin_sms`, `admin_sms_conversation` |
| `StudentViewSet` | `students/` | `list`, `retrieve`, `create_student`, `home`, `edit`, `progress`, `booking`, `set_language` |
| `NoteViewSet` | `notes/` | Full ModelViewSet |
| `AuthViewSet` | `auth/` | `login`, `register`, `register_parent`, `register_tutor`, `register_distributor`, `register_teacher`, `parent_home`, `parent_payments`, `select_tutor`, `remove_tutor`, `request_tutor_mobile`, `launch_assessment`, `add_child`, `resolve_referral`, `exchange_token`, `dev_login`, `dev_switch_to_parent` |
| `BookingWeeklyViewSet` | `weekly_bookings/` | Full ModelViewSet + `skip`, `remove_skip` |
| `BookingAdhocViewSet` | `adhoc_bookings/` | Full ModelViewSet + `delete_override`, `modify_one_week` |
| `PreferenceViewSet` | `preferences/` | ModelViewSet + `set`, `flat` |
| `KnowledgeViewSet` | `knowledge/` | ModelViewSet + `import_bulk`, `preview`, `generate_from_image` |
| `TutoringSessionViewSet` | `sessions/` | `token`, `set_template`, `state`, `next_question`, `end_session`, `student_skills`, `learn_mode`, `incoming_call` |
| `TestViewSet` | `tests/` | `start`, `answer`, `report`, `abandon`, `quit_early`, `past` |
| `YearViewSet` | `years/` | Full ModelViewSet + `import_years` |
| `FocusAreaViewSet` | `focus-areas/` | `list`, `create`, `destroy`, `complete_learning`, `move_up`, `move_down` |
| `TutorJobViewSet` | `jobs/` | `list`, `progress_message`, `save_progress_message`, `send_progress_message`, `payment_summary`, `apply_payment`, `complete` |
| `DistributorViewSet` | `distributors/` | `retrieve` only |
| `AdminJobViewSet` | `admin-jobs/` | `list`, `approve`, `dismiss`, `bank_details`, `save_bank_details`, `payments` |
| `AdminEmailViewSet` | `admin-emails/` | `list_emails`, `send` |
| `ParentFeedbackViewSet` | `parent-feedback/` | `list`, `create`, `respond` |
| `TemplateGroupViewSet` | `template_groups/` | ReadOnlyModelViewSet + `trio`, `create_easy`, `create_medium`, `create_hard` |
| `TeacherViewSet` | `teachers/` | `home`, `create_class`, `import_students`, `email_credentials`, `reset_student_password`, `class_detail`, `gap_report`, `class_add_focus`, `class_remove_focus`, `start_assessment`, `end_assessment`, `assessment_dashboard`, `mark_absent` |
| `AssessmentViewSet` | `assessments/` | `active`, `join`, `record_answer` |

### Non-Router (Path) Endpoints

| Path | View function | Notes |
|---|---|---|
| `auth/jwt/login/` | `SuperuserRoleTokenView` | Public; issues access + refresh tokens |
| `auth/jwt/refresh/` | `TokenRefreshView` | Public; rotates refresh token |
| `docs/` | `editor_docs` | |
| `docs/messages/` | `messages_docs` | |
| `payments/setup-intent/` | `payment_setup_intent` | Parent creates Stripe SetupIntent |
| `payments/save-payment-method/` | `payment_save_method` | Parent saves card after SetupIntent |
| `payments/pending/` | `payment_pending` | Parent views pending payments |
| `payments/tutor-billing/` | `tutor_billing` | Tutor views billing summary |
| `payments/admin-feedback/` | `admin_feedback` | Admin views all session ratings |
| `payments/<int:pk>/` | `payment_detail` | Admin/parent/tutor access with ownership check |
| `payments/<int:pk>/authorise/` | `payment_authorise` | Parent authorises charge |
| `payments/<int:pk>/confirm/` | `payment_confirm_receipt` | Tutor confirms receipt |
| `payments/<int:pk>/retry/` | `payment_retry` | Parent retries failed payment |
| `parents/<int:pk>/payments/` | `parent_payment_history` | Parent or admin views payment history |
| `admin/activity/` | `admin_activity` | Admin-only activity feed |
| `settings/` | `system_settings` | Public; returns platform fee and dev user list |
| `admin/variables/` | `admin_variables` | Admin-only GlobalSetting read/write |

---

## 8. Notifications and Communications

### Email

#### 1. Tutor Welcome / Application Received
- **Trigger:** `register_tutor` endpoint; fires once at registration in a daemon thread.
- **Recipient:** The registering tutor.
- **Subject:** "Welcome to Subject Matter — application received"
- **Template:** `backend/emails/welcome_tutor.html` (placeholders: `[FIRST_NAME]`, `[TUTOR_EMAIL]`, `[SITE_URL]`, `[SITE_DOMAIN]`). Falls back to plain text if file is unreadable.
- **Failure handling:** `except Exception: pass` — silent failure, no retry, no audit log.

#### 2. Parent Welcome
- **Trigger:** First call to `parent_home` endpoint after registration; gated by `user.welcome_email_sent == False`. Sets flag to `True` before dispatch (fires exactly once).
- **Recipient:** The parent user.
- **Subject:** "Welcome to Subject Matter"
- **Template:** `backend/emails/welcome_parent.html` (placeholders: `[FIRST_NAME]`, `[ASSESSMENT_SENTENCE]`). Falls back to plain text.
- **Failure handling:** `except Exception: pass` — silent, no retry, no audit log.

#### 3. Student Welcome
- **Trigger:** Same `parent_home` path as #2; iterates over `children_data`.
- **Recipient:** Each student/child with a recorded email address.
- **Subject:** "Welcome to SubjectMatter"
- **Template:** Plain text only via `send_mail` with `fail_silently=True`. Note: `backend/emails/welcome_student.html` exists on disk but is NOT loaded in code.
- **Failure handling:** `fail_silently=True`.

#### 4. Tutor Confirmed / New Student Matched
- **Trigger:** `select_tutor` endpoint when a parent connects a child to a tutor.
- **Recipients:** Two emails — one to the parent, one to the tutor.
- **Subjects:** Parent: "Your tutor has been confirmed — {tutor_full_name}"; Tutor: "New student — {child_full_name}".
- **Template:** Plain text only, built inline.
- **Failure handling:** `fail_silently=True`.

#### 5. Tutor Contact Number to Parent
- **Trigger:** `request_tutor_mobile` endpoint.
- **Recipients:** Parent (containing tutor mobile) and tutor (alerting them to expect a call).
- **Subjects:** Parent: "{tutor_full_name}'s contact number"; Tutor: "A parent will be calling you".
- **Template:** Plain text only.
- **Failure handling:** `fail_silently=True`.

#### 6. Parent Feedback Response
- **Trigger:** Admin calls `ParentFeedbackViewSet.respond`.
- **Recipient:** The parent who submitted the feedback.
- **Subject:** "We've responded to your feedback — Subject Matter"
- **Template:** `backend/emails/parent_feedback_response.html` (placeholders: `[FIRST_NAME]`, `[ORIGINAL_FEEDBACK]`, `[RESPONSE]`). Falls back to plain text.
- **Failure handling:** Outcome (sent/failed + error string) recorded in `AdminEmailRecord`. The only email type with an audit trail.

#### 7. Admin Bulk / Ad-hoc Email
- **Trigger:** Admin calls `AdminEmailViewSet.send` with `recipient_type` of `custom`, `all_parents`, `all_tutors`, or `all_students`.
- **Recipients:** Custom email address OR all active users of a given role.
- **Template:** Plain text only.
- **Failure handling:** Per-recipient status recorded in `AdminEmailRecord`. Continues to next recipient on failure.

Note: `backend/emails/assessment_report.html` exists on disk but no code path sends it.

### SMS — All Types

All SMS uses ClickSend via `SMSSendJob` queue. The `GlobalSetting` key `sms_send` is a system-wide feature flag; when false, messages are logged as "FAKE-SEND" with no ClickSend contact.

#### 1. Booking Lifecycle SMS
- **Trigger:** Any of 24 booking state changes defined in `SMS_TEMPLATES` in `message.py`: create, update, confirm, unconfirm, skip, unskip, cancel (each for adhoc and weekly) from student, parent, or tutor actors.
- **Recipient:** When actor is student or parent → tutor's `TutorProfile.mobile`. When actor is tutor → student's `StudentProfile.mobile`.
- **Deduplication:** `sms_enqueue()` writes or updates an `SMSSendJob` scheduled `sms_pause` minutes in the future (default 10 min via GlobalSetting). Identical `message_type` jobs are coalesced.
- **Type:** Transactional, debounced.

#### 2. Session Reminder (24-hour)
- **Trigger:** `send_session_reminders` Celery task every 30 minutes. Finds bookings starting 23–25 hours from now.
- **Recipient:** Student mobile (`StudentProfile.mobile`).
- **Message content:** "Hi {first_name}, your next booking with {tutor_first_name} is {date_and_time}. If things change, call {tutor_first_name} to discuss on {tutor_mobile}."
- **Deduplication:** `message_type = reminder_24h_adhoc_{booking.id}` or `reminder_24h_weekly_{booking.id}_{date}`.

#### 3. Account Approval SMS
- **Trigger:** Admin approves a tutor or distributor via `AdminJobViewSet.approve`.
- **Recipient:** The newly approved user's mobile.
- **Message content:** "Hi {first_name}, your SubjectMatter {role} account has been approved. Welcome aboard. You can now log in at subject-matter.com.au"
- **Delivery:** Creates `SMSSendJob` scheduled for now and calls `process_sms_jobs()` synchronously on the request thread.

#### 4. New Student Notification to Tutor
- **Trigger:** `select_tutor` endpoint when parent connects child to tutor.
- **Recipient:** Tutor mobile (`TutorProfile.mobile`).
- **Message content:** "Hi {tutor_first_name}, you have a new student: {child_full_name}. [Your first session is {session_line}.] Please contact their parent to confirm the details."

#### 5. Tutor Removal Notification
- **Trigger:** `remove_tutor` endpoint.
- **Recipient:** The removed tutor's mobile (`TutorProfile.mobile`).
- **Message content:** "Hi {tutor_first_name}, {student_name}'s family has ended the tutoring arrangement. Thank you for your work with SubjectMatter."

#### 6. Post-Session Parent Message
- **Trigger:** Tutor calls `TutorJobViewSet.send_progress_message` after completing post-tuition review.
- **Recipient:** The student's parent mobile, looked up via `ParentChild` → parent → `StudentProfile` chain.
- **Message content:** Free-form text from the tutor's `BookingOutcome.parent_message`.

### SMS Retry and Failure Handling

For each due `SMSSendJob` (`scheduled_for <= now`, not cancelled, `retry_count < 3`):
- **Success:** `job.cancelled = True`, `SMSMessage` row created with direction=outbound and the ClickSend `message_id`.
- **Failure:** `job.retry_count += 1`, `job.last_error` = error text, `job.last_attempt_at` = now. Job remains uncancelled for next Celery tick.
- **After 3 failures:** Permanently skipped by the `retry_count < 3` filter. No admin alert raised.
- **No phone number:** Job immediately cancelled with `last_error = "No phone number"`.

### Notification Preferences

No opt-out or preference system exists. Observations:
- `UserPreference` model exists but no preference keys related to email or SMS opt-out were found.
- `GlobalSetting.sms_send` is a system-wide switch only.
- Whether SMS is sent depends on whether the recipient's mobile field is populated. A blank mobile silently skips the send.
- No unsubscribe link is present in any email template or email body in the codebase.

---

## 9. File Uploads and Media

### 9.1 File Upload Flows

**Template/skill/knowledge YAML imports:**

| Endpoint | ViewSet action | Format |
|---|---|---|
| `POST /api/templates/import_bulk/` | `TemplateViewSet.import_bulk` | YAML or JSON |
| `POST /api/skills/import_bulk/` | `SkillViewSet` import action | YAML or JSON |
| `POST /api/knowledge/import_bulk/` | `KnowledgeViewSet.import_bulk` | YAML |
| `POST /api/years/import_years/` | `YearViewSet.import_years` | YAML |

All four read the file with `uploaded.read().decode("utf-8")` and parse with `yaml.safe_load` or `json.loads` based on file extension. No size limit is enforced in application code. No file is persisted to disk — it is parsed in memory and discarded.

**Tutor logo (profile image):**

`TutorProfile.logo = models.ImageField(upload_to='branding/', null=True, blank=True)`. This is the only `ImageField` in the codebase. Uses Django's default file storage.

### 9.2 Storage Backend

There is no `MEDIA_ROOT`, `MEDIA_URL`, `DEFAULT_FILE_STORAGE`, or S3/cloud storage configuration in `config/settings.py`. Django's default `FileSystemStorage` is used. In production on Railway this means uploaded files (tutor logos) are written to the container's local filesystem, which is ephemeral — files are lost on redeploy.

Static assets (the CRA build output and collected Django statics) are served by WhiteNoise from `/app/backend/staticfiles/`. WhiteNoise is not used for media uploads.

### 9.3 Size and Type Validation Rules

There are no explicit file size or MIME-type validation rules in the application code for any upload flow. Bulk-import endpoints rely entirely on YAML/JSON parse errors to reject malformed content. The `ImageField` for tutor logos relies on Django's default `ImageField` validation (requires Pillow to verify it is a valid image), but no maximum size is enforced in application code.

---

## 10. Known Complexity and Risk Areas

### Risk 1 — Unauthenticated Developer Endpoints Reachable in Production (CRITICAL — Security)

`AuthViewSet` exposes `dev_login` at `POST /api/auth/dev_login/` and `dev_switch_to_parent` at `POST /api/auth/dev_switch_to_parent/`, both with `permission_classes=[AllowAny]` and no `settings.DEBUG` guard.

`dev_login` accepts a username string and issues a full session login for any of three hardcoded accounts (admin, Alex, Blair) with no password check.

`dev_switch_to_parent` accepts a `student_id` in the request body and issues a JWT for that student's parent, again with no authentication requirement.

There is no environment guard preventing these routes from being active in production. Any unauthenticated caller can obtain admin access or impersonate any parent.

The `/api/settings/` endpoint (public, `AllowAny`) returns the list of dev user credentials, potentially exposing the hardcoded usernames.

**Test cases to create:**
- Verify `POST /api/auth/dev_login/` returns 404 or 403 when `settings.DEBUG = False`.
- Verify `POST /api/auth/dev_switch_to_parent/` is inaccessible without an authenticated admin session in production.
- Verify `/api/settings/` does not expose dev credentials in a non-DEBUG environment.

---

### Risk 2 — Plaintext Passwords Stored in the Database (CRITICAL — Security)

`StudentProfile.plain_password` (`CharField(max_length=50)`, models.py line 618) stores the student's plaintext password. It is written at account creation (views.py line 7031) and on password reset (views.py line 7113). The value is returned over the API to the teacher's frontend via a `pin` key in API responses (views.py line 7046 and line 7371).

A database read, SQL injection attack, or compromised backup exposes every student credential in cleartext.

**Test cases to create:**
- Assert `StudentProfile.plain_password` is `None` after all account creation paths.
- Assert the `reset_student_password` endpoint response does not include a plaintext password field.
- Scan all API response serialisers for `plain_password` field inclusion.
- Verify that the `email_credentials` teacher endpoint does not return readable passwords over the wire in production.

---

### Risk 3 — Booking Double-Booking Race Condition (HIGH — Concurrency / Data Integrity)

`booking_create_adhoc()` (models.py lines 333–359) checks slot availability by computing available slots and then creates a `BookingAdhoc` record. There is no `select_for_update()` and no database unique constraint on `(tutor, start_datetime)`.

`booking_create_weekly()` (lines 316–331) checks for duplicates and overlaps in Python then calls `create`, but these two reads and the subsequent write are not wrapped in `transaction.atomic()`.

Two concurrent requests for the same slot would both pass the availability check and both create overlapping bookings.

**Test cases to create:**
- Concurrent integration test: two simultaneous `POST booking_action create` requests for the same ad-hoc slot; assert only one `BookingAdhoc` is created.
- Unit test for `booking_create_weekly` verifying the overlap constraint fires correctly when times are adjacent vs overlapping.
- Test that a booking created between the slot-check and the DB insert is detected.

---

### Risk 4 — Payment Calculation Without DB Atomicity (HIGH — Financial / Data Integrity)

The `apply_payment` view (views.py lines 3717–3808) creates both a `Payment` and a `SessionPayment` record in sequence with no `transaction.atomic()` wrapper. If the server crashes or an exception is thrown between the two `objects.create()` calls, a `Payment` record will exist without a corresponding `SessionPayment`, making the parent's home page inconsistent.

The idempotency check (`if outcome.payment_id: return 400`) before the creation is not inside a database transaction or `select_for_update()` block. Two concurrent POST requests from the same tutor could both read `outcome.payment_id = None`, pass the guard, and create duplicate `Payment` and `SessionPayment` records. There is no `unique_together` constraint on `BookingOutcome.payment` to prevent this at the DB level.

Additionally, `platform_fee_per_hour` and `distributor_fee_per_hour` are read from `GlobalSetting` (cached for 2 minutes), meaning a fee change during that window could apply inconsistently across concurrent payments.

**Test cases to create:**
- Test that `apply_payment` creates both `Payment` and `SessionPayment` atomically — simulate DB error after first write and verify neither record exists.
- Test the fee arithmetic: `amount_tutor + amount_platform + amount_distributor == amount_paid` for various session durations and rates.
- Test calling `apply_payment` twice on the same `TutorJob` returns 400, not 200, and produces no duplicate records.
- Test that Stripe Connect transfer failure (tutor payout) does not roll back the parent charge.

---

### Risk 5 — `eval()` on User-Controlled Template Content (HIGH — Security / Correctness)

`PreviewEngine.evaluate_constraints` (engine.py line 126) calls `eval(expr, {}, ctx.parameters)` on constraint expressions loaded from YAML template content. `evaluate_expressions` (lines 143–147) also calls `eval(expr, {}, ctx.parameters)` on `{{...}}` blocks inside question/answer/solution text.

While the namespace is restricted, Python's `eval` with empty globals still has access to builtins and can be manipulated with dunder attribute access. Any user with template-editing access (tutors with `TutorProfile.edit_syllabus=True`, or any unauthenticated user since `TemplateViewSet` is `AllowAny`) can inject arbitrary Python.

Additionally, the constraint generation retry loop in `generate_parameters` (engine.py lines 90–101) contains a `return` statement on line 98 that exits unconditionally on the first iteration — the retry loop is dead code. Constraint violations on the first attempt are never retried.

**Test cases to create:**
- Submit template content with `{{__import__('os').system('id')}}` via `POST /api/templates/preview/` and assert it is rejected or sandboxed.
- Unit test that a constraint expression with `__builtins__` access raises an appropriate error.
- Unit test that the parameter generation retry loop actually retries when a constraint fails (verifying the dead code bug).
- Verify that an unauthenticated user cannot use `POST /api/templates/generate/` to execute arbitrary code.

---

### Risk 6 — `next_occurrence()` Uses a Module-Level `today` Snapshot (HIGH — Correctness / Booking)

`BookingWeekly.next_occurrence()` (models.py lines 503–515) references the variable `today` which is set once at module import time (models.py line 23: `today = now.date()`). In a long-running Gunicorn/uWSGI process, `today` remains frozen at the date the module was first loaded.

All functions affected: `next_weekly_booking`, `booking_mode`, `BookingWeekly.skip()`, and `student_can_edit()`. The `skip()` method (line 495) also uses the module-level `now` when computing `self.start_date = now + timedelta(weeks=weeks)`.

After midnight following the server startup date, all"After midnight following the server startup date, all weekly booking next-occurrence calculations will be wrong — the booking system will display incorrect upcoming session dates and the cancellation window check (`student_can_edit()`) will apply the wrong cutoff time."

**Test cases to create:**
- Unit test calling `next_occurrence()` with a mocked `date.today()` set to a date different from the module's import date; assert the result reflects the mocked date, not the import date.
- Unit test that `skip()` sets `start_date` relative to the actual current time, not import time.
- Integration test verifying a weekly booking due tomorrow is not shown as "no upcoming booking" when the server has been running since yesterday.
- Test that `student_can_edit()` correctly computes the 24-hour cutoff relative to the real current time.

---

### Risk 7 — Cross-User Data Isolation Gaps (HIGH — Security / Authorization)

Several views accept user IDs as POST body parameters and query the database using them without verifying ownership:

- `QuestionViewSet.record` (views.py line 1204) accepts `student_id` and `template_id` from the request body and creates a `Question` for that student with no check that `request.user` is the assigned tutor or the student themselves. Any authenticated user can record question attempts on behalf of any student.

- `TutorViewSet.edit` (lines 3004–3031) calls `self.get_object()` based on the URL `pk`. There is no check that `request.user` is the same tutor or an admin — any authenticated tutor can modify another tutor's profile.

- `TemplateViewSet` has `permission_classes = [AllowAny]` at class level, meaning unauthenticated users can list all templates, preview them, and call `delete_all` (the latter has its own admin check, but the viewset default is fully open).

- `SkillViewSet` also has `permission_classes = [AllowAny]` — the entire skill/syllabus hierarchy and all CRUD operations are publicly accessible.

**Test cases to create:**
- Test that a parent JWT cannot `POST /api/questions/record/` with a `student_id` belonging to a different family.
- Test that a tutor cannot `PUT /api/tutors/{other_tutor_id}/` and modify another tutor's profile.
- Test that an unauthenticated request to `DELETE /api/templates/{id}/` is rejected.
- Test that `delete_all` requires admin role even though the viewset is otherwise open.
- Test that `GET /api/students/` returns an empty list or 403 to unauthenticated callers (currently returns full student list including names, emails, and tutor assignments).

---

### Risk 8 — Competency Regression and Star-Count Correctness Logic (MEDIUM-HIGH — Correctness / Education)

Three specific fragile interactions exist in the competency system:

**Interaction 1 — Incorrect-answer guard conflicts with regression:**
`prev_level` is captured before `update_template_progress` is called (views.py lines ~1260). If an incorrect answer breaks the robustness streak and `recompute_skill_competency` returns a lower level than `prev_level`, the guard at lines 1269–1271 snaps the level back to `prev_level`, restoring a level that should have been reduced.

**Interaction 2 — No hard templates edge case:**
`_compute_deserved_level` (competency.py lines 133–161) evaluates from level 6 down. If a skill has medium templates that are all robust but has zero hard templates, `hard_total > 0` is `False`, the hard-level checks are skipped, and the medium path correctly produces level 4. However, if `hard_total == 0` and `medium_robust_count >= medium_template_count`, the function produces level 4 and stops — the student cannot advance beyond level 4 for that skill regardless of effort.

**Interaction 3 — Progress score can exceed 100%:**
`get_student_score` (competency.py lines 214–238) divides by `len(leaf_skills) * 4`. Students at levels 5–6 produce values above 1.0. The function's docstring acknowledges this, but callers that multiply by 100 and display as a percentage will show values above 100% with no cap, which may confuse parents and students.

**Test cases to create:**
- Unit test: answer incorrectly when `prev_level == 2` after robustness streak; assert `comp.level <= 2` after the guard, not restored to 2 when recompute gave 1.
- Unit test: a skill with only easy templates; verify levels 0–2 are achievable and 3–6 are not, and that incorrect answers below the 50% threshold correctly reduce the level.
- Unit test: `get_student_score` with a student at level 6 on all skills; assert the float exceeds 1.0 and verify calling code handles this gracefully (does not display "150%").
- Property-based test: any sequence of all-correct answers must result in a monotonically non-decreasing `StudentSkillCompetency.level`.
- Unit test confirming a skill with zero hard templates caps a student at level 4.

---

### Risk 9 — `get_student_profile()` and `get_tutor()` Reference Bugs (MEDIUM — Correctness / Reliability)

`User.get_student_profile()` (models.py lines 70–75): The variable `profile` is used on line 73 (`if not profile`) without being initialised if `self.role != "student"`. Calling this on a non-student user raises `UnboundLocalError`.

`User.get_tutor()` (models.py lines 77–86) for the parent role: sets `tutor_link` inside an `if child_link:` block but accesses `tutor_link` on line 85 outside that block with no guard, causing `UnboundLocalError` if the student has no `TutorStudent` record.

`_get_parent_mobile` (views.py lines 3349–3367): A comment states it should check the parent's mobile first, but the parent branch does nothing (`pass`) — the parent's phone number is never returned even if populated. The fallback reads `StudentProfile.mobile` instead.

**Test cases to create:**
- Unit test: call `get_student_profile()` on a tutor `User`; assert it returns `None` or raises a controlled exception rather than `UnboundLocalError`.
- Unit test: call `get_tutor()` on a parent `User` whose child has no `TutorStudent` link; assert it returns `None` rather than raising `UnboundLocalError`.
- Unit test: call `_get_parent_mobile` on a student whose parent has a phone number set; assert the parent's number is returned (currently it is not).

---

### Risk 10 — Complete Absence of Automated Tests (HIGH — All Areas)

`backend/backend/tests.py` contains only the Django scaffold comment `# Create your tests here.` — it is entirely empty. The diagram-specific test files (`test_tree_diagram.py`, `test_venn_diagram.py`, `test.py`, `test_render.py`) are standalone scripts in `backend/backend/diagram/`, not Django `TestCase` subclasses, and are not part of the test suite runner.

This means:
- No regression safety net for any of the nine risk areas above.
- No CI coverage for payment split arithmetic, competency level transitions, booking overlap detection, the `next_occurrence` date bug, the `eval` sandbox, or the cross-user authorisation checks.
- Refactoring or Django version upgrades carry unknown blast radius.

**Minimum test infrastructure to create:**
- Django `TestCase` subclasses for `update_template_progress` and `recompute_skill_competency` covering all level transitions (0→1, 1→2, robustness reset, regression below 50% threshold).
- `APITestCase` subclasses for `register_parent`, `booking_action create` (overlap case), `apply_payment` (idempotency), `QuestionViewSet.record` (ownership), and the dev endpoint guard.
- A smoke test that imports all models without raising `AppRegistryNotReady`.
- A fixture-based test verifying `next_occurrence()` returns the correct date when called the day after module import.
- A security scan test asserting that `POST /api/auth/dev_login/` returns 403 in non-DEBUG mode.

---

### Additional Risk — Frontend Auth Protection Gaps

Two routes are not wrapped in `ProtectedRoute` in `App.tsx`:
- `/tutors/:id/sms`
- `/tutors/:id/sms/:conversationId`

These routes render without any JWT check. While the underlying API calls from those pages do require a JWT, the pages themselves load for any browser visitor. The `ProtectedRoute` implementation itself only checks for the presence of `localStorage.access` and `localStorage.user` keys — it does not decode the JWT or verify expiry. An expired token sitting in localStorage will pass the `ProtectedRoute` check and the user will see the page UI before API calls start returning 401.

The token refresh logic in `apiFetch.ts` does handle 401 responses automatically by calling `POST /api/auth/jwt/refresh/`. However, if the refresh token is also expired, all three localStorage keys are cleared and the user is not explicitly redirected to `/login` — the API call simply fails and the page is left in an error state.

**Test cases to create:**
- Verify that navigating directly to `/tutors/1/sms` without a token renders a login redirect (currently does not).
- Verify that an expired access token with a valid refresh token results in a seamless token refresh, not a visible error.
- Verify that an expired refresh token results in a redirect to `/login`, not a broken page state.
- Verify that `localStorage.access = "not-a-real-jwt"` does not bypass any page that should require a valid session.