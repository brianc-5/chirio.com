#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Screenshot harness for the Chirio.com redesign.

Serves the static site over HTTP (so relative URLs, fetch() and the search index
behave exactly as they will on GitHub Pages) and captures each page at the
project's breakpoints in both colour schemes.

    python3 shoot.py --site <dir> --out <shots dir> --label before [--pages a.htm b.htm]

Requires a Chromium that can launch; on this host that means
``LD_LIBRARY_PATH=/tmp/stublib`` so the unused libXdamage stub resolves.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import os
import socketserver
import threading

from playwright.sync_api import sync_playwright

VIEWPORTS = [
    ("320", 320, 900),
    ("390", 390, 900),
    ("768", 768, 1000),
    ("1024", 1024, 900),
    ("1440", 1440, 950),
]

DEFAULT_PAGES = [
    ("index.html", "home"),
    ("mini_whip.htm", "article"),
    ("battery_test.htm", "article-tables"),
    ("chaberton/chab.htm", "chaberton"),
    ("chaberton/batteria_2003/index.htm", "gallery"),
]


def serve(directory, port=0):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    handler.log_message = lambda *a, **k: None
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--pages", nargs="*", default=None)
    ap.add_argument("--schemes", nargs="*", default=["light", "dark"])
    ap.add_argument("--widths", nargs="*", default=None)
    ap.add_argument("--full", action="store_true", help="full-page instead of viewport")
    a = ap.parse_args()

    pages = ([(p, os.path.splitext(os.path.basename(p))[0]) for p in a.pages]
             if a.pages else DEFAULT_PAGES)
    views = [v for v in VIEWPORTS if not a.widths or v[0] in a.widths]

    os.makedirs(a.out, exist_ok=True)
    httpd, port = serve(os.path.abspath(a.site))
    base = f"http://127.0.0.1:{port}/"
    errors = []
    made = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage",
                                          "--force-device-scale-factor=1"])
        for scheme in a.schemes:
            ctx = browser.new_context(color_scheme=scheme, device_scale_factor=1,
                                      reduced_motion="reduce")
            page = ctx.new_page()
            page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
                    if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            for rel, name in pages:
                for tag, w, h in views:
                    page.set_viewport_size({"width": w, "height": h})
                    page.goto(base + rel, wait_until="load")
                    page.wait_for_timeout(220)
                    # horizontal overflow check at the same time
                    over = page.evaluate(
                        "() => Math.max(document.documentElement.scrollWidth,"
                        " document.body.scrollWidth) - window.innerWidth")
                    if over and over > 1:
                        errors.append(f"OVERFLOW {rel} @{tag}/{scheme}: +{over}px")
                    out = os.path.join(a.out, f"{a.label}_{name}_{tag}_{scheme}.png")
                    page.screenshot(path=out, full_page=a.full)
                    made.append(out)
            ctx.close()
        browser.close()
    httpd.shutdown()

    print(f"{len(made)} screenshots -> {a.out}")
    if errors:
        print("\nissues:")
        for e in dict.fromkeys(errors):
            print("  -", e)
    else:
        print("no console errors, no horizontal overflow")


if __name__ == "__main__":
    main()
