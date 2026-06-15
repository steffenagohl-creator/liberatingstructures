// pi-minimax · LS-Matchmaker web-v2 · Sprachumschaltung DE <-> EN
// Toggelt die .lang-en Klasse am <html>-Element, speichert die Wahl in localStorage.
(function () {
  'use strict';
  var STORAGE_KEY = 'lsweb.lang';
  var html = document.documentElement;
  var saved = null;
  try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) {}
  if (saved === 'en') html.classList.add('lang-en');
  if (saved === 'de') html.classList.remove('lang-en');

  function toggle() {
    var isEn = html.classList.toggle('lang-en');
    try { localStorage.setItem(STORAGE_KEY, isEn ? 'en' : 'de'); } catch (e) {}
  }

  function bind() {
    var buttons = document.querySelectorAll('.lang-toggle');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', function (e) {
        e.preventDefault();
        toggle();
        // Button-Label synchron halten
        var btns = document.querySelectorAll('.lang-toggle');
        for (var j = 0; j < btns.length; j++) {
          btns[j].textContent = html.classList.contains('lang-en') ? 'DE' : 'EN';
        }
      });
      // Initial-Label setzen
      buttons[i].textContent = html.classList.contains('lang-en') ? 'DE' : 'EN';
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
