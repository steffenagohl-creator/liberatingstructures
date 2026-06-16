#!/usr/bin/env bash
# pi-minimax · web-v3 · Smoke-Tests für die HTML-Struktur der Marketing-Site
# Geschrieben beim Erstbau, 2026-06-15.
#
# Prüft:
#  - Alle 6 HTML-Seiten existieren
#  - Jede hat <header>, <footer> und <script src="assets/js/lang.js">
#  - Sticky-App-Button ist auf jeder Seite
#  - DE/EN-Blöcke sind parallel vorhanden
#  - Datenschutz-Link führt auf die Sicherheit-Sektion der Index
#  - App-Links zeigen auf /app.html
#  - Keine TODO-Platzhalter
#  - Souveränitäts-Block hat die neue Matrix-Struktur
#
# Stil: bash, set +e, eigene Cleanup via trap.

set +e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0

pass() { echo "  ✅ $1"; PASS=$((PASS+1)); }
fail() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

PAGES=(index was-sind-liberating-structures impressum datenschutz cookies nutzungsbedingungen)

echo "── 1. Alle 6 HTML-Seiten existieren"
for p in "${PAGES[@]}"; do
  if [ -f "$DIR/$p.html" ]; then
    pass "$p.html vorhanden"
  else
    fail "$p.html fehlt"
  fi
done

echo ""
echo "── 2. Jede Seite hat <header>, <footer>, lang.js"
for p in "${PAGES[@]}"; do
  f="$DIR/$p.html"
  if [ ! -f "$f" ]; then continue; fi
  if grep -q '<header class="site">' "$f" && \
     grep -q '<footer class="site">' "$f" && \
     grep -q 'assets/js/lang.js' "$f"; then
    pass "$p.html — header/footer/lang.js"
  else
    fail "$p.html — fehlt eines: header/footer/lang.js"
  fi
done

echo ""
echo "── 3. Sticky-App-Button auf jeder Seite"
for p in "${PAGES[@]}"; do
  f="$DIR/$p.html"
  if [ ! -f "$f" ]; then continue; fi
  if grep -q 'app-cta-sticky' "$f"; then
    pass "$p.html — sticky App-Button"
  else
    fail "$p.html — kein app-cta-sticky"
  fi
done

echo ""
echo "── 4. DE/EN-Blöcke parallel"
for p in "${PAGES[@]}"; do
  f="$DIR/$p.html"
  if [ ! -f "$f" ]; then continue; fi
  de=$(grep -c 'class="block de"' "$f" || true)
  en=$(grep -c 'class="block en"' "$f" || true)
  if [ "$de" -gt 0 ] && [ "$en" -gt 0 ] && [ "$de" -eq "$en" ]; then
    pass "$p.html — $de DE / $en EN Blöcke (parallel)"
  else
    fail "$p.html — DE/EN-Block-Zahl ungleich ($de vs $en)"
  fi
done

echo ""
echo "── 5. Datenschutz / Impressum / Cookies / Nutzungsbedingungen: Link zur Sicherheit-Sektion"
for p in datenschutz impressum cookies nutzungsbedingungen; do
  f="$DIR/$p.html"
  if [ ! -f "$f" ]; then continue; fi
  if grep -q 'index.html#sicherheit' "$f"; then
    pass "$p.html — Link auf index.html#sicherheit"
  else
    fail "$p.html — kein Link auf index.html#sicherheit"
  fi
done

echo ""
echo "── 6. App-Links zeigen auf /app.html"
for p in "${PAGES[@]}"; do
  f="$DIR/$p.html"
  if [ ! -f "$f" ]; then continue; fi
  if grep -q 'href="/app.html"' "$f"; then
    pass "$p.html — /app.html-Link"
  else
    fail "$p.html — kein /app.html-Link"
  fi
done

echo ""
echo "── 7. Keine TODO-Platzhalter oder leere <div>s in der Index"
INDEX="$DIR/index.html"
if grep -qi 'TODO\|FIXME\|XXX' "$INDEX"; then
  fail "index.html — TODO/FIXME/XXX-Platzhalter gefunden"
else
  pass "index.html — keine TODO/FIXME-Platzhalter"
fi
if grep -qE '<div></div>|<div>\s*</div>' "$INDEX"; then
  fail "index.html — leere <div>s gefunden"
else
  pass "index.html — keine leeren <div>s"
fi

echo ""
echo "── 8. Souveränitäts-Block hat die neue Matrix-Struktur"
if grep -q 'class="matrix"' "$INDEX"; then
  pass "index.html — .matrix-Klasse vorhanden"
else
  fail "index.html — keine .matrix-Klasse (Souveränität-Block fehlt?)"
fi
if grep -q '>Souverän<\|"de">Souverän<' "$INDEX" || grep -q '>Sovereign<\|"en">Sovereign<' "$INDEX"; then
  pass "index.html — Matrix-Spaltenüberschriften (Souverän/Sovereign)"
else
  fail "index.html — Matrix-Spaltenüberschriften fehlen"
fi
if grep -qE 'id="sicherheit"|id="privacy"' "$INDEX"; then
  pass "index.html — Sektion-Anker (#sicherheit / #privacy)"
else
  fail "index.html — kein Anker #sicherheit"
fi

echo ""
echo "── 9. KEINE Emojis als Icons (Steffen-Vorgabe)"
EMOJI_RE='[\xF0-\xF4][\x80-\xBF][\x80-\xBF][\x80-\xBF]'
for p in "${PAGES[@]}"; do
  f="$DIR/$p.html"
  if [ ! -f "$f" ]; then continue; fi
  # Suche nach typischen Emoji-Bytes im HTML (UTF-8 4-byte-Sequenzen)
  if LC_ALL=C grep -qP "$EMOJI_RE" "$f" 2>/dev/null; then
    fail "$p.html — Emoji-Zeichen gefunden (verboten)"
  else
    pass "$p.html — keine Emojis"
  fi
done

echo ""
echo "── 10. CSS-Datei vorhanden + Größe plausibel"
if [ -f "$DIR/assets/css/styles.css" ]; then
  size=$(wc -c < "$DIR/assets/css/styles.css")
  if [ "$size" -gt 10000 ] && [ "$size" -lt 50000 ]; then
    pass "styles.css — $(($size / 1024)) KB"
  else
    fail "styles.css — Größe ungewöhnlich: $size Bytes"
  fi
else
  fail "styles.css fehlt"
fi

if [ -f "$DIR/assets/js/lang.js" ]; then
  size=$(wc -c < "$DIR/assets/js/lang.js")
  if [ "$size" -gt 500 ] && [ "$size" -lt 10000 ]; then
    pass "lang.js — $(($size / 1024)) KB"
  else
    fail "lang.js — Größe ungewöhnlich: $size Bytes"
  fi
else
  fail "lang.js fehlt"
fi

echo ""
echo "══════════════════════════════════════"
echo "Ergebnis: $PASS PASS, $FAIL FAIL"
echo "══════════════════════════════════════"
[ "$FAIL" -eq 0 ]
