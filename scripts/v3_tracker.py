#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/v3_tracker.py
Manages and tracks the Master V3 Synthesis Audit progress across all 30 Juz and 127 Subchunks.

Usage:
  python scripts/v3_tracker.py init             # Initialize / reset v3_audit_tracker.tsv
  python scripts/v3_tracker.py status           # Print current audit progress overview
  python scripts/v3_tracker.py mark <chunk_name_or_id> DONE
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACKER_TSV = REPO_ROOT / "v3_audit_tracker.tsv"

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from export_v3_audit_chunk import SUBCHUNKS_127, parse_key


def count_verses_in_range(st: str, en: str) -> int:
    # Approximate or exact count using key parser
    s1, a1 = parse_key(st)
    s2, a2 = parse_key(en)
    if s1 == s2:
        return a2 - a1 + 1
    # Multi-surah approximation (sufficient for tracking header)
    return 45


def init_tracker():
    rows = []
    chunk_id = 1
    for juz_num in range(1, 31):
        juz_subchunks = [sc for sc in SUBCHUNKS_127 if sc[0] == juz_num]
        for part_idx, (_, r_str) in enumerate(juz_subchunks, 1):
            st, en = r_str.split("-")
            clean_r_str = r_str.replace(":", "_").replace("-", "_to_")
            fname = f"juz_{juz_num:02d}_part{part_idx}_{clean_r_str}.txt"
            vcount = count_verses_in_range(st, en)

            rows.append({
                "chunk_id": str(chunk_id),
                "juz": str(juz_num),
                "chunk_in_juz": str(part_idx),
                "range": r_str,
                "verses": str(vcount),
                "filename": fname,
                "status": "PENDING",
                "fix_count": "0",
                "fixes_summary": "",
                "updated_at": "",
            })
            chunk_id += 1

    with open(TRACKER_TSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "chunk_id", "juz", "chunk_in_juz", "range", "verses",
            "filename", "status", "fix_count", "fixes_summary", "updated_at"
        ], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Initialized {len(rows)} subchunks across 30 Juz -> {TRACKER_TSV}")


def show_status():
    if not TRACKER_TSV.exists():
        print("Tracker file does not exist. Run: python scripts/v3_tracker.py init")
        return

    with open(TRACKER_TSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    total = len(rows)
    done = sum(1 for r in rows if r["status"] == "DONE")
    in_prog = sum(1 for r in rows if r["status"] == "IN_PROGRESS")
    pending = total - done - in_prog
    total_fixes = sum(int(r.get("fix_count", 0) or 0) for r in rows)

    pct = (done / total * 100) if total else 0.0

    print("=" * 60)
    print("      THAI QURAN MASTER V3 SYNTHESIS AUDIT TRACKER")
    print("=" * 60)
    print(f"Total Subchunks : {total} (127 gold-standard chunks across 30 Juz)")
    print(f"Completed (DONE): {done} / {total} ({pct:.1f}%)")
    print(f"In Progress     : {in_prog}")
    print(f"Pending         : {pending}")
    print(f"Total Fixes     : {total_fixes}")
    print("=" * 60)

    # Show by Juz
    for j in range(1, 31):
        j_rows = [r for r in rows if r["juz"] == str(j)]
        j_done = sum(1 for r in j_rows if r["status"] == "DONE")
        j_tot = len(j_rows)
        bar = "✓" if j_done == j_tot else (f"{j_done}/{j_tot}" if j_done > 0 else "·")
        print(f"Juz {j:02d}: [{bar:^5}]", end="  " if j % 5 != 0 else "\n")
    print("\n" + "=" * 60)


def mark_chunk(chunk_id_or_name: str, status: str):
    with open(TRACKER_TSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    found = False
    for r in rows:
        if chunk_id_or_name.isdigit():
            is_match = (r["chunk_id"] == chunk_id_or_name)
        else:
            is_match = (
                r["filename"] == chunk_id_or_name
                or Path(r["filename"]).stem == chunk_id_or_name
                or chunk_id_or_name in r["filename"]
            )

        if is_match:
            r["status"] = status.upper()
            r["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            found = True
            print(f"Updated Chunk #{r['chunk_id']} ({r['filename']}) -> status: {r['status']}")
            break

    if not found:
        print(f"Error: Chunk '{chunk_id_or_name}' not found.")
        sys.exit(1)

    with open(TRACKER_TSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "chunk_id", "juz", "chunk_in_juz", "range", "verses",
            "filename", "status", "fix_count", "fixes_summary", "updated_at"
        ], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Master V3 Synthesis Audit Tracker")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Initialize or reset tracker TSV")
    subparsers.add_parser("status", help="Show current audit progress")

    mark_p = subparsers.add_parser("mark", help="Mark a chunk status")
    mark_p.add_argument("chunk", type=str, help="Chunk ID or filename")
    mark_p.add_argument("status", type=str, choices=["PENDING", "IN_PROGRESS", "DONE"], help="New status")

    args = parser.parse_args()

    if args.command == "init":
        init_tracker()
    elif args.command == "status":
        show_status()
    elif args.command == "mark":
        mark_chunk(args.chunk, args.status)
    else:
        show_status()


if __name__ == "__main__":
    main()
