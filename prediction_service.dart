// lib/services/prediction_service.dart
import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import '../models/prediction.dart';

class PredictionService {
  static const String _remoteUrl =
      'https://raw.githubusercontent.com/pranitborkar98/sattaboss-data/main/data/todays_predictions.json';
  static const String _assetPath = 'assets/todays_predictions.json';

  Future<List<Prediction>> load() async {
    List<dynamic> listData = [];

    // Try remote first (cache-busted)
    try {
      final url = '$_remoteUrl?nocache=${DateTime.now().millisecondsSinceEpoch}';
      final resp = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 20));
      if (resp.statusCode == 200) {
        final decoded = json.decode(resp.body);
        if (decoded is Map<String, dynamic> && decoded['data'] is List) {
          listData = decoded['data'] as List<dynamic>;
        } else if (decoded is Map<String, dynamic> && decoded['markets'] is List) {
          listData = decoded['markets'] as List<dynamic>;
        } else if (decoded is List) {
          listData = decoded;
        } else if (decoded is Map<String, dynamic>) {
          final vals = <dynamic>[];
          decoded.forEach((k, v) {
            if (v is Map<String, dynamic>) {
              final copy = Map<String, dynamic>.from(v);
              if (copy['marketKey'] == null || (copy['marketKey'] is String && (copy['marketKey'] as String).trim().isEmpty)) {
                copy['marketKey'] = k;
              }
              vals.add(copy);
            }
          });
          if (vals.isNotEmpty) listData = vals;
        }
      }
    } catch (_) {
      // ignore remote failure
    }

    if (listData.isEmpty) {
      try {
        final raw = await rootBundle.loadString(_assetPath);
        final localDecoded = json.decode(raw);
        if (localDecoded is Map<String, dynamic> && localDecoded['data'] is List) {
          listData = localDecoded['data'] as List<dynamic>;
        } else if (localDecoded is Map<String, dynamic> && localDecoded['markets'] is List) {
          listData = localDecoded['markets'] as List<dynamic>;
        } else if (localDecoded is List) {
          listData = localDecoded;
        } else if (localDecoded is Map<String, dynamic>) {
          final vals = <dynamic>[];
          localDecoded.forEach((k, v) {
            if (v is Map<String, dynamic>) {
              final copy = Map<String, dynamic>.from(v);
              if (copy['marketKey'] == null || (copy['marketKey'] is String && (copy['marketKey'] as String).trim().isEmpty)) {
                copy['marketKey'] = k;
              }
              vals.add(copy);
            }
          });
          if (vals.isNotEmpty) listData = vals;
        }
      } catch (_) {
        return <Prediction>[];
      }
    }

    final List<Prediction> out = [];
    for (final e in listData) {
      try {
        if (e is Map<String, dynamic>) {
          // Defensive marketKey logic (same as earlier)
          String? mk;
          if (e['marketKey'] is String && (e['marketKey'] as String).trim().isNotEmpty) {
            mk = (e['marketKey'] as String).trim();
          }
          if (mk == null) {
            if (e['market'] is String && (e['market'] as String).trim().isNotEmpty) {
              mk = (e['market'] as String).trim();
            } else if (e['marketName'] is String && (e['marketName'] as String).trim().isNotEmpty) {
              mk = (e['marketName'] as String).trim();
            }
          }

          if (mk == null) {
            final keys = e.keys.whereType<String>().toList();
            if (keys.isNotEmpty) {
              final firstKey = keys.first;
              final maybe = e[firstKey];
              if (maybe is Map<String, dynamic>) {
                final newMap = Map<String, dynamic>.from(maybe);
                newMap['marketKey'] = firstKey;
                out.add(Prediction.fromJson(newMap));
                continue;
              }
            }
          }

          if (mk != null) e['marketKey'] = mk;
          out.add(Prediction.fromJson(Map<String, dynamic>.from(e)));
        }
      } catch (_) {
        // skip invalid
      }
    }
    return out;
  }
}