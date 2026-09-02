# Deploying Factory in your own organisation

Factory is built for OHDSI network studies specifically — the gates, the artefacts it
watches for, and the guidance study leads read all assume a Strategus study. It is not
a general project tracker, and this guide does not try to make it one.

What it does assume is that *your* programme is not this one. Everything tied to a
particular installation — which organisation owns it, which template it scaffolds from,
which project boards it writes to — is a repository variable or secret, so a copy of
this repository can run somewhere else without editing code.

Budget about an hour, most of it waiting for a GitHub Actions run.

---

## 1. Copy the repository

Use **Use this template** or a fork, into the organisation that will own your studies.

Study repositories are created under whoever owns Factory, so **put Factory in the
organisation you want the studies in**. If Factory lives on a personal account, the
studies will too.

An organisation is strongly preferred over a personal account for two reasons that
already bit this installation: a personal access token bound to one person expires
silently and takes provisioning down with it, and `markProjectV2AsTemplate` refuses
projects owned by a user, so the shared study board has to be org-owned.

## 2. Create the access token

Factory writes to repositories it creates, so `GITHUB_TOKEN` is not enough.

Create a classic PAT at **github.com/settings/tokens** with:

| Scope | Why |
|---|---|
| `repo` | create study repositories, write issues |
| `workflow` | the overlay pushes a workflow file into each study repo |
| `project` | create and copy project boards |
| `admin:org` | read organisation membership, create org projects |

Set an expiry you will actually notice, and put the date somewhere. **This token expiring
is the single most likely way this system dies quietly** — provisioning simply stops, and
nothing announces it until someone tries to create a study.

**If your organisation enforces SAML SSO**, authorise the token for it: on the token page,
**Configure SSO → Authorize**. Without this the token is valid but cannot see org-owned
resources, and the failure reads like a permissions problem rather than an authorisation
one.

## 3. Set the secrets

Repository → Settings → Secrets and variables → Actions → **Secrets**:

| Secret | Value |
|---|---|
| `ORG_ADMIN_TOKEN` | the PAT from step 2 |

That is the only secret. One credential does everything, including committing back to
Factory — which needs the `workflow` scope, because adding a study lead rewrites the
dropdown inside `provision-study.yml`, and `GITHUB_TOKEN` is not permitted to modify
workflow files.

A GitHub App would be better practice for the write-back, being short-lived and scoped.
It was tried and removed: an App installed on one account stops working the moment the
repository moves to another, which is exactly the portability problem this guide exists
to avoid. If you want one, install it on the organisation and reinstate the
`create-github-app-token` step.

## 4. Create the Study Board template

Every study gets a board copied from a template, so the three views stay identical and
can be retuned centrally.

1. In your **organisation** (not a user account), create a new Project.
2. Name it something like `[TEMPLATE] Study Board`.
3. Add three views:

   | View | Layout | Column by | Filter |
   |---|---|---|---|
   | Milestones | Board | Status | `label:milestone` |
   | Work items | Table | — | `label:work-item -label:partner` |
   | Data partners | Board | Data Partner Status | `label:partner` |

   *Column by* is the board's own setting (view menu → **Column by**). A new board
   view defaults to columning by Status, which for the Data partners view means every
   card sits in Todo forever: the columns must be the partner statuses, so dragging a
   card is how a lead marks a partner. Provisioning warns when a copied board's Data
   partners view is columned by anything else.

4. Delete the default "View 1", or every study inherits a stray empty view.
5. On the **Status** field, add a `Ready for review` option and drag it **between
   In Progress and Done**. This is the column that makes "automation proposes, a human
   closes" visible; if it sits after Done the board reads backwards.
6. Add a single-select field named exactly **`Data Partner Status`** with these options,
   in order: `Not yet contacted`, `Contacted`, `Interested`, `Package running`,
   `Results received`, `Declined`. Do this before step 3's Data partners view, or
   come back and set its *Column by* afterwards.

   The names matter. Gate 5 advances when three partners are at *Interested* or
   further along, Gate 6 when three are at *Results received*, and partner status
   labels are derived from these. (`Committed` was an option once; if your template
   still has it, delete it — nothing reads it any more.)

7. Mark it as a template: **⋯ → Make template**.
8. Get its node ID:

   ```bash
   gh api graphql -f query='{organization(login:"YOUR-ORG"){projectsV2(first:50){nodes{id title}}}}' \
     --jq '.data.organization.projectsV2.nodes[] | select(.title|startswith("[TEMPLATE]")) | "\(.title)  \(.id)"'
   ```

## 5. Create the portfolio board

One board across all studies, for the programme-level view. Create it in the same
organisation and note its number from the URL (`/orgs/YOUR-ORG/projects/<number>`).

## 6. Set the variables

Repository → Settings → Secrets and variables → Actions → **Variables**:

| Variable | Required | Default | What it is |
|---|---|---|---|
| `STUDY_BOARD_TEMPLATE_ID` | **yes** | — | node ID from step 4. Provisioning fails without it. |
| `FACTORY_PROJECT_NUMBER` | yes | — | portfolio board number from step 5 |
| `FACTORY_PROJECT_URL` | yes | — | portfolio board URL |
| `STRATEGUS_TEMPLATE_REPO` | no | `ohdsi-studies/StrategusStudyRepoTemplate` | template studies are scaffolded from |
| `STUDY_REPO_PREFIX` | no | `study-` | prefix for generated repository names |

`STRATEGUS_TEMPLATE_REPO` must point at a repository marked as a template, and its layout
must match the detection paths in `.github/issue-templates/`. If you point it somewhere
else, expect to rewrite those paths — see step 9.

## 7. Clear the inherited study leads

Your copy arrives carrying this installation's people.

1. Empty `.github/data/study-leads.json` down to an empty list.
2. In `.github/workflows/provision-study.yml`, cut the `study_lead_selection` options
   back to just `'Add new study lead'`.

The dropdown rewrites itself as you add leads through provisioning, so this is a one-time
edit.

## 8. Provision a throwaway study

Actions → **Provision New Study** → title it something obviously disposable.

Check, in order:

- the repository exists and came from the Strategus template
- it has eight issues, Gate 0 through Gate 7, and the file names in them are links
  into the study repository
- it has `TEAM.md`, `partners.csv`, `Documents/research-question.md`,
  `Documents/results-summary.md`, and `.github/workflows/notify-factory.yml`
- its board has all three views, with Gate 0 and Gate 1 already in *In progress*
- Factory has a tracking issue listing every gate as not started, with no team
  and no partners yet, and `.github/data/baselines/` and `.github/data/state/`
  each gained a file

Then edit `TEAM.md` in the browser. Within a minute or two, Gate 0 should move to
*Ready for review* with a comment naming the commit. **That is the whole system working.**

Delete the study, its board, and its Factory issue afterwards, and remove its baseline
and state files.

## 9. Make the gates yours

The gate prose in `.github/issue-templates/` is written for a specific fellowship — it
references office hours, a study channel, and mentors. Read all eight and rewrite what
does not apply. Study leads read these; wrong instructions are worse than none.

If you change `detection.paths` in the front matter, regenerate the machine config:

```bash
python .github/scripts/build_gates.py
python .github/scripts/gatelib.py        # matcher self-test
python .github/scripts/gate_machine.py   # rule self-test
```

Commit the regenerated `.github/data/gates.json`. The templates are the source of truth;
`gates.json` is generated, and a check fails if they drift.

## 10. Adjust the schedule

Three scheduled workflows, all in UTC. Change the crons to suit your timezone:

| Workflow | Default | Does |
|---|---|---|
| `path-contract-check.yml` | 07:00 daily | verifies detection paths still exist upstream |
| `stall-check.yml` | 07:30 daily | derives Gates 5-6, finds what has gone quiet |
| `partner-sync.yml` | hourly | keeps the board's Data Partner Status and the `status:` labels in step, derives Gates 5-6 |

The stall threshold defaults to 21 days. Change `stall_threshold_days` in the partner
template's front matter and regenerate, or override per study in its state file.

---

## Things that will confuse you

These are all real failures from running this system, not hypotheticals.

**`repository_dispatch` only ever triggers workflows on the default branch.** You cannot
test the gate state machine from a branch — the dispatch is accepted with a 204 and
silently discarded. `gh workflow run` also resolves workflow names against the default
branch. Anything dispatch-driven has to be on `main` to be exercised at all.

**An expired `ORG_ADMIN_TOKEN` reports as almost anything else.** A 401 from the API
surfaces as whatever the calling step was trying to do. If provisioning fails at the
first step for no apparent reason, check the token before anything else.

**SAML authorisation is separate from token scopes.** A correctly-scoped token that has
not been SSO-authorised for your organisation cannot see org-owned projects, and the
error talks about the resource, not the authorisation.

**Nothing false-fires at provisioning, and that is deliberate.** The Strategus template
already ships `Protocol.Rmd`, sample cohorts, `Cohorts.csv`, and
`analysisSpecifications.json`. Factory records a blob SHA per detected path when the
study is created, so a gate only advances when content differs from what the template
gave you. If you change how scaffolding works, keep that.

**Upstream Strategus restructures.** It did so twice in nine months, and either change
would have silently broken Gate 3 and Gate 4 for every study created afterwards. Path
Contract Check runs daily and opens an issue naming the broken paths, where each file
probably moved to, and which template lines to edit. If that issue appears, **stop
provisioning new studies until it is resolved** — studies already created are unaffected,
since each matches against the layout it was scaffolded from.

**Detection config is global, not per study.** If some studies were created before an
upstream restructure and some after, list *both* paths so both cohorts are detected. The
contract check will then keep reporting the retired path as missing, which is accurate
and is the price of not breaking the older cohort.
