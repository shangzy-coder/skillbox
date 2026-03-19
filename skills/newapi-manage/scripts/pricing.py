#!/usr/bin/env python3
"""Model pricing/ratio management for new-api.

Usage:
  python3 pricing.py list
  python3 pricing.py get <model>
  python3 pricing.py set --model MODEL --ratio RATIO
  python3 pricing.py reset [--yes]
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, confirm, write_json, get_option


def cmd_list(client, args):
    result = check_success(client.get("/api/pricing"))
    data = result.get("data", {})
    group_ratio = result.get("group_ratio", {})

    if group_ratio:
        print("Group Ratios:")
        for name, ratio in sorted(group_ratio.items()):
            print(f"  {name:<20} ratio={ratio}")
        print()

    if isinstance(data, dict):
        models = data.get("models", data)
        if isinstance(models, list):
            print(f"Models ({len(models)}):")
            for m in models:
                if isinstance(m, dict):
                    name = m.get("model", m.get("id", "?"))
                    input_r = m.get("input", m.get("prompt", "?"))
                    output_r = m.get("output", m.get("completion", "?"))
                    print(f"  {name:<40} input={input_r:<10} output={output_r}")
        elif isinstance(models, dict):
            print(f"Models ({len(models)}):")
            for name, ratio in sorted(models.items()):
                if isinstance(ratio, (int, float)):
                    print(f"  {name:<40} ratio={ratio}")
                elif isinstance(ratio, dict):
                    input_r = ratio.get("input", "?")
                    output_r = ratio.get("output", "?")
                    print(f"  {name:<40} input={input_r:<10} output={output_r}")
    else:
        print_json(data)


def cmd_get(client, args):
    result = check_success(client.get("/api/pricing"))
    data = result.get("data", {})
    model_name = args.model

    if isinstance(data, dict):
        models = data.get("models", data)
        if isinstance(models, list):
            found = [m for m in models if isinstance(m, dict) and m.get("model", m.get("id", "")) == model_name]
            if found:
                print_json(found[0])
            else:
                print(f"Model '{model_name}' not found in pricing data.", file=sys.stderr)
                sys.exit(1)
        elif isinstance(models, dict) and model_name in models:
            print(f"{model_name}: {models[model_name]}")
        else:
            print(f"Model '{model_name}' not found in pricing data.", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unexpected pricing data format.", file=sys.stderr)
        sys.exit(1)


def cmd_set(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would set model '{args.model}' ratio to {args.ratio}")
        return
    raw = get_option(client, "ModelRatio")
    try:
        ratios = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        ratios = {}

    ratios[args.model] = args.ratio
    updated = json.dumps(ratios, ensure_ascii=False)
    check_success(client.put("/api/option/", {"key": "ModelRatio", "value": updated}))
    print(f"Model '{args.model}' ratio set to {args.ratio}.")


def cmd_reset(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would reset all model ratios to defaults")
        return
    if not args.yes:
        if not confirm("Reset all model ratios to defaults? [y/N] "):
            print("Cancelled.")
            return
    check_success(client.post("/api/option/rest_model_ratio"))
    print("Model ratios reset to defaults.")


def main():
    parser = argparse.ArgumentParser(description="new-api pricing/ratio management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all model pricing/ratios")

    p = sub.add_parser("get", help="Get a specific model's ratio")
    p.add_argument("model", type=str)

    p = sub.add_parser("set", help="Set a model's ratio")
    p.add_argument("--model", required=True, type=str)
    p.add_argument("--ratio", required=True, type=float)
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    p = sub.add_parser("reset", help="Reset all ratios to defaults")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    args = parser.parse_args()
    client = make_client()

    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "set": cmd_set,
        "reset": cmd_reset,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
