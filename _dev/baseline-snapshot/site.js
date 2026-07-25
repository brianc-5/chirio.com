/* Chirio.com — small progressive enhancements. No dependencies.
   Everything below is optional: all content and links work without JavaScript. */
(function () {
  'use strict';

  var root = document.documentElement.getAttribute('data-root') || '';

  /* ---------------------------------------------------- mobile navigation */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('is-open')) {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
      }
    });
  }

  /* ------------------------------------------------- table of contents ui */
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll('.aside-col .toc a[href^="#"]'));
  if (tocLinks.length && 'IntersectionObserver' in window) {
    var targets = tocLinks
      .map(function (a) { return document.getElementById(decodeURIComponent(a.hash.slice(1))); })
      .filter(Boolean);
    var seen = new Map();
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { seen.set(en.target, en); });
      var best = null;
      seen.forEach(function (en) {
        if (!en.isIntersecting) return;
        if (!best || en.target.offsetTop < best.target.offsetTop) best = en;
      });
      if (!best) return;
      tocLinks.forEach(function (a) {
        a.classList.toggle('is-active', decodeURIComponent(a.hash.slice(1)) === best.target.id);
      });
    }, { rootMargin: '-80px 0px -70% 0px', threshold: 0 });
    targets.forEach(function (t) { io.observe(t); });
  }

  /* --------------------------------------------------------- back to top */
  var btt = document.querySelector('.to-top');
  if (btt) {
    var onScroll = function () { btt.classList.toggle('is-visible', window.scrollY > 900); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    btt.addEventListener('click', function () {
      var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
      var skip = document.querySelector('.skip-link');
      if (skip) skip.focus({ preventScroll: true });
    });
  }

  /* ------------------------------------- photo gallery keyboard shortcuts */
  var prev = document.querySelector('[data-photo-prev]');
  var next = document.querySelector('[data-photo-next]');
  if (prev || next) {
    document.addEventListener('keydown', function (e) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      var t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.key === 'ArrowLeft' && prev) { prev.click(); }
      if (e.key === 'ArrowRight' && next) { next.click(); }
    });
  }

  /* --------------------------------------- panorama viewer (drag to pan) */
  Array.prototype.forEach.call(document.querySelectorAll('.pano'), function (pano) {
    var strip = pano.querySelector('.pano-strip');
    if (!strip) return;
    var down = false, startX = 0, startLeft = 0, timer = null;

    strip.addEventListener('pointerdown', function (e) {
      down = true; startX = e.clientX; startLeft = strip.scrollLeft;
      strip.classList.add('is-drag');
      if (strip.setPointerCapture) { try { strip.setPointerCapture(e.pointerId); } catch (err) {} }
    });
    strip.addEventListener('pointermove', function (e) {
      if (!down) return;
      e.preventDefault();
      strip.scrollLeft = startLeft - (e.clientX - startX);
      stopAuto();
    });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (ev) {
      strip.addEventListener(ev, function () { down = false; strip.classList.remove('is-drag'); });
    });
    strip.addEventListener('keydown', function (e) {
      var step = strip.clientWidth * 0.25;
      if (e.key === 'ArrowRight') { strip.scrollLeft += step; e.preventDefault(); stopAuto(); }
      if (e.key === 'ArrowLeft') { strip.scrollLeft -= step; e.preventDefault(); stopAuto(); }
      if (e.key === 'Home') { strip.scrollLeft = 0; e.preventDefault(); stopAuto(); }
      if (e.key === 'End') { strip.scrollLeft = strip.scrollWidth; e.preventDefault(); stopAuto(); }
    });

    function stopAuto() {
      if (!timer) return;
      clearInterval(timer); timer = null;
      if (btn) { btn.setAttribute('aria-pressed', 'false'); btn.textContent = btn.getAttribute('data-play') || 'Scorri'; }
    }
    var btn = pano.querySelector('[data-pano-auto]');
    if (btn) {
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { btn.hidden = true; }
      btn.addEventListener('click', function () {
        if (timer) { stopAuto(); return; }
        btn.setAttribute('aria-pressed', 'true');
        btn.textContent = btn.getAttribute('data-stop') || 'Ferma';
        timer = setInterval(function () {
          if (strip.scrollLeft + strip.clientWidth >= strip.scrollWidth - 1) { strip.scrollLeft = 0; }
          else { strip.scrollLeft += 2; }
        }, 20);
      });
    }
    var full = pano.querySelector('[data-pano-full]');
    if (full) {
      full.addEventListener('click', function () {
        var el = pano.querySelector('.pano-strip');
        if (pano.requestFullscreen) pano.requestFullscreen().catch(function () {});
        else if (el && el.webkitRequestFullscreen) el.webkitRequestFullscreen();
      });
    }
  });

  /* ------------------------------------------------ client-side site search
     Index is fetched only on first interaction, so it never delays load.   */
  var input = document.getElementById('site-search-input');
  if (input) {
    var results = document.getElementById('search-results');
    var status = document.getElementById('search-status');
    var wrapEl = input.closest('.site-search');
    if (wrapEl) wrapEl.classList.remove('no-js-hide');
    var data = null, loading = false;

    function norm(s) {
      s = (s || '').toLowerCase();
      return s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : s;
    }

    function load() {
      if (data || loading) return Promise.resolve(data);
      loading = true;
      if (status) status.textContent = 'Caricamento indice…';
      return fetch(root + 'assets/search-index.json')
        .then(function (r) { return r.json(); })
        .then(function (j) {
          data = j.map(function (p) { return { u: p.u, t: p.t, s: p.s, d: p.d, k: norm(p.t + ' ' + p.s + ' ' + (p.d || '') + ' ' + (p.g || '')) }; });
          loading = false;
          if (status) status.textContent = '';
          return data;
        })
        .catch(function () {
          loading = false;
          if (status) status.textContent = 'Indice di ricerca non disponibile. Usa la navigazione qui sotto.';
          return null;
        });
    }

    function render(q) {
      if (!results) return;
      results.innerHTML = '';
      var nq = norm(q).trim();
      if (!data || nq.length < 2) { if (status && data) status.textContent = ''; return; }
      var terms = nq.split(/\s+/);
      var hits = data.filter(function (p) {
        return terms.every(function (t) { return p.k.indexOf(t) !== -1; });
      }).slice(0, 40);
      if (status) {
        status.textContent = hits.length
          ? hits.length + (hits.length === 1 ? ' pagina trovata' : ' pagine trovate')
          : 'Nessun risultato per “' + q + '”.';
      }
      hits.forEach(function (p) {
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.href = root + p.u;
        var t = document.createElement('span'); t.className = 't'; t.textContent = p.t;
        var s = document.createElement('span'); s.className = 's'; s.textContent = p.s;
        a.appendChild(t); a.appendChild(s);
        li.appendChild(a); results.appendChild(li);
      });
    }

    var debounce;
    input.addEventListener('input', function () {
      var q = input.value;
      clearTimeout(debounce);
      debounce = setTimeout(function () { load().then(function () { render(q); }); }, 140);
    });
    input.addEventListener('focus', load, { once: true });
  }
})();
