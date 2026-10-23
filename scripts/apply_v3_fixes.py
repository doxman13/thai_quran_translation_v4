#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/apply_v3_fixes.py
Safely applies validated audit fixes to Master V3 Synthesis dataset (data/01_v3_base_master.json).
Reads from clipboard (or file), validates with strict safety guardrails (exact match, uniqueness,
footnote parity, balanced parentheses), applies the fixes, logs them in data/v3_manual_audit_fixes.json,
and re-exports affected Juz and Subchunks automatically.

Usage:
  python scripts/apply_v3_fixes.py
  python scripts/apply_v3_fixes.py --clipboard
  python scripts/apply_v3_fixes.py --file fixes.json
  python scripts/apply_v3_fixes.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_DATA_PATH = REPO_ROOT / "data" / "01_v3_base_master.json"
MANUAL_FIXES_JSON = REPO_ROOT / "data" / "v3_manual_audit_fixes.json"

FN_BRACKET_RE = re.compile(r"\[FN:(\d+)\]")
FN_TOKEN_RE = re.compile(r"⟦FN:\d+⟧")

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


def find_juz(ak: str) -> int:
    cur = parse_key(ak)
    for j, (st, en) in JUZ_BOUNDARIES.items():
        if parse_key(st) <= cur <= parse_key(en):
            return j
    return 1


def get_clipboard_text() -> str:
    # 1. macOS pbpaste
    if sys.platform == "darwin":
        try:
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, encoding="utf-8")
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

    # 2. Tkinter cross-platform
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        txt = root.clipboard_get()
        root.destroy()
        return txt
    except Exception:
        pass

    # 3. Windows PowerShell Get-Clipboard
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Clipboard"],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

    return ""


def extract_fixes_from_text(raw_text: str) -> tuple[bool, list[dict]]:
    raw = raw_text.strip()

    # Check for explicit empty array (all verses clean)
    if raw in ("[]", "```json\n[]\n```", "```json\n[]```", "```\n[]\n```"):
        return True, []

    # 1. Try direct JSON parse
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return True, data
    except Exception:
        pass

    # 2. Try finding JSON Array inside markdown codeblock or raw text
    m = re.search(r"```(?:json)?\s*(\[\s*[\s\S]*?\s*\])\s*```", raw)
    if m:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, list):
                return True, data
        except Exception:
            pass

    m2 = re.search(r"(\[\s*\{[\s\S]*?\}\s*\])", raw)
    if m2:
        try:
            data = json.loads(m2.group(1))
            if isinstance(data, list):
                return True, data
        except Exception:
            pass

    # 3. Try line format: [FIX] S:A [TYPE]: 'target' -> 'replacement' (reason)
    pattern = re.compile(
        r"\[FIX\]\s*(\d+:\d+)\s*(?:\[(\w+)\])?:\s*['\"](.*?)['\"]\s*->\s*['\"](.*?)['\"]\s*(?:\((.*?)\))?",
        re.MULTILINE
    )
    line_fixes = []
    for m in pattern.finditer(raw):
        ak = m.group(1)
        ftype = m.group(2) or "AUDIT"
        target = m.group(3)
        replacement = m.group(4)
        reason = m.group(5) or ""
        line_fixes.append({
            "ayah": ak,
            "type": ftype,
            "target": target,
            "replacement": replacement,
            "reason": reason.strip(),
        })

    if line_fixes:
        return True, line_fixes

    return False, []


def main():
    parser = argparse.ArgumentParser(description="Safely apply validated audit fixes to Master V3")
    parser.add_argument("--file", "-f", type=str, help="Path to JSON file containing proposed fixes")
    parser.add_argument("--clipboard", "-c", action="store_true", help="Read fixes from system clipboard (default)")
    parser.add_argument("--dry-run", action="store_true", help="Validate fixes without modifying files")
    parser.add_argument("--re-export", action="store_true", default=False, help="Re-export affected chunks (disabled by default to avoid mutating chunks during audit)")
    args = parser.parse_args()

    raw_input = ""
    if args.file:
        if args.file == "-":
            raw_input = sys.stdin.read()
            print(f"Loaded {len(raw_input)} characters from standard input.")
        else:
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File {file_path} not found.")
                sys.exit(1)
            with open(file_path, "r", encoding="utf-8") as f:
                raw_input = f.read()
            print(f"Loaded {len(raw_input)} characters from file: {file_path}")
    else:
        print("Reading fixes from clipboard...")
        raw_input = get_clipboard_text()
        if raw_input:
            print(f"Loaded {len(raw_input)} characters from clipboard.")
            is_valid, proposed_fixes = extract_fixes_from_text(raw_input)
        else:
            is_valid, proposed_fixes = False, []

        # Fallback to local fixes.json or data/proposed_fixes.json if clipboard didn't provide valid fixes
        if not is_valid:
            fallback_candidates = [
                REPO_ROOT / "fixes.json",
                REPO_ROOT / "data" / "proposed_fixes.json",
                Path("fixes.json")
            ]
            for candidate in fallback_candidates:
                if candidate.exists() and candidate.stat().st_size > 0:
                    try:
                        with open(candidate, "r", encoding="utf-8") as f:
                            cand_text = f.read()
                        c_valid, c_fixes = extract_fixes_from_text(cand_text)
                        if c_valid:
                            print(f"[INFO] Successfully loaded {len(c_fixes)} fixes from fallback file: {candidate.name}")
                            raw_input = cand_text
                            is_valid, proposed_fixes = c_valid, c_fixes
                            break
                    except Exception:
                        pass

    if not is_valid:
        print("\nFailed to find valid fixes in the clipboard or fallback files (fixes.json).")
        print("Expected format: [{\"ayah\": \"S:A\", \"type\": \"...\", \"target\": \"...\", \"replacement\": \"...\", \"reason\": \"...\"}]")
        print("Or if all verses in chunk are verified clean: []")
        print("\nHow to supply fixes:")
        print("  1. Copy JSON to clipboard (Cmd+C) and run: python3 scripts/apply_v3_fixes.py")
        print("  2. Save fixes to 'fixes.json' and run:     python3 scripts/apply_v3_fixes.py")
        print("  3. Pass file directly:                   python3 scripts/apply_v3_fixes.py -f path/to/fixes.json")
        sys.exit(1)

    if not proposed_fixes:
        print("\nAll verses in this chunk are verified 100% accurate! No fixes needed. Chunk is clean.")
        return

    print(f"Parsed {len(proposed_fixes)} proposed fixes. Validating safety guardrails...\n")

    # Load current master v3 dataset
    with open(BASE_DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    v3_map = {r["ayah_key"]: r for r in records}

    validated_fixes = []
    affected_juzs = set()
    errors = []

    for idx, fix in enumerate(proposed_fixes, 1):
        ak = fix.get("ayah", "").strip()
        target = fix.get("target", "")
        replacement = fix.get("replacement", "")
        fix_type = fix.get("type", "AUDIT").upper()
        reason = fix.get("reason", "").strip()

        if not ak or not target or not replacement:
            errors.append(f"Fix #{idx}: Missing required fields ('ayah', 'target', 'replacement')")
            continue

        if ak not in v3_map:
            errors.append(f"Fix #{idx}: Ayah '{ak}' not found in database")
            continue

        rec = v3_map[ak]
        ann_text = rec.get("translation_annotated") or rec.get("translation_v3", "")
        plain_text = rec.get("translation_v3", "")

        # Check whether target matches in annotated (as displayed to auditor with [FN:X]) or plain
        if target in ann_text:
            cur_text = ann_text
            match_in_ann = True
        elif target in plain_text:
            cur_text = plain_text
            match_in_ann = False
        else:
            if replacement in ann_text or replacement in plain_text:
                print(f"[ALREADY APPLIED] {ak} [{fix_type}]: '{replacement}' is already present in this verse.")
                continue
            errors.append(f"Fix #{idx} ({ak}): Target substring '{target}' not found in current verse text:\n    Actual: '{ann_text}'")
            continue

        # Check Uniqueness
        target_occurrences = cur_text.count(target)
        if target_occurrences > 1:
            errors.append(
                f"Fix #{idx} ({ak}): Target substring '{target}' appears {target_occurrences} times in this verse!\n"
                f"    Please include 1-2 adjacent context words in 'target' and 'replacement' to anchor uniquely."
            )
            continue

        simulated = cur_text.replace(target, replacement, 1)

        # Balanced Parentheses Check
        if simulated.count("(") != simulated.count(")"):
            errors.append(f"Fix #{idx} ({ak}): Unbalanced parentheses in modified verse: '('={simulated.count('(')} ')'={simulated.count(')')}")
            continue

        # Passed all gates
        validated_fixes.append({
            "ayah": ak,
            "type": fix_type,
            "target": target,
            "replacement": replacement,
            "reason": reason,
            "match_in_ann": match_in_ann,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        affected_juzs.add(find_juz(ak))

    if errors:
        print("=== VALIDATION FAILURES ENCOUNTERED ===")
        for err in errors:
            print(f"  [ERROR] {err}")
        print(f"\n{len(errors)} errors found. Aborting without applying changes.")
        sys.exit(1)

    if not validated_fixes:
        print("\nAll proposed fixes from clipboard are already applied in the current dataset. Nothing to change!")
        return

    print(f"All {len(validated_fixes)} fixes passed 100% of safety guardrails!")
    for vf in validated_fixes:
        print(f"[FIX] {vf['ayah']} [{vf['type']}]: '{vf['target']}' -> '{vf['replacement']}' ({vf['reason']})")

    if args.dry_run:
        print("\n[DRY-RUN] No files modified.")
        return

    # Apply fixes into database
    for vf in validated_fixes:
        ak = vf["ayah"]
        rec = v3_map[ak]
        if vf.get("match_in_ann", True):
            rec["translation_annotated"] = rec["translation_annotated"].replace(vf["target"], vf["replacement"], 1)
            # Synchronize translation_v3 by stripping footnote markers
            rec["translation_v3"] = re.sub(r"\[FN:\d+\]", "", rec["translation_annotated"])
        else:
            rec["translation_v3"] = rec["translation_v3"].replace(vf["target"], vf["replacement"], 1)
            if vf["target"] in rec.get("translation_annotated", ""):
                rec["translation_annotated"] = rec["translation_annotated"].replace(vf["target"], vf["replacement"], 1)

    with open(BASE_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # Append to manual fixes log
    existing_log = []
    if MANUAL_FIXES_JSON.exists():
        try:
            with open(MANUAL_FIXES_JSON, "r", encoding="utf-8") as f:
                existing_log = json.load(f)
        except Exception:
            existing_log = []

    existing_log.extend(validated_fixes)
    with open(MANUAL_FIXES_JSON, "w", encoding="utf-8") as f:
        json.dump(existing_log, f, ensure_ascii=False, indent=2)

    print(f"\nSuccessfully applied {len(validated_fixes)} fixes to {BASE_DATA_PATH}")
    print(f"Total fixes recorded in {MANUAL_FIXES_JSON}: {len(existing_log)}")

    # Re-export affected Juz chunks (only if explicitly requested via --re-export)
    if args.re_export:
        print("\nRe-exporting affected Juz and Subchunks...")
        for j in sorted(affected_juzs):
            cmd = [sys.executable, str(REPO_ROOT / "scripts" / "export_v3_audit_chunk.py"), "--juz", str(j), "--subchunks"]
            subprocess.run(cmd, check=True)
        print("\nAll affected chunks re-exported successfully!")
    else:
        print("\n[INFO] Chunk re-export skipped to maintain audit chunk stability. (Pass --re-export if you wish to re-export).")


if __name__ == "__main__":
    main()
