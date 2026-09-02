# Demonstrating the automation

A walkthrough that exercises every moving part in about fifteen minutes, entirely in a
browser — which is the point, since study leads never touch a command line.

Do it in a study repository you are happy to throw away. `study-study-to-test-v2` is the
current demo study.

Keep two tabs open beside the study repository:

- the study's **Issues** tab
- the **[Factory Portfolio](https://github.com/orgs/OHDSI-JHU/projects/32)** board

Each step below takes under a minute to fire. The dispatch is near-instant; the workflow
run takes 20–40 seconds.

---

## 1. A gate advances on its own

**Do:** open `TEAM.md` in the study repo, click the pencil, add a row to the table,
**Commit changes**.

**Watch:**

- Factory → Actions → **Gate State Machine** starts within a few seconds
- the **Gate 0** issue gets a comment naming the paths and the commit
- the Factory issue's status block updates
- the portfolio board's `Gate` moves to *Gate 0*

**The point:** nobody reported anything. The commit *was* the report.

> Already at Gate 0? Use `Documents/research-question.md` instead and watch Gate 1.

## 2. It refuses to go backwards

**Do:** edit `TEAM.md` again — add another row.

**Watch:** the gate does **not** move back to 0. A comment appears saying:

> evidence for gate 0, but the study is already at gate N — advance only, never retreat

**The point:** revisiting earlier work never undoes progress. Leads circle back constantly;
the board should not flinch.

## 3. It proposes, it does not conclude

**Look at** any advanced gate issue. It is **open**, marked *Ready for review*.

**The point:** Factory can see a file appeared. It cannot see whether the file is any good.
Closing a gate is a human reading the work and deciding.

## 4. It ignores the template's own files

**Do:** open `inst/Cohorts.csv` and commit it **unchanged** (or change it and change it
back).

**Watch:** Gate 3 does not move. The run log says the path matched a gate but is unchanged
from the template baseline.

**The point:** the Strategus template already ships `Protocol.Rmd`, sample cohorts,
`Cohorts.csv` and `analysisSpecifications.json`. Without this check, five of six gates
would fire the moment a study is created. Factory records a blob SHA per watched path at
provisioning and compares against it.

## 5. Real work on a template file does count

**Do:** open `Documents/Protocol.Rmd`, add a line under any heading, commit.

**Watch:** Gate 2 moves to *Ready for review*.

**The point:** same file as the previous step. The difference is that the content now
differs from what the template gave you.

## 6. Partners appear from a spreadsheet

**Do:** open `partners.csv` and add rows:

```csv
institution,contact_name,contact_role,contact_github
Johns Hopkins Medicine,Alice Chen,Data Steward,alicechen
Stanford Medicine,Carol Diaz,Informatics Lead,cdiaz
Mercy Hospital,Dan Osei,Analyst,
```

**Watch:** three issues appear, labelled `partner` + `work-item` + `status:not-contacted`,
and on the study board's **Data partners** view.

**The point:** the lead edits a spreadsheet. Note the third row has no GitHub username and
still works — the old parser dropped rows like that silently.

## 7. Gate 6 comes from partner status, not from Git

**Do:** on two partner issues, swap `status:not-contacted` for `status:results-received`.
On the third, set `status:declined`.

**Then:** Factory → Actions → **Stall Check** → *Run workflow*. (It runs daily at 07:30
UTC; running it by hand just skips the wait.)

**Watch:** Gate 6 moves to *Ready for review*, with a comment listing which partners
returned.

**The point:** execution happens on machines Factory never sees. The only trace that
reaches GitHub is the labels. Note the declined partner did **not** block the gate — one
refusal should not stall a study.

## 8. Silence becomes visible

**Do:** Actions → **Stall Check** → *Run workflow*, and set **threshold_days** to `0`.

**Watch:** the `portfolio-status` issue in Factory is rewritten with every study red, and
a per-partner breakdown of who has gone quiet. The portfolio board's **Stall radar** view
shows `Days in Gate` for each study.

**Then run it again with the field blank** to return to the real 21-day threshold.

**The point:** this is the whole reason the system exists. A stalled study never announces
itself — it just goes quiet. Something has to go looking.

## 9. It warns when its own contract breaks

**Do:** Actions → **Path Contract Check** → *Run workflow*, with **simulate_move** set to:

```
scriptsForStudyDesigner/=scripts/designer/
```

**Watch:** the run reports Gate 4's path as broken and names where the file probably moved
to. With `dry_run` ticked it only prints; untick it and it opens a real issue containing
the template to edit, the front-matter key, the replacement value, and the commands to run.

**The point:** studies are scaffolded from upstream Strategus at provision time, and
upstream restructured twice in nine months. Either change would have silently broken Gate 3
and Gate 4 for every study created afterwards. This makes it announce itself.

---

## What to say while demonstrating

The system rests on four rules, and steps 2, 3, 4 and 8 each show one:

- **Advance only, never retreat.** Progress is never undone by revisiting work.
- **Automation proposes; a human closes.** Detecting a file is not judging it.
- **Always comment, never silently flip.** Every change says what it saw and where. People
  stop trusting automation the first time it is wrong and unexplained.
- **Evidence, not existence.** A path counts only when its content differs from what the
  template shipped.

And the thing worth repeating: **no study lead is ever asked for a status update.** Progress
is read from the artefacts the study already produces. A lead who is stuck or overwhelmed is
the least likely person to file a report about it — which is exactly when someone needs to
know.

## Resetting between demos

Provision a fresh study, or reset the current one:

1. Delete `.github/data/state/<study>.json` and `.github/data/baselines/<study>.json` from
   Factory
2. Delete the study repository, its board, and its Factory issue

Then Actions → **Provision New Study**. Run it from `main` — provisioning from a branch
writes state to that branch, while `repository_dispatch` only ever delivers to the default
branch, so gate detection will not fire until it is merged. The workflow warns you if you
pick a branch.
