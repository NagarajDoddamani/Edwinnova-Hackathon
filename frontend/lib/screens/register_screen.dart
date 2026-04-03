import 'package:flutter/material.dart';

import '../utils/constants.dart';

class RegisterScreen extends StatelessWidget {
  const RegisterScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Register')),
      body: Center(
        child: ElevatedButton(
          onPressed: () => Navigator.pushReplacementNamed(
            context,
            Routes.financialInput,
          ),
          child: const Text('Create Account'),
        ),
      ),
    );
  }
}
