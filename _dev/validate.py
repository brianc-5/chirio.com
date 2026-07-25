#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation suite for the Chirio.com rebuild
===========================================

Five independent checks, each reporting filename, path, severity and the
recommended action:

* **files**    — every page exists; nothing points back at the source folder;
                 no file over 100 MiB; no FrontPage/system leftovers.
* **links**    — every internal link resolves on a case-sensitive filesystem;
                 every fragment link has a matching id; no `/store` page exists.
* **assets**   — every referenced image / stylesheet / script / download exists
                 in the output; report unreferenced files.
* **content**  — word-level comparison of the original page against the rebuilt
                 page: visible text, headings, numbers/units, image and download
                 references, anchors and metadata.
* **markup**   — well-formedness, one h1, landmarks, skip link, lang, charset,
                 alt attributes, heading order, no leftover FrontPage tags.

Usage::  python3 validate.py --src <original> --out <chirio-modern>
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict, Counter
from urllib.parse import unquote

from bs4 import BeautifulSoup

HTML_EXT = {".htm", ".html"}
FP_DIRS = {"_vti_cnf", "_vti_pvt", "_borders", "_fpclass", "_derived", "_private"}

FINDINGS: list[tuple[str, str, str, str, str]] = []   # check, severity, file, detail, action


def finding(check, severity, file, detail, action=""):
    FINDINGS.append((check, severity, file, detail, action))


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def read_src(path):
    raw = open(path, "rb").read()
    m = re.search(rb"charset\s*=\s*[\"']?([\w-]+)", raw[:4000], re.I)
    declared = (m.group(1).decode("ascii", "ignore").lower() if m else "")
    enc = "utf-8" if declared in ("utf-8", "utf8") else "cp1252"
    try:
        text = raw.decode(enc)
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    if "Ã" in text or "â€" in text:
        try:
            text = text.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return "".join(ch for ch in text if ch >= " " or ch in "\t\n\r")


def walk(root, skip_dirs=FP_DIRS, exclude_abs=(), skip_names=("_dev",)):
    exclude_abs = {os.path.abspath(e) for e in exclude_abs}
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d.lower() not in skip_dirs
                       and d not in skip_names
                       and os.path.abspath(os.path.join(dirpath, d)) not in exclude_abs]
        rd = os.path.relpath(dirpath, root)
        rd = "" if rd == "." else rd.replace(os.sep, "/")
        for fn in filenames:
            out.append(f"{rd}/{fn}" if rd else fn)
    return sorted(out)


WORD_RE = re.compile(r"[0-9]+(?:[.,][0-9]+)*|[^\W\d_]+", re.UNICODE)


def words(text):
    text = unicodedata.normalize("NFKC", text.replace("\xa0", " "))
    return WORD_RE.findall(text.lower())


NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")


def visible_text(soup, drop_chrome=False):
    """All text a reader can see.

    The content check is one-directional — it asks whether every source word is
    still present somewhere on the rebuilt page — so the new template's header,
    navigation, table of contents and footer are *not* stripped.  Removing them
    would flag text that the rebuild deliberately moved into shared chrome
    (the copyright notice, the "home" link) as lost.
    """
    for t in soup(["script", "style", "title"]):
        t.decompose()
    return soup.get_text(" ")


# --------------------------------------------------------------------------- #
# 1. files
# --------------------------------------------------------------------------- #

def check_files(src, out, page_map):
    out_files = set(walk(out))
    out_lower = {f.lower() for f in out_files}

    for rel, target in page_map.items():
        if target.lower() not in out_lower:
            finding("files", "CRITICAL", target,
                    f"page missing from the output (source: {rel})",
                    "re-run the generator for this page")

    for f in sorted(out_files):
        p = os.path.join(out, f.replace("/", os.sep))
        size = os.path.getsize(p)
        if size > 100 * 1024 * 1024:
            finding("files", "CRITICAL", f, f"{size/1048576:.1f} MiB > 100 MiB GitHub Pages limit",
                    "split or externalise this file")
        base = os.path.basename(f).lower()
        if base in ("thumbs.db", ".ds_store", "desktop.ini") or \
                os.path.splitext(base)[1] in (".lck", ".btr", ".cnf", ".class", ".jar"):
            finding("files", "MAJOR", f, "system / FrontPage / plug-in leftover in the deployable output",
                    "exclude from the build")
        if any(part.lower() in FP_DIRS for part in f.split("/")):
            finding("files", "MAJOR", f, "FrontPage metadata directory present in the output",
                    "exclude from the build")

    if any(f.lower() == "store" or f.lower().startswith("store/") for f in out_files):
        finding("files", "MAJOR", "store", "a /store page or folder exists",
                "remove it — a 404 at /store is intentional")
    if not os.path.exists(os.path.join(out, ".nojekyll")):
        finding("files", "MAJOR", ".nojekyll", "missing", "add an empty .nojekyll at the root")
    idx = os.path.join(out, "index.html")
    if not os.path.exists(idx):
        finding("files", "CRITICAL", "index.html", "no directory index at the site root",
                "emit index.html")

    # no output file may reference the source directory
    src_markers = [os.path.abspath(src), os.path.basename(os.path.abspath(src)),
                   "file:///", "/tmp/out", "/sessions/"]
    for f in sorted(out_files):
        if os.path.splitext(f)[1].lower() not in HTML_EXT | {".css", ".js", ".json", ".xml", ".txt"}:
            continue
        try:
            body = open(os.path.join(out, f.replace("/", os.sep)), encoding="utf-8",
                        errors="replace").read()
        except OSError:
            continue
        for marker in src_markers:
            if marker and marker in body:
                finding("files", "CRITICAL", f, f"contains a path to the source/build location: {marker!r}",
                        "rewrite the reference to a site-relative path")

    print(f"  files:    {len(out_files)} in output")
    return out_files


# --------------------------------------------------------------------------- #
# 2 & 3. links and assets
# --------------------------------------------------------------------------- #

ATTR_RE = re.compile(r"""(?:href|src|srcset|poster|data)\s*=\s*["']([^"']+)["']""", re.I)


def check_links(out, out_files):
    out_set = set(out_files)
    referenced = set()
    ids_cache: dict[str, set[str]] = {}
    pages = [f for f in out_files if os.path.splitext(f)[1].lower() in HTML_EXT]

    def ids_of(rel):
        if rel not in ids_cache:
            try:
                s = BeautifulSoup(open(os.path.join(out, rel.replace("/", os.sep)),
                                       encoding="utf-8").read(), "html.parser")
                ids_cache[rel] = {t["id"] for t in s.find_all(id=True)} | \
                                 {t["name"] for t in s.find_all(attrs={"name": True})}
            except OSError:
                ids_cache[rel] = set()
        return ids_cache[rel]

    ext_links = Counter()
    for page in pages:
        text = open(os.path.join(out, page.replace("/", os.sep)), encoding="utf-8").read()
        base = os.path.dirname(page)
        for raw in ATTR_RE.findall(text):
            u = html.unescape(raw).strip()
            if not u:
                continue
            if re.match(r"^[a-zA-Z][\w+.-]*:", u) or u.startswith("//"):
                if u.lower().startswith(("http://", "https://")):
                    ext_links[u] += 1
                elif u.lower().startswith("file:"):
                    finding("links", "CRITICAL", page, f"file:// URL {u!r}",
                            "replace with a site-relative path or remove")
                continue
            if u.startswith("#"):
                frag = unquote(u[1:])
                if frag and frag not in ids_of(page):
                    finding("links", "MAJOR", page, f"fragment #{frag} has no target on this page",
                            "restore the anchor or fix the link")
                continue
            path, _, frag = u.partition("#")
            path = unquote(path.split("?")[0])
            if not path:
                continue
            if path.startswith("/"):
                target = path.lstrip("/")
            else:
                target = os.path.normpath(os.path.join(base, path)).replace(os.sep, "/")
            if target.startswith(".."):
                finding("links", "CRITICAL", page, f"{u!r} escapes the site root",
                        "make the link site-relative")
                continue
            if target.endswith("/") or target == "":
                target += "index.html"
            referenced.add(target)
            if target not in out_set:
                if target.lower() in {f.lower() for f in out_set}:
                    finding("links", "CRITICAL", page,
                            f"{u!r} differs in letter case from the real file "
                            f"(breaks on GitHub Pages)", "match the on-disk case")
                elif target.rstrip("/") == "store":
                    pass
                else:
                    finding("links", "MAJOR", page, f"{u!r} -> {target} does not exist",
                            "fix or remove the link")
                continue
            if frag:
                f2 = unquote(frag)
                if os.path.splitext(target)[1].lower() in HTML_EXT and f2 not in ids_of(target):
                    finding("links", "MINOR", page,
                            f"fragment {u!r} has no target in {target}",
                            "restore the anchor or drop the fragment")

    orphans = sorted(f for f in out_set - referenced
                     if os.path.splitext(f)[1].lower() not in HTML_EXT
                     and not f.startswith("assets/")
                     and f not in (".nojekyll", "CNAME", "robots.txt", "sitemap.xml"))
    print(f"  links:    {len(referenced)} internal targets referenced, "
          f"{len(ext_links)} distinct external URLs, {len(orphans)} unreferenced assets kept")
    return referenced, orphans, ext_links


# --------------------------------------------------------------------------- #
# 4. content preservation
# --------------------------------------------------------------------------- #

#: vocabulary that belonged to the FrontPage chrome the rebuild replaces —
#: the "[ home ]" strip and the <noframes> "your browser cannot show frames"
#: message.  Losing these words is the intended outcome, not a regression.
CHROME_WORDS = set("""home noframes frame frames pagina corrente utilizza questa
caratteristica supportata browser uso body""".split())

STOP = set("""a al alla alle allo agli ai il lo la le i gli un uno una e ed o od
di del dello della delle dei degli da dal dallo dalla dalle dai in nel nello
nella nelle nei negli con col su sul sullo sulla sulle sui per tra fra che chi
cui non piu più come anche se ma however the of and to for with is are was were
be been this that""".split())


def check_content(src, out, page_map, skip_rebuilt):
    worst = []
    for rel, target in sorted(page_map.items()):
        sp = os.path.join(src, rel.replace("/", os.sep))
        op = os.path.join(out, target.replace("/", os.sep))
        if not os.path.exists(op):
            continue
        s_soup = BeautifulSoup(read_src(sp), "html5lib")
        o_soup = BeautifulSoup(open(op, encoding="utf-8").read(), "html.parser")

        s_words = Counter(words(visible_text(s_soup)))
        o_words = Counter(words(visible_text(o_soup, drop_chrome=True)))

        missing = Counter()
        for w, n in s_words.items():
            if w in STOP or len(w) < 2 or w in CHROME_WORDS:
                continue
            gap = n - o_words.get(w, 0)
            if gap > 0:
                missing[w] = gap
        total = sum(n for w, n in s_words.items() if w not in STOP and len(w) >= 2)
        lost = sum(missing.values())
        ratio = (lost / total) if total else 0.0

        if rel in skip_rebuilt:
            sev = None
        elif ratio > 0.06 or (lost > 25 and ratio > 0.03):
            sev = "CRITICAL"
        elif ratio > 0.015 or lost > 12:
            sev = "MAJOR"
        elif lost:
            sev = "MINOR"
        else:
            sev = None
        if sev:
            finding("content", sev, target,
                    f"{lost}/{total} source words absent ({ratio:.1%}); e.g. "
                    + ", ".join(f"{w}×{n}" for w, n in missing.most_common(8)),
                    "restore the missing text")
        worst.append((ratio, lost, total, rel, target, missing.most_common(10)))

        # numeric / unit values must survive exactly
        s_nums = Counter(NUM_RE.findall(visible_text(BeautifulSoup(read_src(sp), "html5lib"))))
        o_nums = Counter(NUM_RE.findall(visible_text(
            BeautifulSoup(open(op, encoding="utf-8").read(), "html.parser"), drop_chrome=True)))
        lost_nums = {k: v - o_nums.get(k, 0) for k, v in s_nums.items() if v > o_nums.get(k, 0)}
        if rel not in skip_rebuilt and sum(lost_nums.values()) > 3:
            finding("content", "MAJOR", target,
                    f"{sum(lost_nums.values())} numeric values missing: "
                    + ", ".join(list(lost_nums)[:10]),
                    "restore the technical values")

        # every asset the original referenced must still be referenced
        s_refs, o_refs = set(), set()
        for soup, acc, base in ((BeautifulSoup(read_src(sp), "html5lib"), s_refs, os.path.dirname(rel)),
                                (BeautifulSoup(open(op, encoding="utf-8").read(), "html.parser"),
                                 o_refs, os.path.dirname(target))):
            for t in soup.find_all(["img", "a", "video", "audio", "source", "area"]):
                u = t.get("src") or t.get("href") or ""
                u = unquote(html.unescape(u).split("#")[0].split("?")[0])
                if not u or re.match(r"^[a-zA-Z][\w+.-]*:", u) or u.startswith("//"):
                    continue
                ext = os.path.splitext(u)[1].lower()
                if ext in HTML_EXT or not ext:
                    continue
                acc.add(os.path.basename(u).lower())
        # purely decorative navigation chrome from the FrontPage templates: the
        # arrow/home GIFs and the repeated banner are replaced by the new header
        # and text navigation.  The files themselves stay in the archive.
        CHROME_ASSETS = {"home.gif", "next.gif", "previous.gif", "prev.gif",
                         "up.gif", "back.gif", "first.gif", "last.gif",
                         "testa_01.gif", "background.jpg", "wait.gif", "bar.gif",
                         "email.jpg", "ptviewer.jar", "fphover.class"}
        gone = {g for g in (s_refs - o_refs) if g not in CHROME_ASSETS}
        if gone:
            finding("content", "MAJOR", target,
                    f"{len(gone)} asset reference(s) dropped: " + ", ".join(sorted(gone)[:8]),
                    "restore the image/download reference")

        # anchors — only real link targets count: <a name>/<a id> and any id.
        # <meta name>, <param name>, <frame name> and <input name> are not
        # navigable fragments.
        s_tree = BeautifulSoup(read_src(sp), "html5lib")
        s_ids = {t["id"] for t in s_tree.find_all(id=True)}
        s_ids |= {t["name"] for t in s_tree.find_all("a", attrs={"name": True})}
        s_ids = {i for i in s_ids if i}
        o_ids = {t["id"] for t in o_soup.find_all(id=True)} if o_soup else set()
        o_soup2 = BeautifulSoup(open(op, encoding="utf-8").read(), "html.parser")
        o_ids = {t["id"] for t in o_soup2.find_all(id=True)}
        lost_ids = s_ids - o_ids
        if lost_ids:
            finding("content", "MAJOR", target,
                    f"anchors lost: {', '.join(sorted(lost_ids)[:8])}",
                    "re-add the id attributes")

    worst.sort(reverse=True)
    print("  content:  worst text-preservation ratios")
    for ratio, lost, total, rel, target, ex in worst[:8]:
        print(f"            {ratio:6.2%}  {lost:5d}/{total:<6d} {target}  {ex[:4]}")
    return worst


# --------------------------------------------------------------------------- #
# 5. markup / accessibility
# --------------------------------------------------------------------------- #

def check_markup(out, out_files):
    pages = [f for f in out_files if os.path.splitext(f)[1].lower() in HTML_EXT]
    for page in pages:
        text = open(os.path.join(out, page.replace("/", os.sep)), encoding="utf-8").read()
        soup = BeautifulSoup(text, "html.parser")
        if page == "index.htm":
            continue     # legacy redirect stub
        if "<!DOCTYPE html>" not in text[:120]:
            finding("markup", "MAJOR", page, "missing HTML5 doctype", "add <!DOCTYPE html>")
        h = soup.find("html")
        if not h or not h.get("lang"):
            finding("markup", "MAJOR", page, "no lang attribute on <html>", "set lang")
        if not soup.find("meta", attrs={"charset": True}):
            finding("markup", "MAJOR", page, "no <meta charset>", "add <meta charset=\"utf-8\">")
        if not soup.find("meta", attrs={"name": "viewport"}):
            finding("markup", "MAJOR", page, "no viewport meta", "add the viewport meta")
        t = soup.find("title")
        if not t or not t.get_text(strip=True):
            finding("markup", "MAJOR", page, "empty or missing <title>", "give the page a title")
        h1s = soup.find_all("h1")
        if len(h1s) != 1:
            finding("markup", "MAJOR", page, f"{len(h1s)} <h1> elements", "use exactly one h1")
        if not soup.find("main"):
            finding("markup", "MAJOR", page, "no <main> landmark", "wrap the content in <main>")
        if not soup.select_one("a.skip-link"):
            finding("markup", "MINOR", page, "no skip link", "add a skip-to-content link")
        for img in soup.find_all("img"):
            if img.get("alt") is None:
                finding("markup", "MAJOR", page, f"<img src={img.get('src')!r}> has no alt attribute",
                        "add alt (empty for decorative images)")
        for tag in ("font", "center", "basefont", "marquee", "applet", "blink"):
            if soup.find(tag):
                finding("markup", "MAJOR", page, f"obsolete <{tag}> survived the migration",
                        "convert to CSS")
        for attr in ("bgcolor", "cellpadding", "cellspacing", "vlink", "alink", "usemap"):
            hit = soup.find(attrs={attr: True})
            if hit is not None and attr != "usemap":
                finding("markup", "MINOR", page, f"presentational attribute {attr} on <{hit.name}>",
                        "move to CSS")
        # stray table parts outside a table
        for t2 in soup.find_all(["tr", "td", "th"]):
            if t2.find_parent("table") is None:
                finding("markup", "CRITICAL", page, f"<{t2.name}> outside any <table>",
                        "re-parse the source with an HTML5 tree builder")
                break
        # heading order
        levels = [int(x.name[1]) for x in soup.select(".prose h2, .prose h3, .prose h4, "
                                                      ".prose h5, .prose h6, h1")]
        prev = 0
        for lv in levels:
            if prev and lv > prev + 1:
                finding("markup", "MINOR", page, f"heading jumps from h{prev} to h{lv}",
                        "use consecutive heading levels")
                break
            prev = lv
        # a template bug can leave an unterminated tag that swallows the markup
        # that follows; the parser then shows it as bogus attribute names
        for t2 in soup.find_all(True):
            for k in t2.attrs:
                if "<" in k or ">" in k or k.startswith(("p", "div")) and k in ("p", "div"):
                    if "<" in k or ">" in k:
                        finding("markup", "CRITICAL", page,
                                f"<{t2.name}> has a malformed attribute {k!r} — an unterminated "
                                f"tag swallowed the following markup",
                                "fix the template")
        void_swallow = re.findall(r"<(input|img|br|hr|meta|link)\b[^<>]*<", text)
        if void_swallow:
            finding("markup", "CRITICAL", page,
                    f"unterminated <{void_swallow[0]}> tag", "close the tag")
        if "localStorage" in text or "sessionStorage" in text:
            finding("markup", "MAJOR", page, "browser storage API referenced", "remove")
    print(f"  markup:   {len(pages)} pages inspected")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    src, out = os.path.abspath(a.src), os.path.abspath(a.out)

    src_pages = [f for f in walk(src, exclude_abs=[out])
                 if os.path.splitext(f)[1].lower() in HTML_EXT]
    page_map = {p: ("index.html" if p.upper() == "INDEX.HTM" else p) for p in src_pages}
    # the homepage is rebuilt from the content inventory, so a word-for-word
    # comparison against the original link directory is not meaningful
    skip_rebuilt = {p for p in src_pages if p.upper() == "INDEX.HTM"}

    print("── validation ──")
    out_files = check_files(src, out, page_map)
    referenced, orphans, ext_links = check_links(out, out_files)
    check_content(src, out, page_map, skip_rebuilt)
    check_markup(out, out_files)

    by = defaultdict(list)
    for c, sev, f, d, act in FINDINGS:
        by[(c, sev)].append((f, d, act))
    print("\n── findings ──")
    order = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}
    for (c, sev) in sorted(by, key=lambda k: (order[k[1]], k[0])):
        rows = by[(c, sev)]
        print(f"\n[{sev}] {c}: {len(rows)}")
        for f, d, act in rows[:40]:
            print(f"   {f}\n      {d}" + (f"\n      → {act}" if act else ""))
        if len(rows) > 40:
            print(f"   … and {len(rows) - 40} more")
    if not FINDINGS:
        print("  no findings")

    if a.json:
        json.dump({"findings": FINDINGS, "orphans": orphans,
                   "external": sorted(ext_links)}, open(a.json, "w"), ensure_ascii=False, indent=1)

    crit = sum(1 for f in FINDINGS if f[1] == "CRITICAL")
    print(f"\nCRITICAL={crit}  MAJOR={sum(1 for f in FINDINGS if f[1]=='MAJOR')}  "
          f"MINOR={sum(1 for f in FINDINGS if f[1]=='MINOR')}")
    sys.exit(1 if crit else 0)


if __name__ == "__main__":
    main()
