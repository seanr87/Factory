---
gate: 3
title: "Gate 3 — Cohort definitions committed"
labels: ["gate", "milestone"]
detection:
  # A cohort exists when it is both defined and registered: the JSON is the
  # definition, and Cohorts.csv is what the analysis specification resolves cohort
  # IDs against. One without the other is half a cohort.
  require: all
  paths:
    - "inst/cohorts/**/*.json"
    - "inst/Cohorts.csv"
  # Exported from Atlas alongside the JSON rather than authored separately.
  supporting_paths:
    - "inst/sql/sql_server/**/*.sql"
  event: content_changed
  baseline: upstream
advance_rule: auto_advance_to_review
---

**What this gate means.** Your study's cohorts exist as files in this repository — exported from Atlas, committed here, and readable by anyone on the team. Until that happens, your definitions live only in Atlas, where nobody else can see them, review them, or run them.

**Why it matters.** Everything downstream depends on these files. The analysis specification points at them, and every data partner runs *these exact definitions* — not a description of them, not a screenshot. This is the moment your study stops being a design and becomes something executable. It's also the point where mistakes get expensive: a concept set that's wrong here is wrong at every site.

**What to produce**

- Your cohort definition JSON files in `inst/cohorts/`
- The matching SQL in `inst/sql/sql_server/`
- One entry per cohort in `inst/Cohorts.csv`

In Atlas, open your cohort definition, go to the Export tab, and copy the JSON. If you've not committed a file before, the fastest route is the **Add file → Create new file** button at the top of the folder in your browser — no command line needed. Post in the study channel if you'd rather someone walk you through it once; that's a five-minute conversation, not a favour.

**What good looks like** — check these yourself before you consider it done:

- Every cohort you named in your protocol has a file here, and nothing extra does.
- You searched the OHDSI Phenotype Library first. If a definition already exists, you've either reused it or documented what you changed and why.
- Your entry event, index date, and exit criteria match what you wrote in your Phenotype Development Worksheet. If they've drifted, update the worksheet — the worksheet is the reasoning, the JSON is the implementation, and reviewers will read them side by side.
- You can say out loud what you deliberately excluded. Reviewers will ask.

**If you're stuck.** The Book of OHDSI, Chapter 10 covers cohort logic, and the Phenotyping & Cohort Definition page in the Resource Library has worked examples — Phenotype Phebruary especially. For anything specific to your study, bring it to office hours or tag your mentor here in this issue.

We don't expect the first version to be right. The point of the diagnostics cycle is to find out what's wrong and fix it — a clear, honest first draft is exactly right. If anything here is unclear, reach out early; asking is always the right move.
