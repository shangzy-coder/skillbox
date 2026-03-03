#!/usr/bin/env python3
"""User management for new-api.

Usage:
  python3 users.py list [--page N]
  python3 users.py get <id>
  python3 users.py search <keyword>
  python3 users.py create --username NAME --password PASS [--display-name NAME] [--role N] [--quota N]
  python3 users.py count
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success


def cmd_list(client, args):
    result = check_success(client.get("/api/user/", {"p": args.page}))
    wrapper = result.get("data", {})
    data = wrapper.get("items", []) if isinstance(wrapper, dict) else wrapper
    total = wrapper.get("total", len(data)) if isinstance(wrapper, dict) else len(data)
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
    p.add_argument("--page", "-p", type=int, default=0)

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

    # count
    sub.add_parser("count", help="Show total user count")

    args = parser.parse_args()
    client = make_client()

    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "search": cmd_search,
        "create": cmd_create,
        "count": cmd_count,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
