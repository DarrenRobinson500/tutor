# Note: building the Processes and Map sheets for the tutoring platform

You are being asked to produce two sheets that describe the tutoring business as a set of capabilities: what the platform must provide for each real-world event, and whether every thing the platform holds has a complete life. The structure has been used on another build and works. This note gives you the framework, the method and the traps. It does not give you the answers, because they are specific to this business and you have the codebase.

There is no existing set of sheets for this domain. You are creating them.

## 1. What the two sheets are

**Processes.** One row per real-world event, grouped by the thing the event acts on. The columns ask what the platform must provide for that event to be handled.

**Map.** One row per thing, one column per stage of its life. The cells ask whether each stage has a process.

They exist as a pair because each finds what the other cannot. Processes will let you describe eight events beautifully and never notice that nothing in the system handles a tutor leaving. Map, laid out as a grid, makes that column visibly empty.

The purpose of both is to make absences findable. A row that reports everything is fine has told the reader nothing.

## 2. Vocabulary

**Area.** A domain of capability. A grouping convenience, not a claim about team structure.

**Subject.** A thing in the world the platform holds, which has a life: a student, a tutor, a booking, a session, a subscription, a payout, a course, a safeguarding check. The test of a subject is that it can be created, can end, and can fail. If it cannot fail, it is probably an attribute of something else rather than a subject in its own right.

**Process.** One real-world event acting on a subject: onboarding a tutor, cancelling a session late, refunding a term, removing a tutor after a concern is raised. Not a procedure document and not a code path. The event, described by what the system owes it.

**Tool.** One of the seven things a process may need. These are the Processes columns.

| Tool | What it is |
|---|---|
| Register | A store. Where state is written and kept. |
| Trigger | What fires the process: a clock, or the arrival of an input. |
| Entry form | Where a person puts in something the system cannot derive. |
| Workflow | An ordered set of tasks, each performed by the system, by AI, or by a named human role. |
| Dashboard | A projection over stores. Never a store itself. |
| Document | Versioned content that comes out. |
| Report / external output | Something that goes to a party outside the business. |

## 3. The Processes sheet

Columns, in order:

`Process | Summary | Register (stores written) | Trigger | Entry form | Workflow | Dashboard | Document | Report / external output | Notes`

Conventions:

- **A filled cell means required, not built.** The sheet states the requirement. What exists is a separate question, and you should answer it in a status field rather than by leaving cells empty.
- **Counts, not ticks.** Say how many of that tool the process needs. Where the count hides variation, say what varies: "1, with 3 approval paths: automatic under £50, support lead above it, and finance where the term has already been invoiced." On the other build, "one" was usually the wrong answer and the axis of variation was the whole content of the cell.
- **A register cell names the stores written**, not a category. If the process writes three, name three.
- **A trigger cell says which kind.** A clock ("Cron, nightly") or an arrival ("Input: a parent submits a cancellation"). A trigger is configuration the platform holds, which is why it is a tool and not prose.
- **`n/a` always carries its reason.** Never a blank and never a bare `n/a`. "n/a: payouts arrive from the payment provider rather than being entered."
- **Notes carry the judgement**, the risk, or the thing a reader would otherwise get wrong. Do not restate the other cells there.

Group rows by subject, and give each area a short note saying what the area is and what is peculiar about it.

## 4. The Map sheet

Columns:

`Area | Subject | Owner | Create / Change | Exit | Run | Periodic Test / Review / Refresh | Failure | Fix | Report`

Every cell is one of five things:

| Marker | Meaning |
|---|---|
| A named process | Covered, by that row on Processes. |
| `-> Area or process` | Covered, by a process another area or row owns. |
| `Trigger:` | Covered, as a trigger on another row rather than as a process of its own. |
| `n/a:` | Deliberately not needed, with the reason. |
| `GAP:` | Needed, and nothing covers it. |

Each subject has an **Owner**, accountable for every stage in that row having an owner. Where the natural owner does not exist in the business yet, record the escalation rather than defaulting to whoever is available, so that accountability moves when the role is filled instead of staying put.

## 5. Method

Work in two steps per area, and do not merge them. On the other build this was the single most useful discipline.

**Step 1, define the rows.** List the subjects for the area and the real-world events that act on them, in prose, and stop. Getting the row set right is most of the work and it is much cheaper to argue about a list than about a filled grid.

**Step 2, write the rows.** Fill the cells.

Deriving the areas is the step that goes wrong. Do not derive them from the codebase's module structure, and do not derive them from whatever documents exist. On the other build the areas were derived from a governance document set, and the result was blind to whole business functions nobody had written a policy about. It took someone noticing that month-end accounting was missing to find them.

Your equivalent trap is sharper: the code will tell you about everything that happens inside the app, and nothing about what the business does outside it. Safeguarding checks chased by email, refunds issued in the payment provider's dashboard, tutor payouts run by hand at month end, a complaint handled in a shared inbox. Every one of those is a real process with no code behind it, and each is exactly where an absence hides.

So derive areas from four sources, and say which source each came from:

1. **What the business does to earn.** Follow the value chain end to end: acquiring a student, matching, booking, delivering a session, being paid, retaining or losing the customer, paying the tutor.
2. **What an external party requires.** Child safety and working-with-children checks, data protection where the data subjects are minors, consumer law on subscriptions, cancellations and refunds, payment scheme rules, anything a school or institutional customer imposes by contract.
3. **What keeps the business running.** People, money, the platform, the data, the content.
4. **What happens when something goes wrong.** Complaints, incidents, safeguarding concerns, disputes and chargebacks, outages.

## 6. What to expect, from the other build

These patterns held there and are worth carrying as expectations rather than conclusions.

**Create is designed, and the other stages are not.** Gaps clustered in Exit, Periodic review and Failure, in that order. Expect the same, and expect it to matter more here: a tutor leaving, a student leaving and a concern being raised are not edge cases in this business.

**Exit is usually one shape instantiated many times.** Every retirement asks the same question. What was depending on this, and is that dependency discharged before it goes? Eleven separate gaps turned out to be one workflow plus a dependency graph. Look for that before writing eleven rows.

**Periodic review is either an assessment or a reconciliation, and they are different.** An assessment is a judgement re-made on a cycle, with a human confirming against evidence. A reconciliation is a machine-computable comparison of two records where only exceptions reach a person. Writing a reconciliation as an assessment puts a person in a loop that does not need one.

**Failure gaps are usually policy gaps wearing a process costume.** You can write the row in ten minutes and it will say "assess, decide, act" with the decision criteria blank, because nobody has set them. Say so rather than filling it in. On this build the likely instances are: a safeguarding concern that turns out to be founded, a tutor found to be unqualified after sessions were delivered, a chargeback, and a term billed wrongly.

**A dashboard is a projection, never a store.** Every dashboard must name what it reads. If it cannot, the missing dashboard is the symptom and the missing store is the problem. This test found two missing stores on the other build.

**Do not create a store that has to be reconciled with an existing one.** If a new store would hold a second copy of something a store already holds, it is probably fields on the existing store plus a projection. This collapsed six proposed stores into one on the other build.

## 7. Rules

1. The absence is the output. Say what is not there.
2. `GAP` and `n/a` are different claims and neither is a blank. `n/a` asserts a decision and carries its reasoning. `GAP` asserts a hole. A cell nobody has examined is neither, and must be labelled unexamined rather than dressed up as a decision.
3. Do not conflate covered-elsewhere with covered-nowhere. If another area owns it, point at that area.
4. Flag, do not settle. Open questions get marked and carried into the design step, not resolved in passing. Use a bracketed marker so they can be extracted mechanically, for example `[QUESTION - design phase: ...]`.
5. No fabrication. Anything inferred is marked as inferred, with what it was inferred from. Anything you cannot verify in the code is marked unverified rather than stated.
6. Say where the business does something the platform does not. That is a finding, not an omission from your remit.

## 8. Output

A workbook with four sheets:

- **Processes**, columns as in section 3, grouped by area and subject.
- **Map**, columns as in section 4.
- **Questions**, generated from the bracketed markers rather than typed separately, so a flag cannot be lost between phases.
- **Summary**, with the area list, where each area came from of the four sources in section 5, and the count of gaps by stage.

Keep the column names and the five markers exactly as given, so that the two builds can be read the same way and the same tooling works on both.

A style note: no em dashes, plain sentences, and no restating a cell's content in its Notes.
