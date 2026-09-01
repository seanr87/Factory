#!/usr/bin/env python3
"""Advance Gate 6 from partner issue status.

Gate 6 — "Study executed across partners" — is the one phase that happens
entirely outside this system. Partners run the package on machines Factory will
never see, on data it will never touch. Nothing about it can be detected from
repository activity, so the evidence is the only trace that reaches GitHub: the
status labels on the partner issues.

The rule, deliberately conservative:

    every committed partner has returned results, and there is at least one

"Committed" counts anyone who agreed to run it — committed, package running, or
results received — because a site that has already returned results was
obviously committed. Partners still being recruited, or who declined, are not
part of the denominator; a study should not be blocked from Gate 6 by a site
that said no.

Like every other advance in this system this proposes rather than concludes: the
gate reaches Ready for review and a human closes it. "You've confirmed each
result set is complete before counting it as received, rather than assuming" is
one of Gate 6's own checks, and that is not something a label can establish.
"""

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
GATES = ROOT / ".github" / "data" / "gates.json"

GATE = 6
RETURNED = "status:results-received"
# Anyone who agreed to run it. A site that has returned results was committed
# whether or not anybody moved its label through every intermediate state.
COMMITTED = {"status:committed", "status:package-running", RETURNED}


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def partner_states(repo):
    raw = gh("issue", "list", "--repo", repo, "--label", "partner",
             "--state", "open", "--limit", "200",
             "--json", "number,title,labels", check=False)
    if not raw:
        return []
    out = []
    for issue in json.loads(raw):
        status = next((l["name"] for l in issue.get("labels", [])
                       if l["name"].startswith("status:")), None)
        out.append({"number": issue["number"], "title": issue["title"],
                    "status": status})
    return out


def assess(partners):
    committed = [p for p in partners if p["status"] in COMMITTED]
    returned = [p for p in partners if p["status"] == RETURNED]
    ready = bool(committed) and len(returned) == len(committed)
    return committed, returned, ready


def comment_body(committed, returned, ready):
    names = "\n".join(
        f"- {p['title'].replace('Data partner — ', '')} — "
        f"{'returned' if p['status'] == RETURNED else 'still running'}"
        for p in committed)

    if ready:
        head = (f"**Moved to Ready for review** — Gate 6\n\n"
                f"All {len(committed)} committed partner(s) have returned results.")
        tail = ("\n\nFactory read this from the partner issue labels, not from anything "
                "in the repository — execution happens on machines it never sees. "
                "Confirm each result set is actually complete before closing this; "
                "a label says results arrived, not that they are whole.")
    else:
        head = (f"**Execution progress** — {len(returned)} of {len(committed)} "
                f"committed partner(s) have returned results.")
        tail = "\n\nThis gate moves when every committed partner has returned."
    return f"{head}\n\n{names}{tail}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=".github/data/state")
    ap.add_argument("--study", default="", help="limit to one study repo")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gates_config = json.loads(GATES.read_text(encoding="utf-8"))
    state_dir = ROOT / args.state_dir
    files = sorted(state_dir.glob("*.json")) if state_dir.exists() else []
    if not files:
        print("No studies tracked yet.")
        return 0

    changed = []
    for path in files:
        state = json.loads(path.read_text(encoding="utf-8"))
        repo = state["study_repo"]
        if args.study and repo != args.study:
            continue

        partners = partner_states(repo)
        if not partners:
            continue

        committed, returned, ready = assess(partners)
        if not committed:
            print(f"  {repo}: no committed partners yet")
            continue

        print(f"  {repo}: {len(returned)}/{len(committed)} committed partners returned"
              + ("  -> Gate 6 ready" if ready else ""))

        rec = state["gates"].get(str(GATE), {})
        already = rec.get("status") in ("ready_for_review", "done")

        # Advance only, and never past a human's decision to close it.
        if not ready or already or state.get("current_gate", -1) >= GATE:
            continue

        issue = state["gate_issues"].get(str(GATE))
        stamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

        if args.dry_run:
            print(f"    [dry run] would advance {repo} to gate {GATE}")
            continue

        rec.update({
            "status": "ready_for_review",
            "entered_at": rec.get("entered_at") or stamp,
            "issue": issue,
            "evidenced_by": [f"{len(returned)} partner(s) at {RETURNED}"],
        })
        state["gates"][str(GATE)] = rec
        state["history"].append({
            "at": stamp,
            "from_gate": state.get("current_gate", -1),
            "to_gate": GATE,
            "commit": None,
            "evidence": [p["title"] for p in returned],
        })
        state["current_gate"] = GATE
        state["gate_entered_at"] = stamp
        path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

        if issue:
            subprocess.run(["gh", "issue", "comment", str(issue), "--repo", repo,
                            "--body", comment_body(committed, returned, ready)],
                           check=False, capture_output=True, text=True)
        changed.append(repo)
        print(f"    advanced {repo} to gate {GATE}")

    out = subprocess.os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")
            fh.write(f"changed_studies={','.join(changed)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
