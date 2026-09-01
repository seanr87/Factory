---
gate: 5
title: "Gate 5 — Data partners recruited"
labels: ["gate", "milestone"]
detection:
  paths: ["partners.csv"]
  event: derived_from_partners
  # In progress once anyone is being tracked at all. Ready for review once at
  # least one institution has actually agreed to run the study — "enough
  # partners to be worth running" is a judgement, so a human still closes it.
  in_progress_when: any_partner
  ready_when: any_committed
  note: "Derived from partner issues, never from a push. Committing partners.csv creates the issues; it does not recruit anyone."
advance_rule: derived_manual_close
---

**What this gate means.** You've identified the institutions you're asking to run your study, each one has an issue in this repository, and you've made contact. The gate closes when you have enough committed partners for the study to be worth running.

**Why it matters.** This is the longest and least visible phase of a network study, and it's where studies most often stall quietly. Nothing about recruitment shows up in your code, so if the tracking doesn't happen here, nobody — including you, three weeks from now — will know where things stand. It's also genuinely relational work: you're asking colleagues at other institutions to spend their analyst's time on your question. That takes follow-up, and follow-up takes a record of what was already said.

**What to produce**

- `partners.csv`, one row per institution you're approaching. Committing this file creates a tracking issue for each partner automatically.
- In each partner issue: keep the **body** current — who your contact is, where things stand, what you're waiting on. Add a **comment** after every exchange with two lines: what was asked, and what happens next.

Keep having your actual conversations by email or on calls. The issue is a log, not a replacement inbox. Two lines after a call is the whole ask.

**What good looks like** — check these yourself before you consider it done:

- Every partner issue's body tells you the current state without scrolling.
- No partner issue has been silent for three weeks. If one has, that's the signal to chase, not to assume.
- Governance status is written down per partner — DUA, IRB, data access — because these run on their own timelines and they're what usually determines your finish date.
- You know which partners are confirmed versus interested, and the issues distinguish the two.

**If you're stuck.** The OHDSI Evidence Network is where leads find partners with the right data, and the "How to Run a Study" material on the OHDSI Network Research Studies page covers the approach. Both are linked from the Network Studies in Practice page. If you're unsure how to make the ask, bring a draft email to office hours — we'd much rather review it than have you sit on it.

Partners saying no, or going quiet, is normal and not a reflection on your study. Tell us early when it happens; there is usually another route. Asking is always the right move.
