#!/usr/bin/env python3
"""Notice & Announcement management for new-api.

Usage:
  python3 notice.py get                     Get current Notice (rich text banner)
  python3 notice.py set <content>           Set Notice (supports Markdown/HTML)
  python3 notice.py set --file FILE         Set Notice from file
  python3 notice.py clear [--yes]           Clear Notice

  python3 notice.py ann-list                List all Announcements
  python3 notice.py ann-add <content> [--type TYPE] [--extra TEXT]
  python3 notice.py ann-clear [--yes]       Clear all Announcements
  python3 notice.py ann-delete <index> [--yes]  Delete one Announcement by index (0-based)
"""

import argparse
import datetime
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from newapi_client import make_client, print_json, check_success, confirm, get_option, get_option_json, set_option


def _get_announcements(client):
    """Get current announcements as a Python list."""
    raw = get_option(client, "console_setting.announcements")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _set_announcements(client, announcements):
    """Save announcements list back to the server."""
    set_option(client, "console_setting.announcements", announcements)


# -- Notice commands ----------------------------------------------------------

def cmd_get(client, args):
    result = client.get("/api/notice")
    notice = result.get("data", "")
    if notice:
        print(notice)
    else:
        print("(no notice set)")


def cmd_set(client, args):
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = args.content
    if not content:
        print("Error: no content provided", file=sys.stderr)
        sys.exit(1)
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would set Notice to: {content[:100]}{'...' if len(content) > 100 else ''}")
        return
    result = check_success(client.put("/api/option/", {
        "key": "Notice",
        "value": content,
    }))
    print("Notice updated.")


def cmd_clear(client, args):
    if getattr(args, "dry_run", False):
        print("[DRY RUN] Would clear the Notice banner")
        return
    if not args.yes:
        if not confirm("Clear the Notice banner? [y/N] "):
            print("Cancelled.")
            return
    check_success(client.put("/api/option/", {"key": "Notice", "value": ""}))
    print("Notice cleared.")


# -- Announcement commands ----------------------------------------------------

def cmd_ann_list(client, args):
    announcements = _get_announcements(client)
    if not announcements:
        print("No announcements.")
        return
    print(f"Announcements ({len(announcements)}):")
    for i, a in enumerate(announcements):
        tag = a.get("type", "default")
        extra = f'  ({a.get("extra")})' if a.get("extra") else ""
        date = a.get("publishDate", "?")[:10]
        print(f"  [{i}] [{tag:<8}] {date}  {a.get('content', '')}{extra}")


def cmd_ann_add(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would add announcement: '{args.content}' (type={args.type})")
        return
    announcements = _get_announcements(client)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "content": args.content,
        "publishDate": now,
        "type": args.type,
    }
    if args.extra:
        entry["extra"] = args.extra
    announcements.append(entry)
    _set_announcements(client, announcements)
    print(f"Announcement added (type={args.type}, total={len(announcements)}).")


def cmd_ann_delete(client, args):
    if getattr(args, "dry_run", False):
        print(f"[DRY RUN] Would delete announcement at index {args.index}")
        return
    announcements = _get_announcements(client)
    if args.index < 0 or args.index >= len(announcements):
        print(f"Error: index {args.index} out of range (0-{len(announcements) - 1})", file=sys.stderr)
        sys.exit(1)
    target = announcements[args.index]
    if not args.yes:
        if not confirm(f"Delete announcement [{args.index}] \"{target.get('content', '')[:50]}\"? [y/N] "):
            print("Cancelled.")
            return
    announcements.pop(args.index)
    _set_announcements(client, announcements)
    print(f"Announcement [{args.index}] deleted (remaining={len(announcements)}).")


def cmd_ann_clear(client, args):
    if getattr(args, "dry_run", False):
        print("[DRY RUN] Would clear all announcements")
        return
    if not args.yes:
        if not confirm("Clear ALL announcements? [y/N] "):
            print("Cancelled.")
            return
    _set_announcements(client, [])
    print("All announcements cleared.")


def main():
    parser = argparse.ArgumentParser(description="new-api notice & announcement management")
    sub = parser.add_subparsers(dest="command", required=True)

    # Notice: get
    sub.add_parser("get", help="Get current Notice banner")

    # Notice: set
    p = sub.add_parser("set", help="Set Notice banner")
    p.add_argument("content", nargs="?", default="", help="Notice content (Markdown/HTML)")
    p.add_argument("--file", "-f", help="Read content from file")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Notice: clear
    p = sub.add_parser("clear", help="Clear Notice banner")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Announcements: list
    sub.add_parser("ann-list", help="List all announcements")

    # Announcements: add
    p = sub.add_parser("ann-add", help="Add an announcement")
    p.add_argument("content", help="Announcement content (max 500 chars)")
    p.add_argument("--type", "-t", default="default",
                   choices=["default", "ongoing", "success", "warning", "error"],
                   help="Announcement type (default: default)")
    p.add_argument("--extra", "-e", help="Extra description (max 200 chars)")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Announcements: delete
    p = sub.add_parser("ann-delete", help="Delete an announcement by index")
    p.add_argument("index", type=int, help="0-based index from ann-list")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Announcements: clear
    p = sub.add_parser("ann-clear", help="Clear all announcements")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    args = parser.parse_args()
    client = make_client()

    commands = {
        "get": cmd_get,
        "set": cmd_set,
        "clear": cmd_clear,
        "ann-list": cmd_ann_list,
        "ann-add": cmd_ann_add,
        "ann-delete": cmd_ann_delete,
        "ann-clear": cmd_ann_clear,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
