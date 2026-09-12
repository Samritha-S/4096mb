import json
from pathlib import Path

with open('output/chunks.json', encoding='utf-8') as f:
    chunks = json.load(f)

print(f"Total chunks: {len(chunks)}")

# (a) Check schema
expected_keys = {'text', 'file_path', 'start_line', 'end_line', 'embedding'}
for i, c in enumerate(chunks):
    if set(c.keys()) != expected_keys:
        print(f"Schema mismatch in chunk {i}: {set(c.keys())}")
        break
else:
    print("(a) Schema check PASSED: Exactly the 5 locked fields in every chunk.")

# (b) Check embeddings
emb_lens = set()
for i, c in enumerate(chunks):
    emb = c['embedding']
    assert emb is not None, f"Chunk {i} has None embedding"
    assert isinstance(emb, list) and len(emb) > 0, f"Chunk {i} embedding is empty or not a list"
    assert all(isinstance(v, float) for v in emb), f"Chunk {i} embedding values are not all floats"
    emb_lens.add(len(emb))

print(f"(b) Embedding check PASSED: All 57 embeddings are non-null float arrays. Dimensions: {emb_lens}")

# (c) Spot check line citations
print("(c) Spot-checking line citations against raw source files:")
for idx in [0, 5, 15, 25, 45, 56]:
    if idx < len(chunks):
        c = chunks[idx]
        file_p = Path('nanoGPT') / c['file_path']
        lines = file_p.read_text(encoding='utf-8', errors='replace').splitlines()
        start = c['start_line']
        end = c['end_line']
        actual_slice = '\n'.join(lines[start-1:end])
        c_first_line = c['text'].strip().splitlines()[0].strip()
        actual_first_line = lines[start-1].strip() if start <= len(lines) else ""
        first_match = (c_first_line == actual_first_line)
        print(f"  • Chunk {idx:>2} [{c['file_path']} L{start}-L{end}]")
        print(f"    - Chunk line count: {end - start + 1}, Chars: {len(c['text'])}")
        print(f"    - First line in chunk: {c_first_line[:50]!r}")
        print(f"    - First line at L{start}: {actual_first_line[:50]!r}")
        print(f"    - Accurate match: {first_match}")
