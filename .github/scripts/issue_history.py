#!/usr/bin/env python3
"""Log every push that touched a gate's files at the top of its issue.

A gate issue used to say only what moved it: one comment when it reached
Ready for review, nothing about the ten commits before or the twenty after.
A reviewer opening it had to go to the repository's commit list and work out
which commits were about this gate. Now the issue carries that itself: a
table at the top, one row per push that changed a file the gate watches, with
when, which files, the commit message, and who — the things someone asks
first when they open the issue.

The rows come from the same rule the state machine uses to decide whether a
push is evidence: a path counts when it matches one of the gate's required or
supporting patterns and its blob differs from the template baseline. So a
file that is still the template's is not "work on this gate" here either, and
a branch-creation push that lists every file produces no rows.

The state file is the record; the table is a view of it. Each gate's record
gains a `commits` list, one entry per push, keyed by commit so a re-run of the
same dispatch does not add a second row. The table is rewritten from that
list between two markers at the top of the body, only when it differs, and
only once there is something to show — a gate nobody has touched keeps the
issue exactly as provisioning wrote it.

One row per push, not per commit: the study side reports the head commit and
the paths changed since the last push. A lead editing in the browser pushes
one commit at a time, which is who this is for.

Usage:
    issue_history.py --self-test
"""

import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from factory_issue import gh  # noqa: E402
from gate_machine import touched_gates  # noqa: E402

__all__ = ["record", "render", "splice", "refresh", "START", "END"]

START, END = "<!--factory:history-->", "<!--/factory:history-->"

# Rows shown on the issue. The state file keeps every push; an issue with a
# few hundred rows at the top stops being an issue.
SHOWN = 50

# Commit messages are shown as their first line, cut here. The full message is
# one click away on the commit itself.
SUBJECT = 72

DELETED = "deleted"


def _utc(stamp):
    """`stamp` as UTC ISO 8601 without microseconds, or as given if unparseable.

    The study side sends the head commit's timestamp with the author's own
    offset. Everything else Factory records is UTC, so this is too.
    """
    try:
        ts = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return stamp or ""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat()


def when(stamp):
    """'YYYY-MM-DD HH:MM' in UTC, or the raw stamp when it does not parse."""
    try:
        ts = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return str(stamp or "—")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")


def subject(message):
    """The first line of a commit message; nothing else belongs in a table."""
    lines = [l.strip() for l in (message or "").strip().splitlines() if l.strip()]
    return lines[0] if lines else ""


def clip(text, limit=SUBJECT):
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def _escape(text):
    """Text safe inside a table cell and a link label."""
    out = str(text)
    for ch in "\\|[]<":
        out = out.replace(ch, "\\" + ch)
    return out


def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------

def record(state, gates_config, baseline, payload, current_blobs, now=None):
    """Add this push to every gate whose files it changed.

    Returns the gate numbers whose record changed. A push already recorded
    against a gate, with the same details, changes nothing; one recorded with
    different details (a manual re-evaluation after a force-push, say) is
    replaced rather than duplicated.
    """
    sha = payload["commit_sha"]
    touched = touched_gates(gates_config, baseline, payload.get("paths", []),
                            current_blobs)
    changed = []
    for gate_no, paths in touched.items():
        key = str(gate_no)
        rec = state.setdefault("gates", {}).setdefault(key, {
            "status": "not_started",
            "entered_at": None,
            "issue": state.get("gate_issues", {}).get(key),
            "evidenced_by": [],
        })
        entry = {
            "sha": sha,
            "url": payload.get("commit_url")
                   or f"https://github.com/{state['study_repo']}/commit/{sha}",
            "at": _utc(payload.get("pushed_at")) or now or _now(),
            "author": payload.get("author") or "",
            "message": subject(payload.get("commit_message")),
            "paths": paths,
            "removed": [p for p in paths if p not in current_blobs],
        }
        commits = rec.setdefault("commits", [])
        existing = next((c for c in commits if c.get("sha") == sha), None)
        if existing == entry:
            continue
        if existing is not None:
            commits[commits.index(existing)] = entry
        else:
            commits.append(entry)
        changed.append(gate_no)
    return changed


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def files_cell(commit, study, branch):
    """Each file by name, linked to where it lives now.

    The name alone is what a person reads; the full path is the link's title,
    for hovering. Two files with the same name in one push are shown by their
    full paths so they can be told apart. A file the push deleted has nothing
    to link to on the branch, so it is struck through and links to the commit.
    """
    paths = commit.get("paths") or []
    removed = set(commit.get("removed") or [])
    names = [p.rsplit("/", 1)[-1] for p in paths]
    dupes = {n for n in names if names.count(n) > 1}
    cells = []
    for path, name in zip(paths, names):
        label = _escape(path if name in dupes else name)
        if path in removed:
            cells.append(f"~~[{label}]({commit.get('url', '')})~~ ({DELETED})")
        else:
            cells.append(f"[{label}](https://github.com/{study}/blob/{branch}/{path}"
                         f" \"{path}\")")
    return ", ".join(cells) or "—"


def render(state, gate_no):
    """The managed block for one gate, markers included; "" if nothing to show."""
    rec = state.get("gates", {}).get(str(gate_no), {})
    commits = rec.get("commits") or []
    if not commits:
        return ""
    study = state["study_repo"]
    branch = state.get("default_branch", "main")
    ordered = sorted(commits, key=lambda c: c.get("at") or "", reverse=True)

    lines = [
        START,
        "### Issue history",
        "",
        "| When (UTC) | Files touched | Commit | By |",
        "|---|---|---|---|",
    ]
    for c in ordered[:SHOWN]:
        message = _escape(clip(c.get("message") or "")) or "(no message)"
        author = c.get("author") or ""
        lines.append(f"| {when(c.get('at'))} | {files_cell(c, study, branch)} "
                     f"| [{message}]({c.get('url', '')}) "
                     f"| {'@' + author if author else '—'} |")

    note = (f"Every push to `{branch}` that changed a file this gate watches, "
            "newest first, whether or not it moved the gate.")
    if len(ordered) > SHOWN:
        note += (f" The latest {SHOWN} of {len(ordered)} are shown; Factory's "
                 "state file for this study has them all.")
    lines += [
        "",
        f"<sub>{note} Rewritten by Factory; edits inside this block are "
        "overwritten.</sub>",
        "",
        "---",
        END,
    ]
    return "\n".join(lines)


def splice(body, block):
    """`body` with the block at the top: replaced if present, else prepended.

    An empty block removes one that is there. Whatever sits below the block
    — the gate prose, the technical requirements, anything a person added —
    is not touched.
    """
    body = body or ""
    if START in body and END in body:
        head = body[:body.index(START)]
        tail = body[body.index(END) + len(END):]
        if not block:
            return (head.rstrip() + "\n\n" + tail.lstrip("\n")).lstrip("\n")
        return head + block + tail
    if not block:
        return body
    return block + "\n\n" + body.lstrip("\n")


# --------------------------------------------------------------------------
# The refresh
# --------------------------------------------------------------------------

def refresh(state, gate_no, dry_run=False):
    """Bring one gate issue's history table up to date. True if it was edited.

    Best-effort: an issue that cannot be read or written must never fail the
    push that called this. The state file is the record; the table is the
    view of it, and the next push will try again.
    """
    repo = state.get("study_repo")
    num = state.get("gate_issues", {}).get(str(gate_no)) \
        or state.get("gates", {}).get(str(gate_no), {}).get("issue")
    if not repo or not num:
        return False

    raw = gh("api", f"repos/{repo}/issues/{num}", check=False)
    try:
        body = json.loads(raw).get("body") or ""
    except (ValueError, AttributeError):
        print(f"::warning::issue history: could not read {repo}#{num}")
        return False

    new_body = splice(body, render(state, gate_no))
    if new_body == body:
        print(f"  issue history: {repo}#{num} unchanged")
        return False
    if dry_run:
        print(new_body)
        return True

    r = subprocess.run(["gh", "issue", "edit", str(num), "--repo", repo,
                        "--body", new_body], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        print(f"::warning::issue history: could not update {repo}#{num}: "
              f"{r.stderr.strip()}")
        return False
    print(f"  issue history: updated {repo}#{num} (gate {gate_no})")
    return True


# --------------------------------------------------------------------------
# Self-test: the rules that must not regress
# --------------------------------------------------------------------------

def _self_test():
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    cfg = {"gates": [
        {"gate": 0, "detection": {"event": "content_changed", "paths": ["TEAM.md"]}},
        {"gate": 3, "detection": {"event": "content_changed", "require": "all",
                                  "paths": ["inst/cohorts/**/*.json", "inst/Cohorts.csv"],
                                  "supporting_paths": ["inst/sql/sql_server/**/*.sql"]}},
        {"gate": 5, "detection": {"event": "derived_from_partners",
                                  "paths": ["partners.csv"]}},
    ]}
    base = {"blobs": {"inst/Cohorts.csv": "bbb", "inst/cohorts/11.json": "ccc"}}

    def fresh():
        return {"study_repo": "org/study-x", "default_branch": "main",
                "gates": {"0": {"status": "in_progress", "entered_at": None,
                                "issue": 1, "evidenced_by": []}},
                "gate_issues": {"0": 1, "3": 4, "5": 6}}

    push = {"commit_sha": "abc1234def", "commit_url": "https://x/c/abc1234def",
            "commit_message": "Added Measurement based logic\n\nLong body here.",
            "author": "jokafor", "pushed_at": "2026-09-11T09:07:00-04:00",
            "paths": ["inst/cohorts/11.json", "inst/sql/sql_server/11.sql",
                      "partners.csv", "README.md"]}
    blobs = {"inst/cohorts/11.json": "new", "inst/sql/sql_server/11.sql": "s",
             "partners.csv": "p", "README.md": "r", "inst/Cohorts.csv": "bbb"}

    s = fresh()
    logged = record(s, cfg, base, push, blobs)
    check("a push is recorded against the gates whose files it changed",
          logged == [3])
    check("  ...never against a manual gate", "5" not in s["gates"])
    entry = s["gates"]["3"]["commits"][0]
    check("  ...with required and supporting paths, nothing else",
          entry["paths"] == ["inst/cohorts/11.json", "inst/sql/sql_server/11.sql"])
    check("  ...the first line of the message",
          entry["message"] == "Added Measurement based logic")
    check("  ...the time in UTC", entry["at"] == "2026-09-11T13:07:00+00:00")
    check("  ...and the gate's issue number, for a gate not yet in the state",
          s["gates"]["3"]["issue"] == 4)
    check("the same push again changes nothing",
          record(s, cfg, base, push, blobs) == [] and len(s["gates"]["3"]["commits"]) == 1)
    again = dict(push, paths=["inst/cohorts/11.json"])
    check("the same commit with different details is replaced, not duplicated",
          record(s, cfg, base, again, blobs) == [3]
          and len(s["gates"]["3"]["commits"]) == 1
          and s["gates"]["3"]["commits"][0]["paths"] == ["inst/cohorts/11.json"])

    check("a template file still identical to the baseline is not logged",
          record(fresh(), cfg, base, dict(push, paths=["inst/Cohorts.csv"]),
                 {"inst/Cohorts.csv": "bbb"}) == [])
    check("an unrelated push is not logged",
          record(fresh(), cfg, base, dict(push, paths=["README.md"]), blobs) == [])
    s = fresh()
    record(s, cfg, base, dict(push, paths=["inst/Cohorts.csv"]), {})
    check("a deleted file is logged and marked as removed",
          s["gates"]["3"]["commits"][0]["removed"] == ["inst/Cohorts.csv"])
    s = fresh()
    record(s, cfg, base, dict(push, pushed_at="not a date", commit_message=""),
           blobs, now="2026-09-12T00:00:00+00:00")
    check("an unparseable timestamp is kept as sent",
          s["gates"]["3"]["commits"][0]["at"] == "not a date")
    s = fresh()
    record(s, cfg, base, dict(push, pushed_at=None), blobs,
           now="2026-09-12T00:00:00+00:00")
    check("a missing timestamp falls back to now",
          s["gates"]["3"]["commits"][0]["at"] == "2026-09-12T00:00:00+00:00")

    check("the time is shown to the minute in UTC",
          when("2026-09-11T09:07:33-04:00") == "2026-09-11 13:07")
    check("a long subject is cut with an ellipsis",
          clip("x" * 80) == "x" * 71 + "…" and clip("short") == "short")
    check("table-breaking characters are escaped",
          _escape("fix [a|b] <c>") == "fix \\[a\\|b\\] \\<c>")

    check("a gate with no commits renders nothing", render(fresh(), 3) == "")
    s = fresh()
    record(s, cfg, base, push, blobs)
    record(s, cfg, base, dict(push, commit_sha="0000000aaa", commit_url="https://x/c/0",
                              commit_message="Removed problematic descendants W61.62XD",
                              pushed_at="2026-09-04T09:10:00Z", author="",
                              paths=["inst/cohorts/11.json"]), blobs)
    block = render(s, 3)
    check("the block is wrapped in its markers",
          block.startswith(START) and block.endswith(END))
    check("  ...has the four columns",
          "| When (UTC) | Files touched | Commit | By |" in block)
    rows = [l for l in block.splitlines() if l.startswith("| 2026")]
    check("  ...one row per push, newest first",
          len(rows) == 2 and rows[0].startswith("| 2026-09-11 13:07 |")
          and rows[1].startswith("| 2026-09-04 09:10 |"))
    check("  ...files by name, linked to the file on the branch, path on hover",
          "[11.json](https://github.com/org/study-x/blob/main/inst/cohorts/11.json "
          "\"inst/cohorts/11.json\")" in rows[0]
          and "[11.sql](https://github.com/org/study-x/blob/main/inst/sql/sql_server/11.sql "
              "\"inst/sql/sql_server/11.sql\")" in rows[0])
    check("  ...the message linked to the commit, and the author",
          "| [Added Measurement based logic](https://x/c/abc1234def) | @jokafor |" in rows[0])
    check("  ...a missing author shown as a dash", rows[1].endswith("| — |"))
    check("  ...and ends with a rule so the prose below stands apart",
          block.splitlines()[-2] == "---")

    s = fresh()
    record(s, cfg, base, dict(push, paths=["inst/cohorts/a/1.json", "inst/cohorts/b/1.json"]),
           {"inst/cohorts/a/1.json": "1", "inst/cohorts/b/1.json": "2"})
    check("two files with one name are shown by their paths",
          "[inst/cohorts/a/1.json](" in render(s, 3) and "[inst/cohorts/b/1.json](" in render(s, 3))
    s = fresh()
    record(s, cfg, base, dict(push, paths=["inst/Cohorts.csv"]), {})
    check("a deleted file is struck through and linked to the commit",
          "~~[Cohorts.csv](https://x/c/abc1234def)~~ (deleted)" in render(s, 3))

    s = fresh()
    for i in range(SHOWN + 3):
        record(s, cfg, base, dict(push, commit_sha=f"sha{i:04}",
                                  pushed_at=f"2026-01-01T00:{i % 60:02}:00+00:00"), blobs)
    big = render(s, 3)
    check("the table stops at the newest rows and says so",
          big.count("\n| 2026") == SHOWN and f"latest {SHOWN} of {SHOWN + 3}" in big)

    prose = "**What this gate means.** Prose.\n\n---\n\nRequirements.\n"
    first = splice(prose, block)
    check("the first table goes above the prose, untouched",
          first.startswith(START) and first.endswith(prose)
          and first.count(START) == 1)
    later = splice(first, block.replace("jokafor", "someone"))
    check("a later refresh replaces the block and nothing else",
          later.count(START) == 1 and "someone" in later and "jokafor" not in later
          and later.endswith(prose))
    check("an identical refresh is a no-op", splice(first, block) == first)
    check("an empty block leaves an untouched issue alone", splice(prose, "") == prose)
    check("  ...and removes one that is there", splice(first, "") == prose)
    check("an empty body still gets the block", splice("", block) == block + "\n\n")

    failed = [n for n, ok in checks if not ok]
    if failed:
        raise AssertionError("issue_history self-test failed:\n  " + "\n  ".join(failed))
    return len(checks)


if __name__ == "__main__":
    if "--self-test" in sys.argv or len(sys.argv) == 1:
        print(f"issue_history self-test passed ({_self_test()} cases)")
