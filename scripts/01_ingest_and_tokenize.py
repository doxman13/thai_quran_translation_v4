#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1: Ingestion, Native Footnote Tokenization & Deep Thai Unicode Hygiene
Repository: H:\\gits\\thai_quran_translation_v4
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

REPO_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = REPO_ROOT.parent
RAW_SOURCE_EXTERNAL = PARENT_ROOT / "thai_quran_scholar_audit_v4" / "thaiquran_scraper" / "quran_thai_by_surah.json"
RAW_SOURCE_LOCAL = REPO_ROOT / "data" / "00_tq_raw_source.json"
OUT_PHASE1_JSON = REPO_ROOT / "data" / "01_tq_ingested_tokenized.json"
OUT_PHASE1_CSV = REPO_ROOT / "reports" / "phase1_unicode_and_fn_audit.csv"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def deep_unicode_clean(text: str, key: str, audit_rows: list, context: str = "ayah") -> str:
    orig = text

    # 1. NFC normalization & invisible char removal
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    text = text.replace("\u00a0", " ")

    # 2. Decomposed Sara Am normalization
    text = re.sub(r"\u0E4D\u0E32", "\u0E33", text)
    text = re.sub(r"([\u0E48-\u0E4B])\u0E4D\u0E32", "\\1\u0E33", text)

    # 3. Targeted corrupt grapheme sequence repairs verified from forensic audit
    targeted_grapheme_fixes = [
        ("บรรดาผู้\u0e37\u0e31\u0e49ปฏิเสธ", "บรรดาผู้ที่ปฏิเสธ", "CORRUPT_GRAPHEME_5_17"),
        ("บรรดาผู้กล่าวร้ายแก่\u0e31ลลอฮ์", "บรรดาผู้กล่าวร้ายแก่อัลลอฮ์", "MISSING_ANG_33_57"),
        ("น\u0e49\u0e48องชาย", "น้องชาย", "STACKED_MISMATCH_TONE_4_23"),
        ("(ที่\u0e49เที่ยงแท้)", "(ที่เที่ยงแท้)", "STACKED_MISMATCH_TONE_21_87"),
        ("อบอุ่นขึ\u0e48\u0e49น", "อบอุ่นขึ้น", "STACKED_MISMATCH_TONE_28_29"),
        ("แท้จริงการนี\u0e35\u0e49\u0e49ย่อมเป็นสัญญาแก่หมู่ชน", "แท้จริงในการนี้ย่อมเป็นสัญญาณแก่หมู่ชน", "STACKED_VOWEL_TONE_30_37"),
        (
            "ให้แก่ผู้กระทำความดส่วนผู้กระทำความชั่วนั้นจะถูกตอบแทนเท่าที่เขาได้กระทำไว้\u0e35",
            "ให้แก่ผู้กระทำความดี ส่วนผู้กระทำความชั่วนั้นจะถูกตอบแทนเท่าที่เขาได้กระทำไว้",
            "DISPLACED_VOWEL_FN_28_84",
        ),
    ]
    for bad, good, reason in targeted_grapheme_fixes:
        if bad in text:
            text = text.replace(bad, good)
            audit_rows.append({
                "ayah_key": key,
                "context": context,
                "category": reason,
                "before": bad,
                "after": good,
            })

    # 4. Deduplicate identical consecutive tone marks (e.g., ที่่ -> ที่, ผู้้ -> ผู้, เบื้้อง -> เบื้อง)
    for m in re.finditer(r"\S*([\u0E48-\u0E4B])\1+\S*", text):
        token_before = m.group(0)
        token_after = re.sub(r"([\u0E48-\u0E4B])\1+", r"\1", token_before)
        audit_rows.append({
            "ayah_key": key,
            "context": context,
            "category": "DUPLICATE_TONE_MARK",
            "before": token_before,
            "after": token_after,
        })
    text = re.sub(r"([\u0E48-\u0E4B])\1+", r"\1", text)

    # 5. Deduplicate identical consecutive upper/lower vowels or karan (e.g., ทีี่ -> ที่, นูห์์ -> นูห์)
    for m in re.finditer(r"\S*([\u0E31\u0E34-\u0E3A\u0E47\u0E4C\u0E4D])\1+\S*", text):
        token_before = m.group(0)
        token_after = re.sub(r"([\u0E31\u0E34-\u0E3A\u0E47\u0E4C\u0E4D])\1+", r"\1", token_before)
        audit_rows.append({
            "ayah_key": key,
            "context": context,
            "category": "DUPLICATE_VOWEL_OR_KARAN",
            "before": token_before,
            "after": token_after,
        })
    text = re.sub(r"([\u0E31\u0E34-\u0E3A\u0E47\u0E4C\u0E4D])\1+", r"\1", text)

    # 6. Collapse multiple spaces
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return text


def main():
    print("=== Phase 1: Ingestion, Native Footnote Tokenization & Deep Unicode Hygiene ===")
    shutil.copy2(RAW_SOURCE_EXTERNAL, RAW_SOURCE_LOCAL)
    checksum = sha256_file(RAW_SOURCE_LOCAL)
    print(f"Copied immutable raw source -> {RAW_SOURCE_LOCAL.name} (SHA-256: {checksum[:16]}...)")

    with open(RAW_SOURCE_LOCAL, "r", encoding="utf-8") as f:
        raw_surahs = json.load(f)

    # Build lookup by ayah_key
    ayah_lookup = {}
    ordered_ayahs = []
    for s in raw_surahs:
        s_num = s["surah_number"]
        s_name_th = s.get("surah_name_th", "")
        s_name_ar = s.get("surah_name_ar", "")
        for a in s.get("ayahs", []):
            entry = {
                "surah": s_num,
                "ayah": a["ayah_number"],
                "ayah_key": a["ayah_key"],
                "surah_name_th": s_name_th,
                "surah_name_ar": s_name_ar,
                "translation_raw": a["translation"],
                "translation_working": a["translation"],
                "footnotes_raw": list(a.get("footnotes", [])),
            }
            ayah_lookup[a["ayah_key"]] = entry
            ordered_ayahs.append(entry)

    audit_rows = []

    # Step 1A: Repair misplaced footnote lists across adjacent verses (5 pairs)
    fn_moves = [
        ("8:59", "8:60", {"148", "149", "150"}),
        ("10:106", "10:107", {"102"}),
        ("24:63", "24:64", {"133", "134", "135"}),
        ("40:50", "40:52", {"64", "65"}),
        ("40:56", "40:64", {"78", "79", "80"}),
    ]
    for src_k, dst_k, target_ids in fn_moves:
        src_fns = ayah_lookup[src_k]["footnotes_raw"]
        kept, moved = [], []
        for fn_str in src_fns:
            m = re.match(r"^\s*\((\d+)\)", fn_str)
            if m and m.group(1) in target_ids:
                moved.append(fn_str)
            else:
                kept.append(fn_str)
        ayah_lookup[src_k]["footnotes_raw"] = kept
        ayah_lookup[dst_k]["footnotes_raw"].extend(moved)
        audit_rows.append({
            "ayah_key": f"{src_k}->{dst_k}",
            "context": "footnote_reassignment",
            "category": "MISPLACED_FOOTNOTE_MOVED",
            "before": f"{src_k} had {sorted(target_ids)}",
            "after": f"Moved {len(moved)} footnotes to {dst_k}",
        })

    # Step 1B: Repair inline footnote marker typos & missing inline markers
    inline_marker_fixes = [
        ("27:16", "และเราได้รับทุกๆ สิ่ง(27)", "และเราได้รับทุกๆ สิ่ง(26)", "INLINE_FN_TYPO_27_TO_26"),
        ("28:7", "เป็นหนึ่งในบรรดาร่อซูล”(15)", "เป็นหนึ่งในบรรดาร่อซูล”(16)", "INLINE_FN_TYPO_15_TO_16"),
        ("47:20", "จงประสบแก่พวกเขาเถิด(12)", "จงประสบแก่พวกเขาเถิด(21)", "INLINE_FN_TYPO_12_TO_21"),
        ("22:34", "กล่าวพระนามของอัลลอฮ์(45) ต่อสิ่งที่", "กล่าวพระนามของอัลลอฮ์ ต่อสิ่งที่", "DUPLICATE_INLINE_FN_45_REMOVED"),
        ("9:53", "เป็นพวกที่ละเมิด", "เป็นพวกที่ละเมิด(127)", "RESTORE_INLINE_FN_127"),
        ("19:76", "ในการกลับ(ไปสู่พระองค์)", "ในการกลับ(ไปสู่พระองค์)(69)", "RESTORE_INLINE_FN_69"),
        ("28:23", "“เรื่องราวของเธอทั้งสองเป็นมาอย่างไร ?”", "“เรื่องราวของเธอทั้งสองเป็นมาอย่างไร ?”(51)", "RESTORE_INLINE_FN_51"),
        ("28:25", "เดินมาอย่างขวยเขิน", "เดินมาอย่างขวยเขิน(55)", "RESTORE_INLINE_FN_55"),
        ("28:31", "เขาก็ผินหลังกลับและไม่กลับมามองอีก", "เขาก็ผินหลังกลับและไม่กลับมามองอีก(67)", "RESTORE_INLINE_FN_67"),
        ("28:79", "บรรดาผู้ปรารถนาชีวิตแห่งโลกนี้", "บรรดาผู้ปรารถนาชีวิตแห่งโลกนี้(176)", "RESTORE_INLINE_FN_176"),
        ("100:11", "ทรงตระหนักในพวกเขาอย่างแน่นอน", "ทรงตระหนักในพวกเขาอย่างแน่นอน(6)", "RESTORE_INLINE_FN_6"),
    ]
    for k, old_sub, new_sub, reason in inline_marker_fixes:
        t = ayah_lookup[k]["translation_working"]
        assert old_sub in t, f"Expected substring {old_sub!r} not found in {k}: {t!r}"
        ayah_lookup[k]["translation_working"] = t.replace(old_sub, new_sub, 1)
        audit_rows.append({
            "ayah_key": k,
            "context": "inline_footnote_marker",
            "category": reason,
            "before": old_sub,
            "after": new_sub,
        })

    # Fix 58:7 footnote header typo ((10) -> (10)
    ayah_lookup["58:7"]["footnotes_raw"] = [
        fn.replace("((10)", "(10)", 1) for fn in ayah_lookup["58:7"]["footnotes_raw"]
    ]
    audit_rows.append({
        "ayah_key": "58:7",
        "context": "footnote_header",
        "category": "DOUBLE_PAREN_FN_HEADER",
        "before": "((10)",
        "after": "(10)",
    })

    # Remove upstream empty footnote (43) on 13:41 and its inline marker (43)
    ayah_lookup["13:41"]["translation_working"] = ayah_lookup["13:41"]["translation_working"].replace("(43)", "", 1)
    ayah_lookup["13:41"]["footnotes_raw"] = []
    audit_rows.append({
        "ayah_key": "13:41",
        "context": "footnote_43",
        "category": "EMPTY_UPSTREAM_FOOTNOTE_REMOVED",
        "before": "(43) [empty body]",
        "after": "[removed empty footnote]",
    })

    # Remove duplicated Footnote 4 text accidentally appended to Footnote 3 on 14:3
    dup_fn4_in_14_3 = " 4. เพื่อที่จะชี้แจงบทบัญญัติของอัลลอฮ์ เพื่อให้พวกเขาเข้าใจจุดมุ่งหมายของพระองค์ และเพื่อให้เป้าหมายของการเป็นร่อซูลมีความสมบูรณ์"
    ayah_lookup["14:3"]["footnotes_raw"] = [
        fn.replace(dup_fn4_in_14_3, "") for fn in ayah_lookup["14:3"]["footnotes_raw"]
    ]
    audit_rows.append({
        "ayah_key": "14:3",
        "context": "footnote_3",
        "category": "DUPLICATED_NEXT_FOOTNOTE_STRIPPED",
        "before": "...ความใคร่ของเขา 4. เพื่อที่จะชี้แจง...",
        "after": "...ความใคร่ของเขา",
    })

    # Step 1C: Muqatta'at parenthetical standardization in 2:1 and 7:1
    muqattaat_fixes = [
        ("2:1", "อะลีฟ ลาม มีม(6)(อัลลอฮ์ทรงทราบความหมายของอักษรย่อนี้)", "อะลิฟ ลาม มีม(6)"),
        ("7:1", "อะลิฟ ลาม มีม ศอด(อัลลอฮ์เท่านั้นที่ทราบความหมายของอักษรเหล่านั้น)", "อะลิฟ ลาม มีม ศอด"),
    ]
    for k, old_m, new_m in muqattaat_fixes:
        t = ayah_lookup[k]["translation_working"].strip()
        assert t == old_m, f"Unexpected {k}: {t!r}"
        ayah_lookup[k]["translation_working"] = new_m
        audit_rows.append({
            "ayah_key": k,
            "context": "ayah",
            "category": "MUQATTAAT_PARENTHETICAL_STANDARDIZED",
            "before": old_m,
            "after": new_m,
        })

    # Step 1D: Tokenize inline (N) -> ⟦FN:N⟧ and verify 100% 1:1 alignment with footnotes_raw
    fn_call_re = re.compile(r"\((\d+)\)")
    total_tokens = 0
    total_fns = 0
    output_records = []

    for item in ordered_ayahs:
        k = item["ayah_key"]
        t = item["translation_working"]

        inline_ids = fn_call_re.findall(t)
        parsed_fns = []
        for idx, fn_str in enumerate(item["footnotes_raw"], start=1):
            m = re.match(r"^\s*\((\d+)\)\s*(.*)", fn_str, re.DOTALL)
            assert m, f"Footnote in {k} missing (id): {fn_str!r}"
            fid, fbody = m.group(1), m.group(2).strip()
            fbody_clean = deep_unicode_clean(fbody, k, audit_rows, context=f"footnote_{fid}")
            parsed_fns.append({
                "id": fid,
                "seq": idx,
                "text_raw": fbody,
                "text": fbody_clean,
            })

        fn_ids_list = [f["id"] for f in parsed_fns]
        assert inline_ids == fn_ids_list, f"Mismatch in {k}: inline={inline_ids} vs list={fn_ids_list}"

        # Replace (N) with protected token ⟦FN:N⟧
        t_tokenized = fn_call_re.sub(r"⟦FN:\1⟧", t)
        t_tokenized = deep_unicode_clean(t_tokenized, k, audit_rows, context="ayah")

        # Also generate clean preview (tokens stripped)
        t_clean = re.sub(r"\s*⟦FN:\d+⟧\s*", " ", t_tokenized)
        t_clean = re.sub(r"[ \t]{2,}", " ", t_clean).strip()

        total_tokens += len(inline_ids)
        total_fns += len(parsed_fns)

        output_records.append({
            "surah": item["surah"],
            "ayah": item["ayah"],
            "ayah_key": k,
            "surah_name_th": item["surah_name_th"],
            "surah_name_ar": item["surah_name_ar"],
            "translation_raw": item["translation_raw"],
            "translation_tokenized": t_tokenized,
            "translation": t_clean,
            "footnotes": parsed_fns,
        })

    assert len(output_records) == 6236, f"Expected 6236 ayahs, got {len(output_records)}"
    assert total_tokens == 7338 and total_fns == 7338, f"Expected 7338 non-empty footnotes, got {total_tokens}/{total_fns}"

    with open(OUT_PHASE1_JSON, "w", encoding="utf-8") as f:
        json.dump(output_records, f, ensure_ascii=False, indent=2)

    with open(OUT_PHASE1_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ayah_key", "context", "category", "before", "after"])
        writer.writeheader()
        writer.writerows(audit_rows)

    print(f"Verified 6,236 Ayahs and {total_fns:,} Footnotes with 0 alignment mismatches.")
    print(f"Logged {len(audit_rows)} Phase 1 structural/Unicode/footnote repairs -> {OUT_PHASE1_CSV.name}")
    print(f"Saved Phase 1 dataset -> {OUT_PHASE1_JSON.name}")


if __name__ == "__main__":
    main()
