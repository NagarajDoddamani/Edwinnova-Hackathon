import 'package:flutter/material.dart';

import 'custom_input.dart';

class ExpenseForm extends StatelessWidget {
  final TextEditingController expenseController;

  const ExpenseForm({
    super.key,
    required this.expenseController,
  });

  @override
  Widget build(BuildContext context) {
    return CustomInput(
      label: 'Monthly Expenses',
      hintText: 'Enter your monthly expenses',
      controller: expenseController,
      keyboardType: TextInputType.number,
    );
  }
}
