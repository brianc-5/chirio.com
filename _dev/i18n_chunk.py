#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Split the string catalogue into translation chunks sized for one model call."""
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument("--catalog", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--chars", type=int, default=22000)
a = ap.parse_args()

cat = json.load(open(a.catalog, encoding="utf-8"))
strings = cat["strings"]
freq = cat["freq"]

# longest first so a chunk never ends up with one giant string plus nothing else
order = sorted(strings, key=lambda s: (-len(s), s))
chunks, cur, size = [], [], 0
for s in order:
    if cur and size + len(s) > a.chars:
        chunks.append(cur); cur, size = [], 0
    cur.append(s); size += len(s)
if cur:
    chunks.append(cur)

os.makedirs(a.out, exist_ok=True)
index = []
for i, ch in enumerate(chunks, 1):
    payload = {str(n): s for n, s in enumerate(ch, 1)}
    p = os.path.join(a.out, f"it_{i:02d}.json")
    json.dump(payload, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    index.append({"chunk": i, "file": os.path.basename(p),
                  "items": len(ch), "chars": sum(len(s) for s in ch)})
json.dump(index, open(os.path.join(a.out, "index.json"), "w", encoding="utf-8"), indent=1)
print(f"{len(chunks)} chunks")
for e in index:
    print(f"  it_{e['chunk']:02d}.json  {e['items']:5d} items  {e['chars']:7,} chars")
