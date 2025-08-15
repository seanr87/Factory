# Factory Demo (Personal Account: `seanr87`) — End-to-End Checklist

## 0) Prereqs (once)
- [x] Ensure **GitHub Projects (v2)** is available on your user account.
- [x] Create a **fine-grained PAT** with: Repos (R/W), Projects (R/W), Actions (R/W).

## 1) Create the **Factory** portfolio (user-level Project)
- [x] Profile → **Projects** → **New project** → name it **Factory**.
- [x] Add fields: **Stage** (single-select), **Lead**, **Lead Site**, **Partner Sites** (text), **Partner Count** (number), **Target Date** (date), **Repo** (text/URL).
- [x] Note the **project number** from the URL → you’ll use it as `FACTORY_PROJECT_NUMBER`.

## 2) Create repos
- [ ] Create private repo **`study-template`** under `seanr87`.
  - [x] Add **labels**: `stage:protocol-development … stage:results-evaluation`, `partner-site`.
  - [x] Add **issue templates** (9 **stage checklist** issues; “Lead-site IRB approved” lives in **Protocol development**).
  - [x] Add **Issue Forms**:  
    - `Add Data Partner` (fields: Site, @GitHub (opt), Email (opt), Notes (opt))  
    - `Bulk Add Data Partners` (one site per line; optional `@github,email,notes` suffixes)
  - [x] Add **workflows**:  
    - **Stage sync** (close a stage checklist → update Stage locally + in Factory)  
    - **Partner sync** (create/edit/close partner-site issues → update **Partner Sites** + **Partner Count** in Factory; welcome ping on assignment)  
    - **Weekly Partner Nudge** (default **Mon 9:00 ET**, configurable via repo vars; stale if no activity for **7** days)
  - [ ] Add **README.md** (language-neutral OHDSI style) + `docs/STRATEGUS.md` placeholder.
- [ ] Create private repo **`BIDS_General`** under `seanr87`.
  - [ ] Add **Provision New Study** workflow (creates repo + per-study Project, seeds stage checklist issues, creates **partner-site** issues from intake, links to Factory, sets perms/vars).
  - [ ] Add **Factory Health** weekly digest workflow (Mon **9:05 ET**).

## 3) Wire secrets & variables (in `BIDS_General` → Settings → Actions)
- [ ] **Secrets**:  
  - `ORG_ADMIN_TOKEN` = your fine-grained PAT  
  - `ORG_LOGIN` = `seanr87`  
  - `FACTORY_PROJECT_NUMBER` = (from step 1)  
  - `TEMPLATE_REPO` = `seanr87/study-template`
- [ ] (Optional) **Variables**: none required at the `BIDS_General` level.

## 4) First end-to-end provision
- [ ] `BIDS_General` → **Actions → Provision New Study → Run workflow** with:
  - **Study Title**, **Lead**, **Lead Site**, **Partner Sites** *(CSV of ALL potential partners)*, **Target Date**
  - **Admins** (e.g., `seanr87`), **Maintainers** (optional)
  - **Partner Contacts CSV** (optional; lines like `SiteName,@github,email(optional),notes(optional)`)
- [ ] Verify it created:
  - [ ] New repo **`study-<kebab-slug>`** under `seanr87`
  - [ ] Per-study Project **`Study: <Title>`** (linked to repo) with **Stage** field
  - [ ] **9 stage checklist issues** labeled `stage:*` (added to the Project)
  - [ ] **Partner-site issues** (one per site), **Status = Potential**, assigned if contacts provided, on the Project
  - [ ] A **Factory** row with **Stage, Lead, Lead Site, Partner Sites, Partner Count, Target Date, Repo**

## 5) Show the demo flow
- [ ] **Advance a stage:** close **Protocol development** checklist → confirm **Stage** updates in both the per-study Project **and** Factory.
- [ ] **Add a partner post-provision (single):** open **Issue → New → Add Data Partner** → submit → confirm issue appears, added to Project, Factory **Partner Sites/Count** update.
- [ ] **Add partners in bulk:** **Issue → New → Bulk Add Data Partners** (paste lines) → confirm multiple issues created & rolled up to Factory.
- [ ] **Weekly nudge (demo now):** run **Weekly Partner Nudge** via `workflow_dispatch` → see a digest issue tagging the Lead + comments on stale partner-site issues.
- [ ] **Factory Health digest:** in `BIDS_General`, run **Factory Health** → verify summary (counts by Stage, overdue, partner counts).

## 6) Tweak defaults (per-study repo → Settings → Variables)
- [ ] `NUDGE_DAY=Mon`
- [ ] `NUDGE_HOUR_LOCAL=9`
- [ ] `NUDGE_TZ=America/New_York` *(can be changed by the Lead)*
- [ ] `STALE_DAYS=7`
- [ ] `STUDY_LEAD_GH=@yourhandle`

## 7) (Optional) External collaborator demo
- [ ] Study repo → **Settings → Collaborators** → add an external GitHub account with **maintain**.
- [ ] Assign them to a **partner-site** issue.
- [ ] Trigger **Weekly Partner Nudge** to show they get a notification.

## 8) Screen-share script (what to show)
- [ ] **Factory** portfolio grouped by **Stage**; fields per study.
- [ ] The new **study repo** (README + stage issues) and **per-study Project**.
- [ ] **Partner management** via partner-site issues (assignment, comments) and automatic roll-up to Factory.
- [ ] **Stage advancement** by closing a checklist issue.
- [ ] **Weekly Partner Nudge** digest and **Factory Health** issue.

---

### Example inputs for the provision form

**Partner Sites (CSV):**
```text
Stanford Medicine, Emory, Johns Hopkins, Columbia, Mayo Clinic
