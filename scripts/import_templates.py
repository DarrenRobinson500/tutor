#!/usr/bin/env python3
"""Bulk template import script.

Reads a templates_to_import.yaml file and imports each template via the API.

Usage:
  python import_templates.py
  python import_templates.py --file path/to/file.yaml
  python import_templates.py --dry-run
  python import_templates.py --failed-only
  python import_templates.py --verbose

Requires API_BASE_URL and API_TOKEN in the project root .env file.
"""

import argparse
import os
import sys
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

# Load .env from the project root (one level above scripts/)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_TOKEN    = os.getenv("API_TOKEN", "")

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
DIVIDER = "─" * 45


def _headers():
    h = {"Content-Type": "application/json"}
    if API_TOKEN:
        h["Authorization"] = f"Bearer {API_TOKEN}"
    return h


def _load_file(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        print(f"\n✗ YAML parse error in {path}:\n  {e}")
        sys.exit(1)
    if not isinstance(data, dict):
        print(f"\n✗ Expected a YAML mapping at the top level of {path}")
        sys.exit(1)
    return data


def _validate(data: dict, path: Path) -> tuple[int, list[dict]]:
    year = data.get("year")
    if year is None:
        print(f"\n✗ Missing required field 'year' in {path}")
        sys.exit(1)
    year = int(year)

    entries = data.get("templates")
    if not entries or not isinstance(entries, list):
        print(f"\n✗ No templates found in {path}")
        sys.exit(1)

    errors = []
    for i, entry in enumerate(entries, start=1):
        if not isinstance(entry.get("skill_detail"), str) or not entry["skill_detail"].strip():
            errors.append(f"  Entry {i}: missing or empty 'skill_detail'")
        diff = entry.get("difficulty", "")
        if str(diff).lower() not in VALID_DIFFICULTIES:
            errors.append(f"  Entry {i}: difficulty '{diff}' must be easy, medium, or hard")
        if not str(entry.get("yaml") or "").strip():
            errors.append(f"  Entry {i}: missing or empty 'yaml' block")

    if errors:
        print(f"\n✗ Validation failed ({len(errors)} error(s)):")
        for e in errors:
            print(e)
        sys.exit(1)

    return year, entries


def _resolve_skill_details(year: int, entries: list[dict], dry_run: bool) -> dict[str, dict]:
    unique_names = list(dict.fromkeys(e["skill_detail"] for e in entries))
    resolved: dict[str, dict] = {}
    not_found: list[str] = []

    print(f"\nResolving {len(unique_names)} skill detail name(s) for Year {year}…")
    for name in unique_names:
        url = f"{API_BASE_URL}/api/skills/resolve_detail/?name={requests.utils.quote(name)}&year={year}"
        try:
            r = requests.get(url, headers=_headers(), timeout=15)
        except requests.RequestException as exc:
            print(f"  ✗ Network error resolving '{name}': {exc}")
            sys.exit(1)

        if r.status_code == 200:
            resolved[name] = r.json()
            print(f"  ✓ {name!r}")
        else:
            not_found.append(name)
            print(f"  ✗ Not found: {name!r}")

    if not_found:
        print(f"\n✗ {len(not_found)} skill detail name(s) not found for Year {year}:")
        for n in not_found:
            print(f'    "{n}"')
        print("  Check names match exactly (case-sensitive) and the year is correct.")
        sys.exit(1)

    return resolved


def _import_entries(year: int, entries: list[dict], resolved: dict[str, dict],
                    dry_run: bool, verbose: bool) -> list[dict]:
    failed: list[dict] = []
    succeeded = 0
    total = len(entries)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Importing {total} template(s) — Year {year}\n")

    for entry in entries:
        name    = entry["skill_detail"]
        diff    = entry["difficulty"]
        content = entry["yaml"]
        detail  = resolved[name]

        payload = {
            "skill_detail_id": detail["id"],
            "year":            year,
            "difficulty":      diff,
            "yaml":            content,
        }

        if dry_run:
            print(f"  [dry-run] Would import: {name!r} — {diff}")
            if verbose:
                print(f"    skill_detail_id={detail['id']}  skill_id={detail['skill_id']}")
            succeeded += 1
            continue

        if verbose:
            print(f"  → POST /api/templates/import_named/")
            print(f"    skill_detail_id={detail['id']}  difficulty={diff}")

        try:
            r = requests.post(
                f"{API_BASE_URL}/api/templates/import_named/",
                json=payload,
                headers=_headers(),
                timeout=30,
            )
        except requests.RequestException as exc:
            msg = f"Network error: {exc}"
            print(f"  ✗ Failed:   {name!r} — {diff}  ({msg})")
            failed.append({**entry, "_error": msg})
            continue

        if r.status_code in (200, 201):
            tid = r.json().get("id", "?")
            print(f"  ✓ Imported: {name!r} — {diff}  (id={tid})")
            if verbose:
                print(f"    Response: {r.text}")
            succeeded += 1
        else:
            msg = f"HTTP {r.status_code}: {r.text[:200]}"
            print(f"  ✗ Failed:   {name!r} — {diff}")
            print(f"    {msg}")
            failed.append({**entry, "_error": msg})

    return failed


def _write_failed(year: int, failed: list[dict], out_path: Path):
    clean = [{k: v for k, v in e.items() if not k.startswith("_")} for e in failed]
    data = {"year": year, "templates": clean}
    out_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8")
    print(f"\n  Failed entries written to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Bulk template import")
    parser.add_argument("--file",        default="templates_to_import.yaml", help="Input YAML file")
    parser.add_argument("--dry-run",     action="store_true", help="Validate and resolve but do not POST")
    parser.add_argument("--failed-only", action="store_true", help="Retry from failed_imports.yaml")
    parser.add_argument("--verbose",     action="store_true", help="Print full request/response details")
    args = parser.parse_args()

    input_path = Path(args.file if not args.failed_only else "failed_imports.yaml")
    if not input_path.exists():
        print(f"\n✗ File not found: {input_path}")
        sys.exit(1)

    data   = _load_file(input_path)
    year, entries = _validate(data, input_path)
    resolved = _resolve_skill_details(year, entries, args.dry_run)
    failed   = _import_entries(year, entries, resolved, args.dry_run, args.verbose)

    total     = len(entries)
    succeeded = total - len(failed)

    print(f"\n{DIVIDER}")
    print(f"Import {'(dry run) ' if args.dry_run else ''}complete — Year {year}")
    print(f"  Attempted:  {total}")
    print(f"  Succeeded:  {succeeded}")
    print(f"  Failed:     {len(failed)}")
    print(DIVIDER)

    if failed:
        print("\nFailed entries:")
        for e in failed:
            print(f"  • {e['skill_detail']!r} — {e['difficulty']}")
        if not args.dry_run:
            _write_failed(year, failed, Path("failed_imports.yaml"))


if __name__ == "__main__":
    main()
