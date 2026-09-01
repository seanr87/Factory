---
gate: 7
title: "Gate 7 — Results synthesised and shared"
labels: ["gate", "milestone"]
detection:
  paths: ["Documents/results-summary.md"]
  event: content_changed
  baseline: overlay
  note: "results/ is gitignored upstream and must not be pushed. The written summary is the evidence."
advance_rule: auto_advance_to_review
---

**What this gate means.** Results from across your partners have been brought together, reviewed, and written up in a form other people can read — a summary in this repository at minimum, and for most studies an abstract, a presentation, or a manuscript.

**Why it matters.** A network study that produces results nobody sees hasn't finished. This is also the gate where you find out whether the answer is trustworthy: diagnostics that looked fine on one database can look very different across ten, and empirical calibration exists precisely because uncalibrated observational estimates tend to be overconfident. Reading your own results sceptically is part of the work, not a lack of confidence in it.

**What to produce**

- Combined results, stored per your team's agreement and honouring any minimum cell count suppression your partners required
- `Documents/results-summary.md` — what you found, what the diagnostics showed, and what you'd caveat
- Whatever external output your study is aiming at: OHDSI community call, symposium abstract, manuscript

**What good looks like** — check these yourself before you consider it done:

- You've looked at diagnostics for every site, not just the aggregate. Sites that disagree are telling you something.
- Negative controls behave as they should, or you've said plainly that they don't.
- Cell count suppression is applied before anything is shared outside the team. Check the terms each partner set individually; they differ.
- Your summary states what the study can't conclude as clearly as what it can.

**If you're stuck.** Chapter 14 on evidence quality and Chapter 18 on method validity are the readings for this stage — Chapter 18 in particular is the clearest explanation of negative controls and calibration you'll find. The OHDSI Evidence Sharing portal shows what results dissemination looks like in practice. For interpretation, bring your output to office hours; this is exactly the conversation your mentor is for.

Results that are null, messy, or not what you hoped are still results, and they are still worth publishing. Bring them to us as they are. Asking is always the right move.
