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
