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

__all__ = ["variants", "matches", "expand"]


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


def _self_test():
    """Guards the `/**/` behaviour this module exists for."""
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
    return len(cases)


if __name__ == "__main__":
    print(f"gatelib self-test passed ({_self_test()} cases)")
