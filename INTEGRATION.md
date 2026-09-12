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

> [!IMPORTANT]
> Queries submitted by Person 2's search function **must be embedded using the exact same model and backend** as the chunks. Vectors from different backends cannot be compared or mixed.

| Attribute | Primary Backend (`gemini`) | Local Offline Backend (`local`) |
|---|---|---|
| **Model** | Google `models/gemini-embedding-001` | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector Dimension** | **3072** | **384** |
| **Active File** | `output/chunks.json` | `output/chunks_local.json` |
| **Query Embedding** | Call Gemini API with `taskType="RETRIEVAL_QUERY"` | Call `model.encode(query)` |

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
