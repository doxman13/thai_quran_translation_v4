# Thai Quran Translation v4 Pipeline

> **Repository Purpose:** Standalone, sandbox environment dedicated to building the pristine, official **Thai Quran Translation v4** derived from the [ThaiQuran.com](https://www.thaiquran.com) revision.
> 
> Production `thai_v3` (in `thai-quran-web`, `thai-quran-app`, and `quran_offline.db`) remains **100% untouched** during this process.

---

## 1. Directory Structure

```text
thai_quran_translation_v4/
├── data/                    # Sequential immutable datasets (01_ -> 05_)
├── scripts/                 # Phase execution runners
├── reports/                 # Audit logs, error lists, HTML visual diffs
├── deliverables/            # Final master JSON, CSV, and scholar review sheet
├── project_progress_log.csv # Machine-readable phase status tracking
├── PROJECT_PROGRESS_LOG.md  # Human-readable progress tracker
├── AGENTS.md                # Multi-agent Git synchronization rules
├── GEMINI.md                # Gemini assistant Git synchronization rules
└── README.md                # Project architecture & execution guide
```

---

## 2. Pipeline Execution Plan

| Phase | Phase Name | Status | Target Output |
| :---: | :--- | :---: | :--- |
| **P0** | **Repository & Sandbox Initialization** | `COMPLETED` | `thai_quran_translation_v4` git repo |
| **P1** | **Ingestion & Footnote Decoupling** | `PENDING` | `data/01_tq_ingested_clean.json` |
| **P2** | **Multi-Pass Typo Remediation** | `PENDING` | `data/02_tq_typos_remediated.json` |
| **P3** | **Transliteration & Phinthu Standardization** | `PENDING` | `data/03_tq_standardized.json` |
| **P4** | **Comparative Upgrade Mapping & Omissions Guard** | `PENDING` | `data/04_tq_upgrades_cataloged.json` |
| **P5** | **Thai Clause Cadence Engine (Pipeline 2 LLM)** | `OPTIONAL` | `data/05_thai_v4_cadence_staged.json` |
| **P6** | **Quality Gate Verification & Packaging** | `PENDING` | `deliverables/01_thai_quran_translation_v4_master.json` |

---

## 3. Progress Tracking

See:
* 📊 **[`project_progress_log.csv`](file:///H:/gits/thai_quran_translation_v4/project_progress_log.csv)** for tabular status.
* 📋 **[`PROJECT_PROGRESS_LOG.md`](file:///H:/gits/thai_quran_translation_v4/PROJECT_PROGRESS_LOG.md)** for detailed milestone logs.
