# Fallback / Backup Repository Specification & Runbook

This document defines the emergency fallback repository (`pallets/itsdangerous`) prepared to replace the primary demo target (`pallets/click`) in case of live demonstration failures (e.g. network partition, GitHub clone outage, or API rate limiting).

---

## 1. Why `itsdangerous`?

| Attribute | Primary (`click`) | Backup (`itsdangerous`) | Rationale |
|---|---|---|---|
| **Organization** | Pallets | Pallets | Same ecosystem, coding standards, and project structure |
| **Language** | 100% Python | 100% Python | Zero foreign language dependencies |
| **Clone Time** | ~15–20s | **~5s** | Ultra-lightweight repository |
| **Source Files** | 142 | **18** | Compact, focused codebase |
| **Total Chunks** | 764 | **82** | 9× fewer chunks, identical AST quality |
| **Pipeline Runtime** | ~14 min | **44.97s (< 1 min)** | Can be re-embedded live from scratch in under a minute |
| **Snapshot Runtime** | ~7 min (10 snapshots) | **55.18s (5 snapshots)** | Drift trend ready immediately |

---

## 2. Backup Output Artifacts

All backup outputs are strictly isolated from primary `click` outputs to prevent accidental overwrites:

| Artifact | File / Directory | Backend | Dimension | Chunks / Entries |
|---|---|---|---|---|
| **Live Q&A Chunks** | `output/backup_chunks.json` | Gemini | **3072** | 82 chunks |
| **Snapshot Manifest** | `output/backup_snapshots/manifest.json` | Local | — | 5 snapshots |
| **Snapshot Chunk Files** | `output/backup_snapshots/*_chunks.json` | Local (`all-MiniLM-L6-v2`) | **384** | 6 → 82 chunks |

---

## 3. One-Line Instant Hot-Swap Instructions

If `click` experiences any failure during the live demo, execute the following one-line hot-swaps:

### For Person 3 (FastAPI Backend / `/ask` endpoint)
Change the chunk file path in your ingestion/loader module:
```python
# Hot-swap chunk file
CHUNKS_PATH = "output/backup_chunks.json"  # was "output/chunks.json"
```
Or set the environment variable:
```bash
# Linux / macOS
export OUTPUT_FILE=backup_chunks.json

# Windows PowerShell
$env:OUTPUT_FILE = "backup_chunks.json"
```

### For Person 3 (FastAPI Backend / `/drift-trend` endpoint)
Point the manifest reader to the backup snapshots directory:
```python
# Hot-swap snapshots manifest
SNAPSHOTS_MANIFEST = "output/backup_snapshots/manifest.json"  # was "output/snapshots/manifest.json"
```

### For Person 4 (Streamlit / Next.js UI)
Update repository selector dropdown or default demo repo name:
- Repo Name: `pallets/itsdangerous`
- Description: `Python cryptographic serialization library (Pallets)`

---

## 4. Verification & Validation Summary

### Live Chunks (`output/backup_chunks.json`)
- **Total Chunks**: 82
  - `37` via Tree-sitter AST `CodeSplitter` (functions and classes in `serializer.py`, `signer.py`, `timed.py`, etc.)
  - `45` via Langchain recursive fallback (`pyproject.toml`, `.pre-commit-config.yaml`, `.readthedocs.yaml`)
- **Schema**: Strictly satisfies 5 locked fields: `text`, `file_path`, `start_line`, `end_line`, `embedding`
- **Embeddings**: All 82 non-null, valid 3072-dimensional float vectors
- **End-to-end runtime**: 44.97s (Chunking: 29.57s, Embedding: 15.40s)

### Historical Snapshots (`output/backup_snapshots/`)
- **Total Snapshots**: 5 uniformly spaced commits across 14 years of git history:

| Commit | Date | Files | Chunks | Message |
|---|---|---|---|---|
| `b393ac7` | 2011-06-24 | 2 | 6 | Initial version |
| `6910fe0` | 2018-10-26 | 22 | 48 | Fix typo |
| `4bda48f` | 2021-02-09 | 20 | 51 | reduce lock schedule to daily |
| `aa7e016` | 2022-11-01 | 18 | 47 | Bump actions/cache from 3.0.9 to 3.0.11 (#319) |
| `672971d` | 2025-06-14 | 19 | 82 | Merge branch 'stable' (HEAD) |

- **Growth Arc**: 6 chunks (2011) → 82 chunks (2025) — ideal 13.6× growth curve for Person 3's `/drift-trend` visualization.
- **Snapshot Runtime**: 55.18 seconds total.
