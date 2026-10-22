#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/apply_v4_fixes.py
Reads proposed fixes directly from Clipboard (or file), validates with strict safety
guardrails (exact match, footnote parity, balanced brackets), applies fixes into
the pipeline, updates master deliverables, and re-exports the affected Juz chunk.

Usage:
  python scripts/apply_v4_fixes.py
  python scripts/apply_v4_fixes.py --file fixes.json
  python scripts/apply_v4_fixes.py --clipboard
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(r"H:\gits\thai_quran_translation_v4")
V4_DATA_PATH = REPO_ROOT / "data" / "06_tq_spacing_and_scholar_fixed.json"
MANUAL_FIXES_JSON = REPO_ROOT / "data" / "v4_manual_audit_fixes.json"

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
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        txt = root.clipboard_get()
        root.destroy()
        return txt
    except Exception:
        pass

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


def set_clipboard_text(text: str):
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
                input=text,
                text=True,
                encoding="utf-8"
            )
        except Exception:
            pass


def extract_fixes_from_text(raw_text: str) -> list[dict]:
    raw = raw_text.strip()

    # 1. Try finding JSON Array
    m = re.search(r"```(?:json)?\s*(\[\s*\{.*?\}\s*\])\s*```", raw, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, list):
                return data
        except Exception:
            pass

    m2 = re.search(r"(\[\s*\{.*\}\s*\])", raw, re.DOTALL)
    if m2:
        try:
            data = json.loads(m2.group(1))
            if isinstance(data, list):
                return data
        except Exception:
            pass

    # 2. Try line format: [FIX] S:A [TYPE]: 'target' -> 'replacement' (reason)
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
        return line_fixes

    return []


def normalize_fn_tokens(s: str) -> str:
    # Convert [FN:123] to native ⟦FN:123⟧
    return FN_BRACKET_RE.sub(r"⟦FN:\1⟧", s)


def main():
    parser = argparse.ArgumentParser(description="Safely apply validated Gemini audit fixes to ThaiQuran v4")
    parser.add_argument("--file", "-f", type=str, help="Path to JSON file containing proposed fixes")
    parser.add_argument("--clipboard", "-c", action="store_true", help="Read fixes from system clipboard (default)")
    parser.add_argument("--dry-run", action="store_true", help="Validate fixes without modifying files")
    args = parser.parse_args()

    raw_input = ""
    if args.file:
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
        if not raw_input.strip():
            print("Clipboard is empty. Copy the JSON fixes block from Gemini Chat and run this script again.")
            print("Or use: python scripts/apply_v4_fixes.py --file <path_to_json>")
            sys.exit(1)
        print(f"Loaded {len(raw_input)} characters from clipboard.")

    proposed_fixes = extract_fixes_from_text(raw_input)
    if not proposed_fixes:
        print("Failed to find valid fixes (JSON array or [FIX] lines) in the provided input.")
        print("Expected format: [{\"ayah\": \"S:A\", \"type\": \"SPACING\", \"target\": \"...\", \"replacement\": \"...\", \"reason\": \"...\"}]")
        sys.exit(1)

    print(f"Parsed {len(proposed_fixes)} proposed fixes. Validating safety guardrails...\n")

    # Load current v4 dataset
    with open(V4_DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    v4_map = {r["ayah_key"]: r for r in records}

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

        if ak not in v4_map:
            errors.append(f"Fix #{idx}: Ayah '{ak}' not found in Quran database")
            continue

        # Normalize [FN:123] to native ⟦FN:123⟧
        target_norm = normalize_fn_tokens(target)
        replacement_norm = normalize_fn_tokens(replacement)

        rec = v4_map[ak]
        t_tok = rec["translation_tokenized"]

        # Check exact target match & Uniqueness
        target_occurrences = t_tok.count(target_norm)
        if target_occurrences == 0:
            errors.append(f"Fix #{idx} ({ak}): Target substring '{target_norm}' not found in current verse text:\n    Actual: '{t_tok}'")
            continue
        elif target_occurrences > 1:
            errors.append(
                f"Fix #{idx} ({ak}): Target substring '{target_norm}' is AMBIGUOUS (appears {target_occurrences} times in this verse)!\n"
                f"    Please include 1-2 adjacent context words in 'target' and 'replacement' to anchor it uniquely."
            )
            continue

        # Check simulated text
        simulated = t_tok.replace(target_norm, replacement_norm, 1)

        # Footnote Parity Check
        orig_fns = FN_TOKEN_RE.findall(t_tok)
        new_fns = FN_TOKEN_RE.findall(simulated)
        if orig_fns != new_fns:
            errors.append(f"Fix #{idx} ({ak}): Footnote mismatch! Original {orig_fns} vs Modified {new_fns}")
            continue

        # Balanced Parentheses Check
        if simulated.count("(") != simulated.count(")"):
            errors.append(f"Fix #{idx} ({ak}): Unbalanced parentheses in modified verse: '('={simulated.count('(')} ')'={simulated.count(')')}")
            continue

        # Passed all gates
        validated_fixes.append({
            "ayah": ak,
            "type": fix_type,
            "target": target_norm,
            "replacement": replacement_norm,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        affected_juzs.add(find_juz(ak))

    if errors:
        print("=== VALIDATION FAILURES ENCOUNTERED ===")
        for err in errors:
            print(f"  [ERROR] {err}")
        print(f"\n{len(errors)} errors found. Aborting without applying changes.")
        sys.exit(1)

    print(f"All {len(validated_fixes)} fixes passed 100% of safety guardrails!")

    if args.dry_run:
        print("[DRY-RUN] No files modified.")
        for idx, vf in enumerate(validated_fixes, 1):
            print(f"  [{idx}] {vf['ayah']} [{vf['type']}]: '{vf['target']}' -> '{vf['replacement']}' ({vf['reason']})")
        return

    # Load existing manual fixes list
    manual_fixes = []
    if MANUAL_FIXES_JSON.exists():
        with open(MANUAL_FIXES_JSON, "r", encoding="utf-8") as f:
            try:
                manual_fixes = json.load(f)
            except Exception:
                manual_fixes = []

    # Append new unique fixes
    added_count = 0
    fix_log_lines = []
    for vf in validated_fixes:
        # Avoid exact duplicate in history
        exists = any(
            x.get("ayah") == vf["ayah"] and x.get("target") == vf["target"] and x.get("replacement") == vf["replacement"]
            for x in manual_fixes
        )
        if not exists:
            manual_fixes.append(vf)
            added_count += 1
        log_line = f"[FIX] {vf['ayah']} [{vf['type']}]: '{vf['target']}' -> '{vf['replacement']}' ({vf['reason']})"
        print(log_line)
        fix_log_lines.append(log_line)

    with open(MANUAL_FIXES_JSON, "w", encoding="utf-8") as f:
        json.dump(manual_fixes, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {added_count} new fixes to {MANUAL_FIXES_JSON} (Total recorded: {len(manual_fixes)})")

    # Update TSV audit tracker
    try:
        from v4_tracker import record_applied_fixes
        record_applied_fixes(validated_fixes)
    except Exception as e:
        print(f"[WARN] Failed to update TSV tracker: {e}")

    # Re-run pipeline phases to package deliverables
    print("\n--- Re-running Pipeline Phases 6, 5 & 7 ---")
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "06_apply_v3_spacing_and_scholar_sync.py")], check=True)
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "05_catalog_upgrades_and_diff.py")], check=True)
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "07_validate_and_package.py")], check=True)

    # Re-export affected Juz chunks
    print("\n--- Re-exporting Affected Juz Chunks ---")
    for j in sorted(affected_juzs):
        subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "export_v4_audit_chunk.py"), "--juz", str(j), "--subchunks"], check=True)

    # Copy log to clipboard
    summary_text = "\n".join(fix_log_lines)
    set_clipboard_text(summary_text)

    print(f"\n=======================================================")
    print(f"[SUCCESS] Applied {len(validated_fixes)} fixes across Juz {sorted(affected_juzs)}.")
    print("Fixes log copied to clipboard!")
    print("=======================================================")


if __name__ == "__main__":
    main()
