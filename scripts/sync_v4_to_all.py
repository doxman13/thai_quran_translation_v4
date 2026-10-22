#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/sync_v4_to_all.py
End-of-Session Synchronizer for ThaiQuran v4 Ecosystem:
1. Rebuilds master deliverables (Phase 6 -> Phase 5 -> Phase 7).
2. Syncs verified v4 master translations and footnotes directly into thai-quran-web.
3. Optionally commits and pushes both repositories (--push "commit message").

Usage:
  python scripts/sync_v4_to_all.py                 # Sync deliverables and web data
  python scripts/sync_v4_to_all.py --dry-run       # Preview sync diffs without writing
  python scripts/sync_v4_to_all.py --push "Message" # Sync + Git Commit & Push both repos
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(r"H:\gits\thai_quran_translation_v4")
WEB_ROOT = Path(r"H:\gits\thai-quran-web")

V4_MASTER_JSON = REPO_ROOT / "deliverables" / "01_thai_quran_translation_v4_master.json"
WEB_TRANSLATION_JSON = WEB_ROOT / "src" / "data" / "thai_v3.json"
WEB_FOOTNOTES_JSON = WEB_ROOT / "src" / "data" / "thai_footnotes.json"


def rebuild_pipeline():
    print("\n--- [1/4] Rebuilding Master Deliverables (Phases 6, 5 & 7) ---")
    scripts = [
        REPO_ROOT / "scripts" / "06_apply_v3_spacing_and_scholar_sync.py",
        REPO_ROOT / "scripts" / "05_catalog_upgrades_and_diff.py",
        REPO_ROOT / "scripts" / "07_validate_and_package.py",
    ]
    for s in scripts:
        print(f"Running {s.name}...")
        res = subprocess.run([sys.executable, str(s)], capture_output=True, text=True, encoding="utf-8")
        if res.returncode != 0:
            print(f"[FAIL] Pipeline script {s.name} failed:\n{res.stderr or res.stdout}")
            sys.exit(1)
    print("[OK] Master deliverables packaged successfully.")


def sync_to_web(dry_run: bool = False):
    print("\n--- [2/4] Syncing v4 Master Deliverables into thai-quran-web ---")
    if not V4_MASTER_JSON.exists():
        print(f"[ERROR] Deliverable not found: {V4_MASTER_JSON}")
        sys.exit(1)

    with open(V4_MASTER_JSON, "r", encoding="utf-8") as f:
        v4_records = json.load(f)

    if not WEB_TRANSLATION_JSON.exists():
        print(f"[ERROR] Web translation file not found: {WEB_TRANSLATION_JSON}")
        sys.exit(1)

    with open(WEB_TRANSLATION_JSON, "r", encoding="utf-8") as f:
        web_trans = json.load(f)

    with open(WEB_FOOTNOTES_JSON, "r", encoding="utf-8") as f:
        web_fns = json.load(f)

    verse_updates = 0
    fn_updates = 0

    for r in v4_records:
        s = str(r["surah"])
        a = str(r["ayah"])
        t_v4 = r["translation"]
        fns_v4 = {str(fn["id"]): fn["text"] for fn in r.get("footnotes", [])}

        # Check translation diff
        s_obj = web_trans.setdefault(s, {"name": "", "verses": {}})
        s_verses = s_obj.setdefault("verses", {})
        curr_t = s_verses.get(a, "")
        if curr_t != t_v4:
            verse_updates += 1
            if verse_updates <= 5:
                print(f"  [VERSE DIFF {s}:{a}]")
                print(f"    Web: '{curr_t}'")
                print(f"    V4:  '{t_v4}'")
            if not dry_run:
                s_verses[a] = t_v4

        # Check footnotes diff
        fn_s_obj = web_fns.setdefault(s, {"name": "", "verses": {}})
        fn_s_verses = fn_s_obj.setdefault("verses", {})
        curr_fns = fn_s_verses.get(a, {})
        if curr_fns != fns_v4:
            fn_updates += 1
            if not dry_run:
                fn_s_verses[a] = fns_v4

    print(f"\nSync Assessment:")
    print(f"  Verses to update in thai-quran-web:   {verse_updates}")
    print(f"  Footnotes to update in thai-quran-web: {fn_updates}")

    if not dry_run:
        if verse_updates > 0:
            with open(WEB_TRANSLATION_JSON, "w", encoding="utf-8") as f:
                json.dump(web_trans, f, ensure_ascii=False, indent=2)
            print(f"[OK] Successfully written {verse_updates} updated verses into thai-quran-web.")
        if fn_updates > 0:
            with open(WEB_FOOTNOTES_JSON, "w", encoding="utf-8") as f:
                json.dump(web_fns, f, ensure_ascii=False)
            print(f"[OK] Successfully written {fn_updates} updated footnotes into thai-quran-web.")
    elif dry_run:
        print("[DRY-RUN] No files modified in thai-quran-web.")
    else:
        print("[OK] thai-quran-web is already 100% in sync with v4 master.")


def git_commit_and_push(commit_msg: str):
    print("\n--- [3/4] Git Commit & Push Across Ecosystem Repositories ---")
    repos = [
        (REPO_ROOT, "thai_quran_translation_v4", "master"),
        (WEB_ROOT, "thai-quran-web", "feat/thai-v4-translation"),
    ]

    for repo_path, repo_name, branch in repos:
        print(f"\nChecking {repo_name} ({branch})...")
        # Pull latest first
        subprocess.run(["git", "-C", str(repo_path), "pull"], check=False)

        # Status check
        res = subprocess.run(["git", "-C", str(repo_path), "status", "--porcelain"], capture_output=True, text=True, encoding="utf-8")
        if not res.stdout.strip():
            print(f"  [{repo_name}] Clean. Nothing to commit.")
            continue

        print(f"  [{repo_name}] Uncommitted changes detected. Staging, committing & pushing...")
        subprocess.run(["git", "-C", str(repo_path), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(repo_path), "commit", "-m", commit_msg], check=True)
        push_res = subprocess.run(["git", "-C", str(repo_path), "push", "origin", branch], capture_output=True, text=True, encoding="utf-8")
        if push_res.returncode == 0:
            print(f"  [{repo_name}] [SUCCESS] Pushed to origin/{branch}.")
        else:
            print(f"  [{repo_name}] [PUSH WARN]: {push_res.stderr or push_res.stdout}")


def main():
    parser = argparse.ArgumentParser(description="End-of-Session Synchronizer for ThaiQuran v4 Ecosystem")
    parser.add_argument("--dry-run", action="store_true", help="Preview sync diffs without modifying files")
    parser.add_argument("--push", type=str, metavar="MSG", help="Commit and push changes across repositories with MSG")
    args = parser.parse_args()

    print("=" * 75)
    print(f"   THAIQURAN V4 ECOSYSTEM SESSION SYNCHRONIZER - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 75)

    if not args.dry_run:
        rebuild_pipeline()

    sync_to_web(dry_run=args.dry_run)

    if args.push and not args.dry_run:
        git_commit_and_push(args.push)

    print("\n" + "=" * 75)
    print("   [DONE] Session synchronization completed!")
    print("=" * 75)


if __name__ == "__main__":
    main()
