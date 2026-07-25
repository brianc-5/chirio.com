#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the page-by-page revision checklist.

Every HTML page in the site gets a row: family, size, what still looks like it
needs a human, and its revision status. Status is derived from evidence, never
assumed:

  curated   listed in _dev/curated.txt — opened, edited and reviewed by hand
  system    carries the design system and the reviewed retrofit passes, but no
            page-specific editorial decision has been made
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter, defaultdict

from bs4 import BeautifulSoup

FAMILY_ORDER = ["home", "technical article", "legal page", "chaberton landing",
                "chaberton article", "gallery index", "photo page", "panorama",
                "error page", "redirect"]


def classify(rel, soup):
    if rel == "index.html":
        return "home"
    if rel == "index.htm":
        return "redirect"
    if rel == "404.html":
        return "error page"
    if soup.select_one(".photo-view"):
        return "photo page"
    if soup.select_one("ul.gallery"):
        return "gallery index"
    if soup.select_one(".pano"):
        return "panorama"
    if rel == "chaberton/chab.htm":
        return "chaberton landing"
    if rel.startswith("chaberton/"):
        return "chaberton article"
    if "privacy" in rel or "disclaimer" in rel:
        return "legal page"
    return "technical article"


def flags(soup, words):
    """Signals that a human should look at this page. Each is observable."""
    out = []
    hs = [re.sub(r"\s+", " ", h.get_text(" ")).strip() for h in soup.select(".prose h2")]
    if any(len(h) > 70 for h in hs):
        out.append("long heading")
    if len(soup.select(".prose h2")) == 0 and words > 700:
        out.append("no sections")
    if len(soup.select(".toc a")) > 14:
        out.append("long TOC")
    if words > 2000:
        out.append("very long")
    if soup.select_one('.prose img[src^="http"]'):
        out.append("external image")
    if len(soup.select(".prose .center")) > 6:
        out.append("centred blocks")
    if soup.select_one(".prose table") and not soup.select_one(".prose th"):
        out.append("headerless table")
    if len(soup.select(".prose ul.dash-list")) > 6:
        out.append("many lists")
    if not soup.select_one(".article-head .subtitle") and words > 1200:
        out.append("no subtitle")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    site = os.path.abspath(a.site)

    curated_file = os.path.join(site, "_dev", "curated.txt")
    curated = set()
    if os.path.exists(curated_file):
        curated = {l.strip() for l in open(curated_file, encoding="utf-8")
                   if l.strip() and not l.startswith("#")}

    sys.path.insert(0, os.path.join(site, "_dev"))
    import sitemeta as meta
    section_of = dict(meta.PAGE_SECTION)
    labels = dict(meta.INDEX_LABEL)

    rows = []
    for dirpath, dirnames, filenames in os.walk(site):
        dirnames[:] = [d for d in dirnames if d != "_dev"]
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1].lower() not in (".htm", ".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), site).replace(os.sep, "/")
            soup = BeautifulSoup(open(os.path.join(dirpath, fn), encoding="utf-8").read(),
                                 "html.parser")
            prose = soup.select_one(".prose")
            words = len(re.findall(r"\w+", prose.get_text(" "))) if prose else 0
            fam = classify(rel, soup)
            rows.append({
                "rel": rel,
                "family": fam,
                "section": section_of.get(rel, ""),
                "title": (labels.get(rel, ("", ""))[0]
                          or (soup.select_one("h1").get_text(" ").strip()
                              if soup.select_one("h1") else rel)),
                "words": words,
                "imgs": len(soup.select(".prose img")) + len(soup.select(".photo-view img")),
                "flags": flags(soup, words),
                "status": "curated" if rel in curated else "system",
            })

    by_family = defaultdict(list)
    for r in rows:
        by_family[r["family"]].append(r)

    def priority(r):
        if r["status"] == "curated":
            return 4
        if r["family"] == "technical article":
            if len(r["flags"]) >= 2 or r["words"] > 1800:
                return 1
            if r["words"] > 800 or r["flags"]:
                return 2
            return 3
        if r["family"] in ("chaberton article", "legal page", "gallery index"):
            return 2 if r["flags"] else 3
        return 3

    for r in rows:
        r["priority"] = priority(r)

    pri_name = {1: "P1 — revise next", 2: "P2 — review", 3: "P3 — spot-check",
                4: "done — hand-curated"}

    lines = []
    w = lines.append
    w("# Revision checklist — chirio-modern")
    w("")
    w("Generated by `_dev/make_checklist.py`. Re-run it any time to refresh the")
    w("counts; move a page to `done` by adding it to `_dev/curated.txt` after you")
    w("have actually opened and revised it.")
    w("")
    w("**Status has two values and neither of them is a promise.**")
    w("")
    w("- `curated` — the page was opened, restructured and reviewed by hand.")
    w("- `system` — the page carries the new design system and every reviewed")
    w("  retrofit pass (chrome, `[home]` removal, lists, spacing, units, media")
    w("  tagging, TOC labels, metadata). No page-specific editorial judgement has")
    w("  been applied. These pages are correct and consistent; they are not")
    w("  individually curated.")
    w("")

    tot = Counter(r["status"] for r in rows)
    w(f"**{len(rows)} pages total — {tot['curated']} curated, {tot['system']} on the system.**")
    w("")

    w("## By page family")
    w("")
    w("| Family | Pages | Curated | Notes |")
    w("| --- | ---: | ---: | --- |")
    fam_note = {
        "home": "hand-built; the only page with a bespoke layout",
        "technical article": "the archive proper — where the remaining work is",
        "legal page": "short, stable, low risk",
        "chaberton landing": "hand-built section entry point",
        "chaberton article": "prose pages of the historical archive",
        "gallery index": "thumbnail grids, uniform",
        "photo page": "one photograph plus prev/next, uniform",
        "panorama": "JS viewer over the 6000 px originals",
        "error page": "static 404",
        "redirect": "legacy lowercase URL stub",
    }
    for fam in FAMILY_ORDER:
        rs = by_family.get(fam, [])
        if not rs:
            continue
        w(f"| {fam} | {len(rs)} | {sum(1 for r in rs if r['status']=='curated')} "
          f"| {fam_note.get(fam,'')} |")
    w("")

    w("## Priority queue")
    w("")
    pc = Counter(r["priority"] for r in rows)
    for p in (1, 2, 3, 4):
        w(f"- **{pri_name[p]}** — {pc[p]} pages")
    w("")
    w("Priority is computed from observable signals: page length, number of")
    w("sections, over-long headings, table-of-contents size, centred blocks,")
    w("headerless tables, external images, missing subtitle.")
    w("")

    for p in (1, 2, 3, 4):
        group = sorted((r for r in rows if r["priority"] == p),
                       key=lambda r: (-r["words"], r["rel"]))
        if not group:
            continue
        w(f"### {pri_name[p]} ({len(group)})")
        w("")
        w("| Page | Family | Words | Img | Needs a look at | Status |")
        w("| --- | --- | ---: | ---: | --- | --- |")
        for r in group:
            fl = ", ".join(r["flags"]) or "—"
            w(f"| `{r['rel']}` | {r['family']} | {r['words']} | {r['imgs']} | {fl} | {r['status']} |")
        w("")

    open(a.out, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print(f"checklist written: {a.out} ({len(rows)} pages)")
    for p in (1, 2, 3, 4):
        print(f"  {pri_name[p]:24s} {pc[p]}")


if __name__ == "__main__":
    main()
