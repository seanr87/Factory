#!/usr/bin/env python3
"""Create the Gate 0-7 issues in a study repository and seed its gate state.

Replaces the three coarse `status-tracking` issues of v1 with the eight gate
issues whose prose lives in .github/issue-templates/. The wording there is
deliberate and matches the fellowship's onboarding materials, so it is copied
through unchanged; only a Factory reference block is appended.

This also writes the study's initial state file. That file is the machine record
Factory owns: which issue is which gate, when each gate was entered, and what
evidenced it. Recording issue numbers here means the state machine never has to
match a gate by parsing an issue title, which is the kind of thing that breaks
the first time somebody edits one.

Usage:
    create_gate_issues.py --repo owner/study-x --factory-repo owner/Factory \\
        --factory-issue 42 [--project-id PVT_...]
"""

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
GATES = ROOT / ".github" / "data" / "gates.json"

# Applied to every study repo. The milestone/work-item split is what lets the
# project board separate gate signal from day-to-day task churn.
LABELS = [
    ("gate", "0969da", "Tracks one gate of study progress"),
    ("milestone", "8250df", "Gate-level signal, not day-to-day work"),
    ("work-item", "0e8a16", "Day-to-day task"),
    ("partner", "d4c5f9", "A data partner tracking issue"),
]


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def ensure_labels(repo, gates):
    wanted = list(LABELS)
    for label in gates.get("partner_status_labels", []):
        wanted.append((label, "fef2c0", "Data partner status"))
    for name, color, desc in wanted:
        gh("label", "create", name, "--repo", repo, "--color", color,
           "--description", desc, check=False)
    print(f"  ensured {len(wanted)} labels")


def build_body(gate, factory_repo, factory_issue, study_repo):
    detection = gate["detection"]
    paths = detection.get("paths") or []

    if detection.get("event") == "content_changed":
        how = (
            "**How this gate moves.** Factory watches this repository for changes to "
            + ", ".join(f"`{p}`" for p in paths)
            + ". When it sees one, it moves this issue to **Ready for review** and "
            "comments here saying exactly what it saw. It never closes the issue "
            "itself — a person does that."
        )
    else:
        how = (
            "**How this gate moves.** This one cannot be detected from the repository, "
            "so it is moved by hand. Nothing you commit will advance it."
        )

    return (
        gate["body"]
        + "\n\n---\n\n"
        + how
        + "\n\n<sub>Study: "
        + study_repo
        + " · Factory tracking: https://github.com/"
        + f"{factory_repo}/issues/{factory_issue}"
        + " · Do not edit this block.</sub>\n"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="study repo, owner/name")
    ap.add_argument("--factory-repo", required=True)
    ap.add_argument("--factory-issue", required=True, type=int)
    ap.add_argument("--project-id", default="")
    ap.add_argument("--state-dir", default=".github/data/state")
    args = ap.parse_args()

    gates = json.loads(GATES.read_text(encoding="utf-8"))
    ensure_labels(args.repo, gates)

    gate_issues, state_gates = {}, {}

    for gate in gates["gates"]:
        number = gate["gate"]
        body = build_body(gate, args.factory_repo, args.factory_issue, args.repo)

        cmd = ["issue", "create", "--repo", args.repo,
               "--title", gate["title"], "--body", body]
        for label in gate.get("labels", []):
            cmd += ["--label", label]

        url = gh(*cmd)
        issue_no = int(url.rstrip("/").split("/")[-1])
        gate_issues[str(number)] = issue_no
        state_gates[str(number)] = {
            "status": "not_started",
            "entered_at": None,
            "issue": issue_no,
            "evidenced_by": [],
        }
        print(f"  gate {number}: #{issue_no}  {gate['title']}")

        if args.project_id:
            node = gh("api", f"repos/{args.repo}/issues/{issue_no}",
                      "--jq", ".node_id")
            gh("api", "graphql", "-f",
               "query=mutation($p:ID!,$c:ID!){addProjectV2ItemById("
               "input:{projectId:$p,contentId:$c}){item{id}}}",
               "-f", f"p={args.project_id}", "-f", f"c={node}", check=False)

        time.sleep(0.4)  # stay clear of secondary rate limits

    state = {
        "study_repo": args.repo,
        "factory_repo": args.factory_repo,
        "factory_issue": args.factory_issue,
        "study_project_id": args.project_id or None,
        "current_gate": -1,
        "gate_entered_at": None,
        "stall_threshold_days": gates.get("stall_threshold_days", 21),
        "gates": state_gates,
        "gate_issues": gate_issues,
        "history": [],
    }

    slug = args.repo.split("/")[-1]
    out = ROOT / args.state_dir / f"{slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    print(f"  wrote state: {out.relative_to(ROOT).as_posix()}")

    with open(subprocess.os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write(f"state_path={out.relative_to(ROOT).as_posix()}\n")
        fh.write(f"issues_created={len(gate_issues)}\n")


if __name__ == "__main__":
    main()
