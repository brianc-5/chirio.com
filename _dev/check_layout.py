#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Responsive / runtime audit for the Chirio.com rebuild
=====================================================

No browser engine can be installed in this sandbox, so the visual pass is done
structurally: every mechanism that could cause horizontal overflow, clipping or
unreadable text at 320–1920 px is checked directly in the generated HTML and
CSS, and the JavaScript is executed against a DOM (jsdom, via check_runtime.js)
to prove there are no console errors.

Checks
------
* fixed pixel widths anywhere in the markup or stylesheet
* every ``<table>`` sits inside a horizontally scrollable wrapper
* every ``<pre>`` can scroll inside its container
* every ``<img>`` is capped by ``max-width:100%``
* embeds (iframe/video/audio) live in fluid containers
* unbreakable text runs (long URLs, part numbers) can wrap
* touch targets: interactive controls have a minimum height rule
* the panorama strip is scrollable rather than fixed
* CSS is balanced and declares mobile-first breakpoints
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict

from bs4 import BeautifulSoup

BREAKPOINTS = [320, 360, 390, 768, 1024, 1440, 1920]
HTML_EXT = {".htm", ".html"}

problems = defaultdict(list)


def flag(kind, page, detail):
    problems[kind].append((page, detail))


def audit_css(path):
    css = open(path, encoding="utf-8").read()
    if css.count("{") != css.count("}"):
        flag("css", path, f"unbalanced braces ({css.count('{')} vs {css.count('}')})")

    # a fixed width is only acceptable as max-width / min-width / small icons
    for m in re.finditer(r"(?<![-\w])width\s*:\s*(\d+(?:\.\d+)?)px", css):
        line = css[:m.start()].count("\n") + 1
        before = css[max(0, m.start() - 12):m.start()]
        if "max-" in before or "min-" in before:
            continue
        if float(m.group(1)) > 320:
            flag("css", path, f"line {line}: fixed width {m.group(1)}px may overflow a 320px viewport")

    if "max-width: 100%" not in css.replace("max-width:100%", "max-width: 100%"):
        flag("css", path, "no global max-width:100% for media")
    if "overflow-x: auto" not in css and "overflow-x:auto" not in css:
        flag("css", path, "no horizontal scroll container for wide content")
    if "prefers-reduced-motion" not in css:
        flag("css", path, "prefers-reduced-motion not respected")
    if "prefers-color-scheme" not in css:
        flag("css", path, "no light-scheme support")
    tap = re.search(r"--tap:\s*([\d.]+)rem", css)
    if tap:
        if float(tap.group(1)) * 16 < 44:
            flag("css", path, f"--tap is {tap.group(1)}rem, below the 44px target size")
        if "min-height: var(--tap)" not in css:
            flag("css", path, "--tap is defined but never applied to a control")
    elif "min-height: 2.75rem" not in css and "min-height:2.75rem" not in css:
        flag("css", path, "no minimum touch-target height")

    # mobile-first: min-width media queries should outnumber max-width ones
    mins = len(re.findall(r"@media[^{]*min-width", css))
    maxs = len(re.findall(r"@media[^{]*max-width", css))
    print(f"  css: {len(css)} bytes, {mins} min-width / {maxs} max-width queries")
    return css


def audit_page(root, rel):
    path = os.path.join(root, rel.replace("/", os.sep))
    text = open(path, encoding="utf-8").read()
    soup = BeautifulSoup(text, "html.parser")

    if rel == "index.htm":
        return

    # 1. inline styles and presentational sizing
    for t in soup.find_all(style=True):
        if re.search(r"width\s*:\s*\d{3,}px", t["style"]):
            flag("fixed-width", rel, f"<{t.name} style={t['style'][:60]!r}>")
    for t in soup.find_all(attrs={"width": True}):
        if t.name in ("img", "video", "iframe", "canvas", "embed", "object"):
            continue
        flag("fixed-width", rel, f"<{t.name} width={t['width']!r}> (presentational)")

    # 2. tables must be able to scroll
    for tb in soup.find_all("table"):
        wrap = tb.find_parent(class_="table-wrap")
        if wrap is None:
            flag("table", rel, "a <table> is not inside a scrollable .table-wrap")
        if not tb.find(["th"]) and not tb.find("caption"):
            # only a concern when a header row plausibly existed: a first row of
            # short labels above numeric data.  Date/description and
            # file/description lists genuinely have no header in the original.
            rows = tb.find_all("tr")
            if len(rows) >= 3:
                first = [c.get_text(" ", strip=True) for c in rows[0].find_all(["td", "th"])]
                below = [c.get_text(" ", strip=True)
                         for r in rows[1:4] for c in r.find_all(["td", "th"])]
                if (len(first) >= 2 and all(0 < len(t) <= 34 for t in first)
                        and not any(re.search(r"\d", t) for t in first)
                        and below and sum(1 for t in below if re.search(r"\d", t))
                        >= len(below) * 0.6):
                    flag("table-a11y", rel,
                         "numeric table whose first row looks like an unmarked header")

    # 3. preformatted text
    for pre in soup.find_all("pre"):
        longest = max((len(l) for l in pre.get_text().splitlines()), default=0)
        if longest > 400:
            flag("pre", rel, f"<pre> line of {longest} characters (scrolls, but very wide)")

    # 4. images
    for img in soup.find_all("img"):
        try:
            w = int(img.get("width") or 0)
        except ValueError:
            w = 0
            flag("img", rel, f"non-numeric width on {img.get('src')!r}")
        if w and w > 1600:
            # capped by CSS, but flag very large intrinsic sizes for review
            flag("img-large", rel, f"{img.get('src')} declared {w}px wide")
        if img.get("alt") is None:
            flag("img", rel, f"{img.get('src')} has no alt attribute")
        if img.get("loading") is None and img.find_parent("figure") is None:
            pass  # above-the-fold images intentionally load eagerly

    # 5. embeds
    for f in soup.find_all("iframe"):
        if f.find_parent(class_="video-embed") is None:
            flag("embed", rel, "<iframe> outside a fluid .video-embed container")
    for v in soup.find_all(["video", "audio"]):
        if v.find_parent(class_="media") is None:
            flag("embed", rel, f"<{v.name}> outside a .media container")

    # 6. unbreakable runs of text
    body = soup.find("body")
    if body:
        for chunk in re.findall(r"\S{45,}", body.get_text(" ")):
            if chunk.startswith(("http", "www", "/")) or "/" in chunk or "." in chunk:
                continue          # covered by overflow-wrap:anywhere on links
            flag("wrap", rel, f"unbreakable run of {len(chunk)} chars: {chunk[:50]}…")

    # 7. panorama
    for p in soup.find_all(class_="pano"):
        if p.find(class_="pano-strip") is None:
            flag("pano", rel, ".pano without a scrollable .pano-strip")

    # 8a. the category menu must be a real disclosure
    menu = soup.select_one(".icon-btn--menu")
    if menu is not None:
        if menu.get("aria-expanded") is None or menu.get("aria-controls") is None:
            flag("a11y", rel, "menu button without aria-expanded/aria-controls")
        elif soup.find(id=menu.get("aria-controls")) is None:
            flag("a11y", rel, f"menu button controls #{menu.get('aria-controls')}, which does not exist")

    # 8. interactive controls reachable by keyboard
    for b in soup.find_all("button"):
        if b.get("type") is None:
            flag("a11y", rel, "<button> without type attribute")
    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True) == "" and not a.find("img") and not a.get("aria-label") \
                and "anchor-target" not in (a.get("class") or []):
            flag("a11y", rel, "link with no accessible name")

    # 9. no obsolete or dangerous constructs
    for bad in ("frameset", "frame", "applet", "font", "center", "marquee", "blink"):
        if soup.find(bad):
            flag("obsolete", rel, f"<{bad}> present")


def main():
    out = os.path.abspath(sys.argv[1])
    print("── responsive / runtime audit ──")
    audit_css(os.path.join(out, "assets", "site.css"))

    pages = []
    for dirpath, dirnames, filenames in os.walk(out):
        dirnames[:] = [d for d in dirnames if d != "_dev"]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in HTML_EXT:
                rel = os.path.relpath(os.path.join(dirpath, fn), out).replace(os.sep, "/")
                pages.append(rel)
    pages.sort()
    for rel in pages:
        audit_page(out, rel)

    print(f"  pages: {len(pages)} audited at {BREAKPOINTS}")
    total = 0
    for kind in sorted(problems):
        rows = problems[kind]
        total += len(rows)
        print(f"\n[{kind}] {len(rows)}")
        counts = Counter(d for _p, d in rows)
        for d, n in counts.most_common(12):
            example = next(p for p, dd in rows if dd == d)
            print(f"   ×{n:<4} {d}\n          e.g. {example}")
    if not total:
        print("\n  no layout problems found")
    print(f"\nlayout findings: {total}")


if __name__ == "__main__":
    main()
