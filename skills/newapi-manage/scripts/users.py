#!/usr/bin/env python3
"""User management for new-api.

Usage:
  python3 users.py list [--page N]
  python3 users.py get <id>
  python3 users.py search <keyword>
  python3 users.py create --username NAME --password PASS [--display-name NAME] [--role N] [--quota N]
  python3 users.py update --id ID [--display-name NAME] [--quota N] [--group GROUP] [--status N]
  python3 users.py manage --id ID --action ACTION [--yes]
  python3 users.py delete <id> [--yes]
  python3 users.py count
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, confirm, write_json, paginate


def cmd_list(client, args):
    data, total, wrapper = paginate(client, "/api/user/", {}, args.page)
    if args.output:
        write_json(wrapper, args.output)
        return
    print(f"Users (page {args.page}, total {total}):")
    if not data:
        print("  (none)")
        return
    for u in data:
        role_map = {0: "user", 1: "admin", 2: "root"}
        role = role_map.get(u.get("role", 0), f"role={u.get('role')}")
        status = "enabled" if u.get("status") == 1 else "disabled"
        name = u.get("display_name") or u.get("username", "?")
        print(f"  [{u.get('id'):>4}] {u.get('username', '?'):<20} {name:<20} {role:<6} {status}  quota={u.get('quota', 0)}")


def cmd_get(client, args):
    result = check_success(client.get(f"/api/user/{args.id}"))
    print_json(result.get("data", result))


def cmd_search(client, args):
    result = check_success(client.get("/api/user/search", {"keyword": args.keyword}))
    wrapper = result.get("data", {})
    data = wrapper.get("items", []) if isinstance(wrapper, dict) else wrapper
    total = wrapper.get("total", len(data)) if isinstance(wrapper, dict) else len(data)
    print(f"Search results for '{args.keyword}' ({total} found):")
    for u in data:
        print(f"  [{u.get('id'):>4}] {u.get('username', '?'):<20} {u.get('display_name', '')}")
    if not data:
        print("  (none)")


def cmd_create(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would create user '{args.username}'")
        return
    body = {
        "username": args.username,
        "password": args.password,
    }
    if args.display_name:
        body["display_name"] = args.display_name
    if args.role is not None:
        body["role"] = args.role
    if args.quota is not None:
        body["quota"] = args.quota

    result = check_success(client.post("/api/user/", body))
    print("User created successfully.")
    print_json(result)


def cmd_update(client, args):
    """Update user fields. Backend Edit() only touches: username, display_name, group, quota, remark.
    We must always send current values for fields we don't want to change,
    because the backend overwrites all 5 fields from the map."""
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would update user {args.id}")
        return
    result = check_success(client.get(f"/api/user/{args.id}"))
    user = result.get("data", result)
    if not isinstance(user, dict):
        print(f"Error: unexpected response for user {args.id}", file=sys.stderr)
        sys.exit(1)
    # Only send the 5 fields that Edit() actually writes
    body = {
        "id": user["id"],
        "username": user.get("username", ""),
        "display_name": user.get("display_name", ""),
        "group": user.get("group", "default"),
        "quota": user.get("quota", 0),
        "remark": user.get("remark", ""),
    }
    changed = False
    if args.display_name is not None:
        body["display_name"] = args.display_name
        changed = True
    if args.quota is not None:
        body["quota"] = args.quota
        changed = True
    if args.group is not None:
        body["group"] = args.group
        changed = True
    if args.status is not None:
        body["status"] = args.status
        changed = True
    if not changed:
        print("No fields to update. Use --display-name, --quota, --group, --status.", file=sys.stderr)
        sys.exit(1)
    check_success(client.put("/api/user/", body))
    print(f"User {args.id} updated.")


def cmd_manage(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would {args.action} user {args.id}")
        return
    destructive = args.action in ("disable", "delete", "demote")
    if destructive and not args.yes:
        if not confirm(f"{args.action.capitalize()} user {args.id}? [y/N] "):
            print("Cancelled.")
            return
    result = check_success(client.post("/api/user/manage", {"id": args.id, "action": args.action}))
    print(f"User {args.id}: {args.action} done.")
    print_json(result.get("data", result))


def cmd_delete(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would delete user {args.id}")
        return
    if not args.yes:
        if not confirm(f"Delete user {args.id}? [y/N] "):
            print("Cancelled.")
            return
    check_success(client.delete(f"/api/user/{args.id}"))
    print(f"User {args.id} deleted.")


def cmd_count(client, args):
    # Fetch first page to get total count
    result = check_success(client.get("/api/user/", {"p": 1}))
    wrapper = result.get("data", {})
    total = wrapper.get("total", 0) if isinstance(wrapper, dict) else 0
    print(f"Total users: {total}")


def main():
    parser = argparse.ArgumentParser(description="new-api user management")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="List users")
    p.add_argument("--page", "-p", type=int, default=1)
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON output to file")

    # get
    p = sub.add_parser("get", help="Get user details")
    p.add_argument("id", type=int)

    # search
    p = sub.add_parser("search", help="Search users")
    p.add_argument("keyword", type=str)

    # create
    p = sub.add_parser("create", help="Create a user")
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--display-name", type=str)
    p.add_argument("--role", type=int, help="0=user, 1=admin, 2=root")
    p.add_argument("--quota", type=int)
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # count
    sub.add_parser("count", help="Show total user count")

    # update
    p = sub.add_parser("update", help="Update a user")
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--display-name", type=str, default=None)
    p.add_argument("--quota", type=int, default=None)
    p.add_argument("--group", type=str, default=None)
    p.add_argument("--status", type=int, default=None, help="1=enabled, other=disabled")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # manage
    p = sub.add_parser("manage", help="Manage user status/role")
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--action", required=True, choices=["disable", "enable", "delete", "promote", "demote"])
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # delete
    p = sub.add_parser("delete", help="Delete a user")
    p.add_argument("id", type=int)
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
        "manage": cmd_manage,
        "delete": cmd_delete,
        "count": cmd_count,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
