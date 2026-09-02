#!/usr/bin/env python3
"""Find studies and partners that have gone quiet, and roll the answer up.

The premise of the whole system: a stalled study never announces itself, it just
goes quiet. Nothing arrives to tell you a study is stuck. So something has to go
looking, on a schedule, and say so out loud.

Two clocks, deliberately different:

  study    days since the current gate was entered. Not days since the last push
           — v1 measured repository `pushed_at`, which meant a README typo read
           as progress. Time-in-state is the only measure that cannot be gamed
           by activity that is not progress.

  partner  days since the last sign of life on the issue, taken as the later of
           the last comment and the last body edit. The brief says comments are
           the history and their dates drive this, but the same templates tell
           leads to keep the body current — so a lead who diligently rewrites the
           body and comments nothing would otherwise read as stalled.

Threshold defaults to 21 days and is configurable per study in its state file, or
globally via gates.json.
"""

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from factory_issue import partner_rows, refresh  # noqa: E402
from gatelib import gate_option  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
GATES = ROOT / ".github" / "data" / "gates.json"
DASHBOARD_LABEL = "portfolio-status"
DASHBOARD_TITLE = "Portfolio status — all studies at a glance"


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def parse_ts(value):
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def days_since(value, now):
    ts = parse_ts(value)
    return None if ts is None else (now - ts).days


def roll_up(state, partners, threshold, now):
    """The per-study summary Factory shows."""
    stalled_partners = [p for p in partners
                        if p["days_quiet"] is not None and p["days_quiet"] >= threshold]
    days_in_gate = days_since(state.get("gate_entered_at"), now)

    return {
        "study_repo": state["study_repo"],
        "factory_repo": state.get("factory_repo"),
        "factory_issue": state.get("factory_issue"),
        "current_gate": state.get("current_gate", -1),
        "days_in_gate": days_in_gate,
        "gate_entered_at": state.get("gate_entered_at"),
        "stalled": days_in_gate is not None and days_in_gate >= threshold,
        "never_started": state.get("gate_entered_at") is None,
        "partner_count": len(partners),
        "stalled_partners": len(stalled_partners),
        "stalled_partner_detail": stalled_partners,
        "threshold": threshold,
    }


def gate_name(gates_config, number):
    if number is None or number < 0:
        return "Not started"
    return next((g["title"] for g in gates_config["gates"] if g["gate"] == number),
                f"Gate {number}")


def partner_line(summary):
    if summary["partner_count"] == 0:
        return "no partners yet"
    if summary["stalled_partners"] == 0:
        return f"{summary['partner_count']} partners, none stalled"
    return f"{summary['partner_count']} partners, {summary['stalled_partners']} stalled"


def dashboard(summaries, gates_config, factory_repo, now):
    stalled = [s for s in summaries if s["stalled"]]
    quiet_partners = sum(s["stalled_partners"] for s in summaries)

    lines = [
        f"_Updated {now.strftime('%Y-%m-%d %H:%M UTC')}._",
        "",
        f"**{len(summaries)} stud{'y' if len(summaries) == 1 else 'ies'} · "
        f"{len(stalled)} stalled · "
        f"{quiet_partners} partner{'' if quiet_partners == 1 else 's'} gone quiet**",
        "",
        "| | Study | Gate | Days in gate | Partners |",
        "|---|---|---|---|---|",
    ]

    # Most-stalled first: the list should open on whatever needs attention.
    for s in sorted(summaries,
                    key=lambda s: (-(s["days_in_gate"] or -1), s["study_repo"])):
        if s["never_started"]:
            mark, days = "⚪", "—"
        elif s["stalled"]:
            mark, days = "🔴", f"**{s['days_in_gate']}**"
        else:
            mark, days = "🟢", str(s["days_in_gate"])
        name = s["study_repo"].split("/")[-1]
        link = f"[{name}](https://github.com/{s['study_repo']})"
        issue = (f" · [#{s['factory_issue']}]"
                 f"(https://github.com/{factory_repo}/issues/{s['factory_issue']})"
                 if s["factory_issue"] else "")
        lines.append(f"| {mark} | {link}{issue} | "
                     f"{gate_name(gates_config, s['current_gate'])} | {days} | "
                     f"{partner_line(s)} |")

    detail = [s for s in summaries if s["stalled_partner_detail"]]
    if detail:
        lines += ["", "### Partners gone quiet", ""]
        for s in detail:
            lines.append(f"**{s['study_repo'].split('/')[-1]}**")
            for p in s["stalled_partner_detail"]:
                lines.append(
                    f"- [{p['title']}](https://github.com/{s['study_repo']}/issues/"
                    f"{p['number']}) — {p['days_quiet']} days quiet, "
                    f"status *{p['status']}*")
            lines.append("")

    lines += [
        "",
        "---",
        "",
        "A study is stalled when it has sat in one gate past the threshold. That is "
        "time-in-state, not time-since-push — activity is not progress. A partner is "
        "quiet when nothing has been logged on its issue, counting the later of the "
        "last comment and the last edit.",
        "",
        "<sub>Rewritten daily by "
        f"[Stall Check](https://github.com/{factory_repo}/actions/workflows/stall-check.yml). "
        "Edits are overwritten.</sub>",
    ]
    return "\n".join(lines)


def update_portfolio_fields(summary, gates_config, project_number, now):
    """Push the stall numbers onto the Factory portfolio board.

    The dashboard issue is the readable version; these fields are what let the
    board sort and filter on the same numbers — which is what makes it a stall
    radar rather than a list of studies.

    Best-effort throughout. A board that cannot be written must never fail the
    sweep; the dashboard issue and the state files remain the record.
    """
    if not project_number or not summary.get("factory_repo") or not summary.get("factory_issue"):
        return

    owner = summary["factory_repo"].split("/")[0]
    issue = summary["factory_issue"]

    raw = gh("api", "graphql", "-f",
             "query=query($login:String!,$num:Int!){repositoryOwner(login:$login){"
             "... on ProjectV2Owner{projectV2(number:$num){id "
             "fields(first:40){nodes{... on ProjectV2FieldCommon{id name dataType}"
             "... on ProjectV2SingleSelectField{options{id name}}}} "
             "items(first:100){nodes{id content{... on Issue{number}}}}}}}}",
             "-f", f"login={owner}", "-F", f"num={project_number}", check=False)
    if not raw:
        return
    try:
        project = json.loads(raw)["data"]["repositoryOwner"]["projectV2"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return
    if not project:
        return

    item = next((i for i in project["items"]["nodes"]
                 if (i.get("content") or {}).get("number") == issue), None)
    if not item:
        return

    fields = {f["name"]: f for f in project["fields"]["nodes"] if f.get("name")}

    def set_field(name, value_expr, value_args):
        f = fields.get(name)
        if not f:
            return
        args = ["-f", f"p={project['id']}", "-f", f"i={item['id']}",
                "-f", f"f={f['id']}"] + value_args
        gh("api", "graphql", "-f",
           "query=mutation($p:ID!,$i:ID!,$f:ID!,$v:" + value_expr[0] + "){"
           "updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,"
           "value:{" + value_expr[1] + "}}){projectV2Item{id}}}", *args, check=False)

    if summary.get("days_in_gate") is not None:
        set_field("Days in Gate", ("Float!", "number:$v"),
                  ["-F", f"v={summary['days_in_gate']}"])
    set_field("Partners", ("Float!", "number:$v"), ["-F", f"v={summary['partner_count']}"])
    set_field("Partners Stalled", ("Float!", "number:$v"),
              ["-F", f"v={summary['stalled_partners']}"])

    entered = summary.get("gate_entered_at")
    if entered:
        set_field("Gate Entered", ("Date!", "date:$v"), ["-f", f"v={entered[:10]}"])

    gate_name_str = gate_name(gates_config, summary["current_gate"])
    gate_field = fields.get("Gate")
    if gate_field and gate_field.get("options"):
        opt = gate_option(gate_field["options"], gate_name_str)
        if opt:
            set_field("Gate", ("String!", "singleSelectOptionId:$v"), ["-f", f"v={opt['id']}"])

    print(f"    portfolio fields updated for #{issue}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--factory-repo", required=True)
    ap.add_argument("--state-dir", default=".github/data/state")
    ap.add_argument("--threshold", type=int, default=None,
                    help="override the threshold for every study")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    gates_config = json.loads(GATES.read_text(encoding="utf-8"))
    global_threshold = (args.threshold if args.threshold is not None
                        else gates_config.get("stall_threshold_days", 21))

    state_dir = ROOT / args.state_dir
    files = sorted(state_dir.glob("*.json")) if state_dir.exists() else []
    if not files:
        print("No studies are being tracked yet — nothing to check.")
        return 0

    summaries = []
    for path in files:
        state = json.loads(path.read_text(encoding="utf-8"))
        threshold = (args.threshold if args.threshold is not None
                     else state.get("stall_threshold_days", global_threshold))
        partners = partner_rows(state["study_repo"], now)
        summary = roll_up(state, partners, threshold, now)
        summaries.append(summary)

        flag = ("STALLED" if summary["stalled"]
                else "not started" if summary["never_started"] else "ok")
        print(f"  {flag:12} {summary['study_repo']}  "
              f"gate {summary['current_gate']}  "
              f"{summary['days_in_gate']} day(s)  {partner_line(summary)}")

        if not args.dry_run:
            refresh(state, gates_config, now=now, threshold=threshold)
            update_portfolio_fields(summary, gates_config,
                                    os.environ.get("FACTORY_PROJECT_NUMBER"), now)

    body = dashboard(summaries, gates_config, args.factory_repo, now)

    if args.dry_run:
        print("\n--- dashboard (dry run) ---\n")
        print(body)
        return 0

    gh("label", "create", DASHBOARD_LABEL, "--repo", args.factory_repo,
       "--color", "1d76db", "--description", "Portfolio stall dashboard",
       check=False)

    existing = gh("issue", "list", "--repo", args.factory_repo,
                  "--label", DASHBOARD_LABEL, "--state", "open", "--limit", "1",
                  "--json", "number", "--jq", ".[0].number // empty", check=False)

    if existing:
        subprocess.run(["gh", "issue", "edit", existing, "--repo", args.factory_repo,
                        "--title", DASHBOARD_TITLE, "--body", body],
                       check=False, capture_output=True, text=True)
        print(f"\nupdated dashboard #{existing}")
    else:
        url = gh("issue", "create", "--repo", args.factory_repo,
                 "--title", DASHBOARD_TITLE, "--body", body,
                 "--label", DASHBOARD_LABEL)
        print(f"\ncreated dashboard {url}")

    stalled = [s for s in summaries if s["stalled"]]
    if stalled:
        print(f"::warning::{len(stalled)} stalled study(ies): "
              + ", ".join(s["study_repo"] for s in stalled))
    return 0


if __name__ == "__main__":
    sys.exit(main())
