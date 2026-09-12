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

### Step 3 — Official Demo Repo (pallets/click)

```bash
git clone --depth 1 https://github.com/pallets/click.git click
python main.py --repo click
```

Produces `output/chunks.json` (~764 chunks) ready for Person 2 (retrieval/vector store) and Person 3 (FastAPI/LLM Q&A).

---

## Benchmark & Performance (Official Demo: click)

- **Target**: `pallets/click` (165 scanned files, 137 processed)
- **Total Chunks**: 764 chunks
  - 675 via Tree-sitter `CodeSplitter` (Python)
  - 89 via `langchain_fallback` (Markdown docs, YAML, TOML)
- **Timing**:
  - Chunking duration: ~5.2s
  - Embedding duration: ~820s (~13.7 min on standard Gemini API tier with 429 backoff)
- **Output**: `output/chunks.json` (locked 5-key schema, 3072-dim embeddings)
