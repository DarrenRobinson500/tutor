# Subject Matter — Messaging Reference

This document summarises every SMS and email notification sent by the platform, including what triggers it, who receives it, and the message content.

---

## SMS Notifications

SMS messages are sent via ClickSend and queued through `SMSSendJob`. A debounce window (default: 10 minutes, configurable via the `sms_pause` variable) prevents duplicates — if the same conversation and message type is already pending, the existing job is updated rather than a new one created.

**Live sending is controlled by the `sms_send` variable (default: off).** When off, messages are logged to the console as "SMS Fake Send" but not dispatched.

### Recipient Rules for Booking SMS

| Message prefix | Sent to |
|---|---|
| `student_*` | Tutor's mobile |
| `parent_*` | Tutor's mobile |
| `tutor_*` | Student's mobile |

### Booking Notifications

Triggered by the `booking_action` API when a booking is created, modified, confirmed, skipped, or cancelled.

| Message Type | Trigger | Recipient |
|---|---|---|
| `student_create_adhoc` | Student books a one-off appointment | Tutor |
| `student_create_weekly` | Student creates a weekly recurring booking | Tutor |
| `student_updated` | Student modifies an existing booking | Tutor |
| `student_confirmed` | Student confirms a booking | Tutor |
| `student_unconfirmed` | Student unconfirms a booking | Tutor |
| `student_skipped` | Student pauses their weekly booking | Tutor |
| `student_unskipped` | Student removes a pause from their weekly booking | Tutor |
| `student_cancelled_weekly` | Student cancels their weekly booking | Tutor |
| `student_cancelled_adhoc` | Student cancels a one-off booking | Tutor |
| `parent_create_adhoc` | Parent books a one-off appointment for their child | Tutor |
| `parent_create_weekly` | Parent creates a weekly recurring booking | Tutor |
| `parent_updated` | Parent modifies a booking | Tutor |
| `parent_confirmed` | Parent confirms a booking | Tutor |
| `parent_unconfirmed` | Parent unconfirms a booking | Tutor |
| `parent_skipped` | Parent pauses the weekly booking | Tutor |
| `parent_unskipped` | Parent removes a booking pause | Tutor |
| `parent_cancelled_weekly` | Parent cancels the weekly booking | Tutor |
| `parent_cancelled_adhoc` | Parent cancels a one-off booking | Tutor |
| `tutor_create_adhoc` | Tutor books a one-off appointment | Student |
| `tutor_create_weekly` | Tutor creates a weekly recurring booking | Student |
| `tutor_updated` | Tutor modifies an existing booking | Student |
| `tutor_confirmed` | Tutor confirms a booking | Student |
| `tutor_unconfirmed` | Tutor unconfirms a booking | Student |
| `tutor_skipped` | Tutor pauses the weekly booking | Student |
| `tutor_unskipped` | Tutor removes a booking pause | Student |
| `tutor_cancelled_weekly` | Tutor cancels the weekly booking | Student |
| `tutor_cancelled_adhoc` | Tutor cancels a one-off booking | Student |

### Other SMS

| Trigger | Recipient | Content |
|---|---|---|
| Admin approves a tutor account | Tutor | Account approval notification with login URL |
| Admin approves a distributor account | Distributor | Account approval notification with login URL |
| Admin assigns a new student to a tutor | Tutor | New student notification, including first session time if set |
| Parent removes a student's tutor | Tutor | End of tutoring arrangement notification |

---

## Email Notifications

Emails are sent via Zoho (smtp.zoho.com.au, port 587). HTML templates are used where available (in the `backend/emails/` directory); plain text is used as a fallback.

### Welcome Emails

| Trigger | Recipient | Subject |
|---|---|---|
| Tutor submits registration | Tutor | Welcome to Subject Matter — application received |
| Parent registers | Parent | Welcome to Subject Matter |
| Parent registers and child has an email address | Each child | Welcome to SubjectMatter |
| Teacher imports a student into a class | Student | Your Subject Matter login for [Class name] |

### Tutor Assignment

| Trigger | Recipient | Subject |
|---|---|---|
| Admin assigns a tutor to a student | Parent | Your tutor has been confirmed — [Tutor name] |
| Admin assigns a tutor to a student | Tutor | New student — [Student name] |
| Parent requests the tutor's mobile number | Parent | [Tutor name]'s contact number |
| Parent requests the tutor's mobile number | Tutor | A parent will be calling you |

### Assessment Reports

| Trigger | Recipient | Subject |
|---|---|---|
| A student completes an assessment session | Parent(s) | [Student name]'s Assessment Report — SubjectMatter (PDF attached) |

### Admin Broadcast

| Trigger | Recipient | Subject |
|---|---|---|
| Admin sends a bulk email from the Emails page | Custom address, all parents, all tutors, or all students | Admin-specified |

---

## Notes

- **Debounce:** Booking SMS messages are debounced per conversation + message type. Rapid changes (e.g. editing a booking time twice) result in only one SMS being sent once the debounce window elapses.
- **Fake send mode:** When `sms_send` is `false` (default), no SMS is dispatched and the message body is printed to the server log instead.
- **Approval SMS:** Sent immediately (no debounce) when an admin approves a tutor or distributor account.
- **Assessment report emails:** Failures are recorded in `AdminEmailRecord` for admin review. An email is sent to every parent linked to the student.
