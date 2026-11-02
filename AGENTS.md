# Mandatory Quran Data Synchronization Rule

> [!IMPORTANT]
> ## 🚨 Mandatory Master Data Sync: `thai-quran-master-data` as Central Canonical Hub
> **ANYTIME** there is ANY modification, refinement, bug fix, errata restoration, orthographic standardization, or lexical correction made to ANY Quranic dataset in ANY repository or subfolder—including:
> 1. **Full Verse Translations** (`thai_v3.json`, clean translation, annotated translation)
> 2. **Word-by-Word (WBW) Translations & Morphology** (`quran_wbw_th_en_MASTER.json`, `public/data/wbw/*.json`, etc.)
> 3. **Footnotes & Scholarly Annotations** (`thai_footnotes.json`, footnote texts, markers)
> 4. **Ayah Themes & Topics** (`qul_ayah_themes.json`, `topics.json`, `reconciled_thai_quran_themes.json`)
> 5. **Tafsir Al-Mukhtasar** (`tafsirThaiMokhtasar.ts`, `tafsir_thai_mokhtasar.json`)
> 6. **Academic Transparency & Errata Catalog** (`transparency_errata_catalog.json`, CSV, Markdown reports)
>
> ### **MANDATORY MULTI-REPO SYNC PROTOCOL:**
> 1. **Synchronize All Consuming Folders:** Update the modified data synchronously across all dependent repositories:
>    - `thai-quran-web` (`src/data/`, `public/data/`)
>    - `thai_quran_translation_v4` (`deliverables/`)
>    - `wbw-translation-en-th` (`Quran-data/`, root files)
>    - `thai-quran-app` & `hifz-quran-app` (`assets/`, `assets/footnotes/`, `assets/quran_offline.db`)
> 2. **Rebuild Canonical Master Datasets in `thai-quran-master-data`:**
>    - You **MUST** run the automated master compilation pipeline:
>      ```bash
>      cd H:/gits/thai-quran-master-data
>      python scripts/build_master_datasets.py
>      python scripts/verify_master_datasets.py
>      ```
>    - This regenerates all master artifacts:
>      - Unified SQLite: `sqlite/thai_quran_master.db`
>      - Master JSONs: `json/*.json`
>      - Master CSVs: `csv/*.csv`
> 3. **Commit & Push to `thai-quran-master-data` Origin:**
>    - All regenerated master files MUST be immediately committed and pushed to `https://github.com/doxman13/thai-quran-master-data` on branch `main`.
>    - **NO DATA CHANGE IS CONSIDERED FINISHED OR MERGED UNTIL IT HAS BEEN SUCCESSFULLY COMPILED, VERIFIED, AND PUSHED TO `thai-quran-master-data`.**

---

# Master V3 Synthesis Audit — Agent Operational Playbook

> **MANDATORY CONTEXT FOR AI AGENTS:**
> This repository is the source of truth for the **Thai Quran Master V3 Synthesis Audit & Tri-Repository Synchronization Project**.
> All agents working on this codebase must strictly adhere to the operational workflows, safety guardrails, and theological principles defined below.

---

## 1. Project Overview & Tri-Repo Architecture

### Repositories & Working Branches:
1. **`thai_quran_translation_v4`** (Branch: `v3_synthesis_audit`): Core canonical master text (`data/01_v3_base_master.json`), audit fixes history (`data/v3_manual_audit_fixes.json`), progress tracker (`v3_audit_tracker.tsv`), and transparency errata catalog (`deliverables/`).
2. **`thai-quran-web`** (Branch: `feat/thai-v4-translation`): Production Next.js web application consuming `src/data/thai_v3.json`, `src/data/thai_footnotes.json`, and `src/data/transparency_errata_catalog.json`.
3. **`thai-quran-app`** (Branch: `main`): Production Flutter mobile application consuming `assets/thai_v3.json`, `assets/footnotes/thai_footnotes.json`, and `assets/quran_offline.db`.

### Scope:
- **127 Subchunks** spanning all 30 Juz (6,236 verses).
- Progress tracking is recorded in `v3_audit_tracker.tsv`. Always check completed rows (`DONE`) before proceeding.

---

## 2. ⚠️ Critical Safe Git Staging Rule (NEVER VIOLATE)

> [!CAUTION]
> The user is actively developing features (Tilawa Web Worker/speech recognition, Hifz memorization engine/modal/player) inside `thai-quran-web` and `thai-quran-app`.
> **NEVER, UNDER ANY CIRCUMSTANCES, RUN BLANKET `git add .` IN `thai-quran-web` OR `thai-quran-app`!**

### Allowed Git Staging:
- **`thai_quran_translation_v4`:**
  `git add data/01_v3_base_master.json data/v3_manual_audit_fixes.json deliverables/v3_transparency_errata_catalog.json deliverables/v3_transparency_errata_catalog.md v3_audit_tracker.tsv` (or other project files).
- **`thai-quran-web` (ONLY stage translation data):**
  `git add src/data/thai_footnotes.json src/data/thai_v3.json src/data/transparency_errata_catalog.json`
- **`thai-quran-app` (ONLY stage translation assets):**
  `git add assets/footnotes/thai_footnotes.json assets/quran_offline.db assets/thai_v3.json`

---

## 3. The 4-Pillar Truth Architecture

1. **Arabic Uthmani Text (`AR`): Supreme Source of Truth**
   - The original Arabic Quran is the ultimate benchmark.
   - **Supreme Truth Principle:** If an Arabic word/clause was accidentally omitted from the 1990 printed book itself and all historical Thai translations (e.g., 3:59 `عِندَ اللَّهِ`, 5:17 `يَخْلُقُ مَا يَشَاءُ`), restore it immediately and record it in **Category 1** of `deliverables/v3_transparency_errata_catalog.json`.
2. **1990 King Fahd Printed Scan (`300 DPI PDF` in `audit_chunks/printed_pdf/`): Physical Ground Truth Anchor**
   - 127 high-resolution PDF slices (`chunk_01_*.pdf` to `chunk_127_*.pdf`).
   - Every text change, typo fix, and footnote placement **must be visually cross-checked against the actual scanned page**.
3. **Master V3 Base Text (`BASE` in `data/01_v3_base_master.json`):**
   - The clean King Fahd digital base text.
4. **ThaiQuran / Ajarn Asman Meesomboon Reference (`REF / Fixer`):**
   - Reference containing 7,338 scholarly footnotes and historical omission restorations.

---

## 4. The Two-Tier Audit Workflow

Do not blindly apply proposed JSON batches from the user or external AI (Tier 1). The Agent acts as **Tier 2 (Deep Verification & Verification Anchor)**:

```
[Tier 1: User / External AI Proposal]
                  ⬇
[Tier 2: Antigravity Agent Verification]
  1. Inspect the relevant 1990 King Fahd PDF slice using PyMuPDF (fitz):
     - Check proposed fixes against the actual printed lines.
     - Reject hallucinations (e.g. moving footnotes contrary to scan proof).
     - Catch missed OCR defects (e.g. dropped words, mangled particles).
  2. Synthesize verified fixes into a clean JSON array.
  3. Validate with dry run:
     python3 scripts/apply_v3_fixes.py --dry-run --file /tmp/chunkXX_verified.json
  4. Apply live:
     python3 scripts/apply_v3_fixes.py --file /tmp/chunkXX_verified.json
  5. Update tracker in v3_audit_tracker.tsv:
     Change row status from PENDING 0 to DONE <count>
  6. Synchronize tri-repo ecosystem:
     python3 scripts/sync_v3_to_all.py
  7. Commit and push each repository following the Safe Git Staging Rule.
```

### PyMuPDF Quick Snippet:
```python
import fitz
doc = fitz.open('audit_chunks/printed_pdf/chunk_XX_..._printed_ref.pdf')
# Render page to check visually
pix = doc[page_index].get_pixmap(dpi=150)
pix.save('/tmp/check_page.png')
```

---

## 5. Core Translation & Formatting Guardrails

1. **Rule Zero (Strict Minimal Invasive):**
   - Preserve 1990 King Fahd printed phrasing unless there is a genuine omission, OCR defect, or syntactic break.
   - Never alter phrasing based solely on modern stylistic preference or Arabic literalism without scan proof.
2. **Vocabulary Fidelity (Option A):**
   - Classical **"พระเจ้า" / "พระผู้เป็นเจ้า"** must be 100% preserved in running prose. Never modernize to "พระผู้อภิบาล" (the `Rabb` root meaning is supported in the app's Word-by-Word layer).
3. **Canonical Transliteration & Spelling Checklist:**
   - `อินทผลัม` (never อินทผาลัม)
   - `ชัยฏอน` (always ฏ-ปฏัก, never ฎ-ชฎา)
   - `มลาอิกะฮฺ`, `อิบรอฮีม`, `อิสมาอีล`, `อิสฮาก`, `ยะอฺกูบ`, `มูซา`, `อีซา`, `นูฮฺ`, `ซะบูร` (no pinthu).
   - Common typos: `กระนั้นหรือ` (not กระนั่นหรือ), `ดื้อรั้น` (not ดื้อดัน), `ผาสุก` (not ผาสุข), `กัมปนาท` (not กำปนาท), `บิดพลิ้ว` (not บิดพริ้ว), `นัยน์ตา` (not นัยตา), `ศีรษะ` (not ศรีษะ).
4. **Footnote Placement & Spacing:**
   - Tag format: `[FN:N]`.
   - Must affix tightly to the preceding word without spaces (e.g. `คำศัพท์[FN:1]`).
   - Move after maiyamok (e.g. `ต่าง ๆ[FN:1]`).
   - **No Mechanical Spacing After (Thai Continuity):** Thai is written continuously.
     - ❌ **Zero Whitespace for Enclitic Post-Modifiers:** If the word following `[FN:N]` is an attached particle or post-modifier like `ด้วย`, `เอง`, `นี้`, `นั้น`, `อีก`, `ก่อน`, or `เท่านั้น`, it MUST be glued directly to the tag with zero whitespace (e.g. `สวนสวรรค์[FN:1]ด้วย`, `พวกเขา[FN:6]เอง`, `พวกเขา[FN:2]นี้`, `อัลลอฮฺ[FN:2]นั้น`).
     - ✅ Keep/add spaces ONLY for genuine clause boundaries (`และ`, `หรือ`, `แต่`, `ดังนั้น`), relative clauses (`ซึ่ง`, `โดยที่`), dialogues (`“...”`), or breath pauses.
5. **De-Overkill Spacing:**
   - Remove unnatural spaces between words or broken compounds. Thai does not use inter-word spaces.

---

## 6. Project Directory Sitemap

- `audit_chunks/printed_pdf/`: 127 sliced 300 DPI PDF scans (`chunk_01_*.pdf` to `chunk_127_*.pdf`).
- `audit_chunks/subchunks/`: 127 prepared text subchunk files (`juz_XX_partY_*.txt`).
- `data/01_v3_base_master.json`: Canonical Master V3 database (all 6,236 verses).
- `data/v3_manual_audit_fixes.json`: History of all applied manual fixes.
- `deliverables/v3_transparency_errata_catalog.json` & `.md`: Public transparency errata catalog.
- `rules/MASTER_V3_SYNTHESIS_RULES.md`: Human & scholar reference guide.
- `scripts/apply_v3_fixes.py`: Safe patch applier with safety guardrails.
- `scripts/sync_v3_to_all.py`: Ecosystem synchronizer for Web and App.
- `v3_audit_tracker.tsv`: Master progress tracker (127 rows).
