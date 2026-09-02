# Getting data out of Factory

Factory exists so that a study's progress is detected from the work rather than
reported by the lead. A side effect is that it accumulates a record of how network
studies actually move: when each gate was reached, how long review took, who was on
the team, which partners said yes and how long that took. This page says where that
record lives, how to pull it, what each column means, and what is *not* captured yet.

## Where the data lives

| Source | What it holds | Kept current by |
|---|---|---|
| [`.github/data/state/<study>.json`](../.github/data/state/) | **The record.** Per gate: status, `entered_at` (In progress), `ready_at` (Ready for review), `closed_at` (Closed), `reopened_at`, what evidenced it, what was still outstanding. `history`: every advance with its commit. `current_gate`, `gate_entered_at`, `start_date`, `target_date`, the issue number of each gate. | The gate machine on every push; the partner sweep hourly; the stall check daily. Every change is a commit, so `git log` on the file is an audit trail. |
| [`.github/data/baselines/<study>.json`](../.github/data/baselines/) | Provenance: which upstream Strategus template commit the study was scaffolded from and when, and the blob SHA of every template file at provisioning. This is what "unchanged from the template" means. | Written once at provisioning. |
| [`.github/data/gates.json`](../.github/data/gates.json) | The gate definitions: number, title, detection rule, thresholds. Join key for `gate` in every table. | Generated from `.github/issue-templates/` by `build_gates.py`. |
| The study repository | `TEAM.md` (who is on the study), `partners.csv` (who they are recruiting), the eight gate issues (Factory's explanations and any human discussion; who closed it and when), one issue per data partner (body is current state, comments are the log, label events are the status timeline), and the commits themselves (who did what, when, to which files). | The study team, and the study's own `notify-factory.yml`. |
| The Factory tracking issue | A **view** of the above, rebuilt by `factory_issue.py`. Do not scrape it; pull from the sources. The one thing only it holds is the header — study title, lead — for studies provisioned before the state file carried dates. | Every push, hourly, daily. |
| Factory's own git history | Every state change is a commit with a message saying what moved (`Advance study-x to gate 3`, `Update gate state from partners and closures: …`). You can reconstruct any study's state on any date. | Git. |

## Pulling it

**The easy way.** Actions → **Export Portfolio Data** → *Run workflow* → download the
`portfolio-export-N` artifact. Tick *offline* to skip the tables that need GitHub calls.

**Locally**, with `gh` authenticated as someone who can read the study repositories:

```bash
python .github/scripts/export_portfolio.py --out data/export/
```

`data/export/` is ignored by git, so pulls never get committed by accident. Add
`--offline` for the state-file tables only, no network.

**Raw, for what the export does not cover yet.** Replace `ORG/study-x`.

```bash
# Every commit in a study: sha, when, who
gh api "repos/ORG/study-x/commits?per_page=100" --paginate \
  --jq '.[] | [.sha[0:7], .commit.author.date, (.author.login // .commit.author.name)] | @csv'
```

```bash
# Files touched by one commit
gh api repos/ORG/study-x/commits/SHA --jq '.files[].filename'
```

```bash
# Who closed a gate issue, and when (issue 3 here)
gh api repos/ORG/study-x/issues/3/events --jq '.[] | select(.event=="closed") | [.created_at, .actor.login] | @csv'
```

```bash
# Every comment on a gate or partner issue: when, who
gh issue view 3 --repo ORG/study-x --json comments --jq '.comments[] | [.createdAt, .author.login] | @csv'
```

```bash
# A study's state on any past date: list the commits that touched it, then show one
git log --format='%h %ad %s' --date=iso -- .github/data/state/study-x.json
git show SHA:.github/data/state/study-x.json
```

## What the export contains

All timestamps are ISO 8601 in UTC. Durations are whole days. Empty means not
reached or not known.

### `studies.csv` — one row per study

| Column | Meaning |
|---|---|
| `study_repo` | `owner/name` of the study repository. Join key everywhere. |
| `factory_repo`, `factory_issue` | Where the tracking issue is. |
| `lead_name`, `lead_github` | From the tracking issue header, which provisioning wrote. |
| `start_date`, `target_date` | From the state file; for older studies, from the tracking issue. |
| `current_gate`, `current_gate_name` | Highest gate reached. `-1` and blank before Gate 0. |
| `gate_entered_at` | When the current gate was reached. Time in gate is now minus this. |
| `stall_threshold_days` | Days in one gate before the stall check flags the study. |
| `gates_closed` | How many gate issues a human has closed. |
| `exported_at` | When this export ran. |

### `gates.csv` — one row per study × gate

| Column | Meaning |
|---|---|
| `gate`, `gate_name` | 0–7 and the name without its number. |
| `status` | `not_started`, `in_progress`, `ready_for_review`, `done`. |
| `in_progress_at` | When Factory first saw work on the gate. For Gates 0 and 1 this is provisioning, since they start open. Blank if the gate went straight to Ready. |
| `ready_at` | When Factory saw enough to propose review. |
| `closed_at` | When a human closed the gate issue. |
| `reopened_at` | When a human reopened it, if ever. |
| `days_in_progress` | `ready_at − in_progress_at`. |
| `days_in_review` | `closed_at − ready_at`. |
| `issue` | The gate issue's number in the study repo. |
| `evidenced_by` | The paths (or partner statuses) that moved it, `;`-separated. |

### `history.csv` — every advance

| Column | Meaning |
|---|---|
| `at`, `from_gate`, `to_gate` | The transition. |
| `commit` | The study commit that evidenced it. Blank when a human closure or partner status moved the study. |
| `evidence` | The paths seen in that commit, `;`-separated. |

### `team.csv` — from `TEAM.md`

`name`, `institution`, `role`, `github` as the team wrote them. The template's example
row is skipped. `github` is blank for studies whose `TEAM.md` predates the column.

### `partners.csv` — one row per data partner

| Column | Meaning |
|---|---|
| `institution` | From the partner issue title, which came from `partners.csv`. |
| `status` | Current status label, without the `status:` prefix. |
| `contact_name`, `contact_role`, `contact_github` | From the issue body's *Primary contact* line. |
| `issue`, `url` | The partner issue. |
| `last_activity` | Later of the last comment and the last body edit. |
| `days_quiet` | Now minus `last_activity`. The stall check flags partners past the threshold. |

### `partner_status_history.csv` — every status change

One row per `labeled` event with a `status:` label, oldest first, including the label
the issue was created with. `status`, `at`, `institution`, `issue`. Nothing in Factory
stores this; it is read from the issue's own event log, so it is complete for as long
as the issue exists.

### `portfolio.json`

Every table above in one document, plus `exported_at` and `offline`.

## Measures you can compute today

- **Time per gate.** `days_in_progress` and `days_in_review` from `gates.csv`, per gate,
  across studies. Which gate takes longest to write? Which sits longest waiting for a
  human to sign off?
- **Time to first commit.** Gate 0 `ready_at` minus `start_date`. How long before a
  new lead makes their first change.
- **Cycle time so far.** `gate_entered_at` of the current gate minus `start_date`, and
  the same per advance from `history.csv`.
- **Stalls.** Studies where now minus `gate_entered_at` exceeds `stall_threshold_days`,
  and which gate they are stalled in.
- **Partner funnel.** From `partner_status_history.csv`: how many partners reach
  *contacted*, *interested*, *committed*, *package running*, *results received*,
  *declined*; days between each step; how many partners a study needs to approach to
  get three commitments.
- **Partner responsiveness.** `days_quiet` distribution, and how it relates to status.
- **Team shape.** Team size, roles, and number of institutions per study from `team.csv`.
- **What evidences a gate.** `evidenced_by` in `gates.csv`: which files leads actually
  produce first, and whether Gate 3 arrives as cohort JSON or as the CSV.

## What is not captured yet

Ordered by how much it would tell you about the process, against how hard it is to
get. The first two are the ones to do next.

1. **A time series.** The export is a snapshot. Gate dates and partner status changes
   are durable, but days quiet, stall flags, team size, and outstanding protocol
   sections are only ever *now*. Fix: have the daily stall check commit the export to
   `data/snapshots/<date>/` (or append to one long CSV). One job, no new data source.
2. **Who does the work.** Commit authorship and cadence per study — lead versus analyst
   versus collaborator, commits per week, which files each person touches. All of it is
   in the study repos' git history; the export just does not pull it yet. Cheap.
3. **Review behaviour.** Who closed each gate, how many comments the gate issue got,
   from whom, and how long after Ready the first human comment arrived. From the issue
   timeline API. Tells you whether review is a bottleneck and whose.
4. **Rework.** Pushes that touch a gate's paths after that gate is Ready or Closed.
   Factory notices these — it posts the *No gate change* comment — but records nothing.
   Recording them in the state file would show which gates get revisited, and when.
5. **Protocol writing trajectory.** For Gate 2 Factory computes which sections are still
   outstanding on every push. Only the latest is kept. Keeping each observation would
   show which sections leads write first and which take longest.
6. **Study design metadata.** Number of cohorts (`inst/Cohorts.csv`), number of cohort
   definitions and concept sets, which Strategus modules the analysis specification
   uses, number of negative controls. All parseable from the repository; none exported.
   The analytic use case (characterization, estimation, prediction) and clinical area
   are in `Documents/research-question.md` as prose; a structured line there would make
   them a column.
7. **Partner governance.** DUA, IRB, and data-access state are structured lines in the
   partner issue body and could be exported now. Decline reasons are free text in
   comments and would need reading.
8. **Outcomes.** Journal and submission date are in `Documents/results-summary.md` and
   the Gate 7 comment as prose. Acceptance and publication are not tracked at all.
   Two structured fields would do it.
9. **Program context.** Fellowship cohort or year, mentor, and whether the lead had used
   GitHub before. Nothing in the system knows these; they would have to be provisioning
   inputs.
10. **Support events.** Office hours, screen-shares, Slack threads. Outside GitHub, and
    invisible unless someone logs them — a `support` label on an issue comment would be
    the lightest way.

Two things the system deliberately never records, which matter for interpreting any of
this: it does not read file *contents* beyond the detection rules, so it cannot judge
quality, and it never closes anything itself, so every `closed_at` is a human decision
and every gap between `ready_at` and `closed_at` is human time.
