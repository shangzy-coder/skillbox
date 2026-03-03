#!/usr/bin/env python3
"""Channel management for new-api.

Usage:
  python3 channels.py list [--page N] [--status N] [--type N]
  python3 channels.py get <id>
  python3 channels.py create --name NAME --type TYPE --key KEY [--models M1,M2] [--base-url URL]
  python3 channels.py create --json  (reads JSON from stdin)
  python3 channels.py test <id>
  python3 channels.py test-all
  python3 channels.py search <keyword>
  python3 channels.py models [--enabled]
  python3 channels.py delete <id> [--yes]
  python3 channels.py copy <id>
  python3 channels.py fix
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, confirm


def cmd_list(client, args):
    params = {"p": args.page}
    if args.status is not None:
        params["status"] = args.status
    if args.type is not None:
        params["type"] = args.type
    result = check_success(client.get("/api/channel/", params))
    wrapper = result.get("data", {})
    data = wrapper.get("items", []) if isinstance(wrapper, dict) else wrapper
    total = wrapper.get("total", len(data)) if isinstance(wrapper, dict) else len(data)
    print(f"Channels (page {args.page}, total {total}):")
    if not data:
        print("  (none)")
        return
    for ch in data:
        status_str = "enabled" if ch.get("status") == 1 else f"status={ch.get('status')}"
        print(f"  [{ch.get('id'):>4}] {ch.get('name', '?'):<30} type={ch.get('type')}  {status_str}  balance={ch.get('balance', 0)}")


def cmd_get(client, args):
    result = check_success(client.get(f"/api/channel/{args.id}"))
    print_json(result.get("data", result))


def cmd_create(client, args):
    if args.json:
        raw = sys.stdin.read()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)
        # If user already passed the nested format, use as-is
        if "channel" in payload and "mode" in payload:
            body = payload
        else:
            # Wrap in the expected nested format
            body = {"mode": "single", "channel": payload}
    else:
        if not args.name or args.type is None or not args.key:
            print("Error: --name, --type, and --key are required (or use --json for stdin)", file=sys.stderr)
            sys.exit(1)
        channel = {
            "name": args.name,
            "type": args.type,
            "key": args.key,
            "status": 1,
        }
        if args.models:
            channel["models"] = args.models
        if args.base_url:
            channel["base_url"] = args.base_url
        if args.groups:
            channel["groups"] = args.groups.split(",")
        if args.model_mapping:
            channel["model_mapping"] = args.model_mapping
        if args.priority is not None:
            channel["priority"] = args.priority
        body = {"mode": "single", "channel": channel}

    result = check_success(client.post("/api/channel/", body))
    print("Channel created successfully.")
    print_json(result)


def cmd_test(client, args):
    print(f"Testing channel {args.id}...")
    result = check_success(client.get(f"/api/channel/test/{args.id}"))
    print_json(result)


def cmd_test_all(client, args):
    print("Testing all channels (this may take a while)...")
    result = check_success(client.get("/api/channel/test"))
    print_json(result)


def cmd_search(client, args):
    result = check_success(client.get("/api/channel/search", {"keyword": args.keyword}))
    wrapper = result.get("data", {})
    data = wrapper.get("items", []) if isinstance(wrapper, dict) else wrapper
    total = wrapper.get("total", len(data)) if isinstance(wrapper, dict) else len(data)
    print(f"Search results for '{args.keyword}' ({total} found):")
    for ch in data:
        print(f"  [{ch.get('id'):>4}] {ch.get('name', '?'):<30} type={ch.get('type')}  status={ch.get('status')}")
    if not data:
        print("  (none)")


def cmd_models(client, args):
    endpoint = "/api/channel/models_enabled" if args.enabled else "/api/channel/models"
    result = check_success(client.get(endpoint))
    data = result.get("data", result)
    if isinstance(data, list):
        print(f"Models ({len(data)}):")
        for m in data:
            if isinstance(m, dict):
                print(f"  {m.get('id', m)}")
            else:
                print(f"  {m}")
    else:
        print_json(data)


def cmd_delete(client, args):
    if not args.yes:
        if not confirm(f"Delete channel {args.id}? [y/N] "):
            print("Cancelled.")
            return
    result = check_success(client.delete(f"/api/channel/{args.id}"))
    print(f"Channel {args.id} deleted.")
    print_json(result)


def cmd_copy(client, args):
    result = check_success(client.post(f"/api/channel/copy/{args.id}"))
    print(f"Channel {args.id} copied.")
    print_json(result)


def cmd_fix(client, args):
    result = check_success(client.post("/api/channel/fix"))
    print("Channel abilities fixed.")
    print_json(result)


def main():
    parser = argparse.ArgumentParser(description="new-api channel management")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="List channels")
    p.add_argument("--page", "-p", type=int, default=0)
    p.add_argument("--status", type=int, default=None)
    p.add_argument("--type", type=int, default=None)

    # get
    p = sub.add_parser("get", help="Get channel details")
    p.add_argument("id", type=int)

    # create
    p = sub.add_parser("create", help="Create a channel")
    p.add_argument("--json", action="store_true", help="Read channel JSON from stdin")
    p.add_argument("--name", type=str)
    p.add_argument("--type", type=int, dest="type")
    p.add_argument("--key", type=str)
    p.add_argument("--models", type=str, help="Comma-separated model list")
    p.add_argument("--base-url", type=str)
    p.add_argument("--groups", type=str, help="Comma-separated group list")
    p.add_argument("--model-mapping", type=str, help="Model mapping JSON string")
    p.add_argument("--priority", type=int)

    # test
    p = sub.add_parser("test", help="Test a channel")
    p.add_argument("id", type=int)

    # test-all
    sub.add_parser("test-all", help="Test all channels")

    # search
    p = sub.add_parser("search", help="Search channels")
    p.add_argument("keyword", type=str)

    # models
    p = sub.add_parser("models", help="List available models")
    p.add_argument("--enabled", action="store_true", help="Only enabled models")

    # delete
    p = sub.add_parser("delete", help="Delete a channel")
    p.add_argument("id", type=int)
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    # copy
    p = sub.add_parser("copy", help="Copy a channel")
    p.add_argument("id", type=int)

    # fix
    sub.add_parser("fix", help="Fix channel abilities")

    args = parser.parse_args()
    client = make_client()

    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "create": cmd_create,
        "test": cmd_test,
        "test-all": cmd_test_all,
        "search": cmd_search,
        "models": cmd_models,
        "delete": cmd_delete,
        "copy": cmd_copy,
        "fix": cmd_fix,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
