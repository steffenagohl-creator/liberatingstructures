/* Sprachumschaltung DE/EN — first-party, ohne externe Dienste.
   Standard ist Deutsch; ohne JavaScript bleibt Deutsch sichtbar (rechtssicher).
   Auswahl wird lokal (localStorage) gemerkt. */
(function () {
  var KEY = 'ls_lang';
  var root = document.documentElement;

  function apply(lang) {
    if (lang === 'en') { root.classList.add('lang-en'); root.setAttribute('lang', 'en'); }
    else { root.classList.remove('lang-en'); root.setAttribute('lang', 'de'); }
    var btns = document.querySelectorAll('.lang-toggle');
    for (var i = 0; i < btns.length; i++) {
      btns[i].textContent = (lang === 'en') ? 'DE' : 'EN';
      btns[i].setAttribute('aria-label', (lang === 'en') ? 'Auf Deutsch umschalten' : 'Switch to English');
    }
  }

  var saved = 'de';
  try { saved = localStorage.getItem(KEY) || 'de'; } catch (e) {}
  apply(saved);

  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.lang-toggle');
    if (!t) return;
    var next = root.classList.contains('lang-en') ? 'de' : 'en';
    apply(next);
    try { localStorage.setItem(KEY, next); } catch (e2) {}
  });
})();
