# How this repository is tracked

Things in this repository will move without you touching them. Issues will change
state, comments will appear, and your board will update. That is intended, and
this page explains exactly what is happening and why.

**The short version.** You do your work. The tracking follows.

---

## You are not asked to do project management

Nobody is going to ask you for a status update, and you are never expected to
drag an issue from one column to another to report progress.

The reason is simple. A study that has stalled does not announce itself — it just
goes quiet. If progress depended on you remembering to report it, the studies most
in need of help would be the ones least likely to be flagged, because a lead who is
stuck or overwhelmed is not going to file a status update about it. So progress is
worked out from the study itself.

## What actually happens

A Strategus study leaves artefacts behind as it moves: a research question, a
protocol, cohort definition files, an analysis specification, results. Those files
are the evidence.

When you commit one of them, a small workflow in this repository tells the Factory
repository which file paths changed — nothing else, not the contents. Factory
decides what that means and updates the matching gate issue here.

So the sequence is:

1. You edit a file. The browser is fine; you never need the command line.
2. Factory notices the path changed.
3. The relevant gate issue moves to **Ready for review**.
4. A comment appears on that issue saying exactly which paths changed and in which
   commit.

## Four rules the automation follows

**It only ever moves forward.** A gate is never moved backward. If you go back and
revise your protocol after reaching a later gate, your board will not regress —
you will get a comment noting the work, and the gate stays where it is.

**It proposes; a person decides.** Factory can see that a file appeared. It cannot
see whether the file is any good. So it moves a gate to *Ready for review* and stops
there. Closing a gate is always a human decision, after a human has read the work.

**It always explains itself.** Every automated change posts a comment saying what it
saw and where. Nothing changes silently. If something moves and you cannot tell why,
that is a bug worth reporting.

**Two gates are never automatic.** Gate 5 (recruiting data partners) and Gate 6
(sites running your study) happen outside this repository entirely, on machines and
in conversations Factory cannot see. Gate 6 moves when every committed partner's
issue is marked as having returned results. Gate 5 is moved by hand.

## What it does *not* do

- It does not read your file contents — only which paths changed.
- It does not close anything. Ever.
- It does not judge quality, and a gate reaching *Ready for review* is not approval.
- It does not email you or chase you. It updates issues and a board.

## Files Factory watches

| Gate | What it watches for |
|---|---|
| 0 | `TEAM.md` |
| 1 | `Documents/research-question.md` |
| 2 | `Documents/Protocol.Rmd` |
| 3 | `inst/cohorts/`, `inst/Cohorts.csv`, `inst/sql/sql_server/` |
| 4 | `inst/analysisSpecifications.json`, the analysis specification script |
| 5 | manual — partner issues are the record |
| 6 | manual — derived from partner issue status |
| 7 | `Documents/results-summary.md` |

Some of these files already exist, because they ship with the Strategus template.
Factory records what the template gave you when your repository was created and
compares against it, so an untouched template file never counts as your work.

Two things it deliberately does not watch: `docs/` and `results/`. Both are excluded
by `.gitignore` — `results/` because aggregate results should not be pushed to a
public repository by reflex. Your written summary is what evidences Gate 7, not the
result files themselves.

## Data partners

Commit a row to `partners.csv` and an issue is created for that partner.

- **The body is the current state.** Overwrite it as things change, so anyone can
  see where a partner stands without scrolling.
- **The comments are the history.** Add two lines after each exchange: what was
  asked, and what happens next.

Those comment dates are how a partner going quiet gets noticed. Keep having your
actual conversations by email and on calls — the issue is a log, not an inbox.

## Going quiet

Once a day, Factory checks how long each study has been sitting in its current gate,
and how long since anything was logged on each partner issue. Past **21 days**, it
flags them.

This is not a performance measure, and it is not there to chase you. Studies stall
for entirely ordinary reasons — a partner goes silent, an approval takes months, a
question turns out to need rethinking. The flag exists so somebody notices and can
offer help, which cannot happen if nobody knows.

## If something looks wrong

If a gate moves when it should not have, or does not move when it should, say so.
Every automated change is explained in a comment, so there is always a record of what
Factory thought it saw. Getting that wrong is a bug in the automation, never a
mistake on your part.

Post in the study channel or raise it with the fellowship team. Asking is always the
right move.
