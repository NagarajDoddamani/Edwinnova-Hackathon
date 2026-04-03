class FinanceModel {
  final double monthlyIncome;
  final double monthlyExpenses;
  final double totalSavings;
  final double totalDebt;
  final double emiAmount;

  const FinanceModel({
    required this.monthlyIncome,
    required this.monthlyExpenses,
    required this.totalSavings,
    required this.totalDebt,
    required this.emiAmount,
  });

  factory FinanceModel.fromJson(Map<String, dynamic> json) {
    return FinanceModel(
      monthlyIncome: (json['monthlyIncome'] as num?)?.toDouble() ?? 0,
      monthlyExpenses: (json['monthlyExpenses'] as num?)?.toDouble() ?? 0,
      totalSavings: (json['totalSavings'] as num?)?.toDouble() ?? 0,
      totalDebt: (json['totalDebt'] as num?)?.toDouble() ?? 0,
      emiAmount: (json['emiAmount'] as num?)?.toDouble() ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'monthlyIncome': monthlyIncome,
      'monthlyExpenses': monthlyExpenses,
      'totalSavings': totalSavings,
      'totalDebt': totalDebt,
      'emiAmount': emiAmount,
    };
  }
}
