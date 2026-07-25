#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the English mirror at /en/ from the Italian pages.

Each English page is the Italian page with its text substituted — same tags,
same attributes, same links, same images, same anchors, same ids. Nothing is
re-laid-out, so the two trees cannot drift structurally.

Three things are rewritten rather than copied:

* **asset paths** gain one ``../`` — ``/en/`` mirrors the tree exactly, so a
  page one level deeper needs one extra hop to reach the shared media. Links to
  other *pages* are left alone: they stay inside the mirror.
* ``lang`` becomes ``en``, and both trees gain ``hreflang`` alternates.
* ``data-root`` (path to the site root, for assets) and ``data-lang-root``
  (path to this language's root, for page links) are set per page.

    python3 i18n_build.py --site <dir> --map <map.en.json>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import unicodedata
from collections import Counter

from bs4 import BeautifulSoup, NavigableString, Comment

SKIP_PARENTS = {"script", "style", "pre", "code", "samp", "kbd", "textarea"}
ATTRS = ("alt", "title", "aria-label", "placeholder", "data-play", "data-stop")
META_NAMES = {"description", "keywords"}
HTML_EXT = {".htm", ".html"}

STATS = Counter()


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def key_of(s):
    return unicodedata.normalize("NFC", norm(s))


def is_page(target, pages_lower):
    return target.lower() in pages_lower


def rewrite_url(url, page_rel, pages_lower):
    """Return the URL as it must appear on the English copy of *page_rel*.

    A link to another page is left untouched — the mirror has the same shape, so
    the same relative path lands on the English counterpart. A link to a shared
    asset is re-anchored: resolve it against the site root, then climb out of
    /en/ and back down. Doing it via the root is the only version that is
    correct at every depth; simply prepending one "../" works at the top level
    and silently breaks one directory down.
    """
    if not url:
        return url
    u = url.strip()
    if u.startswith("#") or re.match(r"^[a-zA-Z][\w+.-]*:", u) or u.startswith("//"):
        return url                              # anchor, mailto, absolute
    if u.startswith("/"):
        # a site-absolute link must stay inside the English tree
        return url if u.startswith("/en/") else "/en" + u
    frag = ""
    if "#" in u:
        u, frag = u.split("#", 1)
        frag = "#" + frag
    if not u:
        return url

    page_dir = os.path.dirname(page_rel)
    from urllib.parse import unquote
    probe = os.path.normpath(os.path.join(page_dir, unquote(u))).replace(os.sep, "/")
    if is_page(probe, pages_lower):
        return url                              # another page: stays in /en/

    # percent-escapes are preserved: path maths never needs them decoded
    from_root = os.path.normpath(os.path.join(page_dir, u)).replace(os.sep, "/")
    depth = page_rel.count("/")
    return "../" * (depth + 1) + from_root + frag


def translate_page(site, rel, mapping, pages_lower, out_root):
    src = os.path.join(site, rel.replace("/", os.sep))
    soup = BeautifulSoup(open(src, encoding="utf-8").read(), "html.parser")

    # --- text -------------------------------------------------------------- #
    body = soup.body
    if body is not None:
        for node in list(body.find_all(string=True)):
            if isinstance(node, Comment) or node.parent.name in SKIP_PARENTS:
                continue
            raw = str(node)
            k = key_of(raw)
            if not k or k not in mapping:
                continue
            # keep the original leading/trailing whitespace: it is meaningful
            # between inline elements
            lead = raw[:len(raw) - len(raw.lstrip())]
            trail = raw[len(raw.rstrip()):]
            node.replace_with(NavigableString(lead + mapping[k] + trail))
            STATS["text"] += 1

        for el in body.find_all(True):
            for a in ATTRS:
                v = el.get(a)
                if isinstance(v, str) and key_of(v) in mapping:
                    el[a] = mapping[key_of(v)]
                    STATS["attr"] += 1

    t = soup.find("title")
    if t and key_of(t.get_text()) in mapping:
        t.string = mapping[key_of(t.get_text())]
        STATS["title"] += 1
    for m in soup.find_all("meta"):
        if (m.get("name") or "").lower() in META_NAMES:
            c = m.get("content") or ""
            if key_of(c) in mapping:
                m["content"] = mapping[key_of(c)]
                STATS["meta"] += 1

    # --- urls -------------------------------------------------------------- #
    for el in soup.find_all(True):
        for attr in ("href", "src", "poster"):
            v = el.get(attr)
            if isinstance(v, str):
                new = rewrite_url(v, rel, pages_lower)
                if new != v:
                    el[attr] = new
                    STATS["url"] += 1

    # --- language switch, now pointing the other way ------------------------ #
    import retrofit as R
    old = soup.select_one(".lang-switch")
    if old is not None:
        old.replace_with(BeautifulSoup(R.lang_switch("en/" + rel, "en"), "html.parser"))
        STATS["lang-switch"] += 1

    head = soup.head
    if head is not None:
        for l in head.find_all("link", rel="alternate"):
            l.decompose()
        depth = rel.count("/")
        for code, href in (("en", os.path.basename(rel)),
                           ("it", "../" * (depth + 1) + rel),
                           ("x-default", "../" * (depth + 1) + rel)):
            tag = soup.new_tag("link", rel="alternate", href=href)
            tag["hreflang"] = code
            head.append(tag)

    # --- document-level ---------------------------------------------------- #
    html_el = soup.find("html")
    if html_el is not None:
        html_el["lang"] = "en"
        depth = rel.count("/")
        html_el["data-root"] = "../" * (depth + 1)     # site root from /en/…
        html_el["data-lang-root"] = "../" * depth      # English root
        html_el["data-search-index"] = "assets/search-index.en.json"

    # (stylesheet and script URLs were already handled by the pass above —
    #  rewriting them a second time would add a second "../")

    out = str(soup)
    if not out.startswith("<!DOCTYPE"):
        out = "<!DOCTYPE html>\n" + out.lstrip()
    dst = os.path.join(out_root, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8", newline="\n").write(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--map", required=True)
    a = ap.parse_args()
    site = os.path.abspath(a.site)
    mapping = json.load(open(a.map, encoding="utf-8"))

    pages = []
    for dirpath, dirnames, filenames in os.walk(site):
        dirnames[:] = [d for d in dirnames if d not in ("_dev", "en")]
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1].lower() in HTML_EXT:
                pages.append(os.path.relpath(os.path.join(dirpath, fn), site)
                             .replace(os.sep, "/"))
    pages.sort()
    pages_lower = {p.lower() for p in pages}

    out_root = os.path.join(site, "en")
    for rel in pages:
        translate_page(site, rel, mapping, pages_lower, out_root)

    print(f"english pages written: {len(pages)} -> {out_root}")
    for k in sorted(STATS):
        print(f"  {k:8s} {STATS[k]}")


if __name__ == "__main__":
    main()
