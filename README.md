# Team 4096mb - Codebase Intelligence & Navigation

## Ingestion & Chunking — Person 1 of 4

Turns a raw code repo into clean, embeddable chunks that the retrieval pipeline consumes.

## Output contract

`output/chunks.json` — a JSON array where every element is:

```json
{
  "text":       "def validate_token(token: str) -> Optional[str]:\n    ...",
  "file_path":  "src/auth.py",
  "start_line": 47,
  "end_line":   68,
  "embedding":  [0.012, -0.034, ...]
}
```

Teammates consuming this: **retrieval/search** (Person 2) reads `chunks.json` directly.

---

## Setup

```bash
# 1. Create & activate venv
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure embedding backend
cp .env.example .env
# Edit .env:  set EMBEDDING_BACKEND and GEMINI_API_KEY
```

---

## Quick start

### Step 1 — Smoke test (single file, end-to-end)

```bash
python main.py --repo test_repo --single-file test_repo/auth.py
```

You'll see:
- Number of chunks produced
- A text preview of chunk 0 with its file path and line range
- Embedding dimension (768 for Gemini text-embedding-004, 384 for local)
- `output/chunks.json` written

### Step 2 — Full test_repo

```bash
python main.py --repo test_repo
```

### Step 3 — Real demo repo

```bash
python main.py --repo /path/to/real/repo
```

---

## Backends

| Backend | Env var value | Notes |
|---------|--------------|-------|
| Gemini  | `gemini`     | Requires `GEMINI_API_KEY`. Dim=768. Rate-limited; retry built in. |
| Local   | `local`      | `all-MiniLM-L6-v2` (~90 MB download on first run). Dim=384. Fully offline. |

Switch backends: edit `EMBEDDING_BACKEND` in `.env` or pass `--backend local`.

---

## CLI reference

```
python main.py --repo <path>          # full repo
               --single-file <path>   # smoke-test mode (one file)
               --backend gemini|local # override .env
               --chunk-size N         # lines per chunk (default 512)
               --chunk-overlap N      # overlap (default 64)
               --output path/to.json  # override output path
```

---

## Architecture

```
main.py          ← orchestrator: CLI + repo walk + save
chunker.py       ← CodeSplitter (tree-sitter) → fallback (langchain)
embedder.py      ← Gemini embed_content  OR  sentence-transformers
test_repo/       ← synthetic Python / JS / TS files for validation
output/          ← chunks.json (gitignored)
```

### Chunking strategy

1. **Primary** — `llama_index.core.node_parser.CodeSplitter`  
   Tree-sitter parses the AST; splits happen at function/class boundaries.  
   Supported: Python, JS, TS, Java, Go, Rust, C/C++.

2. **Fallback** — `langchain_text_splitters.RecursiveCharacterTextSplitter.from_language()`  
   Language-aware separator list (e.g. `\nclass `, `\ndef `).  
   Used when a tree-sitter grammar is missing or parse fails.

Line numbers are always computed by binary-searching a character-offset table built from the raw file, so they are accurate regardless of which splitter runs.
>>>>>>> 30dc5d8 (feat(ingestion): tree-sitter CodeSplitter pipeline with Gemini embeddings and repo traversal)
