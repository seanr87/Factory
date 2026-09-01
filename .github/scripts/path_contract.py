#!/usr/bin/env python3
"""Check gate detection paths against upstream, and say exactly how to fix a break.

Detection is a contract with the upstream Strategus template's file layout. That
layout has moved twice in nine months, and either move would have silently broken
Gate 3 and Gate 4 for every study provisioned afterwards.

Reporting "something broke" is not much use at 07:00 on a Tuesday. So when a path
stops matching, this looks through upstream for where the file most likely went,
and writes an issue that names the file to edit, the key to change, the value to
change it to, and the command to run afterwards. Someone still decides — a
plausible rename is not a confirmed one — but they decide with the work already
laid out.

Usage:
    path_contract.py --factory-repo owner/Factory [--upstream owner/repo] [--dry-run]
"""

import argparse
import json
import pathlib
import posixpath
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gatelib import expand, matches  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
GATES = ROOT / ".github" / "data" / "gates.json"
TEMPLATE_DIR = ".github/issue-templates"


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


# ---------------------------------------------------------------------------
# Working out where a file probably went
# ---------------------------------------------------------------------------

def _tail(pattern):
    """The filename part of a pattern: 'inst/cohorts/**/*.json' -> '*.json'."""
    return posixpath.basename(pattern)


def _dir_similarity(a, b):
    """Shared leading path segments, as a fraction of the longer path."""
    sa, sb = a.split("/")[:-1], b.split("/")[:-1]
    if not sa and not sb:
        return 1.0
    shared = 0
    for x, y in zip(sa, sb):
        if x.lower() == y.lower():
            shared += 1
        else:
            break
    return shared / max(len(sa), len(sb), 1)


def candidates(pattern, paths):
    """Ranked guesses at where `pattern` moved to. [(path, confidence, why)]."""
    tail = _tail(pattern)
    out = []

    if "*" not in tail:
        # A concrete filename. The same name elsewhere in the tree is the
        # overwhelmingly likely answer — that is what a directory move looks like.
        for p in paths:
            base = posixpath.basename(p)
            if base == tail:
                out.append((p, "high", "same filename, moved directory"))
            elif base.lower() == tail.lower():
                out.append((p, "high", "same filename, different case"))
            elif base.lower().replace("s.", ".") == tail.lower().replace("s.", "."):
                out.append((p, "medium", "filename differs only by pluralisation"))

        if not out:
            stem, ext = posixpath.splitext(tail)
            for p in paths:
                pstem, pext = posixpath.splitext(posixpath.basename(p))
                if pext != ext:
                    continue
                # Same extension, and one name contains the other: a rename that
                # kept the recognisable part (Cohorts.csv -> CohortsToCreate.csv).
                if stem.lower() in pstem.lower() or pstem.lower() in stem.lower():
                    sim = _dir_similarity(pattern, p)
                    out.append((p, "medium" if sim > 0.5 else "low",
                                "same extension, similar name"))
    else:
        # A glob. Look for directories now holding files that match its tail.
        dirs = {}
        for p in paths:
            if matches(tail, posixpath.basename(p)):
                dirs.setdefault(posixpath.dirname(p), []).append(p)
        for d, hits in dirs.items():
            sim = _dir_similarity(pattern + "/x", d + "/x")
            conf = "high" if sim >= 0.5 else "medium" if sim > 0 else "low"
            suggestion = f"{d}/{tail}" if d else tail
            out.append((suggestion, conf,
                        f"{len(hits)} file(s) matching `{tail}` live here now"))

    rank = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda c: (rank[c[1]], c[0]))
    return out[:4]


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

def prose_mentions(template_path, pattern):
    """Lines in the gate's prose that name this path, which also need editing."""
    f = ROOT / template_path
    if not f.exists():
        return []
    needle = _tail(pattern) if "*" in pattern else pattern
    hits = []
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith(("gate:", "paths:", "- \"", "  paths")):
            continue
        if needle and needle.strip("*") and needle.strip("*") in line:
            hits.append((i, line.strip()))
    return hits[:3]


def build_issue(broken, upstream, head, factory_repo, checked):
    sha, date = head["sha"], head["date"]
    short = sha[:7]

    L = []
    L.append(f"The upstream Strategus template has changed. **{len(broken)} of {checked} "
             "detection paths no longer match anything upstream.**")
    L.append("")
    L.append(f"Upstream: [`{short}`](https://github.com/{upstream}/commit/{sha}) — committed {date}")
    L.append("")
    L.append("## Impact")
    L.append("")
    gates_hit = sorted({g for g, _, _, _ in broken})
    L.append(f"Studies **provisioned from now on** will not advance through "
             f"{'Gate ' + ', Gate '.join(str(g) for g in gates_hit)}.")
    L.append("")
    L.append("Studies already provisioned are unaffected: each one's baseline in "
             "`.github/data/baselines/` records the upstream commit it was scaffolded "
             "from, and detection matches against paths that exist in that repository. "
             "A rename upstream does not reach backwards into a repo already created.")
    L.append("")
    L.append("**Do not provision new studies until this is resolved.**")
    L.append("")
    L.append("## What broke, and the likely fix")
    L.append("")
    L.append("| Gate | Current pattern | Likely replacement | Confidence | Why |")
    L.append("|---|---|---|---|---|")
    for gate, title, pattern, cands in broken:
        if cands:
            path, conf, why = cands[0]
            L.append(f"| {gate} | `{pattern}` | `{path}` | {conf} | {why} |")
        else:
            L.append(f"| {gate} | `{pattern}` | — none found | — | "
                     "the file may have been removed outright |")
    L.append("")

    L.append("## What to change")
    L.append("")
    for gate, title, pattern, cands in broken:
        tmpl = next((g["template"] for g in json.loads(GATES.read_text(encoding="utf-8"))["gates"]
                     if g["gate"] == gate), f"{TEMPLATE_DIR}/gate-{gate}-*.md")
        L.append(f"### {title}")
        L.append("")
        L.append(f"**File:** `{tmpl}`")
        L.append("")
        L.append(f"In the front matter, under `detection.paths`, replace:")
        L.append("")
        L.append("```yaml")
        L.append(f'- "{pattern}"')
        L.append("```")
        L.append("")
        if cands:
            L.append("with one of:")
            L.append("")
            L.append("```yaml")
            for path, conf, why in cands:
                L.append(f'- "{path}"    # {conf} — {why}')
            L.append("```")
            L.append("")
            L.append("If studies provisioned before this change are still active, **keep the old "
                     "pattern as well as adding the new one** — detection config is global, not "
                     "per-study, so both layouts need to match. See the note at the bottom.")
        else:
            L.append("No replacement was found. Check whether upstream removed the artefact "
                     "entirely; if so this gate may need its detection rethought, or moved to "
                     "`advance_rule: manual_only`.")
        L.append("")
        mentions = prose_mentions(tmpl, pattern)
        if mentions:
            L.append("**The gate prose also names this path** — study leads read it, so it has "
                     "to change too:")
            L.append("")
            for lineno, text in mentions:
                L.append(f"- line {lineno}: `{text[:110]}`")
            L.append("")

    L.append("## Then")
    L.append("")
    L.append("```bash")
    L.append("python .github/scripts/build_gates.py       # regenerate gates.json")
    L.append("python .github/scripts/gatelib.py           # matcher self-test")
    L.append("python .github/scripts/gate_machine.py      # rule self-test")
    L.append("```")
    L.append("")
    L.append("Commit the regenerated `.github/data/gates.json` along with the template edits. "
             "This check runs on every push touching `.github/issue-templates/**`, so it will "
             "confirm the fix and close this issue on its own.")
    L.append("")
    L.append("## Definition of done")
    L.append("")
    L.append("- [ ] `detection.paths` corrected in each affected gate template")
    L.append("- [ ] Gate prose updated wherever it names a changed path")
    L.append("- [ ] `gates.json` regenerated and committed")
    L.append("- [ ] Decided whether to keep the old pattern for already-provisioned studies")
    L.append("- [ ] This check green (it closes this issue automatically)")
    L.append("- [ ] One study provisioned as a smoke test before the next real one")
    L.append("")
    L.append("<details><summary>Why keeping the old pattern may be necessary</summary>")
    L.append("")
    L.append("`gates.json` detection paths apply to every study, not per study. If some studies "
             "were scaffolded before this upstream change and some after, the two cohorts have "
             "different layouts, and only listing both paths will detect both. The cost is that "
             "this check will keep reporting the retired path as missing upstream — which is "
             "accurate, and is the trade for not breaking the older cohort.")
    L.append("")
    L.append("If every active study was scaffolded after the change, just replace the path.")
    L.append("</details>")
    L.append("")
    L.append("---")
    L.append(f"*Opened automatically by [Path Contract Check]"
             f"(https://github.com/{factory_repo}/actions/workflows/path-contract-check.yml). "
             "Updated in place rather than reopened.*")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--factory-repo", required=True)
    ap.add_argument("--upstream", default="ohdsi-studies/StrategusStudyRepoTemplate")
    ap.add_argument("--label", default="path-contract")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--simulate-missing", default="",
                    help="comma-separated upstream paths to pretend are gone, for testing")
    ap.add_argument("--simulate-move", default="",
                    help="comma-separated old=new prefix rewrites, for testing")
    args = ap.parse_args()

    gates = json.loads(GATES.read_text(encoding="utf-8"))
    tree = json.loads(gh("api", f"repos/{args.upstream}/git/trees/HEAD?recursive=1"))
    head = json.loads(gh("api", f"repos/{args.upstream}/commits/HEAD",
                         "--jq", "{sha:.sha,date:.commit.author.date}"))

    paths = [n["path"] for n in tree.get("tree", []) if n["type"] == "blob"]
    if args.simulate_missing:
        gone = {p.strip() for p in args.simulate_missing.split(",") if p.strip()}
        paths = [p for p in paths if p not in gone]
        print(f"(simulating {len(gone)} missing path(s))")
    if args.simulate_move:
        for rule in args.simulate_move.split(","):
            old, _, new = rule.partition("=")
            paths = [new + p[len(old):] if p.startswith(old) else p for p in paths]
        print(f"(simulating move: {args.simulate_move})")

    broken, checked = [], 0
    for gate in gates["gates"]:
        d = gate["detection"]
        if d.get("baseline") != "upstream":
            continue
        for pattern in d.get("paths", []):
            checked += 1
            if expand(pattern, paths):
                print(f"  ok      gate {gate['gate']}  {pattern}")
            else:
                cands = candidates(pattern, paths)
                broken.append((gate["gate"], gate["title"], pattern, cands))
                top = f" -> likely {cands[0][0]} ({cands[0][1]})" if cands else " -> no candidate"
                print(f"  BROKEN  gate {gate['gate']}  {pattern}{top}")

    if not broken:
        print(f"\nAll {checked} detection paths match upstream.")
        if not args.dry_run:
            existing = gh("issue", "list", "--repo", args.factory_repo, "--label", args.label,
                          "--state", "open", "--limit", "1", "--json", "number",
                          "--jq", ".[0].number // empty", check=False)
            if existing:
                gh("issue", "close", existing, "--repo", args.factory_repo,
                   "--comment", f"All gate detection paths match upstream again as of "
                                f"`{head['sha'][:7]}`.")
                print(f"closed #{existing}")
        return 0

    body = build_issue(broken, args.upstream, head, args.factory_repo, checked)
    title = f"Gate detection paths no longer match upstream ({len(broken)} of {checked})"

    if args.dry_run:
        print("\n" + "=" * 70)
        print(f"TITLE: {title}\n")
        print(body)
        return 0

    gh("label", "create", args.label, "--repo", args.factory_repo, "--color", "d93f0b",
       "--description", "Gate detection paths no longer match the upstream template",
       check=False)

    existing = gh("issue", "list", "--repo", args.factory_repo, "--label", args.label,
                  "--state", "open", "--limit", "1", "--json", "number",
                  "--jq", ".[0].number // empty", check=False)

    pathlib.Path("issue-body.md").write_text(body, encoding="utf-8")
    if existing:
        gh("issue", "edit", existing, "--repo", args.factory_repo,
           "--title", title, "--body-file", "issue-body.md")
        print(f"::warning::Updated contract-break issue #{existing}")
    else:
        url = gh("issue", "create", "--repo", args.factory_repo, "--title", title,
                 "--body-file", "issue-body.md", "--label", args.label)
        print(f"::warning::Opened contract-break issue {url}")
    pathlib.Path("issue-body.md").unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
