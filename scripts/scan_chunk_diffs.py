#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/scan_chunk_diffs.py
Deterministic Pre-Audit Scanner for Thai Quran Synthesis.

Scans a chunk of verses prior to human/LLM audit to detect:
  1. Potential OCR Word Truncations (e.g. 'คด' vs 'คดเคี้ยว', single-syllable drops).
  2. Potential Missing Words / Omissions (phrases present in TQ/V4 but absent in V3).
  3. Footnote Anchor Syntax Anomalies (tags inside duplicated words, broken brackets).
  4. V4 Scholar High-Priority Category Alerts ([CLAUSE_OMISSION_RESTORED], [REVERSE_REPAIR_OVER_V3]).

Outputs a formatted "Pre-Audit Watch List" to be included in the audit prompt,
ensuring that neither Gemini nor the auditor relies on pure luck to catch dropped words.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
V3_BASE_PATH = REPO_ROOT / "data" / "01_v3_base_master.json"
TQ_INGESTED_PATH = REPO_ROOT / "data" / "01_tq_ingested_tokenized.json"
V4_ANNOTATED_PATH = REPO_ROOT / "deliverables" / "02_thai_quran_translation_v4_annotated.json"


def clean_text(text: str) -> str:
    """Strip footnote markers and normalize spaces."""
    t = re.sub(r"\[FN:\d+\]|\(\d+\)", "", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_translit(text: str) -> str:
    """Normalize acceptable transliteration differences to avoid false positives."""
    t = text.replace("อัลลอฮฺ", "อัลลอฮ").replace("อัลลอฮ์", "อัลลอฮ")
    t = t.replace("มัรฺยัม", "มัรยัม").replace("อัฏฏอฆูต", "อัฎฎอฆูต")
    t = t.replace("รอซูล", "ร่อซูล")
    return t


def scan_verse(v3_row: dict, tq_row: dict, v4_row: dict) -> list[dict]:
    findings = []
    ayah_key = v3_row["ayah_key"]
    
    v3_raw = v3_row["translation_annotated"]
    tq_raw = tq_row.get("translation_raw", "")
    v4_cat = v4_row.get("v4_vs_v3_category", "NONE")

    v3_clean = clean_text(v3_raw)
    tq_clean = clean_text(tq_raw)

    v3_norm = normalize_translit(v3_clean)
    tq_norm = normalize_translit(tq_clean)

    # 1. Check V4 High-Priority Categories
    if v4_cat in ("CLAUSE_OMISSION_RESTORED", "REVERSE_REPAIR_OVER_V3"):
        findings.append({
            "type": "V4_SCHOLAR_CATEGORY_ALERT",
            "ayah": ayah_key,
            "detail": f"V4 categorized as [{v4_cat}]. Potential restored clause or correction over V3."
        })

    # 2. Check Footnote Placement Anomalies in V3
    fn_dups = re.findall(r"(\w+\[FN:\d+\]\s*ๆ|ๆ\[FN:\d+\]\s*\w+)", v3_raw)
    if fn_dups:
        findings.append({
            "type": "FOOTNOTE_SYNTAX_ANOMALY",
            "ayah": ayah_key,
            "detail": f"Footnote tag adjacent to or splitting mai-yamok (ๆ): {fn_dups}"
        })
    fn_splits = re.findall(r"(\w+)\[FN:\d+\](\w+)", v3_raw)
    for w1, w2 in fn_splits:
        # Ignore if w2 is standard Thai particle or word like 'ว่า'
        if len(w1) > 0 and len(w2) > 0:
            findings.append({
                "type": "FOOTNOTE_MID_WORD_SPLIT",
                "ayah": ayah_key,
                "detail": f"Footnote tag appears inside word/compound: '{w1}[FN:...]{w2}'"
            })

    # 3. Lexical Diff: Detect Potential OCR Truncations / Expansions (like 'คด' vs 'คดเคี้ยว')
    matcher = difflib.SequenceMatcher(None, v3_norm, tq_norm)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            s1 = v3_norm[i1:i2].strip()
            s2 = tq_norm[j1:j2].strip()
            s1_clean = re.sub(r"[\s\(\)\.\,\?\!\-\'\"\d]", "", s1)
            s2_clean = re.sub(r"[\s\(\)\.\,\?\!\-\'\"\d]", "", s2)

            if not s1_clean and not s2_clean:
                continue

            # Ignore systematic stylistic revisions:
            # 'พระผู้เป็นเจ้า' -> 'พระผู้อภิบาล', 'คำแนะนำ' -> 'แนวทาง', 'สูเจ้า' -> 'พวกเจ้า'
            if any(ign in s2 for ign in ["อภิบาล", "สูเจ้า", "แนวทาง", "คัมภีร์"]):
                continue

            # Prefix Truncation (V3 has beginning of TQ word)
            if s1_clean and s2_clean.startswith(s1_clean) and len(s2_clean) > len(s1_clean):
                diff = s2_clean[len(s1_clean):]
                # Filter out pure grammatical suffixes like 'ทั้งหลาย'
                if diff not in ("ทั้งหลาย", "เหล่านั้น"):
                    findings.append({
                        "type": "POTENTIAL_WORD_TRUNCATION",
                        "ayah": ayah_key,
                        "v3": s1_clean,
                        "tq": s2_clean,
                        "diff": f"+'{diff}' in TQ",
                        "detail": f"V3 has '{s1_clean}' while TQ/V4 has '{s2_clean}'. Verify if OCR dropped '{diff}'."
                    })

            # Pure Insertion in TQ (Significant length phrase)
            elif len(s1_clean) == 0 and len(s2_clean) >= 6:
                findings.append({
                    "type": "POTENTIAL_OMISSION_ALERT",
                    "ayah": ayah_key,
                    "v3": "(None)",
                    "tq": s2_clean,
                    "diff": f"+'{s2_clean}' in TQ",
                    "detail": f"TQ has extra phrase '{s2_clean}' absent in V3. Verify against Arabic text."
                })

    return findings


def load_datasets():
    with open(V3_BASE_PATH, "r", encoding="utf-8") as f:
        v3_list = json.load(f)
    with open(TQ_INGESTED_PATH, "r", encoding="utf-8") as f:
        tq_list = json.load(f)
    with open(V4_ANNOTATED_PATH, "r", encoding="utf-8") as f:
        v4_list = json.load(f)

    v3_map = {r["ayah_key"]: r for r in v3_list}
    tq_map = {r["ayah_key"]: r for r in tq_list}
    v4_map = {r["ayah_key"]: r for r in v4_list}
    return v3_list, v3_map, tq_map, v4_map


def main():
    parser = argparse.ArgumentParser(description="Scan Quran subchunks for pre-audit watch items.")
    parser.add_argument("--chunk", type=int, help="Subchunk number (1-127)")
    parser.add_argument("--start", type=str, help="Start ayah_key (e.g. 3:149)")
    parser.add_argument("--end", type=str, help="End ayah_key (e.g. 3:200)")
    args = parser.parse_args()

    v3_list, v3_map, tq_map, v4_map = load_datasets()

    target_keys = []
    if args.chunk:
        # Load subchunk definitions from audit_chunks
        tracker_path = REPO_ROOT / "v3_audit_tracker.tsv"
        with open(tracker_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 4 and parts[0].isdigit() and int(parts[0]) == args.chunk:
                    range_str = parts[3]
                    start_str, end_str = range_str.split("-")
                    s_surah, s_ayah = map(int, start_str.split(":"))
                    e_surah, e_ayah = map(int, end_str.split(":"))
                    for r in v3_list:
                        s, a = r["surah"], r["ayah"]
                        if (s > s_surah or (s == s_surah and a >= s_ayah)) and \
                           (s < e_surah or (s == e_surah and a <= e_ayah)):
                            target_keys.append(r["ayah_key"])
                    break
    elif args.start and args.end:
        s_surah, s_ayah = map(int, args.start.split(":"))
        e_surah, e_ayah = map(int, args.end.split(":"))
        for r in v3_list:
            s, a = r["surah"], r["ayah"]
            if (s > s_surah or (s == s_surah and a >= s_ayah)) and \
               (s < e_surah or (s == e_surah and a <= e_ayah)):
                target_keys.append(r["ayah_key"])
    else:
        print("Please provide --chunk <num> or --start <key> --end <key>")
        sys.exit(1)

    print(f"=== PRE-AUDIT WATCH LIST FOR {target_keys[0]} - {target_keys[-1]} ({len(target_keys)} verses) ===")
    all_findings = []
    for k in target_keys:
        findings = scan_verse(v3_map[k], tq_map[k], v4_map[k])
        all_findings.extend(findings)

    if not all_findings:
        print(" [✓] No suspicious truncations, syntax anomalies, or scholar omission alerts detected.")
        print("     The chunk is mechanically clean. Standard audit can proceed safely.")
        return

    print(f"Found {len(all_findings)} items requiring auditor attention:\n")
    by_ayah = {}
    for item in all_findings:
        by_ayah.setdefault(item["ayah"], []).append(item)

    for ayah, items in by_ayah.items():
        print(f"[{ayah}]")
        for it in items:
            print(f"  - [{it['type']}] {it['detail']}")


if __name__ == "__main__":
    main()
