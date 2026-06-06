/* ===================================================================
   ICONS — die echten offiziellen LS-Icon-SVGs
   ===================================================================
   Lädt alle 46 SVGs aus assets/icons/ als rohe Markup-Strings zur
   Build-Zeit. Schlüssel = Dateiname, der EXAKT dem Backend-Feld
   `Structure.icon` entspricht (SSOT, data/icon_map.json). So lädt das
   Frontend das richtige Icon ausschließlich über die Backend-Zuordnung
   — keine eigene Zahlen-/Namens-Logik hier.

   Die SVGs haben keine fill-Attribute → sie erben `currentColor`
   (Tönung über CSS, s. .ls-icon-Regel in injectTheme).
   =================================================================== */
const modules = import.meta.glob('./assets/icons/*.svg', {
  query: '?raw', import: 'default', eager: true,
});

const byFilename = {};
for (const [path, raw] of Object.entries(modules)) {
  byFilename[path.split('/').pop()] = raw;
}

/** Roher SVG-Markup-String zu einem Icon-Dateinamen (Backend-Feld `icon`); undefined, wenn unbekannt. */
export function iconSvg(filename) {
  return filename ? byFilename[filename] : undefined;
}
