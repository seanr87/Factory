#!/usr/bin/env python3
"""Apply one study_push dispatch to a study's gate state.

All the I/O around gate_machine.evaluate(): read state and baseline, fetch the
blob SHAs the decision needs, then write the result to the study's gate issue,
the Factory tracking issue, and the state file.

Nothing here decides anything. The rules — advance only, propose don't close,
manual gates — live in gate_machine.py so they can be tested without a network.

Every change posts a comment saying what was seen, in which commit. People stop
trusting automation the first time it is wrong and unexplained, so a silent flip
is never acceptable, even when the change is obviously right.

Usage:
    run_gate_machine.py --payload payload.json
"""

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from gate_machine import DONE, READY, evaluate  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
GATES = ROOT / ".github" / "data" / "gates.json"


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def fetch_blobs(repo, sha, paths):
    """Blob SHAs for `paths` at `sha`. Missing paths were deleted."""
    tree = json.loads(gh("api", f"repos/{repo}/git/trees/{sha}?recursive=1"))
    wanted = set(paths)
    return {n["path"]: n["sha"] for n in tree.get("tree", [])
            if n["type"] == "blob" and n["path"] in wanted}


def comment(repo, issue, body):
    subprocess.run(
        ["gh", "issue", "comment", str(issue), "--repo", repo, "--body", body],
        check=False, capture_output=True, text=True)


def evidence_comment(decision, payload, gate_title):
    short = payload["commit_sha"][:7]
    lines = [
        f"**Moved to Ready for review** — {gate_title}",
        "",
        "Factory saw these paths change:",
        "",
    ]
    lines += [f"- `{p}`" for p in decision.evidence]
    lines += [
        "",
        f"in [`{short}`]({payload['commit_url']})"
        + (f" by @{payload['author']}" if payload.get("author") else "")
        + f", pushed {payload['pushed_at']}.",
        "",
        "Detecting a file is not the same as the file being any good, so this "
        "issue is **not** closed. Someone reviews it and closes it by hand.",
    ]
    if decision.ignored:
        lines += ["", "Also changed, for gates already passed:"]
        lines += [f"- gate {g}: " + ", ".join(f"`{p}`" for p in ps)
                  for g, ps in decision.ignored]
    return "\n".join(lines)


def held_comment(decision, payload):
    short = payload["commit_sha"][:7]
    lines = [
        "**No gate change.** Factory saw work here but did not move anything.",
        "",
        f"Reason: {decision.reason}.",
        "",
        f"Commit [`{short}`]({payload['commit_url']}).",
    ]
    if decision.ignored:
        lines += ["", "Paths that matched a gate:"]
        lines += [f"- gate {g}: " + ", ".join(f"`{p}`" for p in ps)
                  for g, ps in decision.ignored]
    return "\n".join(lines)


def update_factory_issue(state, gates_config, payload):
    """Rewrite the Factory issue's status block. Body is current state."""
    gate_no = state["current_gate"]
    title = next((g["title"] for g in gates_config["gates"]
                  if g["gate"] == gate_no), f"Gate {gate_no}")
    entered = state["gate_entered_at"]
    days = ""
    if entered:
        delta = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(entered)
        days = f" · {delta.days} day(s) in this gate"

    block = (
        "<!--factory:status-->\n"
        f"**Current gate:** {title}\n"
        f"**Entered:** {entered or '—'}{days}\n"
        f"**Last activity:** [`{payload['commit_sha'][:7]}`]"
        f"({payload['commit_url']}) on {payload['pushed_at']}\n"
        "<!--/factory:status-->"
    )

    repo, num = state["factory_repo"], state["factory_issue"]
    body = json.loads(gh("api", f"repos/{repo}/issues/{num}", "--jq", "{body:.body}"))["body"] or ""

    start, end = "<!--factory:status-->", "<!--/factory:status-->"
    if start in body and end in body:
        body = body[:body.index(start)] + block + body[body.index(end) + len(end):]
    else:
        body = body.rstrip() + "\n\n" + block + "\n"

    subprocess.run(["gh", "issue", "edit", str(num), "--repo", repo,
                    "--body", body], check=False, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True)
    ap.add_argument("--state-dir", default=".github/data/state")
    ap.add_argument("--baseline-dir", default=".github/data/baselines")
    args = ap.parse_args()

    payload = json.loads(pathlib.Path(args.payload).read_text(encoding="utf-8"))
    study_repo = payload["study_repo"]
    slug = study_repo.split("/")[-1]

    gates_config = json.loads(GATES.read_text(encoding="utf-8"))

    state_path = ROOT / args.state_dir / f"{slug}.json"
    baseline_path = ROOT / args.baseline_dir / f"{slug}.json"

    if not state_path.exists():
        print(f"::warning::No gate state for {study_repo} — not a tracked study. "
              f"Expected {state_path.relative_to(ROOT).as_posix()}")
        return 0
    if not baseline_path.exists():
        print(f"::warning::No baseline for {study_repo}; cannot distinguish lead "
              f"edits from template content. Skipping.")
        return 0

    state = json.loads(state_path.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    paths = payload.get("paths", [])
    current_blobs = fetch_blobs(study_repo, payload["commit_sha"], paths) if paths else {}

    decision = evaluate(gates_config, baseline, state, paths, current_blobs)
    print(f"decision: {decision}")
    print(f"reason:   {decision.reason}")

    if not decision.advance:
        # Only speak up when something matched. Commenting on every unrelated
        # push would train people to ignore the comments.
        if decision.ignored:
            gate_issue = state["gate_issues"].get(str(state["current_gate"]))
            if gate_issue:
                comment(study_repo, gate_issue, held_comment(decision, payload))
        print("no advance")
        return 0

    target = str(decision.to_gate)
    stamp = now()
    gate_title = next((g["title"] for g in gates_config["gates"]
                       if g["gate"] == decision.to_gate), f"Gate {target}")

    rec = state["gates"].setdefault(target, {"status": "not_started",
                                             "entered_at": None,
                                             "issue": None,
                                             "evidenced_by": []})
    # Never downgrade a gate a human already closed.
    if rec.get("status") != DONE:
        rec["status"] = READY
    rec["entered_at"] = rec.get("entered_at") or stamp
    rec["evidenced_by"] = decision.evidence

    state["current_gate"] = decision.to_gate
    state["gate_entered_at"] = stamp
    state["history"].append({
        "at": stamp,
        "from_gate": decision.from_gate,
        "to_gate": decision.to_gate,
        "commit": payload["commit_sha"],
        "evidence": decision.evidence,
    })

    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    gate_issue = state["gate_issues"].get(target)
    if gate_issue:
        comment(study_repo, gate_issue, evidence_comment(decision, payload, gate_title))
        print(f"commented on {study_repo}#{gate_issue}")

    update_factory_issue(state, gates_config, payload)
    print(f"advanced {decision.from_gate} -> {decision.to_gate}")

    with open(subprocess.os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write(f"advanced=true\n")
        fh.write(f"to_gate={decision.to_gate}\n")
        fh.write(f"state_path={state_path.relative_to(ROOT).as_posix()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
