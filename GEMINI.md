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

# thai_quran_translation_v4 Guidelines

## Git Synchronization (Mandatory)
- **Source of Truth**: The remote repository on GitHub (origin) is ALWAYS the authoritative source of truth.
- **Pre-Action Requirement**: Before starting ANY task, analysis, script run, or code edits, ALWAYS run git pull first to synchronize with the latest remote state.
- Never make changes or base decisions on stale local code.
