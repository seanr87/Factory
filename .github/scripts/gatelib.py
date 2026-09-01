"""Shared path-matching for gate detection.

Every place that decides "does this changed file evidence a gate?" must answer
identically — the baseline capture at provisioning, the daily path-contract check,
and the gate state machine. When they disagree, a study either advances on nothing
or sits still while the lead does everything right. So the matcher lives here once.

The subtlety this exists to handle: `fnmatch` translates `**` to `.*`, so the
conventional pattern `inst/cohorts/**/*.json` compiles to something requiring an
intermediate directory and does NOT match `inst/cohorts/11.json` — which is exactly
where upstream keeps its cohort definitions. Patterns are therefore expanded into
variants before matching, so `/**/` means "zero or more directories", as everyone
writing the pattern expects.
"""

import fnmatch

__all__ = ["variants", "matches", "expand", "gate_option"]


def variants(pattern):
    """Pattern variants to try, so `/**/` means zero-or-more directories."""
    out = [pattern]
    if "/**/" in pattern:
        out.append(pattern.replace("/**/", "/"))
    if pattern.endswith("/**"):
        out.append(pattern[: -len("/**")])
    return out


def matches(pattern, path):
    """True if `path` is matched by `pattern`."""
    return any(fnmatch.fnmatch(path, v) for v in variants(pattern))


def expand(pattern, paths):
    """Every path in `paths` matched by `pattern`."""
    return [p for p in paths if matches(pattern, p)]


def gate_option(options, title):
    """The board's single-select option for a gate title, tolerating a rename.

    Exact match first. Failing that, the option that shares the gate's number
    ("Gate 1 — ..."), so renaming a gate in its template does not silently stop
    the portfolio board's Gate field updating until somebody remembers to rename
    the option to match. Options without a gate number ("Complete") never match
    by prefix.
    """
    exact = next((o for o in options if o["name"] == title), None)
    if exact:
        return exact
    prefix = title.split(" — ")[0]
    if not prefix.startswith("Gate "):
        return None
    return next((o for o in options if o["name"].split(" — ")[0] == prefix), None)


def _self_test():
    """Guards the `/**/` behaviour this module exists for, and option matching."""
    options = [{"name": "Gate 0 — Get oriented in GitHub"},
               {"name": "Gate 1 — Research question locked"},
               {"name": "Complete"}]
    option_cases = [
        ("Gate 0 — Get oriented in GitHub", "Gate 0 — Get oriented in GitHub"),
        ("Gate 1 — Research question developed", "Gate 1 — Research question locked"),
        ("Gate 9 — Nothing", None),
        ("Complete", "Complete"),
    ]
    option_failures = [
        f"  gate_option({title!r}): expected {want!r}, got {got!r}"
        for title, want in option_cases
        for got in [(gate_option(options, title) or {}).get("name")]
        if got != want
    ]
    if option_failures:
        raise AssertionError("gatelib self-test failed:\n" + "\n".join(option_failures))
    cases = [
        # (pattern, path, expected)
        ("inst/cohorts/**/*.json", "inst/cohorts/11.json", True),
        ("inst/cohorts/**/*.json", "inst/cohorts/nested/11.json", True),
        ("inst/cohorts/**/*.json", "inst/Cohorts.csv", False),
        ("inst/sql/sql_server/**/*.sql", "inst/sql/sql_server/11.sql", True),
        ("inst/sql/sql_server/**/*.sql", "inst/sql/postgres/11.sql", False),
        ("Documents/Protocol.Rmd", "Documents/Protocol.Rmd", True),
        ("Documents/Protocol.Rmd", "Documents/Protocol.bib", False),
        ("TEAM.md", "TEAM.md", True),
        ("results/**", "results/main/x.csv", True),
    ]
    failures = [
        f"  {pattern!r} vs {path!r}: expected {want}, got {matches(pattern, path)}"
        for pattern, path, want in cases
        if matches(pattern, path) is not want
    ]
    if failures:
        raise AssertionError("gatelib self-test failed:\n" + "\n".join(failures))
    return len(cases) + len(option_cases)


if __name__ == "__main__":
    print(f"gatelib self-test passed ({_self_test()} cases)")
