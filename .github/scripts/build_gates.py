#!/usr/bin/env python3
"""Generate .github/data/gates.json from the gate issue templates.

The templates in .github/issue-templates/ are the source of truth: their prose is
what study leads read, and their front matter carries the machine-readable gate
config. This script extracts that front matter so workflows can consume it
without a YAML dependency, and keeps the two from drifting.

Usage:
    python .github/scripts/build_gates.py            # regenerate gates.json
    python .github/scripts/build_gates.py --check    # fail if gates.json is stale
"""

import argparse
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = ROOT / ".github" / "issue-templates"
OUTPUT = ROOT / ".github" / "data" / "gates.json"

FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


def parse(path):
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER.match(text)
    if not match:
        sys.exit(f"{path.name}: no front matter")
    meta = yaml.safe_load(match.group(1))
    meta["template"] = str(path.relative_to(ROOT)).replace("\\", "/")
    meta["body"] = text[match.end():].strip()
    return meta


def build():
    gates, partner = [], None

    for path in sorted(TEMPLATE_DIR.glob("*.md")):
        meta = parse(path)
        if meta.get("type") == "partner":
            partner = meta
        else:
            gates.append(meta)

    gates.sort(key=lambda g: g["gate"])

    numbers = [g["gate"] for g in gates]
    if numbers != list(range(8)):
        sys.exit(f"expected gates 0-7, found {numbers}")
    if partner is None:
        sys.exit("no partner template found")

    # Every path a gate can be evidenced by, deduplicated. The path-contract
    # check walks this list against upstream to catch a template restructure.
    # Supporting paths need baselines too: they are reported on, so their
    # template SHAs must be recorded at provisioning like any other watched path.
    detected = sorted({
        p
        for g in gates
        if g["detection"].get("event") == "content_changed"
        for key in ("paths", "supporting_paths")
        for p in g["detection"].get(key, [])
    })

    return {
        "_generated_by": ".github/scripts/build_gates.py — do not edit by hand",
        "_source": "'.github/issue-templates/*.md' front matter",
        "stall_threshold_days": partner.get("stall_threshold_days", 21),
        "partner_status_labels": partner.get("status_labels", []),
        "detected_paths": detected,
        "partner": partner,
        "gates": gates,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="fail if gates.json does not match the templates")
    args = parser.parse_args()

    data = build()
    rendered = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not OUTPUT.exists():
            sys.exit(f"{OUTPUT} does not exist — run .github/scripts/build_gates.py")
        if OUTPUT.read_text(encoding="utf-8") != rendered:
            sys.exit(f"{OUTPUT} is stale — run .github/scripts/build_gates.py")
        print(f"{OUTPUT.relative_to(ROOT)} is in sync with the templates")
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")

    auto = [g["gate"] for g in data["gates"]
            if g["advance_rule"] == "auto_advance_to_review"]
    manual = [g["gate"] for g in data["gates"]
              if g["advance_rule"] == "manual_only"]
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    print(f"  gates: {len(data['gates'])}  auto: {auto}  manual: {manual}")
    print(f"  detected paths: {len(data['detected_paths'])}")


if __name__ == "__main__":
    main()
