// pi-minimax · LS-Matchmaker web-v3 · Verhalten
// (1) Sprachumschaltung DE <-> EN, in localStorage gespeichert.
// (2) Sticky-Header bekommt "scrolled"-Klasse ab 8 px.
// (3) Cards/Modi fliegen sanft ein, wenn sie in den Viewport kommen
//     (IntersectionObserver, einmal pro Element).

(function () {
  'use strict';

  // ---- 1) Sprache ----
  var STORAGE_KEY_LANG = 'lsweb.lang';
  var html = document.documentElement;
  var saved = null;
  try { saved = localStorage.getItem(STORAGE_KEY_LANG); } catch (e) {}
  if (saved === 'en') html.classList.add('lang-en');

  function setLangLabel(btn) {
    btn.textContent = html.classList.contains('lang-en') ? 'DE' : 'EN';
  }

  function bindLangToggle() {
    var buttons = document.querySelectorAll('.lang-toggle, .lang-toggle-link');
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      if (b.classList.contains('lang-toggle')) {
        b.addEventListener('click', function (e) {
          e.preventDefault();
          html.classList.toggle('lang-en');
          var isEn = html.classList.contains('lang-en');
          try { localStorage.setItem(STORAGE_KEY_LANG, isEn ? 'en' : 'de'); } catch (err) {}
          var all = document.querySelectorAll('.lang-toggle');
          for (var k = 0; k < all.length; k++) setLangLabel(all[k]);
        });
        setLangLabel(b);
      } else if (b.classList.contains('lang-toggle-link')) {
        // Footer-Sprach-Link: triggert das gleiche Toggle
        b.addEventListener('click', function (e) {
          e.preventDefault();
          var btn = document.querySelector('.lang-toggle');
          if (btn) btn.click();
        });
      }
    }
  }

  // ---- 2) Sticky-Header scrolled class ----
  function bindHeaderScroll() {
    var header = document.querySelector('header.site');
    if (!header) return;
    var threshold = 8;
    var lastState = false;
    function onScroll() {
      var scrolled = window.scrollY > threshold;
      if (scrolled !== lastState) {
        header.classList.toggle('scrolled', scrolled);
        lastState = scrolled;
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ---- 3) Reveal on scroll ----
  function bindReveal() {
    var targets = document.querySelectorAll('.card, .mode');
    if (!('IntersectionObserver' in window)) {
      // Fallback: einfach anzeigen
      for (var i = 0; i < targets.length; i++) targets[i].classList.add('in-view');
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    for (var j = 0; j < targets.length; j++) io.observe(targets[j]);
  }

  // ---- Boot ----
  function boot() {
    bindLangToggle();
    bindHeaderScroll();
    bindReveal();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
