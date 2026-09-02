#!/usr/bin/env python3
"""Render a study's Factory tracking issue: where it is, who is on it, who runs it.

The Factory issue is the page the coordinating team opens when a study needs
help. It used to carry the three v1 milestones — "Analysis Package Prototype",
"Network Execution", "Journal Submission" — written at provisioning and never
touched again, with the live gate appended underneath by two different scripts
in two different blocks. Now one renderer owns everything below the header, and
every job that learns something about a study calls it:

  gate-state-machine   on every push, with the commit as the last activity
  partner-sync         hourly, so a partner moved on the board shows within the hour
  stall-check          daily, with the stall threshold it is using
  provisioning         once, so the issue is complete from the day it exists

What it shows, and where each part comes from:

  Progress        the study's state file: current gate, time in it, last push
  Study history   every gate with its status now and the dates it reached In
                  progress, Ready for review, and Closed — three separate
                  columns, so the record can be studied later. Gates are named
                  by what they are for, not their number: the number is a
                  Factory detail, the name is what a person asks about. Closed
                  comes from the gate issue itself, because closing is the one
                  thing the state file cannot see.
  Study team      TEAM.md in the study repository: name, institution, role,
                  GitHub username
  Data partners   the partner issues: institution, status, contact, and how long
                  since anyone logged anything — so the coordinating team can
                  see who to ring, not just how many partners there are

Everything between the two markers is rewritten on every refresh, and only
written when it differs. A no-op refresh must not touch the issue, or its
updated-at stops meaning anything. Text above the markers — the title, the
repository, the lead — belongs to provisioning and is left alone. An issue from
before the markers existed is migrated the first time it is refreshed: the
header is kept, the v1 table and the old status blocks are replaced, and the
start and target dates are carried across from the old table.

Usage:
    factory_issue.py --study owner/study-x [--dry-run]
    factory_issue.py --all [--dry-run]
    factory_issue.py --self-test
"""

import argparse
import base64
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from partnerlib import OPTION_FOR_LABEL  # noqa: E402

__all__ = ["refresh", "render", "read_file", "team_rows", "partner_rows"]

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
GATES = ROOT / ".github" / "data" / "gates.json"

START, END = "<!--factory:body-->", "<!--/factory:body-->"

# Where the header ends on an issue from before the markers: the v1 table, the
# two blocks the earlier scripts appended, and the v1 activity stamp. The first
# of these found is where the migration cuts.
LEGACY_CUTS = ("### Study History", "### Activity",
               "<!--factory:status-->", "<!--factory:rollup-->")

READY, DONE, IN_PROGRESS, NOT_STARTED = ("ready_for_review", "done",
                                         "in_progress", "not_started")
STATUS_TEXT = {
    DONE: "✅ Closed",
    READY: "🟡 Ready for review",
    IN_PROGRESS: "🔵 In progress",
    NOT_STARTED: "⚪ Not started",
}

# TEAM.md header cells, by alias, so a lead who retitles a column has not
# broken anything.
TEAM_COLUMNS = {
    "name": {"name"},
    "institution": {"institution", "affiliation", "organisation",
                    "organization", "site"},
    "role": {"role", "role on this study"},
    "github": {"github", "github username", "username", "handle"},
}

CONTACT = re.compile(r"\*\*Primary contact\.\*\*\s*(.*)")
HANDLE = re.compile(r"\(@([A-Za-z0-9-]+)\)")
ACTIVITY = re.compile(r"^\*\*Last activity:\*\*\s*(.+?)\s*$", re.M)
STAMP = re.compile(r"<sub>Rewritten by Factory [^<]*</sub>")
GATE_PREFIX = re.compile(r"^Gate\s+\d+\s*[—–-]+\s*")
SEPARATOR = re.compile(r":?-+:?")
PARTNER_PREFIX = re.compile(r"^Data partner\s*[—–-]+\s*")


def gh(*args, check=True):
    # UTF-8 explicitly: issue titles carry an em dash, and a runner whose locale
    # is not UTF-8 would otherwise mangle it and then fail to strip it.
    r = subprocess.run(["gh", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def parse_ts(value):
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def days_since(value, now):
    ts = parse_ts(value)
    return None if ts is None else (now - ts).days


def read_file(repo, path, ref):
    """File contents at a ref, or None if it is not there."""
    if not repo:
        return None
    raw = gh("api", f"repos/{repo}/contents/{path}?ref={ref}",
             "--jq", ".content", check=False)
    if not raw:
        return None
    try:
        return base64.b64decode(raw).decode("utf-8", errors="replace")
    except Exception:
        return None


# --------------------------------------------------------------------------
# Study team, from TEAM.md
# --------------------------------------------------------------------------

def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _plain(cell):
    return cell.strip().strip("_*`").strip()


def parse_table(text, columns):
    """Rows of the first pipe table in `text`, keyed by canonical column name.

    Skips the separator row, rows with nothing in any recognised column, and
    the template's own example (`_e.g. Jane Okafor_`), which is not a person.
    """
    lines = [l for l in (text or "").splitlines() if l.strip().startswith("|")]
    if len(lines) < 2:
        return []
    header = [_plain(c).lower() for c in _cells(lines[0])]
    index = {}
    for canon, names in columns.items():
        for i, h in enumerate(header):
            if h in names:
                index[canon] = i
                break
    if not index:
        return []

    rows = []
    for line in lines[1:]:
        cells = _cells(line)
        if all(SEPARATOR.fullmatch(c) for c in cells if c):
            continue
        values = {canon: (_plain(cells[index[canon]])
                         if canon in index and index[canon] < len(cells)
                         else "")
                  for canon in columns}
        if not any(values.values()):
            continue
        if any(v.lower().startswith("e.g.") for v in values.values()):
            continue
        rows.append(values)
    return rows


def team_rows(repo, branch):
    return parse_table(read_file(repo, "TEAM.md", branch), TEAM_COLUMNS)


# --------------------------------------------------------------------------
# Data partners, from the partner issues
# --------------------------------------------------------------------------

def parse_contact(body):
    """(name, role, github) from the `Primary contact` line sync_partners writes."""
    m = CONTACT.search(body or "")
    if not m:
        return "", "", ""
    text = m.group(1).strip()
    github = ""
    h = HANDLE.search(text)
    if h:
        github = h.group(1)
        text = (text[:h.start()] + text[h.end():]).strip()
    name, _, role = text.partition(", ")
    name = name.strip()
    if name in ("", "—", "-"):
        name = ""
    return name, role.strip(), github


def partner_rows(repo, now):
    """Every open partner issue: status, contact, and days since a sign of life.

    The days-quiet clock is the later of the last comment and the last body
    edit — the stall check's rule. A lead who keeps the body current and
    comments nothing is not a partner gone quiet.
    """
    raw = gh("issue", "list", "--repo", repo, "--label", "partner",
             "--state", "open", "--limit", "200",
             "--json", "number,title,url,body,labels,updatedAt,comments",
             check=False)
    if not raw:
        return []

    out = []
    for issue in json.loads(raw):
        comments = issue.get("comments") or []
        last_comment = max((c.get("createdAt") for c in comments
                            if c.get("createdAt")), default=None)
        marks = [m for m in (last_comment, issue.get("updatedAt")) if m]
        last = max(marks) if marks else None
        label = next((l["name"] for l in issue.get("labels", [])
                      if l["name"].startswith("status:")), None)
        name, role, github = parse_contact(issue.get("body"))
        out.append({
            "number": issue["number"],
            "title": issue["title"],
            "institution": PARTNER_PREFIX.sub("", issue["title"]),
            "url": issue.get("url")
                   or f"https://github.com/{repo}/issues/{issue['number']}",
            "label": label,
            "status": (label or "status:unknown").replace("status:", "")
                                                  .replace("-", " "),
            "status_text": OPTION_FOR_LABEL.get(label, "Unknown"),
            "contact_name": name,
            "contact_role": role,
            "contact_github": github,
            "days_quiet": days_since(last, now),
            "last_activity": last,
        })
    return sorted(out, key=lambda p: p["institution"].lower())


# --------------------------------------------------------------------------
# Study history, from the state file and the gate issues
# --------------------------------------------------------------------------

def gate_name(title):
    """'Gate 3 — Cohort definitions committed' -> 'Cohort definitions committed'."""
    return GATE_PREFIX.sub("", title)


def advanced_at(state, number):
    """When the study advanced to this gate, from the state's history."""
    stamps = [h["at"] for h in state.get("history", [])
              if h.get("to_gate") == number and h.get("at")]
    return stamps[-1] if stamps else None


def _day(stamp):
    return (stamp or "")[:10] or "—"


def gate_issue_states(repo, gate_issues):
    """{issue number: closedAt} for every closed gate issue in the study repo.

    None when the list could not be read — which is not the same as nothing
    being closed, and callers must not treat it so. The closure sync writes
    these into the state file; this is the live view between syncs.
    """
    wanted = {int(n) for n in gate_issues.values() if n}
    if not wanted:
        return {}
    raw = gh("issue", "list", "--repo", repo, "--label", "gate",
             "--state", "closed", "--limit", "50",
             "--json", "number,closedAt", check=False)
    if not raw:
        return None
    try:
        return {i["number"]: i.get("closedAt")
                for i in json.loads(raw) if i["number"] in wanted}
    except (ValueError, KeyError, TypeError):
        return None


def history_rows(state, gates_config, closed=None):
    """One row per gate: its status now, and when it reached each status.

    Three dates, kept apart so the record can be studied later: when work was
    first seen, when Factory saw enough to propose review, and when a human
    closed the issue. Ready for review is the recorded `ready_at` where the
    closure sync has written it, else the advance in the history — never
    `entered_at`, which is first sight. A gate that went straight to Ready
    for review was never In progress, and says so rather than repeating the
    same date twice.

    `closed` is the live view of the gate issues. When it is known it wins
    over the state file, so a closure or a reopen shows before the next
    sync; when it is None the state file is the best information there is.
    """
    rows = []
    for gate in sorted(gates_config["gates"], key=lambda g: g["gate"]):
        n = gate["gate"]
        rec = state.get("gates", {}).get(str(n), {})
        issue = state.get("gate_issues", {}).get(str(n)) or rec.get("issue")
        status = rec.get("status", NOT_STARTED)
        entered = rec.get("entered_at")
        ready = rec.get("ready_at") or (
            (advanced_at(state, n) or entered) if status in (READY, DONE) else None)
        in_progress = entered if entered and (not ready or entered < ready) else None
        if closed is None:
            closed_at = rec.get("closed_at") if status == DONE else None
        elif issue in closed:
            status, closed_at = DONE, closed[issue]
        elif status == DONE:
            status, closed_at = READY, None  # reopened since the last sync
        else:
            closed_at = None
        rows.append({
            "gate": n,
            "name": gate_name(gate["title"]),
            "status": status,
            "status_text": STATUS_TEXT.get(status, status),
            "in_progress": _day(in_progress),
            "ready": _day(ready),
            "closed": _day(closed_at),
            "issue": issue,
        })
    return rows


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _cell(text):
    return str(text if text not in (None, "") else "—").replace("|", "\\|")


def _days(n):
    return f"{n} day{'' if n == 1 else 's'}"


def alarm(state, threshold, now):
    entered = state.get("gate_entered_at")
    if not entered:
        return "⚪ not started"
    days = days_since(entered, now)
    if days >= threshold:
        return f"🔴 **stalled — {_days(days)} in this gate**"
    return f"🟢 {_days(days)} in this gate"


def stalled_partners(partners, threshold):
    return [p for p in partners
            if p["days_quiet"] is not None and p["days_quiet"] >= threshold]


def partner_line(partners, threshold):
    if not partners:
        return "no partners yet"
    n, stalled = len(partners), len(stalled_partners(partners, threshold))
    return (f"{n} partner{'' if n == 1 else 's'}, "
            + ("none stalled" if not stalled else f"{stalled} stalled"))


def activity_line(activity, previous):
    """This push if there is one; otherwise whatever the issue last said."""
    if activity and activity.get("commit_sha"):
        short = activity["commit_sha"][:7]
        who = f" by @{activity['author']}" if activity.get("author") else ""
        return (f"[`{short}`]({activity.get('commit_url', '')}){who} "
                f"on {activity.get('pushed_at', '')}")
    m = ACTIVITY.search(previous or "")
    return m.group(1) if m else None


def legacy_dates(body):
    """Start and target dates from whatever is already on the issue.

    Studies provisioned before the state file carried these have them only in
    the issue body: the v1 two-column table, the three-column table this
    renderer wrote at first, or the Progress line it writes now. Matching all
    three means the dates survive indefinitely without anybody backfilling
    state files.
    """
    def find(line_label, table_label):
        for pattern in (r"\*\*" + line_label + r":\*\*\s*(\d{4}-\d{2}-\d{2})",
                        r"\|\s*\*\*" + table_label + r"\*\*\s*\|(?:\s*\|)?\s*"
                        r"(\d{4}-\d{2}-\d{2})"):
            m = re.search(pattern, body or "", re.I)
            if m:
                return m.group(1)
        return None
    return find("Started", "Study start"), find("Target completion", "Target completion")


def render(state, gates_config, team, partners, now, threshold,
           activity=None, previous=None, dates=(None, None), closed=None):
    """The managed block, markers included."""
    study = state["study_repo"]
    branch = state.get("default_branch", "main")
    current = state.get("current_gate", -1)
    title = next((g["title"] for g in gates_config["gates"]
                  if g["gate"] == current), None)
    start, target = dates
    last = activity_line(activity, previous)

    lines = [
        START,
        "### Progress",
        f"**Gate:** {title or 'Not started'}",
        f"**Time in gate:** {alarm(state, threshold, now)}",
        f"**Started:** {start or '—'} · **Target completion:** {target or '—'}",
    ]
    if last:
        lines.append(f"**Last activity:** {last}")
    lines += [
        f"**Partners:** {partner_line(partners, threshold)}",
        "",
        "### Study history",
        "| Gate | Status | In progress | Ready for review | Closed |",
        "|---|---|---|---|---|",
    ]
    for r in history_rows(state, gates_config, closed):
        name = (f"[{r['name']}](https://github.com/{study}/issues/{r['issue']})"
                if r["issue"] else r["name"])
        lines.append(f"| {name} | {r['status_text']} | {r['in_progress']} "
                     f"| {r['ready']} | {r['closed']} |")

    lines += ["", "### Study team"]
    if team:
        lines += ["| Name | Institution | Role | GitHub |", "|---|---|---|---|"]
        for m in team:
            handle = (m.get("github") or "").lstrip("@")
            lines.append(f"| {_cell(m.get('name'))} | {_cell(m.get('institution'))} "
                         f"| {_cell(m.get('role'))} "
                         f"| {'@' + handle if handle else '—'} |")
    else:
        lines.append("Nobody has added themselves to "
                     f"[`TEAM.md`](https://github.com/{study}/blob/{branch}/TEAM.md) "
                     "yet.")

    lines += ["", "### Data partners"]
    if partners:
        lines += ["| Institution | Status | Contact | GitHub | Quiet for |",
                  "|---|---|---|---|---|"]
        for p in partners:
            contact = p["contact_name"] or "—"
            if p["contact_role"]:
                contact += f", {p['contact_role']}"
            handle = f"@{p['contact_github']}" if p["contact_github"] else "—"
            if p["days_quiet"] is None:
                quiet = "—"
            elif p["days_quiet"] >= threshold:
                quiet = f"🔴 {_days(p['days_quiet'])}"
            else:
                quiet = _days(p["days_quiet"])
            lines.append(f"| [{_cell(p['institution'])}]({p['url']}) "
                         f"| {p['status_text']} | {_cell(contact)} | {handle} "
                         f"| {quiet} |")
    else:
        lines.append("No partner issues yet. Rows committed to "
                     f"[`partners.csv`](https://github.com/{study}/blob/{branch}/partners.csv) "
                     "become partner issues.")

    lines += [
        "",
        f"<sub>Rewritten by Factory {now.strftime('%Y-%m-%d %H:%M UTC')} from the "
        "study's gate state, `TEAM.md`, and its partner issues · stall threshold "
        f"{threshold} days · edits inside this block are overwritten.</sub>",
        END,
    ]
    return "\n".join(lines)


def splice(body, block):
    """`body` with the managed block replaced, or the issue migrated to it."""
    body = body or ""
    if START in body and END in body:
        return (body[:body.index(START)] + block
                + body[body.index(END) + len(END):])

    # First refresh of an issue from before the markers: keep the header, drop
    # the v1 table and the blocks the earlier scripts appended. The v1 Status
    # line went with the table — it was never updated and said Active forever.
    cut = min((body.index(m) for m in LEGACY_CUTS if m in body), default=len(body))
    head = "\n".join(l for l in body[:cut].splitlines()
                     if not l.startswith("**Status:**"))
    return head.rstrip() + "\n\n" + block + "\n"


def comparable(body):
    """The body without the stamp, so a refresh that changed nothing else is a no-op."""
    return STAMP.sub("", body or "").strip()


# --------------------------------------------------------------------------
# The refresh
# --------------------------------------------------------------------------

def refresh(state, gates_config, now=None, activity=None, threshold=None,
            dry_run=False):
    """Bring the study's Factory issue up to date. True if it was edited.

    Best-effort throughout: a Factory issue that cannot be read or written must
    never fail the job that called this. The state file is the record; the
    issue is the view of it.
    """
    repo, num = state.get("factory_repo"), state.get("factory_issue")
    if not repo or not num:
        return False
    now = now or dt.datetime.now(dt.timezone.utc)
    if threshold is None:
        threshold = state.get("stall_threshold_days",
                              gates_config.get("stall_threshold_days", 21))

    raw = gh("api", f"repos/{repo}/issues/{num}", check=False)
    try:
        body = json.loads(raw).get("body") or ""
    except (ValueError, AttributeError):
        print(f"::warning::factory issue: could not read {repo}#{num}")
        return False

    study = state["study_repo"]
    branch = state.get("default_branch", "main")
    old_start, old_target = legacy_dates(body)
    dates = (state.get("start_date") or old_start,
             state.get("target_date") or old_target)

    block = render(
        state, gates_config,
        team=team_rows(study, branch),
        partners=partner_rows(study, now),
        now=now, threshold=threshold, activity=activity, previous=body,
        dates=dates,
        closed=gate_issue_states(study, state.get("gate_issues", {})),
    )
    new_body = splice(body, block)

    if comparable(new_body) == comparable(body):
        print(f"  factory issue: {repo}#{num} unchanged")
        return False
    if dry_run:
        print(new_body)
        return True

    r = subprocess.run(["gh", "issue", "edit", str(num), "--repo", repo,
                        "--body", new_body], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        print(f"::warning::factory issue: could not update {repo}#{num}: "
              f"{r.stderr.strip()}")
        return False
    print(f"  factory issue: updated {repo}#{num}")
    return True


# --------------------------------------------------------------------------
# Self-test: the parsing and migration rules that must not regress
# --------------------------------------------------------------------------

def _self_test():
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    template = ("# Study team\n\n| Name | Institution | Role | GitHub username |\n"
                "|---|---|---|---|\n"
                "| _e.g. Jane Okafor_ | _e.g. Johns Hopkins_ | _e.g. Study lead_ "
                "| _e.g. @jokafor_ |\n")
    check("the template's example row is not a person",
          parse_table(template, TEAM_COLUMNS) == [])

    filled = template + "| Parent1 | Home | Study Lead | @parent1 |\n| Ana | KI | Analyst | |\n"
    rows = parse_table(filled, TEAM_COLUMNS)
    check("real rows are read, example still skipped",
          [r["name"] for r in rows] == ["Parent1", "Ana"])
    check("the GitHub column is read", rows[0]["github"] == "@parent1")
    check("a blank GitHub cell is empty, not missing", rows[1]["github"] == "")

    old = "| Name | Institution | Role |\n|---|---|---|\n| Parent1 | Home | Study Lead |\n"
    rows = parse_table(old, TEAM_COLUMNS)
    check("a TEAM.md without a GitHub column still parses",
          rows and rows[0]["name"] == "Parent1" and rows[0]["github"] == "")
    check("a renamed header is matched by alias",
          parse_table("| Name | Affiliation | Role |\n|---|---|---|\n| A | B | C |\n",
                      TEAM_COLUMNS)[0]["institution"] == "B")
    check("a table with no recognised column is nothing",
          parse_table("| x | y |\n|---|---|\n| 1 | 2 |\n", TEAM_COLUMNS) == [])

    check("a full contact line is split into name, role, handle",
          parse_contact("**Primary contact.** Jane Okafor, PI (@jokafor)\n**Status.** x")
          == ("Jane Okafor", "PI", "jokafor"))
    check("a contact with no handle", parse_contact("**Primary contact.** person, role")
          == ("person", "role", ""))
    check("an empty contact is empty", parse_contact("**Primary contact.** —")
          == ("", "", ""))
    check("a body without the line is empty", parse_contact("hello") == ("", "", ""))

    check("the gate number is dropped from the name",
          gate_name("Gate 3 — Cohort definitions committed") == "Cohort definitions committed")
    check("a title without a number is left alone", gate_name("Complete") == "Complete")
    check("the partner prefix is stripped from a title",
          PARTNER_PREFIX.sub("", "Data partner — Site A") == "Site A")

    state = {
        "study_repo": "org/study-x", "factory_repo": "org/Factory",
        "factory_issue": 7, "current_gate": 1,
        "gate_entered_at": "2026-08-01T00:00:00+00:00",
        "gates": {"0": {"status": READY, "entered_at": "2026-07-01T00:00:00+00:00", "issue": 1},
                  "1": {"status": IN_PROGRESS, "entered_at": "2026-07-20T00:00:00+00:00", "issue": 2},
                  "2": {"status": NOT_STARTED, "entered_at": None, "issue": 3}},
        "gate_issues": {"0": 1, "1": 2, "2": 3},
        "history": [{"at": "2026-07-15T00:00:00+00:00", "to_gate": 0}],
    }
    gates = {"gates": [{"gate": 0, "title": "Gate 0 — Get oriented in GitHub"},
                       {"gate": 1, "title": "Gate 1 — Research question developed"},
                       {"gate": 2, "title": "Gate 2 — Protocol drafted"}]}
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)

    rows = history_rows(state, gates)
    check("Ready for review is dated by the advance, not first sight",
          rows[0]["ready"] == "2026-07-15")
    check("  ...and In progress by first sight, when that came earlier",
          rows[0]["in_progress"] == "2026-07-01" and rows[0]["closed"] == "—")
    check("an In progress gate has only that date",
          rows[1]["in_progress"] == "2026-07-20" and rows[1]["ready"] == "—")
    check("not started has no dates",
          (rows[2]["in_progress"], rows[2]["ready"], rows[2]["closed"]) == ("—",) * 3)
    rows = history_rows(state, gates, closed={1: "2026-08-02T10:00:00Z"})
    check("a closed gate issue shows closed on its close date, keeping the rest",
          rows[0]["status"] == DONE and rows[0]["closed"] == "2026-08-02"
          and rows[0]["ready"] == "2026-07-15")
    direct = {"gates": {"0": {"status": READY, "entered_at": "2026-07-15T00:00:00+00:00"}},
              "gate_issues": {},
              "history": [{"at": "2026-07-15T00:00:00+00:00", "to_gate": 0}]}
    row = history_rows(direct, gates)[0]
    check("a gate that went straight to Ready was never In progress",
          row["in_progress"] == "—" and row["ready"] == "2026-07-15")
    recorded = {"gates": {"0": {"status": DONE, "entered_at": "2026-07-01T00:00:00+00:00",
                                "ready_at": "2026-07-12T00:00:00+00:00",
                                "closed_at": "2026-07-30T00:00:00+00:00", "issue": 1}},
                "gate_issues": {"0": 1}, "history": []}
    row = history_rows(recorded, gates)[0]
    check("recorded ready and closed dates are used when the live view is unknown",
          row["ready"] == "2026-07-12" and row["closed"] == "2026-07-30"
          and row["status"] == DONE)
    row = history_rows(recorded, gates, closed={})[0]
    check("a live view with the issue open shows it reopened, awaiting review",
          row["status"] == READY and row["closed"] == "—")

    v1 = ("## Study X\n\n**Repository:** https://github.com/org/study-x\n"
          "**Lead:** Sean (@seanr87)\n**Status:** 🟢 Active\n\n### Study History\n"
          "| Objective | Date Complete |\n|-----------|---------------|\n"
          "| **Study Start** | 2026-07-01 |\n| Analysis Package Prototype | — |\n"
          "| **Target Completion** | 2027-01-01 |\n\n### Activity\nLast updated: x\n\n"
          "---\n*This issue tracks the study progress. Updates are automated.*\n\n"
          "<!--factory:status-->\n**Current gate:** Gate 1 — x\n"
          "**Last activity:** [`abc1234`](https://example/c) on 2026-08-30\n"
          "<!--/factory:status-->")
    check("v1 dates are read", legacy_dates(v1) == ("2026-07-01", "2027-01-01"))

    partners = [{"number": 9, "title": "Data partner — Site A", "institution": "Site A",
                 "url": "https://github.com/org/study-x/issues/9", "label": "status:committed",
                 "status": "committed", "status_text": "Committed",
                 "contact_name": "Ann", "contact_role": "PI", "contact_github": "ann",
                 "days_quiet": 30, "last_activity": None}]
    team = [{"name": "Parent1", "institution": "Home", "role": "Study Lead",
             "github": "@parent1"}]
    block = render(state, gates, team, partners, now, 21, previous=v1,
                   dates=legacy_dates(v1))
    check("history names gates without their number",
          "| [Get oriented in GitHub](" in block and "| Gate 0" not in block)
    check("the current gate keeps its full title in Progress",
          "**Gate:** Gate 1 — Research question developed" in block)
    check("the last activity is carried over when there is no push",
          "**Last activity:** [`abc1234`](https://example/c) on 2026-08-30" in block)
    check("a push replaces it",
          "**Last activity:** [`def5678`](u) by @x on t" in
          render(state, gates, team, partners, now, 21, previous=v1,
                 activity={"commit_sha": "def5678abc", "commit_url": "u",
                           "author": "x", "pushed_at": "t"}))
    check("the dates survive migration",
          "**Started:** 2026-07-01 · **Target completion:** 2027-01-01" in block)
    check("and are read back from the new line",
          legacy_dates(block) == ("2026-07-01", "2027-01-01"))
    check("and from the first three-column table",
          legacy_dates("| **Study start** | | 2026-07-01 |\n"
                       "| **Target completion** | | 2027-01-01 |")
          == ("2026-07-01", "2027-01-01"))
    check("the history table has the three date columns",
          "| Gate | Status | In progress | Ready for review | Closed |" in block
          and "| [Get oriented in GitHub](https://github.com/org/study-x/issues/1) "
              "| 🟡 Ready for review | 2026-07-01 | 2026-07-15 | — |" in block)
    check("the team shows role and handle", "| Parent1 | Home | Study Lead | @parent1 |" in block)
    check("a partner shows status, contact, handle, and quiet days",
          "| [Site A](https://github.com/org/study-x/issues/9) | Committed | Ann, PI | @ann | 🔴 30 days |"
          in block)
    check("a quiet partner is counted", "**Partners:** 1 partner, 1 stalled" in block)
    check("a stalled study is flagged", "🔴 **stalled — 31 days in this gate**" in block)
    empty = render(state, gates, [], [], now, 21)
    check("no team says so", "Nobody has added themselves" in empty)
    check("no partners says so", "No partner issues yet" in empty)

    migrated = splice(v1, block)
    check("migration keeps the header", migrated.startswith("## Study X\n\n**Repository:**"))
    check("  ...drops the v1 status line", "**Status:** 🟢 Active" not in migrated)
    check("  ...drops the v1 table", "Analysis Package Prototype" not in migrated)
    check("  ...drops the old blocks", "<!--factory:status-->" not in migrated)
    check("  ...and ends with the block", migrated.rstrip().endswith(END))
    again = splice(migrated + "\nA note somebody added.\n", block.replace("Ann", "Bob"))
    check("a marked body is replaced between the markers only",
          "Bob" in again and "Ann" not in again
          and again.rstrip().endswith("A note somebody added."))
    check("a body with no header at all still gets the block",
          splice("", block).strip() == block.strip())
    check("the stamp does not count as a change",
          comparable(block) == comparable(
              render(state, gates, team, partners, now + dt.timedelta(hours=1), 21,
                     previous=v1, dates=legacy_dates(v1))
              .replace("32 days", "31 days")))

    failed = [n for n, ok in checks if not ok]
    if failed:
        raise AssertionError("factory_issue self-test failed:\n  " + "\n  ".join(failed))
    return len(checks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", default="", help="study repo, owner/name")
    ap.add_argument("--all", action="store_true", help="every tracked study")
    ap.add_argument("--state-dir", default=".github/data/state")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the body that would be written")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        print(f"factory_issue self-test passed ({_self_test()} cases)")
        return 0
    if not args.study and not args.all:
        ap.error("--study or --all is required")

    gates_config = json.loads(GATES.read_text(encoding="utf-8"))
    state_dir = ROOT / args.state_dir
    files = sorted(state_dir.glob("*.json")) if state_dir.exists() else []
    if args.study:
        slug = args.study.split("/")[-1]
        files = [state_dir / f"{slug}.json"]
        if not files[0].exists():
            sys.exit(f"No gate state for {args.study}: expected "
                     f"{files[0].relative_to(ROOT).as_posix()}")

    now = dt.datetime.now(dt.timezone.utc)
    for path in files:
        state = json.loads(path.read_text(encoding="utf-8"))
        print(f"{state['study_repo']}")
        refresh(state, gates_config, now=now, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
