#!/usr/bin/env python3
"""Redemption code management for new-api.

Usage:
  python3 redemption.py list [--page N]
  python3 redemption.py get <id>
  python3 redemption.py search <keyword>
  python3 redemption.py create --name NAME --quota N [--count N] [--expire TIMESTAMP]
  python3 redemption.py update --id ID [--name NAME] [--quota N] [--expire TS] [--status-only --status N]
  python3 redemption.py delete <id> [--yes]
  python3 redemption.py cleanup [--yes]
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, confirm, write_json, paginate


def _print_redemptions(items, total, label="Redemptions"):
    print(f"{label} (total {total}):")
    if not items:
        print("  (none)")
        return
    for r in items:
        status_map = {1: "active", 2: "disabled", 3: "redeemed"}
        st = status_map.get(r.get("status"), f"status={r.get('status')}")
        name = r.get("name", "?")
        quota = r.get("quota", 0)
        print(f"  [{r.get('id', '?'):>4}] {name:<20} quota={quota:<8} {st}")


def cmd_list(client, args):
    data, total, wrapper = paginate(client, "/api/redemption/", {}, args.page)
    if args.output:
        write_json(wrapper, args.output)
        return
    _print_redemptions(data, total)


def cmd_get(client, args):
    result = check_success(client.get(f"/api/redemption/{args.id}"))
    print_json(result.get("data", result))


def cmd_search(client, args):
    result = check_success(client.get("/api/redemption/search", {"keyword": args.keyword}))
    if args.output:
        write_json(result, args.output)
        return
    wrapper = result.get("data", {})
    items = wrapper.get("items", []) if isinstance(wrapper, dict) else wrapper
    total = wrapper.get("total", len(items)) if isinstance(wrapper, dict) else len(items)
    _print_redemptions(items, total, f"Search '{args.keyword}'")


def cmd_create(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would create redemption code(s) named '{args.name}'")
        return
    body = {"name": args.name, "quota": args.quota}
    if args.count:
        body["count"] = args.count
    if args.expire is not None:
        body["expired_time"] = args.expire
    result = check_success(client.post("/api/redemption/", body))
    data = result.get("data", result)
    if isinstance(data, list):
        print(f"Created {len(data)} redemption code(s):")
        for key in data:
            print(f"  {key}")
    else:
        print("Redemption code(s) created.")
        print_json(data)


def cmd_update(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would update redemption {args.id}")
        return
    body = {"id": args.id}
    params = {}
    if args.status_only:
        params["status_only"] = "true"
        if args.status is not None:
            body["status"] = args.status
    else:
        if args.name is not None:
            body["name"] = args.name
        if args.quota is not None:
            body["quota"] = args.quota
        if args.expire is not None:
            body["expired_time"] = args.expire
    result = check_success(client.put("/api/redemption/", body, params))
    print("Redemption updated.")
    print_json(result.get("data", result))


def cmd_delete(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would delete redemption {args.id}")
        return
    if not args.yes:
        if not confirm(f"Delete redemption {args.id}? [y/N] "):
            print("Cancelled.")
            return
    check_success(client.delete(f"/api/redemption/{args.id}"))
    print(f"Redemption {args.id} deleted.")


def cmd_cleanup(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would cleanup invalid redemption codes")
        return
    if not args.yes:
        if not confirm("Delete all expired/invalid redemption codes? [y/N] "):
            print("Cancelled.")
            return
    result = check_success(client.delete("/api/redemption/invalid"))
    count = result.get("data", "?")
    print(f"Cleaned up {count} invalid redemption code(s).")


def main():
    parser = argparse.ArgumentParser(description="new-api redemption code management")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="List redemption codes")
    p.add_argument("--page", "-p", type=int, default=1)
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON output to file")

    p = sub.add_parser("get", help="Get redemption details")
    p.add_argument("id", type=int)

    p = sub.add_parser("search", help="Search redemption codes")
    p.add_argument("keyword", type=str)
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON output to file")

    p = sub.add_parser("create", help="Create redemption codes")
    p.add_argument("--name", required=True, type=str)
    p.add_argument("--quota", required=True, type=int)
    p.add_argument("--count", type=int, default=1, help="Batch count (1-100)")
    p.add_argument("--expire", type=int, default=None, help="Expiry timestamp (0=never)")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    p = sub.add_parser("update", help="Update a redemption code")
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--name", type=str, default=None)
    p.add_argument("--quota", type=int, default=None)
    p.add_argument("--expire", type=int, default=None)
    p.add_argument("--status-only", action="store_true", help="Only update status")
    p.add_argument("--status", type=int, default=None)
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    p = sub.add_parser("delete", help="Delete a redemption code")
    p.add_argument("id", type=int)
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    p = sub.add_parser("cleanup", help="Delete all expired/invalid codes")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    args = parser.parse_args()
    client = make_client()

    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "search": cmd_search,
        "create": cmd_create,
        "update": cmd_update,
        "delete": cmd_delete,
        "cleanup": cmd_cleanup,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
