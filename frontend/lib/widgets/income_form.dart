import 'package:flutter/material.dart';

import 'custom_input.dart';

class IncomeForm extends StatelessWidget {
  final TextEditingController incomeController;

  const IncomeForm({
    super.key,
    required this.incomeController,
  });

  @override
  Widget build(BuildContext context) {
    return CustomInput(
      label: 'Monthly Income',
      hintText: 'Enter your monthly income',
      controller: incomeController,
      keyboardType: TextInputType.number,
    );
  }
}
