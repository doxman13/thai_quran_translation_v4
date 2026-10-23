#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/sync_v3_to_all.py
Gradual & Full Production Synchronizer for Master V3 Synthesis:
Syncs audited King Fahd Master V3 translations & authentic footnotes
directly into the live Web (thai-quran-web) and Mobile App (thai-quran-app) ecosystems.

Features:
  1. Gradual Sync by Completed Chunks: By default (--completed-only), syncs only
     the verses from Subchunks marked DONE in v3_audit_tracker.tsv.
  2. Sync by Juz: Use --juz 1 to sync an entire completed Juz.
  3. Full Sync: Use --all to sync all 6,236 verses.
  4. Formats:
     - Plain text (translation_v3) -> thai_v3.json (Web & App) + quran_offline.db (App SQLite)
     - Annotated text with [1], [2] -> thai_footnotes.json (Web & App)
  5. Dry-Run Mode: Preview diffs before committing.
  6. Git Push (--push "msg"): Optionally commit & push to all 3 repositories.

Usage:
  python scripts/sync_v3_to_all.py                  # Syncs all completed chunks (default: gradual)
  python scripts/sync_v3_to_all.py --juz 1          # Syncs all verses of Juz 1
  python scripts/sync_v3_to_all.py --dry-run        # Preview diffs without writing
  python scripts/sync_v3_to_all.py --all            # Sync all 6,236 verses
  python scripts/sync_v3_to_all.py --push "Audit: Sync Juz 1 to production"
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = REPO_ROOT.parent

WEB_ROOT = PARENT_ROOT / "thai-quran-web"
APP_ROOT = PARENT_ROOT / "thai-quran-app"

MASTER_V3_JSON = REPO_ROOT / "data" / "01_v3_base_master.json"
TRACKER_TSV = REPO_ROOT / "v3_audit_tracker.tsv"

WEB_TRANSLATION_JSON = WEB_ROOT / "src" / "data" / "thai_v3.json"
WEB_FOOTNOTES_JSON = WEB_ROOT / "src" / "data" / "thai_footnotes.json"

APP_TRANSLATION_JSON = APP_ROOT / "assets" / "thai_v3.json"
APP_OFFLINE_DB = APP_ROOT / "assets" / "quran_offline.db"
APP_FOOTNOTES_JSON = APP_ROOT / "assets" / "footnotes" / "thai_footnotes.json"

FN_BRACKET_RE = re.compile(r"\[FN:(\d+)\]")

JUZ_BOUNDARIES = {
    1: ("1:1", "2:141"),
    2: ("2:142", "2:252"),
    3: ("2:253", "3:92"),
    4: ("3:93", "4:23"),
    5: ("4:24", "4:147"),
    6: ("4:148", "5:81"),
    7: ("5:82", "6:110"),
    8: ("6:111", "7:87"),
    9: ("7:88", "8:40"),
    10: ("8:41", "9:92"),
    11: ("9:93", "11:5"),
    12: ("11:6", "12:52"),
    13: ("12:53", "14:52"),
    14: ("15:1", "16:128"),
    15: ("17:1", "18:74"),
    16: ("18:75", "20:135"),
    17: ("21:1", "22:78"),
    18: ("23:1", "25:20"),
    19: ("25:21", "27:55"),
    20: ("27:56", "29:45"),
    21: ("29:46", "33:30"),
    22: ("33:31", "36:27"),
    23: ("36:28", "39:31"),
    24: ("39:32", "41:46"),
    25: ("41:47", "45:37"),
    26: ("46:1", "51:30"),
    27: ("51:31", "57:29"),
    28: ("58:1", "66:12"),
    29: ("67:1", "77:50"),
    30: ("78:1", "114:6"),
}


def parse_key(k: str) -> tuple[int, int]:
    s, a = k.split(":")
    return int(s), int(a)


def is_in_range(k: str, start: str, end: str) -> bool:
    kp = parse_key(k)
    return parse_key(start) <= kp <= parse_key(end)


def load_completed_ranges() -> list[tuple[str, str]]:
    """Loads ranges of all subchunks marked DONE from v3_audit_tracker.tsv"""
    if not TRACKER_TSV.exists():
        return []
    completed = []
    with open(TRACKER_TSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("status") == "DONE":
                rng = row.get("range", "")
                if "-" in rng:
                    st, en = rng.split("-", 1)
                    completed.append((st.strip(), en.strip()))
    return completed


def select_verses(master_records: list[dict], args: argparse.Namespace) -> list[dict]:
    if args.all:
        print("[SCOPE] Syncing ALL 6,236 verses across entire Quran.")
        return master_records

    if args.juz is not None:
        j = args.juz
        st, en = JUZ_BOUNDARIES.get(j, ("1:1", "1:1"))
        print(f"[SCOPE] Syncing Juz {j} ({st} to {en}).")
        return [r for r in master_records if is_in_range(r["ayah_key"], st, en)]

    # Default: sync completed ranges from tracker
    completed_ranges = load_completed_ranges()
    if not completed_ranges:
        print("[SCOPE] No subchunks marked DONE in tracker. (Use --all or --juz N to override).")
        return []

    print(f"[SCOPE] Syncing {len(completed_ranges)} completed subchunks marked DONE in tracker:")
    for st, en in completed_ranges:
        print(f"  - Range {st} to {en}")

    selected = []
    for r in master_records:
        ak = r["ayah_key"]
        if any(is_in_range(ak, st, en) for st, en in completed_ranges):
            selected.append(r)
    return selected


def sync_to_web(records: list[dict], dry_run: bool = False):
    print("\n--- [1/3] Syncing into thai-quran-web ---")
    if not WEB_TRANSLATION_JSON.exists() or not WEB_FOOTNOTES_JSON.exists():
        print(f"[ERROR] Web data files not found in {WEB_ROOT}")
        return

    with open(WEB_TRANSLATION_JSON, "r", encoding="utf-8") as f:
        web_trans = json.load(f)
    with open(WEB_FOOTNOTES_JSON, "r", encoding="utf-8") as f:
        web_fns = json.load(f)

    verse_updates = 0
    fn_updates = 0

    for r in records:
        s = str(r["surah"])
        a = str(r["ayah"])
        ak = r["ayah_key"]
        t_v3 = r["translation_v3"]
        annotated_raw = r.get("translation_annotated", t_v3)
        # Convert [FN:N] to [N] for web frontend
        annotated_web = FN_BRACKET_RE.sub(r"[\1]", annotated_raw)
        fns_list = r.get("footnotes", [])

        # Update translation plain text
        s_obj = web_trans.setdefault(s, {"verses": {}})
        s_verses = s_obj.setdefault("verses", {})
        curr_t = s_verses.get(a, "")
        if curr_t != t_v3:
            verse_updates += 1
            if verse_updates <= 3:
                print(f"  [WEB VERSE {ak}] Diff: '{curr_t[:50]}...' -> '{t_v3[:50]}...'")
            if not dry_run:
                s_verses[a] = t_v3

        # Update footnotes entry
        curr_fn_entry = web_fns.get(ak)
        new_fn_entry = {
            "annotated": annotated_web,
            "footnotes": fns_list
        }
        if curr_fn_entry != new_fn_entry:
            fn_updates += 1
            if not dry_run:
                if fns_list:
                    web_fns[ak] = new_fn_entry
                else:
                    web_fns.pop(ak, None)

    print(f"  thai_v3.json updates: {verse_updates}")
    print(f"  thai_footnotes.json updates: {fn_updates}")

    if not dry_run:
        with open(WEB_TRANSLATION_JSON, "w", encoding="utf-8") as f:
            json.dump(web_trans, f, ensure_ascii=False, indent=2)
        with open(WEB_FOOTNOTES_JSON, "w", encoding="utf-8") as f:
            json.dump(web_fns, f, ensure_ascii=False, indent=2)
        print("  [OK] Saved thai-quran-web translation and footnotes.")


def sync_to_app(records: list[dict], dry_run: bool = False):
    print("\n--- [2/3] Syncing into thai-quran-app ---")
    if not APP_ROOT.exists():
        print(f"[WARN] thai-quran-app directory not found at {APP_ROOT}")
        return

    # 1. Update assets/thai_v3.json
    if APP_TRANSLATION_JSON.exists():
        with open(APP_TRANSLATION_JSON, "r", encoding="utf-8") as f:
            app_trans = json.load(f)
        app_verse_updates = 0
        for r in records:
            s = str(r["surah"])
            a = str(r["ayah"])
            t_v3 = r["translation_v3"]
            s_obj = app_trans.setdefault(s, {"verses": {}})
            s_verses = s_obj.setdefault("verses", {})
            if s_verses.get(a) != t_v3:
                app_verse_updates += 1
                if not dry_run:
                    s_verses[a] = t_v3
        print(f"  assets/thai_v3.json updates: {app_verse_updates}")
        if not dry_run:
            with open(APP_TRANSLATION_JSON, "w", encoding="utf-8") as f:
                json.dump(app_trans, f, ensure_ascii=False, indent=2)

    # 2. Update assets/footnotes/thai_footnotes.json
    if APP_FOOTNOTES_JSON.exists() and WEB_FOOTNOTES_JSON.exists():
        with open(WEB_FOOTNOTES_JSON, "r", encoding="utf-8") as f:
            web_fn_raw = f.read()
        with open(APP_FOOTNOTES_JSON, "r", encoding="utf-8") as f:
            app_fn_raw = f.read()
        if web_fn_raw.strip() != app_fn_raw.strip():
            print("  assets/footnotes/thai_footnotes.json requires sync with web footnotes.")
            if not dry_run:
                with open(APP_FOOTNOTES_JSON, "w", encoding="utf-8") as f:
                    f.write(web_fn_raw)
                print(f"  [OK] Synced {APP_FOOTNOTES_JSON}")
        else:
            print("  assets/footnotes/thai_footnotes.json is already up to date.")

    # 3. Update SQLite DB: assets/quran_offline.db
    if APP_OFFLINE_DB.exists():
        conn = sqlite3.connect(APP_OFFLINE_DB)
        c = conn.cursor()
        c.execute("SELECT verse_key, translation_th FROM verses;")
        db_rows = dict(c.fetchall())

        db_updates = 0
        update_params = []
        for r in records:
            ak = r["ayah_key"]
            t_v3 = r["translation_v3"]
            if db_rows.get(ak) != t_v3:
                db_updates += 1
                update_params.append((t_v3, ak))

        print(f"  assets/quran_offline.db updates: {db_updates}")
        if not dry_run and update_params:
            c.executemany("UPDATE verses SET translation_th = ? WHERE verse_key = ?;", update_params)
            conn.commit()
            print(f"  [OK] Updated {len(update_params)} rows in {APP_OFFLINE_DB}")
        conn.close()


def git_commit_and_push(commit_msg: str):
    print("\n--- [3/3] Git Commit & Push Across Repositories ---")
    repos = [
        (REPO_ROOT, "thai_quran_translation_v4", "v3_synthesis_audit"),
        (WEB_ROOT, "thai-quran-web", "feat/thai-v4-translation"),
        (APP_ROOT, "thai-quran-app", "main"),
    ]

    for repo_path, repo_name, branch in repos:
        if not repo_path.exists():
            continue
        print(f"\nChecking git status in {repo_name} ({repo_path})...")
        st = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, encoding="utf-8")
        if not st.stdout.strip():
            print(f"  [CLEAN] No uncommitted changes in {repo_name}.")
            continue

        print(f"  [DIRTY] Staging and committing changes in {repo_name}...")
        subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)
        cm = subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_path, capture_output=True, text=True, encoding="utf-8")
        print(f"  Commit result: {cm.stdout.strip().splitlines()[-1] if cm.stdout else 'done'}")

        print(f"  Pushing to origin {branch}...")
        push_res = subprocess.run(["git", "push", "origin", branch], cwd=repo_path, capture_output=True, text=True, encoding="utf-8")
        if push_res.returncode == 0:
            print(f"  [OK] Pushed {repo_name} -> origin/{branch}")
        else:
            print(f"  [WARN] Push failed for {repo_name}:\n{push_res.stderr or push_res.stdout}")


def main():
    parser = argparse.ArgumentParser(description="Sync Master V3 dataset into Web and App ecosystems.")
    parser.add_argument("--all", action="store_true", help="Sync all 6,236 verses across entire Quran")
    parser.add_argument("--juz", type=int, help="Sync all verses in specified Juz (1-30)")
    parser.add_argument("--dry-run", action="store_true", help="Preview sync diffs without modifying files")
    parser.add_argument("--push", type=str, metavar="MESSAGE", help="Git commit and push all repositories with MESSAGE")
    args = parser.parse_args()

    if not MASTER_V3_JSON.exists():
        print(f"[FATAL] Master V3 dataset not found: {MASTER_V3_JSON}")
        sys.exit(1)

    with open(MASTER_V3_JSON, "r", encoding="utf-8") as f:
        master_records = json.load(f)

    selected = select_verses(master_records, args)
    if not selected:
        print("[INFO] No verses selected for sync. Exiting.")
        return

    print(f"\nProcessing {len(selected)} selected verses...")
    sync_to_web(selected, dry_run=args.dry_run)
    sync_to_app(selected, dry_run=args.dry_run)

    if args.dry_run:
        print("\n[DRY-RUN COMPLETE] No files were modified.")
        return

    print("\n[SYNC COMPLETE] Successfully synced Master V3 to production ecosystems!")

    if args.push:
        git_commit_and_push(args.push)


if __name__ == "__main__":
    main()
