#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/export_v4_audit_chunk.py
Exports ThaiQuran v4 verses alongside Arabic Uthmani, Thai v3, 2 English translations
(Saheeh International & Hilali-Khan), and Footnotes for Juz-by-Juz LLM audit.

Usage:
  python scripts/export_v4_audit_chunk.py --juz 1
  python scripts/export_v4_audit_chunk.py --all
  python scripts/export_v4_audit_chunk.py --surah 2
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(r"H:\gits\thai_quran_translation_v4")
V4_DATA_PATH = REPO_ROOT / "data" / "06_tq_spacing_and_scholar_fixed.json"
V3_DATA_PATH = Path(r"H:\gits\thai_quran_scholar_audit_v4\final_files\01_thai_quran_translation_v3_master.json")
AR_DATA_PATH = Path(r"H:\gits\thai_quran_scholar_audit_v4\step2_tri_lingual_master.json")
EN_SAHEEH_PATH = Path(r"H:\gits\thai-quran-web\src\data\en_saheeh.json")
EN_HILALI_PATH = Path(r"H:\gits\thai-quran-web\src\data\en_hilali_khan.json")

OUT_DIR = REPO_ROOT / "audit_chunks"
OUT_DIR.mkdir(parents=True, exist_ok=True)

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

FN_TOKEN_RE = re.compile(r"⟦FN:(\d+)⟧")


def parse_key(k: str) -> tuple[int, int]:
    s, a = k.split(":")
    return int(s), int(a)


def is_in_range(ak: str, start_k: str, end_k: str) -> bool:
    cur = parse_key(ak)
    st = parse_key(start_k)
    en = parse_key(end_k)
    return st <= cur <= en


def load_all_datasets():
    print("Loading datasets...")
    with open(V4_DATA_PATH, "r", encoding="utf-8") as f:
        v4_records = json.load(f)
    v4_map = {r["ayah_key"]: r for r in v4_records}

    with open(V3_DATA_PATH, "r", encoding="utf-8") as f:
        v3_list = json.load(f)
    v3_map = {f"{r['surah']}:{r['ayah']}": r["translation"] for r in v3_list}

    with open(AR_DATA_PATH, "r", encoding="utf-8") as f:
        ar_list = json.load(f)
    ar_map = {f"{r['surah']}:{r['ayah']}": r.get("arabic", "").split(" | ")[0].strip() for r in ar_list}

    with open(EN_SAHEEH_PATH, "r", encoding="utf-8") as f:
        en_saheeh = json.load(f)

    with open(EN_HILALI_PATH, "r", encoding="utf-8") as f:
        en_hilali = json.load(f)

    return v4_records, v4_map, v3_map, ar_map, en_saheeh, en_hilali


def export_chunk(chunk_name: str, ak_list: list[str], data_maps: tuple) -> Path:
    _, v4_map, v3_map, ar_map, en_saheeh, en_hilali = data_maps
    out_file = OUT_DIR / f"{chunk_name}.txt"

    lines = []
    lines.append(f"=== THAIQURAN V4 AUDIT CHUNK: {chunk_name.upper()} ===")
    lines.append(f"Verses in this chunk: {len(ak_list)} ({ak_list[0]} to {ak_list[-1]})")
    lines.append("")
    lines.append("CRITICAL AUDIT INSTRUCTIONS (RULE ZERO: NO OVERKILL):")
    lines.append("1. DO NOT rewrite sentences. Only propose fixes for (1) Spacing & Cadence, (2) Spelling & Transliteration, (3) Critical/Theological error.")
    lines.append("2. Output verified fixes in strict JSON format: [{\"ayah\": \"S:A\", \"type\": \"...\", \"target\": \"...\", \"replacement\": \"...\", \"reason\": \"...\"}]")
    lines.append("3. If an ayah is accurate and readable, do NOT touch it.")
    lines.append("================================================================================")
    lines.append("")

    for ak in ak_list:
        v4_rec = v4_map.get(ak)
        if not v4_rec:
            continue

        # Convert ⟦FN:123⟧ to [FN:123] for clean readability
        v4_tok = v4_rec.get("translation_tokenized", "")
        v4_clean_tokens = FN_TOKEN_RE.sub(r"[FN:\1]", v4_tok)

        ar_txt = ar_map.get(ak, "")
        v3_txt = v3_map.get(ak, "")
        saheeh_txt = en_saheeh.get(ak, "")
        hilali_txt = en_hilali.get(ak, "")
        fns = v4_rec.get("footnotes", [])

        lines.append(f"[{ak}]")
        if ar_txt:
            lines.append(f"AR: {ar_txt}")
        lines.append(f"V4: {v4_clean_tokens}")
        if v3_txt:
            lines.append(f"V3: {v3_txt}")
        if saheeh_txt:
            lines.append(f"EN1 (Saheeh): {saheeh_txt}")
        if hilali_txt:
            lines.append(f"EN2 (Hilali-Khan): {hilali_txt}")

        for fn in fns:
            lines.append(f"FN[{fn['id']}]: {fn['text']}")

        lines.append("--------------------------------------------------------------------------------")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Exported {len(ak_list)} verses -> {out_file}")
    return out_file


def main():
    parser = argparse.ArgumentParser(description="Export ThaiQuran v4 audit chunks for LLM review")
    parser.add_argument("--juz", type=int, choices=range(1, 31), help="Juz number (1-30)")
    parser.add_argument("--surah", type=int, choices=range(1, 115), help="Surah number (1-114)")
    parser.add_argument("--all", action="store_true", help="Export all 30 Juz")
    args = parser.parse_args()

    data_maps = load_all_datasets()
    v4_records = data_maps[0]

    all_keys = [r["ayah_key"] for r in v4_records]

    if args.juz:
        st, en = JUZ_BOUNDARIES[args.juz]
        juz_keys = [k for k in all_keys if is_in_range(k, st, en)]
        export_chunk(f"juz_{args.juz:02d}", juz_keys, data_maps)
    elif args.surah:
        surah_keys = [k for k in all_keys if parse_key(k)[0] == args.surah]
        export_chunk(f"surah_{args.surah:03d}", surah_keys, data_maps)
    elif args.all:
        for j in range(1, 31):
            st, en = JUZ_BOUNDARIES[j]
            juz_keys = [k for k in all_keys if is_in_range(k, st, en)]
            export_chunk(f"juz_{j:02d}", juz_keys, data_maps)
    else:
        # Default: export Juz 1 for immediate trial
        print("No specific argument provided. Exporting Juz 1 by default (use --all or --juz N).")
        st, en = JUZ_BOUNDARIES[1]
        juz_keys = [k for k in all_keys if is_in_range(k, st, en)]
        export_chunk("juz_01", juz_keys, data_maps)


if __name__ == "__main__":
    main()
