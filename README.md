# OHDSI Study Factory 🏭

Creates and tracks the study repositories for the OHDSI Maternal Health Data Science
Fellowship. Factory holds one issue per study; each study repository holds its own
gate issues and data partner issues.

**Progress is detected from the work itself, not self-reported.**

## Why

A Strategus study leaves artefacts behind as it progresses — a research question, a
protocol, cohort definitions, an analysis specification, results. Those artefacts are
evidence. When they appear, Factory learns about it without anyone filing a status
update.

The reason this matters: a stalled study never announces itself, it just goes quiet.
The point of the whole system is to make silence visible. An earlier version asked
study leads to move issues by hand to report progress; it was built for a cohort of
expert leads, was not adopted, and has been replaced.

Study leads are clinicians and researchers, most of whom have never used GitHub. They
are never asked to do project management as a separate chore, and nothing in this
system requires a command line.

## How it works

```
study repo                          Factory
──────────                          ───────
push
  └─ notify-factory.yml
       reports changed paths ──────▶ gate-state-machine.yml
       (raw list, nothing else)        ├─ match paths against gate config
                                       ├─ compare against template baseline
                                       ├─ decide (advance only, never retreat)
                                       ├─ comment on the gate issue
                                       ├─ update the Factory issue
                                       └─ commit state

                                     stall-check.yml  (daily)
                                       ├─ derive Gate 6 from partner status
                                       ├─ days in gate, days since partner activity
                                       └─ rewrite the portfolio dashboard
```

The study-side workflow is deliberately dumb: it reports which paths changed and
nothing more. All gate logic lives in Factory, so gates can be redefined without
editing ten study repositories.

## The gates

| Gate | Name | Evidence |
|---|---|---|
| 0 | Get oriented in GitHub | `TEAM.md` |
| 1 | Research question locked | `Documents/research-question.md` |
| 2 | Protocol drafted | `Documents/Protocol.Rmd` |
| 3 | Cohort definitions committed | `inst/cohorts/`, `inst/Cohorts.csv`, `inst/sql/sql_server/` |
| 4 | Analysis specification built | `inst/analysisSpecifications.json`, the spec script |
| 5 | Data partners recruited | manual — partner issues are the record |
| 6 | Study executed across partners | derived from partner issue status |
| 7 | Results synthesised and shared | `Documents/results-summary.md` |

Gate prose lives in [`.github/issue-templates/`](.github/issue-templates/) and is what
study leads read. Its front matter carries the machine-readable config, which
[`build_gates.py`](.github/scripts/build_gates.py) compiles into
[`gates.json`](.github/data/gates.json) — so the prose and the behaviour cannot drift.

## Rules the automation follows

- **Advance only, never retreat.** A gate is never moved backward.
- **Automation proposes; a human closes.** Evidence moves a gate to *Ready for
  review*. Detecting a file is not the same as the file being any good.
- **Always comment, never silently flip.** Every change says what it saw and in which
  commit. People stop trusting automation the first time it is wrong and unexplained.
- **Baseline before evidence.** A path counts only when its blob differs from what the
  Strategus template shipped. Without this, five of six gates would fire at
  provisioning.

These live in [`gate_machine.py`](.github/scripts/gate_machine.py) as a pure function
with a self-test that runs in CI before every decision, rather than in workflow YAML
where they would be easy to route around.

## Scaffolding

Study repositories are created from
[`ohdsi-studies/StrategusStudyRepoTemplate`](https://github.com/ohdsi-studies/StrategusStudyRepoTemplate)
at provision time, always from upstream `main`. Factory's own files — the dispatcher,
`partners.csv`, and the stub files the gate issues ask leads to edit — are applied
afterwards as an overlay in a single commit. There is no fork to keep in sync.

Upstream can restructure without warning, and has twice in nine months. Two things are
therefore recorded per study and are not optional:

- the upstream commit SHA it was scaffolded from, in `.github/data/baselines/`
- a blob SHA per detected path, so detection can tell a lead's edit from template content

[Path Contract Check](.github/workflows/path-contract-check.yml) runs daily against
upstream and opens an issue when a detection path stops matching, so a restructure
announces itself instead of silently stalling every study provisioned afterwards.

## Stall detection

Two clocks, deliberately different:

- **Studies** — days since the current gate was entered. Not days since the last push:
  the previous version measured repository `pushed_at`, so a README typo read as
  progress. Time-in-state cannot be reset by activity that is not progress.
- **Partners** — days since the later of the last comment and the last body edit.

Default threshold 21 days, configurable in `gates.json`, per study in its state file,
or per run via `workflow_dispatch`. Results go to a `portfolio-status` dashboard issue,
rewritten daily and sorted most-stalled-first, plus a roll-up on each study's Factory
issue.

## Layout

```
.github/
  workflows/
    provision-study.yml       create a study: repo, board, gate issues, overlay
    gate-state-machine.yml    receive study_push, advance gates, sync partners
    stall-check.yml           daily: derive Gate 6, find what has gone quiet
    path-contract-check.yml   daily: verify detection paths still exist upstream
  actions/                    composite actions used by provisioning
  scripts/
    gatelib.py                path matching, shared by everything that matches
    gate_machine.py           the decision rules, with a self-test
    run_gate_machine.py       I/O around a decision
    create_gate_issues.py     Gates 0-7 in a study repo, seeds its state
    sync_partners.py          partners.csv -> partner issues
    stall_check.py            time-in-gate and partner quiet, dashboard
    derive_partner_gates.py   Gate 6 from partner status
    build_gates.py            issue templates -> gates.json
  issue-templates/            gate prose; the source of truth for gate config
  overlay/                    Factory files pushed into each study repo
  data/
    gates.json                generated; do not edit by hand
    baselines/<study>.json    template blob SHAs per study
    state/<study>.json        current gate, entry time, issue map, history
```

## Seeing it work

[DEMO.md](DEMO.md) is a fifteen-minute browser walkthrough that exercises every moving
part: a gate advancing on a commit, the refusal to move backwards, the baseline check that
stops the template's own files counting as work, partners appearing from a spreadsheet,
Gate 6 derived from partner labels, stall detection, and the contract check catching a
simulated upstream restructure.

## Setup

**Deploying this in your own organisation: [DEPLOYING.md](DEPLOYING.md).** It covers the
token and its scopes, building the study board template, the variables below, and the
handful of failure modes that are confusing the first time you hit them.

Everything tied to a particular installation is a repository variable or secret, so a
copy of this repository runs elsewhere without editing code. The gates themselves stay
OHDSI-specific — this tracks Strategus network studies, not projects in general.

Secret: `ORG_ADMIN_TOKEN` (scopes `repo`, `workflow`, `project`, `admin:org`, and
SSO-authorised if your org enforces SAML). It is the only one.

| Variable | Required | Default |
|---|---|---|
| `STUDY_BOARD_TEMPLATE_ID` | yes | — |
| `FACTORY_PROJECT_NUMBER` | yes | — |
| `FACTORY_PROJECT_URL` | yes | — |
| `STRATEGUS_TEMPLATE_REPO` | no | `ohdsi-studies/StrategusStudyRepoTemplate` |
| `STUDY_REPO_PREFIX` | no | `study-` |

Study repositories are created under whoever owns Factory, so put Factory in the
organisation you want the studies in.

`STUDY_BOARD_TEMPLATE_ID` is the node ID of the
[`[TEMPLATE] Study Board`](https://github.com/orgs/OHDSI-JHU/projects/30) project.
Each study's board is a copy of it, which carries the three views — Milestones, Work
items, Data partners — with their filters intact. Retune a view on the template and
every study provisioned afterwards picks it up with no code release. The template must
be owned by an organisation; `markProjectV2AsTemplate` refuses user-owned projects.

## For study leads

[HOW-THIS-REPO-IS-TRACKED.md](.github/overlay/HOW-THIS-REPO-IS-TRACKED.md) is delivered
into every study repository and explains what the automation does and why things move
without them touching anything.
