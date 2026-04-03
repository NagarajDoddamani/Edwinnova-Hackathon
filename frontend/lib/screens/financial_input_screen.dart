import 'package:flutter/material.dart';

import '../models/finance_model.dart';
import '../models/user_model.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';
import '../widgets/expense_form.dart';
import '../widgets/income_form.dart';

class FinancialInputScreen extends StatefulWidget {
  const FinancialInputScreen({super.key});

  @override
  State<FinancialInputScreen> createState() => _FinancialInputScreenState();
}

class _FinancialInputScreenState extends State<FinancialInputScreen> {
  final _incomeController = TextEditingController();
  final _expenseController = TextEditingController();
  final _apiService = ApiService();

  @override
  void dispose() {
    _incomeController.dispose();
    _expenseController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final income = double.tryParse(_incomeController.text) ?? 0;
    final expenses = double.tryParse(_expenseController.text) ?? 0;

    final response = await _apiService.getRecommendation(
      user: const UserModel(
        id: 'demo-user',
        name: 'Demo User',
        email: 'demo@example.com',
      ),
      finance: FinanceModel(
        monthlyIncome: income,
        monthlyExpenses: expenses,
        totalSavings: 0,
        totalDebt: 0,
        emiAmount: 0,
      ),
    );

    if (!mounted) return;
    Navigator.pushNamed(context, Routes.result, arguments: response);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Financial Input')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            IncomeForm(incomeController: _incomeController),
            const SizedBox(height: 12),
            ExpenseForm(expenseController: _expenseController),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _submit,
              child: const Text('Get Recommendation'),
            ),
          ],
        ),
      ),
    );
  }
}
