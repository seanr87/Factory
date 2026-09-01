---
gate: 2
title: "Gate 2 — Protocol drafted"
labels: ["gate", "milestone"]
detection:
  paths: ["Documents/Protocol.Rmd"]
  event: content_changed
  baseline: upstream
  # "The file changed" is a poor proxy here: a sentence added to a 16-section
  # protocol makes the file differ from the template without the protocol being
  # drafted. A section counts as written when its body differs from the body the
  # template shipped, so untouched boilerplate never counts.
  require: all_sections
  # The subset that applies to a characterization study. Exposure Comparators,
  # Sample Size and Study Power, and Adverse Events are deliberately absent —
  # requiring them would leave a legitimate characterization study permanently
  # in progress. Add them back for an estimation programme.
  sections:
    - "Rationale and Background"
    - "Study Objectives"
    - "Study Design"
    - "Data Sources"
    - "Study Population"
    - "Outcomes"
    - "Analysis"
    - "Strengths and Limitations"
    - "Protection of Human Subjects"
    - "Plans for Disseminating and Communicating Study Results"
advance_rule: auto_advance_to_review
---

**What this gate means.** Your study has a written protocol in this repository, following the OHDSI protocol structure. It doesn't need to be finished prose, but every section needs a real answer rather than a placeholder.

**Why it matters.** In OHDSI, the protocol is what you hand a data partner when you ask them to run your study, and it's what a reviewer reads when deciding whether to trust your results. Writing it before execution is a norm the community takes seriously: it's how the field distinguishes a planned analysis from one that was shaped after seeing the answer. Practically, it's also the document that forces you to make decisions you've been deferring — comparator choice, follow-up window, how you'll handle people who appear more than once.

**What to produce**

- `Documents/Protocol.Rmd`, using the 16-section OHDSI protocol skeleton (Appendix D of the Book of OHDSI). Copy the structure wholesale; don't invent your own.

**What good looks like** — check these yourself before you consider it done:

- Every section has content. Where you genuinely haven't decided, write what the options are and what would settle it, rather than leaving the heading bare.
- Your population, outcome, and timing match `Documents/research-question.md` word for word. If they've changed, change both.
- You've named your negative controls, or explained why the design doesn't call for them.
- A data partner reading only this document would know what will be run on their data and what leaves their site.

**If you're stuck.** Appendix D gives you the skeleton, Chapter 3 explains why forward registration matters, and the LEGEND-T2DM protocol paper on the Network Studies in Practice page is a published example of the standard to aim at. The `ohdsi-studies` organisation on GitHub has around 190 real study repositories — reading two or three protocols from studies like yours is the fastest way to calibrate.

Nobody writes a good protocol from a blank page. Copy the structure, fill it roughly, then refine with your mentor. If anything here is unclear, reach out early; asking is always the right move.
