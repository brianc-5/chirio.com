#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emit the hand-designed homepage once.

The layout, copy, editorial selection and ordering below are authored by hand;
this script only interpolates the archive inventory so the category counts and
the 66 links cannot drift from reality. After it runs, ``index.html`` is listed
in ``_dev/curated.txt`` and is never regenerated — edit the file directly.
"""

from __future__ import annotations

import argparse
import html
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import retrofit as R  # noqa: E402


def esc(s):
    return html.escape(s or "", quote=True)


# --- editorial selection ---------------------------------------------------- #

# Three projects that best represent what this archive is: a signature antenna,
# a measuring instrument, a bench power supply. Each image is the author's own
# photograph, taken from the page it links to.
FEATURED = [
    ("mini_whip.htm", "IMAGES/mini_whip_034.jpg", "Radio & antenne",
     "Mini Whip — antenna attiva HF/VLF",
     "L’antenna capacitiva da 10 kHz a 30 MHz che dà il nome al progetto più "
     "seguito del sito, in cinque versioni."),
    ("geiger_counter.htm", "IMAGES/geiger_pc_008.jpg", "Radioattività",
     "Misura ambientale delle radiazioni",
     "Un contatore Geiger collegato al PC per registrare il fondo naturale e le "
     "sue variazioni."),
    ("switching_power_supply_atx.htm", "IMAGES/atx_005.jpg", "Alimentatori",
     "Alimentatore da laboratorio da un ATX",
     "Come trasformare un alimentatore per computer in uno strumento da banco "
     "regolabile e protetto."),
]

# Entry points for someone arriving without a specific question.
START_HERE = [
    ("legge_di_ohm.htm", "La legge di Ohm",
     "I fondamenti, spiegati per chi comincia."),
    ("led_light_emitting_diodes.htm", "Cosa è un LED",
     "Come funziona e come si alimenta correttamente."),
    ("battery_test.htm", "Come testare le batterie",
     "Il metodo di misura usato in tutte le prove del sito."),
]

HERO_IMG = ("IMAGES/SPM_15_02.jpg", "mini_whip.htm",
            "Misure di ascolto HF e VLF con un selective level meter "
            "Wandel &amp; Goltermann SPM 15, dalla pagina Mini Whip.")

CHAB_IMG = "chaberton/images/chab_01_alba.jpg"

# The original homepage closed with an aerial photograph of the Valle di Susa.
# Image, link target and caption are all the author's own.
VALLE = ("IMAGES/immagini_dallalto_small.jpg", "IMAGES/valle_susa_chirio.jpg",
         "Valle di Susa, immagini dall’alto — foto di Roberto Chirio.",
         "In volo con aereo a motore sulla valle Susa, fotografando verso il basso: "
         "paesi e viste mozzafiato con foto spettacolari sulle montagne della "
         "Valle di Susa.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    a = ap.parse_args()
    site = os.path.abspath(a.site)
    sys.path.insert(0, os.path.join(site, "_dev"))
    import sitemeta as meta
    meta.NAV_SHORT = {"radio": "Radio", "alimentatori": "Alimentatori",
                      "batterie": "Batterie", "led": "LED",
                      "radioattivita": "Radioattività", "misure": "Misure",
                      "progetti": "Progetti"}
    meta.CHAB_COUNT = 185

    counts = Counter(meta.PAGE_SECTION.values())
    order = list(meta.PAGE_SECTION)
    total = len(meta.PAGE_SECTION)

    # --- featured cards ---------------------------------------------------- #
    feats = []
    for href, img, sec, title, desc in FEATURED:
        feats.append(f'''        <a class="card-feature" href="{esc(href)}">
          <img src="{esc(img)}" alt="" width="600" height="375" loading="lazy" decoding="async">
          <span class="card-body">
            <span class="card-sec">{esc(sec)}</span>
            <span class="card-title">{esc(title)}</span>
            <span class="card-desc">{esc(desc)}</span>
          </span>
        </a>''')

    starts = []
    for href, title, desc in START_HERE:
        starts.append(f'''        <a class="card-text" href="{esc(href)}">
          <span class="card-title">{esc(title)}</span>
          <span class="card-desc">{esc(desc)}</span>
        </a>''')

    # --- category overview -------------------------------------------------- #
    tiles = []
    for slug, label, _heading, desc in meta.SECTIONS:
        tiles.append(f'''        <a class="tile" href="#{slug}">
          <span class="tile-top"><span class="tile-name">{esc(meta.NAV_SHORT[slug])}</span>
            <span class="count">{counts[slug]}</span></span>
          <span class="tile-desc">{esc(desc)}</span>
        </a>''')

    # --- full archive, one disclosure per category -------------------------- #
    #
    # The list carries the id, not the <details>. Linking to an element *inside*
    # a closed <details> makes the browser expand it on its own, so a category
    # tile or a header link opens the right list with no JavaScript at all.
    #
    # The shared name= makes it an exclusive accordion: opening one category
    # closes the others, natively, still without JavaScript.
    thumbs = getattr(meta, "INDEX_THUMB", {})

    def row(p):
        t, d = meta.INDEX_LABEL.get(p, (p, ""))
        th = thumbs.get(p)
        img = (f'<img src="{esc(th)}" alt="" width="64" height="48" loading="lazy" decoding="async">'
               if th else '<span class="a-noimg" aria-hidden="true"></span>')
        return (f'            <li><a href="{esc(p)}">{img}'
                f'<span class="a-text"><span class="a-title">{esc(t)}</span>'
                f'<span class="a-desc">{esc(d)}</span></span></a></li>')

    blocks = []
    for slug, label, heading, desc in meta.SECTIONS:
        pages = sorted((p for p, s in meta.PAGE_SECTION.items() if s == slug),
                       key=order.index)
        blocks.append(f'''      <details class="cat" name="archivio" id="cat-{slug}">
        <summary><span>{esc(heading)}</span><span class="count">{counts[slug]}</span></summary>
        <ul id="{slug}">
{chr(10).join(row(p) for p in pages)}
        </ul>
      </details>''')

    blocks.append(f'''      <details class="cat" name="archivio" id="cat-documenti">
        <summary><span>Documenti e note legali</span><span class="count">{len(meta.LEGAL_PAGES)}</span></summary>
        <ul id="documenti">
{chr(10).join(row(p) for p in meta.LEGAL_PAGES)}
        </ul>
      </details>''')

    hero_img, hero_link, hero_cap = HERO_IMG

    doc = f'''<!DOCTYPE html>
<html lang="it" data-root="">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chirio.com — archivio tecnico di elettronica, radio e antenne</title>
  <meta name="description" content="Progetti e note di laboratorio di Roberto Chirio: antenne attive per HF e VLF, generatori a radiofrequenza, alimentatori switching, illuminazione a LED, contatori Geiger e prove su batterie. Con l’archivio storico della Batteria dello Chaberton.">
  <meta name="author" content="Roberto Chirio">
  <meta name="color-scheme" content="light dark">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
<a class="skip-link" href="#main">Vai al contenuto principale</a>
{R.build_header("", meta)}

<main id="main">

  <section class="hero">
    <div class="wrap hero-grid">
      <div>
        <p class="kicker">Archivio tecnico</p>
        <h1>Progetti di elettronica, radio e antenne.</h1>
        <p class="lede">Schemi, misure e prove di laboratorio di Roberto Chirio —
          antenne attive per HF e VLF, generatori a radiofrequenza, alimentatori
          switching, illuminazione a LED, contatori Geiger e caratterizzazione di
          batterie, raccolti in un unico archivio consultabile.</p>
        <p class="hero-stats"><span>{total} pagine tecniche</span><span>7 categorie</span><span>archivio storico Chaberton</span></p>
        <p class="hero-by"><strong>Roberto Chirio</strong> ·
          <a href="mailto:{R.EMAIL}">{R.EMAIL}</a></p>
        <p class="hero-actions">
          <a class="btn btn--primary" href="#archivio">Esplora i progetti</a>
          <a class="btn" href="chaberton/chab.htm">Archivio Chaberton</a>
        </p>
      </div>
      <figure class="hero-figure">
        <a href="{esc(hero_link)}"><img src="{esc(hero_img)}" alt="Ricevitore selettivo Wandel &amp; Goltermann SPM 15 su un banco di misura, con la frequenza di 7155,00 kHz sul display." width="1600" height="1067" decoding="async" fetchpriority="high"></a>
        <figcaption>{hero_cap}</figcaption>
      </figure>
    </div>
  </section>

  <div class="wrap">

    <section class="section" id="cerca">
      <div class="search">
        <label for="site-search-input">Cerca nell’archivio</label>
        <div class="search-field">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.6-3.6"></path></svg>
          <input type="search" id="site-search-input" autocomplete="off" spellcheck="false"
                 placeholder="mini whip, geiger, ATX, torcia LED…">
        </div>
        <p class="search-status js-only" id="search-status" role="status" aria-live="polite"></p>
        <ul class="search-results" id="search-results"></ul>
        <noscript><p class="search-status">La ricerca richiede JavaScript. L’indice
          completo dell’archivio è qui sotto, diviso per categoria.</p></noscript>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Inizia da qui</h2>
        <p>Tre pagine che spiegano le basi usate in tutto il resto dell’archivio.</p>
      </div>
      <div class="grid grid--3">
{chr(10).join(starts)}
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Progetti in evidenza</h2>
        <p>Le realizzazioni più complete, con schemi, misure e fotografie.</p>
      </div>
      <div class="grid grid--3">
{chr(10).join(feats)}
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Sfoglia per categoria</h2>
        <p>{total} pagine tecniche in sette aree.</p>
      </div>
      <div class="grid grid--tiles">
{chr(10).join(tiles)}
      </div>
    </section>

    <section class="section" id="archivio">
      <div class="section-head">
        <h2>Archivio completo</h2>
        <p>Ogni categoria si apre sull’elenco delle sue pagine.</p>
      </div>
      <div class="archive">
{chr(10).join(blocks)}
      </div>
    </section>

    <section class="section">
      <figure class="fig fig-photo valle">
        <a class="zoom-link" href="{esc(VALLE[1])}" title="Apri la fotografia a piena risoluzione"><img src="{esc(VALLE[0])}" alt="Veduta aerea della Valle di Susa ripresa da un aereo da turismo." width="100" height="98" loading="lazy" decoding="async"></a>
        <figcaption><strong>{esc(VALLE[2])}</strong><br>{esc(VALLE[3])}</figcaption>
      </figure>
    </section>

    <section class="section">
      <div class="chab-feature">
        <a href="chaberton/chab.htm" tabindex="-1" aria-hidden="true"><img src="{esc(CHAB_IMG)}" alt="" width="710" height="213" loading="lazy" decoding="async"></a>
        <div class="chab-body">
          <p class="kicker">Archivio storico</p>
          <h2><a href="chaberton/chab.htm">La Batteria dello Chaberton</a></h2>
          <p>A 3130 metri, la fortificazione più alta d’Europa. Una pubblicazione
            virtuale con la storia, le fortificazioni, i tunnel, la teleferica,
            le panoramiche a 360° e {meta.CHAB_COUNT} pagine di fotografie e video
            d’archivio.</p>
          <p class="chab-links">
            <a href="chaberton/storia_chaberton.htm">Storia</a>
            <a href="chaberton/fortificazioni.htm">Fortificazioni</a>
            <a href="chaberton/tunnel_chaberton.htm">Tunnel</a>
            <a href="chaberton/teleferica_chaberton.htm">Teleferica</a>
            <a href="chaberton/pan_360.HTM">Panoramiche 360°</a>
            <a href="chaberton/foto_chaberton.HTM">Gallerie fotografiche</a>
          </p>
        </div>
      </div>
    </section>

  </div>
</main>

{R.build_footer("", meta)}
<script src="assets/site.js" defer></script>
</body>
</html>
'''

    out = os.path.join(site, "index.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)
    print(f"homepage written: {out} ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
