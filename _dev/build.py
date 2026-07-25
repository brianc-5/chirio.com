#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chirio.com static rebuild generator
===================================

Reads the original (read-only) FrontPage filebase and writes a modern,
responsive, accessible static site into ``chirio-modern/``.

Design goals, in priority order:

1. **Preservation.** Every non-store page, every word of visible text, every
   image / download reference, every anchor and every public URL is carried
   over unchanged.  Only broken encoding, invalid markup, accidental duplicate
   markup and broken relative paths are corrected.
2. **Semantics.** FrontPage layout tables are unwrapped into semantic HTML5;
   real data tables are kept as tables.
3. **No build step at deploy time.** The output is plain HTML/CSS/JS.

Usage::

    python3 build.py --src <original filebase> --out <chirio-modern dir>

The generator never writes outside ``--out``.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
import unicodedata
from collections import defaultdict

from urllib.parse import unquote
from bs4 import BeautifulSoup, NavigableString, Comment, Tag

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sitemeta as M  # noqa: E402

# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

FP_DIRS = {"_vti_cnf", "_vti_pvt", "_borders", "_fpclass", "_vti_txt", "_vti_log",
           "_vti_script", "_derived", "_private"}

#: files never copied to the output
SKIP_FILES = {"thumbs.db", ".ds_store", "desktop.ini", "frontpg.lck", "service.lck"}
SKIP_EXT = {".db", ".lck", ".btr", ".cnf", ".class", ".jar", ".ini", ".tmp", ".bak"}

HTML_EXT = {".htm", ".html"}

#: original FrontPage "band" colours that were used as section headings
BAND_COLOURS = {"#336699", "#006666", "#808080", "#666699", "#003366", "#4a4034",
                "#993366", "#669999", "#996633", "#660000", "#000080"}

#: colour -> preserved emphasis class
FONT_COLOUR_CLASS = {
    "#ffff00": "hl", "#ffff99": "hl", "#ffcc00": "hl", "#ffd700": "hl",
    "#00ff00": "hl-g", "#33ff33": "hl-g", "#00ff66": "hl-g", "#99ff99": "hl-g",
    "#ff0000": "hl-r", "#ff3300": "hl-r", "#ff6600": "hl-r", "#ff9900": "hl-r",
}

#: FrontPage wrote "picture.jpg (12345 byte)" into alt attributes
AUTO_ALT_RE = re.compile(r"^[\w .()\[\]+\-]+\.(jpe?g|gif|png|bmp)"
                         r"(\s*\(\s*[\d.,]+\s*(byte|bytes|kb|mb)\s*\))?$", re.I)

MEDIA_EXT = {".mp4": "video", ".m4v": "video", ".webm": "video", ".ogv": "video",
             ".mov": "video", ".avi": "download", ".wmv": "download",
             ".wav": "audio", ".mp3": "audio", ".ogg": "audio"}

DOWNLOAD_EXT = {".pdf", ".zip", ".xls", ".xlsx", ".doc", ".docx", ".ino", ".hex",
                ".txt", ".exe", ".bak", ".avi", ".wmv", ".rar", ".7z"}

DROP_ATTRS = {
    "bgcolor", "background", "link", "vlink", "alink", "text", "leftmargin",
    "topmargin", "marginwidth", "marginheight", "stylesrc", "cellpadding",
    "cellspacing", "bordercolor", "bordercolorlight", "bordercolordark",
    "hspace", "vspace", "valign", "nowrap", "clear", "compact", "language",
    "onmouseover", "onmouseout", "onclick", "onload", "profile", "scrolling",
    "frameborder", "marginlines", "rules", "framespacing", "startspan",
    "endspan", "webbot", "bot", "u-file", "tag", "s-type", "b-tab", "s-format",
}

REPORT: dict[str, list] = defaultdict(list)


def note(kind, *msg):
    REPORT[kind].append(" ".join(str(m) for m in msg))


# --------------------------------------------------------------------------- #
# source scanning helpers
# --------------------------------------------------------------------------- #

class Source:
    """Read-only view of the original filebase."""

    def __init__(self, root, exclude=()):
        self.root = os.path.abspath(root)
        #: absolute paths never scanned (e.g. the generator's own output folder
        #: when it happens to sit inside the source tree)
        self.exclude = {os.path.abspath(e) for e in exclude}
        self.files: list[str] = []          # rel paths, original case
        self.lower: dict[str, str] = {}     # lowercase rel path -> real rel path
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(
                d for d in dirnames
                if d.lower() not in FP_DIRS
                and os.path.abspath(os.path.join(dirpath, d)) not in self.exclude)
            rel_dir = os.path.relpath(dirpath, self.root)
            rel_dir = "" if rel_dir == "." else rel_dir.replace(os.sep, "/")
            for fn in sorted(filenames):
                rel = f"{rel_dir}/{fn}" if rel_dir else fn
                self.files.append(rel)
                self.lower[rel.lower()] = rel

    def exists(self, rel):
        return rel.lower() in self.lower

    def real(self, rel):
        return self.lower.get(rel.lower())

    def abspath(self, rel):
        return os.path.join(self.root, rel.replace("/", os.sep))

    def pages(self):
        return [f for f in self.files if os.path.splitext(f)[1].lower() in HTML_EXT]

    def read_text(self, rel):
        raw = open(self.abspath(rel), "rb").read()
        m = re.search(rb"charset\s*=\s*[\"']?([\w-]+)", raw[:4000], re.I)
        declared = (m.group(1).decode("ascii", "ignore").lower() if m else "")
        # windows-1252 is a superset of iso-8859-1 and is what FrontPage on
        # Windows actually produced; decoding latin-1 pages as cp1252 recovers
        # the smart quotes / dashes that would otherwise become control chars.
        order = ["cp1252"]
        if declared in ("utf-8", "utf8"):
            order = ["utf-8", "cp1252"]
        for enc in order:
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("cp1252", errors="replace")
            note("encoding", f"{rel}: undecodable bytes replaced")
        # repair characters that were mis-saved as UTF-8 inside a cp1252 file
        if "Ã" in text or "â€" in text:
            try:
                fixed = text.encode("cp1252", errors="strict").decode("utf-8", errors="strict")
                if fixed.count("�") == 0:
                    note("encoding", f"{rel}: double-encoded UTF-8 repaired")
                    text = fixed
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        # strip C1 control characters that cp1252 leaves behind
        cleaned = "".join(ch for ch in text if ch >= " " or ch in "\t\n\r")
        if len(cleaned) != len(text):
            note("encoding", f"{rel}: {len(text) - len(cleaned)} control character(s) removed")
        return cleaned


# --------------------------------------------------------------------------- #
# small utilities
# --------------------------------------------------------------------------- #

NBSP = " "


def txt(node):
    """Visible text of a node, whitespace-collapsed."""
    if node is None:
        return ""
    s = node if isinstance(node, str) else node.get_text(" ")
    s = s.replace(NBSP, " ")
    return re.sub(r"\s+", " ", s).strip()


def is_blank(node):
    """True when a node carries no visible content at all."""
    if isinstance(node, Comment):
        return True
    if isinstance(node, NavigableString):
        return txt(str(node)) == ""
    if node.name in ("img", "br", "hr", "input", "video", "audio", "iframe",
                     "source", "object", "embed", "table", "svg", "canvas"):
        return False
    if node.find(["img", "table", "video", "audio", "iframe", "object", "embed",
                  "hr", "input"]):
        return False
    return txt(node) == ""


BOILERPLATE_RE = re.compile(
    r"(vietato ogni utilizzo|all rights reserved|are copyright|is copyright|"
    r"tutti i diritti riservati)", re.I)


def norm_key(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def slugify(s, fallback="sez"):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    s = re.sub(r"-{2,}", "-", s)
    return s[:60] or fallback


def rel_root(page_rel):
    """Relative prefix that reaches the output root from *page_rel*."""
    depth = page_rel.count("/")
    return "../" * depth


def esc(s):
    return html.escape(s or "", quote=True)


# --------------------------------------------------------------------------- #
# link / asset rewriting
# --------------------------------------------------------------------------- #

class Rewriter:
    """Resolves and repairs the URLs found in the original pages."""

    def __init__(self, src: Source, page_map: dict[str, str]):
        self.src = src
        self.page_map = page_map      # source rel page -> output rel page

    def resolve(self, page_rel, url):
        """Return (new_url, kind).  kind in {external, anchor, page, asset,
        broken, mail}."""
        url = (url or "").strip()
        if not url:
            return None, "empty"
        if url.startswith("#"):
            return url, "anchor"
        low = url.lower()
        if low.startswith(("mailto:", "tel:")):
            return url, "mail"
        if low.startswith("javascript:"):
            return None, "broken"
        if low.startswith("file:"):
            return None, "broken"
        if re.match(r"^[a-zA-Z][\w+.-]*://", url) or url.startswith("//"):
            return url, "external"

        frag = ""
        if "#" in url:
            url, frag = url.split("#", 1)
            frag = "#" + frag
        query = ""
        if "?" in url:
            url, query = url.split("?", 1)
            query = "?" + query
        if not url:
            return frag or None, "anchor"

        raw = html.unescape(url)
        path = raw.replace("\\", "/")
        # a handful of original hrefs contain percent-encoded spaces
        from urllib.parse import unquote, quote
        plain = unquote(path)

        base = os.path.dirname(page_rel)
        target = os.path.normpath(os.path.join(base, plain)).replace(os.sep, "/")
        if target.startswith(".."):
            return None, "broken"

        real = self.src.real(target)
        if real is None:
            return None, "broken"

        if real in self.page_map:
            out_target = self.page_map[real]
        else:
            out_target = real

        newrel = os.path.relpath(out_target, base or ".").replace(os.sep, "/")
        kind = "page" if real in self.page_map else "asset"
        return quote(newrel, safe="/()!$&'*+,;=:@~") + query + frag, kind


# --------------------------------------------------------------------------- #
# HTML transformation
# --------------------------------------------------------------------------- #

META_BAND_RE = re.compile(
    r"^\s*(autore|author|a cura di|ultimo aggiornamento|ultima modifica|"
    r"last update|updated|aggiornato|copyright|\u00a9)\b", re.I)

NAVLINE_RE = re.compile(
    r"^\[?\s*(home|privacy|disclaimer|panoramiche\s*360|indietro|back|top|su|"
    r"chirio\.com|www\.chirio\.com)\b", re.I)


class Transformer:
    """Turns one original page body into clean semantic HTML."""

    def __init__(self, src, rewriter, page_rel, out_rel):
        self.src = src
        self.rw = rewriter
        self.page_rel = page_rel
        self.out_rel = out_rel
        self.headings: list[tuple[int, str, str]] = []   # (level, id, text)
        self.used_ids: set[str] = set()
        self.title_lines: list[str] = []
        self.dropped_nav = 0
        self.auto_alt = 0
        self.demoted_h1 = 0

    # -- entry point -------------------------------------------------------- #

    def run(self, soup: BeautifulSoup):
        body = soup.body or soup
        self._strip_comments(body)
        self._drop_frontpage_junk(body)
        self._harvest_title_block(body)
        self._drop_nav_lines(body)
        self._unwrap_presentational(body)
        self._convert_tables(body)
        self._fix_links(body)
        self._fix_images(body)
        self._fix_image_maps(body)
        self._mark_zoom_links(body)
        self._fix_media(body)
        self._normalise_anchors(body)
        self._tidy_blocks(body)
        self._drop_markers(body)
        self._demote_stray_h1(body)
        self._assign_heading_ids(body)
        return body

    # -- individual passes -------------------------------------------------- #

    def _strip_comments(self, body):
        for c in body.find_all(string=lambda s: isinstance(s, Comment)):
            c.extract()

    def _drop_frontpage_junk(self, body):
        for t in body.find_all("script"):
            src = t.get("src") or ""
            what = src or "inline script"
            if "shinystat" in (src + t.get_text()).lower():
                what = f"ShinyStat visitor counter ({src or 'inline'})"
            note("removed", f"{self.page_rel}: <script> removed — {what}")
            t.decompose()
        for t in body.find_all(["basefont", "marquee", "blink", "noscript",
                                "base", "applet", "param", "map", "area"]):
            if t.name == "applet":
                continue      # handled separately by the panorama builder
            if t.name in ("map", "area"):
                continue      # image maps are preserved
            t.decompose()
        # FrontPage hover-button applets and hit counters
        for t in body.find_all("a", href=True):
            if "shinystat" in t["href"].lower():
                note("removed", f"{self.page_rel}: ShinyStat visitor counter removed")
                t.decompose()
        for t in body.find_all("img", src=True):
            if "shinystat" in t["src"].lower():
                t.decompose()

    def _harvest_title_block(self, body):
        """Original pages open with a small banner table holding the page title
        as one or more ``<h2>`` lines.  Lift it out so the new template can
        render a single, correct ``<h1>`` — no text is discarded: the heading
        lines become the h1/subtitle and any remaining text is kept as the
        subtitle."""
        first = None
        for h in body.find_all(["h1", "h2", "h3"]):
            if txt(h):
                first = h
                break
        if first is None:
            return

        table = first.find_parent("table")
        if table is not None:
            # only the *leading* banner table qualifies
            prior = [e for e in table.find_all_previous()
                     if getattr(e, "name", None) in ("p", "img", "table", "hr", "h1",
                                                     "h2", "h3", "div")
                     and e.find_parent("table") is None]
            prior = [e for e in prior if not is_blank(e) and e.name != "div"]
            if (not prior and not table.find("img")
                    and len(txt(table)) <= 420 and table.find_parent("table") is None):
                heads = [txt(h) for h in table.find_all(["h1", "h2", "h3"]) if txt(h)]
                for h in table.find_all(["h1", "h2", "h3"]):
                    h.decompose()
                rest = [t for t in (txt(c) for c in table.find_all(["td", "th"])) if t]
                self.title_lines = heads + rest
                table.decompose()
                return

        # otherwise: a run of consecutive standalone headings
        block, node = [], first
        while node is not None and getattr(node, "name", None) in ("h1", "h2", "h3"):
            block.append(node)
            nxt = node.find_next_sibling()
            while nxt is not None and is_blank(nxt) and getattr(nxt, "name", None) not in (
                    "h1", "h2", "h3"):
                nxt = nxt.find_next_sibling()
            node = nxt
        lines = [txt(h) for h in block if txt(h)]
        if not lines:
            return
        self.title_lines = lines
        for h in block:
            h.decompose()

    def _drop_nav_lines(self, body):
        """Remove the original ``[home] [privacy]`` breadcrumb strips: the new
        template provides real navigation and breadcrumbs for them."""
        for p in body.find_all(["p", "div", "td", "font"]):
            if getattr(p, "decomposed", False) or p.parent is None:
                continue
            links = p.find_all("a", href=True)
            if not links:
                continue
            if p.find(["img", "table", "video", "iframe"]):
                continue
            t = txt(p)
            if len(t) > 260:
                continue
            # a bracketed strip such as "[ home ] [ privacy ]" is pure chrome:
            # every target is a site-level page and nothing but punctuation sits
            # around the links.  Anything else — including sitemap and gallery
            # link lists — is content and is preserved.
            CHROME_TARGETS = {"index.htm", "chab.htm", "chirio_com_privacy.htm",
                              "chirio_com_disclaimer.htm"}
            targets = set()
            for a in links:
                u = html.unescape(a.get("href", "")).split("#")[0].split("?")[0]
                if not u or re.match(r"^[a-zA-Z][\w+.-]*:", u):
                    targets.add("?")
                    continue
                t = os.path.normpath(os.path.join(os.path.dirname(self.page_rel), u))
                targets.add(t.replace(os.sep, "/").lower())
            if not targets or not targets <= CHROME_TARGETS:
                continue
            if "[" not in t and "]" not in t:
                continue
            outside = t
            for a in links:
                lt = txt(a)
                if lt:
                    outside = outside.replace(lt, " ", 1)
            if re.fullmatch(r"[\s\[\]()·|,;:/>«»<\-–—]*", outside or ""):
                self.dropped_nav += 1
                if p.name == "td":
                    p.clear()
                else:
                    p.decompose()

    def _unwrap_presentational(self, body):
        # The original used coloured table cells as section headings; remember
        # which cells were painted before the presentational attributes go.
        for cell in body.find_all(["td", "th"]):
            colour = (cell.get("bgcolor") or "").strip().lower()
            if colour in BAND_COLOURS:
                cell["data-band"] = "1"

        # <center> and <div align=...> are pure layout
        for t in body.find_all(["center"]):
            t.unwrap()
        for t in body.find_all("div"):
            if set(t.attrs) <= {"align", "style", "class", "id"} and not t.get("id"):
                al = (t.get("align") or "").lower()
                if al == "center" and not t.get("id"):
                    t.unwrap()
                elif not t.attrs or set(t.attrs) <= {"style", "align"}:
                    t.unwrap()

        # <font> carries the only emphasis information the original had
        for f in body.find_all("font"):
            if getattr(f, "decomposed", False) or f.parent is None:
                continue
            colour = (f.get("color") or "").strip().lower()
            cls = FONT_COLOUR_CLASS.get(colour)
            if cls and txt(f):
                f.name = "span"
                f.attrs = {"class": [cls]}
            else:
                f.unwrap()

        for t in body.find_all(["u", "s", "strike", "big", "tt", "nobr", "span"]):
            if t.name == "span":
                if not t.get("class"):
                    t.unwrap()
                continue
            if t.name in ("s", "strike"):
                t.name = "del"
                t.attrs = {}
            elif t.name == "u":
                t.name = "em"
                t.attrs = {}
            elif t.name == "big":
                t.name = "strong"
                t.attrs = {}
            elif t.name == "tt":
                t.name = "code"
                t.attrs = {}
            elif t.name == "nobr":
                t.unwrap()

        for t in body.find_all(["b", "i"]):
            t.name = "strong" if t.name == "b" else "em"
            t.attrs = {}

        # drop presentational attributes everywhere
        for t in body.find_all(True):
            if getattr(t, "decomposed", False) or (t.parent is None and t is not body):
                continue
            for a in list(t.attrs):
                al = a.lower()
                if al in DROP_ATTRS or al.startswith(("on", "ms")):
                    del t.attrs[a]
            if t.name not in ("img", "video", "iframe", "canvas", "embed", "object"):
                t.attrs.pop("width", None)
                t.attrs.pop("height", None)
                t.attrs.pop("border", None)
            if "style" in t.attrs and t.name not in ("img",):
                # every inline style in the source is FrontPage margin/border noise
                del t.attrs["style"]
            al = (t.get("align") or "").lower()
            if al:
                del t.attrs["align"]
                if t.name in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th"):
                    if al == "center":
                        t["class"] = t.get("class", []) + ["center"]
                    elif al == "right":
                        t["class"] = t.get("class", []) + ["right"]
                elif t.name == "img" and al in ("left", "right"):
                    t["class"] = t.get("class", []) + [f"float-{al}"]

    # ---- tables ----------------------------------------------------------- #

    @staticmethod
    def _rows(table):
        out = []
        for tr in table.find_all("tr", recursive=True):
            if tr.find_parent("table") is not table:
                continue
            cells = [c for c in tr.find_all(["td", "th"], recursive=True)
                     if c.find_parent("table") is table]
            out.append((tr, cells))
        return out

    def _is_data_table(self, table):
        """Tell a real tabular dataset from a FrontPage layout grid.

        The discriminator that works across this filebase: data tables have
        *many* cells holding *little* text each and a stable column count;
        layout grids have a handful of cells holding whole articles, full-width
        illustrations or navigation link lists.
        """
        rows = self._rows(table)
        if len(rows) < 2:
            return False
        widths = [len(cells) for _, cells in rows if cells]
        if not widths or max(widths) < 2:
            return False
        if sum(1 for w in widths if w >= 2) < 2:
            return False

        cells = [c for _, cs in rows for c in cs]
        if len(cells) < 6:
            return False

        # structural disqualifiers: things that never appear inside a dataset
        for c in cells:
            if c.find(["hr", "h1", "h2", "h3", "h4", "blockquote", "table"]):
                return False
            for im in c.find_all("img"):
                try:
                    if int(im.get("width") or 0) >= 260:
                        return False
                except ValueError:
                    return False

        texts = [txt(c) for c in cells]
        total = sum(len(t) for t in texts)
        if total == 0:
            return False
        if total / len(cells) > 95:              # prose, not data
            return False
        if sum(1 for t in texts if len(t) > 200) > len(cells) * 0.15:
            return False

        # a grid of links is navigation
        linked = sum(len(txt(a)) for a in table.find_all("a"))
        if linked > total * 0.6:
            return False

        # a dataset keeps the same number of columns on most of its rows
        body_widths = [w for w in widths if w >= 2]
        common = max(set(body_widths), key=body_widths.count)
        if body_widths.count(common) < max(2, len(body_widths) * 0.6):
            return False
        return True

    def _promote_band_cell(self, cell):
        """A cell painted in one of the original band colours acted as a
        section heading."""
        if cell.get("data-band") != "1":
            return None
        if cell.find(["img", "table", "video", "iframe"]):
            return None
        t = txt(cell)
        if not t or len(t) > 160:
            return None
        # a band cell filled with links is navigation, not a section heading
        linked = sum(len(txt(a)) for a in cell.find_all("a"))
        if linked and linked > len(t) * 0.5:
            return None
        # page metadata ("Autore: ...", "Ultimo aggiornamento: ...") is not a
        # section heading either
        if META_BAND_RE.match(t):
            return None
        return t

    def _convert_tables(self, body):
        # innermost first so nested layout tables collapse cleanly
        for table in reversed(body.find_all("table")):
            if table.parent is None:
                continue
            if self._is_data_table(table):
                self._style_data_table(table)
            else:
                self._flatten_layout_table(table)

    BLOCK_NAMES = {"p", "div", "table", "ul", "ol", "dl", "h1", "h2", "h3", "h4",
                   "h5", "h6", "pre", "blockquote", "figure", "figcaption", "hr",
                   "section", "aside", "nav", "details", "address", "fieldset"}

    def _style_data_table(self, table):
        soup = BeautifulSoup("", "html.parser")
        summary = table.get("summary")
        for a in list(table.attrs):
            if a.lower() not in ("class", "id"):
                del table.attrs[a]
        table["class"] = ["data-table"]

        rows = self._rows(table)
        if rows:
            tr, cells = rows[0]
            painted = bool(cells) and all(c.get("data-band") == "1" for c in cells)
            bolded = bool(cells) and all(
                c.find(["strong", "em"]) is not None or txt(c) == "" for c in cells)
            allth = bool(cells) and all(c.name == "th" for c in cells)
            # a measurement table whose first row is short non-numeric labels
            # while the rows below are numbers has an unstyled header row
            labelled = False
            if len(rows) >= 3 and len(cells) >= 2:
                first = [txt(c) for c in cells]
                below = [txt(c) for _t, cs in rows[1:4] for c in cs]
                first_numeric = sum(1 for t in first if re.fullmatch(r"[\d.,\-+ ]+", t or "x"))
                below_numeric = sum(1 for t in below if re.search(r"\d", t or ""))
                labelled = (all(0 < len(t) <= 34 for t in first)
                            and first_numeric == 0
                            and below and below_numeric >= len(below) * 0.6)
            if painted or bolded or allth or labelled:
                for c in cells:
                    c.name = "th"
                    c["scope"] = "col"
                thead = soup.new_tag("thead")
                tr.insert_before(thead)
                thead.append(tr.extract())
        for _, cells in self._rows(table):
            for c in cells:
                for a in list(c.attrs):
                    if a.lower() not in ("class", "id", "colspan", "rowspan",
                                         "scope", "headers"):
                        del c.attrs[a]
        if summary and not table.find("caption"):
            cap = soup.new_tag("caption")
            cap.string = summary
            table.insert(0, cap)

        # wrap so wide technical tables scroll instead of breaking the layout
        wrap = soup.new_tag("div")
        wrap["class"] = ["table-wrap"]
        wrap["tabindex"] = "0"
        wrap["role"] = "region"
        cap = table.find("caption")
        wrap["aria-label"] = (txt(cap)[:120] if cap else "Tabella dati")
        table.replace_with(wrap)
        wrap.append(table)

    def _flatten_layout_table(self, table):
        """Replace a FrontPage layout table by the flow of its cell contents."""
        soup = BeautifulSoup("", "html.parser")
        out = []

        def flush(buf, centred):
            if not buf or all(is_blank(k) for k in buf):
                return
            p = soup.new_tag("p")
            if centred:
                p["class"] = ["center"]
            for k in buf:
                p.append(k)
            out.append(p)

        for _, cells in self._rows(table):
            for cell in cells:
                band = self._promote_band_cell(cell)
                if band is not None:
                    h = soup.new_tag("h2")
                    h.string = band
                    out.append(h)
                    continue
                kids = list(cell.contents)
                if all(is_blank(k) for k in kids):
                    continue
                centred = "center" in (cell.get("class") or [])
                buf = []
                for k in kids:
                    if getattr(k, "name", None) in self.BLOCK_NAMES:
                        flush(buf, centred)
                        buf = []
                        out.append(k.extract())
                    else:
                        buf.append(k.extract())
                flush(buf, centred)
        if out:
            table.replace_with(*out)
        else:
            table.decompose()

    # ---- links, images, media -------------------------------------------- #

    #: pre-existing mistakes in the source where the link text makes the
    #: intended target unambiguous (a broken relative path, per the brief)
    HREF_FIXUPS = {
        ("chaberton/video_chaberton.HTM", "video/3_16_08_86.WMV", "video/2_07_08_86.WMV"),
    }

    def _fix_links(self, body):
        for page, wrong, right in self.HREF_FIXUPS:
            if page != self.page_rel:
                continue
            for a in body.find_all("a", href=True):
                if a["href"].strip() == wrong and txt(a).strip().endswith(
                        os.path.basename(right)):
                    a["href"] = right
                    note("fixed", f"{page}: link labelled {txt(a)!r} pointed at "
                                  f"{wrong} — corrected to {right}")
        for a in body.find_all(["a", "area"]):
            if getattr(a, "decomposed", False) or a.parent is None:
                continue
            href = a.get("href")
            if href is None:
                if a.name == "area":
                    a.decompose()
                continue
            new, kind = self.rw.resolve(self.page_rel, href)
            if kind == "broken" or new is None:
                if a.name == "area":
                    a.decompose()
                    note("broken-link", f"{self.page_rel}: image-map area <{href}> unresolved — removed")
                    continue
                has_content = bool(txt(a)) or a.find(["img", "video", "audio", "table"])
                if has_content:
                    note("broken-link",
                         f"{self.page_rel}: <{href}> missing in source — link removed, "
                         f"content kept in place")
                    a.unwrap()
                else:
                    a.decompose()
                continue
            a["href"] = new
            if kind == "external":
                a["rel"] = "noopener"
                if a.get("target") != "_blank":
                    a.attrs.pop("target", None)
            else:
                a.attrs.pop("target", None)
            ext = os.path.splitext(new.split("#")[0].split("?")[0])[1].lower()
            if a.name == "a" and kind == "asset" and (
                    ext in DOWNLOAD_EXT or ext in MEDIA_EXT):
                if not a.find("img"):
                    a["class"] = a.get("class", []) + ["download"]
                    if not txt(a):
                        a.string = os.path.basename(new)

    def _fix_image_maps(self, body):
        """Client-side image maps have fixed pixel coordinates and therefore do
        not survive responsive scaling.  The map is kept for pointer users and a
        plain link list is added so every target stays reachable at any width."""
        soup = BeautifulSoup("", "html.parser")
        for img in body.find_all("img", usemap=True):
            name = (img.get("usemap") or "").lstrip("#")
            mp = body.find("map", attrs={"name": name}) or body.find("map", id=name)
            if mp is None:
                del img.attrs["usemap"]
                continue
            mp["id"] = name
            areas = [ar for ar in mp.find_all("area") if ar.get("href")]
            if not areas:
                continue
            ul = soup.new_tag("ul")
            ul["class"] = ["map-links"]
            for i, ar in enumerate(areas, 1):
                li = soup.new_tag("li")
                a = soup.new_tag("a", href=ar["href"])
                label = ar.get("alt") or ar.get("title") or ""
                a.string = label or f"Fotografia {i}"
                li.append(a)
                ul.append(li)
            holder = soup.new_tag("div")
            holder["class"] = ["band-note"]
            p = soup.new_tag("p")
            p.append(soup.new_string("Fotografie collegate alla mappa: "))
            holder.append(p)
            holder.append(ul)
            anchor = img.find_parent(["p", "div", "figure"]) or img
            anchor.insert_after(holder)
            note("accessibility",
                 f"{self.page_rel}: image map “{name}” supplemented with a text link list "
                 f"({len(areas)} targets) for small screens and keyboard users")

    def _fix_images(self, body):
        for img in body.find_all("img"):
            if getattr(img, "decomposed", False) or img.parent is None:
                continue
            src = img.get("src")
            if not src:
                img.decompose()
                continue
            new, kind = self.rw.resolve(self.page_rel, src)
            if new is None or kind in ("broken",):
                alt = img.get("alt") or ""
                repl = BeautifulSoup("", "html.parser").new_tag("span")
                repl["class"] = ["img-note"]
                repl.string = f"[immagine non disponibile: {os.path.basename(src)}"                                + (f" — {alt}]" if alt else "]")
                img.replace_with(repl)
                continue
            img["src"] = new
            for a in list(img.attrs):
                if a.lower() not in ("src", "alt", "width", "height", "class",
                                     "id", "usemap", "title", "srcset", "sizes"):
                    del img.attrs[a]
            for dim in ("width", "height"):
                v = (img.get(dim) or "").strip()
                if v and not v.isdigit():
                    del img.attrs[dim]
            alt = img.get("alt")
            if alt is None:
                # never invent a description for a technical drawing; an empty
                # alt keeps the image out of the accessibility tree instead.
                img["alt"] = ""
            elif AUTO_ALT_RE.match(alt.strip()):
                # FrontPage inserted "file.jpg (12345 byte)" as alt text; that is
                # machine noise, not an editorial description.
                img["alt"] = ""
                self.auto_alt += 1
            img["loading"] = "lazy"
            img["decoding"] = "async"

    def _mark_zoom_links(self, body):
        """A thumbnail linking to the same picture at full size is the original
        way of inspecting wide schematics; label it so it is obvious."""
        for a in body.find_all("a", href=True):
            if getattr(a, "decomposed", False) or a.parent is None:
                continue
            ext = os.path.splitext(a["href"].split("#")[0])[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".gif"):
                continue
            img = a.find("img")
            if img is None:
                continue
            a["class"] = [c for c in a.get("class", []) if c != "download"] + ["zoom-link"]
            if not a.get("title"):
                a["title"] = "Apri l'immagine a piena risoluzione"

    def _fix_media(self, body):
        """Turn links to browser-playable media into inline players, keeping the
        original download link as a fallback.  Only done when the link stands
        alone in its block, so surrounding prose is never restructured."""
        soup = BeautifulSoup("", "html.parser")
        for a in body.find_all("a", href=True):
            if getattr(a, "decomposed", False) or a.parent is None:
                continue
            href = a["href"].split("#")[0].split("?")[0]
            ext = os.path.splitext(href)[1].lower()
            kind = MEDIA_EXT.get(ext)
            if kind not in ("video", "audio") or a.find("img"):
                continue
            parent = a.parent
            if getattr(parent, "name", None) not in ("p", "td", "div", "li"):
                continue
            siblings = [k for k in parent.contents if k is not a and not is_blank(k)]
            if siblings:
                continue      # keep it as a plain download link
            label = txt(a) or os.path.basename(href)
            wrap = soup.new_tag("div")
            wrap["class"] = ["media"]
            el = soup.new_tag(kind)
            el["controls"] = ""
            el["preload"] = "metadata"
            el["src"] = a["href"]
            fb = soup.new_tag("a")
            fb["href"] = a["href"]
            fb["class"] = ["download"]
            fb.string = label
            el.append(fb)
            cap = soup.new_tag("p")
            cap["class"] = ["center"]
            dl = soup.new_tag("a")
            dl["href"] = a["href"]
            dl["class"] = ["download"]
            dl.string = label
            cap.append(dl)
            wrap.append(el)
            wrap.append(cap)
            if parent.name in ("p", "li"):
                parent.replace_with(wrap)
            else:
                a.replace_with(wrap)
        for f in body.find_all("iframe"):
            src = f.get("src") or ""
            if "youtube" in src or "vimeo" in src:
                f.attrs = {"src": src, "loading": "lazy",
                           "title": "Video (YouTube)" if "youtube" in src else "Video",
                           "allow": "encrypted-media; picture-in-picture",
                           "allowfullscreen": ""}
                wrap = soup.new_tag("div")
                wrap["class"] = ["video-embed"]
                f.replace_with(wrap)
                wrap.append(f)
            else:
                f.decompose()
        for t in body.find_all(["object", "embed"]):
            note("removed", f"{self.page_rel}: <{t.name}> plug-in object removed (not usable in modern browsers)")
            t.decompose()

    def _normalise_anchors(self, body):
        """``<a name=x>`` is obsolete; keep the same fragment as an id."""
        for a in body.find_all("a"):
            if getattr(a, "decomposed", False) or a.parent is None:
                continue
            name = a.get("name")
            if not name:
                continue
            del a.attrs["name"]
            if not a.get("id"):
                a["id"] = name
            self.used_ids.add(a["id"])
            if not a.get("href") and not txt(a) and not a.find("img"):
                a["class"] = a.get("class", []) + ["anchor-target"]
        for t in body.find_all(id=True):
            self.used_ids.add(t["id"])

    def _tidy_blocks(self, body):
        # remove FrontPage's empty spacer paragraphs and stray table remnants
        for name in ("p", "div", "span", "strong", "em", "font", "h1", "h2",
                     "h3", "h4", "h5", "h6", "td", "tr", "table", "tbody",
                     "thead", "li", "ul", "ol", "center", "figure", "small"):
            for t in body.find_all(name):
                if getattr(t, "decomposed", False) or t.parent is None:
                    continue
                if t.get("id"):
                    continue
                if name in ("td", "tr", "tbody", "thead") and t.find_parent("table"):
                    continue
                if is_blank(t) and not t.find(["img", "hr", "video", "audio", "iframe"]):
                    t.decompose()
        # collapse consecutive <br>
        for br in body.find_all("br"):
            if getattr(br, "decomposed", False) or br.parent is None:
                continue
            nxt = br.next_sibling
            while nxt is not None and isinstance(nxt, NavigableString) and txt(str(nxt)) == "":
                nxt = nxt.next_sibling
            if getattr(nxt, "name", None) == "br":
                br.decompose()
        # unwrap paragraphs that only wrap a nested paragraph (FrontPage bug)
        for p in body.find_all("p"):
            if getattr(p, "decomposed", False) or p.parent is None:
                continue
            kids = [k for k in p.contents if not (isinstance(k, NavigableString) and txt(str(k)) == "")]
            if len(kids) == 1 and getattr(kids[0], "name", None) in ("p", "div", "table", "ul", "ol"):
                p.unwrap()
        # trailing/leading <hr> add nothing next to the new template rules
        for hr in body.find_all("hr"):
            if getattr(hr, "decomposed", False) or hr.parent is None:
                continue
            prev = hr.find_previous_sibling()
            nxt = hr.find_next_sibling()
            if prev is None or nxt is None:
                hr.decompose()

    def _drop_markers(self, body):
        for t in body.find_all(attrs={"data-band": True}):
            del t.attrs["data-band"]

    def _demote_stray_h1(self, body):
        """The template owns the page <h1>; any heading the source left in the
        body becomes an <h2> so the outline stays valid."""
        for h in body.find_all("h1"):
            if getattr(h, "decomposed", False) or h.parent is None:
                continue
            h.name = "h2"
            self.demoted_h1 += 1

    def _assign_heading_ids(self, body):
        for h in body.find_all(["h2", "h3", "h4"]):
            if getattr(h, "decomposed", False) or h.parent is None:
                continue
            t = txt(h)
            if not t:
                h.decompose()
                continue
            hid = h.get("id") or slugify(t)
            base, n = hid, 2
            while hid in self.used_ids:
                hid = f"{base}-{n}"
                n += 1
            self.used_ids.add(hid)
            h["id"] = hid
            self.headings.append((int(h.name[1]), hid, t))


# --------------------------------------------------------------------------- #
# templates
# --------------------------------------------------------------------------- #

def nav_html(root, active_section=None, chaberton=False, active_page=None,
             chab_prefix=""):
    items = []
    if chaberton:
        for href, label in M.CHAB_NAV:
            cur = ' aria-current="page"' if active_page == href else ""
            items.append(f'<li><a href="{chab_prefix}{esc(href)}"{cur}>{esc(label)}</a></li>')
        items.insert(0, f'<li><a href="{root}index.html">Chirio.com</a></li>')
    else:
        for slug, label, _h, _d in M.SECTIONS:
            cur = ' aria-current="true"' if active_section == slug else ""
            items.append(f'<li><a href="{root}index.html#{slug}"{cur}>{esc(label)}</a></li>')
        items.append(f'<li><a href="{root}chaberton/chab.htm">Chaberton</a></li>')
    return "\n".join(items)


def header_html(root, active_section=None, chaberton=False, active_page=None,
                chab_prefix=""):
    if chaberton:
        brand = (f'<a class="brand" href="{chab_prefix}chab.htm">Chaberton'
                 f'<small>Chirio.com · archivio storico</small></a>')
    else:
        brand = (f'<a class="brand" href="{root}index.html">Chirio<b>.com</b>'
                 f'<small>Elettronica · radio · progetti</small></a>')
    return f"""<header class="site-header">
  <div class="wrap">
    {brand}
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">
      <span class="bars" aria-hidden="true"></span><span>Menu</span>
    </button>
    <nav id="site-nav" aria-label="Navigazione principale">
      <ul>
{nav_html(root, active_section, chaberton, active_page, chab_prefix)}
      </ul>
    </nav>
  </div>
</header>"""


def breadcrumb_html(trail):
    if not trail:
        return ""
    li = []
    for i, (href, label) in enumerate(trail):
        last = i == len(trail) - 1
        if last or not href:
            li.append(f'<li aria-current="page">{esc(label)}</li>')
        else:
            li.append(f'<li><a href="{esc(href)}">{esc(label)}</a></li>')
    return ('<nav class="breadcrumb" aria-label="Percorso di navigazione"><div class="wrap">'
            f'<ol>{"".join(li)}</ol></div></nav>')


def footer_html(root, chaberton=False):
    seclinks = "\n".join(
        f'<li><a href="{root}index.html#{slug}">{esc(label)}</a></li>'
        for slug, label, _h, _d in M.SECTIONS)
    chablinks = "\n".join(
        f'<li><a href="{root}chaberton/{esc(href)}">{esc(label)}</a></li>'
        for href, label in M.CHAB_NAV[1:7])
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div>
        <h2>Sezioni</h2>
        <ul>
{seclinks}
        </ul>
      </div>
      <div>
        <h2>Chaberton</h2>
        <ul>
          <li><a href="{root}chaberton/chab.htm">La Batteria dello Chaberton</a></li>
{chablinks}
        </ul>
      </div>
      <div>
        <h2>Il sito</h2>
        <ul>
          <li><a href="{root}index.html">Indice generale</a></li>
          <li><a href="{root}chirio_com_privacy.htm">Informativa sulla privacy</a></li>
          <li><a href="{root}chirio_com_disclaimer.htm">Disclaimer</a></li>
        </ul>
      </div>
    </div>
    <div class="legal">
      <p><strong>Chirio.com</strong> — Roberto Chirio. Archivio tecnico di progetti di
        elettronica, radio, illuminazione a LED e documentazione storica.</p>
      <p>È vietato ogni utilizzo non autorizzato delle foto, dei video, delle immagini,
        degli schemi e dei testi. Photos and videos are copyright © Roberto Chirio:
        all rights reserved.</p>
    </div>
  </div>
  <button class="to-top" type="button" aria-label="Torna all'inizio della pagina">↑</button>
</footer>"""


def toc_html(headings, mobile=False):
    hs = [h for h in headings if h[0] == 2]
    if len(hs) < 3:
        return ""
    items = "\n".join(f'<li><a href="#{esc(hid)}">{esc(t)}</a></li>' for _l, hid, t in hs)
    inner = (f'<nav class="toc" aria-labelledby="toc-title{"-m" if mobile else ""}">'
             f'<p class="toc-title" id="toc-title{"-m" if mobile else ""}">In questa pagina</p>'
             f'<ol>{items}</ol></nav>')
    if mobile:
        return f'<details class="toc-mobile"><summary>Indice della pagina</summary>{inner}</details>'
    return inner


def document(*, root, lang, title, description, keywords, body, section=None,
             chaberton=False, active_page=None, trail=None, extra_head="",
             chab_prefix=""):
    meta_desc = f'\n  <meta name="description" content="{esc(description)}">' if description else ""
    meta_kw = f'\n  <meta name="keywords" content="{esc(keywords)}">' if keywords else ""
    site_attr = ' data-site="chaberton"' if chaberton else ""
    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}" data-root="{root}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>{meta_desc}{meta_kw}
  <meta name="author" content="Roberto Chirio">
  <meta name="color-scheme" content="dark light">
  <link rel="stylesheet" href="{root}assets/site.css">{extra_head}
</head>
<body{site_attr}>
<a class="skip-link" href="#main">Vai al contenuto principale</a>
{header_html(root, section, chaberton, active_page, chab_prefix)}
{breadcrumb_html(trail or [])}
{body}
{footer_html(root, chaberton)}
<script src="{root}assets/site.js" defer></script>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# the build
# --------------------------------------------------------------------------- #

class Builder:
    def __init__(self, src_dir, out_dir):
        self.out = os.path.abspath(out_dir)
        self.src = Source(src_dir, exclude=[self.out])
        self.page_map: dict[str, str] = {}
        self.search: list[dict] = []
        self.written: set[str] = set()
        self.stats = defaultdict(int)
        self.page_info: dict[str, dict] = {}

    # -- helpers ------------------------------------------------------------ #

    def write(self, rel, text):
        path = os.path.join(self.out, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        self.written.add(rel)

    # -- 1. url plan -------------------------------------------------------- #

    def plan_urls(self):
        """Public URLs are preserved verbatim.  The single exception is the
        homepage: the original file is ``INDEX.HTM`` while every internal link
        points at ``index.htm``.  GitHub Pages is case sensitive and serves
        ``index.html`` as the directory index, so the homepage is emitted as
        ``index.html`` with a tiny ``index.htm`` redirect kept for the legacy
        lowercase URL."""
        for p in self.src.pages():
            if p.upper() == "INDEX.HTM":
                self.page_map[p] = "index.html"
            else:
                self.page_map[p] = p
        self.rw = Rewriter(self.src, self.page_map)

    # -- 2. assets ---------------------------------------------------------- #

    def copy_assets(self):
        copied = skipped = 0
        for rel in self.src.files:
            ext = os.path.splitext(rel)[1].lower()
            name = os.path.basename(rel).lower()
            if ext in HTML_EXT:
                continue
            if name in SKIP_FILES or ext in SKIP_EXT:
                skipped += 1
                self.stats["assets_skipped"] += 1
                continue
            srcp = self.src.abspath(rel)
            dstp = os.path.join(self.out, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dstp), exist_ok=True)
            if not os.path.exists(dstp) or os.path.getsize(dstp) != os.path.getsize(srcp):
                shutil.copy2(srcp, dstp)
            size = os.path.getsize(dstp)
            if size > 100 * 1024 * 1024:
                note("oversize", f"{rel}: {size/1048576:.1f} MiB exceeds the GitHub Pages 100 MiB limit")
            self.written.add(rel)
            copied += 1
        self.stats["assets"] = copied
        print(f"  assets copied: {copied}  (skipped {skipped} system/plug-in files)")

    def make_pano_previews(self):
        """Small still previews for the three 6000 px panoramas (the originals
        were only reachable through a Java applet)."""
        try:
            from PIL import Image
        except ImportError:
            return
        for page, pano in M.CHAB_PANORAMAS.items():
            rel = f"chaberton/{pano[0]}"
            real = self.src.real(rel)
            if not real:
                continue
            out_rel = f"chaberton/{os.path.dirname(pano[0])}/preview.jpg"
            dst = os.path.join(self.out, out_rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            im = Image.open(self.src.abspath(real))
            im.thumbnail((1400, 1400), Image.LANCZOS)
            im.convert("RGB").save(dst, "JPEG", quality=82, optimize=True, progressive=True)
            self.written.add(out_rel)

    # -- 3. page classification -------------------------------------------- #

    def classify(self, rel):
        low = rel.lower()
        if low == "index.htm":
            return "home"
        if not low.startswith("chaberton/"):
            if rel in M.LEGAL_PAGES:
                return "legal"
            return "article"
        tail = rel[len("chaberton/"):]
        if tail in M.CHAB_PANORAMAS:
            return "panorama"
        if "/pages/" in tail:
            return "photo"
        d = tail.split("/")[0]
        if d in M.CHAB_GALLERIES and "/" in tail:
            return "gallery"
        return "chab"

    # -- 4. main site ------------------------------------------------------- #

    def parse(self, rel):
        raw = self.src.read_text(rel)
        soup = BeautifulSoup(raw, "html5lib")
        for sc in soup.find_all("script"):
            src = sc.get("src") or ""
            if "shinystat" in (src + sc.get_text()).lower():
                note("removed", f"{rel}: ShinyStat visitor counter removed ({src or 'inline'})")
            elif sc.parent is not None and sc.find_parent("body") is None:
                note("removed", f"{rel}: <script> in <head> removed ({src or 'inline'})")
            sc.decompose()
        title = txt(soup.title) if soup.title else ""
        desc = kw = ""
        kws = []
        lang = "it"
        for m in soup.find_all("meta"):
            n = (m.get("name") or m.get("http-equiv") or "").lower()
            c = m.get("content") or ""
            if n == "description" and not desc:
                desc = re.sub(r"\s+", " ", html.unescape(c)).strip()
            elif n == "keywords" and c.strip():
                kws.append(re.sub(r"\s+", " ", html.unescape(c)).strip(" ,"))
            elif n == "content-language" and c.strip():
                lang = c.strip().split(",")[0].strip() or "it"
        kw = ", ".join(kws)
        return soup, title, desc, kw, lang

    def build_article(self, rel):
        soup, title, desc, kw, lang = self.parse(rel)
        out_rel = self.page_map[rel]
        tf = Transformer(self.src, self.rw, rel, out_rel)
        body = tf.run(soup)
        root = rel_root(out_rel)

        slug = M.PAGE_SECTION.get(rel)
        sec = next((s for s in M.SECTIONS if s[0] == slug), None)
        label, blurb = M.INDEX_LABEL.get(rel, (None, None))

        h1 = tf.title_lines[0] if tf.title_lines else (label or title or rel)
        subtitle = " ".join(tf.title_lines[1:]) if len(tf.title_lines) > 1 else ""
        # the original title block sometimes repeated the site's column name
        column = ""
        m = re.search(r'["“]?\s*Radio Corner\s*["”]?\s*(?:di\s*R\.?\s*Chirio)?', subtitle, re.I)
        if m:
            column = re.sub(r"\s{2,}", " ", m.group(0)).strip(' "“”')
            subtitle = (subtitle[:m.start()] + " " + subtitle[m.end():])
        subtitle = re.sub(r"\s{2,}", " ", subtitle).strip(" -–·|")

        kicker = sec[1] if sec else ("Documenti" if rel in M.LEGAL_PAGES else "")
        trail = [(f"{root}index.html", "Chirio.com")]
        if sec:
            trail.append((f"{root}index.html#{sec[0]}", sec[1]))
        trail.append((None, label or h1))

        inner = body.decode_contents() if hasattr(body, "decode_contents") else str(body)
        toc_side = toc_html(tf.headings)
        toc_mob = toc_html(tf.headings, mobile=True)

        related = self.related_html(rel, slug, root)
        meta_bits = []
        if sec:
            meta_bits.append(f'<span><a href="{root}index.html#{sec[0]}">{esc(sec[1])}</a></span>')
        meta_bits.append("<span>Roberto Chirio</span>")
        if column:
            meta_bits.append(f'<span>“{esc(column)}” di R. Chirio</span>')

        page = f"""<div class="wrap page{' has-aside' if toc_side else ''}">
  <main id="main">
    <article class="article">
      <header class="article-head">
        {f'<p class="kicker">{esc(kicker)}</p>' if kicker else ''}
        <h1>{esc(h1)}</h1>
        {f'<p class="subtitle">{esc(subtitle)}</p>' if subtitle else ''}
        <p class="meta">{''.join(meta_bits)}</p>
      </header>
      {toc_mob}
      <div class="prose">
{inner}
      </div>
    </article>
{related}
  </main>
{f'<aside class="aside-col" aria-label="Indice della pagina">{toc_side}</aside>' if toc_side else ''}
</div>"""

        self.write(out_rel, document(
            root=root, lang=lang, title=title or h1, description=desc, keywords=kw,
            body=page, section=slug, trail=trail))

        if tf.auto_alt:
            self.stats["auto_alt_cleared"] += tf.auto_alt
        self.page_info[rel] = {"out": out_rel, "h1": h1, "title": title,
                               "desc": desc, "section": slug, "headings": tf.headings}
        self.search.append({"u": out_rel, "t": label or h1,
                            "s": sec[1] if sec else "Documenti",
                            "d": blurb or desc, "g": kw[:400]})
        self.stats["articles" if rel not in M.LEGAL_PAGES else "legal"] += 1

    def related_html(self, rel, slug, root):
        if not slug:
            return ""
        peers = [p for p, s in M.PAGE_SECTION.items() if s == slug and p != rel]
        if not peers:
            return ""
        order = list(M.PAGE_SECTION)
        peers.sort(key=order.index)
        sec = next(s for s in M.SECTIONS if s[0] == slug)
        cards = []
        for p in peers[:9]:
            label, blurb = M.INDEX_LABEL.get(p, (p, ""))
            cards.append(f'<li><a href="{root}{esc(self.page_map[p])}">'
                         f'<span class="c-sec">{esc(sec[1])}</span>{esc(label)}</a></li>')
        return f"""    <section class="related" aria-labelledby="related-h">
      <h2 id="related-h">Altre pagine in “{esc(sec[1])}”</h2>
      <ul class="card-grid">
{chr(10).join(cards)}
      </ul>
    </section>"""

    # -- 5. homepage -------------------------------------------------------- #

    def build_home(self, rel):
        soup, title, desc, kw, lang = self.parse(rel)
        out_rel = self.page_map[rel]
        # the original homepage is a pure link directory; it is rebuilt from the
        # content inventory so that navigation reflects what is really here.
        self.load_home_thumbs(rel)
        banner = self.src.real("IMAGES/chirio_com_04.jpg")
        # the wide Chaberton teaser photograph from the original homepage
        chab_banner = ""
        real = self.src.real("chaberton/images/chab_01_alba.jpg")
        if real:
            chab_banner = (f'<p class="center"><a href="chaberton/chab.htm">'
                           f'<img src="{esc(real)}" alt="La Batteria Chaberton all\'alba" '
                           f'width="480" height="144" loading="lazy" decoding="async"></a></p>')
        chab_hero = ""
        hero_img = (f'<img src="{esc(banner)}" alt="Chirio.com" width="800" height="73" '
                    f'decoding="async">') if banner else ""
        # the original homepage closed with a photograph of the Valle di Susa
        valle_full = self.src.real("IMAGES/valle_susa_chirio.jpg")
        valle_thumb = self.src.real("IMAGES/immagini_dallalto_small.jpg")
        # the author's own caption, read from the original homepage
        valle_cap = ""
        vimg = soup.find("img", src=lambda v: v and "immagini_dallalto" in v)
        if vimg is not None:
            holder = vimg.find_parent("tr") or vimg.find_parent("table")
            if holder is not None:
                valle_cap = txt(holder)
        valle_html = ""
        if valle_full and valle_thumb:
            valle_html = (
                f'<figure class="fig"><a class="zoom-link" href="{esc(valle_full)}" '
                f'title="Apri la fotografia a piena risoluzione">'
                f'<img src="{esc(valle_thumb)}" alt="Immagini dall\'alto della Valle di Susa" '
                f'width="100" height="98" loading="lazy" decoding="async"></a>'
                f'<figcaption>{esc(valle_cap)}</figcaption></figure>')
        email_img = self.src.real("IMAGES/email.jpg")
        contact_html = ""
        if email_img:
            contact_html = (
                f'<p class="contact"><strong>Roberto Chirio</strong> — e-mail: '
                f'<img src="{esc(email_img)}" alt="indirizzo e-mail pubblicato come '
                f'immagine sul sito originale" width="93" height="16" decoding="async">'
                f'</p>')

        blocks = []
        for slug, navlabel, heading, sdesc in M.SECTIONS:
            pages = [p for p, s in M.PAGE_SECTION.items() if s == slug]
            order = list(M.PAGE_SECTION)
            pages.sort(key=order.index)
            items = []
            for p in pages:
                label, blurb = M.INDEX_LABEL.get(p, (p, ""))
                out_p = self.page_map[p]
                thumb = (self.home_thumbs.get(out_p, (None,))[0]
                         or self.first_image(p))
                img = (f'<img src="{esc(thumb)}" alt="" width="72" height="54" '
                       f'loading="lazy" decoding="async">') if thumb else ""
                items.append(
                    f'<li><a href="{esc(self.page_map[p])}">{img}<span>'
                    f'<span class="t">{esc(label)}</span>'
                    f'<span class="d">{esc(blurb)}</span></span></a></li>')
            blocks.append(f"""      <section class="section-block" aria-labelledby="{slug}">
        <h2 id="{slug}">{esc(heading)}</h2>
        <p class="sec-desc">{esc(sdesc)}</p>
        <ul class="index-list">
{chr(10).join(items)}
        </ul>
      </section>""")

        chab_items = []
        for href, label in M.CHAB_NAV[1:]:
            if not self.src.exists(f"chaberton/{href}"):
                continue
            th = self.home_thumbs.get(f"chaberton/{href}", (None,))[0]
            im = (f'<img src="{esc(th)}" alt="" width="72" height="54" loading="lazy" '
                  f'decoding="async">') if th else ""
            chab_items.append(f'<li><a href="chaberton/{esc(href)}">{im}<span>'
                              f'<span class="t">{esc(label)}</span></span></a></li>')
        blocks.append(f"""      <section class="section-block" aria-labelledby="chaberton">
        <h2 id="chaberton">La Batteria dello Chaberton</h2>
        <p class="sec-desc">Pubblicazione virtuale dedicata alla batteria corazzata dello
          Chaberton (3130 m s.l.m.): storia, fortificazioni, tunnel, teleferica, panoramiche
          a 360°, gallerie fotografiche e video d'archivio.</p>
        {chab_banner}
        <ul class="index-list">
          <li><a href="chaberton/chab.htm">{chab_hero}<span><span class="t">Ingresso alla sezione Chaberton</span>
            <span class="d">Indice completo della pubblicazione</span></span></a></li>
{chr(10).join(chab_items)}
        </ul>
      </section>""")

        legal = "\n".join(
            f'<li><a href="{esc(p)}"><span><span class="t">{esc(M.INDEX_LABEL[p][0])}</span>'
            f'<span class="d">{esc(M.INDEX_LABEL[p][1])}</span></span></a></li>'
            for p in M.LEGAL_PAGES if self.src.exists(p))
        blocks.append(f"""      <section class="section-block" aria-labelledby="documenti">
        <h2 id="documenti">Documenti e note legali</h2>
        <ul class="index-list">
{legal}
        </ul>
      </section>""")

        total = len([p for p in M.PAGE_SECTION])
        body = f"""<div class="wrap page">
  <main id="main">
    <div class="home-hero">
      {hero_img}
      <h1>Chirio.com — archivio tecnico di elettronica e radio</h1>
      <p class="lede">Progetti e note di laboratorio di Roberto Chirio: antenne attive per
        HF e VLF, generatori a radiofrequenza, alimentatori switching, illuminazione a LED,
        contatori Geiger, prove su batterie e accumulatori. Insieme all'archivio storico
        dedicato alla <a href="chaberton/chab.htm">Batteria dello Chaberton</a>.</p>
      <p class="meta">{total} pagine tecniche · sezione storica Chaberton · ultimo aggiornamento dell'archivio originale: 15 marzo 2026</p>
      {contact_html}
    </div>

    <div class="site-search no-js-hide">
      <label for="site-search-input">Cerca nell'archivio</label>
      <input type="search" id="site-search-input" autocomplete="off" spellcheck="false"
             placeholder="es. mini whip, geiger, ATX, torcia LED…">
      <p id="search-status" role="status" aria-live="polite"></p>
      <ul id="search-results"></ul>
    </div>

{chr(10).join(blocks)}
    {valle_html}
  </main>
</div>"""
        self.write(out_rel, document(
            root="", lang=lang, title=title or "Chirio.com", description=desc,
            keywords=kw, body=body, trail=None))
        # legacy lowercase URL kept alive
        self.write("index.htm",
                   '<!DOCTYPE html>\n<html lang="it">\n<head>\n<meta charset="utf-8">\n'
                   '<title>Chirio.com</title>\n'
                   '<link rel="canonical" href="https://chirio.com/">\n'
                   '<meta http-equiv="refresh" content="0; url=./index.html">\n'
                   '</head>\n<body>\n<p>Questa pagina si trova ora su '
                   '<a href="./index.html">chirio.com</a>.</p>\n</body>\n</html>\n')
        self.stats["home"] += 1

    def load_home_thumbs(self, home_rel):
        """The original homepage paired each link with its own small thumbnail;
        reuse exactly those images so no asset reference is lost."""
        self.home_thumbs = {}
        soup = BeautifulSoup(self.src.read_text(home_rel), "html5lib")
        for a in soup.find_all("a", href=True):
            img = a.find("img")
            if img is None or not img.get("src"):
                continue
            page, k1 = self.rw.resolve(home_rel, a["href"])
            thumb, k2 = self.rw.resolve(home_rel, img["src"])
            if not page or not thumb or k1 != "page" or k2 != "asset":
                continue
            self.home_thumbs.setdefault(page, (thumb, img.get("alt") or "",
                                               img.get("width"), img.get("height")))

    _first_img_cache: dict[str, str] = {}

    def first_image(self, rel):
        """First reasonably sized image on a page — used as its index thumbnail."""
        if rel in self._first_img_cache:
            return self._first_img_cache[rel]
        best = ""
        try:
            raw = self.src.read_text(rel)
        except OSError:
            self._first_img_cache[rel] = ""
            return ""
        for m in re.finditer(r"<img[^>]*>", raw, re.I):
            tag = m.group(0)
            s = re.search(r'src\s*=\s*"([^"]+)"', tag, re.I)
            if not s:
                continue
            w = re.search(r'width\s*=\s*"?(\d+)', tag, re.I)
            h = re.search(r'height\s*=\s*"?(\d+)', tag, re.I)
            if w and h and (int(w.group(1)) < 120 or int(h.group(1)) < 80):
                continue
            new, kind = self.rw.resolve(rel, s.group(1))
            if new and kind == "asset" and os.path.splitext(new)[1].lower() in (
                    ".jpg", ".jpeg", ".png", ".gif"):
                best = new
                break
        self._first_img_cache[rel] = best
        return best

    # -- 6. chaberton ------------------------------------------------------- #

    @staticmethod
    def chab_prefix(rel):
        """Relative path from *rel* to the chaberton/ directory."""
        p = os.path.relpath("chaberton", os.path.dirname(rel)).replace(os.sep, "/")
        return "" if p == "." else p + "/"

    def chab_trail(self, rel, label, extra=None):
        root = rel_root(rel)
        trail = [(f"{root}index.html", "Chirio.com"),
                 (self.chab_prefix(rel) + "chab.htm", "Chaberton")]
        if extra:
            trail.extend(extra)
        trail.append((None, label))
        return trail

    def build_chab_page(self, rel):
        soup, title, desc, kw, lang = self.parse(rel)
        tf = Transformer(self.src, self.rw, rel, rel)
        body = tf.run(soup)
        root = rel_root(rel)
        tail = rel[len("chaberton/"):]
        label = dict(M.CHAB_NAV).get(tail, txt(soup.title) or tail)
        h1 = tf.title_lines[0] if tf.title_lines else label
        subtitle = " ".join(tf.title_lines[1:]) if len(tf.title_lines) > 1 else ""
        inner = body.decode_contents()
        toc_side = toc_html(tf.headings)
        page = f"""<div class="wrap page{' has-aside' if toc_side else ''}">
  <main id="main">
    <article class="article">
      <header class="article-head">
        <p class="kicker">La Batteria dello Chaberton</p>
        <h1>{esc(h1)}</h1>
        {f'<p class="subtitle">{esc(subtitle)}</p>' if subtitle else ''}
      </header>
      {toc_html(tf.headings, mobile=True)}
      <div class="prose">
{inner}
      </div>
    </article>
  </main>
{f'<aside class="aside-col" aria-label="Indice della pagina">{toc_side}</aside>' if toc_side else ''}
</div>"""
        self.write(rel, document(
            root=root, lang=lang, title=title or f"{label} — Chaberton",
            description=desc, keywords=kw, body=page, chaberton=True,
            active_page=tail, trail=self.chab_trail(rel, label),
            chab_prefix=self.chab_prefix(rel)))
        self.search.append({"u": rel, "t": h1, "s": "Chaberton",
                            "d": desc, "g": kw[:400]})
        self.stats["chaberton"] += 1

    def build_gallery_index(self, rel):
        soup, title, desc, kw, lang = self.parse(rel)
        d = rel[len("chaberton/"):].split("/")[0]
        gtitle = M.CHAB_GALLERIES.get(d, (None, d))[1]
        root = rel_root(rel)

        # Some gallery entry points are FrontPage framesets that framed the real
        # thumbnail page.  Framesets are obsolete, so the framed page's content
        # is rendered directly at the frameset's URL (which stays valid).
        fs = soup.find("frameset")
        if fs is not None:
            inner = None
            for fr in soup.find_all("frame"):
                cand = (fr.get("src") or "").strip()
                if not cand or "testa" in cand.lower() or cand.startswith(".."):
                    continue
                t = os.path.normpath(os.path.join(os.path.dirname(rel), cand)
                                     ).replace(os.sep, "/")
                if self.src.exists(t):
                    inner = self.src.real(t)
                    break
            if inner:
                note("replaced", f"{rel}: <frameset> replaced by the framed gallery "
                                 f"content from {inner} (URL preserved)")
                soup = BeautifulSoup(self.src.read_text(inner), "html5lib")
                for sc in soup.find_all("script"):
                    sc.decompose()
                if not title or "frame" in title.lower():
                    title = txt(soup.title) if soup.title else gtitle
                rel_for_links = inner
            else:
                rel_for_links = rel
        else:
            rel_for_links = rel

        # FrontPage laid some galleries out as a row of thumbnails followed by a
        # row of file-name captions, each with its own link; collect those first
        # so no caption is lost.
        cap_by_href = {}
        for a in soup.find_all("a", href=True):
            if a.find("img"):
                continue
            t = txt(a)
            if t:
                cap_by_href.setdefault(a["href"].strip(), t)

        # collect thumbnail -> photo page pairs, in document order
        items, seen = [], set()
        for a in soup.find_all("a", href=True):
            img = a.find("img")
            if not img or not img.get("src"):
                continue
            href, k1 = self.rw.resolve(rel_for_links, a["href"])
            src, k2 = self.rw.resolve(rel_for_links, img["src"])
            if not href or not src or k1 != "page":
                continue
            if rel_for_links != rel:
                # re-base onto the frameset page's own directory
                abs_href = os.path.normpath(os.path.join(
                    os.path.dirname(rel_for_links), href)).replace(os.sep, "/")
                abs_src = os.path.normpath(os.path.join(
                    os.path.dirname(rel_for_links), src)).replace(os.sep, "/")
                href = os.path.relpath(abs_href, os.path.dirname(rel)).replace(os.sep, "/")
                src = os.path.relpath(abs_src, os.path.dirname(rel)).replace(os.sep, "/")
            if href in seen:
                continue
            seen.add(href)
            # the original printed the file name under each thumbnail
            cap = cap_by_href.get(a["href"].strip(), "")
            if not cap:
                cell = a.find_parent(["td", "th", "p", "div"]) or a.parent
                cap = txt(cell) if cell is not None else ""
            if not cap:
                cap = txt(img.get("alt") or "") or os.path.basename(src)
            items.append((href, src, cap))
        # the gallery's own description: the first substantial run of text that
        # is neither a thumbnail nor the standing copyright notice
        intro = []
        for el in soup.find_all(["p", "td", "font"]):
            if el.find(["img", "table"]):
                continue
            t = txt(el)
            if len(t) < 20 or t in intro or BOILERPLATE_RE.search(t):
                continue
            if any(t in prev or prev in t for prev in intro):
                continue
            intro.append(t)
        intro_html = "".join(f"<p>{esc(t)}</p>" for t in intro[:3])
        cells = "\n".join(
            f'        <li><a href="{esc(h)}"><img src="{esc(s)}" alt="" loading="lazy" '
            f'decoding="async"><span class="cap">{esc(c)}</span></a></li>'
            for h, s, c in items)
        page = f"""<div class="wrap page">
  <main id="main">
    <article class="article">
      <header class="article-head">
        <p class="kicker">Galleria fotografica · Chaberton</p>
        <h1>{esc(gtitle)}</h1>
        <p class="meta"><span>{len(items)} fotografie</span><span>Roberto Chirio</span></p>
      </header>
      <div class="prose">
        {intro_html}
      </div>
      <ul class="gallery">
{cells}
      </ul>
      <p class="center"><a href="{self.chab_prefix(rel)}foto_chaberton.HTM">Tutte le gallerie fotografiche</a></p>
    </article>
  </main>
</div>"""
        self.write(rel, document(
            root=root, lang=lang, title=title or gtitle, description=desc,
            keywords=kw, body=page, chaberton=True, active_page="foto_chaberton.HTM",
            chab_prefix=self.chab_prefix(rel),
            trail=self.chab_trail(rel, gtitle,
                                  [(self.chab_prefix(rel) + "foto_chaberton.HTM", "Foto")])))
        self.search.append({"u": rel, "t": gtitle, "s": "Chaberton · gallerie",
                            "d": (intro[0][:160] if intro else desc), "g": ""})
        self.stats["gallery"] += 1
        return items, (intro[0] if intro else "")

    def build_photo_page(self, rel, order_ctx):
        soup, title, desc, kw, lang = self.parse(rel)
        root = rel_root(rel)
        parts = rel.split("/")
        d = parts[1]
        gtitle = M.CHAB_GALLERIES.get(d, (None, d))[1]
        gal_index = M.CHAB_GALLERIES.get(d, ("index.htm", d))[0]

        # FrontPage galleries name the photo after the page: 005.htm -> 005.jpg
        stem = os.path.splitext(os.path.basename(rel))[0].lower()
        CHROME = ("home.gif", "next.gif", "previous.gif", "prev.gif", "up.gif",
                  "back.gif", "first.gif", "last.gif", "testa_", "background",
                  "indietro", "successivo")
        big, alt, best_area = None, "", -1
        for img in soup.find_all("img", src=True):
            src, kind = self.rw.resolve(rel, img["src"])
            if not src or kind != "asset":
                continue
            low = src.lower()
            if any(c in low for c in CHROME):
                continue
            if os.path.splitext(os.path.basename(low))[0] == stem:
                big, alt = src, (img.get("alt") or "")
                break
            try:
                area = int(img.get("width") or 0) * int(img.get("height") or 0)
            except ValueError:
                area = 0
            if area > best_area:
                big, alt, best_area = src, (img.get("alt") or ""), area

        # caption: text that belongs to this photo only — the repeated gallery
        # description, the bare file name and the copyright notice are chrome.
        # Text belonging to this page: the gallery's own description line is
        # kept as the page subtitle, per-photo text becomes the figure caption,
        # and the standing copyright notice lives in the site footer.
        gdesc = norm_key(order_ctx.get("_desc", {}).get(d, ""))
        photo_name = os.path.splitext(os.path.basename(big or rel))[0]
        drop_keys = {norm_key(photo_name), norm_key(photo_name + ".jpg"),
                     norm_key(os.path.basename(unquote(big or "")))}
        subtitle, caps, seen_keys = "", [], set()
        for el in soup.find_all(["p", "td", "font"]):
            if el.find(["img", "a", "table"]):
                continue
            t = txt(el)
            if not t or len(t) < 2:
                continue
            k = norm_key(t)
            if not k or k in seen_keys or k in drop_keys:
                continue
            if BOILERPLATE_RE.search(t):
                seen_keys.add(k)
                continue
            if any(k in prev or prev in k for prev in seen_keys):
                continue
            seen_keys.add(k)
            if not subtitle and gdesc and (k in gdesc or gdesc in k):
                subtitle = t
            else:
                caps.append(t)
        if not subtitle and caps and len(caps) > 1:
            subtitle = caps.pop(0)
        caption = " ".join(caps)[:800]

        seq = order_ctx.get(d, [])
        cur = seq.index(rel) if rel in seq else -1
        prev_rel = seq[cur - 1] if cur > 0 else None
        next_rel = seq[cur + 1] if 0 <= cur < len(seq) - 1 else None

        def relurl(target):
            return os.path.relpath(target, os.path.dirname(rel)).replace(os.sep, "/")

        prev_html = (f'<a href="{esc(relurl(prev_rel))}" data-photo-prev rel="prev">'
                     f'← Precedente</a>' if prev_rel else '<span>← Precedente</span>')
        next_html = (f'<a href="{esc(relurl(next_rel))}" data-photo-next rel="next">'
                     f'Successiva →</a>' if next_rel else '<span>Successiva →</span>')
        counter = f'<span class="photo-count">{cur + 1} di {len(seq)}</span>' if seq else ""

        dims = ""
        img_html = ""
        if big:
            try:
                from PIL import Image
                real = self.src.real(os.path.normpath(
                    os.path.join(os.path.dirname(rel), big)).replace(os.sep, "/"))
                if real:
                    iw, ih = Image.open(self.src.abspath(real)).size
                    dims = f' width="{iw}" height="{ih}"'
            except Exception:
                dims = ""
            orig_name = os.path.basename(unquote(big))
            img_html = (f'<a class="zoom-link" href="{esc(big)}" title="Apri la fotografia '
                        f'a piena risoluzione"><img src="{esc(big)}" alt="{esc(alt or caption[:120])}"'
                        f'{dims} decoding="async"></a>'
                        f'<span class="img-note">{esc(orig_name)} — apri l\'immagine '
                        f'per vederla a piena risoluzione</span>')

        page = f"""<div class="wrap page">
  <main id="main">
    <article class="article">
      <header class="article-head">
        <p class="kicker">{esc(gtitle)}</p>
        <h1>{esc(photo_name)}</h1>
        {f'<p class="subtitle">{esc(subtitle)}</p>' if subtitle else ''}
      </header>
      <nav class="photo-nav" aria-label="Navigazione fotografie">
        {prev_html}
        <a href="{esc(relurl(f'chaberton/{d}/{gal_index}'))}">Indice galleria</a>
        {next_html}
        {counter}
      </nav>
      <figure class="photo-view">
        {img_html}
        {f'<figcaption>{esc(caption)}</figcaption>' if caption else ''}
      </figure>
      <nav class="photo-nav" aria-label="Navigazione fotografie (fine pagina)">
        {prev_html}
        <a href="{esc(relurl(f'chaberton/{d}/{gal_index}'))}">Indice galleria</a>
        {next_html}
      </nav>
    </article>
  </main>
</div>"""
        self.write(rel, document(
            root=root, lang=lang, title=title or f"{photo_name} — {gtitle}",
            description=caption[:180] or desc, keywords=kw, body=page,
            chaberton=True, active_page="foto_chaberton.HTM",
            chab_prefix=self.chab_prefix(rel),
            trail=self.chab_trail(rel, photo_name, [
                (relurl(f"chaberton/{d}/{gal_index}"), gtitle)])))
        self.stats["photo"] += 1

    def build_panorama(self, rel):
        soup, title, desc, kw, lang = self.parse(rel)
        root = rel_root(rel)
        tail = rel[len("chaberton/"):]
        pano, pano_title = M.CHAB_PANORAMAS[tail]
        pano_url = os.path.relpath(f"chaberton/{pano}", os.path.dirname(rel)).replace(os.sep, "/")
        # descriptive text of the original page (everything that is not chrome)
        applet = soup.find("applet")
        if applet:
            applet.decompose()
        tf = Transformer(self.src, self.rw, rel, rel)
        body = tf.run(soup)
        inner = body.decode_contents()
        h1 = pano_title
        pano_subtitle = " · ".join(tf.title_lines) if tf.title_lines else ""

        try:
            from PIL import Image
            iw, ih = Image.open(self.src.abspath(self.src.real(f"chaberton/{pano}"))).size
            dims = f' width="{iw}" height="{ih}"'
            size_note = f"{iw}×{ih} pixel"
        except Exception:
            dims, size_note = "", ""

        viewer = f"""      <div class="pano">
        <div class="pano-strip" tabindex="0" role="img"
             aria-label="Panoramica a 360° del Forte Chaberton — trascina o usa le frecce per scorrere">
          <img src="{esc(pano_url)}" alt=""{dims} decoding="async">
        </div>
        <div class="pano-bar">
          <button type="button" data-pano-auto aria-pressed="false"
                  data-play="Scorri automaticamente" data-stop="Ferma">Scorri automaticamente</button>
          <button type="button" data-pano-full>Schermo intero</button>
          <span class="pano-hint">Trascina con il mouse o usa ← → · {esc(size_note)}</span>
        </div>
      </div>
      <p class="center"><a class="download" href="{esc(pano_url)}">Immagine panoramica originale</a></p>"""

        page = f"""<div class="wrap page">
  <main id="main">
    <article class="article">
      <header class="article-head">
        <p class="kicker">Panoramiche 360° · Chaberton</p>
        <h1>{esc(h1)}</h1>
        {f'<p class="subtitle">{esc(pano_subtitle)}</p>' if pano_subtitle else ''}
      </header>
{viewer}
      <div class="prose">
{inner}
      </div>
      <p><a href="{self.chab_prefix(rel)}pan_360.HTM">Tutte le panoramiche a 360°</a></p>
    </article>
  </main>
</div>"""
        self.write(rel, document(
            root=root, lang=lang, title=title or h1, description=desc, keywords=kw,
            body=page, chaberton=True, active_page="pan_360.HTM",
            chab_prefix=self.chab_prefix(rel),
            trail=self.chab_trail(rel, h1, [
                (self.chab_prefix(rel) + "pan_360.HTM", "Panoramiche 360°")])))
        note("replaced", f"{rel}: Java ptviewer applet replaced with a plain-JavaScript panorama viewer")
        self.stats["panorama"] += 1

    # -- 7. orchestration --------------------------------------------------- #

    def run(self):
        print("· planning URLs")
        self.plan_urls()
        print("· copying assets")
        self.copy_assets()
        self.make_pano_previews()

        pages = self.src.pages()
        groups = defaultdict(list)
        for p in pages:
            groups[self.classify(p)].append(p)

        # photo-page ordering per gallery (document order of the gallery index)
        order_ctx: dict = {"_desc": {}}
        print("· galleries")
        for rel in groups["gallery"]:
            items, gdesc = self.build_gallery_index(rel)
            d = rel[len("chaberton/"):].split("/")[0]
            if gdesc and not order_ctx["_desc"].get(d):
                order_ctx["_desc"][d] = gdesc
            seq = []
            for href, _s, _c in items:
                t = os.path.normpath(os.path.join(os.path.dirname(rel), href)).replace(os.sep, "/")
                if self.src.exists(t):
                    seq.append(self.src.real(t))
            if seq and not order_ctx.get(d):
                order_ctx[d] = seq

        print("· photo pages")
        for rel in groups["photo"]:
            d = rel.split("/")[1]
            if rel not in order_ctx.get(d, []):
                order_ctx.setdefault(d, []).append(rel)
                note("orphan", f"{rel}: photo page not listed in its gallery index — kept and appended")
        for rel in groups["photo"]:
            self.build_photo_page(rel, order_ctx)

        print("· chaberton pages")
        for rel in groups["chab"]:
            self.build_chab_page(rel)
        for rel in groups["panorama"]:
            self.build_panorama(rel)

        print("· articles")
        for rel in groups["article"] + groups["legal"]:
            self.build_article(rel)

        print("· homepage")
        for rel in groups["home"]:
            self.build_home(rel)

        print("· site assets")
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ("site.css", "site.js"):
            shutil.copy2(os.path.join(here, name), os.path.join(self.out, "assets", name)) \
                if os.path.isdir(os.path.join(self.out, "assets")) else None
        os.makedirs(os.path.join(self.out, "assets"), exist_ok=True)
        for name in ("site.css", "site.js"):
            shutil.copy2(os.path.join(here, name), os.path.join(self.out, "assets", name))
            self.written.add(f"assets/{name}")
        # the generator itself, kept in a clearly separated development folder
        for name in ("build.py", "sitemeta.py", "site.css", "site.js",
                     "validate.py", "check_layout.py", "check_runtime.js",
                     "retrofit.py", "make_home.py", "shoot.py"):
            src_f = os.path.join(here, name)
            if os.path.exists(src_f):
                os.makedirs(os.path.join(self.out, "_dev"), exist_ok=True)
                shutil.copy2(src_f, os.path.join(self.out, "_dev", name))
                self.written.add(f"_dev/{name}")
        readme = os.path.join(here, "DEV-README.md")
        if os.path.exists(readme):
            shutil.copy2(readme, os.path.join(self.out, "_dev", "README.md"))
            self.written.add("_dev/README.md")

        self.write("assets/search-index.json",
                   json.dumps(self.search, ensure_ascii=False, separators=(",", ":")))
        self.write(".nojekyll", "")
        self.write("CNAME", "chirio.com\n")
        self.write("robots.txt", "User-agent: *\nAllow: /\nSitemap: https://chirio.com/sitemap.xml\n")
        self.build_sitemap()
        self.write("404.html", document(
            root="", lang="it", title="Pagina non trovata — Chirio.com",
            description="", keywords="", body="""<div class="wrap page">
  <main id="main">
    <article class="article">
      <header class="article-head">
        <p class="kicker">Errore 404</p>
        <h1>Pagina non trovata</h1>
      </header>
      <div class="prose">
        <p>L'indirizzo richiesto non esiste (o non esiste più) su questo sito.</p>
        <p>Puoi ripartire dall'<a href="/index.html">indice generale</a>, che elenca tutte
          le pagine tecniche e la sezione storica dedicata allo
          <a href="/chaberton/chab.htm">Chaberton</a>.</p>
      </div>
    </article>
  </main>
</div>"""))

        print("· report")
        self.print_report()

    def build_sitemap(self):
        urls = []
        for rel in sorted(self.written):
            if rel.startswith("_dev/"):
                continue
            if os.path.splitext(rel)[1].lower() in HTML_EXT and rel != "index.htm":
                loc = "https://chirio.com/" + ("" if rel == "index.html" else rel)
                urls.append(f"  <url><loc>{esc(loc)}</loc></url>")
        self.write("sitemap.xml",
                   '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                   + "\n".join(urls) + "\n</urlset>\n")

    def print_report(self):
        print("\n──────── build summary ────────")
        for k in sorted(self.stats):
            print(f"  {k:>16}: {self.stats[k]}")
        print(f"  {'html written':>16}: "
              f"{sum(1 for w in self.written if os.path.splitext(w)[1].lower() in HTML_EXT)}")
        for kind in sorted(REPORT):
            items = REPORT[kind]
            print(f"\n  [{kind}] {len(items)}")
            for i in items[:200]:
                print("    -", i)
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "build-report.txt"), "w", encoding="utf-8") as fh:
            for kind in sorted(REPORT):
                fh.write(f"[{kind}] {len(REPORT[kind])}\n")
                for i in REPORT[kind]:
                    fh.write(f"  - {i}\n")
                fh.write("\n")


# --------------------------------------------------------------------------- #
# FROZEN OUTPUT GUARD
# --------------------------------------------------------------------------- #
#
# The generated HTML is no longer the product of this file. Since the redesign,
# ``chirio-modern/`` is the canonical, hand-maintained source: pages carry a
# design system, curated navigation and per-page editorial work that this
# importer knows nothing about. Re-running it over a live site would silently
# destroy that work.
#
# build.py is kept as documented provenance — it records exactly how the
# FrontPage filebase was converted — and it can still be re-run into an *empty*
# directory to reproduce the original import. It refuses to write into a
# directory that already contains a redesigned site unless you pass
# ``--i-know-this-overwrites-the-redesign``.
#
# To change the live site, edit the HTML, or use _dev/retrofit.py for a
# reviewed repetitive pass.

FREEZE_MARKER = "site.css"
FREEZE_SENTINEL = "Chirio.com — design system"


def refuse_if_redesigned(out_dir, override):
    """Abort rather than overwrite hand-maintained pages."""
    css = os.path.join(out_dir, "assets", FREEZE_MARKER)
    curated = os.path.join(out_dir, "_dev", "curated.txt")
    redesigned = False
    if os.path.exists(css):
        try:
            redesigned = FREEZE_SENTINEL in open(css, encoding="utf-8").read(4000)
        except OSError:
            redesigned = False
    if not redesigned and os.path.exists(curated):
        redesigned = True
    if redesigned and not override:
        sys.stderr.write(
            "\n"
            "  REFUSING TO RUN\n"
            "  ---------------\n"
            f"  {out_dir}\n"
            "  contains the redesigned, hand-maintained site. Running build.py\n"
            "  would overwrite the design system, the curated homepage and every\n"
            "  page-level editorial fix.\n\n"
            "  * to edit the live site: edit the HTML directly\n"
            "  * for a repetitive reviewed change: use _dev/retrofit.py\n"
            "  * to reproduce the original import: run with --out on an EMPTY dir\n"
            "  * if you really mean it: --i-know-this-overwrites-the-redesign\n\n")
        raise SystemExit(2)



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--i-know-this-overwrites-the-redesign", action="store_true",
                    dest="override", help=argparse.SUPPRESS)
    a = ap.parse_args()
    refuse_if_redesigned(os.path.abspath(a.out), a.override)
    b = Builder(a.src, a.out)
    b.run()


if __name__ == "__main__":
    main()
