/// Normalize a raw market name/key into a consistent, comparable string.
/// Safe with nulls and various input shapes.
String normalizeMarketKey(Object? raw) {
  // Always produce a non-null String
  var s = (raw?.toString() ?? '').toString();

  // Remove known suffixes/words (case-insensitive)
  s = s.replaceAll(RegExp(r'_panel_chart', caseSensitive: false), '');
  s = s.replaceAll(RegExp(r'_penal_chart', caseSensitive: false), '');
  s = s.replaceAll(RegExp(r'satta', caseSensitive: false), '');
  s = s.replaceAll(RegExp(r'record', caseSensitive: false), '');

  // Normalize separators (spaces, underscores, dashes) into a single underscore
  s = s.replaceAll(RegExp(r'[_\s\-]+'), '_');

  // Trim and make lowercase for canonical key
  s = s.trim().toLowerCase();

  // ✅ Fallback for completely empty keys (so UI never breaks)
  if (s.isEmpty) {
    s = 'unknown_market';
  }

  return s;
}