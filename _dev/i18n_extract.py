#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract every translatable string from the Italian site.

Why extract instead of translating whole pages: a model asked to translate raw
HTML will eventually break markup, drop an attribute or reflow a table. Pulling
the text out, translating only text, and putting it back guarantees the English
site is structurally identical to the Italian one — same tags, same links, same
images, same anchors — and it costs a fraction of the tokens because no markup
is ever sent to the model.

Strings are deduplicated across the whole site, so the shared header, footer and
navigation are translated once rather than 256 times.

    python3 i18n_extract.py --site <dir> --out <_dev/i18n>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict

from bs4 import BeautifulSoup, NavigableString, Comment

# elements whose text is code or data, never prose
SKIP_PARENTS = {"script", "style", "pre", "code", "samp", "kbd", "textarea"}

# attributes that hold human-readable text
ATTRS = ("alt", "title", "aria-label", "placeholder", "data-play", "data-stop")

# <meta name=...> whose content is prose
META_NAMES = {"description", "keywords"}

#: strings that must never be sent to a translator
NOT_TRANSLATABLE = re.compile(
    r"""^(
        [\s\W\d]*                       # punctuation / digits / symbols only
        |[\w.\-]+\.(jpg|jpeg|png|gif|pdf|mp4|wav|avi|wmv|htm|html|zip|xls|ino)
        |https?://\S*
        |[A-Za-z]{1,3}\d[\w./\-]*       # part numbers: BC547, 2N3819, IC-R20
        |\d[\w./\-]*
    )$""",
    re.I | re.X,
)


def norm(s: str) -> str:
    """Collapse whitespace but keep the original wording."""
    return re.sub(r"\s+", " ", s).strip()


def translatable(s: str) -> bool:
    s = norm(s)
    if len(s) < 2:
        return False
    if NOT_TRANSLATABLE.match(s):
        return False
    # needs at least one run of letters
    if not re.search(r"[A-Za-zÀ-ÿ]{2,}", s):
        return False
    return True


def key_of(s: str) -> str:
    """Stable identity for a string: normalised text, case preserved."""
    return unicodedata.normalize("NFC", norm(s))


def walk(site, rel):
    """Yield ('text'|attr-name, key) for every translatable unit on a page."""
    path = os.path.join(site, rel.replace("/", os.sep))
    soup = BeautifulSoup(open(path, encoding="utf-8").read(), "html.parser")

    t = soup.find("title")
    if t and translatable(t.get_text()):
        yield ("title", key_of(t.get_text()))

    for m in soup.find_all("meta"):
        if (m.get("name") or "").lower() in META_NAMES:
            c = m.get("content") or ""
            if translatable(c):
                yield ("meta:" + m["name"].lower(), key_of(c))

    body = soup.body
    if body is None:
        return

    for node in body.find_all(string=True):
        if isinstance(node, Comment):
            continue
        if node.parent.name in SKIP_PARENTS:
            continue
        if translatable(str(node)):
            yield ("text", key_of(str(node)))

    for el in body.find_all(True):
        for a in ATTRS:
            v = el.get(a)
            if isinstance(v, str) and translatable(v):
                yield ("attr:" + a, key_of(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    site = os.path.abspath(a.site)
    os.makedirs(a.out, exist_ok=True)

    pages = []
    for dirpath, dirnames, filenames in os.walk(site):
        dirnames[:] = [d for d in dirnames if d not in ("_dev", "en")]
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1].lower() in (".htm", ".html"):
                pages.append(os.path.relpath(os.path.join(dirpath, fn), site)
                             .replace(os.sep, "/"))
    pages.sort()

    freq = Counter()
    kinds = defaultdict(set)
    per_page = {}
    for rel in pages:
        if rel == "index.htm":          # the legacy redirect stub
            continue
        units = list(walk(site, rel))
        per_page[rel] = len(units)
        for kind, k in units:
            freq[k] += 1
            kinds[k].add(kind.split(":")[0])

    strings = sorted(freq)
    chars = sum(len(s) for s in strings)
    total_uses = sum(freq.values())

    json.dump(
        {"strings": strings, "freq": {k: freq[k] for k in strings}},
        open(os.path.join(a.out, "catalog.it.json"), "w", encoding="utf-8"),
        ensure_ascii=False, indent=0)

    print(f"pages scanned      : {len(per_page)}")
    print(f"translatable units : {total_uses}")
    print(f"unique strings     : {len(strings)}   ({total_uses/max(1,len(strings)):.1f}× reuse)")
    print(f"characters         : {chars:,}")
    print(f"est. source tokens : ~{chars/3.3:,.0f}")
    print()
    print("length distribution of unique strings:")
    buckets = [(0, 20), (20, 60), (60, 150), (150, 400), (400, 1200), (1200, 10**9)]
    for lo, hi in buckets:
        n = sum(1 for s in strings if lo <= len(s) < hi)
        c = sum(len(s) for s in strings if lo <= len(s) < hi)
        label = f"{lo}-{hi if hi < 10**9 else '∞'}"
        print(f"  {label:>10} chars : {n:5d} strings, {c:8,} chars")
    print()
    print("heaviest pages by unit count:")
    for rel, n in sorted(per_page.items(), key=lambda x: -x[1])[:8]:
        print(f"  {n:5d}  {rel}")


if __name__ == "__main__":
    main()
