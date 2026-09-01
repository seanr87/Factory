---
gate: 6
title: "Gate 6 — Study executed across partners"
labels: ["gate", "milestone"]
detection:
  event: none
  derived_from: partner_issue_status
  note: "Not detectable from repository activity. Advanced from partner issue status labels."
advance_rule: manual_only
---

**What this gate means.** Partners have run your study package on their data and returned aggregate results to you. This gate tracks how many have, out of how many committed.

**Why it matters.** This is the one phase that happens outside this repository entirely — on machines you'll never see, on data you'll never touch. Only aggregate results ever leave a partner site, which is the point of the whole federated model. What that means practically is that nothing here updates itself: if a site hits an error running your package, the only way you'll find out is that they tell you, or that you ask.

Expect errors. A package that runs cleanly on our data will still fail somewhere, usually on a vocabulary version or a table that site populates differently. That's ordinary, and it's fixable, but it needs someone chasing it.

**What to produce**

- Move each partner issue to **Results received** as their results arrive.
- When a site hits an error, log it as a comment on that partner's issue — what failed, and what you tried. Errors repeat across sites, and the second site's fix is usually the first site's comment.
- Store returned results where your team has agreed, following whatever the partner's transfer conditions were.

**What good looks like** — check these yourself before you consider it done:

- Every committed partner has either returned results or has a live, dated reason in their issue explaining why not.
- No partner has been silent for three weeks without a chase logged.
- You've confirmed each result set is complete before counting it as received, rather than assuming.

**If you're stuck.** Execution problems are almost always technical rather than scientific, and your analyst and the wider fellowship support are the right first call — don't spend a week debugging someone else's environment alone. Chapter 20 of the Book of OHDSI covers the execution phase and what to expect.

A site that fails to run your package has not rejected your study. Nearly every network study hits this. Flag it early and we'll help you work it through. Asking is always the right move.
