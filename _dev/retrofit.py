#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-time retrofit: apply the redesign to the generated baseline
===============================================================

The generated HTML — not ``_dev/build.py`` — is now the canonical source for
the public pages. This script performs the *single* reviewed, repetitive pass
that carries every page from the old generated chrome onto the new design
system, and then retires itself.

What it changes
---------------
Shared chrome (all pages)
  * new header: one wordmark, search affordance, category menu with counts
  * new footer: condensed identity/contact, categories, Chaberton, legal
  * ``assets/site.css`` / ``assets/site.js`` class contracts

Article bodies (reviewed, mechanical, meaning-preserving)
  * removes the leftover ``[ home ]`` strips the generator failed to drop
    (a variable-shadowing bug in ``Transformer._drop_nav_lines``)
  * turns runs of ``- item`` paragraphs into real ``<ul class="dash-list">``
  * collapses FrontPage runs of four or more spaces inside text
  * shortens over-long table-of-contents labels, keeping the full heading text
    as the link's ``title``
  * tags images as photograph or diagram so line art keeps a light plate in
    dark mode
  * removes the ``email.jpg`` raster from the interface

What it does NOT do
-------------------
It never rewrites prose, never invents metadata, and never touches a page
listed in ``_dev/curated.txt`` — those have been revised by hand.

Usage::

    python3 retrofit.py --site <dir> [--check]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

from bs4 import BeautifulSoup, NavigableString

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "_dev"))

STATS = Counter()
NOTES = []

EMAIL = "info@chirio.com"

BRAND_MARK = (
    '<svg class="brand-mark" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round" aria-hidden="true" focusable="false">'
    '<path d="M12 21V9"/><circle cx="12" cy="6.5" r="2.2"/>'
    '<path d="M6.6 4.2a7.6 7.6 0 0 0 0 10.6M17.4 4.2a7.6 7.6 0 0 1 0 10.6"/>'
    '<path d="M8.9 6.6a3.5 3.5 0 0 0 0 5.8M15.1 6.6a3.5 3.5 0 0 1 0 5.8"/>'
    '<path d="M8.5 21h7"/></svg>'
)

ICON_SEARCH = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
               'stroke-linecap="round" aria-hidden="true" focusable="false">'
               '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/></svg>')
ICON_MENU = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round" aria-hidden="true" focusable="false">'
             '<path d="M4 7h16M4 12h16M4 17h16"/></svg>')


def lang_switch(rel, current="it"):
    """IT / EN switch, top right of every page.

    The English mirror has the same shape as the Italian tree, so the
    counterpart of any page is the same relative path under /en/.
    """
    depth = rel.count("/")
    if current == "it":
        it_href, en_href = "", "../" * depth + "en/" + rel
    else:
        inner = rel[len("en/"):] if rel.startswith("en/") else rel
        depth = inner.count("/")
        it_href, en_href = "../" * (depth + 1) + inner, ""

    def item(code, label, href, is_current):
        if is_current:
            return (f'<span class="lang-current" lang="{code}" aria-current="true">'
                    f'{label}</span>')
        return (f'<a href="{href}" lang="{code}" hreflang="{code}">{label}</a>')

    return ('<div class="lang-switch">'
            '<span class="visually-hidden" id="lang-label">Lingua / Language</span>'
            '<div class="lang-group" role="group" aria-labelledby="lang-label">'
            + item("it", "IT", it_href, current == "it")
            + item("en", "EN", en_href, current == "en")
            + '</div></div>')

#: one-line descriptions shown in the mobile category menu
NAV_DESC = {
    "radio": "Antenne attive, generatori RF, misure di campo",
    "alimentatori": "Switching da laboratorio, ATX, step-up, carichi",
    "batterie": "Capacità, caricabatterie, BMS, energia in casa",
    "led": "LED di potenza, torce, proiettori, dimmer, prove",
    "radioattivita": "Contatori Geiger, alta tensione, calibrazione",
    "misure": "Strumenti autocostruiti e fondamenti",
    "progetti": "Fotografia, stampa 3D, meccanica",
}


def note(kind, msg):
    NOTES.append((kind, msg))
    STATS[kind] += 1


# --------------------------------------------------------------------------- #
# shared chrome
# --------------------------------------------------------------------------- #

def build_header(root, meta, section=None, chaberton=False, chab_prefix="",
                 rel="index.html", lang="it", switch=True):
    if chaberton:
        brand = (f'<a class="brand" href="{chab_prefix}chab.htm">{BRAND_MARK}'
                 f'<span class="brand-text"><span class="brand-name">Chaberton</span>'
                 f'<span class="brand-sub">Archivio storico · Chirio.com</span></span></a>')
        items = [f'<li><a href="{root}index.html"><span class="n-label">Chirio.com</span>'
                 f'<span class="n-desc">Archivio tecnico di elettronica e radio</span></a></li>']
        for href, label in meta.CHAB_NAV[1:]:
            items.append(f'<li><a href="{chab_prefix}{href}">'
                         f'<span class="n-label">{label}</span></a></li>')
    else:
        brand = (f'<a class="brand" href="{root}index.html">{BRAND_MARK}'
                 f'<span class="brand-text"><span class="brand-name">Chirio<i>.com</i></span>'
                 f'<span class="brand-sub">Archivio tecnico</span></span></a>')
        counts = Counter(meta.PAGE_SECTION.values())
        items = []
        for slug, label, _h, _d in meta.SECTIONS:
            cur = ' aria-current="true"' if slug == section else ""
            items.append(
                f'<li><a href="{root}index.html#{slug}"{cur}>'
                f'<span><span class="n-label">{meta.NAV_SHORT.get(slug, label)}</span>'
                f'<span class="n-desc">{NAV_DESC.get(slug, "")}</span></span>'
                f'<span class="count">{counts[slug]}</span></a></li>')
        items.append(f'<li><a href="{root}chaberton/chab.htm">'
                     f'<span><span class="n-label">Chaberton</span>'
                     f'<span class="n-desc">Archivio storico della Batteria</span></span>'
                     f'<span class="count">{meta.CHAB_COUNT}</span></a></li>')

    return f'''<header class="site-header">
  <div class="wrap header-bar">
    {brand}
    <a class="icon-btn icon-btn--search" href="{root}index.html#cerca">{ICON_SEARCH}<span class="visually-hidden">Cerca nell’archivio</span></a>
    <button class="icon-btn icon-btn--menu" type="button" aria-expanded="false" aria-controls="site-nav">{ICON_MENU}<span class="btn-label">Categorie</span></button>
    {lang_switch(rel, lang) if switch else ""}
  </div>
  <div class="nav-panel" id="site-nav">
    <div class="wrap">
      <nav aria-label="Categorie dell’archivio">
        <ul class="nav-list">
{chr(10).join("          " + i for i in items)}
        </ul>
      </nav>
    </div>
  </div>
</header>'''


def build_footer(root, meta, chaberton=False):
    cats = "\n".join(
        f'          <li><a href="{root}index.html#{slug}">{meta.NAV_SHORT.get(slug, label)}</a></li>'
        for slug, label, _h, _d in meta.SECTIONS)
    chab = "\n".join(
        f'          <li><a href="{root}chaberton/{href}">{label}</a></li>'
        for href, label in meta.CHAB_NAV[1:6])
    return f'''<footer class="site-footer">
  <div class="wrap">
    <div class="footer-top">
      <div class="footer-id">
        <p class="footer-name">Chirio.com</p>
        <p>Archivio tecnico di Roberto Chirio: elettronica, radio e antenne,
          alimentatori, batterie, illuminazione a LED, misure di laboratorio, e
          l’archivio storico della Batteria dello Chaberton.</p>
        <p><a href="mailto:{EMAIL}">{EMAIL}</a></p>
      </div>
      <div class="footer-nav">
        <h2>Archivio</h2>
        <ul>
{cats}
          <li><a href="{root}chaberton/chab.htm">Chaberton</a></li>
{chab}
        </ul>
      </div>
    </div>
    <div class="footer-legal">
      <p>È vietato ogni utilizzo non autorizzato delle foto, dei video, delle
        immagini, degli schemi e dei testi. Photos and videos are copyright
        © Roberto Chirio: all rights reserved.</p>
      <p><a href="{root}chirio_com_privacy.htm">Privacy</a> ·
         <a href="{root}chirio_com_disclaimer.htm">Disclaimer</a></p>
    </div>
  </div>
  <button class="to-top" type="button" aria-label="Torna all’inizio della pagina">↑</button>
</footer>'''


# --------------------------------------------------------------------------- #
# article-body cleanups
# --------------------------------------------------------------------------- #

DASH_RE = re.compile(r"^\s*[-–—•]\s*(?=\S)")
DIAGRAM_HINT = re.compile(
    r"(schema|schemi|sch_|circuit|diagram|grafic|graph|curve|plot|teoria|"
    r"legge_di_ohm|_sh_|layout|pcb_top|pinout|tabella)", re.I)


def strip_home_strips(prose, rel):
    """Remove the ``[ home ]`` strips the generator left behind.

    Deliberately conservative. A block only qualifies when *every* link is a
    relative link that resolves to one of the site-level pages, the text is
    bracketed, and nothing but punctuation sits around the link labels. Matching
    on the file name alone would delete any paragraph holding an external URL
    that happens to end in ``index.htm``; comparing resolved paths does not.
    """
    CHROME = {"index.html", "index.htm", "chab.htm",
              "chirio_com_privacy.htm", "chirio_com_disclaimer.htm"}
    page_dir = os.path.dirname(rel)
    n = 0
    for el in list(prose.find_all(["p", "div"])):
        if el.decomposed or el.parent is None:
            continue
        links = el.find_all("a", href=True)
        if not links or el.find(["img", "table", "video", "iframe"]):
            continue
        text = re.sub(r"\s+", " ", el.get_text(" ")).strip()
        if len(text) > 80 or "[" not in text:
            continue

        ok = True
        for a in links:
            href = a["href"].strip()
            if re.match(r"^[a-zA-Z][\w+.-]*:", href) or href.startswith("//"):
                ok = False        # external, mailto, tel: never chrome
                break
            target = os.path.normpath(os.path.join(page_dir, href.split("#")[0]))
            if target.replace(os.sep, "/") not in CHROME:
                ok = False
                break
        if not ok:
            continue

        outside = text
        for a in links:
            t = re.sub(r"\s+", " ", a.get_text(" ")).strip()
            if t:
                outside = outside.replace(t, " ", 1)
        if outside.strip() and re.fullmatch(r"[\s\[\]()·|,;:/]*", outside):
            el.decompose()
            n += 1
    if n:
        note("home-strip", f"{rel}: removed {n} redundant “[ home ]” strip(s)")
    return n


def dash_runs_to_lists(prose, rel):
    """A run of two or more ``- item`` paragraphs is a list the author typed
    before lists were convenient. Converting is meaning-preserving."""
    soup = BeautifulSoup("", "html.parser")
    made = 0
    container_stack = [prose]
    for container in container_stack:
        kids = [k for k in container.children if getattr(k, "name", None)]
        run = []
        def flush(run):
            nonlocal made
            if len(run) < 2:
                return
            ul = soup.new_tag("ul")
            ul["class"] = ["dash-list"]
            for p in run:
                li = soup.new_tag("li")
                for c in list(p.contents):
                    li.append(c.extract())
                # strip the leading dash from the first text node
                first = li.find(string=True)
                if first is not None:
                    new = DASH_RE.sub("", str(first), count=1)
                    if new != str(first):
                        first.replace_with(NavigableString(new))
                ul.append(li)
            run[0].insert_before(ul)
            for p in run:
                p.decompose()
            made += 1
        for el in kids:
            if el.name == "p" and not el.find(["img", "table", "br"]):
                t = re.sub(r"\s+", " ", el.get_text(" ")).strip()
                if DASH_RE.match(t) and 2 < len(t) < 400:
                    run.append(el)
                    continue
            flush(run)
            run = []
        flush(run)
    if made:
        note("dash-list", f"{rel}: {made} paragraph run(s) became lists")
    return made


def collapse_spaces(prose, rel):
    n = 0
    for node in list(prose.find_all(string=True)):
        if node.parent.name in ("pre", "code", "samp", "kbd"):
            continue
        s = str(node)
        new = re.sub(r"[ \t ]{3,}", " ", s)
        new = re.sub(r"\n[ \t]+", "\n", new)
        if new != s:
            node.replace_with(NavigableString(new))
            n += 1
    if n:
        STATS["space-collapse"] += 1
    return n


def tag_media(prose, rel, site_dir, page_dir):
    """Photographs and line art need different treatment: a schematic on a dark
    page must keep a light plate or it becomes unreadable."""
    photo = diagram = 0
    for img in prose.find_all("img"):
        src = (img.get("src") or "")
        if not src:
            continue
        classes = img.get("class", [])
        if "is-photo" in classes or "is-diagram" in classes:
            continue
        ext = os.path.splitext(src.split("?")[0])[1].lower()
        looks_line_art = ext in (".gif", ".png") or bool(DIAGRAM_HINT.search(src))
        if looks_line_art:
            img["class"] = classes + ["is-diagram"]
            diagram += 1
        else:
            img["class"] = classes + ["is-photo"]
            photo += 1
    STATS["img-photo"] += photo
    STATS["img-diagram"] += diagram
    return photo, diagram


def shorten(label, limit=52):
    label = re.sub(r"\s+", " ", label).strip()
    if len(label) <= limit:
        return label
    cut = label[:limit]
    for sep in (". ", " — ", " – ", ", ", " ("):
        i = cut.rfind(sep)
        if i > limit * 0.45:
            return cut[:i].rstrip(" ,–—(")
    i = cut.rfind(" ")
    return (cut[:i] if i > limit * 0.5 else cut).rstrip(" ,–—(") + "…"


def curate_toc(soup, rel):
    changed = 0
    for a in soup.select(".toc a"):
        full = re.sub(r"\s+", " ", a.get_text(" ")).strip()
        short = shorten(full)
        if short != full:
            a.string = short
            a["title"] = full
            changed += 1
    if changed:
        note("toc", f"{rel}: shortened {changed} table-of-contents label(s)")
    return changed


def drop_email_image(soup, rel):
    n = 0
    for img in list(soup.find_all("img", src=True)):
        if "email.jpg" not in img["src"].lower():
            continue
        link = soup.new_tag("a", href=f"mailto:{EMAIL}")
        link.string = EMAIL
        holder = img.parent
        img.replace_with(link)
        if holder is not None and holder.name == "a":
            holder.unwrap()
        n += 1
    if n:
        note("email", f"{rel}: replaced the e-mail raster with a mailto link")
    return n


# --------------------------------------------------------------------------- #
# metadata, typography and alignment
# --------------------------------------------------------------------------- #

COLUMN_RE = re.compile(r'^\s*[“"]?\s*(.+?)\s*["”]?\s*(?:di\s*R\.?\s*Chirio\.?)?\s*$', re.I)


def tidy_meta(soup, rel):
    """The generator sometimes emitted the column name and the author twice —
    “Radio Corner" di R.Chirio” di R. Chirio. Keep one clean rendering."""
    meta_el = soup.select_one(".article-meta")
    if meta_el is None:
        return 0
    seen, fixed = [], 0
    for sp in list(meta_el.find_all("span", recursive=False)):
        txt = re.sub(r"\s+", " ", sp.get_text(" ")).strip()
        if "corner" in txt.lower():
            # The source wrote the column name with mismatched quotes and then
            # repeated the author: 〈Radio Corner" di R.Chirio〉 di R. Chirio.
            # Normalise to one clean rendering; safe to re-run.
            name = re.sub(r"\s*di\s*R\.?\s*Chirio\.?", " ", txt, flags=re.I)
            name = re.sub(r"\brubrica\b", " ", name, flags=re.I)
            name = re.sub(r"[\"“”'']", " ", name)
            name = re.sub(r"\s+", " ", name).strip()
            want = f"rubrica \u201c{name}\u201d"
            if name and txt != want:
                sp.string = want
                fixed += 1
                txt = want
        key = re.sub(r"[^a-z0-9]+", "", txt.lower())
        if key and key in seen:
            sp.decompose()
            fixed += 1
            continue
        seen.append(key)
    if fixed:
        note("meta", f"{rel}: tidied {fixed} metadata item(s)")
    return fixed


def tidy_breadcrumb(soup, rel):
    ol = soup.select_one(".breadcrumb ol")
    if ol is None:
        return 0
    items = ol.find_all("li", recursive=False)
    n = 0
    for i in range(len(items) - 1, 0, -1):
        a = re.sub(r"\s+", " ", items[i].get_text(" ")).strip().lower()
        b = re.sub(r"\s+", " ", items[i - 1].get_text(" ")).strip().lower()
        if a and a == b:
            items[i].decompose()
            n += 1
    if n:
        note("breadcrumb", f"{rel}: removed {n} duplicated crumb(s)")
    return n


#: unit spellings only — never a value. "10khz" -> "10 kHz", "2700Mhz" -> "2700 MHz".
UNIT_FIXES = [
    (re.compile(r"(?<=\d)\s*(?:khz|kHz|Khz|KHz|KHZ)\b"), " kHz"),
    (re.compile(r"(?<=\d)\s*(?:mhz|Mhz|MHz|MHZ)\b"), " MHz"),
    (re.compile(r"(?<=\d)\s*(?:ghz|Ghz|GHz|GHZ)\b"), " GHz"),
    (re.compile(r"(?<=\d)\s*(?:hz|Hz|HZ)\b"), " Hz"),
    (re.compile(r"\bMhz\b"), "MHz"),
    (re.compile(r"\bKhz\b|\bkhz\b"), "kHz"),
    (re.compile(r"\bGhz\b"), "GHz"),
]


def tidy_units(root_el, rel):
    """Correct unit capitalisation and insert the missing space between a value
    and its unit. Values themselves are never touched."""
    n = 0
    for node in list(root_el.find_all(string=True)):
        if node.parent.name in ("pre", "code", "samp", "kbd", "script", "style"):
            continue
        s = str(node)
        new = s
        for rx, rep in UNIT_FIXES:
            new = rx.sub(rep, new)
        if new != s:
            node.replace_with(NavigableString(new))
            n += 1
    if n:
        STATS["units"] += 1
    return n


def unwrap_centering(prose, rel):
    """FrontPage centred whole paragraphs of prose. Centred running text is hard
    to read; captions and single images keep their centring."""
    n = 0
    for el in prose.find_all(["p", "div"]):
        cls = el.get("class") or []
        if "center" not in cls:
            continue
        if el.find(["img", "video", "iframe", "table"]):
            continue
        text = re.sub(r"\s+", " ", el.get_text(" ")).strip()
        if len(text) < 120:
            continue                      # short line: a caption or a label
        el["class"] = [c for c in cls if c != "center"]
        if not el["class"]:
            del el["class"]
        n += 1
    if n:
        note("align", f"{rel}: left-aligned {n} centred paragraph(s) of running text")
    return n


# --------------------------------------------------------------------------- #
# page rewrite
# --------------------------------------------------------------------------- #

def rel_root(rel):
    return "../" * rel.count("/")


def chab_prefix(rel):
    p = os.path.relpath("chaberton", os.path.dirname(rel)).replace(os.sep, "/")
    return "" if p == "." else p + "/"


def retrofit_page(site, rel, meta, section_of):
    path = os.path.join(site, rel.replace("/", os.sep))
    html = open(path, encoding="utf-8").read()
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body
    if body is None:
        return False

    chaberton = body.get("data-site") == "chaberton"
    is_404 = os.path.basename(rel) == "404.html"
    # This repository is a GitHub Pages project site, served below
    # /chirio.com/. The 404 keeps the originally requested URL as its base,
    # so its chrome must use the stable project-root prefix at every depth.
    root = "/chirio.com/" if is_404 else rel_root(rel)
    section = section_of.get(rel)

    # ---- head -------------------------------------------------------------
    head = soup.head
    if head is not None:
        for m in head.find_all("meta", attrs={"name": "color-scheme"}):
            m["content"] = "light dark"
        for l in head.find_all("link", rel="alternate"):
            l.decompose()
        depth = rel.count("/")
        for code, href in () if is_404 else (("it", os.path.basename(rel)),
                           ("en", "../" * depth + "en/" + rel),
                           ("x-default", os.path.basename(rel))):
            tag = soup.new_tag("link", rel="alternate", href=href)
            tag["hreflang"] = code
            head.append(tag)

    # ---- chrome -----------------------------------------------------------
    old_header = body.find("header", class_="site-header")
    if old_header is not None:
        new = BeautifulSoup(build_header(root, meta, section, chaberton,
                                         chab_prefix(rel) if chaberton else "",
                                         rel=rel, lang="it", switch=not is_404),
                            "html.parser")
        old_header.replace_with(new)
        STATS["header"] += 1

    old_footer = body.find("footer", class_="site-footer")
    if old_footer is not None:
        old_footer.replace_with(BeautifulSoup(build_footer(root, meta, chaberton), "html.parser"))
        STATS["footer"] += 1

    # ---- layout contract --------------------------------------------------
    page = body.find("div", class_="page")
    if page is not None:
        classes = page.get("class", [])
        had_aside = "has-aside" in classes
        page["class"] = ["wrap", "page"]
        main = page.find("main", recursive=False)
        aside = page.find("aside", recursive=False)
        if main is not None:
            wrapper = soup.new_tag("div")
            wrapper["class"] = ["layout"] + (["layout--toc"] if aside is not None else [])
            main.insert_before(wrapper)
            wrapper.append(main.extract())
            if aside is not None:
                aside["class"] = ["toc-rail"]
                wrapper.append(aside.extract())
        elif had_aside:
            pass

    for art in body.find_all("article", class_="article"):
        # normalise to a leading "article" but keep modifier classes such as
        # "error-page" — blindly resetting the list silently unstyles them
        art["class"] = ["article"] + [c for c in art.get("class", []) if c != "article"]
    for m in body.select(".article-head .meta"):
        m["class"] = ["article-meta"]
    for ul in body.select(".related ul.card-grid"):
        del ul["class"]
    for sp in body.select(".related .c-sec"):
        sp["class"] = ["r-sec"]
    for el in body.select(".aside-col"):
        el["class"] = ["toc-rail"]

    # ---- body content cleanups -------------------------------------------
    drop_email_image(soup, rel)
    tidy_breadcrumb(soup, rel)
    tidy_meta(soup, rel)
    prose = body.find("div", class_="prose")
    if prose is not None:
        strip_home_strips(prose, rel)
        dash_runs_to_lists(prose, rel)
        collapse_spaces(prose, rel)
        unwrap_centering(prose, rel)
        tag_media(prose, rel, site, os.path.dirname(rel))
    head_el = body.find(class_="article-head")
    for target in (prose, head_el):
        if target is not None:
            tidy_units(target, rel)
    curate_toc(soup, rel)
    t = soup.find("title")
    if t is not None:
        tidy_units(t, rel)

    # legacy note boxes adopt the callout component
    for bn in body.select(".band-note"):
        bn["class"] = ["callout"]

    if is_404:
        for el in soup.find_all(True):
            for attr in ("href", "src"):
                v = el.get(attr)
                if isinstance(v, str) and v and not v.startswith(("#", "/", "http",
                                                                 "mailto:", "tel:")):
                    el[attr] = "/" + v
        h = soup.find("html")
        if h is not None:
            h["data-root"] = root
            h["data-lang-root"] = root

    out = str(soup)
    if not out.startswith("<!DOCTYPE"):
        out = "<!DOCTYPE html>\n" + out.lstrip()
    changed = out != html
    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
    return changed


# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--check", action="store_true", help="report without writing")
    a = ap.parse_args()
    site = os.path.abspath(a.site)

    sys.path.insert(0, os.path.join(site, "_dev"))
    import sitemeta as meta
    # navigation labels are shorter than the homepage headings
    meta.NAV_SHORT = {
        "radio": "Radio", "alimentatori": "Alimentatori", "batterie": "Batterie",
        "led": "LED", "radioattivita": "Radioattività", "misure": "Misure",
        "progetti": "Progetti",
    }
    meta.CHAB_COUNT = 185

    section_of = dict(meta.PAGE_SECTION)

    curated_path = os.path.join(site, "_dev", "curated.txt")
    curated = set()
    if os.path.exists(curated_path):
        curated = {l.strip() for l in open(curated_path, encoding="utf-8")
                   if l.strip() and not l.startswith("#")}

    pages = []
    for dirpath, dirnames, filenames in os.walk(site):
        # "en" is the generated English mirror: it is produced by i18n_build.py
        # from the finished Italian pages, never retrofitted directly.
        dirnames[:] = [d for d in dirnames if d not in ("_dev", "en")]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in (".htm", ".html"):
                rel = os.path.relpath(os.path.join(dirpath, fn), site).replace(os.sep, "/")
                pages.append(rel)
    pages.sort()

    skipped = touched = 0
    for rel in pages:
        if rel in ("index.html", "index.htm") or rel in curated:
            skipped += 1
            continue
        if a.check:
            continue
        if retrofit_page(site, rel, meta, section_of):
            touched += 1

    print(f"retrofit: {touched} pages rewritten, {skipped} skipped "
          f"(hand-curated or replaced)")
    for k in sorted(STATS):
        print(f"  {k:16s} {STATS[k]}")
    if NOTES:
        with open(os.path.join(HERE, "retrofit-notes.txt"), "w", encoding="utf-8") as fh:
            for k, m in NOTES:
                fh.write(f"[{k}] {m}\n")
        print(f"  notes written to retrofit-notes.txt ({len(NOTES)} entries)")


if __name__ == "__main__":
    main()
