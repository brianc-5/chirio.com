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
| fix wording, a heading, an image on one page | edit that `.htm` file directly |
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
