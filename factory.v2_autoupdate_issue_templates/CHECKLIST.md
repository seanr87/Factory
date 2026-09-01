# Factory v2 — work checklist

Living document. Tick items as they land. See [AUDIT.md](AUDIT.md) for the reasoning behind
anything marked with a section reference.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked on a decision

---

## Phase 0 — Decisions (blocking)

- [x] **D0** Audit written and reviewed — *AUDIT.md*
- [x] **D1 — DECIDED: Option A.** Scaffold with `gh repo create --template ohdsi-studies/StrategusStudyRepoTemplate`
      at provision time, always from upstream `main`, then push the factory overlay on top.
  - Upstream is `is_template: true`, so the template API works directly. No fork, no ref pinning.
  - Accepted trade-off: upstream breakage arrives untested, and studies provisioned weeks apart
    can carry different layouts. Two breaking layout changes in the last nine months
    (`v2.0.0` 2026-05-21 restructure; Dec 2025 moved cohorts out of `inst/sampleStudy/`).
  - Mitigations, now mandatory rather than optional:
    - record the upstream commit SHA on each study's factory issue, so factory knows that study's layout
    - run the path-contract check against upstream `main` **daily**, not weekly
  - Retires `seanr87/study-template`: factory automation becomes an **overlay** pushed after
    scaffolding, not files maintained inside a fork.
- [x] **D2 — settled by consequence.** `Documents/` for prose artefacts. Upstream gitignores `docs/`
      and we no longer control the template, so un-ignoring it is not available under Option A.
- [x] **D3 — settled by consequence.** Partner CSV is `partners.csv` at repo root. It ships in the
      factory overlay, and D7 means there are no legacy consumers of the old path.
- [x] **D4 — settled by consequence.** Stub `TEAM.md`, `Documents/research-question.md`,
      `Documents/results-summary.md` ship in the overlay. Required: a lead cannot pencil-edit a
      file that does not exist, and upstream provides none of the three.
- [!] **D5 — NOW BLOCKING.** `ORG_ADMIN_TOKEN` returns `Bad credentials (HTTP 401)`.
      The PAT is expired or revoked, so **provisioning cannot run at all** — this is not caused by
      the v2 changes and would fail identically on `main`. The last successful provision was
      September 2025.
  - Immediate fix: regenerate a classic PAT and update the `ORG_ADMIN_TOKEN` secret on
    `seanr87/Factory`. Scopes needed: `repo`, `workflow` (the overlay pushes a workflow file),
    `delete_repo`, `project`, `admin:org`.
  - This is exactly the failure mode logged in AUDIT §1.5: a PAT bound to one person's account,
    expiring silently. Worth revisiting the GitHub App path, and D12 (move to `OHDSI-JHU`),
    once v2 is landed.
- [ ] **D6** Allow out-of-order gate evidence without backfilling *(rec: yes)*
- [x] **D7 — RESOLVED: clean slate.** Nothing is in production. The 19 test `study-*` repos under
      `seanr87` are test artifacts from Aug–Sep 2025 ("Left toe fungus", "Eagles 24 Cowboys 20",
      "absolutely zero"); the 2026 cohort has not been provisioned. No migration, no back-compat,
      no legacy path aliases. v2 can be built as the only implementation.
- [~] **D8** Test-artifact cleanup.
  - [x] 19 test `study-*` repositories deleted
  - [x] `seanr87/study-template` archived
  - [ ] 117 orphaned `Study: *` ProjectV2 boards deleted — blocked by the auto-mode classifier
        (bulk deletion); run `scratchpad/d8-cleanup.sh` section 1
  - [ ] 19 stale factory issues closed — same block; run `d8-cleanup.sh` section 2
  - Preserved deliberately: Factory Portfolio (#40), Factory Development (#57),
    `study-template-project-template` (#141), and all non-study projects.
- [x] **D9 — DECIDED: keep one ProjectV2 board per study**, with three views built in at provisioning.
      Factory keeps its own portfolio board for the cross-study stall radar; gate transitions write
      to both targets. My recommendation was one board; overridden, and that is the call.
  - **Milestones** — Board, grouped by Status, `label:milestone`. `Ready for review` gets its own
    column so the automation-proposes / human-closes step is visible.
  - **Work items** — Table, `label:work-item -label:partner`.
  - **Data partners** — Board, grouped by partner status, `label:partner`.
  - Build via `markProjectV2AsTemplate` + `copyProjectV2` from a hand-configured "Study Board"
    template, not `createProjectV2View` per study: one mutation instead of seven, views retunable
    in the UI without a code change, and it sidesteps any preview-gating on the view mutations.
- [ ] **D12** Should Factory and the study repos move to the `OHDSI-JHU` org?
      *(rec: yes, but not now — after v2 works)*
  - You are an org admin. The template board already lives there, and org ownership is what makes
    `markProjectV2AsTemplate` work at all.
  - `OHDSI-JHU` already has **Network Study Portfolio (#23)**, which looks like the intended home
    for the cross-study stall radar — worth checking before building a new factory portfolio board.
  - A fellowship program on one person's personal account is a succession risk; the PAT concern in
    D5 is the same problem wearing a different hat.
  - Against doing it now: study repos are created under `github.repository_owner`, so moving means
    re-pointing provisioning, re-issuing tokens, and re-testing everything. Land v2 first.
- [ ] **D10** Partner issues carry both `partner` and `work-item` labels, so they appear in the
      work-item queue. *(rec: exclude them — `-label:partner` — the partner view is their surface)*
- [ ] **D11** `Data Partner Status` field options: `setup-study-project` creates three
      (Preparation / Analysis / Results); `partner-tracking.md` defines seven (Not yet contacted ·
      Contacted · Interested · Committed · Package running · Results received · Declined).
      *(rec: adopt the seven — Gate 5 asks leads to distinguish interested from committed, and the
      three-option field cannot express Declined)*

Nothing below Phase 1 should start until D1–D4 are settled.

---

## Phase 1 — Scaffold from upstream, push the factory overlay

- [x] Repoint `create-study-repository` to `--template ohdsi-studies/StrategusStudyRepoTemplate`
- [x] Capture the upstream commit SHA at scaffold time; write it to the study's factory issue
- [x] Capture blob SHAs for every detected path at scaffold time, for baseline diffing (§3.2)
- [ ] Build the **factory overlay** — files pushed to the new repo after scaffolding:
  - [x] `.github/workflows/` — the push dispatcher (Phase 2)
  - [ ] `.github/actions/` — partner management
  - [x] `partners.csv`, schema `institution,contact_name,contact_role,contact_github`
  - [x] `TEAM.md` stub with a one-line example row
  - [x] `Documents/research-question.md` stub with Gate 1 headings pre-filled
  - [x] `Documents/results-summary.md` stub with Gate 7 headings pre-filled
- [x] Push the overlay as **one commit** with a known message, so the dispatcher can ignore it (§Phase 2)
- [x] Confirm `docs/` and `results/` stay gitignored, and that no gate depends on either (§3.1)
- [x] **Path-contract check** — daily factory workflow verifying every gate's detection paths still
      exist in upstream `main`; open a factory issue when one disappears
      — `.github/workflows/path-contract-check.yml`; all 8 upstream paths verified green
- [ ] Archive `seanr87/study-template` once the overlay replaces it

## Phase 2 — Study-repo dispatcher (the thin half)

- [x] New workflow: `on: push` → collect changed paths → `repository_dispatch` to factory
- [x] Send the **raw changed-file list**, not a pre-computed gate — all matching happens in factory (§4.6)
- [x] Payload: study repo, commit SHA, commit URL, author, changed paths, timestamp
- [ ] Verify `ORG_ADMIN_TOKEN` already present in provisioned repos can dispatch (§1.1 step 14)
- [x] Ignore pushes authored by factory automation, to prevent self-triggering
- [ ] Retire `factory-objective-update.yml`
- [ ] Replace `scheduled-project-status-sync.yml` polling with issue-event triggers
- [ ] Keep `manage-data-partners` but make it an upsert, and fix the CSV parser (§1.6)
- [ ] Point the partner action at the *study* project explicitly, not `projectsV2[0]`

## Phase 3 — Factory gate state machine (the thick half)

- [x] Gate config: gate number, name, corrected detection paths, advance rule, per §3.3
      — `.github/data/gates.json`, generated from the templates by `tools/build_gates.py`
- [x] `repository_dispatch` receiver mapping changed paths → candidate gate — `gate-state-machine.yml`
- [x] Baseline-diff check so scaffold-shipped files don't false-fire (§3.2)
- [x] **Overlay baseline gap closed** — `push-study-overlay` now re-reads the tree after its commit
      and records SHAs for `TEAM.md` and both `Documents/` stubs. Verified: baseline holds 15 blobs
      with `overlay_baseline` listing all three.
- [x] **Advance only** — reject any transition to a lower gate, log the rejection
- [x] **Propose, don't close** — evidenced gate moves to `Ready for review`; a human closes
- [x] **Always comment** — post which paths changed, in which commit, with a link. Pushes matching
      an already-passed gate also comment; pushes matching nothing stay silent, so comments keep meaning something.
- [x] Gates 5 and 6 excluded from path detection
- [ ] Gate 6 derived from partner issue status — needs the partner upsert (Phase 2)
- [x] Record `gate_entered_at` on every transition — this is the stall clock
- [x] Update the study repo's gate issue **and** the factory issue in the same run
- [ ] Update project fields: current gate, date entered, partner roll-up

## Phase 4 — Issue creation and templates

- [x] Parser for the front matter in `gate-*.md` (gate, title, labels, detection, advance_rule)
- [x] Apply the corrected paths from §3.3 to all eight gate files, and log every change made
- [x] Fix Gate 5's contradictory front matter (`detection.paths` + `manual_only`) (§4.5)
- [~] Factory issue status block — `run_gate_machine.py` rewrites a `<!--factory:status-->` block
      with current gate, entered date and days-in-gate. Partner roll-up still to come (Phase 5).
- [x] Replaced `create-status-issues` with `create-gate-issues` (Gates 0–7). Partner issues remain in Phase 2.
- [x] Label every item `milestone` or `work-item` — verified on a live study
- [ ] Make partner status machine-readable via `status:*` labels, mirrored into the body line (§4.1)
- [ ] Migrate the three legacy `status-tracking` issues in existing repos, or close them with an explanation

## Phase 5 — Stall detection

- [ ] Study stall = days since `gate_entered_at`; default 21, configurable via repo variable
- [ ] Partner stall = days since `max(last comment, last body edit)` (§4.2)
- [ ] Daily scheduled sweep across all studies
- [ ] Partner roll-up onto the factory issue — "4 partners, 2 stalled"
- [ ] Single at-a-glance view of all ten studies
- [ ] Retire `activity-check.yml` and its `pushed_at` signal
- [ ] Re-point or retire `bi-weekly-reminders.yml`

## Phase 6 — Project boards

### Per-study board (three views, D9)

- [x] Smoke-tested against the live API. Results:
  - `createProjectV2View`, `updateProjectV2View` (filter), `deleteProjectV2View` all work —
    **not** preview-gated. `deleteProjectV2View` returns no `deletedViewId`; select
    `clientMutationId`.
  - `markProjectV2AsTemplate` **fails for user-owned projects**: "Only projects owned by an
    Organization can be marked as a template." Factory is user-owned, so this is unavailable.
  - `copyProjectV2` works **without** the template mark, and carries every view across with its
    layout *and* filter intact. The template mark was never needed.
  - The default "View 1" is copied too — delete it from the source board once so studies come clean.
- [x] **Template board built and marked as a template:**
      [OHDSI-JHU/projects/30](https://github.com/orgs/OHDSI-JHU/projects/30) — `PVT_kwDOCQMYQc4BiEgy`
  - Three views with filters applied; default "View 1" deleted so copies come clean
  - `Data Partner Status` field with the seven D11 options
  - `markProjectV2AsTemplate` **succeeds here** because the project is org-owned — the earlier
    failure was purely about user ownership
  - **Cross-owner copy verified**: OHDSI-JHU template → `seanr87` user carried all three views
    (layouts + filters) and both fields (Status 3 options, Data Partner Status 7 options)
- [ ] Add a `Ready for review` option to the template's Status field, by hand in the UI.
      `updateProjectV2Field` replaces all options wholesale, so it is not safe to script.
      Target: Not started · In progress · **Ready for review** · Done
- [ ] Repoint `setup-study-project` from `createProjectV2` to `copyProjectV2` off template #30
- [ ] Fix `manage-data-partners`: address the study project explicitly, not `projectsV2(first:5).nodes[0]`

### Factory portfolio board (cross-study)

- [ ] Milestone view: current gate per study, all ten at a glance
- [ ] Fields: current gate, date entered, days in gate, partner count, stalled count
- [ ] Confirm gate transitions write to both the study board and the factory board

### Verification

- [ ] Confirm all three views survive provisioning of a new study
- [ ] Confirm a retune of the template board's views reaches subsequently provisioned studies

## Phase 7 — Cleanup and docs

- [ ] Delete `factory-issue-updater.yml` (dead — §1.4)
- [ ] Delete `.github/data/study-status-issues.json`
- [ ] Delete `.github/actions/create-status-issues`, `.github/actions/invite-collaborator`
- [ ] Delete `archive/` from factory
- [ ] README section for study leads: what the automation does to their repo, and why the board
      moves without them touching anything
- [ ] Update the factory README — the "Currently Built Functions" list describes v1
- [ ] Log the PAT-expiry risk (D5) somewhere durable

## Phase 8 — Verification before the cohort sees it

### Phase 3 end-to-end — PASSED on `main`

Branch merged to `main` first, because `repository_dispatch` only ever triggers workflows on the
default branch (see constraint below). Live results on `study-zzz-e2e-gate-test`:

| Action | Result |
|---|---|
| Provision | 8 gate issues, baseline (15 blobs), state file committed |
| Edit `TEAM.md` | dispatch → **advance −1 → 0**, Gate 0 issue commented, state committed, Factory issue status block written |
| Edit `Documents/Protocol.Rmd` | **advance 0 → 2** |
| Edit `TEAM.md` again | **HELD at gate 2** — "advance only, never retreat", comment explains why |

History recorded as `[(-1, 0), (0, 2)]` — no retreat, and the skipped Gate 1 was not backfilled (D6).

### Known constraint

**`repository_dispatch` only ever triggers workflows on the default branch.** The state machine
cannot be exercised by a real dispatch while it lives on `factory-v2-phase1` — the dispatch is
accepted (204) and silently discarded. `gh workflow run` resolves workflow names against the
default branch too, so the manual re-evaluation path is equally unreachable from a branch.
Merging to `main` is therefore a prerequisite for live end-to-end testing, not a final step.

### Test run log

- [x] **Path Contract Check** — passed in CI on `factory-v2-phase1`
      ([run 33467120633](https://github.com/seanr87/Factory/actions/runs/33467120633)):
      gatelib self-test 9/9, `gates.json` in sync, all 8 upstream detection paths matching.
- [x] **Provision smoke test — PASSED**
      ([run 33467968753](https://github.com/seanr87/Factory/actions/runs/33467968753)), after two
      failures that each found a real defect:
  - run 33467264099 — `ORG_ADMIN_TOKEN` invalid (401). PAT regenerated. **Provisioning had been
    broken since ~Sept 2025 and nobody knew.**
  - run 33467605623 — baseline commit rebased onto a hardcoded `main`; fixed to use
    `github.ref_name`.
  - Verified end to end: scaffolded from upstream `8c5c4a8`; **12 baseline blobs** recorded with
    only the 3 overlay-supplied paths unmatched; overlay applied as one `[factory-overlay]` commit
    (`TEAM.md`, `partners.csv`, both `Documents/` stubs, `notify-factory.yml`); `FACTORY_REPO` set;
    dispatcher **skipped** the overlay commit; a subsequent `TEAM.md` edit dispatched exactly
    `1 changed path: TEAM.md` to Factory with a 204.
  - The `ORG_ADMIN_TOKEN` PAT **does** carry `workflow` scope — pushing `.github/workflows/`
    cross-repo works, which was the top pre-test risk.

- [ ] End-to-end on a throwaway study repo: provision → edit `TEAM.md` in browser → Gate 0 moves to `Ready for review` → comment posted
- [ ] Confirm no gate false-fires on the provisioning commits themselves (README population)
- [ ] Confirm a backward transition is refused and logged
- [ ] Confirm a lead can complete Gate 0 through Gate 3 with **no command line**
- [ ] Confirm partner CSV round-trip: commit → issues created → status change → factory roll-up
- [ ] Confirm stall detection fires at the configured threshold, using a back-dated fixture
