---
gate: 7
title: "Gate 7 — Manuscript submitted"
labels: ["gate", "milestone"]
detection:
  paths: ["Documents/results-summary.md"]
  event: content_changed
  baseline: overlay
  note: "results/ is gitignored upstream and must not be pushed. The written summary is the evidence that reaches GitHub; the submission itself happens on a journal's system Factory never sees, so a person closes this gate once the lead reports it."
advance_rule: auto_advance_to_review
---

**What this gate means.** Your study has reached the thing it was for. Results from across your partners have been brought together, reviewed, written up, and submitted as a manuscript. This is the last gate, and it closes when the submission has gone in — not when it's accepted, and not when it's published. Acceptance runs on the journal's timeline; submitting is the part you control.

**Why it matters.** A network study that produces results nobody sees hasn't finished, and a summary in a repository is not the same as a paper on the record. The manuscript is also the first time your work is read sceptically by someone with no stake in it, so it's worth being your own harshest reviewer first: diagnostics that looked fine on one database can look very different across ten, and empirical calibration exists precisely because uncalibrated observational estimates tend to be overconfident. Reading your own results sceptically is part of the work, not a lack of confidence in it.

**What to produce**

- Combined results, stored per your team's agreement and honouring any minimum cell count suppression your partners required
- `Documents/results-summary.md` — what you found, what the diagnostics showed, what you'd caveat, and where the manuscript went: the journal and the date it was submitted
- The manuscript itself, submitted. A community call or a symposium abstract on the way there is good and encouraged, but neither closes this gate.
- A comment on this issue once it's in, saying which journal and when. Factory can't see a submission system; you're the only one who can tell it.

**What good looks like** — check these yourself before you consider it done:

- You've looked at diagnostics for every site, not just the aggregate. Sites that disagree are telling you something.
- Negative controls behave as they should, or you've said plainly that they don't.
- Cell count suppression is applied before anything is shared outside the team, the manuscript included. Check the terms each partner set individually; they differ.
- Every partner who contributed data is credited the way they asked to be — authorship, acknowledgement, or how their database is named — and has seen the manuscript before it went in.
- The manuscript states what the study can't conclude as clearly as what it can.

**If you're stuck.** Chapter 14 on evidence quality and Chapter 18 on method validity are the readings for this stage — Chapter 18 in particular is the clearest explanation of negative controls and calibration you'll find. The OHDSI Evidence Sharing portal shows what results dissemination looks like in practice, and recent OHDSI network study papers are the model for how a manuscript is structured. For interpretation, and for choosing where to submit, bring your draft to office hours; this is exactly the conversation your mentor is for.

Results that are null, messy, or not what you hoped are still results, and they are still worth publishing — a careful null finding from a network study is exactly what the literature is short of. Bring them to us as they are. Asking is always the right move.
