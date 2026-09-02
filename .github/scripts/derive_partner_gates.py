#!/usr/bin/env python3
"""Advance the partner-derived gates from partner issue labels.

Gates 5 and 6 are the two phases that happen outside this system. Recruitment is
conversations with colleagues at other institutions; execution is packages running
on machines Factory will never see, against data it will never touch. Neither
leaves a trace in the repository, so the only evidence that reaches GitHub is the
status label on each partner issue.

Each gate declares its own rules in front matter rather than having them written
here, so changing when a gate moves is a template edit:

    in_progress_when: any_partner | any_returned
    ready_when:       any_committed | all_committed_returned

This is also where gate closures are written into the state file (see
closures.py): it is the one sweep that runs on every push, every hour, and
every morning, and already commits what it changes.

Like every other advance in this system these propose rather than conclude. A
label records what somebody said; it cannot tell you a result set is complete, or
that you have enough partners for the study to be worth running. Both of those
are checks the gates themselves ask a human to make.
"""

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import closures  # noqa: E402
from factory_issue import gate_issue_states, refresh  # noqa: E402
from partnerlib import reconcile  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
GATES = ROOT / ".github" / "data" / "gates.json"
NEWLINE = chr(10)

READY = "ready_for_review"
IN_PROGRESS = "in_progress"
DONE = "done"

RETURNED = "status:results-received"
# Anyone who agreed to run it. A site that has returned results was committed
# whether or not anybody moved its label through every intermediate state.
COMMITTED = {"status:committed", "status:package-running", RETURNED}
# A site that said no should not hold a study back.
INACTIVE = {"status:declined"}

BOARD_NAME = {READY: "Ready for review", IN_PROGRESS: "In progress"}


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:" + NEWLINE + r.stderr.strip())
    return r.stdout.strip()


ISSUE_FIELDS = "number,title,labels,createdAt,state"


def partner_record(issue):
    labels = [l["name"] for l in issue.get("labels", [])]
    status = next((l for l in labels if l.startswith("status:")), None)
    return {"number": issue["number"],
            "title": issue["title"].replace("Data partner — ", ""),
            "status": status,
            "labels": labels,
            "created_at": issue.get("createdAt")}


def merge_partners(listed, expected, fetch):
    """Every open partner issue: the listing, plus any expected issue it missed.

    GitHub's issue listing can lag a just-created issue by a second or so. The
    sync that runs before this on a push creates issues and then names them,
    and this fetches any of those the listing left out — by number, which does
    not lag — so Gate 5 never reports two partners when the CSV has three.
    fetch(number) returns the raw issue or None.
    """
    out = [partner_record(i) for i in listed]
    seen = {p["number"] for p in out}
    for number in expected:
        if number in seen:
            continue
        issue = fetch(number)
        if not issue or issue.get("state", "OPEN").upper() != "OPEN":
            continue
        if "partner" not in {l["name"] for l in issue.get("labels", [])}:
            continue
        out.append(partner_record(issue))
        seen.add(number)
    return out


def partner_states(repo, expected=()):
    raw = gh("issue", "list", "--repo", repo, "--label", "partner",
             "--state", "open", "--limit", "200",
             "--json", ISSUE_FIELDS, check=False)
    listed = json.loads(raw) if raw else []

    def fetch(number):
        raw = gh("issue", "view", str(number), "--repo", repo,
                 "--json", ISSUE_FIELDS, check=False)
        return json.loads(raw) if raw else None

    return merge_partners(listed, expected, fetch)


def parse_expected(text):
    """'9,10,11' -> [9, 10, 11]; blanks and junk ignored."""
    out = []
    for piece in (text or "").split(","):
        piece = piece.strip().lstrip("#")
        if piece.isdigit():
            out.append(int(piece))
    return out


def assess(partners):
    active = [p for p in partners if p["status"] not in INACTIVE]
    committed = [p for p in partners if p["status"] in COMMITTED]
    returned = [p for p in partners if p["status"] == RETURNED]
    return active, committed, returned


def gate_state(rules, partners):
    """The state a partner-derived gate should be in, and why.

    Returns (status, reason). status is READY, IN_PROGRESS, or None meaning
    leave the gate alone.
    """
    active, committed, returned = assess(partners)

    minimum = rules.get("minimum_partners", 1)

    if rules.get("ready_when") == "all_committed_returned":
        if committed and len(returned) == len(committed) and len(returned) >= minimum:
            return READY, (f"all {len(committed)} committed partner(s) have "
                           f"returned results")
    elif rules.get("ready_when") == "minimum_committed":
        if len(committed) >= minimum:
            return READY, (f"{len(committed)} partner(s) have committed to "
                           f"running the study")
    elif rules.get("ready_when") == "any_committed":
        if committed:
            return READY, (f"{len(committed)} partner(s) have committed to "
                           f"running the study")

    if rules.get("in_progress_when") == "any_returned" and returned:
        short = (f", {minimum} needed for a network study"
                 if len(returned) < minimum else "")
        return IN_PROGRESS, (f"{len(returned)} of {len(committed)} committed "
                             f"partner(s) have returned results{short}")
    if rules.get("in_progress_when") == "any_partner" and active:
        detail = (f"{len(committed)} committed of {minimum} needed"
                  if committed else "none committed yet")
        return IN_PROGRESS, (f"{len(active)} partner(s) being tracked, {detail}")

    return None, "nothing to report"


def roster(partners):
    """Where each partner stands, for the comment."""
    lines = []
    for p in sorted(partners, key=lambda x: x["title"]):
        status = (p["status"] or "status:unknown").replace("status:", "").replace("-", " ")
        lines.append(f"- {p['title']} — {status}")
    return lines


def comment_body(gate_title, status, reason, partners):
    head = "**Moved to Ready for review**" if status == READY else "**In progress**"
    lines = [f"{head} — {gate_title}", "", reason[0].upper() + reason[1:] + ".", ""]
    lines += roster(partners)
    lines += [
        "",
        "Factory read this from each partner's status — its column on the board's "
        "Data partners view and the `status:` label on its issue, kept in step — "
        "not from anything in the repository. This phase happens outside GitHub "
        "entirely.",
    ]
    if status == READY:
        lines += [
            "",
            "Confirm this is genuinely complete before closing. A label records "
            "what somebody said; it cannot tell you a result set is whole, or "
            "that you have enough partners for the study to be worth running.",
        ]
    return NEWLINE.join(lines)


def update_study_board(state, gate_number, status_name):
    """Move the gate's card on the study's own board. Best-effort."""
    project_id = state.get("study_project_id")
    issue = state.get("gate_issues", {}).get(str(gate_number))
    if not project_id or not issue:
        return

    raw = gh("api", "graphql", "-f",
             'query=query($p:ID!){node(id:$p){... on ProjectV2{'
             'field(name:"Status"){... on ProjectV2SingleSelectField{id options{id name}}} '
             'items(first:100){nodes{id content{... on Issue{number}}}}}}}',
             "-f", f"p={project_id}", check=False)
    if not raw:
        return
    try:
        project = json.loads(raw)["data"]["node"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return
    if not project or not project.get("field"):
        return

    item = next((i for i in project["items"]["nodes"]
                 if (i.get("content") or {}).get("number") == issue), None)
    option = next((o for o in project["field"]["options"]
                   if o["name"].lower() == status_name.lower()), None)
    if not item or not option:
        return

    gh("api", "graphql", "-f",
       "query=mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){updateProjectV2ItemFieldValue("
       "input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}"
       "){projectV2Item{id}}}",
       "-f", f"p={project_id}", "-f", f"i={item['id']}",
       "-f", f"f={project['field']['id']}", "-f", f"o={option['id']}", check=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=".github/data/state")
    ap.add_argument("--study", default="", help="limit to one study repo")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--expect", default="",
                    help="comma-separated partner issue numbers that must be "
                         "included even if the listing has not caught up "
                         "(only meaningful with --study)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    expected = parse_expected(args.expect)

    gates_config = json.loads(GATES.read_text(encoding="utf-8"))
    derived = [g for g in gates_config["gates"]
               if g["detection"].get("event") == "derived_from_partners"]
    if not derived:
        print("No partner-derived gates configured.")
        return 0

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

        # Closures first, so a gate a human has signed off is recorded — with
        # its date — before anything below could propose it again. This is the
        # one sweep that runs on every trigger, which is why it lives here.
        closure_changes = closures.sync(state, gate_issue_states(
            repo, state.get("gate_issues", {})))
        for change in closure_changes:
            print(f"  {repo}: {change}")
        dirty = bool(closure_changes)

        partners = partner_states(repo, expected if args.study else ())
        if partners:
            # A lead may have dragged a card on the board or changed a label.
            # Bring the two into step before reading either, so the gates are
            # derived from whatever the lead most recently said.
            for change in reconcile(repo, state.get("study_project_id"), partners,
                                    dry_run=args.dry_run):
                print(f"  {repo}: {change}")
        else:
            print(f"  {repo}: no partner issues")

        for gate in sorted(derived, key=lambda g: g["gate"]):
            number = gate["gate"]
            status, reason = gate_state(gate["detection"], partners)
            if status is None:
                continue

            rec = state["gates"].setdefault(str(number), {
                "status": "not_started", "entered_at": None,
                "issue": state["gate_issues"].get(str(number)),
                "evidenced_by": []})

            # Never undo a human's close, never walk a gate back from Ready for
            # review to In progress, and never re-comment on an unchanged state.
            if rec.get("status") == DONE:
                continue
            if rec.get("status") == READY and status == IN_PROGRESS:
                continue
            if rec.get("status") == status and rec.get("reason") == reason:
                continue

            print(f"  {repo}: gate {number} -> {status} ({reason})")
            if args.dry_run:
                continue

            stamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
            rec["status"] = status
            rec["reason"] = reason
            rec["entered_at"] = rec.get("entered_at") or stamp
            if status == READY:
                rec["ready_at"] = rec.get("ready_at") or stamp
            rec["evidenced_by"] = [f"{p['title']}: {p['status']}" for p in partners]
            state["gates"][str(number)] = rec
            dirty = True

            # Only a Ready gate moves the study forward. In progress is a
            # statement about one gate, not about where the study has reached.
            if status == READY and number > state.get("current_gate", -1):
                state["history"].append({
                    "at": stamp,
                    "from_gate": state.get("current_gate", -1),
                    "to_gate": number,
                    "commit": None,
                    "evidence": [p["title"] for p in partners
                                 if p["status"] == RETURNED] or None,
                })
                state["current_gate"] = number
                state["gate_entered_at"] = stamp

            update_study_board(state, number, BOARD_NAME[status])
            issue_no = state["gate_issues"].get(str(number))
            if issue_no:
                subprocess.run(
                    ["gh", "issue", "comment", str(issue_no), "--repo", repo,
                     "--body", comment_body(gate["title"], status, reason, partners)],
                    check=False, capture_output=True, text=True)

        if dirty and not args.dry_run:
            path.write_text(json.dumps(state, indent=2) + NEWLINE, encoding="utf-8")
            changed.append(repo)

        # The Factory issue lists every partner with its status, so a card a
        # lead dragged shows there within the hour even when no gate moved.
        if not args.dry_run:
            refresh(state, gates_config)

    out = subprocess.os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(("changed=true" if changed else "changed=false") + NEWLINE)
            fh.write("changed_studies=" + ",".join(changed) + NEWLINE)
    return 0


def self_test():
    def issue(n, title, labels, state="OPEN"):
        return {"number": n, "title": f"Data partner — {title}",
                "labels": [{"name": l} for l in labels],
                "createdAt": "2026-09-02T13:15:18Z", "state": state}

    store = {
        9: issue(9, "Sugar Man University", ["partner", "status:not-contacted"]),
        10: issue(10, "Candyland", ["partner", "status:not-contacted"]),
        11: issue(11, "Cape Town University", ["partner", "status:not-contacted"]),
        12: issue(12, "Closed U", ["partner", "status:declined"], state="CLOSED"),
        13: issue(13, "Not a partner", ["work-item"]),
    }
    fetched = []

    def fetch(n):
        fetched.append(n)
        return store.get(n)

    # The listing missed #11 (the case that produced "2 partner(s)" for 3).
    got = merge_partners([store[9], store[10]], [9, 10, 11], fetch)
    assert [p["number"] for p in got] == [9, 10, 11], got
    assert got[2]["title"] == "Cape Town University"
    assert got[2]["status"] == "status:not-contacted"
    assert fetched == [11], fetched  # listed issues are not re-fetched

    # Nothing expected: plain listing, no fetches.
    fetched.clear()
    got = merge_partners([store[9]], [], fetch)
    assert [p["number"] for p in got] == [9] and fetched == []

    # Expected but closed, unlabelled, or gone: left out, not crashed on.
    got = merge_partners([], [12, 13, 99], fetch)
    assert got == [], got

    # Listing empty and everything expected: all fetched.
    got = merge_partners([], [9, 10, 11], fetch)
    assert [p["number"] for p in got] == [9, 10, 11]

    assert parse_expected("9,10,11") == [9, 10, 11]
    assert parse_expected(" #9, ,x,11 ") == [9, 11]
    assert parse_expected("") == []

    # Gate 5 reads three partners as three.
    rules = {"in_progress_when": "any_partner", "ready_when": "minimum_committed",
             "minimum_partners": 3}
    status, reason = gate_state(rules, got)
    assert status == IN_PROGRESS and reason.startswith("3 partner(s)"), reason

    print("derive_partner_gates self-test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
