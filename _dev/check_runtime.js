/* Runtime check: load representative pages in a DOM, execute assets/site.js and
   report any console error or uncaught exception.  Proves the progressive
   enhancements are wired correctly and that nothing depends on a server. */
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('/tmp/node_modules/jsdom');

const out = process.argv[2];
const pages = process.argv.slice(3);
const js = fs.readFileSync(path.join(out, 'assets', 'site.js'), 'utf8');

let failures = 0;

for (const rel of pages) {
  const file = path.join(out, rel);
  if (!fs.existsSync(file)) { console.log(`  MISSING ${rel}`); failures++; continue; }
  const messages = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', (e) => messages.push('jsdomError: ' + e.message));
  vc.on('error', (...a) => messages.push('console.error: ' + a.join(' ')));
  vc.on('warn', (...a) => messages.push('console.warn: ' + a.join(' ')));

  const dom = new JSDOM(fs.readFileSync(file, 'utf8'), {
    url: 'https://chirio.com/' + rel,
    runScripts: 'outside-only',
    virtualConsole: vc,
    pretendToBeVisual: true,
  });
  const w = dom.window;
  // jsdom lacks these; the script guards for them, stub so the guards are exercised
  if (!w.matchMedia) w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {} });
  if (!w.fetch) w.fetch = () => Promise.reject(new Error('offline'));

  try {
    w.eval(js);
  } catch (e) {
    messages.push('exception: ' + e.message);
  }

  // exercise the interactive controls
  const doc = w.document;
  const results = [];
  const toggle = doc.querySelector('.icon-btn--menu');
  const nav = doc.getElementById('site-nav');
  if (toggle && nav) {
    if (!nav.hidden) { messages.push('category panel is not collapsed on load'); }
    toggle.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    const opened = !nav.hidden && toggle.getAttribute('aria-expanded') === 'true';
    results.push('menu:' + (opened ? 'ok' : 'FAIL'));
    if (!opened) { messages.push('category panel did not open'); }
    doc.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    toggle.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    toggle.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    if (!nav.hidden) { messages.push('category panel did not close again'); }
  }
  const input = doc.getElementById('site-search-input');
  if (input) {
    input.value = 'whip';
    input.dispatchEvent(new w.Event('input', { bubbles: true }));
    results.push('search:wired');
  }
  const pano = doc.querySelector('.pano-strip');
  if (pano) {
    pano.dispatchEvent(new w.Event('pointerdown', { bubbles: true }));
    pano.dispatchEvent(new w.Event('pointerup', { bubbles: true }));
    const auto = doc.querySelector('[data-pano-auto]');
    if (auto) { auto.dispatchEvent(new w.MouseEvent('click', { bubbles: true })); auto.dispatchEvent(new w.MouseEvent('click', { bubbles: true })); }
    results.push('pano:ok');
  }
  if (doc.querySelector('[data-photo-next]')) {
    doc.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    results.push('photo-keys:ok');
  }
  const btt = doc.querySelector('.to-top');
  if (btt) {
    w.dispatchEvent(new w.Event('scroll'));
    results.push('to-top:ok');
  }
  // no external resource may be requested
  const externals = [...doc.querySelectorAll('link[href], script[src]')]
    .map((e) => e.getAttribute('href') || e.getAttribute('src'))
    .filter((u) => /^(https?:)?\/\//.test(u));
  if (externals.length) { messages.push('external asset dependency: ' + externals.join(', ')); }

  if (messages.length) {
    failures++;
    console.log(`  FAIL ${rel}`);
    messages.forEach((m) => console.log('        ' + m));
  } else {
    console.log(`  ok   ${rel}  [${results.join(' ')}]`);
  }
  dom.window.close();
}

console.log(failures ? `\nruntime failures: ${failures}` : '\nruntime: all pages clean');
process.exit(failures ? 1 : 0);
