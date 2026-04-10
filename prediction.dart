// lib/models/prediction.dart
// Backwards-compatible Prediction model with defensive parsing and list normalization.
// Drop this file in place of your old model and rebuild.

class Prediction {
  final String marketKey;
  final String marketName;
  final String tier;
  final Map<String, dynamic> p; // legacy code expects p[...] access
  final double score;
  final bool passed;

  Prediction({
    required this.marketKey,
    required this.marketName,
    required this.tier,
    required Map<String, dynamic> p,
    required this.score,
    required this.passed,
  }) : p = Map<String, dynamic>.from(p);

  /// copyWith kept for compatibility with older main.dart usage.
  Prediction copyWith({
    String? marketKey,
    String? marketName,
    String? tier,
    Map<String, dynamic>? p,
    double? score,
    bool? passed,
  }) {
    return Prediction(
      marketKey: marketKey ?? this.marketKey,
      marketName: marketName ?? this.marketName,
      tier: tier ?? this.tier,
      p: p ?? Map<String, dynamic>.from(this.p),
      score: score ?? this.score,
      passed: passed ?? this.passed,
    );
  }

  /// Factory constructor: tolerant parsing of many shapes.
  factory Prediction.fromJson(Map<String, dynamic> src) {
    final Map<String, dynamic> map = Map<String, dynamic>.from(src);

    // --- determine marketKey and marketName (defensive) ---
    String marketKey = '';
    if (map['marketKey'] is String && (map['marketKey'] as String).trim().isNotEmpty) {
      marketKey = (map['marketKey'] as String).trim();
    } else if (map['market'] is String && (map['market'] as String).trim().isNotEmpty) {
      marketKey = (map['market'] as String).trim();
    } else if (map['marketName'] is String && (map['marketName'] as String).trim().isNotEmpty) {
      marketKey = (map['marketName'] as String).trim();
    }

    String marketName = '';
    if (map['marketName'] is String && (map['marketName'] as String).trim().isNotEmpty) {
      marketName = (map['marketName'] as String).trim();
    } else if (map['market'] is String && (map['market'] as String).trim().isNotEmpty) {
      marketName = (map['market'] as String).trim();
    } else {
      marketName = marketKey;
    }

    // tier
    final String tier = (map['tier'] is String && (map['tier'] as String).trim().isNotEmpty)
        ? (map['tier'] as String).trim()
        : 'free';

    // score
    double score = 0.0;
    final s = map['score'];
    if (s is num) {
      score = s.toDouble();
    } else if (s is String) {
      score = double.tryParse(s) ?? 0.0;
    }

    // passed
    final bool passed = (map['passed'] is bool) ? (map['passed'] as bool) : false;

    // --- Extract the predictions map in a resilient way ---
    dynamic rawPredictions;
    if (map.containsKey('predictions')) {
      rawPredictions = map['predictions'];
    } else if (map.containsKey('p')) {
      rawPredictions = map['p'];
    } else {
      // Possibly map-of-markets like { "kalyan": { ... } }
      final firstMapEntry =
      map.entries.firstWhere((e) => e.value is Map<String, dynamic>, orElse: () => MapEntry('', <String, dynamic>{}));
      if (firstMapEntry.value is Map<String, dynamic>) {
        rawPredictions = firstMapEntry.value;
        // ensure nested map gets its marketKey if missing
        if (!(rawPredictions as Map).containsKey('marketKey')) {
          (rawPredictions as Map)['marketKey'] = firstMapEntry.key;
        }
      } else {
        rawPredictions = <String, dynamic>{};
      }
    }

    final Map<String, dynamic> preds = <String, dynamic>{};

    if (rawPredictions is Map) {
      (rawPredictions as Map).forEach((k, v) {
        preds[k.toString()] = _normalizeValue(v);
      });
    } else if (rawPredictions is List) {
      preds['list'] = _normalizeValue(rawPredictions);
    } else {
      // leave preds empty
    }

    // Ensure keys that older code expects exist
    if (!preds.containsKey('marketKey')) preds['marketKey'] = marketKey;
    if (!preds.containsKey('marketName')) preds['marketName'] = marketName;
    if (!preds.containsKey('tier')) preds['tier'] = tier;

    return Prediction(
      marketKey: marketKey,
      marketName: marketName,
      tier: tier,
      p: preds,
      score: score,
      passed: passed,
    );
  }

  /// Convert nested values to safe representations:
  /// - Lists become List<String>
  /// - Maps processed recursively
  /// - Scalars become strings
  static dynamic _normalizeValue(dynamic v) {
    if (v == null) return <String>[];
    if (v is List) {
      return v.map((e) => e == null ? '' : e.toString()).toList(growable: false);
    }
    if (v is Map) {
      final out = <String, dynamic>{};
      v.forEach((k, val) {
        out[k.toString()] = _normalizeValue(val);
      });
      return out;
    }
    // scalar
    return v.toString();
  }

  Map<String, dynamic> toJson() {
    final out = Map<String, dynamic>.from(p);
    out['marketKey'] = marketKey;
    out['marketName'] = marketName;
    out['tier'] = tier;
    out['score'] = score;
    out['passed'] = passed;
    return out;
  }

  // ------------------------------
  // Convenience helpers to avoid
  // List<dynamic> -> List<String> errors
  // ------------------------------

  /// Safely returns the raw p[key] as a List<String>
  List<String> asStringList(String key) {
    final v = p[key];
    if (v == null) return <String>[];
    if (v is List) {
      try {
        return v.map((e) => e == null ? '' : e.toString()).toList(growable: false);
      } catch (_) {
        return v.map((e) => e?.toString() ?? '').toList(growable: false);
      }
    }
    return <String>[v.toString()];
  }

  /// Common named getters (older code might reference these patterns or p['open_pannas'])
  List<String> get openPannas => asStringList('open_pannas');
  List<String> get closePannas => asStringList('close_pannas');
  List<String> get openDigits => asStringList('open_digits');
  List<String> get closeDigits => asStringList('close_digits');
  List<String> get jodis => asStringList('jodis');

  /// Safe first-as-string helpers
  String firstOpenPanna() => openPannas.isNotEmpty ? openPannas.first : '';
  String firstClosePanna() => closePannas.isNotEmpty ? closePannas.first : '';

/// Legacy helper name compatibility:
/// Some places used p['open_pannas'] directly expecting List<String>.
/// To avoid changing main.dart, ensure p[...] returns List<String> in the parsed model.
}