# Thai Quran Translation v4 Pipeline (`thai_quran_translation_v4`)

> **Repository Purpose:** Standalone, reproducible data engineering pipeline and master repository for **Thai Quran Translation v4**, built from the updated [ThaiQuran.com](https://www.thaiquran.com) official revision (`6,236` Ayahs + `7,338` non-empty Footnotes), while restoring 28 eye-skip clause omissions, remediating 1,924 OCR/spelling/structural defects, and standardizing 10,270 Islamic transliteration instances to Quranic Phinthu (`ฺ` `U+0E3A`).
>
> **Production Isolation Guarantee:** Live `thai_v3` across `thai-quran-web`, `thai-quran-app`, `quran_offline.db`, and `thai_quran_scholar_audit_v4` remains **100% untouched**.

---

## 1. Repository Layout

```text
thai_quran_translation_v4/
├── data/
│   ├── 00_tq_raw_source.json           # Immutable raw scrape (SHA-256: abbf001828fbe4e2...)
│   ├── 01_tq_ingested_tokenized.json   # Phase 1: 0-offset ⟦FN:N⟧ tokens + Unicode hygiene
│   ├── 02_tq_omissions_restored.json   # Phase 2: 28 eye-skip clause omissions restored
│   ├── 03_tq_typos_remediated.json     # Phase 3: 5-pass OCR/typo & punctuation remediation
│   ├── 04_tq_standardized.json         # Phase 4: Canonical Islamic translit & Phinthu (ฺ)
│   └── 05_tq_upgrades_cataloged.json   # Phase 5: 3-way comparison vs Thai 1, Thai 2, and v3
├── scripts/
│   ├── 01_ingest_and_tokenize.py
│   ├── 02_restore_omissions.py
│   ├── 03_remediate_typos_and_punct.py
│   ├── 04_standardize_translit.py
│   ├── 05_catalog_upgrades_and_diff.py
│   └── 07_validate_and_package.py
├── reports/
│   ├── phase1_unicode_and_fn_audit.csv
│   ├── phase2_omissions_restored_log.csv
│   ├── phase3_typos_remediation_log.csv
│   ├── phase4_translit_change_log.csv
│   ├── phase5_upgraded_sentences.csv
│   ├── thai_v4_vs_v3_full_diff.html    # Interactive side-by-side HTML diff viewer
│   └── phase7_quality_gates_report.json
├── deliverables/
│   ├── 01_thai_quran_translation_v4_master.json     # Clean drop-in v3-compatible master JSON
│   ├── 02_thai_quran_translation_v4_annotated.json  # Annotated master with [1],[2] & 7,338 footnotes
│   ├── 03_thai_quran_translation_v4_master.csv      # Full UTF-8-BOM CSV
│   └── 04_thai_v4_scholar_review_sheet.csv          # Prioritized scholar review sheet (2,239 rows)
├── project_progress_log.csv
├── PROJECT_PROGRESS_LOG.md
├── AGENTS.md
├── GEMINI.md
└── README.md
```

---

## 2. Pipeline Execution Summary & Metrics

| Phase | Script | Status | Key Metrics |
| :---: | :--- | :---: | :--- |
| **P0** | Git Sandbox Initialization | `COMPLETED` | Standalone repo initialized; production `v3` untouched |
| **P1** | [`scripts/01_ingest_and_tokenize.py`](file:///H:/gits/thai_quran_translation_v4/scripts/01_ingest_and_tokenize.py) | `COMPLETED` | `6,236` Ayahs + `7,338` non-empty Footnotes aligned 1:1 with `⟦FN:N⟧`; `35` structural/Unicode repairs |
| **P2** | [`scripts/02_restore_omissions.py`](file:///H:/gits/thai_quran_translation_v4/scripts/02_restore_omissions.py) | `COMPLETED` | `28` eye-skip clause omissions restored (`22:62`, `4:12`, `8:1`, `14:18`, `59:7`, `2:286`, etc.) + `6` reverse repairs over `v3` (`35:4`, `2:162`, etc.) |
| **P3** | [`scripts/03_remediate_typos_and_punct.py`](file:///H:/gits/thai_quran_translation_v4/scripts/03_remediate_typos_and_punct.py) | `COMPLETED` | `1,924` typo/punctuation operations across `1,399` Ayahs and `316` Footnotes |
| **P4** | [`scripts/04_standardize_translit.py`](file:///H:/gits/thai_quran_translation_v4/scripts/04_standardize_translit.py) | `COMPLETED` | `10,270` canonical Islamic transliteration & Phinthu (`ฺ`) replacements across `2,423` Ayahs and `3,243` Footnotes |
| **P5** | [`scripts/05_catalog_upgrades_and_diff.py`](file:///H:/gits/thai_quran_translation_v4/scripts/05_catalog_upgrades_and_diff.py) | `COMPLETED` | `2,239` substantive sentence diffs cataloged (`581` Theological, `9` Guidance, `1,615` Prose, `28` Restored, `6` Reverse Repairs); `3,997` verses identical in characters to `v3` |
| **P6** | Thai Clause Cadence Engine (LLM) | `OPTIONAL_STAGED` | Reserved for optional breath-pause spacing optimization |
| **P7** | [`scripts/07_validate_and_package.py`](file:///H:/gits/thai_quran_translation_v4/scripts/07_validate_and_package.py) | `COMPLETED` | **10 / 10 Automated Quality Gates Passed (100%)** |

---

## 3. Reproducing the Full Pipeline

Run all deterministic phases end-to-end from the repository root:

```powershell
python scripts/01_ingest_and_tokenize.py
python scripts/02_restore_omissions.py
python scripts/03_remediate_typos_and_punct.py
python scripts/04_standardize_translit.py
python scripts/05_catalog_upgrades_and_diff.py
python scripts/07_validate_and_package.py
```
