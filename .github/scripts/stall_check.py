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
import pathlib
import subprocess
import sys

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


def partner_activity(repo, now):
    """Per-partner days since the last sign of life."""
    raw = gh("issue", "list", "--repo", repo, "--label", "partner",
             "--state", "open", "--limit", "200",
             "--json", "number,title,updatedAt,labels,comments", check=False)
    if not raw:
        return []

    out = []
    for issue in json.loads(raw):
        comments = issue.get("comments") or []
        last_comment = max((c.get("createdAt") for c in comments if c.get("createdAt")),
                           default=None)
        # Later of the two: a body rewrite is real work even with no comment.
        marks = [m for m in (last_comment, issue.get("updatedAt")) if m]
        last = max(marks) if marks else None
        status = next((l["name"] for l in issue.get("labels", [])
                       if l["name"].startswith("status:")), "status:unknown")
        out.append({
            "number": issue["number"],
            "title": issue["title"],
            "status": status.replace("status:", "").replace("-", " "),
            "days_quiet": days_since(last, now),
            "last_activity": last,
        })
    return out


def roll_up(state, partners, threshold, now):
    """The per-study summary Factory shows."""
    stalled_partners = [p for p in partners
                        if p["days_quiet"] is not None and p["days_quiet"] >= threshold]
    days_in_gate = days_since(state.get("gate_entered_at"), now)

    return {
        "study_repo": state["study_repo"],
        "factory_issue": state.get("factory_issue"),
        "current_gate": state.get("current_gate", -1),
        "days_in_gate": days_in_gate,
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


def update_factory_issue(summary, gates_config, now):
    """Rewrite the roll-up block on the study's Factory issue."""
    num = summary["factory_issue"]
    if not num:
        return

    if summary["never_started"]:
        alarm = "⚪ not started"
    elif summary["stalled"]:
        alarm = f"🔴 **stalled — {summary['days_in_gate']} days in this gate**"
    else:
        alarm = f"🟢 {summary['days_in_gate']} days in this gate"

    block = (
        "<!--factory:rollup-->\n"
        f"**Gate:** {gate_name(gates_config, summary['current_gate'])}\n"
        f"**Time in gate:** {alarm}\n"
        f"**Partners:** {partner_line(summary)}\n"
        f"<sub>Threshold {summary['threshold']} days · checked "
        f"{now.date().isoformat()}</sub>\n"
        "<!--/factory:rollup-->"
    )

    repo = "/".join(summary["study_repo"].split("/")[:1] + ["Factory"])
    body = json.loads(gh("api", f"repos/{repo}/issues/{num}",
                         "--jq", "{body:.body}"))["body"] or ""

    start, end = "<!--factory:rollup-->", "<!--/factory:rollup-->"
    if start in body and end in body:
        body = body[:body.index(start)] + block + body[body.index(end) + len(end):]
    else:
        body = body.rstrip() + "\n\n" + block + "\n"

    subprocess.run(["gh", "issue", "edit", str(num), "--repo", repo, "--body", body],
                   check=False, capture_output=True, text=True)


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
    global_threshold = args.threshold or gates_config.get("stall_threshold_days", 21)

    state_dir = ROOT / args.state_dir
    files = sorted(state_dir.glob("*.json")) if state_dir.exists() else []
    if not files:
        print("No studies are being tracked yet — nothing to check.")
        return 0

    summaries = []
    for path in files:
        state = json.loads(path.read_text(encoding="utf-8"))
        threshold = args.threshold or state.get("stall_threshold_days", global_threshold)
        partners = partner_activity(state["study_repo"], now)
        summary = roll_up(state, partners, threshold, now)
        summaries.append(summary)

        flag = ("STALLED" if summary["stalled"]
                else "not started" if summary["never_started"] else "ok")
        print(f"  {flag:12} {summary['study_repo']}  "
              f"gate {summary['current_gate']}  "
              f"{summary['days_in_gate']} day(s)  {partner_line(summary)}")

        if not args.dry_run:
            update_factory_issue(summary, gates_config, now)

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
