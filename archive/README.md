# Factory: A Simple, Consistent Way to Track OHDSI Network Studies

**Audience:** General (study leads, collaborators, PMs)

## Vision

Give every OHDSI network study the same, simple tracking experience: one click to create a study space, a clear checklist of stages, and an org‑wide portfolio view that shows where each study is—without extra project‑management overhead.

## Why

* Today, tracking is inconsistent and manual; status is hard to see across studies.
* Study leads are busy clinicians—tools must be low‑friction.
* We want something portable the wider OHDSI community can adopt.

## What We’re Building

**Hybrid structure on GitHub Enterprise (JHU‑OHDSI):**

* **Factory (org project):** a single portfolio view showing one row per study with key fields: **Stage, Lead, Lead Site, Partner Sites, Target Date, Repo**.
* **Per‑study space (one repo + small project):** each study has its own repository and a lightweight project board that the lead uses day‑to‑day.

**Standard stages (from Ben’s framework):**

1. Protocol development  2) Data diagnostics  3) Phenotype development  4) Phenotype evaluation  5) Analysis specifications  6) Network execution  7) Study diagnostics  8) Evidence synthesis  9) Results evaluation
   *(Ben remains the owner of this list and can adjust as needed.)*

**Low‑code automation:**

* In **BIDS\_General**, a “**Provision New Study**” button asks for **Title, Lead, Lead Site, Partner Sites (best guess), Target Date, Admins/Maintainers**.
* The workflow then **creates the repo from a template**, makes the per‑study project/fields, seeds **stage checklist issues** (one per stage), links everything to **Factory**, and assigns repo permissions.
* Leads advance the study by closing the appropriate **stage checklist issue**. The study’s **Stage** updates automatically in the per‑study board and in **Factory**.

**Portable by design:**

* Language‑neutral study template (README based on OHDSI conventions).
* Option to add a Strategus scaffold later when it stabilizes.

## How It Works (at a glance)

1. Operator clicks **Provision New Study** in **BIDS\_General** and fills the short form (best‑guess is fine).
2. GitHub Actions/CLI create and wire up the study repo and project.
3. The study lead uses the per‑study board and closes **stage checklist issues** as milestones are met.
4. **Factory** always shows the latest Stage and key metadata for all studies.

## Implementation Steps

1. **Confirm stages:** Ben reviews/edits the 9‑stage list.
2. **Create Factory:** Org‑level project in `JHU‑Odyssey` with fields: Stage, Lead, Lead Site, Partner Sites, Target Date, Repo.
3. **Make a study template repo:**

   * Include OHDSI‑style **README** and the 9 **stage checklist issues** (issue templates).
   * Add a minimal `docs/STRATEGUS.md` noting future option.
4. **Add the provision workflow in ****`BIDS_General`****:** inputs (Title, Lead, Lead Site, Partner Sites, Target Date, Admins, Maintainers) → creates repo & project, seeds issues, links to Factory, sets permissions.
5. **Configure org secrets:** `ORG_ADMIN_TOKEN`, `ORG_LOGIN`, `FACTORY_PROJECT_NUMBER`, `TEMPLATE_REPO`.
6. **Create project views:**

   * **Factory:** table grouped by Stage; show Lead, Lead Site, Partner Sites, Target Date, Repo; add basic Insights charts.
   * **Per‑study:** simple board/roadmap for leads.
7. **Pilot with 2 studies,** adjust fields/wording, confirm auto‑updates.
8. **Roll out** to remaining studies; share the template/provisioner so other OHDSI groups can adopt.

*Questions or stage changes? Ben is the stage owner—edit once, everything respects the update.*

---

## Amendments (per latest decisions)

### A) Partner Tracker = **Issue-based**, assignable, and automated

* Each Data Partner is a **GitHub Issue** labeled `partner-site`, automatically added to the per‑study Project.
* **Initial Status:** `Potential` (default) → `Invited` → `Diagnostics Sent` → `Diagnostics Returned` → `Package Executed` → `Results Uploaded` → `Blocked` (if needed).
* **Intake:** Provision form must list **ALL potential partners**; automation creates one `partner-site` issue per site (no manual issue creation by the operator).
* **Lead adds partners later:** Use an **Issue Form: “Add Data Partner”**. A small workflow creates the `partner-site` issue, assigns the contact, and adds it to the project. The Factory row is updated with **Partner Sites** (CSV) and **Partner Count**.

### B) Weekly Nudge = default Monday 9am ET, **configurable by Study Lead**

* Default cadence: **Mondays at 9:00 AM America/New\_York**.
* Config via repo variables: `NUDGE_DAY` (Mon|Tue|...), `NUDGE_HOUR_LOCAL` (0–23). The workflow runs hourly on the chosen day and self‑checks local time to fire **once** at the configured hour (DST‑safe); Study Lead can edit variables in repo **Settings → Variables**.
* Behavior:

  * Updates/creates a **“Weekly Partner Nudge”** issue tagging the Study Lead with a checklist of stale partner‑site issues.
  * Posts a short comment on each stale partner‑site issue tagging its **assignee** (generates a GitHub notification).

### C) Provisioner behavior

* The **Provision workflow** in `BIDS_General` creates everything: repo, per‑study project/fields, **stage checklist issues**, **partner‑site issues** (from intake list), Factory item, and permissions. The operator **never** creates issues manually.

### D) Factory fields

* Add **Partner Count** (number) and keep **Partner Sites** (CSV/text) so the portfolio can summarize partner activity.

### E) README adjustments (study template)

* Add a short **“Working with Data Partners”** section:

  1. Use **Issue Form: “Add Data Partner”** to add a site (creates an assignable issue and adds it to the board).
  2. Status starts at **Potential**; update as you progress (or close when withdrawn).
  3. Weekly nudge defaults to **Mon 9am ET**. To change, update repo variables **NUDGE\_DAY**/**NUDGE\_HOUR\_LOCAL**.
  4. Keep the **Protocol** and **ATLAS/Cohort links** in the README up to date.
* Keep the README **language‑neutral**; include note that a **Strategus** scaffold can be added later once stable.
