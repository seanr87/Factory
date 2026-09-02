#!/usr/bin/env python3
"""Export everything Factory knows about its studies, as CSV and JSON.

The state files are the durable record: which gate each study is in, when each
gate reached In progress, Ready for review, and Closed, and every advance with
the commit that caused it. This writes that out as flat tables that open in a
spreadsheet or load into R without anyone parsing JSON by hand, and — unless
--offline — adds what lives only in GitHub: the study team from TEAM.md, each
partner's current status and contact, and every partner status change, read
from the label events on the partner issues.

Files written to --out:

  studies.csv                  one row per study
  gates.csv                    one row per study x gate, with the three dates
                               and the durations between them
  history.csv                  every advance: study, from, to, when, commit
  commits.csv                  every push logged against a gate: when, who,
                               message, and the gate's files it changed
  team.csv                     one row per person per study          (online)
  partners.csv                 one row per data partner               (online)
  partner_status_history.csv   every partner status change            (online)
  portfolio.json               all of the above in one document

Usage:
    export_portfolio.py --out export/             # everything
    export_portfolio.py --out export/ --offline   # state files only, no API
    export_portfolio.py --self-test
"""

import argparse
import csv
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from factory_issue import (advanced_at, gate_name, gh, legacy_dates,  # noqa: E402
                           parse_ts, partner_rows, team_rows)

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
GATES = ROOT / ".github" / "data" / "gates.json"

READY, DONE = "ready_for_review", "done"

LEAD = re.compile(r"^\*\*Lead:\*\*\s*(.+?)\s*(?:\(@([A-Za-z0-9-]+)\))?\s*$", re.M)

STUDY_FIELDS = ["study_repo", "factory_repo", "factory_issue", "lead_name",
                "lead_github", "start_date", "target_date", "current_gate",
                "current_gate_name", "gate_entered_at", "stall_threshold_days",
                "gates_closed", "exported_at"]
GATE_FIELDS = ["study_repo", "gate", "gate_name", "status", "in_progress_at",
               "ready_at", "closed_at", "reopened_at", "days_in_progress",
               "days_in_review", "issue", "evidenced_by"]
HISTORY_FIELDS = ["study_repo", "at", "from_gate", "to_gate", "commit", "evidence"]
COMMIT_FIELDS = ["study_repo", "gate", "gate_name", "at", "commit", "author",
                 "message", "paths", "removed", "url"]
TEAM_FIELDS = ["study_repo", "name", "institution", "role", "github"]
PARTNER_FIELDS = ["study_repo", "institution", "status", "contact_name",
                  "contact_role", "contact_github", "issue", "url",
                  "last_activity", "days_quiet"]
PARTNER_HISTORY_FIELDS = ["study_repo", "institution", "issue", "status", "at"]


def _days(a, b):
    """Whole days from a to b, or empty if either is missing."""
    ta, tb = parse_ts(a), parse_ts(b)
    if ta is None or tb is None:
        return ""
    return (tb - ta).days


# --------------------------------------------------------------------------
# From the state files (offline)
# --------------------------------------------------------------------------

def gate_rows(state, gates_config):
    """One row per gate, the three dates kept apart.

    Ready for review is the recorded `ready_at` where the closure sync has
    written it, and otherwise the advance in the history — never `entered_at`,
    which is first sight. A gate that went straight to Ready was never In
    progress and has no date there.
    """
    rows = []
    for gate in sorted(gates_config["gates"], key=lambda g: g["gate"]):
        n = gate["gate"]
        rec = state.get("gates", {}).get(str(n), {})
        status = rec.get("status", "not_started")
        entered = rec.get("entered_at")
        ready = rec.get("ready_at") or (
            (advanced_at(state, n) or entered) if status in (READY, DONE) else None)
        in_progress = entered if entered and (not ready or entered < ready) else None
        closed = rec.get("closed_at") if status == DONE else None
        rows.append({
            "study_repo": state["study_repo"],
            "gate": n,
            "gate_name": gate_name(gate["title"]),
            "status": status,
            "in_progress_at": in_progress or "",
            "ready_at": ready or "",
            "closed_at": closed or "",
            "reopened_at": rec.get("reopened_at") or "",
            "days_in_progress": _days(in_progress, ready),
            "days_in_review": _days(ready, closed),
            "issue": rec.get("issue") or state.get("gate_issues", {}).get(str(n)) or "",
            "evidenced_by": "; ".join(rec.get("evidenced_by") or []),
        })
    return rows


def history_rows(state):
    return [{
        "study_repo": state["study_repo"],
        "at": h.get("at") or "",
        "from_gate": h.get("from_gate", ""),
        "to_gate": h.get("to_gate", ""),
        "commit": h.get("commit") or "",
        "evidence": "; ".join(h.get("evidence") or []),
    } for h in state.get("history", [])]


def commit_rows(state, gates_config):
    """One row per push per gate it touched, oldest first.

    The same push appears once for each gate whose files it changed, so the
    table answers "what was done on gate 3, and when" without a join.
    """
    rows = []
    for gate in sorted(gates_config["gates"], key=lambda g: g["gate"]):
        n = gate["gate"]
        commits = state.get("gates", {}).get(str(n), {}).get("commits") or []
        for c in sorted(commits, key=lambda c: c.get("at") or ""):
            rows.append({
                "study_repo": state["study_repo"],
                "gate": n,
                "gate_name": gate_name(gate["title"]),
                "at": c.get("at") or "",
                "commit": c.get("sha") or "",
                "author": c.get("author") or "",
                "message": c.get("message") or "",
                "paths": "; ".join(c.get("paths") or []),
                "removed": "; ".join(c.get("removed") or []),
                "url": c.get("url") or "",
            })
    return rows


def study_row(state, gates_config, now, header=None):
    """One row per study. `header` is what the Factory issue's header says —
    lead, start, target — for studies whose state file predates those fields."""
    header = header or {}
    current = state.get("current_gate", -1)
    name = next((gate_name(g["title"]) for g in gates_config["gates"]
                 if g["gate"] == current), "")
    return {
        "study_repo": state["study_repo"],
        "factory_repo": state.get("factory_repo") or "",
        "factory_issue": state.get("factory_issue") or "",
        "lead_name": header.get("lead_name", ""),
        "lead_github": header.get("lead_github", ""),
        "start_date": state.get("start_date") or header.get("start_date") or "",
        "target_date": state.get("target_date") or header.get("target_date") or "",
        "current_gate": current,
        "current_gate_name": name,
        "gate_entered_at": state.get("gate_entered_at") or "",
        "stall_threshold_days": state.get("stall_threshold_days", ""),
        "gates_closed": sum(1 for r in state.get("gates", {}).values()
                            if r.get("status") == DONE),
        "exported_at": now.isoformat(),
    }


# --------------------------------------------------------------------------
# From GitHub (online)
# --------------------------------------------------------------------------

def header_of(body):
    """Lead, start, and target from a Factory issue body.

    Provisioning writes the lead into the header and, for studies from before
    the state file carried them, the dates live only on the issue.
    """
    m = LEAD.search(body or "")
    start, target = legacy_dates(body)
    return {
        "lead_name": m.group(1) if m else "",
        "lead_github": (m.group(2) or "") if m else "",
        "start_date": start or "",
        "target_date": target or "",
    }


def factory_header(factory_repo, number):
    if not factory_repo or not number:
        return {}
    raw = gh("api", f"repos/{factory_repo}/issues/{number}", "--jq", ".body // \"\"",
             check=False)
    return header_of(raw)


def partner_history(repo, partner):
    """Every status label ever applied to a partner issue, oldest first.

    GitHub keeps the `labeled` events, so the whole timeline is recoverable
    without Factory having stored anything — including the label the issue
    was created with.
    """
    raw = gh("api", f"repos/{repo}/issues/{partner['number']}/events", "--paginate",
             "--jq", '.[] | select(.event == "labeled") '
                     '| select(.label.name | startswith("status:")) '
                     '| "\\(.created_at)\\t\\(.label.name)"',
             check=False)
    rows = []
    for line in raw.splitlines():
        at, _, label = line.partition("\t")
        if not label:
            continue
        rows.append({
            "study_repo": repo,
            "institution": partner["institution"],
            "issue": partner["number"],
            "status": label.replace("status:", ""),
            "at": at,
        })
    return sorted(rows, key=lambda r: r["at"])


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------

def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def export(out, offline=False, state_dir=None, now=None, gates_config=None):
    now = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    gates_config = gates_config or json.loads(GATES.read_text(encoding="utf-8"))
    state_dir = state_dir or ROOT / ".github" / "data" / "state"
    files = sorted(state_dir.glob("*.json")) if state_dir.exists() else []

    tables = {"studies": [], "gates": [], "history": [], "commits": [],
              "team": [], "partners": [], "partner_status_history": []}

    for path in files:
        state = json.loads(path.read_text(encoding="utf-8"))
        repo = state["study_repo"]
        print(f"  {repo}")
        header = {} if offline else factory_header(state.get("factory_repo"),
                                                   state.get("factory_issue"))
        tables["studies"].append(study_row(state, gates_config, now, header))
        tables["gates"] += gate_rows(state, gates_config)
        tables["history"] += history_rows(state)
        tables["commits"] += commit_rows(state, gates_config)
        if offline:
            continue
        for member in team_rows(repo, state.get("default_branch", "main")):
            tables["team"].append({"study_repo": repo, **member})
        partners = partner_rows(repo, now)
        for p in partners:
            tables["partners"].append({
                "study_repo": repo,
                "institution": p["institution"],
                "status": p["status"],
                "contact_name": p["contact_name"],
                "contact_role": p["contact_role"],
                "contact_github": p["contact_github"],
                "issue": p["number"],
                "url": p["url"],
                "last_activity": p["last_activity"] or "",
                "days_quiet": "" if p["days_quiet"] is None else p["days_quiet"],
            })
            tables["partner_status_history"] += partner_history(repo, p)

    out.mkdir(parents=True, exist_ok=True)
    fields = {"studies": STUDY_FIELDS, "gates": GATE_FIELDS, "history": HISTORY_FIELDS,
              "commits": COMMIT_FIELDS, "team": TEAM_FIELDS, "partners": PARTNER_FIELDS,
              "partner_status_history": PARTNER_HISTORY_FIELDS}
    written = []
    for name, rows in tables.items():
        if offline and name in ("team", "partners", "partner_status_history"):
            continue
        write_csv(out / f"{name}.csv", fields[name], rows)
        written.append((f"{name}.csv", len(rows)))

    (out / "portfolio.json").write_text(
        json.dumps({"exported_at": now.isoformat(), "offline": offline, **tables},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written.append(("portfolio.json", len(tables["studies"])))
    return written


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

def _self_test():
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    gates = {"gates": [{"gate": 0, "title": "Gate 0 — Get oriented in GitHub"},
                       {"gate": 1, "title": "Gate 1 — Research question developed"},
                       {"gate": 2, "title": "Gate 2 — Protocol drafted"}]}
    state = {
        "study_repo": "org/study-x", "factory_repo": "org/Factory", "factory_issue": 7,
        "start_date": "2026-06-01", "target_date": "2027-01-01",
        "current_gate": 1, "gate_entered_at": "2026-07-15T00:00:00+00:00",
        "stall_threshold_days": 21,
        "gates": {
            "0": {"status": DONE, "entered_at": "2026-07-01T00:00:00+00:00",
                  "ready_at": "2026-07-10T00:00:00+00:00",
                  "closed_at": "2026-07-20T00:00:00+00:00", "issue": 1,
                  "evidenced_by": ["TEAM.md"]},
            "1": {"status": READY, "entered_at": "2026-07-15T00:00:00+00:00", "issue": 2,
                  "commits": [
                      {"sha": "def", "url": "https://x/c/def", "at": "2026-07-15T00:00:00+00:00",
                       "author": "jokafor", "message": "Draft the question",
                       "paths": ["Documents/research-question.md"], "removed": []},
                      {"sha": "abc", "url": "https://x/c/abc", "at": "2026-07-12T00:00:00+00:00",
                       "author": "", "message": "Start", "paths": ["Documents/research-question.md"],
                       "removed": []}]},
            "2": {"status": "not_started", "entered_at": None, "issue": 3},
        },
        "gate_issues": {"0": 1, "1": 2, "2": 3},
        "history": [{"at": "2026-07-10T00:00:00+00:00", "from_gate": -1, "to_gate": 0,
                     "commit": "abc", "evidence": ["TEAM.md"]},
                    {"at": "2026-07-15T00:00:00+00:00", "from_gate": 0, "to_gate": 1,
                     "commit": "def", "evidence": ["Documents/research-question.md"]}],
    }
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)

    rows = gate_rows(state, gates)
    g0, g1, g2 = rows
    check("a closed gate carries all three dates",
          (g0["in_progress_at"][:10], g0["ready_at"][:10], g0["closed_at"][:10])
          == ("2026-07-01", "2026-07-10", "2026-07-20"))
    check("  ...and the durations between them",
          g0["days_in_progress"] == 9 and g0["days_in_review"] == 10)
    check("the gate is named without its number", g0["gate_name"] == "Get oriented in GitHub")
    check("a gate that went straight to Ready has no In progress date",
          g1["in_progress_at"] == "" and g1["ready_at"][:10] == "2026-07-15")
    check("  ...ready is taken from history when not recorded",
          g1["ready_at"] == "2026-07-15T00:00:00+00:00")
    check("  ...and no durations that would need a missing date",
          g1["days_in_progress"] == "" and g1["days_in_review"] == "")
    check("a gate not started is all blanks",
          (g2["in_progress_at"], g2["ready_at"], g2["closed_at"]) == ("", "", ""))
    check("evidence is flattened for CSV", g0["evidenced_by"] == "TEAM.md")

    s = study_row(state, gates, now, {"lead_name": "Jane Okafor", "lead_github": "jokafor",
                                      "start_date": "2000-01-01", "target_date": ""})
    check("the study row names its current gate",
          s["current_gate"] == 1 and s["current_gate_name"] == "Research question developed")
    check("  ...counts closed gates", s["gates_closed"] == 1)
    check("  ...and carries the lead", s["lead_name"] == "Jane Okafor" and s["lead_github"] == "jokafor")
    check("  ...preferring the state file's dates over the issue's",
          s["start_date"] == "2026-06-01" and s["target_date"] == "2027-01-01")
    old = dict(state, start_date=None, target_date=None)
    check("  ...but taking the issue's when the state file has none",
          study_row(old, gates, now, {"start_date": "2000-01-01"})["start_date"] == "2000-01-01")

    h = history_rows(state)
    check("history rows are one per advance", len(h) == 2 and h[1]["commit"] == "def")

    c = commit_rows(state, gates)
    check("commit rows are one per push per gate, oldest first",
          [r["commit"] for r in c] == ["abc", "def"] and c[0]["gate"] == 1)
    check("  ...naming the gate and flattening the paths",
          c[1]["gate_name"] == "Research question developed"
          and c[1]["paths"] == "Documents/research-question.md"
          and c[1]["author"] == "jokafor" and c[1]["message"] == "Draft the question")
    check("a study with nothing logged has no commit rows",
          commit_rows({"study_repo": "s", "gates": {}}, gates) == [])

    hdr = header_of("## X\n\n**Repository:** u\n**Lead:** Sean O'Reilly (@seanr87)\n\n"
                    "### Study History\n| Objective | Date Complete |\n|---|---|\n"
                    "| **Study Start** | 2026-07-01 |\n| **Target Completion** | 2027-01-01 |\n")
    check("the lead and the v1 dates are read from the Factory issue header",
          hdr == {"lead_name": "Sean O'Reilly", "lead_github": "seanr87",
                  "start_date": "2026-07-01", "target_date": "2027-01-01"})
    check("  ...even without a handle or dates",
          header_of("**Lead:** Someone\n") == {"lead_name": "Someone", "lead_github": "",
                                               "start_date": "", "target_date": ""})

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        (tmp / "state").mkdir()
        (tmp / "state" / "study-x.json").write_text(json.dumps(state), encoding="utf-8")
        written = export(tmp / "out", offline=True, state_dir=tmp / "state", now=now,
                         gates_config=gates)
        names = dict(written)
        check("offline export writes the state-derived tables and the JSON",
              set(names) == {"studies.csv", "gates.csv", "history.csv", "commits.csv",
                             "portfolio.json"})
        check("commits.csv carries the logged pushes", names["commits.csv"] == 2)
        text = (tmp / "out" / "gates.csv").read_text(encoding="utf-8")
        check("gates.csv has a header and one row per gate",
              text.startswith("study_repo,gate,gate_name,status,in_progress_at,")
              and text.count("org/study-x") == 3)
        doc = json.loads((tmp / "out" / "portfolio.json").read_text(encoding="utf-8"))
        check("the JSON carries every table", doc["offline"] is True
              and len(doc["gates"]) == 3 and doc["studies"][0]["study_repo"] == "org/study-x"
              and len(doc["commits"]) == 2)

    failed = [n for n, ok in checks if not ok]
    if failed:
        raise AssertionError("export_portfolio self-test failed:\n  " + "\n  ".join(failed))
    return len(checks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="export", help="directory to write into")
    ap.add_argument("--offline", action="store_true",
                    help="state files only; no GitHub calls")
    ap.add_argument("--state-dir", default=".github/data/state")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        print(f"export_portfolio self-test passed ({_self_test()} cases)")
        return 0

    written = export(pathlib.Path(args.out), offline=args.offline,
                     state_dir=ROOT / args.state_dir)
    print()
    for name, count in written:
        print(f"  {name:30} {count} row(s)")
    summary = subprocess.os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("| File | Rows |\n|---|---|\n")
            for name, count in written:
                fh.write(f"| `{name}` | {count} |\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
