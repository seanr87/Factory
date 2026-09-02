#!/usr/bin/env python3
"""Create the Gate 0-7 issues in a study repository and seed its gate state.

Replaces the three coarse `status-tracking` issues of v1 with the eight gate
issues whose prose lives in .github/issue-templates/. The wording there is
deliberate and matches the fellowship's onboarding materials, so it is copied
through with one transformation: a backticked repository path becomes a link into
the study repository. Relative links do not resolve inside a GitHub issue, so
that can only happen here, where the repository's name is known.

A "Technical requirements" block is then appended: the exact file to edit, the
branch to commit to, the headings to keep, and what counts as a change. It is
generated from the gate's detection rules rather than written by hand, so the
issue can never demand something the state machine does not check, or promise a
behaviour it does not have — a `require: all_sections` gate that said "any change
moves this" is how a lead ends up editing the abstract and wondering why nothing
happened.

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

from run_gate_machine import read_file, update_study_board_status  # noqa: E402
from sections import heading_lines, normalise  # noqa: E402

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

# What a watched file is compared against, by the gate's `baseline`.
SHIPPED = {
    "overlay": "the stub Factory placed there when the repository was created",
    "upstream": "what the Strategus template shipped",
}
SHIPPED_DEFAULT = "the version the repository was created with"

CLOSES = "It never closes the issue — a person does that."


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
    """The branch links point at and leads must commit to. Falls back to main."""
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


def line_url(study_repo, path, branch, line):
    """The file's source view with one line highlighted.

    `plain=1` matters: GitHub renders .Rmd and .md as Markdown by default, and
    `#L` anchors only work on the source view.
    """
    return f"{repo_url(study_repo, path, branch)}?plain=1#L{line}"


def section_lines(study_repo, path, branch):
    """Line of each heading in the study's copy of `path`; {} if unreadable."""
    return heading_lines(read_file(study_repo, path, branch) or "")


def linkify(text, study_repo, branch):
    """Turn every backticked repository path in `text` into a link."""
    return REPO_PATH.sub(lambda m: link(study_repo, m.group(1), branch), text)


def _join(items):
    return ", ".join(items)


def requirements(gate, study_repo, branch, lines=None):
    """The Technical requirements block: exactly what Factory needs to see.

    One shape per detection rule, so the requirements match the machine:

      content_changed, any           one file, any change from the scaffold
      content_changed, all           several files, every one of them changed
      content_changed, all_sections  one file, named sections written under
                                     headings kept word for word
      derived_from_partners          partner issue labels, never a push

    `lines` maps heading name to line number in the study's file, so a
    sections gate can link each heading to the exact line to write under.
    """
    detection = gate["detection"]
    event = detection.get("event")
    paths = detection.get("paths") or []
    supporting = detection.get("supporting_paths") or []
    shipped = SHIPPED.get(detection.get("baseline"), SHIPPED_DEFAULT)
    lines = lines or {}

    def L(path):
        return link(study_repo, path, branch)

    def S(section):
        n = lines.get(normalise(section))
        if not n:
            return section
        return f"[{section}]({line_url(study_repo, paths[0], branch, n)})"

    head = ("**Technical requirements** — what Factory needs to see before it "
            "moves this gate:")
    branch_req = (f"- **Branch:** commit to `{branch}`. Factory only hears about "
                  f"pushes to `{branch}`; work on any other branch is invisible "
                  "to it until merged.")

    if event == "derived_from_partners":
        minimum = detection.get("minimum_partners", 1)
        progress = {
            "minimum_partners": f"{minimum} partner issues exist.",
            "any_running": "the first partner is marked *Package running* "
                           "or further along.",
        }.get(detection.get("in_progress_when"))
        ready = {
            "minimum_interested": f"{minimum} partners are marked *Interested* "
                                  "or further along.",
            "minimum_returned": f"{minimum} partners are marked *Results received*.",
        }.get(detection.get("ready_when"))
        lines = [
            head, "",
            "- **No file moves this gate.** Factory reads each partner's status "
            "from its issue in this repository.",
            "- **To mark a partner:** drag its card to the right column on the "
            "board's *Data partners* view, or set the `status:` label on its "
            "issue — either works. Factory keeps the two in step and checks "
            "every hour.",
        ]
        if paths:
            lines.append(f"- **Partner issues come from** {_join(L(p) for p in paths)}: "
                         f"one row per institution, committed to `{branch}`. "
                         "Committing the file creates the issues; it does not "
                         "recruit anyone.")
        if progress:
            lines.append(f"- **In progress when:** {progress}")
        if ready:
            lines.append(f"- **Ready for review when:** {ready}")
        lines += ["", "Factory comments here each time it moves this gate. " + CLOSES]
    elif event != "content_changed":
        lines = [head, "",
                 "- **Nothing you commit moves this gate.** It cannot be detected "
                 "from the repository and is moved by hand."]
    elif detection.get("require") == "all_sections":
        sections = detection.get("sections", [])
        lines = [
            head, "",
            f"- **File to edit:** {_join(L(p) for p in paths)}. It already exists — "
            "edit it in place. Do not create a new file, rename it, or move it.",
            branch_req,
            "- **Headings to keep, word for word** — Factory finds each section "
            "by its heading. Each one links to its line in the file"
            + (", as of when this issue was created" if lines else "") + ":",
            *[f"  - {S(s)}" for s in sections],
            "- **What counts:** a section is written when the text under its "
            "heading, including any sub-headings you add, differs from "
            f"{shipped}. Text anywhere else in the file — the title block, the "
            "abstract, the appendices — does not count.",
            "",
            "Factory moves this issue to **In progress** at the first written "
            "section, with a comment listing what is still to write, and to "
            "**Ready for review** once all of them are written. " + CLOSES,
        ]
    elif detection.get("require") == "all":
        lines = [
            head, "",
            "- **Files to produce, all of them:**",
            *[f"  - {L(p)}" for p in paths],
        ]
        if supporting:
            lines.append(f"- **Reported but not required:** "
                         f"{_join(L(p) for p in supporting)}. Changes here are "
                         "mentioned in the comment but never move the gate alone.")
        lines += [
            branch_req,
            f"- **What counts:** each required file differs from {shipped}. A new "
            "file matching one of the patterns counts as changed.",
            "",
            "Factory moves this issue to **In progress** when the first required "
            "file changes, with a comment saying what is still outstanding, and "
            "to **Ready for review** once every one of them has. " + CLOSES,
        ]
    else:
        lines = [
            head, "",
            f"- **File to edit:** {_join(L(p) for p in paths)}, in this repository. "
            "Edit that file where it is; a new file somewhere else does not count.",
            branch_req,
            f"- **What counts:** the file's content differs from {shipped}. Any "
            "real change does.",
            "",
            "Factory then moves this issue to **Ready for review** and comments "
            "here saying exactly what it saw. " + CLOSES,
        ]

    if gate.get("initial_status") == IN_PROGRESS:
        lines += ["",
                  "This gate starts in **In progress**: there is nothing to wait "
                  "for before beginning it."]
    return "\n".join(lines)


def history_note(gate, branch):
    """How the issue will show the work, for gates a push can touch."""
    if gate["detection"].get("event") != "content_changed":
        return ""
    return (f"\n\nEvery push to `{branch}` that changes one of these files is "
            "listed in a table at the top of this issue — when, which files, "
            "and the commit message — whether or not it moves the gate. The "
            "table appears with the first such push.")


def build_body(gate, factory_repo, factory_issue, study_repo, branch="main",
               lines=None):
    return (
        linkify(gate["body"], study_repo, branch)
        + "\n\n---\n\n"
        + requirements(gate, study_repo, branch, lines)
        + history_note(gate, branch)
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
    ap.add_argument("--start-date", default="")
    ap.add_argument("--target-date", default="")
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
        detection = gate["detection"]
        lines = None
        if detection.get("require") == "all_sections" and detection.get("paths"):
            # The file is already there — it comes from the upstream template,
            # which is scaffolded before the gate issues are created.
            lines = section_lines(args.repo, detection["paths"][0], branch)
        body = build_body(gate, args.factory_repo, args.factory_issue, args.repo,
                          branch, lines)

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
        # So later comments can link into the live file without an API call.
        "default_branch": branch,
        "current_gate": -1,
        "gate_entered_at": None,
        "stall_threshold_days": gates.get("stall_threshold_days", 21),
        # Bracket the gates on the Factory issue's history table.
        "start_date": args.start_date or None,
        "target_date": args.target_date or None,
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

    # The requirements block matches the detection rule.
    any_gate = {"detection": {"event": "content_changed", "paths": ["TEAM.md"],
                              "baseline": "overlay"}}
    text = requirements(any_gate, repo, br)
    check("an any-gate names the file to edit, linked",
          "**File to edit:**" in text and f"{base}/blob/main/TEAM.md" in text)
    check("  ...names the branch to commit to", "commit to `main`" in text)
    check("  ...promises Ready for review on the first change",
          "**Ready for review**" in text and "In progress" not in text)
    check("  ...and describes the overlay baseline",
          "stub Factory placed there" in text)
    check("the branch requirement follows the repo's default branch",
          "commit to `develop`" in requirements(any_gate, repo, "develop"))

    all_gate = {"detection": {"event": "content_changed", "require": "all",
                              "paths": ["spec.R", "spec.json"],
                              "supporting_paths": ["nc.csv"],
                              "baseline": "upstream"}}
    text = requirements(all_gate, repo, br)
    check("an all-gate lists every required file",
          "- [`spec.R`]" in text and "- [`spec.json`]" in text)
    check("  ...promises In progress before Ready for review",
          text.index("**In progress**") < text.index("**Ready for review**"))
    check("  ...and says supporting paths never move it alone",
          "nc.csv" in text and "never move the gate alone" in text)
    check("  ...and describes the upstream baseline",
          "Strategus template shipped" in text)

    sections_gate = {"detection": {"event": "content_changed",
                                   "require": "all_sections",
                                   "paths": ["Documents/Protocol.Rmd"],
                                   "sections": ["Study Objectives", "Analysis"]}}
    text = requirements(sections_gate, repo, br)
    check("a sections-gate says to edit the existing file in place",
          "edit it in place" in text and "Do not create a new file" in text)
    check("  ...names every required section",
          "- Study Objectives" in text and "- Analysis" in text)
    check("  ...says the headings must be kept word for word",
          "Headings to keep, word for word" in text)
    check("  ...says sub-headings count", "including any sub-headings you add" in text)
    check("  ...and says what does not count", "the abstract" in text)
    check("  ...and lists headings as plain text when lines are unknown",
          "  - Study Objectives\n" in text and "#L" not in text)
    text = requirements(sections_gate, repo, br,
                        lines={"Study Objectives": 182, "Analysis": 198})
    check("with lines known, each heading links to its line in the source view",
          f"  - [Study Objectives]({base}/blob/main/Documents/Protocol.Rmd?plain=1#L182)"
          in text and "?plain=1#L198)" in text)
    check("  ...and says the lines date from issue creation",
          "as of when this issue was created" in text)
    check("a heading with no known line stays plain text",
          "  - Analysis\n" in requirements(sections_gate, repo, br,
                                           lines={"Study Objectives": 182}))

    derived = {"detection": {"event": "derived_from_partners",
                             "paths": ["partners.csv"],
                             "in_progress_when": "minimum_partners",
                             "ready_when": "minimum_interested",
                             "minimum_partners": 3}}
    text = requirements(derived, repo, br)
    check("a derived gate says no file moves it", "No file moves this gate" in text)
    check("  ...links the file that creates partner issues",
          f"{base}/blob/main/partners.csv" in text)
    check("  ...says a card or a label both work",
          "drag its card" in text and "`status:` label" in text)
    check("  ...and states both thresholds",
          "**In progress when:** 3 partner issues exist." in text
          and "3 partners are marked *Interested*" in text)
    text = requirements({"detection": {"event": "derived_from_partners",
                                       "in_progress_when": "any_running",
                                       "ready_when": "minimum_returned",
                                       "minimum_partners": 3}}, repo, br)
    check("a pathless derived gate still states its thresholds",
          "*Package running*" in text and "3 partners are marked *Results received*" in text
          and "Partner issues come from" not in text)

    body = build_body({"body": "See `TEAM.md`.", "initial_status": "in_progress",
                       "detection": any_gate["detection"]},
                      "org/Factory", 7, repo, br)
    check("a gate that starts open says so", "starts in **In progress**" in body)
    check("the body ends with the reference block",
          "Factory tracking: https://github.com/org/Factory/issues/7" in body)
    check("a push-detected gate says its pushes will be tabled at the top",
          "listed in a table at the top of this issue" in body)
    check("  ...and a derived gate does not",
          "table at the top" not in build_body({"body": "x", "detection": derived["detection"]},
                                               "org/Factory", 7, repo, br))

    real = json.loads(GATES.read_text(encoding="utf-8"))
    rendered = [build_body(g, "org/Factory", 1, repo, br) for g in real["gates"]]
    check("every real template renders a Technical requirements block",
          all("**Technical requirements**" in b for b in rendered))
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
