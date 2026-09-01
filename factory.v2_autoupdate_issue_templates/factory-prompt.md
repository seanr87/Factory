# Task: rework the MHF factory repo for detection-based study tracking

## Context

`factory` is a GitHub repository that generates and tracks study repositories for the OHDSI Maternal Health Data Science Fellowship. Each fellowship study gets its own repo, scaffolded from a Strategus study template, and factory holds one issue per study representing that study's overall progress.

There are roughly ten studies in the 2026 cohort. Study leads are clinicians and researchers, most of whom have never used GitHub. They are not project managers and should never be asked to do project management as a separate chore.

The existing implementation tracks study progress by having the study lead move issues around by hand. That approach was built for a prior cohort of expert leads, was not adopted, and is being replaced.

## What we're changing, and why

Progress should be **detected from the work itself**, not self-reported.

A Strategus study leaves artefacts behind as it progresses: cohort definition JSON, an analysis specification, results. Those artefacts are evidence. When they appear, factory should learn about it without anyone filing a status update.

The reason this matters: a stalled study never announces itself, it just goes quiet. The point of the whole system is to make silence visible.

## Before you write anything

1. Read the existing factory codebase and write me a short summary of what's currently there: the scaffolding logic, the existing status/project code, the data partner CSV-to-issues feature, and anything that pushes partner state up to factory. Say plainly what works, what's dead code, and what you'd remove.
2. Inspect the actual study repo template that factory scaffolds from. **Every file path in the issue templates I'm supplying is a guess and must be verified against the real scaffold.** Where a path is wrong, correct it in the template file and tell me what you changed.
3. Do not proceed to implementation until I've seen that summary.

## Target architecture

**Study repo → factory, one direction.** A workflow in each study repo fires on push, inspects which paths changed, and notifies factory via `repository_dispatch` with the study identifier and the gate that's now evidenced. Factory owns all gate logic in one place, so gates can be changed without editing ten repos.

**Two levels of tracking:**

- **Factory** holds one issue per study, showing the current gate, the date it entered that gate, and a partner roll-up (e.g. "4 partners, 2 stalled"). This is the program-level stall radar.
- **Each study repo** holds the full set of gate issues (Gates 0–7) plus one issue per data partner. This is the lead's own view of their work.

Factory updates the study repo's gate issues too. Leads should see their progress reflected without ever having to move anything.

**Two item types on the project board.** Every item is tagged `milestone` or `work-item`. Build two saved views: one showing only milestones across all studies, and one that's the analyst's or lead's filtered task queue. Gate signal must not be buried under day-to-day task churn.

**Stall detection is time-in-state, not status text.** For each study, the alarm is days since the current gate was entered. For each partner issue, the alarm is days since the last comment. Default threshold: 21 days. Make it configurable.

## Automation rules — these are firm

- **Advance only, never retreat.** Automation can move a gate forward. It must never move one backward.
- **Automation proposes; a human closes.** Detecting a file is not the same as the file being any good. When evidence appears, move the gate to a `Ready for review` state and leave the final close to a human.
- **Always comment, never silently flip.** Every automated change posts a comment on the issue saying what it saw — which paths changed, in which commit. People stop trusting automation the first time it's wrong and unexplained.
- **Gates 5 and 6 are manual.** Partner recruitment and execution happen outside Git and cannot be detected from repository activity. Gate 6 advances from partner issue status, not from pushes.

## The gates

| Gate | Name | Detection |
|---|---|---|
| 0 | Get oriented in GitHub | `TEAM.md` changed |
| 1 | Research question locked | `docs/research-question.md` |
| 2 | Protocol drafted | `docs/protocol.md` |
| 3 | Cohort definitions committed | `inst/cohorts/**`, `inst/settings/CohortsToCreate.csv` |
| 4 | Analysis specification built | analysis spec R script + generated JSON |
| 5 | Data partners recruited | manual; partner issues exist and are active |
| 6 | Study executed across partners | manual; derived from partner issue status |
| 7 | Results synthesised and shared | `results/**`, `docs/results-summary.md` |

Issue body text for all eight gates, plus the partner issue template, is in `issue-templates/`. Scaffolding a new study repo should create all of these. Use them as written — the wording is deliberate and matches the fellowship's existing onboarding materials. Front matter in each file carries the gate number, labels, detection paths, and advance rule.

## Partner tracking

Keep the existing CSV-to-issues feature. A lead commits `partners.csv`, and each row becomes a partner issue in their study repo.

Refine the partner issue so the **body** is the current state (overwritten as things change) and **comments** are the append-only history. Last comment date is what feeds stall detection. Do not ask leads to move partner conversations into GitHub — the issue is a log, not an inbox.

Roll partner counts up to the study's factory issue.

## Deliverables

1. The written audit from step one, before any code.
2. Corrected file paths in the issue templates, with a list of what changed.
3. The study-repo workflow that detects path changes and dispatches to factory.
4. Factory-side handling: gate state machine, issue updates in both repos, explanatory comments, project field updates.
5. Stall detection with a configurable threshold and a way to see all ten studies at a glance.
6. A short README section a study lead could read to understand what the automation does to their repo and why things move on their board without them touching anything.

## Constraints

- Do not guess at paths, API shapes, or the existing code's behaviour. Inspect, then act.
- Prefer changing factory over changing ten study repos.
- Nothing in this system should require a study lead to use the command line.
