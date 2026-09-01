---
gate: 1
title: "Gate 1 — Research question locked"
labels: ["gate", "milestone"]
detection:
  paths: ["Documents/research-question.md"]
  event: content_changed
  baseline: overlay
advance_rule: auto_advance_to_review
---

**What this gate means.** The question your team is running is written down in this repository, in the form the rest of the study will be built against. Not the version from your symposium pitch, and not a topic area — a single question with a defined population, a defined thing being measured, and a defined window of time.

**Why it matters.** Every later gate inherits the wording of this one. Your cohort definitions are an attempt to express this question in code; your protocol is an attempt to defend it; your data partners will decide whether to participate based on it. Teams that leave the question slightly loose here spend weeks discovering they were each building something subtly different. It's also the cheapest possible moment to find out the question can't be answered — far better now than after a partner has run your package.

**What to produce**

- `Documents/research-question.md`, covering:
  - **Population** — who, and how they're identified in the data
  - **What you're measuring** — the condition, exposure, or outcome of interest
  - **Timing relative to pregnancy** — pre-existing, onset during pregnancy, delivery, or a postpartum window
  - **Analytic use case** — characterization, estimation, or prediction, and why that one
  - **Feasibility notes** — what you found when you looked for concept counts, and any databases you already know will or won't support this

**What good looks like** — check these yourself before you consider it done:

- Someone outside your team could read it and describe your study back to you correctly.
- Every clinical term you use is one you could point to concepts for. If you can't, say so explicitly — an acknowledged gap is fine, an unnoticed one is not.
- The timing window is stated in actual time, not implied. "During pregnancy" means different things to different people.
- You've said what this study will *not* answer. Scope you've deliberately excluded belongs in writing.

**If you're stuck.** Chapter 19 of the Book of OHDSI walks the path from research interest to precise question, and Chapter 20 covers what makes a question suitable for a network study specifically. The Network Studies in Practice page in the Resource Library has the exemplar protocols worth imitating. For your specific question, bring it to office hours — this is the gate where a conversation saves the most time.

We don't expect the first version to be final. Questions narrow as you learn what the data can support, and that's the process working, not a setback. If anything here is unclear, reach out early; asking is always the right move.
