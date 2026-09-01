"""Gate state machine — decides whether a push moves a study forward.

Pure decision logic, no network. Everything the workflow knows is passed in and a
decision comes back out, so the rules that matter can be tested without
provisioning a repository.

Three rules from the brief are enforced here rather than in the workflow, because
a rule enforced at the edge is a rule someone eventually routes around:

  advance only      A gate is never moved backward. Evidence for a gate at or
                    below the current one is recorded and otherwise ignored.
  propose, close    Detecting a file is not the same as the file being any good.
                    An evidenced gate reaches `ready_for_review`; only a human
                    moves it to `done`.
  manual gates      Gates 5 and 6 happen outside Git — partner recruitment and
                    site execution — and are never advanced by a push.

The baseline check is what keeps the whole thing honest. Five of the six
auto-detected gates point at files the Strategus template already ships, so
"this path changed" means "its blob differs from what the template gave us",
never "this path exists".
"""

import fnmatch
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0] if "/" in __file__ else ".")

from gatelib import matches  # noqa: E402

__all__ = ["evaluate", "Decision"]

READY = "ready_for_review"
DONE = "done"
NOT_STARTED = "not_started"


class Decision:
    """What the workflow should do about one push."""

    def __init__(self, advance=False, from_gate=None, to_gate=None,
                 evidence=None, reason="", ignored=None, outstanding=None,
                 supporting=None, partial_gate=None):
        self.advance = advance
        self.from_gate = from_gate
        self.to_gate = to_gate
        self.evidence = evidence or []
        self.reason = reason
        # Evidence that matched a gate but did not move anything. Reported in the
        # issue comment so a lead can see their work was noticed even when the
        # board does not move.
        self.ignored = ignored or []
        # Required paths still identical to the template. On an advance this tells
        # the reviewer what is genuinely done; on a hold it tells the lead what is
        # still needed. Either way the human closing the gate is the one who needs
        # it, and "something changed" alone does not give it to them.
        self.outstanding = outstanding or []
        # Supporting paths that changed. Never sufficient alone.
        self.supporting = supporting or []
        # The gate a require:all push made progress on without completing.
        self.partial_gate = partial_gate

    def __repr__(self):
        if self.advance:
            return (f"<Decision advance {self.from_gate}->{self.to_gate} "
                    f"on {self.evidence}>")
        return f"<Decision hold ({self.reason})>"


def _current_gate(state):
    """Highest gate the study has reached. -1 before Gate 0."""
    reached = [int(g) for g, rec in state.get("gates", {}).items()
               if rec.get("status") in (READY, DONE)]
    return max(reached) if reached else -1


def _gates_for_path(gates_config, path, key="paths"):
    """Every gate whose detection paths match this path."""
    hits = []
    for gate in gates_config["gates"]:
        detection = gate["detection"]
        if detection.get("event") != "content_changed":
            continue  # manual or advisory — never advanced by a push
        for pattern in detection.get(key, []):
            if matches(pattern, path):
                hits.append((gate["gate"], pattern))
                break
    return hits


def _gate_by_number(gates_config, number):
    return next((g for g in gates_config["gates"] if g["gate"] == number), None)


def _changed(path, baseline_blobs, current_blobs):
    """True if `path` differs from what the template shipped."""
    now, was = current_blobs.get(path), baseline_blobs.get(path)
    if now is None and was is None:
        return False          # never existed
    if now is None or was is None:
        return True           # added or deleted
    return now != was


def _unsatisfied(gate, baseline_blobs, current_blobs):
    """Required patterns for `gate` with nothing changed against them."""
    out = []
    for pattern in gate["detection"].get("paths", []):
        known = set(baseline_blobs) | set(current_blobs)
        if not any(matches(pattern, p) and _changed(p, baseline_blobs, current_blobs)
                   for p in known):
            out.append(pattern)
    return out


def evaluate(gates_config, baseline, state, changed_paths, current_blobs):
    """Decide whether `changed_paths` moves this study forward.

    gates_config  parsed .github/data/gates.json
    baseline      {path: blob_sha} recorded when the study was scaffolded
    state         this study's stored gate state
    changed_paths paths the study repo reported as changed
    current_blobs {path: blob_sha} for those paths as they are now.
                  A path absent from this map was deleted.

    A gate whose detection says `require: all` needs every one of its required
    paths to differ from the template before it advances. Partial work still
    counts for something: the gate is reported as in progress, with the paths
    still outstanding, so the board shows work happening rather than nothing.
    """
    baseline_blobs = baseline.get("blobs", {})
    current = _current_gate(state)

    evidenced = {}    # gate -> [paths] that changed against a required pattern
    supporting = {}   # gate -> [paths] that changed against a supporting pattern
    unchanged = []    # matched a gate, but identical to the template baseline

    for path in changed_paths:
        if not _changed(path, baseline_blobs, current_blobs):
            if _gates_for_path(gates_config, path) or                _gates_for_path(gates_config, path, "supporting_paths"):
                unchanged.append(path)
            continue
        for gate_no, _p in _gates_for_path(gates_config, path):
            evidenced.setdefault(gate_no, []).append(path)
        for gate_no, _p in _gates_for_path(gates_config, path, "supporting_paths"):
            supporting.setdefault(gate_no, []).append(path)

    touched = set(evidenced) | set(supporting)
    if not touched:
        reason = ("no gate paths changed" if not unchanged else
                  f"{len(unchanged)} path(s) matched a gate but are unchanged "
                  f"from the template baseline")
        return Decision(reason=reason)

    # Which touched gates are actually complete?
    complete, partial = [], []
    for gate_no in sorted(touched):
        gate = _gate_by_number(gates_config, gate_no)
        if gate is None:
            continue
        outstanding = _unsatisfied(gate, baseline_blobs, current_blobs)
        requires_all = gate["detection"].get("require", "any") == "all"
        if requires_all:
            (complete if not outstanding else partial).append((gate_no, outstanding))
        elif gate_no in evidenced:
            complete.append((gate_no, outstanding))
        else:
            # Only supporting paths changed on an any-gate: progress, not evidence.
            partial.append((gate_no, outstanding))

    ahead = [(g, o) for g, o in complete if g > current]
    if ahead:
        target, outstanding = max(ahead)
        return Decision(
            advance=True,
            from_gate=current,
            to_gate=target,
            evidence=sorted(evidenced.get(target, []) or supporting.get(target, [])),
            reason=f"gate {target} evidenced by "
                   f"{len(evidenced.get(target, []) or supporting.get(target, []))} changed path(s)",
            ignored=[(g, p) for g, p in sorted(evidenced.items()) if g != target],
            outstanding=outstanding,
            supporting=sorted(supporting.get(target, [])),
        )

    ahead_partial = [(g, o) for g, o in partial if g > current]
    if ahead_partial:
        gate_no, outstanding = min(ahead_partial)
        changed_here = sorted(set(evidenced.get(gate_no, []))
                              | set(supporting.get(gate_no, [])))
        return Decision(
            reason=f"gate {gate_no} in progress — "
                   f"{len(outstanding)} required path(s) still unchanged",
            partial_gate=gate_no,
            evidence=changed_here,
            outstanding=outstanding,
            supporting=sorted(supporting.get(gate_no, [])),
        )

    return Decision(
        reason=(f"evidence for gate {max(touched)}, but the study is already at "
                f"gate {current} — advance only, never retreat"),
        ignored=[(g, p) for g, p in sorted(evidenced.items())],
    )


# --------------------------------------------------------------------------
# Self-test. These are the rules that must not regress.
# --------------------------------------------------------------------------

def _fixture_config():
    return {
        "gates": [
            {"gate": 0, "detection": {"event": "content_changed",
                                      "paths": ["TEAM.md"]}},
            {"gate": 2, "detection": {"event": "content_changed",
                                      "paths": ["Documents/Protocol.Rmd"]}},
            {"gate": 3, "detection": {"event": "content_changed",
                                      "paths": ["inst/cohorts/**/*.json",
                                                "inst/Cohorts.csv"]}},
            {"gate": 4, "detection": {"event": "content_changed",
                                      "require": "all",
                                      "paths": ["spec.R", "spec.json"],
                                      "supporting_paths": ["negativeControls.csv"]}},
            {"gate": 5, "detection": {"event": "advisory_only",
                                      "paths": ["partners.csv"]}},
            {"gate": 6, "detection": {"event": "none"}},
        ]
    }


def _self_test():
    cfg = _fixture_config()
    base = {"blobs": {"Documents/Protocol.Rmd": "aaa",
                      "inst/Cohorts.csv": "bbb",
                      "inst/cohorts/11.json": "ccc"}}
    empty = {"gates": {}}
    at3 = {"gates": {"0": {"status": DONE}, "3": {"status": READY}}}
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    # Baseline guard: the template's own files must not evidence anything.
    d = evaluate(cfg, base, empty,
                 ["Documents/Protocol.Rmd", "inst/Cohorts.csv"],
                 {"Documents/Protocol.Rmd": "aaa", "inst/Cohorts.csv": "bbb"})
    check("unchanged template files do not advance", not d.advance)

    # A real edit to a template-shipped file does evidence its gate.
    d = evaluate(cfg, base, empty, ["Documents/Protocol.Rmd"],
                 {"Documents/Protocol.Rmd": "zzz"})
    check("edited Protocol.Rmd advances to gate 2", d.advance and d.to_gate == 2)

    # Overlay files have no baseline; any change is the lead's.
    d = evaluate(cfg, base, empty, ["TEAM.md"], {"TEAM.md": "new"})
    check("TEAM.md advances to gate 0", d.advance and d.to_gate == 0)

    # Advance only.
    d = evaluate(cfg, base, at3, ["TEAM.md"], {"TEAM.md": "newer"})
    check("gate 0 evidence does not retreat from gate 3",
          not d.advance and "advance only" in d.reason)

    # Highest gate wins when a push spans several.
    d = evaluate(cfg, base, empty,
                 ["TEAM.md", "inst/cohorts/11.json"],
                 {"TEAM.md": "x", "inst/cohorts/11.json": "changed"})
    check("highest evidenced gate is taken", d.advance and d.to_gate == 3)

    # Manual gates are never advanced by a push.
    d = evaluate(cfg, base, empty, ["partners.csv"], {"partners.csv": "x"})
    check("partners.csv does not advance gate 5", not d.advance)

    # Irrelevant paths do nothing.
    d = evaluate(cfg, base, empty, ["README.md", "renv.lock"],
                 {"README.md": "x", "renv.lock": "y"})
    check("unrelated paths do not advance", not d.advance)

    # Deleting a template file still counts as a change.
    d = evaluate(cfg, base, empty, ["inst/Cohorts.csv"], {})
    check("deleted file counts as changed", d.advance and d.to_gate == 3)

    # Glob nesting, the bug that shipped once already.
    d = evaluate(cfg, base, empty, ["inst/cohorts/99.json"],
                 {"inst/cohorts/99.json": "new"})
    check("new cohort json matches the ** pattern", d.advance and d.to_gate == 3)

    # require: all — the rule Gate 4 uses.
    base4 = {"blobs": {"spec.R": "r0", "spec.json": "j0",
                       "negativeControls.csv": "n0"}}
    full = lambda **over: {**base4["blobs"], **over}
    d = evaluate(cfg, base4, empty, ["spec.R"], full(**{"spec.R": "r1"}))
    check("one of two required paths does not advance", not d.advance)
    check("  ...and reports the gate as in progress", d.partial_gate == 4)
    check("  ...naming what is outstanding", d.outstanding == ["spec.json"])

    d = evaluate(cfg, base4, empty, ["spec.R", "spec.json"],
                 full(**{"spec.R": "r1", "spec.json": "j1"}))
    check("both required paths advance to gate 4", d.advance and d.to_gate == 4)
    check("  ...with nothing outstanding", d.outstanding == [])

    # A supporting path is progress, never evidence on its own.
    d = evaluate(cfg, base4, empty, ["negativeControls.csv"],
                 full(**{"negativeControls.csv": "n1"}))
    check("supporting path alone does not advance", not d.advance)
    check("  ...but is reported as progress", d.partial_gate == 4)

    # The second required path arriving later completes it.
    part = {"gates": {}}
    d = evaluate(cfg, base4, part, ["spec.json"],
                 full(**{"spec.json": "j1", "spec.R": "r1"}))
    check("completing the pair later advances", d.advance and d.to_gate == 4)

    failed = [n for n, ok in checks if not ok]
    if failed:
        raise AssertionError("gate_machine self-test failed:\n  " +
                             "\n  ".join(failed))
    return len(checks)


if __name__ == "__main__":
    print(f"gate_machine self-test passed ({_self_test()} cases)")
