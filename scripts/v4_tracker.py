#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/v4_tracker.py
Manages the TSV audit tracker (v4_audit_tracker.tsv) for all 127 chunks across 30 Juz.
Supports viewing progress, marking chunks done, and auto-logging applied fixes.

Usage:
  python scripts/v4_tracker.py                  # Show progress summary
  python scripts/v4_tracker.py --list           # List all 127 chunks and status
  python scripts/v4_tracker.py --juz 1          # Show status of Juz 1
  python scripts/v4_tracker.py --mark 1 1 DONE "Clean, verified, no issues"
  python scripts/v4_tracker.py --reset          # Re-initialize tracker from scratch
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(r"H:\gits\thai_quran_translation_v4")
TRACKER_TSV_PATH = REPO_ROOT / "v4_audit_tracker.tsv"
V4_DATA_PATH = REPO_ROOT / "data" / "06_tq_spacing_and_scholar_fixed.json"

from export_v4_audit_chunk import SUBCHUNKS_127, is_in_range, parse_key

TSV_HEADERS = [
    "chunk_id",
    "juz",
    "chunk_in_juz",
    "range",
    "verses",
    "filename",
    "status",
    "fix_count",
    "fixes_summary",
    "updated_at",
]


def load_all_keys() -> list[str]:
    with open(V4_DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    return [r["ayah_key"] for r in records]


def init_tracker(force: bool = False) -> list[dict]:
    if TRACKER_TSV_PATH.exists() and not force:
        return load_tracker()

    all_keys = load_all_keys()

    # Build chunk records
    rows = []
    chunk_counter_per_juz = {}

    for idx, (juz, r_str) in enumerate(SUBCHUNKS_127, start=1):
        chunk_in_j = chunk_counter_per_juz.get(juz, 0) + 1
        chunk_counter_per_juz[juz] = chunk_in_j

        st, en = r_str.split("-")
        v_keys = [k for k in all_keys if is_in_range(k, st, en)]
        clean_r_str = r_str.replace(":", "_").replace("-", "_to_")
        fn = f"juz_{juz:02d}_part{chunk_in_j}_{clean_r_str}.txt"

        rows.append({
            "chunk_id": str(idx),
            "juz": str(juz),
            "chunk_in_juz": str(chunk_in_j),
            "range": r_str,
            "verses": str(len(v_keys)),
            "filename": fn,
            "status": "PENDING",
            "fix_count": "0",
            "fixes_summary": "",
            "updated_at": "",
        })

    save_tracker(rows)
    print(f"Initialized {len(rows)} chunks in {TRACKER_TSV_PATH}")
    return rows


def load_tracker() -> list[dict]:
    if not TRACKER_TSV_PATH.exists():
        return init_tracker()

    rows = []
    with open(TRACKER_TSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            rows.append(r)
    return rows


def save_tracker(rows: list[dict]):
    with open(TRACKER_TSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TSV_HEADERS, delimiter="\t")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def find_chunk_for_ayah(ayah_key: str, tracker_rows: list[dict]) -> dict | None:
    for row in tracker_rows:
        r_str = row["range"]
        st, en = r_str.split("-")
        if is_in_range(ayah_key, st, en):
            return row
    return None


def record_applied_fixes(validated_fixes: list[dict]):
    """Called automatically by apply_v4_fixes.py when fixes are applied."""
    tracker_rows = load_tracker()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Group fixes by chunk_id
    fixes_by_chunk = {}
    for vf in validated_fixes:
        ak = vf["ayah"]
        chunk = find_chunk_for_ayah(ak, tracker_rows)
        if chunk:
            cid = chunk["chunk_id"]
            fixes_by_chunk.setdefault(cid, []).append(vf)

    for cid, fixes in fixes_by_chunk.items():
        row = next(r for r in tracker_rows if r["chunk_id"] == cid)
        current_count = int(row.get("fix_count") or 0)
        row["fix_count"] = str(current_count + len(fixes))
        row["status"] = "DONE"
        row["updated_at"] = now_str

        # Format fix summaries
        summaries = []
        for f in fixes:
            summaries.append(f"{f['ayah']} [{f['type']}]: '{f['target']}'->'{f['replacement']}'")
        new_summary = "; ".join(summaries)

        existing = row.get("fixes_summary", "").strip()
        if existing:
            row["fixes_summary"] = f"{existing} | {new_summary}"
        else:
            row["fixes_summary"] = new_summary

    save_tracker(tracker_rows)
    print(f"[TRACKER] Updated {len(fixes_by_chunk)} chunk(s) in {TRACKER_TSV_PATH}")


def mark_chunk(juz: int, chunk_in_juz: int, status: str, note: str = ""):
    rows = load_tracker()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    found = False

    for r in rows:
        if int(r["juz"]) == juz and int(r["chunk_in_juz"]) == chunk_in_juz:
            r["status"] = status.upper()
            r["updated_at"] = now_str
            if note:
                existing = r.get("fixes_summary", "").strip()
                r["fixes_summary"] = f"{existing} | {note}" if existing else note
            found = True
            print(f"[TRACKER] Juz {juz} Chunk {chunk_in_juz} ({r['range']}) marked as {r['status']}.")
            break

    if not found:
        print(f"[ERROR] Could not find Juz {juz} Chunk {chunk_in_juz} in tracker.")
        return

    save_tracker(rows)


def print_progress(juz_filter: int = None, show_all: bool = False):
    rows = load_tracker()
    total = len(rows)
    done_count = sum(1 for r in rows if r["status"] in ("DONE", "NO_FIX", "VERIFIED"))
    total_fixes = sum(int(r.get("fix_count") or 0) for r in rows)

    pct = (done_count / total) * 100 if total > 0 else 0

    print("=" * 80)
    print("           THAIQURAN V4 TRANSLATION AUDIT TRACKER (TSV)")
    print("=" * 80)
    print(f"Overall Progress: {done_count}/{total} Chunks Done ({pct:.1f}%) | Total Fixes Logged: {total_fixes}")
    print("-" * 80)

    # Filter rows if juz requested
    display_rows = rows
    if juz_filter:
        display_rows = [r for r in rows if int(r["juz"]) == juz_filter]
        print(f"Displaying Juz {juz_filter} only:")

    if show_all or juz_filter:
        print(f"{'ID':<4} {'Juz':<4} {'Part':<5} {'Range':<16} {'Verses':<7} {'Status':<10} {'Fixes':<6} {'Summary'}")
        print("-" * 80)
        for r in display_rows:
            sm = r["fixes_summary"]
            if len(sm) > 40:
                sm = sm[:37] + "..."
            print(f"{r['chunk_id']:<4} {r['juz']:<4} {r['chunk_in_juz']:<5} {r['range']:<16} {r['verses']:<7} {r['status']:<10} {r['fix_count']:<6} {sm}")
    else:
        # Show recent activity or pending next
        pending = [r for r in rows if r["status"] == "PENDING"]
        done = [r for r in rows if r["status"] != "PENDING"]
        if done:
            print("\nRecent Activity (Completed Chunks):")
            for r in done[-5:]:
                print(f"  [DONE] Chunk #{r['chunk_id']} (Juz {r['juz']} Part {r['chunk_in_juz']} - {r['range']}): {r['fix_count']} fixes -> {r['fixes_summary']}")
        if pending:
            nxt = pending[0]
            print(f"\nNext Pending Chunk: Chunk #{nxt['chunk_id']} (Juz {nxt['juz']} Part {nxt['chunk_in_juz']} - {nxt['range']})")
            print(f"File to inspect: audit_chunks/subchunks/{nxt['filename']}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="ThaiQuran v4 TSV Audit Progress Tracker")
    parser.add_argument("--list", action="store_true", help="List all 127 chunks")
    parser.add_argument("--juz", type=int, help="Show chunks for specific Juz (1-30)")
    parser.add_argument("--reset", action="store_true", help="Reset/Re-init tracker TSV from scratch")
    parser.add_argument("--mark", nargs="+", help="Mark chunk status: --mark <juz> <chunk_in_juz> <STATUS> [NOTE]")
    args = parser.parse_args()

    if args.reset:
        init_tracker(force=True)
        return

    if args.mark:
        juz = int(args.mark[0])
        chunk_in_j = int(args.mark[1])
        status = args.mark[2]
        note = " ".join(args.mark[3:]) if len(args.mark) > 3 else ""
        mark_chunk(juz, chunk_in_j, status, note)
        return

    print_progress(juz_filter=args.juz, show_all=args.list)


if __name__ == "__main__":
    main()
