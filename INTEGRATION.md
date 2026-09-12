# Integration Guide — Ingestion Chunks (Person 1 → Person 2 & 3)

This document provides the contract, specifications, and consumption guidelines for Person 2 (Retrieval / Vector Search) and Person 3 (FastAPI / LLM Backend) consuming `output/chunks.json`.

---

## 1. Output Contract & Schema

The output is written to `output/chunks.json` as a single UTF-8 encoded JSON array of 764 chunks for `pallets/click` (~2.4 MB on disk).

Each item strictly satisfies the 5 locked schema fields:

```json
{
  "text": "def option(*param_decls: str, ...):\n    ...",
  "file_path": "src/click/decorators.py",
  "start_line": 352,
  "end_line": 418,
  "embedding": [0.0125, -0.0341, ...]
}
```

### Schema Specification
- `text` (`str`): Clean source code text slice. Guaranteed non-empty.
- `file_path` (`str`): Relative path from the repository root, normalized with forward slashes `/`.
- `start_line` (`int`): 1-indexed inclusive starting line number in the source file.
- `end_line` (`int`): 1-indexed inclusive ending line number in the source file.
- `embedding` (`List[float]`): Float vector. Guaranteed non-null, valid floats with no `NaN` or `Inf` values.

---

## 2. Embedding Model & Vector Space Matching

> [!CAUTION]
> **CRITICAL VECTOR SPACE WARNING FOR PERSON 2 & PERSON 3**:
> Even though Google `models/gemini-embedding-001` and `models/gemini-embedding-2` both produce **3072-dimensional** vectors, their coordinate spaces are **completely different, orthogonal, and mathematically incompatible**.
> - An empirical dot product of identical text across the two models yields ~0.0018 (essentially random noise).
> - **DO NOT mix chunks embedded under different Gemini model versions in the same index.**
> - **Person 2's `/ask` query embedder MUST call the EXACT same model version that was used to produce `output/chunks.json`.**
>
> Currently, `output/chunks.json` for Click (764 chunks) and `output/backup_chunks.json` for itsdangerous (82 chunks) are embedded using:
> **`models/gemini-embedding-2`** (due to Google's 1,000 req/day cap on v1).
>
> When embedding queries in Person 2/3's retrieval service, specify:
> `"model": "models/gemini-embedding-2"` and `"taskType": "RETRIEVAL_QUERY"`.

| Attribute | Primary Cloud Backend (`gemini`) | Local Offline Backend (`local`) |
|---|---|---|
| **Active Model** | Google **`models/gemini-embedding-2`** (fallback from `001`) | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector Dimension** | **3072** | **384** |
| **Active File** | `output/chunks.json` | `output/chunks_local.json` |
| **Query Embedding** | `batchEmbedContents` with `model="models/gemini-embedding-2"`, `taskType="RETRIEVAL_QUERY"` | Call `model.encode(query)` |

---

## 3. Dataset Characteristics & File Statistics (Target: pallets/click)

- **Total files scanned**: 165
- **Files processed (chunks > 0)**: 137
- **Files skipped / 0-chunks**: 28
  - `5` empty `__init__.py` files (0 code lines)
  - `23` non-code assets (docs images `.svg`, `.jpg`, `.ini`, `.lock`, `.typed`, `.txt`)
- **Total chunks produced**: 764
  - `675` chunks via Tree-sitter AST `CodeSplitter` (Python)
  - `89` chunks via Langchain recursive fallback (Markdown documentation, TOML, YAML configs)
- **JSON File Size**: ~2.4 MB (loads into memory in < 15ms via `json.load()`)

---

## 4. Known Edge Cases & FAQ for Search/Retrieval Consumers

### Q: Why are there tiny 1-line chunks like `class Command:` (line 964) in `core.py`?
**Explanation**: Tree-sitter parses the code as a syntax tree (AST). In Python grammars, `class_definition` contains the class header as an independent node, while inner methods (`__init__`, `invoke`, etc.) are parsed as child AST blocks. When methods exceed the chunk window (~40 lines), CodeSplitter splits at inner method boundaries, leaving the class declaration as an independent semantic header.
**Search Recommendation**: If a query matches a class declaration chunk, Person 2's search ranker can retrieve the subsequent chunk (the primary `__init__` or docstring block) to provide complete context.

### Q: What about non-UTF-8 or Latin-1 files?
Files containing non-UTF-8 characters (e.g. Latin-1 umlauts or legacy docstrings) are decoded with UTF-8 `replace` fallback. The character offsets and 1-based `start_line` / `end_line` coordinates are computed strictly from the underlying byte layout, ensuring that line citations remain accurate even if an unsupported glyph is replaced.

---

## 5. Python Consumer Quickstart for Person 2

```python
import json
import numpy as np

# Load chunks
with open("output/chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

# Extract matrix for cosine similarity search (764 x 3072)
embeddings = np.array([c["embedding"] for c in chunks], dtype=np.float32)

def search(query_vector: np.ndarray, top_k: int = 5):
    # Cosine similarity: (A . B) / (||A|| * ||B||)
    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_vector)
    similarities = np.dot(embeddings, query_vector) / np.maximum(norms, 1e-9)
    top_indices = np.argsort(similarities)[::-1][:top_k]

    return [{
        "file_path": chunks[i]["file_path"],
        "lines": f"{chunks[i]['start_line']}-{chunks[i]['end_line']}",
        "score": float(similarities[i]),
        "text": chunks[i]["text"]
    } for i in top_indices]
```

---

## 6. Historical Snapshots (for Person 3's `/drift-trend` endpoint)

A separate pipeline (`historical_snapshots.py`) pre-computes chunk embeddings across 10 evenly-spaced commits in click's full git history (2014 to 2026), producing a time-series dataset for codebase duplication/drift analysis.

### 6.1 Manifest

**Path**: `output/snapshots/manifest.json`

```json
{
  "repository": "click",
  "total_snapshots": 10,
  "snapshots": [
    {
      "commit_hash": "4101de3daf91c6d35b92395a72bf84132ef48f7c",
      "short_hash":  "4101de3",
      "date":        "2014-04-24",
      "message":     "Initial commit",
      "file_count":  9,
      "chunk_count": 39,
      "embedding_backend":   "local",
      "embedding_dimension": 384,
      "output_file": "4101de3daf91c6d35b92395a72bf84132ef48f7c_chunks.json"
    }
  ]
}
```

The `snapshots` array is ordered **oldest to newest**. Each entry provides:
- `commit_hash` / `short_hash` — full and 7-char git SHA
- `date` — ISO 8601 commit date (author date)
- `message` — first line of the commit message
- `file_count` — source files processed at that commit
- `chunk_count` — total chunks produced
- `embedding_backend` — always `"local"` for snapshots (see § 6.3)
- `embedding_dimension` — always `384` for snapshots
- `output_file` — filename (not full path) of the per-snapshot chunk file

### 6.2 Per-Snapshot Chunk Files

**Path pattern**: `output/snapshots/<full_commit_hash>_chunks.json`

Each file is a JSON array using the same 5-field schema as `output/chunks.json`:

```json
[
  {
    "text":       "...",
    "file_path":  "click.py",
    "start_line": 1,
    "end_line":   96,
    "embedding":  [0.0125, -0.0341, "..."]
  }
]
```

> **Note**: Only `manifest.json` is committed to git. The individual `*_chunks.json` files are gitignored (~40 MB total). Person 3 should read them from the local `output/snapshots/` directory after running `historical_snapshots.py`.

### 6.3 Backend Split (Critical for Vector Space Matching)

| Output | Backend | Model | Dimension |
|---|---|---|---|
| `output/chunks.json` | `gemini` | `models/gemini-embedding-001` | **3072** |
| `output/snapshots/*_chunks.json` | `local` | `all-MiniLM-L6-v2` | **384** |

The two vector spaces are **incompatible**. Person 3's `/drift-trend` endpoint should embed queries using the local backend (`sentence-transformers`) when searching snapshot chunks.

### 6.4 Snapshot Growth Timeline

| Commit | Date | Files | Chunks |
|---|---|---|---|
| `4101de3` | 2014-04-24 | 9 | 39 |
| `c42e93c` | 2014-06-01 | 53 | 148 |
| `c55d7d2` | 2015-11-05 | 60 | 196 |
| `537cd3c` | 2018-06-13 | 64 | 229 |
| `7cc7d40` | 2020-05-23 | 63 | 233 |
| `dcd991d` | 2021-05-07 | 66 | 290 |
| `58c2d97` | 2023-03-01 | 66 | 313 |
| `2a20aca` | 2025-03-26 | 76 | 373 |
| `aaf99a3` | 2026-02-20 | 105 | 545 |
| `6aabf09` | 2026-09-05 | 142 | **764** |

The codebase grew from 39 to 764 chunks (~20x growth) over 12 years.

### 6.5 Re-generating Snapshots

```powershell
# Regenerate with defaults (10 snapshots, local backend)
.venv\Scripts\python historical_snapshots.py --repo click --max-snapshots 10

# Custom step size
.venv\Scripts\python historical_snapshots.py --repo click --max-snapshots 10 --step 30
```

The script is **idempotent**: it skips already-generated snapshots if their output file exists. Worktrees are cleaned up automatically even on failure.

---

## 7. Emergency Fallback / Backup Repository (`itsdangerous`)

In case the primary `click` target encounters live demonstration issues (network partition, rate limits, etc.), an identical full dataset has been pre-computed for `pallets/itsdangerous`:

- **Live Chunks**: `output/backup_chunks.json` (82 chunks, 3072-dim Gemini, 100% schema valid)
- **Historical Snapshots**: `output/backup_snapshots/` (5 snapshots from 2011 to 2025, 384-dim)
- **Full Runbook**: See [`BACKUP.md`](file:///c:/Users/samri/Documents/antigravity/intelligent-faraday/BACKUP.md)

### Instant Hot-Swap:
- **Person 3 (`/ask`)**: Load from `output/backup_chunks.json` instead of `output/chunks.json`.
- **Person 3 (`/drift-trend`)**: Read manifest from `output/backup_snapshots/manifest.json`.
- **Re-run Pipeline**: `python main.py --repo itsdangerous --output output/backup_chunks.json` (takes only 45 seconds).
