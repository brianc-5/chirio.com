#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""English search index + bilingual sitemap."""
import argparse, json, os, re, unicodedata

ap = argparse.ArgumentParser()
ap.add_argument("--site", required=True)
ap.add_argument("--map", required=True)
a = ap.parse_args()
site = os.path.abspath(a.site)
m = json.load(open(a.map, encoding="utf-8"))

def key(s):
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", s or "").strip())

# --- search index ---------------------------------------------------------- #
it = json.load(open(os.path.join(site, "assets", "search-index.json"), encoding="utf-8"))
en, hits, misses = [], 0, 0
for e in it:
    out = dict(e)
    for f in ("t", "s", "d", "g"):
        v = e.get(f)
        if not v:
            continue
        k = key(v)
        if k in m:
            out[f] = m[k]; hits += 1
        else:
            misses += 1
    en.append(out)
json.dump(en, open(os.path.join(site, "assets", "search-index.en.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"search-index.en.json: {len(en)} entries, {hits} fields translated, {misses} left as-is")

# --- sitemap --------------------------------------------------------------- #
pages = []
for dp, dn, fn in os.walk(site):
    dn[:] = [d for d in dn if d != "_dev"]
    for f in fn:
        if os.path.splitext(f)[1].lower() in (".htm", ".html"):
            rel = os.path.relpath(os.path.join(dp, f), site).replace(os.sep, "/")
            if rel in ("index.htm", "en/index.htm"):
                continue
            pages.append(rel)
pages.sort()

def loc(rel):
    return "https://chirio.com/" + ("" if rel == "index.html" else rel)

lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
         ' xmlns:xhtml="http://www.w3.org/1999/xhtml">']
for rel in pages:
    it_rel = rel[3:] if rel.startswith("en/") else rel
    en_rel = "en/" + it_rel
    lines.append("  <url>")
    lines.append(f"    <loc>{loc(rel)}</loc>")
    lines.append(f'    <xhtml:link rel="alternate" hreflang="it" href="{loc(it_rel)}"/>')
    lines.append(f'    <xhtml:link rel="alternate" hreflang="en" href="{loc(en_rel)}"/>')
    lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{loc(it_rel)}"/>')
    lines.append("  </url>")
lines.append("</urlset>")
open(os.path.join(site, "sitemap.xml"), "w", encoding="utf-8", newline="\n").write(
    "\n".join(lines) + "\n")
print(f"sitemap.xml: {len(pages)} URLs with hreflang alternates")
