/* Chirio.com — progressive enhancement only.
   Every link, every page and the whole archive index work with this file absent.
   No dependencies, no storage APIs, no network calls except the search index,
   which is fetched on first interaction. */
(function () {
  'use strict';

  var doc = document;
  var root = doc.documentElement;
  var base = root.getAttribute('data-root') || '';
  root.classList.add('has-js');

  var reduce = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : { matches: false };

  /* ---------------------------------------------------- category menu ----
     Below the nav breakpoint the category list is a disclosure; at or above it
     the list is always visible and the button is hidden by CSS. The breakpoint
     is read with matchMedia so it always agrees with the stylesheet — testing
     element visibility instead would break wherever layout is not computed. */
  var menuBtn = doc.querySelector('.icon-btn--menu');
  var panel = doc.getElementById('site-nav');
  if (menuBtn && panel) {
    var wide = window.matchMedia
      ? window.matchMedia('(min-width: 62rem)')
      : { matches: false, addEventListener: null, addListener: null };

    var setMenu = function (open) {
      panel.hidden = !open;
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    var apply = function () {
      if (wide.matches) {
        panel.hidden = false;
        menuBtn.setAttribute('aria-expanded', 'false');
      } else {
        setMenu(false);
      }
    };
    apply();

    menuBtn.addEventListener('click', function () {
      if (wide.matches) return;
      var open = panel.hidden;
      setMenu(open);
      if (open) {
        var first = panel.querySelector('a');
        if (first) first.focus();
      }
    });
    doc.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || wide.matches || panel.hidden) return;
      setMenu(false);
      menuBtn.focus();
    });
    if (wide.addEventListener) wide.addEventListener('change', apply);
    else if (wide.addListener) wide.addListener(apply);
  }

  /* ------------------------------------------------------ search field --- */
  var searchBtn = doc.querySelector('.icon-btn--search');
  var searchInput = doc.getElementById('site-search-input');
  if (searchBtn && searchInput) {
    searchBtn.addEventListener('click', function () {
      var box = searchInput.closest('.search');
      if (box) box.scrollIntoView({ behavior: reduce.matches ? 'auto' : 'smooth', block: 'center' });
      searchInput.focus({ preventScroll: true });
    });
  }

  if (searchInput) {
    var results = doc.getElementById('search-results');
    var status = doc.getElementById('search-status');
    var data = null;
    var loading = false;
    var pending = null;

    var fold = function (s) {
      s = (s || '').toLowerCase();
      return s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : s;
    };

    var load = function () {
      if (data) return Promise.resolve(data);
      if (loading) return loading;
      if (status) status.textContent = 'Caricamento indice…';
      loading = fetch(base + 'assets/search-index.json')
        .then(function (r) { return r.json(); })
        .then(function (j) {
          data = j.map(function (p) {
            return { u: p.u, t: p.t, s: p.s, d: p.d,
                     k: fold([p.t, p.s, p.d, p.g].join(' ')) };
          });
          if (status) status.textContent = '';
          return data;
        })
        .catch(function () {
          if (status) {
            status.textContent = 'Indice di ricerca non disponibile. '
              + 'Usa l’elenco delle categorie qui sotto.';
          }
          return null;
        });
      return loading;
    };

    var render = function (q) {
      if (!results) return;
      results.textContent = '';
      var nq = fold(q).trim();
      if (!data || nq.length < 2) { if (status && data) status.textContent = ''; return; }
      var terms = nq.split(/\s+/);
      var hits = data.filter(function (p) {
        return terms.every(function (t) { return p.k.indexOf(t) !== -1; });
      }).slice(0, 30);
      if (status) {
        status.textContent = hits.length
          ? hits.length + (hits.length === 1 ? ' pagina trovata' : ' pagine trovate')
          : 'Nessun risultato per “' + q + '”.';
      }
      hits.forEach(function (p) {
        var li = doc.createElement('li');
        var a = doc.createElement('a');
        a.href = base + p.u;
        var t = doc.createElement('span'); t.className = 'r-title'; t.textContent = p.t;
        var s = doc.createElement('span'); s.className = 'r-sec';
        s.textContent = p.s + (p.d ? ' — ' + p.d : '');
        a.appendChild(t); a.appendChild(s);
        li.appendChild(a);
        results.appendChild(li);
      });
    };

    searchInput.addEventListener('input', function () {
      var q = searchInput.value;
      clearTimeout(pending);
      pending = setTimeout(function () { load().then(function () { render(q); }); }, 140);
    });
    searchInput.addEventListener('focus', load, { once: true });
    searchInput.form && searchInput.form.addEventListener('submit', function (e) { e.preventDefault(); });
  }

  /* --------------------------------------- open a linked archive category -
     The list inside each <details> carries the id, so modern browsers expand
     the right category on their own. This does the same for older ones, keeps
     the disclosure marker honest, and handles in-page clicks where the hash
     does not change. */
  var archive = doc.querySelector('.archive');
  if (archive) {
    var openFromHash = function (hash, smooth) {
      if (!hash || hash.length < 2) return;
      var target;
      try { target = doc.getElementById(decodeURIComponent(hash.slice(1))); }
      catch (e) { return; }
      if (!target) return;
      var det = target.closest ? target.closest('details') : null;
      if (!det || !archive.contains(det)) return;
      det.open = true;
      det.scrollIntoView({
        behavior: (smooth && !reduce.matches) ? 'smooth' : 'auto',
        block: 'start'
      });
    };
    /* Only one category open at a time. Browsers that support the exclusive
       accordion do this from the shared name= attribute; this closes the
       siblings for the ones that do not. Closing a sibling fires its own
       toggle event, but that event is a close, so nothing cascades. */
    var exclusiveNative = (function () {
      var d = doc.createElement('details');
      return 'name' in d;
    })();
    if (!exclusiveNative) {
      archive.addEventListener('toggle', function (e) {
        var det = e.target;
        if (!det || det.tagName !== 'DETAILS' || !det.open) return;
        [].forEach.call(archive.querySelectorAll('details[name]'), function (other) {
          if (other !== det) other.open = false;
        });
      }, true);
    }

    openFromHash(window.location.hash, false);
    window.addEventListener('hashchange', function () {
      openFromHash(window.location.hash, true);
    });
    doc.addEventListener('click', function (e) {
      var a = e.target.closest ? e.target.closest('a[href*="#"]') : null;
      if (!a) return;
      var href = a.getAttribute('href') || '';
      var hash = href.slice(href.indexOf('#'));
      if (hash.length < 2) return;
      var path = href.slice(0, href.indexOf('#'));
      if (path && path !== window.location.pathname.split('/').pop()) return;
      var target = doc.getElementById(decodeURIComponent(hash.slice(1)));
      if (!target || !archive.contains(target)) return;
      e.preventDefault();
      openFromHash(hash, true);
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, '', hash);
      }
    });
  }

  /* ------------------------------------------- table of contents state --- */
  var tocLinks = [].slice.call(doc.querySelectorAll('.toc-rail .toc a[href^="#"]'));
  if (tocLinks.length && 'IntersectionObserver' in window) {
    var seen = new Map();
    var targets = tocLinks
      .map(function (a) { return doc.getElementById(decodeURIComponent(a.hash.slice(1))); })
      .filter(Boolean);
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
    }, { rootMargin: '-80px 0px -70% 0px' });
    targets.forEach(function (t) { io.observe(t); });
  }

  /* --------------------------------------------------------- back to top - */
  var btt = doc.querySelector('.to-top');
  if (btt) {
    var onScroll = function () { btt.classList.toggle('is-visible', window.scrollY > 900); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    btt.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduce.matches ? 'auto' : 'smooth' });
      var skip = doc.querySelector('.skip-link');
      if (skip) skip.focus({ preventScroll: true });
    });
  }

  /* ------------------------------------------------ photo gallery keys --- */
  var prev = doc.querySelector('[data-photo-prev]');
  var next = doc.querySelector('[data-photo-next]');
  if (prev || next) {
    doc.addEventListener('keydown', function (e) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      var t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.key === 'ArrowLeft' && prev) prev.click();
      if (e.key === 'ArrowRight' && next) next.click();
    });
  }

  /* --------------------------------------------------- panorama viewer --- */
  [].forEach.call(doc.querySelectorAll('.pano'), function (pano) {
    var strip = pano.querySelector('.pano-strip');
    if (!strip) return;
    var down = false, startX = 0, startLeft = 0, timer = null;
    var btn = pano.querySelector('[data-pano-auto]');

    function stopAuto() {
      if (!timer) return;
      clearInterval(timer); timer = null;
      if (btn) {
        btn.setAttribute('aria-pressed', 'false');
        btn.textContent = btn.getAttribute('data-play') || 'Scorri';
      }
    }

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
      else if (e.key === 'ArrowLeft') { strip.scrollLeft -= step; e.preventDefault(); stopAuto(); }
      else if (e.key === 'Home') { strip.scrollLeft = 0; e.preventDefault(); stopAuto(); }
      else if (e.key === 'End') { strip.scrollLeft = strip.scrollWidth; e.preventDefault(); stopAuto(); }
    });

    if (btn) {
      if (reduce.matches) btn.hidden = true;
      btn.addEventListener('click', function () {
        if (timer) { stopAuto(); return; }
        btn.setAttribute('aria-pressed', 'true');
        btn.textContent = btn.getAttribute('data-stop') || 'Ferma';
        timer = setInterval(function () {
          if (strip.scrollLeft + strip.clientWidth >= strip.scrollWidth - 1) strip.scrollLeft = 0;
          else strip.scrollLeft += 2;
        }, 20);
      });
    }
    var full = pano.querySelector('[data-pano-full]');
    if (full && pano.requestFullscreen) {
      full.addEventListener('click', function () { pano.requestFullscreen().catch(function () {}); });
    } else if (full) {
      full.hidden = true;
    }
  });
})();
