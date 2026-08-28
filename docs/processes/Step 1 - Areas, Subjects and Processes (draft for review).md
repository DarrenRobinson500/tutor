# Step 1: areas, subjects and processes (draft for review)

This is Step 1 only, as the note requires: the row list in prose, not the filled sheets. Nothing here is a Register, Trigger, Workflow, Dashboard, Document or Report cell, and nothing here is yet marked as a named process, a GAP or an n/a on Map. That is Step 2, and it starts after this list is agreed.

For each area: the source it comes from (section 5 of the note: 1 value chain, 2 external requirement, 3 keeps the business running, 4 what happens when something goes wrong), a short note on what is peculiar about it, and its subjects with the real-world events that act on each one.

Everything describing what the platform does is grounded in the codebase (`backend/models.py`, `backend/views.py`, `backend/tasks.py`, `config/settings.py`) and cross-checked against `SYSTEM_DESCRIPTION.md`. Anything I could not verify in the code is marked **[unverified]**. Anything that is my inference about the business rather than a read of the code is marked **[inferred]**. Open calls for the design phase are marked with `[QUESTION - design phase: ...]`, per rule 4.

---

## Area: Acquisition and referral
**Source:** 1 (value chain — the front of it).

Marketing itself (the public landing pages for parents, tutors, teachers, distributors, and the competition page) is informational only. There is no lead-capture or enquiry form anywhere in the code **[verified absent — no contact/enquiry endpoint in `views.py`]**; the first thing the platform records about a prospective customer is a full registration. The one exception is a distributor's referral code, which is tracked from first contact.

- **Referral code** — a distributor's unique code, resolved before a parent registers. Real-world events: issuing a code to a distributor (happens as a side effect of distributor approval, not a process of its own), a prospective parent presenting a code (`resolve_referral`), and the code being linked to the parent's account at registration (`DistributorParent`).

`[QUESTION - design phase: does the business consider the public marketing pages themselves in scope for this exercise, given they carry no process, or are they out of scope as pure content?]`

---

## Area: Account onboarding and approval
**Source:** 1 (value chain — acquiring each type of user).

Five distinct registration paths exist, and two of them (tutor, distributor) are gated behind manual admin approval before the account can do anything; two (parent, student) are not gated at all; teacher is auto-approved.

- **Parent account** — created via `register_parent`, together with the first child in one step. Real-world events: registering, adding a further child (`add_child`), updating own details (`update_parent_details`).
- **Tutor application** — created via `register_tutor`. Held inactive (`User.active=False`, `TutorProfile.approved=False`) until admin approval. Real-world events: applying, being approved (`AdminJob 'approve_tutor'`, SMS sent on approval), being declined **[unverified — no decline/reject code path found; the AdminJob has `approve`/`dismiss` actions but I have not traced what `dismiss` does to the applicant's account]**.
- **Distributor application** — created via `register_distributor`. Same gated shape as tutor. Real-world events: applying, being approved (`AdminJob 'approve_distributor'`), being declined **[unverified, same caveat as tutor]**.
- **Teacher account** — created via `register_teacher`. Auto-approved (`TeacherProfile.approved=True` by default), unlike tutor and distributor. Real-world events: registering only; no approval event exists for this subject.
- **Student account** — created either by a parent (`add_child`) or a teacher (`import_students` / `create_student`). No approval gate. Real-world events: creation by parent, creation/import by teacher, a welcome email being sent once (`welcome_email_sent` flag).

`[QUESTION - design phase: what happens to a tutor or distributor application on rejection. AdminJobViewSet has a "dismiss" action but its effect on the underlying account is not something I traced; worth confirming before this becomes a Map cell, since "n/a: nothing to remediate" and "GAP: no reject path" are very different findings.]`

---

## Area: Tutor-student matching and roster
**Source:** 1 (value chain — matching).

- **Tutor-student assignment** (`TutorStudent`) — links one tutor to one student. Real-world events: a parent selecting a tutor for a child (`select_tutor`, which also creates the first weekly booking and sends parent/tutor emails and an SMS to the tutor), a parent or tutor ending the arrangement (`remove_tutor`, which hard-deletes the student's `BookingAdhoc` rows, creates `AdminJob 'tutor_removed'`, and sends the tutor an SMS).
- **Parent-child link** (`ParentChild`) — links a parent to their child, and carries `sessions_paused`. Real-world events: creation alongside parent registration or `add_child`; being paused (set by the payment-overdue path, not by a person); no explicit "unpause" event was found **[unverified — I did not find code that clears `sessions_paused` back to False other than the underlying payment being brought current, which I have not traced end to end]**.

---

## Area: Booking and scheduling
**Source:** 1 (value chain — booking).

- **Weekly booking** (`BookingWeekly`) — a recurring slot. Real-world events: creation (`booking_create_weekly`), pausing for a period (`skip`), resuming (`remove_skip`), one-off rescheduling for a single week (`modify_one_week`), deletion. No status field beyond `confirmed`; cancellation is hard deletion, not a soft-cancel state.
- **Ad-hoc booking** (`BookingAdhoc`) — a single appointment. Real-world events: creation (`booking_create_adhoc`, checked against tutor availability and blocked days), confirmation (set `True` as a side effect of `select_tutor`), rescheduling this week's occurrence, cancellation (hard deletion, subject to the `cancellation_notice_hours` window via `student_can_edit`).
- **Tutor availability** (`TutorAvailability`) — recurring weekly windows a tutor is bookable in. Real-world events: setting/adding a window, removing one.
- **Tutor blocked day** (`TutorBlockedDay`) — a specific date a tutor is unavailable. Real-world events: blocking a day, unblocking it.

`[QUESTION - design phase: cancellation for both booking types is a hard delete with no retained record of what was cancelled or why. Is that acceptable as a permanent design choice (n/a) or a gap for a business that may need a cancellation history for disputes or patterns of late cancellation?]`

---

## Area: Session delivery
**Source:** 1 (value chain — delivering the service).

- **Tutoring session** (`TutoringSession`) — a live video session between one tutor and one student, backed by LiveKit. Real-world events: starting (token issued via `sessions/token/`, `room_name` unique per tutor-student pair), the tutor joining (`last_called_at`), the student joining (`student_joined_at`), in-session state changes (active template, focus-area selection), ending (`end_session`, which writes a `SessionSkillSnapshot` per skill).
- **In-session question practice** — a student answering `Question` instances generated from a `Template` during the session. Real-world events: a question being served, an answer being recorded (`QuestionAttempt`), help being requested.

No LiveKit webhook exists, so the platform has no record of session quality events (dropped connections, no-shows on the call itself) beyond the two timestamps above **[verified absent per `SYSTEM_DESCRIPTION.md` section 5.2]**.

---

## Area: Curriculum and content
**Source:** 1 (value chain — the product itself) and 3 (an asset the business depends on).

- **Skill** — a node in the syllabus hierarchy, leaf nodes carry templates. Real-world events: creation/edit, hierarchy changes, import in bulk (`import_bulk`, YAML/JSON).
- **Template** — a parameterised question template. Real-world events: creation (always starts `status="draft"`), editing/autosave, preview generation, AI-assisted generation (`generate`, `generate_from_image`), validation (`toggle_validated`, the actual serving gate), being flagged faulty, duplication, translation, export/import in bulk, deletion.
- **Knowledge item** — a reusable formula/rule/definition shown alongside solutions. Real-world events: creation, bulk import, AI generation from an image.
- **Template group** — bundles the easy/medium/hard variants of one concept. Real-world events: creation, generating the medium/hard variant from the easy one (`create_medium`, `create_hard`).

No retirement or supersession event was found for any of these four subjects **[unverified — I did not find a "retire a skill" or "archive a template" action beyond `delete_all` on templates, which is a bulk destructive action rather than a considered retirement]**. Given the note's expectation that Exit is one of the most commonly missing stages, this is worth checking directly against Step 2 rather than assumed now.

---

## Area: Student progress and assessment
**Source:** 1 (value chain — the thing the parent is paying for evidence of).

- **Student competency record** (`StudentSkillCompetency`, `StudentTemplateProgress`, `StudentFocusArea`) — the 0-6 level per skill per student, and the tutor's current focus picks. Real-world events: recomputation after every answered question, regression on poor performance, a tutor adding/removing/reordering a focus area, weekly and post-session snapshotting (`WeeklyProgressSnapshot`).
- **Test session** (`TestSession`) — an adaptive testing or learning-mode run. Real-world events: starting, answering, completing, abandoning (explicit `quit_early`, or implicit when a new one starts), a periodic report (`past`).
- **Teacher class assessment** (`ClassAssessment`) — a class-wide assessment event a teacher runs. Real-world events: starting (`start_assessment`), a student joining and answering, marking a student absent, ending (`end_assessment`), viewing the result dashboard (`assessment_dashboard`), a gap report across the class (`gap_report`).

---

## Area: Payments and billing
**Source:** 1 (value chain — being paid, and paying the tutor/distributor).

- **Session payment** (`SessionPayment`) — the Stripe-backed charge to a parent for one delivered session, split into tutor/platform/distributor amounts. Real-world events, in sequence: creation as `pending` when the tutor submits their post-session review (`apply_payment`), parent authorisation of the charge, capture (`paid`), tutor confirmation of receipt (`confirmed`), parent rating (1-5, a rating of 2 or below raises `AdminJob 'low_session_rating'`), failure (`failed`, raising jobs for tutor/parent/admin), 7-day overdue escalation, 14-day overdue escalation (which also pauses the parent's other children's sessions).
- **Legacy payment record** (`Payment`) — a simpler manual bookkeeping record predating `SessionPayment`, still written alongside it. Real-world events: creation only; I found no further lifecycle on this subject.
- **Parent payment profile** (`ParentPaymentProfile`) — the card on file. Real-world events: Stripe SetupIntent creation, card save/attach, no explicit "update card" distinct from the failed-payment retry path **[unverified]**.

Two things worth carrying into Step 2 rather than settling here:

`[QUESTION - design phase: the 7-day/14-day escalation is a Django management command, not a Celery beat task. SYSTEM_DESCRIPTION.md section 4 states it has no scheduled trigger anywhere in this codebase or in docker-compose. If nothing external runs it, the entire overdue-payment and session-pause path never fires. This needs to be confirmed as either "run by an external cron on the host/Railway" (n/a, with that as the reason) or "GAP: no trigger exists."]`

`[QUESTION - design phase: there is no Stripe webhook endpoint at all (verified absent). A dispute, chargeback, or refund raised by the card issuer or by Stripe support would not reach the platform's records under any subject. Is that handled entirely inside the Stripe dashboard today, and if so is that a deliberate n/a or a live gap?]`

---

## Area: Tutor and distributor commercial administration
**Source:** 1 (value chain) and 3 (keeps the money side running).

- **Tutor fee and bank details** — a tutor's hourly rate and payout account. Real-world events: setting the fee (`set_fee` job created at registration), setting up bank details (triggers `AdminJob 'setup_bank_details'` if missing), Stripe Connect account linkage for payout (`stripe_account_id`).
- **Distributor commission** — the distributor's share of a session payment. Real-world events: the per-hour distributor fee being read from `GlobalSetting` at payment time; no distributor-specific payout confirmation step was found distinct from the tutor's **[unverified]**.

---

## Area: Customer communications
**Source:** 3 (a channel the whole business depends on) and 2 (anti-spam and opt-out obligations touch this regardless of platform design).

- **Email notification** — seven distinct triggers exist (tutor welcome, parent welcome, student welcome, tutor-confirmed/new-student-matched, tutor-contact-number, parent-feedback-response, admin bulk/ad-hoc). Real-world events: sending, and for exactly one of the seven (parent feedback response) and the bulk admin path, recording the outcome in `AdminEmailRecord`. The other five fail silently with no audit trail **[verified per SYSTEM_DESCRIPTION.md section 8]**.
- **SMS notification** (`SMSConversation`, `SMSMessage`, `SMSSendJob`) — six trigger types (booking lifecycle, 24-hour reminder, account approval, new-student-to-tutor, tutor-removal, post-session parent message). Real-world events: enqueueing (with debounce/coalescing on identical `message_type`), sending via ClickSend, retry up to 3 attempts, permanent skip after 3 failures with **no admin alert** **[verified]**.

`[QUESTION - design phase: no opt-out or unsubscribe mechanism exists for either channel, verified absent in code. Is that a considered position for a transactional-only service, or a gap against the Spam Act 2003 / Privacy Act requirements? This sits half in this area and half in Privacy and data protection below; I have put the subjects here and left the compliance judgement to that area's Step 2 row.]`

---

## Area: Customer feedback and complaints
**Source:** 4 (what happens when something goes wrong, from the customer's side).

- **Parent feedback** (`ParentFeedback`) — free-text feedback with an optional admin response. Real-world events: submission, admin response (the one email type with a full audit trail via `AdminEmailRecord`).

There is exactly one channel for anything a parent wants to raise, whether it is a minor gripe or something serious. Nothing in the model distinguishes a complaint from a safeguarding concern from a service compliment; there is no severity or category field **[verified]**. I have not created a separate "complaint" subject here because the code does not distinguish one; whether it should be split is exactly the kind of question this method is meant to surface, and I have carried it into the safeguarding area below rather than guessing an answer.

---

## Area: Child safety and safeguarding
**Source:** 2 (an external requirement that applies regardless of what the code does; tutors work one-to-one online with school-aged children).

- **Tutor vetting** — whatever check happens before a tutor is trusted alone with a child over video. Real-world events: none found in the code beyond the generic `approve_tutor` admin action. **[inferred]** Working With Children Check verification (or equivalent) is a standard requirement for this kind of business in every Australian state; there is no field on `TutorProfile` recording one, no expiry tracking, and no re-verification cadence. `[QUESTION - design phase: is a WWCC (or equivalent) collected today as part of the off-platform approval decision, with nothing recorded in the system, or is it not collected at all? This is the single most consequential absence to confirm before Step 2, because it determines whether the Map cell is n/a-with-reason, GAP, or an off-platform process this exercise should still name.]`
- **Safeguarding concern** — a report that a tutor behaved inappropriately with a child. Real-world events: none found; the only capture path in the platform is the undifferentiated `ParentFeedback` channel above. **[inferred]** This is a real event class for this business regardless of whether the platform has ever seen one, per the note's instruction to say where the business does something the platform does not (rule 6, section 7).

---

## Area: Privacy and data protection
**Source:** 2 (Australian Privacy Principles and the Notifiable Data Breaches scheme apply to any business holding personal information, and here most of the data subjects are minors).

- **Personal information holding** — student and parent data held across `StudentProfile`, `User`, session records, and (per `SYSTEM_DESCRIPTION.md` Risk section) `StudentProfile.plain_password` storing a cleartext password. Real-world events: none of creation, retention review, or destruction were found as considered processes; data simply persists. **[inferred]** A privacy policy and collection notice are a legal baseline for a business handling minors' data; not found anywhere in the codebase, though it may exist as a static page **[unverified, I did not check the marketing site's static content for a privacy policy page]**.
- **Data subject request** — a parent or student asking what is held or asking for deletion. Real-world events: none found in the code **[verified absent]**.

---

## Area: Consumer protection, cancellations and payment disputes
**Source:** 2 (Australian Consumer Law guarantees around cancellations, refunds and subscription-like billing).

- **Session cancellation** — covered as an event under Booking and scheduling above; listed again here because the consumer-rights question (was proper notice given, is a fee owed) is a compliance question layered on the same event, not a separate subject.
- **Refund** — money returned to a parent after a charge. Real-world events: none found anywhere in the codebase; no `stripe.Refund` call exists **[verified absent]**. If refunds happen today they happen entirely inside the Stripe dashboard, outside the platform's records.
- **Payment dispute / chargeback** — a card issuer reversing a charge. Real-world events: none found; no webhook exists to even inform the platform a dispute occurred **[verified absent, same finding as the payments area above]**.

---

## Area: Tax and business accounting
**Source:** 2 (GST/BAS and contractor payment obligations apply to the business regardless of the platform) and 3 (keeps the business running).

- **Contractor payment record** — tutors and distributors are paid as contractors via Stripe Connect, not employees. Real-world events: none of ABN validation, contractor agreement, or annual reporting (e.g. Taxable Payments Annual Report, which applies to businesses paying contractors in some industries) were found in the codebase. **[inferred]** Entirely a business-side process today if it happens at all.
- **GST / BAS lodgement** — the platform fee is revenue. Real-world events: none found; the legacy `Payment` model's manual bookkeeping fields (`account_paid`, `date_debit`, `date_credit`) suggest reconciliation happens by hand outside the platform. **[inferred]**

---

## Area: People and business operations (non-platform staff)
**Source:** 3 (keeps the business running; distinct from the `admin` platform role, which is a login, not an employment relationship).

- **Staff member** — whoever holds the `admin` role and does the actual approving, emailing, and job-clearing day to day. Real-world events: none found; there is no employment, rostering, or leave-cover model at all, which is expected for a business this size but still worth naming rather than silently omitting, per rule 6.
- **Key vendor** (Stripe, LiveKit, ClickSend, the hosting provider) — the external services the whole platform depends on. Real-world events: none of vendor onboarding, contract review, or an exit/replacement plan were found as considered processes. **[inferred]**

---

## Area: Platform, infrastructure and technical operations
**Source:** 3 (keeps the platform itself running).

- **Application infrastructure** — hosting (Railway, per `SYSTEM_DESCRIPTION.md`), the Django/Celery/Redis/Postgres stack. Real-world events: deployment, none of backup or disaster-recovery were found as considered processes **[unverified — I did not check for a database backup configuration outside the codebase]**.
- **Uploaded media** — tutor logos, the only `ImageField` in the system. Real-world events: upload; storage is local ephemeral disk with no cloud backend configured, so a redeploy silently loses every uploaded logo **[verified, `SYSTEM_DESCRIPTION.md` section 9.2]**. No event exists for detecting or recovering from this loss.
- **Background job queue** (Celery/Redis) — the mechanism six of the platform's automated processes run on. Real-world events: none of retry configuration, dead-letter handling, or failure alerting were found for any task **[verified — no `autoretry_for`/`max_retries` anywhere, per section 4]**.

---

## Area: Incidents and service disruption
**Source:** 4 (what happens when something goes wrong with the platform itself, as opposed to a customer complaint).

- **Automated job failure** — a Celery task or the payment-escalation command erroring or simply never running. Real-world events: none found. Failures are only visible in worker logs or by directly querying `SMSSendJob` rows with `retry_count >= 3` **[verified, section 4]**; no alert reaches a person.
- **Service outage** — LiveKit, Stripe, or the platform itself being unavailable during a live session or a payment attempt. Real-world events: none found as a considered process; the code has no monitoring, alerting, or declared incident-response step for any of the three integrations named in `SYSTEM_DESCRIPTION.md` section 5.

---

# Summary of what needs an answer before Step 2

These are the flagged questions above, collected in one place per rule 4, so none can be lost between phases:

1. Tutor/distributor application rejection: what actually happens to the account (Account onboarding and approval).
2. Whether `ParentChild.sessions_paused` has any unpause path other than a fresh escalation cycle (Tutor-student matching and roster).
3. Whether hard-deleting bookings on cancellation is a deliberate design choice or a gap (Booking and scheduling).
4. Whether curriculum content (Skill, Template, Knowledge, TemplateGroup) has any retirement process at all (Curriculum and content).
5. Whether `check_payment_escalation` is actually run by an external cron today, since nothing in this codebase schedules it (Payments and billing).
6. Whether the complete absence of a Stripe webhook (no dispute, chargeback, or refund visibility) is known and accepted (Payments and billing; Consumer protection).
7. Whether a WWCC-equivalent check exists off-platform today for tutor approval, and if so why nothing records it (Child safety and safeguarding). This is the single highest-priority one to confirm.
8. Whether ParentFeedback is deliberately the single channel for both routine feedback and safeguarding concerns, or whether that conflation is itself a finding (Customer feedback and complaints / Child safety and safeguarding).
9. Whether a privacy policy or collection notice exists as static site content even though no code enforces or references it (Privacy and data protection).
10. Whether the absence of email/SMS opt-out is a considered position (Customer communications / Privacy and data protection).

Eighteen areas, roughly forty subjects. Let me know which of the above you can answer now versus which should just carry forward as open questions into the Processes and Map sheets, and I'll start Step 2.
