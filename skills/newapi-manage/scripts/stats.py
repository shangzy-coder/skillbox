#!/usr/bin/env python3
"""Usage statistics and ranking for new-api.

Usage:
  python3 stats.py summary                          Overall stats (calls, tokens, quota)
  python3 stats.py summary --start 2025-03-01 --end 2025-03-07
  python3 stats.py user-ranking [--start DATE] [--end DATE] [--top N]
  python3 stats.py model-ranking [--start DATE] [--end DATE] [--top N]
  python3 stats.py user-detail <username> [--start DATE] [--end DATE]
  python3 stats.py report [--start DATE] [--end DATE] [--output FILE]
"""

import argparse
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, write_json


def _ts(date_str):
    """Date string YYYY-MM-DD -> unix timestamp."""
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())


def _fmt_human(n):
    """Format number to human-readable (K/M/B)."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _fmt(n):
    """Format number with comma separators."""
    return f"{n:,}"


def _time_params(args):
    """Build time filter params from --start/--end args."""
    params = {}
    if getattr(args, "start", None):
        params["start_timestamp"] = _ts(args.start)
    if getattr(args, "end", None):
        params["end_timestamp"] = _ts(args.end)
    return params


def _fetch_all_logs(client, params, log_type=2):
    """Fetch all logs with pagination. type=2 is API call logs."""
    params["type"] = log_type
    all_items = []
    page = 1
    while True:
        params["p"] = page
        result = check_success(client.get("/api/log/", params))
        wrapper = result.get("data", {})
        items = wrapper.get("items", []) if isinstance(wrapper, dict) else wrapper
        total = wrapper.get("total", 0) if isinstance(wrapper, dict) else 0
        if not items:
            break
        all_items.extend(items)
        if len(all_items) >= total:
            break
        page += 1
    return all_items


def _aggregate_by_user(logs):
    """Aggregate logs by user, return sorted list."""
    users = {}
    for log in logs:
        uid = log.get("user_id", 0)
        uname = log.get("username", "unknown")
        if uid not in users:
            users[uid] = {
                "user_id": uid,
                "username": uname,
                "call_count": 0,
                "total_quota": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "models": set(),
            }
        u = users[uid]
        u["call_count"] += 1
        u["total_quota"] += log.get("quota", 0)
        u["total_prompt_tokens"] += log.get("prompt_tokens", 0)
        u["total_completion_tokens"] += log.get("completion_tokens", 0)
        model = log.get("model_name", "")
        if model:
            u["models"].add(model)
    # Sort by total tokens desc
    result = []
    for rank, u in enumerate(sorted(users.values(),
                                     key=lambda x: x["total_prompt_tokens"] + x["total_completion_tokens"],
                                     reverse=True), 1):
        u["rank"] = rank
        u["total_tokens"] = u["total_prompt_tokens"] + u["total_completion_tokens"]
        u["model_count"] = len(u["models"])
        del u["models"]
        result.append(u)
    return result


def _aggregate_by_model(logs):
    """Aggregate logs by model, return sorted list."""
    models = {}
    for log in logs:
        model = log.get("model_name", "unknown")
        if model not in models:
            models[model] = {
                "model": model,
                "call_count": 0,
                "total_quota": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "users": set(),
            }
        m = models[model]
        m["call_count"] += 1
        m["total_quota"] += log.get("quota", 0)
        m["total_prompt_tokens"] += log.get("prompt_tokens", 0)
        m["total_completion_tokens"] += log.get("completion_tokens", 0)
        uid = log.get("user_id", 0)
        if uid:
            m["users"].add(uid)
    result = []
    for rank, m in enumerate(sorted(models.values(),
                                     key=lambda x: x["total_prompt_tokens"] + x["total_completion_tokens"],
                                     reverse=True), 1):
        m["rank"] = rank
        m["total_tokens"] = m["total_prompt_tokens"] + m["total_completion_tokens"]
        m["user_count"] = len(m["users"])
        del m["users"]
        result.append(m)
    return result


def cmd_summary(client, args):
    params = _time_params(args)
    result = check_success(client.get("/api/log/stat", params))
    stat = result.get("data", result)

    # Also get log count
    params2 = _time_params(args)
    params2["type"] = 2
    params2["p"] = 1
    log_result = check_success(client.get("/api/log/", params2))
    wrapper = log_result.get("data", {})
    total_logs = wrapper.get("total", 0) if isinstance(wrapper, dict) else 0

    time_label = "all time"
    if args.start or args.end:
        time_label = f"{args.start or '...'} ~ {args.end or '...'}"

    print(f"Usage Summary ({time_label}):")
    print(f"  Total API calls:  {_fmt(total_logs)}")
    if isinstance(stat, dict):
        quota = stat.get("quota", 0)
        rpm = stat.get("rpm", 0)
        tpm = stat.get("tpm", 0)
        print(f"  Total quota used: {_fmt(quota)}")
        print(f"  Current RPM:      {_fmt(rpm)}")
        print(f"  Current TPM:      {_fmt(tpm)}")
    else:
        print_json(stat)

    if args.output:
        write_json({"summary": stat, "total_calls": total_logs, "time_range": time_label}, args.output)


def cmd_user_ranking(client, args):
    params = _time_params(args)
    top = getattr(args, "top", 20) or 20

    print(f"Fetching logs...", flush=True)
    logs = _fetch_all_logs(client, params)
    ranking = _aggregate_by_user(logs)

    time_label = "all time"
    if args.start or args.end:
        time_label = f"{args.start or '...'} ~ {args.end or '...'}"

    print(f"\nUser Ranking by Token Usage ({time_label}, top {top}):\n")
    print(f"  {'#':<4} {'User':<20} {'Calls':>10} {'Tokens':>12} {'Prompt':>12} {'Completion':>12} {'Models':>6}")
    print(f"  {'─'*4} {'─'*20} {'─'*10} {'─'*12} {'─'*12} {'─'*12} {'─'*6}")

    for u in ranking[:top]:
        print(f"  {u['rank']:<4} {u['username']:<20} "
              f"{_fmt(u['call_count']):>10} "
              f"{_fmt_human(u['total_tokens']):>12} "
              f"{_fmt_human(u['total_prompt_tokens']):>12} "
              f"{_fmt_human(u['total_completion_tokens']):>12} "
              f"{u['model_count']:>6}")

    print(f"\n  Total: {len(ranking)} users, {_fmt(sum(u['call_count'] for u in ranking))} calls, "
          f"{_fmt_human(sum(u['total_tokens'] for u in ranking))} tokens")

    if args.output:
        write_json(ranking[:top], args.output)


def cmd_model_ranking(client, args):
    params = _time_params(args)
    top = getattr(args, "top", 20) or 20

    print(f"Fetching logs...", flush=True)
    logs = _fetch_all_logs(client, params)
    ranking = _aggregate_by_model(logs)

    time_label = "all time"
    if args.start or args.end:
        time_label = f"{args.start or '...'} ~ {args.end or '...'}"

    print(f"\nModel Ranking by Token Usage ({time_label}, top {top}):\n")
    print(f"  {'#':<4} {'Model':<40} {'Calls':>10} {'Users':>6} {'Tokens':>12} {'Prompt':>12} {'Completion':>12}")
    print(f"  {'─'*4} {'─'*40} {'─'*10} {'─'*6} {'─'*12} {'─'*12} {'─'*12}")

    for m in ranking[:top]:
        print(f"  {m['rank']:<4} {m['model']:<40} "
              f"{_fmt(m['call_count']):>10} "
              f"{m['user_count']:>6} "
              f"{_fmt_human(m['total_tokens']):>12} "
              f"{_fmt_human(m['total_prompt_tokens']):>12} "
              f"{_fmt_human(m['total_completion_tokens']):>12}")

    if args.output:
        write_json(ranking[:top], args.output)


def cmd_user_detail(client, args):
    params = _time_params(args)
    params["username"] = args.username

    print(f"Fetching logs for {args.username}...", flush=True)
    logs = _fetch_all_logs(client, params)

    if not logs:
        print(f"No logs found for user '{args.username}'")
        return

    # Aggregate by model for this user
    models = {}
    total_prompt = 0
    total_comp = 0
    total_quota = 0
    for log in logs:
        model = log.get("model_name", "unknown")
        if model not in models:
            models[model] = {"model": model, "calls": 0, "prompt": 0, "completion": 0, "quota": 0}
        m = models[model]
        m["calls"] += 1
        m["prompt"] += log.get("prompt_tokens", 0)
        m["completion"] += log.get("completion_tokens", 0)
        m["quota"] += log.get("quota", 0)
        total_prompt += log.get("prompt_tokens", 0)
        total_comp += log.get("completion_tokens", 0)
        total_quota += log.get("quota", 0)

    sorted_models = sorted(models.values(), key=lambda x: x["prompt"] + x["completion"], reverse=True)

    time_label = "all time"
    if args.start or args.end:
        time_label = f"{args.start or '...'} ~ {args.end or '...'}"

    print(f"\nUser: {args.username} ({time_label})")
    print(f"  Total calls:      {_fmt(len(logs))}")
    print(f"  Total tokens:     {_fmt_human(total_prompt + total_comp)}")
    print(f"  Prompt tokens:    {_fmt_human(total_prompt)}")
    print(f"  Completion tokens:{_fmt_human(total_comp)}")
    print(f"  Total quota:      {_fmt(total_quota)}")
    print(f"  Models used:      {len(models)}")
    print(f"\n  Model breakdown:")
    print(f"  {'Model':<40} {'Calls':>8} {'Tokens':>12} {'Prompt':>12} {'Completion':>12}")
    print(f"  {'─'*40} {'─'*8} {'─'*12} {'─'*12} {'─'*12}")
    for m in sorted_models:
        print(f"  {m['model']:<40} {_fmt(m['calls']):>8} "
              f"{_fmt_human(m['prompt'] + m['completion']):>12} "
              f"{_fmt_human(m['prompt']):>12} "
              f"{_fmt_human(m['completion']):>12}")

    if args.output:
        write_json({"username": args.username, "total_calls": len(logs),
                     "total_tokens": total_prompt + total_comp, "models": sorted_models}, args.output)


def cmd_report(client, args):
    """Generate a full Markdown report with user + model rankings."""
    params = _time_params(args)
    output = getattr(args, "output", None) or "usage_report"

    print("Fetching all logs...", flush=True)
    logs = _fetch_all_logs(client, params)
    if not logs:
        print("No logs found for the given time range.")
        return

    user_ranking = _aggregate_by_user(logs)
    model_ranking = _aggregate_by_model(logs)

    time_label = "all time"
    if args.start or args.end:
        time_label = f"{args.start or '...'} ~ {args.end or '...'}"

    total_calls = sum(u["call_count"] for u in user_ranking)
    total_tokens = sum(u["total_tokens"] for u in user_ranking)
    total_quota = sum(u["total_quota"] for u in user_ranking)

    lines = [
        "# API Usage Report\n",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> Time range: {time_label}\n",
        "---\n",
        "## Summary\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Active users | {len(user_ranking)} |",
        f"| Total calls | {_fmt(total_calls)} |",
        f"| Total tokens | {_fmt_human(total_tokens)} |",
        f"| Total quota | {_fmt(total_quota)} |",
        "",
        "---\n",
        "## User Ranking (by token usage)\n",
        "| # | User | Calls | Tokens | Prompt | Completion | Models |",
        "|:-:|------|------:|-------:|-------:|-----------:|:------:|",
    ]

    for u in user_ranking:
        lines.append(
            f"| {u['rank']} | {u['username']} "
            f"| {_fmt(u['call_count'])} "
            f"| {_fmt_human(u['total_tokens'])} "
            f"| {_fmt_human(u['total_prompt_tokens'])} "
            f"| {_fmt_human(u['total_completion_tokens'])} "
            f"| {u['model_count']} |"
        )

    lines += [
        "", "---\n",
        "## Model Ranking (by token usage)\n",
        "| # | Model | Calls | Users | Tokens | Prompt | Completion |",
        "|:-:|-------|------:|:-----:|-------:|-------:|-----------:|",
    ]

    for m in model_ranking:
        lines.append(
            f"| {m['rank']} | {m['model']} "
            f"| {_fmt(m['call_count'])} "
            f"| {m['user_count']} "
            f"| {_fmt_human(m['total_tokens'])} "
            f"| {_fmt_human(m['total_prompt_tokens'])} "
            f"| {_fmt_human(m['total_completion_tokens'])} |"
        )

    # Write markdown
    md_path = output if output.endswith(".md") else output + ".md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report saved to {md_path}")

    # Write JSON
    json_path = output.rsplit(".", 1)[0] + ".json" if "." in output else output + ".json"
    data = {
        "generated_at": datetime.now().isoformat(),
        "time_range": time_label,
        "summary": {
            "total_users": len(user_ranking),
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_quota": total_quota,
        },
        "user_ranking": user_ranking,
        "model_ranking": model_ranking,
    }
    write_json(data, json_path)


def main():
    parser = argparse.ArgumentParser(description="new-api usage statistics")
    sub = parser.add_subparsers(dest="command", required=True)

    # summary
    p = sub.add_parser("summary", help="Overall usage stats")
    p.add_argument("--start", "-s", type=str, default=None, help="Start date YYYY-MM-DD")
    p.add_argument("--end", "-e", type=str, default=None, help="End date YYYY-MM-DD")
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON to file")

    # user-ranking
    p = sub.add_parser("user-ranking", help="Rank users by token usage")
    p.add_argument("--start", "-s", type=str, default=None, help="Start date YYYY-MM-DD")
    p.add_argument("--end", "-e", type=str, default=None, help="End date YYYY-MM-DD")
    p.add_argument("--top", "-n", type=int, default=20, help="Show top N users (default: 20)")
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON to file")

    # model-ranking
    p = sub.add_parser("model-ranking", help="Rank models by token usage")
    p.add_argument("--start", "-s", type=str, default=None, help="Start date YYYY-MM-DD")
    p.add_argument("--end", "-e", type=str, default=None, help="End date YYYY-MM-DD")
    p.add_argument("--top", "-n", type=int, default=20, help="Show top N models (default: 20)")
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON to file")

    # user-detail
    p = sub.add_parser("user-detail", help="Detailed stats for a specific user")
    p.add_argument("username", type=str, help="Username to look up")
    p.add_argument("--start", "-s", type=str, default=None, help="Start date YYYY-MM-DD")
    p.add_argument("--end", "-e", type=str, default=None, help="End date YYYY-MM-DD")
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON to file")

    # report
    p = sub.add_parser("report", help="Generate full Markdown + JSON report")
    p.add_argument("--start", "-s", type=str, default=None, help="Start date YYYY-MM-DD")
    p.add_argument("--end", "-e", type=str, default=None, help="End date YYYY-MM-DD")
    p.add_argument("--output", "-o", type=str, default="usage_report", help="Output file base name (default: usage_report)")

    args = parser.parse_args()
    client = make_client()

    commands = {
        "summary": cmd_summary,
        "user-ranking": cmd_user_ranking,
        "model-ranking": cmd_model_ranking,
        "user-detail": cmd_user_detail,
        "report": cmd_report,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
