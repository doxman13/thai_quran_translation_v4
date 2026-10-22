#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 4: Transliteration & Quranic Phinthu (ฺ U+0E3A) Standardization
Standardizes Arabic/Islamic transliterations and converts Karan (์ U+0E4C) to
Quranic Phinthu (ฺ U+0E3A) across all 6,236 Ayahs, 7,339 Footnotes, and 114 Surah names,
preserving 100% of native ⟦FN:N⟧ tokens.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PHASE3_JSON = REPO_ROOT / "data" / "03_tq_typos_remediated.json"
OUT_PHASE4_JSON = REPO_ROOT / "data" / "04_tq_standardized.json"
OUT_PHASE4_CSV = REPO_ROOT / "reports" / "phase4_translit_change_log.csv"

# Ordered Canonical Transliteration & Phinthu Replacement Matrix
CANONICAL_REPLACEMENTS = [
    # 1. Divine Name & Core Expressions (including OCR variants of Allah/Rasulullah)
    ("อัลลลอฮ์", "อัลลอฮฺ"),
    ("อัลลออฮ์", "อัลลอฮฺ"),
    ("อัลลออ์", "อัลลอฮฺ"),
    ("อัลลฮ์", "อัลลอฮฺ"),
    ("อัลออฮ์", "อัลลอฮฺ"),
    ("อัลลอ์", "อัลลอฮฺ"),
    ("ฮัลลอฮ์", "อัลลอฮฺ"),
    ("อัลลอฮ์", "อัลลอฮฺ"),
    ("ร่อซูลุลอฮ์", "รอซูลุลลอฮฺ"),
    ("รอซูลุลอฮ์", "รอซูลุลลอฮฺ"),
    ("ร่อซูลุลลอฮ์", "รอซูลุลลอฮฺ"),
    ("ร่อซูลุลลอฮฺ", "รอซูลุลลอฮฺ"),
    ("รอซูลุลลอฮ์", "รอซูลุลลอฮฺ"),
    ("อับดุลลอฮ์", "อับดุลลอฮฺ"),
    ("บัยตุลลอฮ์", "บัยตุลลอฮฺ"),
    ("ซิกรุลลอฮ์", "ซิกรุลลอฮฺ"),
    ("ศ็อลลัลลอฮ์", "ศ็อลลัลลอฮฺ"),
    ("เคาะลีลุลลอฮ์", "เคาะลีลุลลอฮฺ"),
    ("คอลีลุลลอฮ์", "คอลีลุลลอฮฺ"),
    ("บิสมิลลาฮ์", "บิสมิลลาฮฺ"),
    ("ซุบฮานัลลอฮ์", "ซุบฮานัลลอฮฺ"),
    ("ซุบฮ์านัลลอฮ์", "ซุบฮานัลลอฮฺ"),
    ("อินชาอัลลอฮ์", "อินชาอัลลอฮฺ"),
    ("อัลฮัมดุลิลลาฮ์", "อัลฮัมดุลิลลาฮฺ"),
    ("อัลฮัมดุลิลลอฮ์", "อัลฮัมดุลิลลาฮฺ"),
    ("อิลลัลลอฮ์", "อิลลัลลอฮฺ"),
    ("ศ็ลลัลลอฮุ", "ศ็อลลัลลอฮุ"),
    ("ศ็อลัลลอฮุ", "ศ็อลลัลลอฮุ"),
    ("อะอูซุบิลลาฮ์", "อะอูซุบิลลาฮฺ"),
    ("อายะฮนี้", "อายะฮฺนี้"),
    ("อัลเราะห์มาน", "อัลเราะฮฺมาน"),
    ("อัรเราะห์มาน", "อัรเราะฮฺมาน"),
    ("เราะห์มาน", "เราะฮฺมาน"),
    ("รอห์มาน", "รอฮฺมาน"),
    ("เราะห์มัต", "เราะฮฺมัต"),
    ("เราะห์มัด", "เราะฮฺมัด"),

    # 2. Prophets, Messengers, Angels & Quranic Figures
    ("ร่อซูล", "รอซูล"),
    ("ร่อซู้ล", "รอซูล"),
    ("นะบี", "นบี"),
    ("มะลาอิกะฮฺ", "มลาอิกะฮฺ"),
    ("มะลาอิกะฮ์", "มลาอิกะฮฺ"),
    ("มลาอิกะฮ์", "มลาอิกะฮฺ"),
    ("มะลาอิกะห์", "มลาอิกะฮฺ"),
    ("มลาอิกะห์", "มลาอิกะฮฺ"),
    ("มะลาอีกะฮ์", "มลาอิกะฮฺ"),
    ("มลาอีกะฮ์", "มลาอิกะฮฺ"),
    ("มลาอิกะอ์", "มลาอิกะฮฺ"),
    ("มลาอิกะอฺ", "มลาอิกะฮฺ"),
    ("ญิบริล", "ญิบรีล"),
    ("อัรรูห์", "อัรรูฮฺ"),
    ("อัลรูฮ์", "อัลรูฮฺ"),
    ("ฟิรอาวน์", "ฟิรเอานฺ"),
    ("ฟิรเอาน์", "ฟิรเอานฺ"),
    ("ฟิรเอาวน์", "ฟิรเอานฺ"),
    ("ฟิรอานว์", "ฟิรเอานฺ"),
    ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    ("ฟีรเอานฺ", "ฟิรเอานฺ"),
    ("อิบรอฮิม", "อิบรอฮีม"),
    ("อิบราฮิม", "อิบรอฮีม"),
    ("อิสมาอิล", "อิสมาอีล"),
    ("อิสราอีล", "อิสรออีล"),
    ("บนีอิสรออีล", "บะนีอิสรออีล"),
    ("ยะบีอิสรออีล", "บะนีอิสรออีล"),
    ("ยะอ์กูบ", "ยะอฺกูบ"),
    ("โอ้ยะห์ยา", "โอ้ยะฮฺยา"),
    ("ยะฮห์ยา", "ยะฮฺยา"),
    ("ยะห์ยา", "ยะฮฺยา"),
    ("นูห์", "นูฮฺ"),
    ("นูฮ์", "นูฮฺ"),
    ("นูหฺ", "นูฮฺ"),
    ("นุห์", "นูฮฺ"),
    ("นุฮฺ", "นูฮฺ"),
    ("อัลมะซีห์", "อัลมะซีหฺ"),
    ("มะซีห์", "มะซีหฺ"),
    ("มัรยัม", "มัรฺยัม"),
    ("อิบน์นูน", "อิบนฺนูน"),
    ("ชุอัยบ์", "ชุอัยบฺ"),
    ("ชุไอบ์", "ชุอัยบฺ"),
    ("ศอลิห์", "ศอลิหฺ"),
    ("ศอและห์", "ศอและฮฺ"),
    ("ซอและห์", "ซอและฮฺ"),
    ("อัลยะสะอ์", "อัลยะสะอฺ"),
    ("อัลยะซะอ์", "อัลยะซะอฺ"),
    ("ลู๊ฏ", "ลูฏ"),
    ("นบีลูต", "นบีลูฏ"),
    ("มูฮัมหมัด", "มุฮัมมัด"),
    ("มูฮัมมัด", "มุฮัมมัด"),
    ("ดุลกอฮ์นัยน์", "ซุลก็อรนัยนฺ"),
    ("ซุลก็อรนัยน์", "ซุลก็อรนัยนฺ"),
    ("อุซัยร์", "อุซัยรฺ"),
    ("ฎอลูต", "ฏอลูต"),
    ("บะอ์ลฺ", "บะอฺลฺ"),
    ("บะอ์ล์", "บะอฺลฺ"),
    ("สะบะอ์", "สะบะอฺ"),
    ("ตุบบะอ์", "ตุบบะอฺ"),
    ("ตุ๊บบะอ์", "ตุ๊บบะอฺ"),
    ("ยะอ์ญูจ", "ยะอฺญูจ"),
    ("มะอ์ญูจ", "มะอฺญูจ"),
    ("กะอ์บ์", "กะอฺบฺ"),
    ("อัรร่อบีอ์", "อัรร่อบีอฺ"),
    ("ยูชะฮ์", "ยูชะอฺ"),
    ("วัดด์", "วัดดฺ"),
    ("สุวาอ์", "สุวาอฺ"),
    ("นัซร์", "นัซรฺ"),
    ("เฮาวาอ์", "เฮาวาอฺ"),

    # 3. Islamic Concepts, Eschatology, Worship & Locations
    ("วะฮีย์", "วะฮียฺ"),
    ("วะฮีห์", "วะฮียฺ"),
    ("มุอ์มินะฮ์", "มุอฺมินะฮฺ"),
    ("มุอ์มิน", "มุอฺมิน"),
    ("ละอ์นัต", "ละอฺนัต"),
    ("ชัยตอน", "ชัยฏอน"),
    ("กิยามะฮ์", "กิยามะฮฺ"),
    ("กิยามะห์", "กิยามะฮฺ"),
    ("กียามะฮ์", "กิยามะฮฺ"),
    ("วันกิยามะฮ ", "วันกิยามะฮฺ "),
    ("อาคิเราะฮ์", "อาคิเราะฮฺ"),
    ("อาคิเราะห์", "อาคิเราะฮฺ"),
    ("อาคีเราะห์", "อาคีเราะฮฺ"),
    ("อิบาดะฮ์", "อิบาดะฮฺ"),
    ("อิบาดะห์", "อิบาดะฮฺ"),
    ("ฮิดายะฮ์", "ฮิดายะฮฺ"),
    ("ชะฟาอะฮ์", "ชะฟาอะฮฺ"),
    ("เตาบะฮ์", "เตาบะฮฺ"),
    ("ฟิตนะฮ์", "ฟิตนะฮฺ"),
    ("ฟิตนะห์", "ฟิตนะฮฺ"),
    ("ซุนนะฮ์", "ซุนนะฮฺ"),
    ("ซุนนะห์", "ซุนนะฮฺ"),
    ("อะมานะฮ์", "อะมานะฮฺ"),
    ("เศาะฮาบะฮ์", "เศาะฮาบะฮฺ"),
    ("หิกมะฮ์", "หิกมะฮฺ"),
    ("ฮิกมะฮ์", "หิกมะฮฺ"),
    ("ฮิกมะฮฺ", "หิกมะฮฺ"),
    ("ฮิกมะฮ ", "หิกมะฮฺ "),
    ("นิอ์มะฮ์", "นิอฺมะฮฺ"),
    ("นิอ์มะฮฺ", "นิอฺมะฮฺ"),
    ("อุมเราะฮ์", "อุมเราะฮฺ"),
    ("ดียะฮ์", "ดียะฮฺ"),
    ("กิบละฮ์", "กิบละฮฺ"),
    ("มัรวะฮ์", "มัรวะฮฺ"),
    ("บัยอะฮ์", "บัยอะฮฺ"),
    ("กะลาละฮ์", "กะลาละฮฺ"),
    ("ญานาซะฮ์", "ญะนาซะฮฺ"),
    ("อัลญาฮิลียะฮ์", "อัลญาฮิลียะฮฺ"),
    ("ญาฮิลียะฮ์", "ญาฮิลียะฮฺ"),
    ("กะอ์บะฮ์", "กะอฺบะฮฺ"),
    ("กะอ์บะฮฺ", "กะอฺบะฮฺ"),
    ("บัยตุลมะอ์มูร", "บัยตุลมะอฺมูร"),
    ("ชะฮาดะฮ์", "ชะฮาดะฮฺ"),
    ("ซะกาฮ์", "ซะกาฮฺ"),
    ("เตารอฮ์", "เตารอฮฺ"),
    ("ซะบูร์", "ซะบูรฺ"),
    ("อะฮ์ลุลกิตาบ", "อะฮฺลุลกิตาบ"),
    ("อัลเลาฮุลมะฮฟูซ", "อัลเลาฮุลมะฮฺฟูซ"),
    ("ลูห์มะห์ฟูซ", "ลูหฺมะฮฺฟูซ"),
    ("ลูห์มะฮฺฟูซ", "ลูหฺมะฮฺฟูซ"),
    ("มะฮฟูซ", "มะฮฺฟูซ"),
    ("มะห์ฟูซ", "มะฮฺฟูซ"),
    ("มะห์ชัร", "มะฮฺชัร"),
    ("ตัสบีห์", "ตัสบีหฺ"),
    ("นิกาห์", "นิกาหฺ"),
    ("มะฮัร์", "มะฮัรฺ"),
    ("กุรูอ์", "กุรูอฺ"),
    ("กุรุฮ์", "กุรุฮฺ"),
    ("อีลาอ์", "อีลาอฺ"),
    ("ศุบห์", "ศุบหฺ"),
    ("อิชาอ์", "อิชาอฺ"),
    ("มิห์รอบ", "มิหฺรอบ"),
    ("รุกัวะอ์", "รุกัวอฺ"),
    ("รุกัวะว์", "รุกัวอฺ"),
    ("รุกูอ์", "รุกูอฺ"),
    ("เอี๊ยะห์รอม", "อิหฺรอม"),
    ("อี๊ยะห์รอม", "อิหฺรอม"),
    ("อิห์รอม", "อิหฺรอม"),
    ("รอกะอะฮ์", "ร็อกอะฮฺ"),
    ("ซูเราะฮ์", "ซูเราะฮฺ"),
    ("ซูเราะห์", "ซูเราะฮฺ"),
    ("ซูเราะอ์", "ซูเราะฮฺ"),
    ("อายะฮ์", "อายะฮฺ"),
    ("อายะห์", "อายะฮฺ"),
    ("อายะอ์", "อายะฮฺ"),
    ("มักกะฮ์", "มักกะฮฺ"),
    ("มักกะห์", "มักกะฮฺ"),
    ("มักกฮ์", "มักกะฮฺ"),
    ("มะดีนะฮ์", "มะดีนะฮฺ"),
    ("มะดีนะห์", "มะดีนะฮฺ"),
    ("มาดีนะฮ์", "มะดีนะฮฺ"),
    ("ฮุดัยบียะฮ์", "ฮุดัยบิยะฮฺ"),
    ("ฮุดัยบียะฮฺ", "ฮุดัยบิยะฮฺ"),
    ("อันฏอกียะฮ์", "อันฏอกียะฮฺ"),
    ("อัลบะเกาะเราะฮ์", "อัลบะเกาะเราะฮฺ"),
    ("อัลบะกอเราะฮ์", "อัลบะเกาะเราะฮฺ"),
    ("อัลฟาติฮะฮ์", "อัลฟาติฮะฮฺ"),
    ("อัลเกาะรีอะฮ์", "อัลกอริอะฮฺ"),
    ("อัลกอรีอะฮ์", "อัลกอริอะฮฺ"),
    ("อัลกอรีอะฮฺ", "อัลกอริอะฮฺ"),
    ("อัลฮุเฏามะฮ์", "อัลฮุเฏาะมะฮฺ"),
    ("อัล-กะฮ์ฟ", "อัล-กะฮฺฟ"),
    ("อัส-สัจญ์ดะฮ์", "อัส-สัจญ์ดะฮฺ"),
    ("อัฏฏูร์", "อัฏฏูรฺ"),
    ("อัลฮิจร์", "อัลฮิจรฺ"),
    ("อัลก็อดร์", "อัลก็อดรฺ"),
    ("ฟิรเดาส์", "ฟิรเดาสฺ"),
    ("อัชเชียะอ์รอ", "อัชเชียะอฺรอ"),
    ("อัลมุอ์ตะฟิกะฮ์", "อัลมุอฺตะฟิกะฮฺ"),
    ("มุอ์ตะฟิกาต", "มุอฺตะฟิกาต"),
    ("อัล-มุตะฟิกาต", "อัลมุตะฟิกาต"),
    ("อัยน์", "อัยนฺ"),
]

REGEX_REPLACEMENTS = [
    # Ensure any bare อัลลอฮ / ฟิรเอาน / มลาอิกะฮ without Phinthu or Karan gets Phinthu
    (re.compile(r"อัลลอฮ(?![\u0E3A\u0E4C])"), "อัลลอฮฺ", "BARE_ALLAH_PHINTHU"),
    (re.compile(r"ฟิรเอาน(?![\u0E3A\u0E4C])"), "ฟิรเอานฺ", "BARE_FIRAWN_PHINTHU"),
    (re.compile(r"มลาอิกะฮ(?![\u0E3A\u0E4C])"), "มลาอิกะฮฺ", "BARE_MALAIKAH_PHINTHU"),
    # Residual Arabic Tā' marbūṭah in waqf (ะฮ์ / ะห์ -> ะฮฺ), protecting native Thai เคราะห์
    (re.compile(r"ะฮ์"), "ะฮฺ", "RESIDUAL_TA_MARBUTAH_HO_NOKHUK"),
    (re.compile(r"(?<!เครา)ะห์"), "ะฮฺ", "RESIDUAL_TA_MARBUTAH_HO_HIP"),
    # Accidental double Phinthu cleanup if any
    (re.compile(r"\u0E3A{2,}"), "\u0E3A", "DEDUP_PHINTHU"),
]


def standardize_text(text: str, key: str, context: str, log_rows: list) -> str:
    if not text:
        return ""
    for old, new in CANONICAL_REPLACEMENTS:
        if old in text:
            cnt = text.count(old)
            text = text.replace(old, new)
            log_rows.append({
                "ayah_key": key,
                "context": context,
                "rule_type": "CANONICAL_MATRIX",
                "before": old,
                "after": new,
                "occurrences": cnt,
            })
    for pat, repl, rule_name in REGEX_REPLACEMENTS:
        matches = pat.findall(text)
        if matches:
            text = pat.sub(repl, text)
            log_rows.append({
                "ayah_key": key,
                "context": context,
                "rule_type": rule_name,
                "before": matches[0],
                "after": repl,
                "occurrences": len(matches),
            })
    return text


def main():
    print("=== Phase 4: Transliteration & Quranic Phinthu Standardization ===")
    with open(IN_PHASE3_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    log_rows = []
    ayahs_changed = 0
    fns_changed = 0
    surah_names_changed = 0

    for rec in records:
        k = rec["ayah_key"]

        # 1. Surah Name (Thai)
        sn_orig = rec.get("surah_name_th", "")
        sn_new = standardize_text(sn_orig, k, "surah_name_th", [])
        if sn_new != sn_orig:
            surah_names_changed += 1
        rec["surah_name_th"] = sn_new

        # 2. Ayah Translation (Tokenized & Clean)
        t_orig = rec["translation_tokenized"]
        t_new = standardize_text(t_orig, k, "ayah", log_rows)
        assert re.findall(r"⟦FN:(\d+)⟧", t_orig) == re.findall(r"⟦FN:(\d+)⟧", t_new), f"FN token mismatch in {k}"
        if t_new != t_orig:
            ayahs_changed += 1
        rec["translation_tokenized"] = t_new
        t_clean = re.sub(r"\s*⟦FN:\d+⟧\s*", " ", t_new)
        rec["translation"] = re.sub(r"[ \t]{2,}", " ", t_clean).strip()

        # 3. Footnotes
        for fn in rec.get("footnotes", []):
            ft_orig = fn["text"]
            ft_new = standardize_text(ft_orig, k, f"footnote_{fn['id']}", log_rows)
            if ft_new != ft_orig:
                fns_changed += 1
            fn["text"] = ft_new

    with open(OUT_PHASE4_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    with open(OUT_PHASE4_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["ayah_key", "context", "rule_type", "before", "after", "occurrences"],
        )
        writer.writeheader()
        writer.writerows(log_rows)

    total_replacements = sum(r["occurrences"] for r in log_rows)
    print(f"Standardized transliteration & Phinthu across {ayahs_changed:,} Ayahs and {fns_changed:,} Footnotes.")
    print(f"Total replacement instances: {total_replacements:,} ({len(log_rows):,} rule hits) -> {OUT_PHASE4_CSV.name}")
    print(f"Saved Phase 4 dataset -> {OUT_PHASE4_JSON.name}")


if __name__ == "__main__":
    main()
