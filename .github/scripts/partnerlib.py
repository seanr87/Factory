#!/usr/bin/env python3
"""Keep a partner's board column and its status label saying the same thing.

A data partner's status lives in two places that leads can each reach from the
browser: the `Data Partner Status` column on the study board's *Data partners*
view, and the `status:*` label on the partner issue. Factory derives Gates 5
and 6 from the label — but the board is what a lead is most likely to touch,
because dragging a card is what a board invites. Before this module existed
nothing wrote the board field at all, so every partner card sat in the
no-status column, and nothing read it, so dragging a card changed nothing.

The rule: either side may be changed by a person, and Factory brings the other
into step before reading anything.

  - one side empty            fill it from the other
  - both set, disagreeing     the side that changed later wins

"Changed later" is the board value's `updatedAt` against the newest `labeled`
event on the issue. Both are timestamps GitHub already keeps, so no state has
to be stored here to know which of two humans spoke last.
"""

import datetime as dt
import json
import subprocess
import sys

__all__ = ["STATUS_LABELS", "DEFAULT_STATUS", "OPTION_FOR_LABEL",
           "LABEL_FOR_OPTION", "FIELD_NAME", "partner_board",
           "set_board_status", "set_label", "decide", "reconcile"]

FIELD_NAME = "Data Partner Status"

# Label -> board option. The option names are the ones DEPLOYING.md tells an
# installer to create, in this order; the labels are what derive_partner_gates
# and the stall check read.
OPTION_FOR_LABEL = {
    "status:not-contacted": "Not yet contacted",
    "status:contacted": "Contacted",
    "status:interested": "Interested",
    "status:package-running": "Package running",
    "status:results-received": "Results received",
    "status:declined": "Declined",
}
LABEL_FOR_OPTION = {option: label for label, option in OPTION_FOR_LABEL.items()}
STATUS_LABELS = list(OPTION_FOR_LABEL)
DEFAULT_STATUS = "status:not-contacted"


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def _ts(value):
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


# --------------------------------------------------------------------------
# The board
# --------------------------------------------------------------------------

def partner_board(project_id):
    """The study board's partner field and every card's current value.

    Returns None when there is no board, or the board has no `Data Partner
    Status` field — an older study board, or a template somebody retuned.
    Callers treat that as "the board has nothing to say" rather than an error;
    the labels still work on their own.
    """
    if not project_id:
        return None
    raw = gh("api", "graphql", "-f",
             'query=query($p:ID!){node(id:$p){... on ProjectV2{'
             f'field(name:"{FIELD_NAME}")'
             '{... on ProjectV2SingleSelectField{id options{id name}}} '
             'items(first:100){nodes{id content{... on Issue{number}} '
             'fieldValues(first:20){nodes{... on ProjectV2ItemFieldSingleSelectValue{'
             'name updatedAt field{... on ProjectV2SingleSelectField{name}}}}}}}}}}',
             "-f", f"p={project_id}", check=False)
    if not raw:
        return None
    try:
        node = json.loads(raw)["data"]["node"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return None
    if not node or not node.get("field"):
        return None

    items = {}
    for item in node["items"]["nodes"]:
        number = (item.get("content") or {}).get("number")
        if number is None:
            continue
        value = next((v for v in item["fieldValues"]["nodes"]
                      if v.get("field", {}).get("name") == FIELD_NAME), None)
        items[number] = {
            "item_id": item["id"],
            "option": value["name"] if value else None,
            "updated_at": value["updatedAt"] if value else None,
        }
    return {
        "project_id": project_id,
        "field_id": node["field"]["id"],
        "options": {o["name"]: o["id"] for o in node["field"]["options"]},
        "items": items,
    }


def set_board_status(board, item_id, option_name):
    """Move one card to `option_name`. False if the board lacks that option."""
    option_id = board["options"].get(option_name)
    if not option_id:
        print(f"  board: no '{option_name}' option on {FIELD_NAME}; "
              f"have {', '.join(board['options'])}")
        return False
    gh("api", "graphql", "-f",
       "query=mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){updateProjectV2ItemFieldValue("
       "input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}"
       "){projectV2Item{id}}}",
       "-f", f"p={board['project_id']}", "-f", f"i={item_id}",
       "-f", f"f={board['field_id']}", "-f", f"o={option_id}", check=False)
    return True


# --------------------------------------------------------------------------
# The label
# --------------------------------------------------------------------------

def label_changed_at(repo, number, fallback):
    """When the issue's status label last changed; the issue's creation if never."""
    raw = gh("api", f"repos/{repo}/issues/{number}/events", "--paginate",
             "--jq", '.[] | select(.event == "labeled" or .event == "unlabeled") '
                     '| select(.label.name | startswith("status:")) | .created_at',
             check=False)
    stamps = [s for s in raw.split() if s]
    return max(stamps) if stamps else fallback


def set_label(repo, number, new_label, current_labels):
    """Replace whatever status label the issue carries with `new_label`."""
    cmd = ["issue", "edit", str(number), "--repo", repo, "--add-label", new_label]
    stale = [l for l in current_labels if l.startswith("status:") and l != new_label]
    if stale:
        cmd += ["--remove-label", ",".join(stale)]
    gh(*cmd, check=False)


# --------------------------------------------------------------------------
# The decision, kept pure so it can be tested
# --------------------------------------------------------------------------

def decide(label, label_at, option, option_at):
    """What to change so the two sides agree.

    Returns ("label", new_label), ("board", new_option), or None for nothing.
    A label Factory does not recognise counts as no label.
    """
    if label not in OPTION_FOR_LABEL:
        label = None
    if option not in LABEL_FOR_OPTION:
        option = None

    if label is None and option is None:
        return None
    if option is None:
        return ("board", OPTION_FOR_LABEL[label])
    if label is None:
        return ("label", LABEL_FOR_OPTION[option])
    if OPTION_FOR_LABEL[label] == option:
        return None

    board_later = (_ts(option_at) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)) \
        > (_ts(label_at) or dt.datetime.min.replace(tzinfo=dt.timezone.utc))
    if board_later:
        return ("label", LABEL_FOR_OPTION[option])
    return ("board", OPTION_FOR_LABEL[label])


def reconcile(repo, project_id, partners, dry_run=False):
    """Bring every partner's board column and label into step.

    `partners` is derive_partner_gates' list: dicts with number, title, status
    (the label) and created_at. Entries whose label changes are updated in
    place, so the caller derives gates from what the lead most recently said.
    Returns one line per change, for the log.
    """
    board = partner_board(project_id)
    if board is None:
        return []

    changes = []
    for p in partners:
        card = board["items"].get(p["number"])
        if card is None:
            continue  # not on the board; nothing to reconcile against
        label = p.get("status")
        option = card["option"]
        label_at = None
        if label and option and OPTION_FOR_LABEL.get(label) != option:
            # Only pay for the events call when the two actually disagree.
            label_at = label_changed_at(repo, p["number"], p.get("created_at"))
        verdict = decide(label, label_at, option, card["updated_at"])
        if verdict is None:
            continue
        side, value = verdict
        if side == "label":
            changes.append(f"#{p['number']} {p['title']}: label -> {value} "
                           f"(board says {option})")
            if not dry_run:
                set_label(repo, p["number"], value, p.get("labels", []))
            p["status"] = value
        else:
            changes.append(f"#{p['number']} {p['title']}: board -> {value} "
                           f"(label says {label})")
            if not dry_run:
                set_board_status(board, card["item_id"], value)
    return changes


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

def _self_test():
    t0, t1 = "2026-09-01T10:00:00Z", "2026-09-01T11:00:00Z"
    cases = [
        ("every label maps to an option and back",
         all(LABEL_FOR_OPTION[OPTION_FOR_LABEL[l]] == l for l in STATUS_LABELS)),
        ("the default label has an option",
         DEFAULT_STATUS in OPTION_FOR_LABEL),
        ("nothing on either side is nothing to do",
         decide(None, None, None, None) is None),
        ("an empty board is filled from the label",
         decide("status:package-running", t0, None, None) == ("board", "Package running")),
        ("a missing label is filled from the board",
         decide(None, None, "Interested", t0) == ("label", "status:interested")),
        ("agreement is nothing to do",
         decide("status:contacted", t0, "Contacted", t1) is None),
        ("a later board change wins",
         decide("status:contacted", t0, "Interested", t1) == ("label", "status:interested")),
        ("a later label change wins",
         decide("status:interested", t1, "Contacted", t0) == ("board", "Interested")),
        ("an unrecognised label is treated as absent",
         decide("status:whatever", t1, "Declined", t0) == ("label", "status:declined")),
        ("an unrecognised option is treated as absent",
         decide("status:declined", t0, "Maybe", t1) == ("board", "Declined")),
        ("the retired Committed option is not written back to a label",
         decide(None, None, "Committed", t1) is None),
    ]
    failed = [n for n, ok in cases if not ok]
    if failed:
        raise AssertionError("partnerlib self-test failed:\n  " + "\n  ".join(failed))
    return len(cases)


if __name__ == "__main__":
    print(f"partnerlib self-test passed ({_self_test()} cases)")
