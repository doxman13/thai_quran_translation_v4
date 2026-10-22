#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5: Comparative Upgrade Cataloging & 3-Way Diff Generation
Compares Standardized ThaiQuran v4 against Production thai_v3, Thai 1 (ID 51), and Thai 2 (ID 230).
Outputs:
  - data/05_tq_upgrades_cataloged.json
  - reports/phase5_upgraded_sentences.csv
  - reports/thai_v4_vs_v3_full_diff.html
"""

from __future__ import annotations

import csv
import difflib
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = REPO_ROOT.parent
AUDIT_DIR = PARENT_ROOT / "thai_quran_scholar_audit_v4"

IN_PHASE6_JSON = REPO_ROOT / "data" / "06_tq_spacing_and_scholar_fixed.json"
IN_PHASE4_JSON = IN_PHASE6_JSON if IN_PHASE6_JSON.exists() else (REPO_ROOT / "data" / "04_tq_standardized.json")
IN_PHASE2_CSV = REPO_ROOT / "reports" / "phase2_omissions_restored_log.csv"
V3_MASTER_JSON = AUDIT_DIR / "final_files" / "01_thai_quran_translation_v3_master.json"
THAI1_JSON = AUDIT_DIR / "quran_foundation_thai_id51.json"
THAI2_JSON = AUDIT_DIR / "quran_foundation_thai_id230.json"

OUT_PHASE5_JSON = REPO_ROOT / "data" / "05_tq_upgrades_cataloged.json"
OUT_PHASE5_CSV = REPO_ROOT / "reports" / "phase5_upgraded_sentences.csv"
OUT_HTML_DIFF = REPO_ROOT / "reports" / "thai_v4_vs_v3_full_diff.html"

THEOLOGICAL_TERMS = (
    "พระผู้อภิบาล",
    "พระผู้เป็นเจ้า",
    "พระเจ้าของ",
    "บรรดามลาอิกะฮฺ",
    "ผู้ทรงปรีชาญาณ",
    "ผู้ทรงเกรียงไกร",
    "ผู้ทรงอานุภาพ",
    "ผู้ทรงเดชานุภาพ",
    "ผู้ทรงเอกะ",
    "วันปรโลก",
    "เคารพภักดี",
    "เคารพสักการะ",
    "เคารพอิบาดะฮฺ",
)

GUIDANCE_TERMS = (
    "ทางนำ",
    "การชี้แนะ",
    "คำแนะนำ",
    "โองการ",
    "อายะฮฺ",
    "อายาต",
    "สัญญาณ",
    "เครื่องหมาย",
    "ข้อตักเตือน",
)


def strip_ws_punct(text: str) -> str:
    return re.sub(r'[\s"“”‘’?!.,\-]', "", text)


def clean_qf_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^\s*\[\d+\]\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def make_inline_diff_html(v3_text: str, v4_text: str) -> tuple[str, str]:
    sm = difflib.SequenceMatcher(None, v3_text, v4_text)
    v3_parts = []
    v4_parts = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        s3 = html.escape(v3_text[i1:i2])
        s4 = html.escape(v4_text[j1:j2])
        if tag == "equal":
            v3_parts.append(s3)
            v4_parts.append(s4)
        elif tag == "delete":
            v3_parts.append(f'<del class="diff-del">{s3}</del>')
        elif tag == "insert":
            v4_parts.append(f'<ins class="diff-ins">{s4}</ins>')
        elif tag == "replace":
            v3_parts.append(f'<del class="diff-del">{s3}</del>')
            v4_parts.append(f'<ins class="diff-ins">{s4}</ins>')
    return "".join(v3_parts), "".join(v4_parts)


def summarize_diff_snippets(v3_text: str, v4_text: str, max_pairs: int = 4) -> str:
    sm = difflib.SequenceMatcher(None, v3_text, v4_text)
    snippets = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        s3 = v3_text[i1:i2].strip()
        s4 = v4_text[j1:j2].strip()
        if not s3 and not s4:
            continue
        snippets.append(f"'{s3}' -> '{s4}'")
        if len(snippets) >= max_pairs:
            break
    return "; ".join(snippets)


def main():
    print("=== Phase 5: Comparative Upgrade Cataloging & 3-Way Diff Generation ===")
    with open(IN_PHASE4_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    with open(V3_MASTER_JSON, "r", encoding="utf-8") as f:
        v3_map = {f"{r['surah']}:{r['ayah']}": r["translation"] for r in json.load(f)}

    with open(THAI1_JSON, "r", encoding="utf-8") as f:
        thai1_list = [clean_qf_text(x.get("text", "")) for x in json.load(f)]

    with open(THAI2_JSON, "r", encoding="utf-8") as f:
        thai2_list = [clean_qf_text(x.get("text", "")) for x in json.load(f)]

    restored_keys = set()
    reverse_repair_keys = set()
    with open(IN_PHASE2_CSV, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ak = row["ayah_key"]
            if row["repair_direction"] == "RESTORED_FROM_ARABIC_AND_V3_INTO_V4":
                restored_keys.add(ak)
            else:
                reverse_repair_keys.add(ak)

    category_counts = Counter()
    csv_rows = []
    html_cards = []

    for idx, rec in enumerate(records):
        ak = rec["ayah_key"]
        v4_clean = rec["translation"]
        v3_text = v3_map[ak]
        t1_text = thai1_list[idx] if idx < len(thai1_list) else ""
        t2_text = thai2_list[idx] if idx < len(thai2_list) else ""

        v4_ns = strip_ws_punct(v4_clean)
        v3_ns = strip_ws_punct(v3_text)
        char_sim = round(difflib.SequenceMatcher(None, v3_ns, v4_ns).ratio(), 4)

        if ak in restored_keys:
            cat = "CLAUSE_OMISSION_RESTORED"
        elif ak in reverse_repair_keys:
            cat = "REVERSE_REPAIR_OVER_V3"
        elif v4_clean == v3_text:
            cat = "IDENTICAL_TO_V3"
        elif v4_ns == v3_ns:
            cat = "SPACING_AND_PUNCTUATION_ONLY"
        else:
            diff_summary = summarize_diff_snippets(v3_text, v4_clean, max_pairs=8)
            if any(term in diff_summary for term in THEOLOGICAL_TERMS) or (
                ("พระผู้อภิบาล" in v4_clean) != ("พระผู้อภิบาล" in v3_text)
            ):
                cat = "THEOLOGICAL_VOCABULARY_UPGRADE"
            elif any(term in diff_summary for term in GUIDANCE_TERMS):
                cat = "GUIDANCE_TERMINOLOGY_UPGRADE"
            else:
                cat = "PROSE_SENTENCE_UPGRADE"

        category_counts[cat] += 1
        rec["v3_translation"] = v3_text
        rec["v4_vs_v3_category"] = cat
        rec["v4_vs_v3_char_similarity"] = char_sim

        if cat not in ("IDENTICAL_TO_V3", "SPACING_AND_PUNCTUATION_ONLY"):
            diff_snip = summarize_diff_snippets(v3_text, v4_clean, max_pairs=5)
            csv_rows.append({
                "ayah_key": ak,
                "surah": rec["surah"],
                "ayah": rec["ayah"],
                "category": cat,
                "char_similarity": char_sim,
                "footnote_count": len(rec.get("footnotes", [])),
                "diff_highlights": diff_snip,
                "v3_translation": v3_text,
                "v4_translation_clean": v4_clean,
                "thai1_id51": t1_text,
                "thai2_id230": t2_text,
            })

            v3_html, v4_html = make_inline_diff_html(v3_text, v4_clean)
            fn_items = "".join(
                f'<li><strong>[{fn["seq"]}] (orig #{fn["id"]}):</strong> {html.escape(fn["text"])}</li>'
                for fn in rec.get("footnotes", [])
            )
            fn_block = (
                f'<details class="fn-details"><summary>{len(rec.get("footnotes", []))} Footnote(s)</summary><ul>{fn_items}</ul></details>'
                if fn_items
                else '<span class="no-fn">0 Footnotes</span>'
            )
            html_cards.append(
                f'<tr class="diff-row" data-cat="{cat}" data-key="{ak}">'
                f'<td class="col-key"><strong>{ak}</strong><br><span class="badge badge-{cat}">{cat}</span><br><small>Sim: {char_sim:.1%}</small><br>{fn_block}</td>'
                f'<td class="col-v3">{v3_html}</td>'
                f'<td class="col-v4">{v4_html}</td>'
                f"</tr>"
            )

    with open(OUT_PHASE5_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    with open(OUT_PHASE5_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ayah_key",
                "surah",
                "ayah",
                "category",
                "char_similarity",
                "footnote_count",
                "diff_highlights",
                "v3_translation",
                "v4_translation_clean",
                "thai1_id51",
                "thai2_id230",
            ],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    html_doc = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>Thai Quran Translation v4 vs Production v3 — Full Comparative Audit</title>
<style>
  body {{ font-family: 'Sarabun', 'Noto Sans Thai', system-ui, sans-serif; margin: 0; padding: 24px; background: #f8fafc; color: #0f172a; line-height: 1.65; }}
  h1 {{ margin-top: 0; font-size: 24px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .kpi-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
  .kpi-num {{ font-size: 22px; font-weight: 700; color: #0284c7; }}
  .kpi-label {{ font-size: 12px; color: #475569; text-transform: uppercase; }}
  .controls {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; align-items: center; background: #fff; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 10; }}
  .controls input {{ padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; min-width: 260px; font-size: 14px; }}
  .filter-btn {{ padding: 6px 12px; border-radius: 6px; border: 1px solid #cbd5e1; background: #f1f5f9; cursor: pointer; font-size: 13px; }}
  .filter-btn.active {{ background: #0f172a; color: #fff; border-color: #0f172a; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }}
  th, td {{ padding: 12px 14px; border-bottom: 1px solid #e2e8f0; vertical-align: top; text-align: left; font-size: 15px; }}
  th {{ background: #f1f5f9; font-weight: 600; font-size: 13px; text-transform: uppercase; color: #334155; }}
  .col-key {{ width: 210px; font-size: 13px; background: #fcfcfd; }}
  .col-v3, .col-v4 {{ width: 39.5%; }}
  del.diff-del {{ background: #fee2e2; color: #991b1b; text-decoration: line-through; padding: 0 2px; border-radius: 3px; }}
  ins.diff-ins {{ background: #dcfce7; color: #166534; text-decoration: none; font-weight: 600; padding: 0 2px; border-radius: 3px; }}
  .badge {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; margin: 4px 0; }}
  .badge-CLAUSE_OMISSION_RESTORED {{ background: #fef3c7; color: #92400e; }}
  .badge-REVERSE_REPAIR_OVER_V3 {{ background: #dbeafe; color: #1e40af; }}
  .badge-THEOLOGICAL_VOCABULARY_UPGRADE {{ background: #f3e8ff; color: #6b21a8; }}
  .badge-GUIDANCE_TERMINOLOGY_UPGRADE {{ background: #e0f2fe; color: #075985; }}
  .badge-PROSE_SENTENCE_UPGRADE {{ background: #f1f5f9; color: #334155; }}
  .fn-details summary {{ cursor: pointer; color: #0284c7; font-weight: 600; margin-top: 4px; }}
  .fn-details ul {{ margin: 6px 0 0 0; padding-left: 16px; font-size: 12.5px; color: #334155; }}
  .no-fn {{ color: #94a3b8; font-size: 12px; }}
</style>
</head>
<body>
<h1>Thai Quran Translation v4 vs Production v3 — Comparative Upgrade Report</h1>
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-num">6,236</div><div class="kpi-label">Total Quran Verses</div></div>
  <div class="kpi-card"><div class="kpi-num">{category_counts['CLAUSE_OMISSION_RESTORED']:,}</div><div class="kpi-label">Omissions Restored</div></div>
  <div class="kpi-card"><div class="kpi-num">{category_counts['REVERSE_REPAIR_OVER_V3']:,}</div><div class="kpi-label">Reverse Repairs Over v3</div></div>
  <div class="kpi-card"><div class="kpi-num">{category_counts['THEOLOGICAL_VOCABULARY_UPGRADE']:,}</div><div class="kpi-label">Theological Vocab Upgrades</div></div>
  <div class="kpi-card"><div class="kpi-num">{category_counts['GUIDANCE_TERMINOLOGY_UPGRADE']:,}</div><div class="kpi-label">Guidance Term Upgrades</div></div>
  <div class="kpi-card"><div class="kpi-num">{category_counts['PROSE_SENTENCE_UPGRADE']:,}</div><div class="kpi-label">Prose Sentence Upgrades</div></div>
  <div class="kpi-card"><div class="kpi-num">{category_counts['SPACING_AND_PUNCTUATION_ONLY']:,}</div><div class="kpi-label">Spacing/Punct Only</div></div>
  <div class="kpi-card"><div class="kpi-num">{category_counts['IDENTICAL_TO_V3']:,}</div><div class="kpi-label">Byte-Identical to v3</div></div>
</div>
<div class="controls">
  <input type="text" id="searchBox" placeholder="Search Surah:Ayah (e.g. 22:62) or Thai text..." oninput="filterRows()">
  <button class="filter-btn active" onclick="setCat('ALL', this)">All Substantive Diffs ({len(csv_rows):,})</button>
  <button class="filter-btn" onclick="setCat('CLAUSE_OMISSION_RESTORED', this)">Omissions Restored ({category_counts['CLAUSE_OMISSION_RESTORED']})</button>
  <button class="filter-btn" onclick="setCat('REVERSE_REPAIR_OVER_V3', this)">Reverse Repairs ({category_counts['REVERSE_REPAIR_OVER_V3']})</button>
  <button class="filter-btn" onclick="setCat('THEOLOGICAL_VOCABULARY_UPGRADE', this)">Theological Upgrades ({category_counts['THEOLOGICAL_VOCABULARY_UPGRADE']})</button>
  <button class="filter-btn" onclick="setCat('GUIDANCE_TERMINOLOGY_UPGRADE', this)">Guidance Upgrades ({category_counts['GUIDANCE_TERMINOLOGY_UPGRADE']})</button>
  <button class="filter-btn" onclick="setCat('PROSE_SENTENCE_UPGRADE', this)">Prose Upgrades ({category_counts['PROSE_SENTENCE_UPGRADE']})</button>
</div>
<table>
  <thead>
    <tr>
      <th>Verse &amp; Category</th>
      <th>Production thai_v3</th>
      <th>Master thai_v4 (Clean)</th>
    </tr>
  </thead>
  <tbody id="diffBody">
    {"".join(html_cards)}
  </tbody>
</table>
<script>
let currentCat = 'ALL';
function setCat(cat, btn) {{
  currentCat = cat;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filterRows();
}}
function filterRows() {{
  const q = document.getElementById('searchBox').value.trim().toLowerCase();
  document.querySelectorAll('.diff-row').forEach(row => {{
    const matchCat = (currentCat === 'ALL') || (row.getAttribute('data-cat') === currentCat);
    const matchQ = !q || row.innerText.toLowerCase().includes(q);
    row.style.display = (matchCat && matchQ) ? '' : 'none';
  }});
}}
</script>
</body>
</html>
"""
    with open(OUT_HTML_DIFF, "w", encoding="utf-8") as f:
        f.write(html_doc)

    print("Category Breakdown across all 6,236 Ayahs:")
    for cat, cnt in category_counts.most_common():
        print(f"  - {cat:32s}: {cnt:,}")
    print(f"Total substantive sentence diffs logged: {len(csv_rows):,} -> {OUT_PHASE5_CSV.name}")
    print(f"Saved interactive HTML diff report -> {OUT_HTML_DIFF.name}")
    print(f"Saved Phase 5 dataset -> {OUT_PHASE5_JSON.name}")


if __name__ == "__main__":
    main()
