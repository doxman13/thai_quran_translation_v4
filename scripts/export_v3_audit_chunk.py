#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/export_v3_audit_chunk.py
Exports Master V3 verses alongside Arabic Uthmani, ThaiQuran reference,
2 English translations (Saheeh International & Hilali-Khan), and Footnotes
for Juz-by-Juz or Subchunk LLM audit.

Architecture:
  - Base: Master V3 (King Fahd revised clean text)
  - Reference / Fixer: ThaiQuran.com (supplies missing clauses & footnotes)
  - Supreme Truth: Arabic Uthmani (AR)

Usage:
  python scripts/export_v3_audit_chunk.py --juz 1
  python scripts/export_v3_audit_chunk.py --juz 1 --subchunks
  python scripts/export_v3_audit_chunk.py --all
  python scripts/export_v3_audit_chunk.py --all --subchunks
  python scripts/export_v3_audit_chunk.py --surah 2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = REPO_ROOT.parent

BASE_DATA_PATH = REPO_ROOT / "data" / "01_v3_base_master.json"
AR_DATA_PATH = PARENT_ROOT / "thai_quran_scholar_audit_v4" / "step2_tri_lingual_master.json"
EN_SAHEEH_PATH = PARENT_ROOT / "thai-quran-web" / "src" / "data" / "en_saheeh.json"
EN_HILALI_PATH = PARENT_ROOT / "thai-quran-web" / "src" / "data" / "en_hilali_khan.json"

OUT_DIR = REPO_ROOT / "audit_chunks"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUBCHUNK_DIR = OUT_DIR / "subchunks"
SUBCHUNK_DIR.mkdir(parents=True, exist_ok=True)

FN_TOKEN_RE = re.compile(r"⟦FN:(\d+)⟧")
FN_BRACKET_RE = re.compile(r"\[(\d+)\]")

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

SUBCHUNKS_127 = [
    # Juz 1
    (1, "1:1-2:43"), (1, "2:44-2:91"), (1, "2:92-2:141"),
    # Juz 2
    (2, "2:142-2:176"), (2, "2:177-2:218"), (2, "2:219-2:252"),
    # Juz 3
    (3, "2:253-2:286"), (3, "3:1-3:45"), (3, "3:46-3:92"),
    # Juz 4
    (4, "3:93-3:148"), (4, "3:149-3:200"), (4, "4:1-4:23"),
    # Juz 5
    (5, "4:24-4:65"), (5, "4:66-4:104"), (5, "4:105-4:147"),
    # Juz 6
    (6, "4:148-4:176"), (6, "5:1-5:40"), (6, "5:41-5:81"),
    # Juz 7
    (7, "5:82-5:120"), (7, "6:1-6:58"), (7, "6:59-6:110"),
    # Juz 8
    (8, "6:111-6:165"), (8, "7:1-7:46"), (8, "7:47-7:87"),
    # Juz 9
    (9, "7:88-7:147"), (9, "7:148-7:206"), (9, "8:1-8:40"),
    # Juz 10
    (10, "8:41-8:75"), (10, "9:1-9:45"), (10, "9:46-9:92"),
    # Juz 11
    (11, "9:93-9:129"), (11, "10:1-10:60"), (11, "10:61-10:109"), (11, "11:1-11:5"),
    # Juz 12
    (12, "11:6-11:60"), (12, "11:61-11:123"), (12, "12:1-12:52"),
    # Juz 13
    (13, "12:53-12:111"), (13, "13:1-13:43"), (13, "14:1-14:52"),
    # Juz 14
    (14, "15:1-15:99"), (14, "16:1-16:64"), (14, "16:65-16:128"),
    # Juz 15
    (15, "17:1-17:55"), (15, "17:56-17:111"), (15, "18:1-18:74"),
    # Juz 16
    (16, "18:75-18:110"), (16, "19:1-19:98"), (16, "20:1-20:76"), (16, "20:77-20:135"),
    # Juz 17
    (17, "21:1-21:50"), (17, "21:51-21:112"), (17, "22:1-22:41"), (17, "22:42-22:78"),
    # Juz 18
    (18, "23:1-23:62"), (18, "23:63-23:118"), (18, "24:1-24:34"), (18, "24:35-24:64"), (18, "25:1-25:20"),
    # Juz 19
    (19, "25:21-25:77"), (19, "26:1-26:104"), (19, "26:105-26:227"), (19, "27:1-27:55"),
    # Juz 20
    (20, "27:56-27:93"), (20, "28:1-28:43"), (20, "28:44-28:88"), (20, "29:1-29:45"),
    # Juz 21
    (21, "29:46-29:69"), (21, "30:1-30:60"), (21, "31:1-31:34"), (21, "32:1-32:30"), (21, "33:1-33:30"),
    # Juz 22
    (22, "33:31-33:73"), (22, "34:1-34:54"), (22, "35:1-35:45"), (22, "36:1-36:27"),
    # Juz 23
    (23, "36:28-36:83"), (23, "37:1-37:82"), (23, "37:83-37:182"), (23, "38:1-38:88"), (23, "39:1-39:31"),
    # Juz 24
    (24, "39:32-39:75"), (24, "40:1-40:40"), (24, "40:41-40:85"), (24, "41:1-41:46"),
    # Juz 25
    (25, "41:47-41:54"), (25, "42:1-42:53"), (25, "43:1-43:89"), (25, "44:1-44:59"), (25, "45:1-45:37"),
    # Juz 26
    (26, "46:1-46:35"), (26, "47:1-47:38"), (26, "48:1-48:29"), (26, "49:1-49:18"), (26, "50:1-50:45"), (26, "51:1-51:30"),
    # Juz 27
    (27, "51:31-51:60"), (27, "52:1-52:49"), (27, "53:1-53:62"), (27, "54:1-54:55"), (27, "55:1-55:78"), (27, "56:1-56:96"), (27, "57:1-57:29"),
    # Juz 28
    (28, "58:1-58:22"), (28, "59:1-59:24"), (28, "60:1-60:13"), (28, "61:1-61:14"), (28, "62:1-62:11"), (28, "63:1-63:11"), (28, "64:1-64:18"), (28, "65:1-65:12"), (28, "66:1-66:12"),
    # Juz 29
    (29, "67:1-67:30"), (29, "68:1-68:52"), (29, "69:1-69:52"), (29, "70:1-70:44"), (29, "71:1-71:28"), (29, "72:1-72:28"), (29, "73:1-73:20"), (29, "74:1-74:56"), (29, "75:1-75:40"), (29, "76:1-76:31"), (29, "77:1-77:50"),
    # Juz 30
    (30, "78:1-79:46"), (30, "80:1-89:30"), (30, "90:1-100:11"), (30, "101:1-114:6"),
]


def parse_key(k: str) -> tuple[int, int]:
    s, a = k.split(":")
    return int(s), int(a)


def is_in_range(k: str, start: str, end: str) -> bool:
    kp = parse_key(k)
    return parse_key(start) <= kp <= parse_key(end)


def load_all_datasets():
    with open(BASE_DATA_PATH, "r", encoding="utf-8") as f:
        base_records = json.load(f)

    base_map = {r["ayah_key"]: r for r in base_records}

    with open(AR_DATA_PATH, "r", encoding="utf-8") as f:
        ar_data = json.load(f)
    ar_map = {f"{x['surah']}:{x['ayah']}": x["arabic"] for x in ar_data}

    with open(EN_SAHEEH_PATH, "r", encoding="utf-8") as f:
        en_saheeh = json.load(f)
    with open(EN_HILALI_PATH, "r", encoding="utf-8") as f:
        en_hilali = json.load(f)

    return base_records, base_map, ar_map, en_saheeh, en_hilali


def export_chunk(chunk_name: str, ak_list: list[str], data_maps: tuple, out_folder: Path = OUT_DIR) -> Path:
    base_records, base_map, ar_map, en_saheeh, en_hilali = data_maps
    out_file = out_folder / f"{chunk_name}.txt"

    lines = []
    lines.append(f"=== THAI QURAN MASTER SYNTHESIS AUDIT: {chunk_name.upper()} ===")
    lines.append(f"Verses in this chunk: {len(ak_list)} ({ak_list[0]} to {ak_list[-1]})")
    lines.append("")
    lines.append("CRITICAL AUDIT INSTRUCTIONS (READ CAREFULLY):")
    lines.append("1. RULE ZERO: NO OVERKILL. Do NOT rewrite natural, accurate Thai sentences.")
    lines.append("   Preserve the original King Fahd phrasing unless there is a factual error, omission, or severe typo.")
    lines.append("2. DE-OVERKILL SPACING: Remove unnecessary, unnatural, or chopped-up spaces.")
    lines.append("   Thai is written continuously without spaces between words.")
    lines.append("   Keep spaces ONLY for natural breath pauses, dialogue breaks, list items, or clause boundaries.")
    lines.append("3. BASE TEXT IS V3. Arabic (AR) is the SUPREME SOURCE OF TRUTH.")
    lines.append("   - If V3 accurately conveys AR: DO NOT TOUCH IT.")
    lines.append("   - If V3 has an Arabic defect (dropped clause, missing word): Check TQ. If TQ is accurate, patch V3 using TQ.")
    lines.append("   - If BOTH V3 & TQ have an error against Arabic: Propose scholarly correction based on Arabic.")
    lines.append("4. FOOTNOTE PLACEMENT CHECK:")
    lines.append("   Verify that [FN:N] markers sit at the END of the concept/phrase they explain (e.g. after the full term 'อะลิฟ ลาม มีม[FN:1]', not mid-word or awkwardly placed).")
    lines.append("5. OUTPUT STRICT JSON FORMAT ONLY:")
    lines.append('[')
    lines.append('  {')
    lines.append('    "ayah": "S:A",')
    lines.append('    "type": "OMISSION" | "TYPO" | "SPACING" | "FN_PLACEMENT" | "THEOLOGICAL",')
    lines.append('    "target": "exact substring in V3 to replace",')
    lines.append('    "replacement": "new substring",')
    lines.append('    "reason": "concise explanation"')
    lines.append('  }')
    lines.append(']')
    lines.append("If all verses in this chunk are accurate and readable, output: []")
    lines.append("================================================================================")

    for ak in ak_list:
        rec = base_map.get(ak)
        if not rec:
            continue

        ar_txt = ar_map.get(ak, "")
        saheeh_txt = en_saheeh.get(ak, "")
        hilali_txt = en_hilali.get(ak, "")

        v3_base = rec.get("translation_v3", "")
        v3_ann = rec.get("translation_annotated", "")
        # Format footnote markers nicely as [FN:N]
        v3_display = FN_BRACKET_RE.sub(r"[FN:\1]", v3_ann)
        if not v3_display:
            v3_display = v3_base

        tq_ref = rec.get("tq_reference", "")
        tq_tok = rec.get("tq_tokenized", "")
        tq_display = FN_TOKEN_RE.sub(r"[FN:\1]", tq_tok) if tq_tok else tq_ref

        fns = rec.get("footnotes", [])

        lines.append(f"[{ak}]")
        if ar_txt:
            lines.append(f"AR: {ar_txt}")
        lines.append(f"V3 (BASE): {v3_display}")
        if tq_display:
            lines.append(f"TQ (REF):  {tq_display}")
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


def export_subchunks_for_juz(target_juz: int, all_keys: list[str], data_maps: tuple):
    juz_subchunks = [sc for sc in SUBCHUNKS_127 if sc[0] == target_juz]
    for idx, (_, r_str) in enumerate(juz_subchunks, 1):
        st, en = r_str.split("-")
        clean_r_str = r_str.replace(":", "_").replace("-", "_to_")
        chunk_name = f"juz_{target_juz:02d}_part{idx}_{clean_r_str}"
        chunk_keys = [k for k in all_keys if is_in_range(k, st, en)]
        export_chunk(chunk_name, chunk_keys, data_maps, out_folder=SUBCHUNK_DIR)


def main():
    parser = argparse.ArgumentParser(description="Export Master V3 audit chunks for Gemini review")
    parser.add_argument("--juz", type=int, choices=range(1, 31), help="Juz number (1-30)")
    parser.add_argument("--surah", type=int, choices=range(1, 115), help="Surah number (1-114)")
    parser.add_argument("--all", action="store_true", help="Export all 30 Juz")
    parser.add_argument("--subchunks", action="store_true", help="Export 35-50 verse subchunks (127 chunks)")
    args = parser.parse_args()

    data_maps = load_all_datasets()
    base_records = data_maps[0]
    all_keys = [r["ayah_key"] for r in base_records]

    if args.juz:
        st, en = JUZ_BOUNDARIES[args.juz]
        juz_keys = [k for k in all_keys if is_in_range(k, st, en)]
        export_chunk(f"juz_{args.juz:02d}", juz_keys, data_maps, out_folder=OUT_DIR)
        if args.subchunks:
            export_subchunks_for_juz(args.juz, all_keys, data_maps)

    elif args.surah:
        surah_keys = [k for k in all_keys if parse_key(k)[0] == args.surah]
        export_chunk(f"surah_{args.surah:03d}", surah_keys, data_maps, out_folder=OUT_DIR)

    elif args.all:
        for j in range(1, 31):
            st, en = JUZ_BOUNDARIES[j]
            juz_keys = [k for k in all_keys if is_in_range(k, st, en)]
            export_chunk(f"juz_{j:02d}", juz_keys, data_maps, out_folder=OUT_DIR)
            if args.subchunks:
                export_subchunks_for_juz(j, all_keys, data_maps)
    else:
        print("Defaulting to Juz 1 (with subchunks). Use --all or --juz N for others.")
        st, en = JUZ_BOUNDARIES[1]
        juz_keys = [k for k in all_keys if is_in_range(k, st, en)]
        export_chunk("juz_01", juz_keys, data_maps, out_folder=OUT_DIR)
        export_subchunks_for_juz(1, all_keys, data_maps)


if __name__ == "__main__":
    main()
