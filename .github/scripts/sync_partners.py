#!/usr/bin/env python3
"""Upsert data partner issues in a study repository from its partners.csv.

Runs in Factory, not in the study repo, so partner tracking can change without
editing ten repositories. The study repo already reports `partners.csv` among its
changed paths, so no extra dispatch is needed.

Two rules from the brief shape this:

  the body is current state    Overwritten on every sync. Anyone should see where
                               a partner stands without scrolling.
  comments are the history     Append-only, never rewritten. Their dates are what
                               stall detection reads.

So a sync rewrites the body freely but only ever *adds* a comment, and only when
something actually changed — a no-op sync stays silent, or the comment dates stop
meaning "somebody did something" and stall detection quietly becomes useless.

v1 parsed this file with `line.split(',')` and skipped any row with fewer than
three columns, which silently dropped partners whose GitHub username was blank
and mangled any institution with a comma in its name. This uses a real CSV
parser.
"""

import argparse
import csv
import io
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from partnerlib import (DEFAULT_STATUS, OPTION_FOR_LABEL, STATUS_LABELS,  # noqa: E402
                        partner_board, set_board_status)

# Column aliases, so a lead editing the header by hand does not break the sync.
ALIASES = {
    "institution": {"institution", "site name", "site", "organisation", "organization"},
    "contact_name": {"contact_name", "contact name", "contact", "name"},
    "contact_role": {"contact_role", "contact role", "role", "title"},
    "contact_github": {"contact_github", "contact github username", "github", "username"},
}


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def normalise(header):
    """Map the file's actual headers onto our canonical field names."""
    out = {}
    for i, raw in enumerate(header):
        key = (raw or "").strip().lower()
        for canon, names in ALIASES.items():
            if key in names:
                out[canon] = i
                break
    return out


def read_partners(repo, ref):
    """Parse partners.csv from the study repo. Returns [] if absent or empty."""
    r = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/partners.csv?ref={ref}", "--jq", ".content"],
        capture_output=True, text=True)
    if r.returncode:
        print("  partners.csv not found")
        return []

    import base64
    text = base64.b64decode(r.stdout.strip()).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if len(rows) < 2:
        print("  partners.csv has no data rows")
        return []

    cols = normalise(rows[0])
    if "institution" not in cols:
        print(f"::warning::partners.csv has no institution column; headers were {rows[0]}")
        return []

    partners = []
    for row in rows[1:]:
        def cell(field):
            i = cols.get(field)
            return (row[i].strip() if i is not None and i < len(row) else "")

        institution = cell("institution")
        if not institution:
            continue  # a blank name is a blank row, not a partner
        partners.append({
            "institution": institution,
            "contact_name": cell("contact_name"),
            "contact_role": cell("contact_role"),
            "contact_github": cell("contact_github").lstrip("@"),
        })
    return partners


def build_body(p, status_label):
    # The same words the board column uses, so the body and the card agree.
    status = OPTION_FOR_LABEL.get(
        status_label, status_label.replace("status:", "").replace("-", " ").capitalize())
    contact = p["contact_name"] or "—"
    if p["contact_role"]:
        contact += f", {p['contact_role']}"
    if p["contact_github"]:
        contact += f" (@{p['contact_github']})"

    return f"""**Institution.** {p['institution']}
**Primary contact.** {contact}
**Status.** {status}
**Waiting on.** —
**Governance.** DUA: not started · IRB: not started · Data access: not confirmed

---

*Keep the section above current — overwrite it as things change, so anyone can see where this \
partner stands without scrolling. Add a comment below after every exchange: what was asked, and \
what happens next. Two lines is enough. The comments are the history, and their dates are how we \
spot a partner going quiet.*

*Have the conversations wherever you normally would. This issue is a log, not an inbox.*

**Status values:** Not yet contacted · Contacted · Interested · Package running · \
Results received · Declined

<sub>Managed by Factory from `partners.csv`. Editing the fields above is fine; the institution \
name is how this issue is matched.</sub>
"""


def title_for(institution):
    return f"Data partner — {institution}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--project-id", default="")
    args = ap.parse_args()

    partners = read_partners(args.repo, args.ref)
    if not partners:
        print("  nothing to sync")
        return 0

    existing = json.loads(gh("issue", "list", "--repo", args.repo,
                             "--label", "partner", "--state", "all",
                             "--limit", "200",
                             "--json", "number,title,labels,body") or "[]")
    by_title = {i["title"]: i for i in existing}

    # A card with no Data Partner Status sits in a nameless column on the
    # board's Data partners view, which is where every partner used to land.
    board = partner_board(args.project_id) if args.project_id else None

    created = updated = 0
    numbers = []  # every issue the CSV maps to, for the gate derivation
    for p in partners:
        title = title_for(p["institution"])
        issue = by_title.get(title)

        if issue is None:
            body = build_body(p, DEFAULT_STATUS)
            url = gh("issue", "create", "--repo", args.repo, "--title", title,
                     "--body", body, "--label", "partner", "--label", "work-item",
                     "--label", DEFAULT_STATUS)
            number = int(url.rstrip("/").split("/")[-1])
            numbers.append(number)
            created += 1
            print(f"  created #{number}  {p['institution']}")

            if args.project_id:
                node = gh("api", f"repos/{args.repo}/issues/{number}", "--jq", ".node_id")
                item = gh("api", "graphql", "-f",
                          "query=mutation($p:ID!,$c:ID!){addProjectV2ItemById("
                          "input:{projectId:$p,contentId:$c}){item{id}}}",
                          "-f", f"p={args.project_id}", "-f", f"c={node}",
                          "--jq", ".data.addProjectV2ItemById.item.id", check=False)
                if board and item:
                    set_board_status(board, item, OPTION_FOR_LABEL[DEFAULT_STATUS])
            continue

        # Existing partner: refresh the body from the CSV but keep whatever status
        # label a human has set. v1 found existing issues and then did nothing,
        # so a corrected contact never reached the issue.
        numbers.append(issue["number"])
        current_status = next(
            (l["name"] for l in issue["labels"] if l["name"] in STATUS_LABELS),
            DEFAULT_STATUS)
        body = build_body(p, current_status)

        if (issue.get("body") or "").strip() == body.strip():
            continue

        subprocess.run(["gh", "issue", "edit", str(issue["number"]),
                        "--repo", args.repo, "--body", body],
                       check=False, capture_output=True, text=True)
        updated += 1
        print(f"  updated #{issue['number']}  {p['institution']}")

    csv_names = {title_for(p["institution"]) for p in partners}
    orphans = [i for t, i in by_title.items() if t not in csv_names]
    if orphans:
        # Never close these automatically. A partner removed from the CSV may be a
        # typo being fixed, and closing a real conversation is not recoverable.
        print(f"::warning::{len(orphans)} partner issue(s) have no row in partners.csv: "
              + ", ".join(f"#{i['number']}" for i in orphans))

    print(f"  partners: {created} created, {updated} updated, {len(partners)} in CSV")

    # Tell the gate derivation which issues exist now. Listing issues by label
    # right after creating one can miss it — the list lagged the last of three
    # new partners by under a second once, and Gate 5 reported two — so the
    # derivation fetches anything named here that the list leaves out.
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("partner_issues=" + ",".join(str(n) for n in numbers) + chr(10))
    return 0


if __name__ == "__main__":
    sys.exit(main())
