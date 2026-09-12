import json
from pathlib import Path

with open('output/chunks.json', encoding='utf-8') as f:
    chunks = json.load(f)

print(f"Total chunks: {len(chunks)}")
assert len(chunks) == 19

# (a) Check schema
expected_keys = {'text', 'file_path', 'start_line', 'end_line', 'embedding'}
for i, c in enumerate(chunks):
    assert set(c.keys()) == expected_keys, f"Schema mismatch in chunk {i}"
print("(a) Schema verified: exactly the 5 locked fields in all 19 chunks.")

# (b) Check embeddings
emb_dims = set()
for i, c in enumerate(chunks):
    emb = c['embedding']
    assert emb is not None and isinstance(emb, list) and len(emb) == 3072
    assert all(isinstance(v, float) for v in emb)
    emb_dims.add(len(emb))
print(f"(b) Embeddings verified: all 19 non-null float arrays of dimension {emb_dims}.")

# (c) Spot check 4 chunks
print("(c) Spot-checking 4 chunks against source code:")
for idx in [0, 2, 4, 8]:
    c = chunks[idx]
    file_p = Path('nanoGPT') / c['file_path']
    lines = file_p.read_text(encoding='utf-8', errors='replace').splitlines()
    start = c['start_line']
    end = c['end_line']
    first_c_line = c['text'].strip().splitlines()[0].strip()
    first_actual = lines[start-1].strip() if start <= len(lines) else ''
    last_c_line = c['text'].strip().splitlines()[-1].strip()
    last_actual = lines[end-1].strip() if end <= len(lines) else ''
    print(f"  • Chunk {idx} ({c['file_path']}: L{start}-L{end}):")
    print(f"    - First line: {first_c_line[:50]!r} == {first_actual[:50]!r} (Match: {first_c_line == first_actual})")
    print(f"    - Last line:  {last_c_line[:50]!r} == {last_actual[:50]!r} (Match: {last_c_line == last_actual})")
