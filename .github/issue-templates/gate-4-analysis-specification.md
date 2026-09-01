---
gate: 4
title: "Gate 4 — Analysis specification built"
labels: ["gate", "milestone"]
detection:
  # Both are needed before the specification exists in any real sense: the script
  # is what a designer edits, and the JSON it generates is what sites actually
  # run. Either one alone is work in progress, not a built specification.
  require: all
  paths:
    - "scriptsForStudyDesigner/CreateStrategusAnalysisSpecifications.R"
    - "inst/analysisSpecifications.json"
  # Inputs the script reads. Reported when they change, never sufficient on their
  # own — a design without negative controls is a legitimate design.
  supporting_paths:
    - "inst/negativeControlOutcomes.csv"
    - "inst/covariateConceptsToExclude.csv"
  event: content_changed
  baseline: upstream
advance_rule: auto_advance_to_review
---

**What this gate means.** Your study design now exists as a Strategus analysis specification: an R script that builds it, and the JSON specification that script produces. This is the artefact a data partner actually runs.

**Why it matters.** Up to now your study has been described in prose. This is the point where it becomes one machine-readable object that every site executes identically — which is the whole premise of a network study. It's also where design decisions stop being negotiable in conversation: if the specification says a 365-day washout, that's what runs at all ten sites, whatever the protocol says. Getting the two to agree is the work of this gate.

You are not expected to write this alone. We have analyst support, and most leads pair with an analyst here. Your job is to be certain the specification expresses the study *you* designed.

**What to produce**

- The R script that assembles the specification (`scriptsForStudyDesigner/CreateStrategusAnalysisSpecifications.R`)
- The generated specification JSON at `inst/analysisSpecifications.json`
- Negative control concepts, if your design uses them

**What good looks like** — check these yourself before you consider it done:

- The script runs end to end and produces the JSON without manual editing afterwards. A hand-edited specification will drift.
- Every cohort referenced in the specification exists in `inst/cohorts/`, by the same ID.
- Time windows, washout periods, and follow-up in the specification match `Documents/Protocol.Rmd`. Check these individually; this is the most common place the two diverge.
- You can explain, in a sentence each, what every analysis module in the specification does and why your study includes it.

**If you're stuck.** The Strategus documentation covers the concepts, and "Get Study-Ready with Strategus & HADES" (Anthony Sena, community call) is the clearest end-to-end walkthrough — both are linked on the Network Studies in Practice page. For the code itself, work with your analyst; that's what they're here for.

Not understanding every line of the specification is fine. Not knowing what your own study does is not — so if a module in there is a mystery to you, ask before this gate closes. Asking is always the right move.
