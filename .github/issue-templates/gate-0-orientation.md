---
gate: 0
title: "Gate 0 — Get oriented in GitHub"
labels: ["gate", "milestone"]
detection:
  paths: ["TEAM.md"]
  event: content_changed
  baseline: overlay
advance_rule: auto_advance_to_review
# Nothing has to happen before a lead can start this, so the board should say
# so from day one rather than showing it as not started.
initial_status: in_progress
---

**What this gate means.** You've made your first change in this repository and it worked. That's all. There's no research content here — this exists so the mechanics are behind you before anything intellectually hard starts.

**Why it matters.** Most of you haven't used GitHub before, and that's completely normal. The problem isn't that GitHub is hard; it's that the first commit feels like it might break something. It won't. Everything here is versioned and recoverable, and nobody has ever been thought less of for a messy first commit. Getting this one out of the way means that when you're wrestling with a cohort definition later, you're wrestling with the cohort definition and not the tooling.

**What to produce**

- Add yourself to `TEAM.md`: your name, institution, and your role on this study.

The easiest route is entirely in your browser. Open `TEAM.md` from the file list, click the pencil icon at the top right, type your line, then click **Commit changes** at the bottom. That's it — no software to install, nothing to download.

**What good looks like** — check these yourself before you consider it done:

- Your line appears in `TEAM.md` when you view the file normally (not in edit mode).
- You can find this issue again from the **Issues** tab without following a link from an email.
- You know where the **Files** view and the **Issues** tab are, and roughly what each is for.

**If you're stuck.** Post in the study channel. Someone will screen-share for five minutes and you'll be sorted — this is a normal thing to ask for, not a favour. If you'd like to read ahead, GitHub's own "Hello World" guide covers exactly this flow in about ten minutes.

We don't expect anyone to arrive fluent in this. A clumsy first commit is exactly right. If anything here is unclear, reach out early; asking is always the right move.
