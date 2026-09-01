#!/usr/bin/env python3
"""Create the Gate 0-7 issues in a study repository and seed its gate state.

Replaces the three coarse `status-tracking` issues of v1 with the eight gate
issues whose prose lives in .github/issue-templates/. The wording there is
deliberate and matches the fellowship's onboarding materials, so it is copied
through with one transformation: a backticked repository path becomes a link into
the study repository. Relative links do not resolve inside a GitHub issue, so
that can only happen here, where the repository's name is known.

A "How this gate moves" block is then appended. It is generated from the gate's
detection rules rather than written by hand, so the issue can never promise a
behaviour the state machine does not have — a `require: all_sections` gate that
said "any change moves this" is how a lead ends up editing the abstract and
wondering why nothing happened.

This also writes the study's initial state file. That file is the machine record
Factory owns: which issue is which gate, when each gate was entered, and what
evidenced it. Recording issue numbers here means the state machine never has to
match a gate by parsing an issue title, which is the kind of thing that breaks
the first time somebody edits one.

A gate whose front matter says `initial_status: in_progress` starts there, on the
board and in the state file. Gates 0 and 1 have no prerequisite — a lead can open
either file the day the repository exists — so a board that shows them as not
started is telling the lead there is nothing to do yet, which is the opposite of
the truth.

Usage:
    create_gate_issues.py --repo owner/study-x --factory-repo owner/Factory \\
        --factory-issue 42 [--project-id PVT_...] [--branch main]
    create_gate_issues.py --self-test
"""

import argparse
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from run_gate_machine import update_study_board_status  # noqa: E402

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

# A backticked token that reads as a repository path: either a directory
# (`inst/cohorts/`) or a file with an extension (`TEAM.md`,
# `Documents/Protocol.Rmd`). Plain names such as `ohdsi-studies` are left alone.
# The guards skip a token that is already the text of a link.
REPO_PATH = re.compile(
    r"(?<!\[)`("
    r"(?:[A-Za-z0-9_.-]+/)+"                                     # directory
    r"|(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_-][A-Za-z0-9_.-]*\.[A-Za-z0-9]+"  # file
    r")`(?!\])"
)

GLOB_CHARS = "*?["

# Board column and state-file status for a gate that starts open.
IN_PROGRESS = "in_progress"
BOARD_IN_PROGRESS = "In progress"


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def ensure_labels(repo, gates):
    wanted = list(LABELS)
    for label in gates.get("partner_status_labels", []):
        wanted.append((label, "fef2c0", "Data partner status"))
    for name, color, desc in wanted:
        gh("label", "create", name, "--repo", repo, "--color", color,
           "--description", desc, check=False)
    print(f"  ensured {len(wanted)} labels")


def default_branch(repo):
    """The branch links should point at. Falls back to main if unreadable."""
    return gh("api", f"repos/{repo}", "--jq", ".default_branch", check=False) or "main"


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def repo_url(study_repo, path, branch):
    """Where `path` lives on GitHub. A glob links to the directory it starts in."""
    base = f"https://github.com/{study_repo}"
    if any(c in path for c in GLOB_CHARS):
        fixed = []
        for segment in path.split("/"):
            if any(c in segment for c in GLOB_CHARS):
                break
            fixed.append(segment)
        return f"{base}/tree/{branch}/{'/'.join(fixed)}"
    if path.endswith("/"):
        return f"{base}/tree/{branch}/{path.rstrip('/')}"
    return f"{base}/blob/{branch}/{path}"


def link(study_repo, path, branch):
    return f"[`{path}`]({repo_url(study_repo, path, branch)})"


def linkify(text, study_repo, branch):
    """Turn every backticked repository path in `text` into a link."""
    return REPO_PATH.sub(lambda m: link(study_repo, m.group(1), branch), text)


def _join(items):
    return ", ".join(items)


def how_it_moves(gate, study_repo, branch):
    """The paragraph explaining what Factory watches and when it acts.

    One shape per detection rule, so the promise matches the machine:

      content_changed, any           first change -> Ready for review
      content_changed, all           first change -> In progress, all -> Ready
      content_changed, all_sections  first section -> In progress, all -> Ready
      derived_from_partners          read from partner issue labels, never a push
    """
    detection = gate["detection"]
    event = detection.get("event")
    paths = detection.get("paths") or []
    supporting = detection.get("supporting_paths") or []
    closes = "It never closes the issue itself — a person does that."

    def L(path):
        return link(study_repo, path, branch)

    if event == "derived_from_partners":
        minimum = detection.get("minimum_partners", 1)
        progress = {
            "any_partner": "It moves to **In progress** as soon as any partner "
                           "issue exists.",
            "any_returned": "It moves to **In progress** when the first partner "
                            "is marked *Results received*.",
        }.get(detection.get("in_progress_when"), "")
        ready = {
            "minimum_committed": f"It moves to **Ready for review** once {minimum} "
                                 "partners are marked *Committed* or further along.",
            "any_committed": "It moves to **Ready for review** once one partner is "
                             "marked *Committed* or further along.",
            "all_committed_returned": "It moves to **Ready for review** once every "
                                      "committed partner is marked *Results "
                                      f"received*, with at least {minimum} of them.",
        }.get(detection.get("ready_when"), "")
        lines = ["**How this gate moves.** Nothing you commit moves this gate. "
                 "Factory reads it from the status labels on the partner issues "
                 "in this repository. " + " ".join(s for s in (progress, ready) if s)
                 + " " + closes]
    elif event != "content_changed":
        lines = ["**How this gate moves.** This one cannot be detected from the "
                 "repository, so it is moved by hand. Nothing you commit will "
                 "advance it."]
    elif detection.get("require") == "all_sections":
        sections = detection.get("sections", [])
        lines = [
            f"**How this gate moves.** Factory watches {_join(L(p) for p in paths)} "
            "and reads these sections of it. The headings must stay exactly as "
            "they are, because that is how it finds them:",
            "",
            *[f"- {s}" for s in sections],
            "",
            "A section counts as written when the text under its heading differs "
            "from what the template shipped. Nothing else in the file counts: not "
            "the title block, not the abstract, not a heading with nothing under "
            "it. The first written section moves this issue to **In progress**, "
            "with a comment listing what is still to write. When every one of them "
            "is written it moves to **Ready for review**. " + closes,
        ]
    elif detection.get("require") == "all":
        lines = [
            "**How this gate moves.** Factory watches this repository for changes "
            "to all of:",
            "",
            *[f"- {L(p)}" for p in paths],
            "",
            "The first of these to differ from the Strategus template moves this "
            "issue to **In progress**, with a comment saying what is still "
            "outstanding. When every one of them differs it moves to **Ready for "
            "review** and comments here saying exactly what it saw. " + closes,
        ]
        if supporting:
            lines += ["",
                      f"Changes to {_join(L(p) for p in supporting)} are reported "
                      "too, but never move the gate on their own."]
    else:
        lines = [
            "**How this gate moves.** Factory watches this repository for changes "
            f"to {_join(L(p) for p in paths)}. When it sees one, it moves this "
            "issue to **Ready for review** and comments here saying exactly what "
            "it saw. " + closes
        ]

    if gate.get("initial_status") == IN_PROGRESS:
        lines += ["",
                  "This gate starts in **In progress**: there is nothing to wait "
                  "for before beginning it."]
    return "\n".join(lines)


def build_body(gate, factory_repo, factory_issue, study_repo, branch="main"):
    return (
        linkify(gate["body"], study_repo, branch)
        + "\n\n---\n\n"
        + how_it_moves(gate, study_repo, branch)
        + "\n\n<sub>Study: "
        + study_repo
        + " · Factory tracking: https://github.com/"
        + f"{factory_repo}/issues/{factory_issue}"
        + " · Do not edit this block.</sub>\n"
    )


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", help="study repo, owner/name")
    ap.add_argument("--factory-repo")
    ap.add_argument("--factory-issue", type=int)
    ap.add_argument("--project-id", default="")
    ap.add_argument("--branch", default="",
                    help="branch file links point at; default: the repo's default branch")
    ap.add_argument("--state-dir", default=".github/data/state")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        print(f"create_gate_issues self-test passed ({_self_test()} cases)")
        return
    for required in ("repo", "factory_repo", "factory_issue"):
        if getattr(args, required) is None:
            ap.error(f"--{required.replace('_', '-')} is required")

    gates = json.loads(GATES.read_text(encoding="utf-8"))
    ensure_labels(args.repo, gates)
    branch = args.branch or default_branch(args.repo)

    gate_issues, state_gates = {}, {}

    for gate in gates["gates"]:
        number = gate["gate"]
        body = build_body(gate, args.factory_repo, args.factory_issue, args.repo,
                          branch)

        cmd = ["issue", "create", "--repo", args.repo,
               "--title", gate["title"], "--body", body]
        for label in gate.get("labels", []):
            cmd += ["--label", label]

        url = gh(*cmd)
        issue_no = int(url.rstrip("/").split("/")[-1])
        gate_issues[str(number)] = issue_no
        initial = gate.get("initial_status", "not_started")
        state_gates[str(number)] = {
            "status": initial,
            "entered_at": now() if initial != "not_started" else None,
            "issue": issue_no,
            "evidenced_by": [],
        }
        print(f"  gate {number}: #{issue_no}  {gate['title']}"
              + (f"  [{initial}]" if initial != "not_started" else ""))

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

    # The board defaults every new card to its first column. A gate that starts
    # open has to be moved, or the board contradicts the state file from day one.
    for number, rec in state_gates.items():
        if rec["status"] == IN_PROGRESS:
            update_study_board_status(state, int(number), BOARD_IN_PROGRESS)

    slug = args.repo.split("/")[-1]
    out = ROOT / args.state_dir / f"{slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    print(f"  wrote state: {out.relative_to(ROOT).as_posix()}")

    with open(subprocess.os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write(f"state_path={out.relative_to(ROOT).as_posix()}\n")
        fh.write(f"issues_created={len(gate_issues)}\n")


# --------------------------------------------------------------------------
# Self-test. The rendering rules that must not regress.
# --------------------------------------------------------------------------

def _self_test():
    repo, br = "org/study-x", "main"
    base = f"https://github.com/{repo}"
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    # Linking repository paths.
    check("a file becomes a blob link",
          linkify("Add yourself to `TEAM.md`.", repo, br)
          == f"Add yourself to [`TEAM.md`]({base}/blob/main/TEAM.md).")
    check("a nested file keeps its path",
          f"({base}/blob/main/Documents/Protocol.Rmd)"
          in linkify("Edit `Documents/Protocol.Rmd` first.", repo, br))
    check("a directory becomes a tree link",
          linkify("JSON in `inst/cohorts/`", repo, br)
          == f"JSON in [`inst/cohorts/`]({base}/tree/main/inst/cohorts)")
    check("a plain name is left alone",
          linkify("The `ohdsi-studies` organisation", repo, br)
          == "The `ohdsi-studies` organisation")
    check("an existing link is not linked twice",
          linkify("[`TEAM.md`](x)", repo, br) == "[`TEAM.md`](x)")
    check("a path in parentheses is still linked",
          linkify("the script (`spec.R`)", repo, br)
          == f"the script ([`spec.R`]({base}/blob/main/spec.R))")
    check("several paths in one line are all linked",
          linkify("`TEAM.md` and `partners.csv`", repo, br).count("](") == 2)
    check("a glob links to the directory it starts in",
          repo_url(repo, "inst/cohorts/**/*.json", br)
          == f"{base}/tree/main/inst/cohorts")
    check("a non-default branch is honoured",
          repo_url(repo, "TEAM.md", "develop") == f"{base}/blob/develop/TEAM.md")

    # The generated block matches the detection rule.
    any_gate = {"detection": {"event": "content_changed", "paths": ["TEAM.md"]}}
    text = how_it_moves(any_gate, repo, br)
    check("an any-gate promises Ready for review on the first change",
          "**Ready for review**" in text and "In progress" not in text)
    check("  ...and links the watched path", f"{base}/blob/main/TEAM.md" in text)

    all_gate = {"detection": {"event": "content_changed", "require": "all",
                              "paths": ["spec.R", "spec.json"],
                              "supporting_paths": ["nc.csv"]}}
    text = how_it_moves(all_gate, repo, br)
    check("an all-gate lists every required path",
          "- [`spec.R`]" in text and "- [`spec.json`]" in text)
    check("  ...promises In progress before Ready for review",
          text.index("**In progress**") < text.index("**Ready for review**"))
    check("  ...and says supporting paths never move it alone",
          "nc.csv" in text and "never move the gate on their own" in text)

    sections_gate = {"detection": {"event": "content_changed",
                                   "require": "all_sections",
                                   "paths": ["Documents/Protocol.Rmd"],
                                   "sections": ["Study Objectives", "Analysis"]}}
    text = how_it_moves(sections_gate, repo, br)
    check("a sections-gate names every required section",
          "- Study Objectives" in text and "- Analysis" in text)
    check("  ...says the headings must not change",
          "headings must stay exactly as they are" in text)
    check("  ...and says what does not count", "not the abstract" in text)

    derived = {"detection": {"event": "derived_from_partners",
                             "in_progress_when": "any_returned",
                             "ready_when": "all_committed_returned",
                             "minimum_partners": 3}}
    text = how_it_moves(derived, repo, br)
    check("a derived gate says a push never moves it",
          "Nothing you commit moves this gate" in text)
    check("  ...and states both thresholds",
          "*Results received*" in text and "at least 3" in text)

    body = build_body({"body": "See `TEAM.md`.", "initial_status": "in_progress",
                       "detection": any_gate["detection"]},
                      "org/Factory", 7, repo, br)
    check("a gate that starts open says so", "starts in **In progress**" in body)
    check("the body ends with the reference block",
          "Factory tracking: https://github.com/org/Factory/issues/7" in body)

    real = json.loads(GATES.read_text(encoding="utf-8"))
    rendered = [build_body(g, "org/Factory", 1, repo, br) for g in real["gates"]]
    check("every real template that watches a path renders it as a link",
          all("](https://github.com/" in b
              for g, b in zip(real["gates"], rendered)
              if g["detection"].get("paths")))
    check("no real template leaves a bare watched path in its prose",
          not any(re.search(r"(?<!\[)`(TEAM\.md|partners\.csv|Documents/[^`]+)`", b)
                  for b in rendered))

    failed = [n for n, ok in checks if not ok]
    if failed:
        raise AssertionError("create_gate_issues self-test failed:\n  "
                             + "\n  ".join(failed))
    return len(checks)


if __name__ == "__main__":
    main()
