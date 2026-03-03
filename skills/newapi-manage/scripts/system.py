#!/usr/bin/env python3
"""System operations for new-api.

Usage:
  python3 system.py status
  python3 system.py stats
  python3 system.py options
  python3 system.py logs [--page N] [--type T] [--model M] [--username U] [--channel C] [--start TS] [--end TS]
  python3 system.py log-stats [--type T] [--model M] [--username U] [--start TS] [--end TS]
  python3 system.py gc
  python3 system.py clear-cache
  python3 system.py reset-stats
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, confirm


def cmd_status(client, args):
    result = client.get("/api/status")
    print_json(result)


def cmd_stats(client, args):
    result = check_success(client.get("/api/performance/stats"))
    print_json(result)


def cmd_options(client, args):
    result = check_success(client.get("/api/option/"))
    print_json(result.get("data", result))


def cmd_logs(client, args):
    params = {"p": args.page}
    if args.type is not None:
        params["type"] = args.type
    if args.model:
        params["model_name"] = args.model
    if args.username:
        params["username"] = args.username
    if args.channel is not None:
        params["channel"] = args.channel
    if args.start is not None:
        params["start_timestamp"] = args.start
    if args.end is not None:
        params["end_timestamp"] = args.end
    if args.token_name:
        params["token_name"] = args.token_name
    if args.request_id:
        params["request_id"] = args.request_id

    result = check_success(client.get("/api/log/", params))
    wrapper = result.get("data", {})
    data = wrapper.get("items", []) if isinstance(wrapper, dict) else wrapper
    total = wrapper.get("total", len(data)) if isinstance(wrapper, dict) else len(data)
    print(f"Logs (page {args.page}, total {total}):")
    if not data:
        print("  (none)")
        return
    for log in data:
        ts = log.get("created_at", "?")
        model = log.get("model_name", "")
        user = log.get("username", "")
        tokens = log.get("prompt_tokens", 0) + log.get("completion_tokens", 0)
        quota = log.get("quota", 0)
        ch = log.get("channel", "")
        print(f"  [{ts}] user={user:<12} model={model:<25} tokens={tokens:>8} quota={quota:>8} channel={ch}")


def cmd_log_stats(client, args):
    params = {}
    if args.type is not None:
        params["type"] = args.type
    if args.model:
        params["model_name"] = args.model
    if args.username:
        params["username"] = args.username
    if args.start is not None:
        params["start_timestamp"] = args.start
    if args.end is not None:
        params["end_timestamp"] = args.end

    result = check_success(client.get("/api/log/stat", params))
    print_json(result)


def cmd_gc(client, args):
    print("Forcing garbage collection...")
    result = check_success(client.post("/api/performance/gc"))
    print("GC completed.")
    print_json(result)


def cmd_clear_cache(client, args):
    if not args.yes:
        if not confirm("Clear disk cache? [y/N] "):
            print("Cancelled.")
            return
    result = check_success(client.delete("/api/performance/disk_cache"))
    print("Disk cache cleared.")
    print_json(result)


def cmd_reset_stats(client, args):
    if not args.yes:
        if not confirm("Reset performance stats? [y/N] "):
            print("Cancelled.")
            return
    result = check_success(client.post("/api/performance/reset_stats"))
    print("Performance stats reset.")
    print_json(result)


def main():
    parser = argparse.ArgumentParser(description="new-api system operations")
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    sub.add_parser("status", help="System health check")

    # stats
    sub.add_parser("stats", help="Performance statistics")

    # options
    sub.add_parser("options", help="Get system options")

    # logs
    p = sub.add_parser("logs", help="Query logs")
    p.add_argument("--page", "-p", type=int, default=0)
    p.add_argument("--type", type=int, default=None)
    p.add_argument("--model", type=str, default=None)
    p.add_argument("--username", type=str, default=None)
    p.add_argument("--channel", type=int, default=None)
    p.add_argument("--token-name", type=str, default=None)
    p.add_argument("--request-id", type=str, default=None)
    p.add_argument("--start", type=int, default=None, help="Start timestamp (unix)")
    p.add_argument("--end", type=int, default=None, help="End timestamp (unix)")

    # log-stats
    p = sub.add_parser("log-stats", help="Log statistics")
    p.add_argument("--type", type=int, default=None)
    p.add_argument("--model", type=str, default=None)
    p.add_argument("--username", type=str, default=None)
    p.add_argument("--start", type=int, default=None, help="Start timestamp (unix)")
    p.add_argument("--end", type=int, default=None, help="End timestamp (unix)")

    # gc
    sub.add_parser("gc", help="Force garbage collection")

    # clear-cache
    p = sub.add_parser("clear-cache", help="Clear disk cache")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    # reset-stats
    p = sub.add_parser("reset-stats", help="Reset performance stats")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    args = parser.parse_args()
    client = make_client()

    commands = {
        "status": cmd_status,
        "stats": cmd_stats,
        "options": cmd_options,
        "logs": cmd_logs,
        "log-stats": cmd_log_stats,
        "gc": cmd_gc,
        "clear-cache": cmd_clear_cache,
        "reset-stats": cmd_reset_stats,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
