#!/usr/bin/env python3
"""User group management for new-api.

Usage:
  python3 groups.py list
  python3 groups.py user-groups
  python3 groups.py prefill-list
  python3 groups.py prefill-create --name NAME --ratio RATIO [--desc DESC]
  python3 groups.py prefill-update --id ID [--name NAME] [--ratio RATIO] [--desc DESC]
  python3 groups.py prefill-delete <id> [--yes]
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, confirm, write_json, get_option_json, set_option


def cmd_list(client, args):
    result = check_success(client.get("/api/group/"))
    data = result.get("data", [])
    if isinstance(data, list):
        print(f"Groups ({len(data)}):")
        for g in data:
            print(f"  {g}")
    else:
        print_json(data)


def cmd_user_groups(client, args):
    result = check_success(client.get("/api/user/groups"))
    data = result.get("data", {})
    if isinstance(data, dict):
        print(f"Usable Groups ({len(data)}):")
        for name, info in sorted(data.items()):
            if isinstance(info, dict):
                ratio = info.get("ratio", "?")
                desc = info.get("desc", "")
                print(f"  {name:<20} ratio={ratio:<8} {desc}")
            else:
                print(f"  {name:<20} {info}")
    else:
        print_json(data)


def cmd_set_ratio(client, args):
    """Set group ratio. Updates GroupRatio, group_ratio_setting.group_ratio,
    UserUsableGroups, and TopupGroupRatio atomically."""
    name = args.name
    ratio = args.ratio
    desc = args.desc or name
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would set group '{name}' ratio to {ratio} (updates 4 options)")
        return

    gr = get_option_json(client, "GroupRatio")
    gr[name] = ratio
    set_option(client, "GroupRatio", gr)
    set_option(client, "group_ratio_setting.group_ratio", gr)

    uug = get_option_json(client, "UserUsableGroups")
    if name not in uug:
        uug[name] = desc
    set_option(client, "UserUsableGroups", uug)

    tgr = get_option_json(client, "TopupGroupRatio")
    tgr[name] = ratio
    set_option(client, "TopupGroupRatio", tgr)

    print(f"Group '{name}' ratio set to {ratio}. All related options updated.")


def cmd_prefill_list(client, args):
    result = check_success(client.get("/api/prefill_group/"))
    if args.output:
        write_json(result, args.output)
        return
    data = result.get("data", [])
    if isinstance(data, list):
        print(f"Prefill Groups ({len(data)}):")
        if not data:
            print("  (none)")
            return
        for g in data:
            if isinstance(g, dict):
                print(f"  [{g.get('id', '?'):>4}] {g.get('name', '?'):<20} ratio={g.get('ratio', '?'):<8} {g.get('description', '')}")
            else:
                print(f"  {g}")
    else:
        print_json(data)


def cmd_prefill_create(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would create prefill group '{args.name}'")
        return
    body = {"name": args.name, "ratio": args.ratio}
    if args.desc:
        body["description"] = args.desc
    result = check_success(client.post("/api/prefill_group/", body))
    print("Prefill group created.")
    print_json(result.get("data", result))


def cmd_prefill_update(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would update prefill group {args.id}")
        return
    body = {"id": args.id}
    if args.name is not None:
        body["name"] = args.name
    if args.ratio is not None:
        body["ratio"] = args.ratio
    if args.desc is not None:
        body["description"] = args.desc
    result = check_success(client.put("/api/prefill_group/", body))
    print("Prefill group updated.")
    print_json(result.get("data", result))


def cmd_prefill_delete(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would delete prefill group {args.id}")
        return
    if not args.yes:
        if not confirm(f"Delete prefill group {args.id}? [y/N] "):
            print("Cancelled.")
            return
    result = check_success(client.delete(f"/api/prefill_group/{args.id}"))
    print(f"Prefill group {args.id} deleted.")


def main():
    parser = argparse.ArgumentParser(description="new-api group management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all groups")
    sub.add_parser("user-groups", help="Show usable groups with ratios")

    p = sub.add_parser("set-ratio", help="Set group ratio (updates all related options)")
    p.add_argument("--name", required=True, type=str, help="Group name")
    p.add_argument("--ratio", required=True, type=float, help="Group ratio multiplier")
    p.add_argument("--desc", type=str, default=None, help="Group description for users")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    p = sub.add_parser("prefill-list", help="List prefill groups")
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON output to file")

    p = sub.add_parser("prefill-create", help="Create a prefill group")
    p.add_argument("--name", required=True, type=str)
    p.add_argument("--ratio", required=True, type=float)
    p.add_argument("--desc", type=str, default=None)
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    p = sub.add_parser("prefill-update", help="Update a prefill group")
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--name", type=str, default=None)
    p.add_argument("--ratio", type=float, default=None)
    p.add_argument("--desc", type=str, default=None)
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    p = sub.add_parser("prefill-delete", help="Delete a prefill group")
    p.add_argument("id", type=int)
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    args = parser.parse_args()
    client = make_client()

    commands = {
        "list": cmd_list,
        "user-groups": cmd_user_groups,
        "set-ratio": cmd_set_ratio,
        "prefill-list": cmd_prefill_list,
        "prefill-create": cmd_prefill_create,
        "prefill-update": cmd_prefill_update,
        "prefill-delete": cmd_prefill_delete,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
