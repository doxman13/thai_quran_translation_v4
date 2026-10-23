#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_errata_catalog.py
Generates the comprehensive, public-facing Transparency & Errata Catalog
(บันทึกประวัติการแก้ไขข้อผิดพลาดเพื่อความโปร่งใสทางวิชาการ).

Consolidates:
  1. Manual audit fixes verified via Gemini & scholarly review (data/v3_manual_audit_fixes.json)
  2. Baseline clerical pre-patches (scripts/build_v3_synthesis_base.py)

Outputs:
  - thai_quran_translation_v4/deliverables/v3_transparency_errata_catalog.json
  - thai_quran_translation_v4/deliverables/v3_transparency_errata_catalog.md
  - thai-quran-web/src/data/transparency_errata_catalog.json (for live website transparency page)

Usage:
  python scripts/generate_errata_catalog.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = REPO_ROOT.parent

MANUAL_FIXES_JSON = REPO_ROOT / "data" / "v3_manual_audit_fixes.json"
BASE_BUILDER_PY = REPO_ROOT / "scripts" / "build_v3_synthesis_base.py"

OUT_DIR = REPO_ROOT / "deliverables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_JSON = OUT_DIR / "v3_transparency_errata_catalog.json"
OUT_MD = OUT_DIR / "v3_transparency_errata_catalog.md"

WEB_CATALOG_JSON = PARENT_ROOT / "thai-quran-web" / "src" / "data" / "transparency_errata_catalog.json"


def parse_key(k: str) -> tuple[int, int]:
    s, a = k.split(":")
    return int(s), int(a)


def extract_base_patches() -> list[dict]:
    """Extracts clerical patches from build_v3_synthesis_base.py."""
    if not BASE_BUILDER_PY.exists():
        return []
    with open(BASE_BUILDER_PY, "r", encoding="utf-8") as f:
        code = f.read()

    m = re.search(r"CLERICAL_PRE_PATCHES\s*=\s*\[(.*?)\]\n\n", code, re.DOTALL)
    if not m:
        return []

    try:
        raw_list = eval("[" + m.group(1) + "]")
        res = []
        for p in raw_list:
            res.append({
                "ayah": p.get("ayah", ""),
                "type": "CLERICAL_OMISSION" if "Restore" in p.get("reason", "") else "OCR_TYPO",
                "target": p.get("target", ""),
                "replacement": p.get("replacement", ""),
                "reason": p.get("reason", ""),
                "source": "Layer 0 Pre-Patcher (Baseline Scan)"
            })
        return res
    except Exception as e:
        print(f"[WARN] Could not parse base patches: {e}")
        return []


def main():
    manual_fixes = []
    if MANUAL_FIXES_JSON.exists():
        with open(MANUAL_FIXES_JSON, "r", encoding="utf-8") as f:
            manual_fixes = json.load(f)

    base_patches = extract_base_patches()

    # Deduplicate and combine by (ayah, target, replacement)
    seen = set()
    combined = []

    for f in manual_fixes:
        key = (f["ayah"], f["target"].strip(), f["replacement"].strip())
        if key not in seen:
            seen.add(key)
            combined.append({
                "ayah": f["ayah"],
                "type": f.get("type", "SCHOLAR_FIX"),
                "target": f["target"],
                "replacement": f["replacement"],
                "reason": f.get("reason", ""),
                "source": "Scholarly LLM Audit (Gemini + Uthmani Cross-Check)",
                "timestamp": f.get("timestamp", "")
            })

    for bp in base_patches:
        key = (bp["ayah"], bp["target"].strip(), bp["replacement"].strip())
        if key not in seen:
            seen.add(key)
            combined.append(bp)

    # Sort numerically by Surah:Ayah
    combined.sort(key=lambda x: parse_key(x["ayah"]))

    # Save to JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"[OK] Exported {len(combined)} errata entries -> {OUT_JSON}")

    # Mirror to Web if web repo exists
    if WEB_CATALOG_JSON.parent.exists():
        with open(WEB_CATALOG_JSON, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        print(f"[OK] Synced transparency catalog to Web -> {WEB_CATALOG_JSON}")

    # Generate Human-Readable Markdown Report
    categories = {
        "THEOLOGICAL": "1. การแก้ไขสรรพนามและหลักเตาฮีด (Theological Purity & Divine Pronouns)",
        "OMISSION": "2. การกู้คืนตัวบทภาษาอาหรับที่ตกหล่น (Restoration of Dropped Arabic Clauses)",
        "CLERICAL_OMISSION": "2. การกู้คืนตัวบทภาษาอาหรับที่ตกหล่น (Restoration of Dropped Arabic Clauses)",
        "TYPO": "3. การแก้ไขข้อผิดพลาดจากการสแกน OCR และคำสะกดผิด (Severe OCR Misreads & Typo Fixes)",
        "OCR_TYPO": "3. การแก้ไขข้อผิดพลาดจากการสแกน OCR และคำสะกดผิด (Severe OCR Misreads & Typo Fixes)",
        "FN_PLACEMENT": "4. การจัดตำแหน่งเชิงอรรถที่ตัดกลางคำ (Footnote Placement & Word Repair)",
        "SPACING": "5. การปรับปรุงจังหวะการอ่านและการเว้นวรรค (Cadence & Natural Spacing)"
    }

    by_cat = {}
    for item in combined:
        cat_key = item.get("type", "TYPO")
        cat_title = categories.get(cat_key, "6. การแก้ไขอื่น ๆ (Other Scholarly Corrections)")
        by_cat.setdefault(cat_title, []).append(item)

    md = []
    md.append("# บันทึกรายงานการตรวจทานและแก้ไขข้อผิดพลาดเพื่อความโปร่งใสทางวิชาการ")
    md.append("## (Thai Quran Master V3 Synthesis: Errata & Transparency Report)")
    md.append("")
    md.append(f"> **สถิติรวม:** ตรวจพบและแก้ไขข้อผิดพลาดที่ตกค้างในระบบดิจิทัล/ฉบับพิมพ์เดิมแล้วทั้งสิ้น **{len(combined)} รายการ**")
    md.append(f"> **วันที่จัดทำรายงาน:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    md.append("> **วัตถุประสงค์:** เพื่อเผยแพร่แก่สาธารณชน นักวิชาการ และผู้ใช้งานทั่วไป ให้ทราบถึงที่มาและเหตุผลของการแก้ไขตัวบทแปลอัลกุรอานภาษาไทย โดยเทียบเคียงกับตัวบทภาษาอาหรับอุษมานีย์เป็นมาตรฐานสูงสุด")
    md.append("")
    md.append("---")
    md.append("")

    for title in sorted(by_cat.keys()):
        items = by_cat[title]
        md.append(f"## {title} ({len(items)} รายการ)")
        md.append("")
        md.append("| ลำดับ | อายะฮฺ | ข้อความเดิมที่มีข้อบกพร่อง (พบในฉบับพิมพ์/เว็บอื่น) | ข้อความที่แก้ไขให้ถูกต้องตามหลักวิชาการ | เหตุผลและตัวบทอ้างอิงภาษาอาหรับ |")
        md.append("| :---: | :---: | :--- | :--- | :--- |")
        for idx, it in enumerate(items, 1):
            ak = it["ayah"]
            tgt = it["target"].replace("|", "\\|").replace("\n", " ")
            rep = it["replacement"].replace("|", "\\|").replace("\n", " ")
            rsn = it["reason"].replace("|", "\\|").replace("\n", " ")
            md.append(f"| {idx} | **{ak}** | `{tgt}` | **{rep}** | {rsn} |")
        md.append("")
        md.append("---")
        md.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"[OK] Generated Human-Readable Report -> {OUT_MD}")


if __name__ == "__main__":
    main()
