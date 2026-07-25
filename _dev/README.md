# `_dev/` — how this site is edited

**Nothing in this folder is needed to serve the site.** Everything above it is
finished static HTML, CSS and JavaScript. Push the parent folder to GitHub
Pages and it works, with no build step.

---

## Read this first: the generated output is frozen

The site began as an automated import of a Microsoft FrontPage filebase, made
by `build.py`. **That is no longer how these pages are produced.**

Since the redesign, **the HTML in `chirio-modern/` is the source of truth.** It
carries a design system, a hand-built homepage, a hand-built Chaberton landing
page and page-level editorial work that `build.py` knows nothing about.

`build.py` now **refuses to run** against a directory that contains the
redesigned site:

```
$ python3 _dev/build.py --src ../.. --out .

  REFUSING TO RUN
  ---------------
  … contains the redesigned, hand-maintained site.
```

It can still reproduce the original import into an *empty* directory, which is
why it is kept: it documents exactly how the FrontPage material was converted.

### So how do I change something?

| I want to… | Do this |
| --- | --- |
| fix wording, a heading, an image on one page | edit that `.htm` file directly, then re-run the i18n pipeline so `/en/` follows |
| fix an English translation | edit `_dev/i18n/map.en.json`, then re-run `i18n_build.py` |
| change colour, type, spacing, a component | edit `assets/site.css` |
| change behaviour (menu, search, panorama) | edit `assets/site.js` |
| make the same mechanical change on many pages | write it into `retrofit.py`, run it, read the notes, review the diff |
| add a page to the homepage index | edit `_dev/sitemeta.py`, re-run `make_home.py`, then re-freeze |
| record that you have revised a page by hand | add its path to `_dev/curated.txt` |

`_dev/curated.txt` is the safety catch: `retrofit.py` never touches a page
listed there. Add a page to it as soon as you have made a page-specific
decision, or the next repetitive pass may flatten your work.

---

## Contents

| File | Purpose |
| --- | --- |
| `site.css`, `site.js` | Sources for `assets/`. Edit these *and* copy to `assets/`, or edit `assets/` and copy back — they must stay identical. |
| `retrofit.py` | The reviewed repetitive pass. Rebuilds shared chrome and applies the mechanical body cleanups. Idempotent. |
| `make_home.py` | Emitted the homepage once. `index.html` is curated now; re-run only if the archive inventory changes, then re-apply any hand edits. |
| `make_checklist.py` | Regenerates `REVISION-CHECKLIST.md` from the actual pages. |
| `sitemeta.py` | Section taxonomy, page→section map, index labels, **and `INDEX_THUMB`** — the preview image shown beside each page in the homepage archive list. |
| `curated.txt` | Pages revised by hand; `retrofit.py` skips them. |
| `baseline-snapshot/` | The 256 pages as they were before the redesign. Restore from here if a pass goes wrong. |
| `build.py` | The frozen original importer. Provenance only. |
| `validate.py` | Preservation check against the original FrontPage source. |
| `check_layout.py` | Responsive audit: overflow, fixed widths, tables, embeds, touch targets. |
| `check_runtime.js` | Loads pages in a DOM and fails on any console error. |
| `shoot.py` | Screenshots every breakpoint in light and dark, and fails on horizontal overflow. |
| `REVISION-CHECKLIST.md` | Page-by-page status and priority queue. |
| `retrofit-notes.txt` | What the last retrofit pass changed, page by page. |
| `i18n_extract.py` | Pulls every translatable string out of the Italian pages and deduplicates. |
| `i18n_chunk.py` | Splits the catalogue into model-sized chunks. |
| `i18n_build.py` | Rebuilds `/en/` from the Italian pages plus the translation map. |
| `i18n_assets.py` | English search index and the bilingual sitemap. |
| `i18n/map.en.json` | The Italian → English string map. **This is the file to edit to fix a translation.** |
| `i18n/BRIEF.md` | The translator brief and domain glossary. |

## Running the checks

```sh
python3 _dev/validate.py     --src <original filebase> --out .
python3 _dev/check_layout.py .
node     _dev/check_runtime.js . index.html mini_whip.htm chaberton/chab.htm
LD_LIBRARY_PATH=/path/to/stub python3 _dev/shoot.py --site . --out /tmp/shots --label after
```

Requirements: Python 3.10+, `beautifulsoup4`, `html5lib`, `Pillow`; Node with
`jsdom` for the runtime check; Playwright Chromium for screenshots.

---

## The design system

Defined entirely in `assets/site.css` with custom properties. No framework, no
external font, no third-party request.

**Type.** A system serif for display (`ui-serif, Georgia, …`) over the system
sans for reading. The serif is what makes the archive read as a technical
notebook rather than a dashboard, and it costs nothing to download. Scale:
`--fs-micro` 12 → `--fs-display` clamp(32, 52). Body 17 px, measure 68 ch.

**Colour.** Warm paper `#f7f5f0` and warm ink `#171614`, one petrol accent
`#0d5c63` (light) / `#6fc6c9` (dark) descended from the original site's
`#336699` and `#006666`. The Chaberton archive overrides the same tokens with a
brass accent and stone paper via `body[data-site="chaberton"]` — one system,
two identities. Both schemes follow `prefers-color-scheme`.

**Space.** `--s1`…`--s9` on a 4 px base. `--tap: 2.75rem` is the minimum size
of every interactive control.

**Layout.** `.wrap` caps at 74 rem. `.layout--toc` becomes two columns at
64 rem. Every grid sets `grid-template-columns: minmax(0, 1fr)` and every grid
child sets `min-width: 0` — without that, one wide table stretches the column
past the viewport, which is exactly the bug the responsive audit caught.

**Media.** `.is-photo` and `.is-diagram` are not decoration: a schematic on a
dark page needs a light plate (`--plate`) or the line art disappears.
`aspect-ratio` + `object-fit: cover` are used only on editorial thumbnails,
never on a diagram.

**The archive index opens itself, one category at a time.** Each category is a
`<details>`, but the id lives on the `<ul>` *inside* it, not on the `<details>`.
Linking to an element inside a closed `<details>` makes the browser expand it —
so a category tile or a header link opens the right list **with no JavaScript at
all**. The shared `name="archivio"` makes it an exclusive accordion: opening one
category closes the others, natively, also without JavaScript. The script only
supplies the fallbacks — sibling closing for browsers without `name` support,
expansion for browsers without fragment auto-expand, and same-page clicks where
the hash does not change.

Verified in a real browser across nine cases: on load, three successive tile
clicks, opening and re-closing a summary, arriving from an article via the
header nav, and both fragment arrival and summary clicking with JavaScript
disabled.

**Archive previews.** Every row in the archive list carries a 64×48 preview.
65 of the 68 pages have one: 59 are the exact thumbnails the original homepage
paired with that link, 6 are the first substantial image on the page itself.
`power_supply_12v_30A.htm` has no image at all ("in preparazione") and the two
legal pages do not want one — those rows get a neutral placeholder so the text
stays aligned. Previews are `loading="lazy"`, so a closed category costs
nothing.

**Components.** header + category disclosure, breadcrumb, search, hero, buttons,
feature card / text card / category tile / archive disclosure, Chaberton
feature, article header, TOC rail + mobile disclosure, callouts
(`--specs`, `--warning`, `--update`), spec list, figures, tables, gallery,
photo navigation, panorama, footer.

**Mobile navigation.** Below 62 rem the categories are a disclosure panel with
item counts and one-line descriptions; at or above 62 rem they are a single
compact row and the button is hidden. The breakpoint is read with `matchMedia`
so JavaScript and CSS can never disagree.

---

## The English mirror

The site is bilingual. Italian stays at the original URLs; English lives at
`/en/` with exactly the same shape, so `mini_whip.htm` ↔ `en/mini_whip.htm`.
A compact IT/EN switch sits in the top-right corner of every page and links to
the counterpart of the page you are on, at any depth.

**Nothing is translated as HTML.** A model asked to translate raw markup will
eventually drop an attribute, break a table or mangle a link. Instead:

1. `i18n_extract.py` walks the DOM and pulls out text nodes, `title`, `alt`,
   `aria-label`, `placeholder` and the prose `<meta>` tags — **text only, never
   markup**. Strings are deduplicated across the whole site, which turned
   21,189 occurrences into **4,425 unique strings**: the shared header, footer
   and navigation are translated once, not 256 times.
2. `i18n_chunk.py` splits those into 22 chunks of ~22,000 characters.
3. Each chunk was translated by **Claude Haiku 4.5**, working from
   `i18n/BRIEF.md` — a register brief plus a 40-term domain glossary that fixes
   *tensione* → voltage, *autonomia* → runtime, *schema elettrico* → circuit
   diagram, and so on.
4. `i18n_build.py` clones each Italian page and substitutes the text. Same
   tags, same ids, same anchors, same images. The two trees cannot drift.

Because the English page is a clone, three things are re-anchored: `lang`
becomes `en`; asset URLs are resolved against the site root and re-pointed out
of `/en/` (doing this by "just add one `../`" is correct at the top level and
silently wrong one directory down); and `data-root` / `data-lang-root` /
`data-search-index` are set per page so the search box loads
`assets/search-index.en.json` and links to English results.

### Verification

* every one of the 4,425 strings came back translated — **zero gaps**
* **11,732 local references** in the English tree resolve to a real file
* numeric drift was audited string by string. 258 differences are all Italian
  decimal commas becoming English decimal points (`3,6V` → `3.6V`) or grouped
  lists being split (`torri 5,6,7` → `towers 5, 6, 7`). Exactly **5 strings**
  showed a genuinely different numeral count, and all five are correct English
  idiom: *guadagno 1* → "unity gain", *anni 70* → "the 1970s", *antenna a 1/4
  onda* → "quarter-wave antenna", *2 batterie* → "Two batteries"
* IT→EN→IT round trips verified in a real browser at six different depths,
  including a gallery photo page four levels down and a panorama page

### Editing a translation

Edit the value in `_dev/i18n/map.en.json` and re-run:

```sh
python3 _dev/i18n_build.py  --site . --map _dev/i18n/map.en.json
python3 _dev/i18n_assets.py --site . --map _dev/i18n/map.en.json
```

The English tree is fully generated. Never hand-edit a file under `/en/`: the
next build overwrites it. Fix the map, or fix the Italian page and re-run.

---

## Known issues and deliberate decisions

- **The old metallic banners are gone from the interface.**
  `IMAGES/chirio_com_04.jpg` and `chaberton/images/testa_01.gif` duplicated the
  wordmark and dated the page. The files remain in the archive.
- **`email.jpg` is no longer used.** The address is a normal
  `mailto:info@chirio.com` link, in the hero and in the footer of every page.
- **The homepage no longer opens with 66 tiny cards.** It shows three featured
  projects with real photographs, three entry points, seven category tiles and
  a per-category disclosure list. The original thumbnails were not discarded —
  they are the previews inside those lists, so every one of them is referenced
  again.
- **`IMAGES/chirio_com_04.jpg` is the only homepage image no longer used.**
  That is the metallic banner, retired on purpose. The Valle di Susa aerial
  photograph and its caption are back, closing the page as they did originally.
- **`chaberton/chab.htm` was rebuilt by hand.** Every destination the original
  linked to is still linked — 28 destinations now against 18 before. Four
  decorative thumbnails and a `<blink>Gallery</blink>` label were dropped;
  `[ 30_12_04 ]`-style labels became readable names.
- **Three source files were already missing from the backup** and remain so:
  `IMAGES/SAB 0529 timer.pdf`, `IMAGES/car_lamp_000.gif`,
  `IMAGES/sh_regolatore_ventola.gif`.
- **One external image is hotlinked** on `mini_whip.htm`
  (`hamqsl.com/solarbc.php`, live solar conditions). It is the author's own
  editorial choice, set to `loading="lazy"` and `referrerpolicy="no-referrer"`.
  Flagged for a human decision.
- **Unit typography was corrected, values were not.** `10khz` → `10 kHz`,
  `2700Mhz` → `2700 MHz`. Only the unit spelling and the space before it.
  Millimetres, amperes and volts were left alone deliberately — the risk of
  touching a value is not worth the polish.
- **`/INDEX.HTM` in uppercase is still not served.** `/`, `/index.html` and
  `/index.htm` all work.
- **The English text is machine translation, reviewed mechanically but not by a
  native technical editor.** Numbers, units and part numbers were verified
  programmatically; register and idiom were not. Treat `/en/` as a good
  working translation, not a publication-grade one. Corrections go in
  `i18n/map.en.json`.
- **Italian is the default language.** `x-default` in the `hreflang` set points
  at the Italian page, and no automatic redirection by browser language is
  performed — the reader chooses with the switch.
