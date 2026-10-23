#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/extract_chunk_pdf.py
Extracts the exact printed King Fahd Quran pages for any audit chunk.

Slices /Users/admin/Documents/th_Holy_Quran_and_the_translation_of_the_Meaning_of_the_Thai_language.pdf
into a lightweight, standalone PDF (5-10 pages, ~150 KB) corresponding to the chunk's verses.

Use cases:
  1. Drag & drop the sliced PDF directly into Gemini (Multimodal Verification).
  2. Instant 1-click desktop review in macOS Preview (no physical book flipping).
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    print("Error: pymupdf not installed. Run: python3 -m pip install --user pymupdf")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = Path("/Users/admin/Documents/th_Holy_Quran_and_the_translation_of_the_Meaning_of_the_Thai_language.pdf")
TRACKER_PATH = REPO_ROOT / "v3_audit_tracker.tsv"
V3_BASE_PATH = REPO_ROOT / "data" / "01_v3_base_master.json"
OUT_DIR = REPO_ROOT / "audit_chunks" / "printed_pdf"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_surah_page_map(doc):
    toc = doc.get_toc()
    surah_pages = {}
    for level, title, page in toc:
        if title.isdigit():
            surah_pages[int(title)] = page  # 1-based page in PDF
    # Add page for index/end
    surah_pages[115] = 1783
    return surah_pages


def main():
    parser = argparse.ArgumentParser(description="Extract printed PDF pages for a chunk.")
    parser.add_argument("--chunk", type=int, required=True, help="Chunk ID (1-127)")
    args = parser.parse_args()

    if not PDF_PATH.exists():
        print(f"Error: PDF not found at {PDF_PATH}")
        sys.exit(1)

    # 1. Read chunk info from tracker
    chunk_range = None
    with open(TRACKER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 4 and parts[0].isdigit() and int(parts[0]) == args.chunk:
                chunk_range = parts[3]
                break

    if not chunk_range:
        print(f"Error: Chunk {args.chunk} not found in tracker.")
        sys.exit(1)

    start_str, end_str = chunk_range.split("-")
    s_surah, s_ayah = map(int, start_str.split(":"))
    e_surah, e_ayah = map(int, end_str.split(":"))

    # 2. Load total ayah counts per surah
    with open(V3_BASE_PATH, "r", encoding="utf-8") as f:
        v3_list = json.load(f)

    surah_max_ayah = {}
    for r in v3_list:
        s, a = r["surah"], r["ayah"]
        surah_max_ayah[s] = max(surah_max_ayah.get(s, 0), a)

    # 3. Open PDF and calculate page range
    doc = fitz.open(PDF_PATH)
    surah_pages = get_surah_page_map(doc)

    start_surah_page = surah_pages[s_surah]
    next_surah_page = surah_pages[s_surah + 1]
    surah_page_span = next_surah_page - start_surah_page

    # Interpolate estimated page range with safety margin of +/- 1 page
    start_ratio = (s_ayah - 1) / surah_max_ayah[s_surah]
    if s_surah == e_surah:
        end_ratio = e_ayah / surah_max_ayah[s_surah]
        calc_start_page = int(start_surah_page + (start_ratio * surah_page_span)) - 1
        calc_end_page = int(start_surah_page + (end_ratio * surah_page_span)) + 1
    else:
        # Crosses surah boundary
        end_surah_page = surah_pages[e_surah]
        next_after_end = surah_pages[e_surah + 1]
        end_span = next_after_end - end_surah_page
        end_ratio = e_ayah / surah_max_ayah[e_surah]

        calc_start_page = int(start_surah_page + (start_ratio * surah_page_span)) - 1
        calc_end_page = int(end_surah_page + (end_ratio * end_span)) + 1

    # Clamp bounds (0-based for fitz)
    calc_start_page = max(0, calc_start_page - 1)
    calc_end_page = min(len(doc) - 1, calc_end_page)

    # 4. Extract pages into new PDF
    out_doc = fitz.open()
    for p in range(calc_start_page, calc_end_page + 1):
        out_doc.insert_pdf(doc, from_page=p, to_page=p)

    out_file = OUT_DIR / f"chunk_{args.chunk:02d}_{s_surah}_{s_ayah}_to_{e_surah}_{e_ayah}_printed_ref.pdf"
    out_doc.save(out_file)
    size_kb = out_file.stat().st_size / 1024

    print(f"=== EXTRACTED PRINTED KING FAHD PAGES FOR CHUNK {args.chunk} ===")
    print(f"Verses Range: {chunk_range}")
    print(f"PDF Pages:    Page {calc_start_page + 1} to Page {calc_end_page + 1} ({len(out_doc)} pages)")
    print(f"File Saved:   {out_file}")
    print(f"File Size:    {size_kb:.1f} KB")
    print(f"\n[HOW TO USE]")
    print(f"1. In Gemini Web Chat: Attach this PDF file directly to your prompt!")
    print(f"   Gemini's Vision AI will read the exact printed Arabic & Thai pages automatically.")
    print(f"2. On your Mac: Double-click to open in Preview right beside your screen.")


if __name__ == "__main__":
    main()
