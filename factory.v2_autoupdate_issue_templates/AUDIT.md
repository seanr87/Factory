# Factory v2 — pre-implementation audit

Date: 2026-08-31. No code changed. Deliverable 1 of `factory-prompt.md`.

Sources inspected: `seanr87/Factory` (this repo, `main`), `seanr87/study-template` (`main`),
`ohdsi-studies/StrategusStudyRepoTemplate` (`main`).

---

## 1. What factory does today

### 1.1 Provisioning — works, and is the part worth keeping

`.github/workflows/provision-study.yml` is a `workflow_dispatch` pipeline composed from twelve
local composite actions. In order:

| # | Step | Action | Verdict |
|---|---|---|---|
| 1 | Mint GitHub App token | `actions/create-github-app-token@v1` | works, but see 1.5 |
| 2 | Resolve study lead | `manage-study-leads` | works |
| 3 | Append new lead to `.github/data/study-leads.json`, commit | inline + `manage-study-leads` | works |
| 4 | Rewrite this workflow's own dropdown, commit, rebase, push | `update-workflow-dropdown` | works; self-mutating |
| 5 | Validate title/date/username, derive repo slug | `validate-study-inputs` | works |
| 6 | `gh repo create --template <owner>/study-template --public` | `create-study-repository` | works |
| 7 | Create per-study ProjectV2, make public, link to repo, add `Data Partner Status` field | `setup-study-project` | works |
| 8 | Invite lead as collaborator (read) | `invite-collaborator` | works; redundant — step 6 already grants admin |
| 9 | Create factory tracking issue, label `study-tracking` | `create-factory-tracking` | works |
| 10 | Add tracking issue to Factory Portfolio project | `add-to-factory-project` | works |
| 11 | Create 3 status issues in study repo from JSON config | `create-status-issues` | works; being replaced |
| 12 | Regex-patch the factory issue body to hyperlink the objective table | inline `github-script` | brittle string match |
| 13 | `{{PLACEHOLDER}}` substitution in study README | `populate-study-template-files`, `create-study-readme` | works |
| 14 | `gh secret set ORG_ADMIN_TOKEN` + `gh variable set FACTORY_PROJECT_URL` on the new repo | inline | **works — v2 depends on this** |

Step 14 matters more than it looks. Every provisioned study repo already receives a token that
can write to factory. The `repository_dispatch` channel v2 needs is **already plumbed** — we do
not need new credential distribution, only a new dispatch event type.

### 1.2 Status tracking — the mechanism being replaced

Three coarse milestones, not eight gates. `.github/data/study-status-issues.json` defines
`Analysis Package Prototype` → `Network Execution` → `Journal Submission`, each becoming one
`status-tracking` issue in the study repo.

The loop: lead closes a status issue → study repo's `.github/workflows/factory-objective-update.yml`
(`on: issues: [closed, reopened]`) → fetches factory's `study-status-issues.json` over the API →
recomputes "current objective" → writes it to the factory issue's project field.

Two defects in that loop, both answered by v2's rules rather than by patching:

- **It can retreat.** The trigger includes `reopened`, and the objective is recomputed from
  scratch each time. Reopening an issue moves the study backward. v2's *advance only, never
  retreat* rule is the direct fix.
- **The scan order is wrong.** The loop sets `currentObjective` from each closed issue but only
  `break`s on the first *open* one, so a closed → open → closed sequence resolves inconsistently.

### 1.3 Activity monitoring — works, wrong signal

`.github/workflows/activity-check.yml`, daily 09:00 UTC. For each `study-tracking` issue it
regexes the repo URL out of the body, calls `GET /repos/{repo}` and reads `pushed_at`, then
rewrites the issue **title** with a green/yellow/red circle at hardcoded 14 / 30 day thresholds.

- The signal is repo-level `pushed_at` — a README typo counts as progress. This is exactly the
  gap v2 closes: activity is not progress, and time-since-push is not time-in-gate.
- `sed "s|Status:.*|...|"` on the issue body rewrites *any* line containing `Status:`.
- Mixes `secrets.GITHUB_TOKEN` (gather step) and `secrets.ORG_ADMIN_TOKEN` (write step).
- Thresholds are not configurable; v2 requires a configurable 21-day default.

### 1.4 `factory-issue-updater.yml` — dead code

`on: repository_dispatch: [update_factory_issue]` plus a daily 06:00 cron. It selects factory
issues by `labels: 'study'` and parses the study repo with `/\*\*Repository\*\*:.*?github\.com\/.../`.

But `create-factory-tracking` applies the label **`study-tracking`**, and writes the body line as
**`**Repository:** <url>`** — colon *inside* the bold markers. Neither the label filter nor the
regex matches anything factory actually creates. This workflow has been matching zero issues on
every scheduled run. It also duplicates what `activity-check.yml` does.

**Recommendation: delete.** v2 needs a `repository_dispatch` receiver, but a new one built to the
gate state machine, not a repair of this.

### 1.5 Credentials — two systems, inconsistently applied

`provision-study.yml` mints a GitHub App token in step 1 and then uses `secrets.ORG_ADMIN_TOKEN`
(a PAT) for nine of the eleven steps needing write access. The App token is used only for checkout
and the dropdown commit. The PAT is what gets copied into every study repo.

Not a v2 blocker, but worth settling: a PAT bound to one person's account is a single point of
failure across ten study repos, and it is the thing that expires silently.

### 1.6 Data partner tracking — lives in the study template, not in factory

Contrary to the brief's framing, the CSV-to-issues feature is **not** factory code. It is in
`seanr87/study-template`:

- `._ADD_DATA_PARTNERS_/data_partners.csv`, header `Site Name,Contact Name,Contact GitHub Username`
- `.github/workflows/manage-data-partners.yml` — `on: push: paths: ['._ADD_DATA_PARTNERS_/data_partners.csv']`
- `.github/actions/manage-data-partners/action.yml` — one issue per row, title = site name,
  labels `data-partner` + `status:preparation`
- `.github/workflows/scheduled-project-status-sync.yml` — **every 15 minutes**, syncs the
  `Data Partner Status` project field into issue labels and a body history block

What works: the commit-a-CSV-and-get-issues flow is sound and worth keeping, as the brief says.

What is weak:

- **Parsing.** `line.split(',')` with `columns.length >= 3`. A site name containing a comma
  breaks it; a row with an empty GitHub column is silently dropped. The committed sample file
  already contains four malformed rows.
- **Create-only.** Existing issues are found and then explicitly skipped — "no updates needed".
  v2 wants the body to be current state, so this must become an upsert.
- **Wrong project.** It takes `projectsV2(first: 5).nodes[0]` — the first project linked to the
  repo, not necessarily the study project.
- **Cost.** The 15-minute sync is 96 runs/day/repo — roughly 29,000 runs/year across ten studies,
  polling something that could be event-driven.
- **No roll-up.** Nothing sends partner counts to factory. The brief's partner roll-up is entirely
  new work.

### 1.7 Remove list

| Item | Why |
|---|---|
| `.github/workflows/factory-issue-updater.yml` | dead — label and regex never match (1.4) |
| `.github/workflows/activity-check.yml` | superseded by time-in-gate stall detection (1.3) |
| `.github/data/study-status-issues.json` | superseded by the eight gate templates |
| `.github/actions/create-status-issues` | replaced by a gate-issue creator |
| study-template `factory-objective-update.yml` | replaced by the path-detection dispatcher |
| study-template `scheduled-project-status-sync.yml` | replace polling with issue-event triggers |
| `.github/actions/invite-collaborator` | redundant with the admin grant in `create-study-repository` |
| `.github/workflows/bi-weekly-reminders.yml`, `test-reminder-system.yml` | re-point at stall detection or drop; currently nudges on the old model |
| `archive/` (both repos) | already dead, and it makes the live surface hard to read |

---

## 2. The scaffold is not the repo you linked

**This is the finding that changes the plan.** `create-study-repository` scaffolds from
`<owner>/study-template` — i.e. `seanr87/study-template`. That repo is an **older fork** of
`ohdsi-studies/StrategusStudyRepoTemplate`, and the two have diverged structurally:

| Asset | Upstream (current) | `seanr87/study-template` |
|---|---|---|
| Analysis spec script | `scriptsForStudyDesigner/CreateStrategusAnalysisSpecifications.R` | `CreateStrategusAnalysisSpecification.R` (root, singular) |
| Analysis spec JSON | `inst/analysisSpecifications.json` | `inst/sampleStudy/sampleStudyAnalysisSpecification.json` |
| Cohort JSON | `inst/cohorts/*.json` | `inst/sampleStudy/cohorts/*.json` |
| Cohort manifest | `inst/Cohorts.csv` | — |
| Cohort SQL | `inst/sql/sql_server/*.sql` | `inst/sampleStudy/sql/sql_server/*.sql` |
| Protocol | `Documents/Protocol.Rmd` (+ `.bib`, `.csl`, style assets) | — no `Documents/` |
| Site execution | `ExecuteAnalyses.R` | `StrategusCodeToRun.R` |
| Coordinator scripts | `scriptsForStudyCoordinator/` (7 files) | root-level `UploadResults.R`, `app.R`, … |
| Role guides | `template_docs/` (6 docs incl. designer / site / coordinator guides) | `template_docs/` (4 docs) |
| Partner tracking | — | `._ADD_DATA_PARTNERS_/`, `._.START_HERE_/`, `.github/` automation |

Per your instruction we standardise on the **current upstream structure**. That makes "re-base
`study-template` on current upstream, re-applying the factory automation on top" a prerequisite
work item, not an optional cleanup — otherwise every detection path we write points at files that
will not exist in provisioned repos.

---

## 3. Corrected detection paths

### 3.1 Two blockers found in `.gitignore`

Both templates ignore these, upstream for pkgdown and Strategus reasons:

```
docs/          # pkgdown output
results/       # Strategus results folder
```

Consequences, and they are not small:

- **Gates 1, 2 and 7 as written can never fire.** Every `docs/...` path in the supplied templates
  is unpushable. A lead following the instructions would commit `docs/research-question.md`, see
  nothing happen, and reasonably conclude the system is broken.
- **Gate 7's `results/**` can never fire.** Aggregate results are also exactly the kind of thing
  that should not be pushed to a public repo by reflex.

Fix: move all prose artefacts to `Documents/`, which the template already uses for protocol
materials and which is not ignored. Detect Gate 7 on a written summary, not on results data.

### 3.2 The template-baseline problem

Five of the six auto-detected gates point at files the scaffold **already ships** — `Protocol.Rmd`,
three sample cohort JSONs (11/21/31), `Cohorts.csv` carrying celecoxib / diclofenac / GI-Bleed, and
`analysisSpecifications.json`. So detection must be *content changed from the scaffold baseline*,
never *file exists*. Concretely: record the template's blob SHA per detected path at provisioning
time, and treat a gate as evidenced only when the current SHA differs.

Related trap: factory's own step 13 commits to the study `README.md` during provisioning. Any gate
keyed on `README.md` would self-trigger before the lead touches anything.

### 3.3 Path corrections, gate by gate

| Gate | Supplied (guess) | Corrected | Note |
|---|---|---|---|
| 0 | `TEAM.md` | `TEAM.md` — **must be added to the scaffold** | does not exist upstream; add a stub. Do *not* substitute `README.md` (3.2) |
| 1 | `docs/research-question.md` | `Documents/research-question.md` | `docs/` is gitignored; add a stub to the scaffold |
| 2 | `docs/protocol.md` | `Documents/Protocol.Rmd` | exists upstream, pre-populated → baseline diff required |
| 3 | `inst/cohorts/**/*.json` | `inst/cohorts/**/*.json` | correct as supplied |
| 3 | `inst/settings/CohortsToCreate.csv` | `inst/Cohorts.csv` | supplied path does not exist; also add `inst/sql/sql_server/**` |
| 4 | `inst/analysisSpecification.json` | `inst/analysisSpecifications.json` | **plural** — confirmed in `config.yml` (`studySpecificationFileName`) |
| 4 | `CreateAnalysisSpecification.R` | `scriptsForStudyDesigner/CreateStrategusAnalysisSpecifications.R` | moved into a subfolder upstream |
| 4 | — | also `inst/negativeControlOutcomes.csv`, `inst/covariateConceptsToExclude.csv` | gate prose already asks for negative controls |
| 5 | `partners.csv` | `partners.csv` (renamed from `._ADD_DATA_PARTNERS_/data_partners.csv`) | decision D3 |
| 6 | none | none | correct — manual, derived from partner issues |
| 7 | `results/**` | *drop* | gitignored, and results should not be pushed |
| 7 | `docs/results-summary.md` | `Documents/results-summary.md` | `docs/` gitignored |

Three gates therefore need **stub files added to the scaffold** so leads have something to edit in
the browser: `TEAM.md`, `Documents/research-question.md`, `Documents/results-summary.md`. That is
consistent with the templates' own "click the pencil icon" instructions — a lead cannot
pencil-edit a file that does not exist.

Also worth noting: `Documents/Protocol.Rmd` is R Markdown, not the Markdown the Gate 2 prose
implies. The gate text says "16-section OHDSI protocol skeleton"; the upstream `Protocol.Rmd` is
already that skeleton, so the wording holds — but the file extension in the prose should match.

---

## 4. Design gaps in the supplied templates

1. **Gate 6 has no machine-readable partner status.** The brief derives Gate 6 from partner issue
   status, but `partner-tracking.md` keeps status as prose (`**Status.** Not yet contacted`).
   Parsing issue bodies is brittle. The existing system already solved this with `status:*` labels
   plus a `Data Partner Status` project field — keep the label as source of truth and mirror it
   into the body line.
2. **Partner stall detection can misfire.** Stall = days since last comment, but the template tells
   leads to keep the *body* current. A lead who diligently rewrites the body and comments nothing
   reads as stalled. Use `max(last comment, last body edit)`, or have automation post body changes
   as a comment.
3. **No factory-side issue body exists.** All nine supplied files are study-repo issues. The
   program-level factory issue — current gate, date entered, partner roll-up — has no template.
   It needs writing.
4. **`partners.csv` schema is unstated.** The templates need `{{INSTITUTION}}`, `{{CONTACT_NAME}}`,
   `{{CONTACT_ROLE}}`; the existing CSV supplies `Site Name, Contact Name, Contact GitHub Username`.
   Neither is a superset. Proposed: `institution,contact_name,contact_role,contact_github`.
5. **Gate 5 front matter contradicts itself** — it carries `detection.paths` *and*
   `advance_rule: manual_only`, plus an `also:` key no other file uses. Harmless, but the state
   machine needs to know paths are advisory there.
6. **Keep path → gate matching in factory.** If the study workflow filters paths, changing a gate
   means editing ten repos — against the brief's own constraint. The study workflow should dispatch
   the raw changed-file list; factory does all matching.

---

## 5. Decisions needed from you

| # | Decision | Recommendation |
|---|---|---|
| D1 | Re-base `study-template` on current upstream `StrategusStudyRepoTemplate`? | **Yes** — you've said assume that structure; this is what makes it true |
| D2 | `Documents/` for prose artefacts, vs. un-ignoring `docs/` | **`Documents/`** — matches the template's own convention, no `.gitignore` surgery |
| D3 | Rename `._ADD_DATA_PARTNERS_/data_partners.csv` → `partners.csv` | **Yes** — the brief's wording, and the current name is hostile to a first-time user |
| D4 | Add stub `TEAM.md`, `Documents/research-question.md`, `Documents/results-summary.md` to scaffold | **Yes** — required for browser-only editing |
| D5 | Keep the PAT (`ORG_ADMIN_TOKEN`) or move fully to the GitHub App | Defer; not a v2 blocker, but logged |
| D6 | Can a study evidence Gate 4 before Gate 2 is closed? | Allow it, record it, do not backfill skipped gates |
