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


from factory_issue import read_file, refresh  # noqa: E402
from gate_machine import DONE, READY, evaluate  # noqa: E402
from gatelib import gate_option  # noqa: E402
from sections import heading_lines, normalise, outstanding_sections  # noqa: E402


ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


NEWLINE = chr(10)

GATES = ROOT / ".github" / "data" / "gates.json"


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def now():

    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def fetch_blobs(repo, sha):

    """Blob SHAs for every file at `sha`.


    The whole tree, not just the pushed paths. A gate with `require: all` has to
    answer "is the other required file still identical to the template?" — and
    that file will usually not be in the push being evaluated. Filtering to the
    changed paths made every absent file look deleted.
    """
    tree = json.loads(gh("api", f"repos/{repo}/git/trees/{sha}?recursive=1"))
    return {n["path"]: n["sha"] for n in tree.get("tree", [])
            if n["type"] == "blob"}


def section_state(gates_config, baseline, study_repo, sha, branch="main"):
    """Outstanding sections per gate, for gates that measure completeness.

    Reads the study's file and the template's version of it at the commit the
    study was scaffolded from, so boilerplate the lead never touched does not
    count as written. A file that cannot be read is reported as fully
    outstanding rather than assumed complete.

    Returns (outstanding, links): both keyed by gate number; `links` maps each
    section name to the line of its heading in the live file, so the comment
    can point at exactly where to write rather than just naming the section.
    """
    out, links = {}, {}
    upstream = baseline.get("upstream_template")
    upstream_sha = baseline.get("upstream_sha")

    for gate in gates_config["gates"]:
        detection = gate["detection"]
        if detection.get("require") != "all_sections":
            continue
        required = detection.get("sections", [])
        path = (detection.get("paths") or [None])[0]
        if not path or not required:
            continue

        study_text = read_file(study_repo, path, sha)
        template_text = (read_file(upstream, path, upstream_sha)
                         if upstream and upstream_sha else "")
        if study_text is None:
            out[gate["gate"]] = list(required)
            continue
        out[gate["gate"]] = outstanding_sections(study_text, template_text or "",
                                                  required)
        lines = heading_lines(study_text)
        links[gate["gate"]] = {
            name: f"https://github.com/{study_repo}/blob/{branch}/{path}"
                  f"?plain=1#L{lines[normalise(name)]}"
            for name in required if normalise(name) in lines
        }
    return out, links


def comment(repo, issue, body):

    subprocess.run(

        ["gh", "issue", "comment", str(issue), "--repo", repo, "--body", body],

        check=False, capture_output=True, text=True)


def section_items(decision, links):
    """Outstanding items as list lines; sections link to their line in the file."""
    if not decision.section_mode:
        return [f"- `{p}`" for p in decision.outstanding]
    return [f"- [{s}]({links[s]})" if s in (links or {}) else f"- {s}"
            for s in decision.outstanding]


def evidence_comment(decision, payload, gate_title, links=None):
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
    if decision.supporting:
        lines += ["", "Supporting files also changed:"]
        lines += [f"- `{p}`" for p in decision.supporting]
    if decision.outstanding:
        lines += ["",
                  ("Sections still to write, in case that matters when you "
                   "review this:") if decision.section_mode else
                  ("Still identical to the Strategus template, in case that "
                   "matters when you review this:")]
        lines += section_items(decision, links)
    if decision.ignored:
        lines += ["", "Also changed, for gates already passed:"]
        lines += [f"- gate {g}: " + ", ".join(f"`{p}`" for p in ps)
                  for g, ps in decision.ignored]
    return "\n".join(lines)


def progress_comment(decision, payload, gate_title, links=None):
    """A gate that needs several files, with only some of them done."""
    short = payload["commit_sha"][:7]
    lines = [
        f"**In progress** — {gate_title}",
        "",
        "Factory saw these paths change:",
        "",
    ]
    lines += [f"- `{p}`" for p in decision.evidence]
    lines += [
        "",
        f"in [`{short}`]({payload['commit_url']})"
        + (f" by @{payload['author']}" if payload.get("author") else "")
        + ".",
        "",
        f"**This gate moves to Ready for review once all of the following are "
        f"{'written' if decision.section_mode else 'changed from the Strategus template'}.** "
        f"Still outstanding:",
        "",
    ]
    lines += section_items(decision, links)
    return NEWLINE.join(lines)


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


def update_study_board_status(state, gate_number, status_name="Ready for review"):

    """Move the gate's card on the study's own board.


    On the study board each item is a gate, so the axis that matters is how far

    along that gate is — which is what the Milestones view groups by. The

    portfolio board is the other way round: each item is a whole study, so it

    carries a Gate field instead.


    Best-effort. A board that cannot be written must never fail a gate advance;
    the issue comment and the state file are the record.
    """
    project_id = state.get("study_project_id")
    issue = state.get("gate_issues", {}).get(str(gate_number))
    if not project_id or not issue:
        return


    raw = gh("api", "graphql", "-f",
             "query=query($p:ID!){node(id:$p){... on ProjectV2{"
             "field(name:\"Status\"){... on ProjectV2SingleSelectField{id options{id name}}} "
             "items(first:100){nodes{id content{... on Issue{number}}}}}}}",
             "-f", f"p={project_id}", check=False)
    if not raw:
        return
    try:
        project = json.loads(raw)["data"]["node"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return
    if not project or not project.get("field"):
        print("  study board: no Status field, skipping")
        return


    item = next((i for i in project["items"]["nodes"]
                 if (i.get("content") or {}).get("number") == issue), None)
    if not item:
        print(f"  study board: gate issue #{issue} is not on the board, skipping")
        return


    option = next((o for o in project["field"]["options"]
                   if o["name"].lower() == status_name.lower()), None)
    if not option:
        names = ", ".join(o["name"] for o in project["field"]["options"])
        print(f"  study board: no '{status_name}' option on Status (have: {names})")
        return


    gh("api", "graphql", "-f",
       "query=mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){updateProjectV2ItemFieldValue("
       "input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}"
       "){projectV2Item{id}}}",
       "-f", f"p={project_id}", "-f", f"i={item['id']}",
       "-f", f"f={project['field']['id']}", "-f", f"o={option['id']}", check=False)
    print(f"  study board: gate {gate_number} -> {status_name}")


def update_portfolio_gate(state, gate_title, project_number):

    """Set the study's Gate field on the Factory portfolio board.


    The board previously carried an Objective field from the three-milestone v1

    model, set once at provisioning and never again — so every study sat under

    "Analysis Package Prototype" forever. This is the same idea told truthfully:

    one field, kept current, that the board can group and filter by.


    Best-effort. A board that cannot be updated must not fail a gate advance;
    the issue comment and the state file are the record.
    """
    if not project_number:
        return
    owner = state["factory_repo"].split("/")[0]
    issue = state.get("factory_issue")
    if not issue:
        return


    try:
        data = json.loads(gh(
            "api", "graphql", "-f",
            "query=query($login:String!,$num:Int!){repositoryOwner(login:$login){"
            "... on ProjectV2Owner{projectV2(number:$num){id "
            "field(name:\"Gate\"){... on ProjectV2SingleSelectField{id options{id name}}} "
            "items(first:100){nodes{id content{... on Issue{number}}}}}}}}",
            "-f", f"login={owner}", "-F", f"num={project_number}", check=False))
    except Exception:
        return


    project = ((data.get("data") or {}).get("repositoryOwner") or {}).get("projectV2")

    if not project or not project.get("field"):

        print("  portfolio: no Gate field on the board, skipping")

        return


    item = next((i for i in project["items"]["nodes"]
                 if (i.get("content") or {}).get("number") == issue), None)
    if not item:
        print(f"  portfolio: issue #{issue} is not on the board, skipping")
        return


    option = gate_option(project["field"]["options"], gate_title)
    if not option:
        print(f"  portfolio: no option matching '{gate_title}', skipping")
        return
    if option["name"] != gate_title:
        print(f"  portfolio: option '{option['name']}' is out of date; "
              f"rename it to '{gate_title}' on the board")


    gh("api", "graphql", "-f",
       "query=mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){updateProjectV2ItemFieldValue("
       "input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}"
       "){projectV2Item{id}}}",
       "-f", f"p={project['id']}", "-f", f"i={item['id']}",
       "-f", f"f={project['field']['id']}", "-f", f"o={option['id']}", check=False)
    print(f"  portfolio: Gate set to {gate_title}")


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

    code = apply(payload, state, state_path, baseline, gates_config)

    # Every dispatch, not only an advance. A push that moves no gate can still
    # be someone joining TEAM.md, and the Factory issue is where the
    # coordinating team looks for who is on a study.
    refresh(state, gates_config, activity=payload)
    return code


def apply(payload, state, state_path, baseline, gates_config):
    """Evaluate one push against the study's state and act on the decision."""
    study_repo = payload["study_repo"]
    paths = payload.get("paths", [])

    current_blobs = fetch_blobs(study_repo, payload["commit_sha"]) if paths else {}


    sections, section_links = section_state(gates_config, baseline, study_repo,
                                            payload["commit_sha"],
                                            state.get("default_branch", "main"))
    decision = evaluate(gates_config, baseline, state, paths, current_blobs,
                        section_outstanding=sections)

    print(f"decision: {decision}")

    print(f"reason:   {decision.reason}")


    if not decision.advance and decision.partial_gate is not None:
        # Real work on a gate that needs more than one file. Show it on the board
        # as In Progress and say what is still missing — otherwise a lead who has
        # done half the work sees nothing happen at all.
        target = str(decision.partial_gate)
        rec = state["gates"].setdefault(target, {"status": "not_started",
                                                 "entered_at": None,
                                                 "issue": state["gate_issues"].get(target),
                                                 "evidenced_by": []})
        gate_title = next((g["title"] for g in gates_config["gates"]
                           if g["gate"] == decision.partial_gate),
                          f"Gate {target}")
        already = rec.get("status") == "in_progress"
        same = rec.get("outstanding") == decision.outstanding


        if rec.get("status") not in (READY, DONE):
            rec["status"] = "in_progress"
            rec["outstanding"] = decision.outstanding
            rec["entered_at"] = rec.get("entered_at") or now()
            state_path.write_text(json.dumps(state, indent=2) + NEWLINE, encoding="utf-8")
            update_study_board_status(state, decision.partial_gate, "In progress")


            # Re-comment only when the outstanding set changes. A lead pushing
            # five times while building a specification should not collect five
            # identical comments.
            issue_no = state["gate_issues"].get(target)
            if issue_no and not (already and same):
                comment(study_repo, issue_no,
                        progress_comment(decision, payload, gate_title,
                                         section_links.get(decision.partial_gate)))


            with open(subprocess.os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
                fh.write("advanced=true" + NEWLINE)
                fh.write(f"to_gate={decision.partial_gate}" + NEWLINE)
                fh.write(f"state_path={state_path.relative_to(ROOT).as_posix()}" + NEWLINE)
        print(f"in progress on gate {decision.partial_gate}; "
              f"outstanding: {decision.outstanding}")
        return 0


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
    # Recorded outright, so the export never has to derive it from history.
    rec["ready_at"] = rec.get("ready_at") or stamp
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

        comment(study_repo, gate_issue,
                evidence_comment(decision, payload, gate_title,
                                 section_links.get(decision.to_gate)))

        print(f"commented on {study_repo}#{gate_issue}")


    update_study_board_status(state, decision.to_gate)
    update_portfolio_gate(state, gate_title,
                          subprocess.os.environ.get("FACTORY_PROJECT_NUMBER"))
    print(f"advanced {decision.from_gate} -> {decision.to_gate}")


    with open(subprocess.os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write(f"advanced=true\n")
        fh.write(f"to_gate={decision.to_gate}\n")
        fh.write(f"state_path={state_path.relative_to(ROOT).as_posix()}\n")
    return 0


if __name__ == "__main__":

    sys.exit(main())

