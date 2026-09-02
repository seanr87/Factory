#!/usr/bin/env python3
"""Record gate closures in the state file.

Closing a gate issue is the one thing a human does in this system, and until
now it was the one thing the state file did not record. The board showed it and
the Factory issue fetched it live, but the durable record — the file you would
export to study how studies actually move — had no idea. Anyone asking "how
long do gates sit in review before someone signs off?" had to go back to the
GitHub API and reconstruct it.

So each sweep that already reads state (every push, hourly, daily) also asks
the study repo which gate issues are closed, and writes the answer down:

  status      done
  closed_at   the issue's closedAt, as GitHub recorded it
  ready_at    backfilled from the advance history for gates that reached Ready
              for review before this field existed, so every gate record
              carries all three of its dates in one place

Two rules carried over from the rest of the system:

  a closed gate advances the study    If a human closes Gate 5 while the machine
                                      still has the study at Gate 3, the human
                                      is right. current_gate moves up and the
                                      history says why.
  a reopened gate is awaiting review  A human who reopens an issue is saying the
                                      sign-off was premature. The gate goes back
                                      to Ready for review and records when;
                                      current_gate stays, because gates never
                                      move backward.

An API failure is not "nothing is closed". When the study's issues cannot be
read, nothing is touched.

Usage:
    closures.py --self-test
"""

import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from factory_issue import advanced_at  # noqa: E402

__all__ = ["sync"]

READY, DONE = "ready_for_review", "done"


def _iso(stamp):
    """GitHub's `Z` suffix normalised to the `+00:00` the state files use."""
    return stamp.replace("Z", "+00:00") if stamp else stamp


def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sync(state, closed, now=None):
    """Apply the study's closed gate issues to its state. Returns change lines.

    `closed` is {issue number: closedAt} for every closed gate issue in the
    study repo, or None when that could not be read.
    """
    if closed is None:
        return []
    now = now or _now()
    changes = []

    for key in sorted(state.get("gates", {}), key=int):
        rec = state["gates"][key]
        number = int(key)
        issue = rec.get("issue") or state.get("gate_issues", {}).get(key)

        if rec.get("status") in (READY, DONE) and not rec.get("ready_at"):
            stamp = advanced_at(state, number) or rec.get("entered_at")
            if stamp:
                rec["ready_at"] = stamp
                changes.append(f"gate {number}: ready_at backfilled from history "
                               f"({stamp[:10]})")

        if issue in closed:
            closed_at = _iso(closed[issue])
            if rec.get("status") == DONE and rec.get("closed_at") == closed_at:
                continue
            rec["status"] = DONE
            rec["closed_at"] = closed_at
            rec["entered_at"] = rec.get("entered_at") or closed_at
            changes.append(f"gate {number}: closed {closed_at[:10]}")

            if number > state.get("current_gate", -1):
                state.setdefault("history", []).append({
                    "at": closed_at,
                    "from_gate": state.get("current_gate", -1),
                    "to_gate": number,
                    "commit": None,
                    "evidence": ["gate issue closed by hand"],
                })
                state["current_gate"] = number
                state["gate_entered_at"] = closed_at
                changes.append(f"study advanced to gate {number} by that closure")

        elif rec.get("status") == DONE:
            rec["status"] = READY
            rec["reopened_at"] = now
            rec.pop("closed_at", None)
            changes.append(f"gate {number}: reopened, back to Ready for review")

    return changes


def _self_test():
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    def fresh():
        return {
            "current_gate": 1,
            "gate_entered_at": "2026-07-15T00:00:00+00:00",
            "gates": {
                "0": {"status": READY, "entered_at": "2026-07-01T00:00:00+00:00", "issue": 1},
                "1": {"status": READY, "entered_at": "2026-07-15T00:00:00+00:00", "issue": 2},
                "2": {"status": "in_progress", "entered_at": "2026-07-20T00:00:00+00:00",
                      "issue": 3},
                "5": {"status": "not_started", "entered_at": None, "issue": 6},
            },
            "gate_issues": {"0": 1, "1": 2, "2": 3, "5": 6},
            "history": [{"at": "2026-07-10T00:00:00+00:00", "to_gate": 0},
                        {"at": "2026-07-15T00:00:00+00:00", "to_gate": 1}],
        }

    s = fresh()
    check("an unreadable issue list changes nothing",
          sync(s, None) == [] and s == fresh())

    s = fresh()
    sync(s, {})
    check("ready_at is backfilled from the advance, not first sight",
          s["gates"]["0"]["ready_at"] == "2026-07-10T00:00:00+00:00")
    check("  ...and never for a gate that is not Ready",
          "ready_at" not in s["gates"]["2"])
    check("nothing closed leaves statuses alone",
          s["gates"]["0"]["status"] == READY and s["current_gate"] == 1)

    s = fresh()
    out = sync(s, {1: "2026-08-02T10:00:00Z"})
    g0 = s["gates"]["0"]
    check("a closed issue marks its gate done with the close date",
          g0["status"] == DONE and g0["closed_at"] == "2026-08-02T10:00:00+00:00")
    check("  ...keeping its ready date", g0["ready_at"] == "2026-07-10T00:00:00+00:00")
    check("  ...and says so", any("gate 0: closed 2026-08-02" in c for c in out))
    check("closing a gate at or below the current one does not move the study",
          s["current_gate"] == 1 and len(s["history"]) == 2)
    check("a second sync is quiet",
          all("ready_at" in c for c in sync(s, {1: "2026-08-02T10:00:00Z"})) is True
          and sync(s, {1: "2026-08-02T10:00:00Z"}) == [])

    s = fresh()
    sync(s, {6: "2026-09-01T09:00:00Z"})
    g5 = s["gates"]["5"]
    check("closing a gate the machine never reached still marks it done",
          g5["status"] == DONE and g5["entered_at"] == "2026-09-01T09:00:00+00:00")
    check("  ...without inventing a ready date", "ready_at" not in g5)
    check("  ...and advances the study to it",
          s["current_gate"] == 5 and s["gate_entered_at"] == "2026-09-01T09:00:00+00:00")
    check("  ...with a history entry saying why",
          s["history"][-1]["to_gate"] == 5 and s["history"][-1]["from_gate"] == 1
          and s["history"][-1]["commit"] is None)

    s = fresh()
    sync(s, {1: "2026-08-02T10:00:00Z"})
    out = sync(s, {}, now="2026-08-05T00:00:00+00:00")
    g0 = s["gates"]["0"]
    check("a reopened issue goes back to Ready for review",
          g0["status"] == READY and "closed_at" not in g0
          and g0["reopened_at"] == "2026-08-05T00:00:00+00:00")
    check("  ...and is reported", any("reopened" in c for c in out))

    failed = [n for n, ok in checks if not ok]
    if failed:
        raise AssertionError("closures self-test failed:\n  " + "\n  ".join(failed))
    return len(checks)


if __name__ == "__main__":
    if "--self-test" in sys.argv or len(sys.argv) == 1:
        print(f"closures self-test passed ({_self_test()} cases)")
