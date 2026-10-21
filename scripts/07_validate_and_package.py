#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 7: Automated 10-Gate Quality Verification & Master Deliverables Packaging
Validates `data/05_tq_upgrades_cataloged.json` against all 10 quality gates and packages:
  - deliverables/01_thai_quran_translation_v4_master.json
  - deliverables/02_thai_quran_translation_v4_annotated.json
  - deliverables/03_thai_quran_translation_v4_master.csv
  - deliverables/04_thai_v4_scholar_review_sheet.csv
  - reports/phase7_quality_gates_report.json
"""

import csv
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(r"H:\gits\thai_quran_translation_v4")
IN_PHASE5_JSON = REPO_ROOT / "data" / "05_tq_upgrades_cataloged.json"
IN_PHASE2_CSV = REPO_ROOT / "reports" / "phase2_omissions_restored_log.csv"

DELIV_DIR = REPO_ROOT / "deliverables"
DELIV_DIR.mkdir(parents=True, exist_ok=True)

OUT_MASTER_JSON = DELIV_DIR / "01_thai_quran_translation_v4_master.json"
OUT_ANNOTATED_JSON = DELIV_DIR / "02_thai_quran_translation_v4_annotated.json"
OUT_MASTER_CSV = DELIV_DIR / "03_thai_quran_translation_v4_master.csv"
OUT_REVIEW_CSV = DELIV_DIR / "04_thai_v4_scholar_review_sheet.csv"
OUT_GATES_JSON = REPO_ROOT / "reports" / "phase7_quality_gates_report.json"

FORBIDDEN_TRANSLIT_TERMS = (
    "อัลลอฮ์",
    "อัลลลอฮ",
    "อัลลออ",
    "อัลลฮ",
    "ฮัลลอฮ",
    "มลาอิกะฮ์",
    "มะลาอิกะฮฺ",
    "มะลาอิกะฮ์",
    "กิยามะฮ์",
    "อาคิเราะฮ์",
    "อิบาดะฮ์",
    "ฟิรอาวน์",
    "ฟิรเอาน์",
    "ฟิรเอาวน์",
    "ร่อซูล",
    "ร่อซู้ล",
    "นะบี",
    "นูห์",
    "นูหฺ",
    "ยะอ์กูบ",
    "ชุอัยบ์",
    "ละอ์นัต",
    "มุอ์มิน",
    "วะฮีย์",
    "กะอ์บะฮ์",
    "มักกะฮ์",
    "มะดีนะฮ์",
    "ซูเราะฮ์",
    "อายะฮ์",
)

FORBIDDEN_TYPOS = (
    "กล่าว่า",
    "ผุ้",
    "อยุ่",
    "หมุ่",
    "เป้น",
    "แป็น",
    "พรองค์",
    "พระงอค์",
    "คัมภัร์",
    "ปราณี",
    "ปรากฎ",
    "ปฎิเสธ",
    "ปฎิบัติ",
    "กฏหมาย",
    "กฏเกณฑ์",
    "ฟื้นคือชีพ",
    "ซี่ง",
    "ขี้น",
    "เพี่อ",
    "เกิดขั้น",
    "ยิ่งขั้น",
    "ผู้ืั้",
    "แก่ัลลอฮ",
    "ต่อัลลอฮ",
    "แต่ออัลลอฮ",
    "ไม่เชื่อฟังออัลลอฮ",
    "ที่เกรงกลัวออัลลอฮ",
    "เมืออัลลอฮ",
    "เคราะฮฺ",
    "ปลีกตัวอกจาก",
    "รอมฏอน",
    "อัลกรุอาน",
    "กระนั่นหรือ",
    "ได้ให้ในการรับรอง",
    "วิญญาณอันปริสุทธิ์",
    "อย่าภริยา",
    "ต้นพุทธา",
    "ได้มายังพวกเขาได้มายังพวกเขา",
    "มุฮัมมัดฉ",
)


def build_annotated_translation(tokenized_text: str, footnotes: list) -> str:
    """
    Replaces `⟦FN:orig_id⟧` with sequential `[1]`, `[2]`, ... per verse.
    """
    id_to_seq = {str(fn["id"]): fn["seq"] for fn in footnotes}

    def repl(m):
        orig_id = m.group(1)
        seq = id_to_seq[orig_id]
        return f"[{seq}]"

    annotated = re.sub(r"⟦FN:(\d+)⟧", repl, tokenized_text)
    return re.sub(r"[ \t]{2,}", " ", annotated).strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("=== Phase 7: Automated 10-Gate Quality Verification & Deliverables Packaging ===")
    with open(IN_PHASE5_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    master_list = []
    annotated_list = []
    csv_rows = []
    review_rows = []

    # Prepare Phase 2 notes lookup
    phase2_notes = {}
    with open(IN_PHASE2_CSV, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            phase2_notes[r["ayah_key"]] = r

    # Quality Gate Counters
    total_ayahs = len(records)
    surah_set = set()
    total_fns = 0
    fn_token_mismatches = []
    leaked_markers = []
    empty_strings = []
    corrupt_graphemes = []
    unbalanced_parens = []
    forbidden_translit_hits = []
    forbidden_typo_hits = []

    for rec in records:
        ak = rec["ayah_key"]
        s = rec["surah"]
        a = rec["ayah"]
        surah_set.add(s)

        t_tok = rec["translation_tokenized"]
        t_clean = rec["translation"]
        fns = rec.get("footnotes", [])
        total_fns += len(fns)

        # Build sequential footnotes and annotated text
        t_annotated = build_annotated_translation(t_tok, fns)
        clean_fns = [
            {
                "seq": fn["seq"],
                "orig_id": fn["id"],
                "text": fn["text"],
            }
            for fn in fns
        ]

        # Gate 2 check: 1:1 token parity
        tok_ids = re.findall(r"⟦FN:(\d+)⟧", t_tok)
        fn_ids = [str(fn["id"]) for fn in fns]
        ann_seqs = [int(x) for x in re.findall(r"\[(\d+)\]", t_annotated)]
        expected_seqs = [fn["seq"] for fn in fns]
        if tok_ids != fn_ids or ann_seqs != expected_seqs:
            fn_token_mismatches.append(ak)

        # Gate 3 check: Zero leaked markers in clean text
        if "⟦FN:" in t_clean or re.search(r"\(\s*\d+\s*\)", t_clean) or re.search(r"\[\d+\]", t_clean):
            leaked_markers.append(ak)

        # Gate 4 check: Non-empty strings
        if not t_clean.strip():
            empty_strings.append(f"ayah:{ak}")
        for fn in clean_fns:
            if not fn["text"].strip():
                empty_strings.append(f"fn:{ak}:{fn['orig_id']}")

        # Gate 5 check: Corrupt graphemes / stacked tone marks / zero-width / HTML
        for ctx_label, txt in [("ayah", t_clean)] + [(f"fn_{fn['orig_id']}", fn["text"]) for fn in clean_fns]:
            if (
                re.search(r"[\u0E48-\u0E4B]{2,}", txt)
                or re.search(r"[\u0E40\u0E41]\u0E33", txt)
                or re.search(r"[\u200B-\u200D\uFEFF]", txt)
                or re.search(r"<[^>]+>", txt)
            ):
                corrupt_graphemes.append(f"{ak}:{ctx_label}")

        # Gate 6 check: Balanced parentheses
        if t_clean.count("(") != t_clean.count(")"):
            unbalanced_parens.append(f"ayah:{ak}")
        for fn in clean_fns:
            if fn["text"].count("(") != fn["text"].count(")"):
                unbalanced_parens.append(f"fn:{ak}:{fn['orig_id']}")

        # Gate 7 check: 0 Forbidden non-standardized transliterations
        for term in FORBIDDEN_TRANSLIT_TERMS:
            if term in t_clean:
                forbidden_translit_hits.append(f"ayah:{ak}:{term}")
            for fn in clean_fns:
                if term in fn["text"]:
                    forbidden_translit_hits.append(f"fn:{ak}:{fn['orig_id']}:{term}")

        # Gate 8 check: 0 Forbidden OCR typos
        for typo in FORBIDDEN_TYPOS:
            if typo == "ต่อัลลอฮ":
                if re.search(r"(?<!แ)ต่อัลลอฮ", t_clean):
                    forbidden_typo_hits.append(f"ayah:{ak}:{typo}")
                for fn in clean_fns:
                    if re.search(r"(?<!แ)ต่อัลลอฮ", fn["text"]):
                        forbidden_typo_hits.append(f"fn:{ak}:{fn['orig_id']}:{typo}")
            else:
                if typo in t_clean:
                    forbidden_typo_hits.append(f"ayah:{ak}:{typo}")
                for fn in clean_fns:
                    if typo in fn["text"]:
                        forbidden_typo_hits.append(f"fn:{ak}:{fn['orig_id']}:{typo}")

        # Populate deliverables
        master_list.append({
            "surah": s,
            "ayah": a,
            "translation": t_clean,
        })

        annotated_list.append({
            "surah": s,
            "ayah": a,
            "ayah_key": ak,
            "surah_name_th": rec["surah_name_th"],
            "surah_name_ar": rec["surah_name_ar"],
            "translation_clean": t_clean,
            "translation_annotated": t_annotated,
            "v4_vs_v3_category": rec["v4_vs_v3_category"],
            "v4_vs_v3_char_similarity": rec["v4_vs_v3_char_similarity"],
            "footnotes": clean_fns,
        })

        csv_rows.append({
            "surah": s,
            "ayah": a,
            "ayah_key": ak,
            "surah_name_th": rec["surah_name_th"],
            "translation_clean": t_clean,
            "translation_annotated": t_annotated,
            "footnote_count": len(clean_fns),
            "footnotes_json": json.dumps(clean_fns, ensure_ascii=False),
        })

        cat = rec["v4_vs_v3_category"]
        if cat not in ("IDENTICAL_TO_V3", "SPACING_AND_PUNCTUATION_ONLY"):
            p2 = phase2_notes.get(ak, {})
            priority = (
                "1_P0_RESTORED_OMISSION"
                if cat == "CLAUSE_OMISSION_RESTORED"
                else "2_P0_REVERSE_REPAIR"
                if cat == "REVERSE_REPAIR_OVER_V3"
                else "3_P1_THEOLOGICAL_UPGRADE"
                if cat == "THEOLOGICAL_VOCABULARY_UPGRADE"
                else "4_P1_GUIDANCE_UPGRADE"
                if cat == "GUIDANCE_TERMINOLOGY_UPGRADE"
                else "5_P2_PROSE_UPGRADE"
            )
            review_rows.append({
                "review_priority": priority,
                "ayah_key": ak,
                "category": cat,
                "char_similarity": rec["v4_vs_v3_char_similarity"],
                "scholar_note": p2.get("rationale", "ThaiQuran.com official updated translation + v4 standardization"),
                "v3_production": rec["v3_translation"],
                "v4_master_clean": t_clean,
                "v4_master_annotated": t_annotated,
                "footnote_count": len(clean_fns),
            })

    # Gate 9 check: Verify key restored clauses & theological fixes
    v4_lookup = {f"{r['surah']}:{r['ayah']}": r["translation"] for r in master_list}
    gate9_checks = [
        ("22:62", "นั้นมันเป็นเท็จ และแท้จริงอัลลอฮฺพระองค์เป็นผู้ทรงสูงส่ง"),
        ("4:12", "แต่ถ้าพวกเจ้ามีบุตร พวกนางก็จะได้รับหนึ่งในแปด"),
        ("8:1", "และจงปรับปรุงความสัมพันธ์ระหว่างพวกท่านเถิด และจงเชื่อฟังอัลลอฮฺและรอซูลของพระองค์เถิด"),
        ("14:18", "ประดุจดังขี้เถ้าเมื่อลมพัดมันไปอย่างแรงในวันมีพายุ"),
        ("59:7", "และอันใดที่รอซูลได้นำมายังพวกเจ้าก็จงยึดเอาไว้"),
        ("2:286", "โปรดอย่าให้พวกเราแบกสิ่งที่ไม่มีกำลังใด ๆ แก่พวกเราที่จะแบกมันได้"),
        ("31:34", "และไม่มีชีวิตใดรู้สิ่งที่มันจะขวนขวายหาได้ในวันพรุ่งนี้"),
        ("37:125", "และพวกท่านทอดทิ้งผู้ทรงเลิศยิ่งแห่งปวงผู้สร้างกระนั้นหรือ"),
        ("24:35", "และมิได้อยู่ทางตะวันตก"),
        ("69:7", "พระองค์ทรงให้ภัยนั้นเกิดขึ้นแก่พวกเขา"),
    ]
    gate9_failures = [
        f"{ak}: missing '{sub}'" for ak, sub in gate9_checks if sub not in v4_lookup.get(ak, "")
    ]

    # Gate 10 check: Production repositories untouched
    prod_repos = [
        Path(r"H:\gits\thai_quran_scholar_audit_v4"),
        Path(r"H:\gits\thai-quran-web"),
        Path(r"H:\gits\thai-quran-app"),
    ]
    gate10_dirty = []
    for pr in prod_repos:
        if pr.exists():
            res = subprocess.run(
                ["git", "-C", str(pr), "status", "--porcelain"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if res.stdout.strip():
                gate10_dirty.append(f"{pr.name}: {res.stdout.strip()}")

    # Sort review rows by priority then canonical order
    review_rows.sort(key=lambda r: (r["review_priority"], int(r["ayah_key"].split(":")[0]), int(r["ayah_key"].split(":")[1])))

    # Write Deliverables
    with open(OUT_MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(master_list, f, ensure_ascii=False, indent=2)

    with open(OUT_ANNOTATED_JSON, "w", encoding="utf-8") as f:
        json.dump(annotated_list, f, ensure_ascii=False, indent=2)

    with open(OUT_MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "surah",
                "ayah",
                "ayah_key",
                "surah_name_th",
                "translation_clean",
                "translation_annotated",
                "footnote_count",
                "footnotes_json",
            ],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    with open(OUT_REVIEW_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "review_priority",
                "ayah_key",
                "category",
                "char_similarity",
                "scholar_note",
                "v3_production",
                "v4_master_clean",
                "v4_master_annotated",
                "footnote_count",
            ],
        )
        writer.writeheader()
        writer.writerows(review_rows)

    deliverable_hashes = {
        OUT_MASTER_JSON.name: sha256_file(OUT_MASTER_JSON),
        OUT_ANNOTATED_JSON.name: sha256_file(OUT_ANNOTATED_JSON),
        OUT_MASTER_CSV.name: sha256_file(OUT_MASTER_CSV),
        OUT_REVIEW_CSV.name: sha256_file(OUT_REVIEW_CSV),
    }
    for extra_csv in ("05_pipeline1_human_review_v4_synced.csv", "06_pipeline1_remaining_active_reviews_v4.csv"):
        extra_path = DELIV_DIR / extra_csv
        if extra_path.exists():
            deliverable_hashes[extra_csv] = sha256_file(extra_path)

    gates_report = {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "deliverable_hashes_sha256": deliverable_hashes,
        "gates": {
            "gate_01_canonical_verse_and_surah_count": {
                "passed": total_ayahs == 6236 and len(surah_set) == 114,
                "total_ayahs": total_ayahs,
                "total_surahs": len(surah_set),
            },
            "gate_02_footnote_count_and_token_parity": {
                "passed": total_fns == 7338 and len(fn_token_mismatches) == 0,
                "total_footnotes": total_fns,
                "mismatches": fn_token_mismatches,
            },
            "gate_03_zero_leaked_markers_in_clean_master": {
                "passed": len(leaked_markers) == 0,
                "leaked_verses": leaked_markers,
            },
            "gate_04_zero_empty_strings": {
                "passed": len(empty_strings) == 0,
                "empty_items": empty_strings,
            },
            "gate_05_zero_corrupt_graphemes_or_html": {
                "passed": len(corrupt_graphemes) == 0,
                "corrupt_items": corrupt_graphemes,
            },
            "gate_06_balanced_parentheses": {
                "passed": len(unbalanced_parens) == 0,
                "unbalanced_items": unbalanced_parens[:20],
                "unbalanced_count": len(unbalanced_parens),
            },
            "gate_07_phinthu_and_transliteration_compliance": {
                "passed": len(forbidden_translit_hits) == 0,
                "violations": forbidden_translit_hits[:20],
                "violation_count": len(forbidden_translit_hits),
            },
            "gate_08_zero_known_ocr_typos": {
                "passed": len(forbidden_typo_hits) == 0,
                "violations": forbidden_typo_hits[:20],
                "violation_count": len(forbidden_typo_hits),
            },
            "gate_09_omission_restoration_and_factual_fixes": {
                "passed": len(gate9_failures) == 0,
                "failures": gate9_failures,
            },
            "gate_10_production_isolation_untouched": {
                "passed": len(gate10_dirty) == 0,
                "dirty_repos": gate10_dirty,
            },
        },
    }
    all_passed = all(g["passed"] for g in gates_report["gates"].values())
    gates_report["all_10_gates_passed"] = all_passed

    with open(OUT_GATES_JSON, "w", encoding="utf-8") as f:
        json.dump(gates_report, f, ensure_ascii=False, indent=2)

    print("\n--- 10-GATE QUALITY VERIFICATION RESULTS ---")
    for g_name, g_data in gates_report["gates"].items():
        status = "PASS" if g_data["passed"] else "FAIL"
        print(f"  [{status}] {g_name}: {g_data}")

    print(f"\nOVERALL STATUS: {'ALL 10 GATES PASSED (100%)' if all_passed else 'GATE FAILURE DETECTED'}")
    print(f"Packaged Master Deliverables in: {DELIV_DIR}")


if __name__ == "__main__":
    main()
