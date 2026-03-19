#!/usr/bin/env python3
"""Token management for new-api.

Usage:
  python3 tokens.py list [--page N]
  python3 tokens.py get <id>
  python3 tokens.py create --name NAME [--quota N] [--unlimited] [--expire TIMESTAMP]
  python3 tokens.py update --id ID [--name NAME] [--quota N] [--unlimited] [--expire TS] [--status N]
  python3 tokens.py search <keyword>
  python3 tokens.py delete <id> [--yes]
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, confirm, write_json, paginate


def cmd_list(client, args):
    data, total, wrapper = paginate(client, "/api/token/", {}, args.page)
    if args.output:
        write_json(wrapper, args.output)
        return
    print(f"Tokens (page {args.page}, total {total}):")
    if not data:
        print("  (none)")
        return
    for t in data:
        status = "disabled" if t.get("disabled") else "active"
        unlimited = " (unlimited)" if t.get("unlimited_quota") else ""
        quota = t.get("remain_quota", 0)
        key = t.get("key", "") or ""
        if len(key) > 20:
            key_preview = key[:8] + "..." + key[-8:]
        else:
            key_preview = key
        print(f"  [{t.get('id'):>4}] {t.get('name', '?'):<25} {status:<10} quota={quota}{unlimited}  key={key_preview}")


def cmd_get(client, args):
    result = check_success(client.get(f"/api/token/{args.id}"))
    print_json(result.get("data", result))


def cmd_create(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would create token '{args.name}'")
        return
    body = {
        "name": args.name,
    }
    if args.quota is not None:
        body["remain_quota"] = args.quota
    if args.unlimited:
        body["unlimited_quota"] = True
    if args.expire is not None:
        body["expired_time"] = args.expire

    result = check_success(client.post("/api/token/", body))
    print("Token created successfully.")
    # Show the key so the user can copy it
    data = result.get("data", result)
    if isinstance(data, dict) and data.get("key"):
        print(f"Key: {data['key']}")
    print_json(result)


def cmd_update(client, args):
    """Update token fields. Backend uses Select() to only write:
    name, status, expired_time, remain_quota, unlimited_quota,
    model_limits_enabled, model_limits, allow_ips, group, cross_group_retry.
    Safe to send partial data — other fields are ignored."""
    body = {"id": args.id}
    if args.name is not None:
        body["name"] = args.name
    if args.quota is not None:
        body["remain_quota"] = args.quota
    if args.unlimited:
        body["unlimited_quota"] = True
    if args.expire is not None:
        body["expired_time"] = args.expire
    if args.status is not None:
        body["status"] = args.status
    if len(body) == 1:
        print("No fields to update. Use --name, --quota, --unlimited, --expire, --status.", file=sys.stderr)
        sys.exit(1)
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would update token {args.id}")
        return
    check_success(client.put("/api/token/", body))
    print(f"Token {args.id} updated.")


def cmd_search(client, args):
    result = check_success(client.get("/api/token/search", {"keyword": args.keyword}))
    wrapper = result.get("data", {})
    data = wrapper.get("items", []) if isinstance(wrapper, dict) else wrapper
    total = wrapper.get("total", len(data)) if isinstance(wrapper, dict) else len(data)
    print(f"Search results for '{args.keyword}' ({total} found):")
    for t in data:
        status = "disabled" if t.get("disabled") else "active"
        print(f"  [{t.get('id'):>4}] {t.get('name', '?'):<25} {status}")
    if not data:
        print("  (none)")


def cmd_delete(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would delete token {args.id}")
        return
    if not args.yes:
        if not confirm(f"Delete token {args.id}? [y/N] "):
            print("Cancelled.")
            return
    result = check_success(client.delete(f"/api/token/{args.id}"))
    print(f"Token {args.id} deleted.")
    print_json(result)


def main():
    parser = argparse.ArgumentParser(description="new-api token management")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="List tokens")
    p.add_argument("--page", "-p", type=int, default=1)
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON output to file")

    # get
    p = sub.add_parser("get", help="Get token details")
    p.add_argument("id", type=int)

    # create
    p = sub.add_parser("create", help="Create a token")
    p.add_argument("--name", required=True, help="Token name")
    p.add_argument("--quota", type=int, help="Remaining quota")
    p.add_argument("--unlimited", action="store_true", help="Unlimited quota")
    p.add_argument("--expire", type=int, help="Expiry timestamp (-1 for never)")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # update
    p = sub.add_parser("update", help="Update a token")
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--name", type=str, default=None)
    p.add_argument("--quota", type=int, default=None, help="Remaining quota")
    p.add_argument("--unlimited", action="store_true", help="Set unlimited quota")
    p.add_argument("--expire", type=int, default=None, help="Expiry timestamp")
    p.add_argument("--status", type=int, default=None, help="1=enabled, 0=disabled")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # search
    p = sub.add_parser("search", help="Search tokens")
    p.add_argument("keyword", type=str)

    # delete
    p = sub.add_parser("delete", help="Delete a token")
    p.add_argument("id", type=int)
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    args = parser.parse_args()
    client = make_client()

    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "create": cmd_create,
        "update": cmd_update,
        "search": cmd_search,
        "delete": cmd_delete,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
