import 'dart:convert';
import 'package:flutter/services.dart';

class MarketService {
  static final MarketService _instance = MarketService._internal();
  factory MarketService() => _instance;
  MarketService._internal();

  /// Markets that always stay premium
  final List<String> premiumMarkets = [
    "KALYAN",
    "KALYAN NIGHT",
    "RAJDHANI NIGHT",
    "MILAN DAY",
    "MILAN NIGHT",
    "MAIN BAZAR",
    "MAIN RATAN",
    "MAIN BOMBAY",
    "TIME BAZAR",
    "SUPREME NIGHT",
    "SUPREME DAY"
  ];

  /// Start as empty lists so we can check `.isNotEmpty`
  List<String> allMarkets = [];
  List<String> freeMarkets = [];

  /// Loads once; if already loaded returns immediately
  Future<void> loadMarkets() async {
    if (allMarkets.isNotEmpty) return;

    // 1. Load raw JSON
    final raw = await rootBundle.loadString('assets/cleaned_market_list.json');

    // 2. Decode as List<dynamic>, then cast each entry to String
    final List<dynamic> jsonList = json.decode(raw);
    final List<String> data = jsonList.map((e) => e.toString()).toList();

    // 3. Clean up each name, uppercase, remove unwanted substrings
    final names = data.map((item) {
      return item
          .replaceAll("_panel_chart", "")
          .replaceAll("_penal_chart", "")
          .replaceAll("satta", "")
          .replaceAll("record", "")
          .replaceAll("_", " ")
          .trim()
          .toUpperCase();
    }).toSet();

    // 4. Assign, sort, and partition into free vs premium
    allMarkets = names.toList()..sort();
    freeMarkets = allMarkets.where((m) {
      final cleanName = m.toUpperCase().replaceAll('_', ' ');
      return !premiumMarkets.any((p) => cleanName.contains(p));
    }).toList();
  }

  List<String> getAll() => allMarkets;
  List<String> getPremium() => premiumMarkets;
  List<String> getFree() => freeMarkets;
}
