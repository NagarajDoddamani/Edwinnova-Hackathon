import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/finance_model.dart';
import '../models/user_model.dart';

class ApiService {
  static String get baseUrl {
    if (kIsWeb) {
      return "http://localhost:8000";
    }

    if (defaultTargetPlatform == TargetPlatform.android) {
      return "http://10.0.2.2:8000";
    }

    return "http://localhost:8000";
  }

  static Future<Map<String, dynamic>> getRecommendation({
    required UserModel user,
    required FinanceModel finance,
    Map<String, dynamic> preferences = const {},
    Map<String, dynamic> queryContext = const {},
  }) async {
    final payload = {
      "user_profile": user.toJson(),
      "financial_data": {
        "income": finance.monthlyIncome,
        "expenses": finance.monthlyExpenses,
        "savings": finance.totalSavings,
        "debt": finance.totalDebt,
        "emi": finance.emiAmount,
      },
      "derived_metrics": {
        "monthly_surplus": finance.monthlyIncome - finance.monthlyExpenses,
      },
      "preferences": preferences,
      "query_context": queryContext,
    };

    final response = await http.post(
      Uri.parse("$baseUrl/recommendations/recommend"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode(payload),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception("Backend error: ${response.statusCode} ${response.body}");
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
