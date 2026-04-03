import 'package:flutter/material.dart';
import 'services/api_service.dart';
import 'models/user_model.dart';
import 'models/finance_model.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: TestScreen(),
    );
  }
}

class TestScreen extends StatefulWidget {
  @override
  _TestScreenState createState() => _TestScreenState();
}

class _TestScreenState extends State<TestScreen> {
  String result = "No response yet";

  void sendData() async {
    try {
      // Create UserModel object
      UserModel user = UserModel(
        name: "Sanjeevini",
        email: "sanjeevini@example.com",
      );

      // Create FinanceModel object
      FinanceModel finance = FinanceModel(
        monthlyIncome: 20000,
        monthlyExpenses: 10000,
        totalSavings: 50000,
        totalDebt: 10000,
        emiAmount: 2000,
      );

      var response = await ApiService.getRecommendation(
        user: user,
        finance: finance,
        queryContext: {
          "user_query": "I want to invest 10000"
        },
      );

      setState(() {
        result = response.toString();
      });
    } catch (e) {
      setState(() {
        result = "Error: $e";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("FinArmor Test"),
      ),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            ElevatedButton(
              onPressed: sendData,
              child: Text("Send to Backend"),
            ),
            SizedBox(height: 20),
            Expanded(
              child: SingleChildScrollView(
                child: Text(result),
              ),
            ),
          ],
        ),
      ),
    );
  }
}