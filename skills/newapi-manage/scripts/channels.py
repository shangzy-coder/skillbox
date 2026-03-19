#!/usr/bin/env python3
"""Channel management for new-api.

Usage:
  python3 channels.py list [--page N] [--status N] [--type N] [--output FILE]
  python3 channels.py get <id>
  python3 channels.py create --name NAME --type TYPE --key KEY [--models M1,M2] [--base-url URL] [--dry-run]
  python3 channels.py create --json  (reads JSON from stdin)
  python3 channels.py update --id ID [--name NAME] [--status N] [--key KEY] [--models M] [--base-url URL] [--priority N] [--tag TAG] [--group G] [--groups G1,G2] [--strip-prefix P] [--dry-run]
  python3 channels.py enable <id>
  python3 channels.py disable <id>
  python3 channels.py test <id>
  python3 channels.py test-all
  python3 channels.py search <keyword> [--output FILE]
  python3 channels.py models [--enabled]
  python3 channels.py delete <id> [--yes] [--dry-run]
  python3 channels.py copy <id>
  python3 channels.py fix
  python3 channels.py batch-disable --ids 1,2,3 [--dry-run]
  python3 channels.py batch-delete --ids 1,2,3 [--yes] [--dry-run]
  python3 channels.py batch-tag --ids 1,2,3 --tag TAG [--dry-run]
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, confirm, write_json, paginate


def cmd_list(client, args):
    params = {}
    if args.status is not None:
        params["status"] = args.status
    if args.type is not None:
        params["type"] = args.type
    data, total, wrapper = paginate(client, "/api/channel/", params, args.page)
    if args.output:
        write_json(wrapper, args.output)
        return
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
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would create channel: {json.dumps(body, indent=2, ensure_ascii=False)}")
        return
    result = check_success(client.post("/api/channel/", body))
    print("Channel created successfully.")
    print_json(result)


def _update_channel(client, channel_id, overrides):
    """Fetch channel, merge overrides, PUT back.
    Backend Updates(channel) writes ALL fields, so we must send
    the full current state with only our changes applied."""
    result = check_success(client.get(f"/api/channel/{channel_id}"))
    channel = result.get("data", result)
    if not isinstance(channel, dict):
        print(f"Error: unexpected response for channel {channel_id}", file=sys.stderr)
        sys.exit(1)
    for k, v in overrides.items():
        if v is not None:
            channel[k] = v
    check_success(client.put("/api/channel/", channel))
    print(f"Channel {channel_id} updated.")


def cmd_update(client, args):
    overrides = {}
    if args.name is not None:
        overrides["name"] = args.name
    if args.status is not None:
        overrides["status"] = args.status
    if args.key is not None:
        overrides["key"] = args.key
    if args.models is not None:
        overrides["models"] = args.models
    if args.base_url is not None:
        overrides["base_url"] = args.base_url
    if args.priority is not None:
        overrides["priority"] = args.priority
    if args.tag is not None:
        overrides["tag"] = args.tag
    if args.group is not None:
        overrides["group"] = args.group
    if args.groups is not None:
        overrides["groups"] = args.groups.split(",")
    if args.model_mapping is not None:
        overrides["model_mapping"] = args.model_mapping
    if args.strip_prefix is not None:
        # Auto-generate model_mapping and stripped models from current channel
        result = check_success(client.get(f"/api/channel/{args.id}"))
        ch = result.get("data", result)
        raw_models = [m.strip() for m in (ch.get("models", "") or "").split(",") if m.strip()]
        prefix = args.strip_prefix.rstrip("/") + "/"
        mapping = {}
        stripped = []
        for m in raw_models:
            if m.startswith(prefix):
                short = m[len(prefix):]
                mapping[short] = m
                stripped.append(short)
            else:
                stripped.append(m)
        overrides["models"] = ",".join(stripped)
        overrides["model_mapping"] = json.dumps(mapping, ensure_ascii=False)
    if not overrides:
        print("No fields to update. Use --name, --status, --key, etc.", file=sys.stderr)
        sys.exit(1)
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would update channel {args.id} with: {overrides}")
        return
    _update_channel(client, args.id, overrides)


def cmd_enable(client, args):
    _update_channel(client, args.id, {"status": 1})


def cmd_disable(client, args):
    _update_channel(client, args.id, {"status": 2})


def cmd_test(client, args):
    print(f"Testing channel {args.id}...")
    result = check_success(client.get(f"/api/channel/test/{args.id}"))
    print_json(result)


def cmd_test_all(client, args):
    print("Testing all channels (async, may take a while)...", flush=True)
    result = check_success(client.get("/api/channel/test"))
    # test-all is async: it triggers tests and returns immediately.
    # Per-channel results are stored in the channel model.
    # After tests complete, check channel list to see updated statuses.
    if result.get("success"):
        print("Test job started. Check channel list after a minute to see results.")
    else:
        print(f"Failed: {result.get('message', 'unknown error')}")
    print_json(result)


def cmd_search(client, args):
    result = check_success(client.get("/api/channel/search", {"keyword": args.keyword}))
    if args.output:
        write_json(result, args.output)
        return
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
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would delete channel {args.id}")
        return
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


def _parse_ids(s):
    """Parse comma-separated IDs, return list of ints."""
    try:
        return [int(x.strip()) for x in s.split(",") if x.strip()]
    except ValueError:
        print(f"Error: invalid ID list '{s}'. Expected comma-separated integers.", file=sys.stderr)
        sys.exit(1)


def cmd_batch_disable(client, args):
    ids = _parse_ids(args.ids)
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would disable channels: {ids}")
        return
    ok, fail = 0, 0
    for cid in ids:
        try:
            _update_channel(client, cid, {"status": 2})
            ok += 1
        except SystemExit:
            fail += 1
    print(f"Disabled {ok} channel(s), {fail} failed.")


def cmd_batch_delete(client, args):
    ids = _parse_ids(args.ids)
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would delete channels: {ids}")
        return
    if not args.yes:
        if not confirm(f"Delete {len(ids)} channels? [y/N] "):
            print("Cancelled.")
            return
    ok, fail = 0, 0
    for cid in ids:
        try:
            check_success(client.delete(f"/api/channel/{cid}"))
            print(f"  Deleted channel {cid}")
            ok += 1
        except SystemExit:
            fail += 1
    print(f"Deleted {ok} channel(s), {fail} failed.")


def cmd_batch_tag(client, args):
    ids = _parse_ids(args.ids)
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would set tag '{args.tag}' on channels: {ids}")
        return
    body = {"tag": args.tag, "ids": ids}
    result = check_success(client.post("/api/channel/batch/tag", body))
    print(f"Tag '{args.tag}' set on {len(ids)} channel(s).")
    print_json(result)


def main():
    parser = argparse.ArgumentParser(description="new-api channel management")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p = sub.add_parser("list", help="List channels")
    p.add_argument("--page", "-p", type=int, default=1)
    p.add_argument("--status", type=int, default=None)
    p.add_argument("--type", type=int, default=None)
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON output to file")

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
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # update
    p = sub.add_parser("update", help="Update a channel")
    p.add_argument("--id", required=True, type=int)
    p.add_argument("--name", type=str, default=None)
    p.add_argument("--status", type=int, default=None, help="1=enabled, 2=disabled")
    p.add_argument("--key", type=str, default=None)
    p.add_argument("--models", type=str, default=None)
    p.add_argument("--base-url", type=str, default=None)
    p.add_argument("--priority", type=int, default=None)
    p.add_argument("--tag", type=str, default=None)
    p.add_argument("--group", type=str, default=None, help="Single group name")
    p.add_argument("--groups", type=str, default=None, help="Comma-separated group list (sets groups array)")
    p.add_argument("--model-mapping", type=str, default=None, help="Model mapping JSON string")
    p.add_argument("--strip-prefix", type=str, default=None, help="Auto-strip prefix from models and generate mapping (e.g. 'ikun')")
    p.add_argument("--dry-run", action="store_true", help="Preview changes without executing")

    # enable
    p = sub.add_parser("enable", help="Enable a channel")
    p.add_argument("id", type=int)

    # disable
    p = sub.add_parser("disable", help="Disable a channel")
    p.add_argument("id", type=int)

    # test
    p = sub.add_parser("test", help="Test a channel")
    p.add_argument("id", type=int)

    # test-all
    sub.add_parser("test-all", help="Test all channels")

    # search
    p = sub.add_parser("search", help="Search channels")
    p.add_argument("keyword", type=str)
    p.add_argument("--output", "-o", type=str, default=None, help="Write JSON output to file")

    # models
    p = sub.add_parser("models", help="List available models")
    p.add_argument("--enabled", action="store_true", help="Only enabled models")

    # delete
    p = sub.add_parser("delete", help="Delete a channel")
    p.add_argument("id", type=int)
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # batch-disable
    p = sub.add_parser("batch-disable", help="Disable multiple channels by ID")
    p.add_argument("--ids", required=True, type=str, help="Comma-separated channel IDs")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # batch-delete
    p = sub.add_parser("batch-delete", help="Delete multiple channels by ID")
    p.add_argument("--ids", required=True, type=str, help="Comma-separated channel IDs")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # batch-tag
    p = sub.add_parser("batch-tag", help="Set tag on multiple channels")
    p.add_argument("--ids", required=True, type=str, help="Comma-separated channel IDs")
    p.add_argument("--tag", required=True, type=str, help="Tag to set")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

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
        "update": cmd_update,
        "enable": cmd_enable,
        "disable": cmd_disable,
        "test": cmd_test,
        "test-all": cmd_test_all,
        "search": cmd_search,
        "models": cmd_models,
        "delete": cmd_delete,
        "batch-disable": cmd_batch_disable,
        "batch-delete": cmd_batch_delete,
        "batch-tag": cmd_batch_tag,
        "copy": cmd_copy,
        "fix": cmd_fix,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
