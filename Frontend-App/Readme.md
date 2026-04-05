# 📱 FinArmor Mobile App — Flutter System Manual

> **Frontend App Architecture (Flutter Developer Guide)**
> Designed for smooth UX, modular UI, and seamless backend integration.

---

## 🎯 Purpose

The Flutter app is responsible for:

* Collecting user data (basic + financial)
* Providing step-by-step guided input
* Visualizing financial analytics
* Communicating with backend (`/ai/analyze`)

---

## 🏗️ Architecture Overview

```text id="h9w2fp"
User → Flutter UI → API Service → FastAPI Backend → Response → UI Update
```

---

## 📂 Project Structure

```text id="3otk0k"
frontend-app/
│
├── lib/
│   ├── main.dart
│
│   ├── screens/
│   │   ├── welcome_screen.dart
│   │   ├── register_screen.dart
│   │   ├── financial_screen.dart
│   │   ├── dashboard_screen.dart
│
│   ├── widgets/
│   │   ├── progress_bar.dart
│   │   ├── input_field.dart
│   │   ├── dynamic_list.dart
│
│   ├── models/
│   │   ├── user_model.dart
│   │   ├── finance_model.dart
│
│   ├── services/
│   │   └── api_service.dart
│
│   ├── providers/
│   │   └── app_provider.dart
│
│   └── utils/
│       └── constants.dart
│
└── pubspec.yaml
```

---

## 🔄 Application Flow

```text id="5k4b0c"
Welcome Screen
   ↓
Register Screen (Basic Info)
   ↓
Financial Screen (Dynamic Inputs + PDF Upload)
   ↓
API Call → /ai/analyze
   ↓
Dashboard Screen (Analytics + AI Insights)
```

---

## 📌 Core Screens

---

### 1. Welcome Screen

* App intro
* “Get Started” button

---

### 2. Register Screen

Collect:

* Name
* Email
* Age
* Gender
* Employment Type
* Location

---

### 3. Financial Screen

Features:

* Dynamic lists:

  * Income []
  * Expenses []
  * Savings []
* Add/remove fields
* PDF upload (bank statement)

---

### 4. Dashboard Screen

Displays:

* Financial metrics
* Risk score
* AI advice
* Charts

---

## 🧩 Key Widgets

---

### 🔹 Progress Bar

Tracks completion:

```dart id="tq1x9g"
LinearProgressIndicator(value: progress)
```

---

### 🔹 Dynamic List Widget

Reusable for:

```text id="9kkq1j"
income[]
expenses[]
savings[]
```

---

### 🔹 Input Field Widget

Reusable styled input fields

---

## 🔌 API Integration

## `services/api_service.dart`

```dart id="xotk1g"
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = "http://10.0.2.2:8000";

  static Future<Map<String, dynamic>> analyze(data) async {
    final res = await http.post(
      Uri.parse("$baseUrl/ai/analyze"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode(data),
    );

    return jsonDecode(res.body);
  }
}
```

---

## 📊 Analytics Visualization

Use:

```yaml id="gdfb3k"
fl_chart: ^0.66.0
```

Display:

* Pie chart → Income vs Expense
* Bar chart → Savings

---

## 🧠 State Management

Use Provider:

```yaml id="k8l9wd"
provider: ^6.0.0
```

---

## Example:

```dart id="8z2v7o"
class AppProvider extends ChangeNotifier {
  Map user = {};
  Map financial = {};
  Map result = {};

  void setUser(data) {
    user = data;
    notifyListeners();
  }

  void setResult(data) {
    result = data;
    notifyListeners();
  }
}
```

---

## ⚠️ API CONTRACT

### Endpoint

```text id="h0v9ka"
/ai/analyze
```

---

### Request

```json id="kg2n0r"
{
  "user_profile": {...},
  "financial_data": {...},
  "preferences": {...}
}
```

---

### Response

```json id="3ptmvn"
{
  "metrics": {...},
  "rule": {...},
  "profile": {...},
  "risk": {...},
  "advice": "..."
}
```

---

## 🎨 UI/UX DESIGN

* Dark fintech theme
* Card-based layout
* Smooth transitions
* Step-by-step flow
* Minimal clutter

---

## 🛠️ Required Packages

```yaml id="v2e8xq"
http: ^0.13.5
provider: ^6.0.0
fl_chart: ^0.66.0
file_picker: ^8.0.0
percent_indicator: ^4.2.3
```

---

## 🚀 Run App

```bash id="1ey0th"
flutter run
```

---

## 🔐 Best Practices

```text id="z1g8wx"
✔ Separate UI and logic
✔ Use reusable widgets
✔ Validate inputs
✔ Handle API errors
✔ Maintain clean state
```

---

## ❗ Common Mistakes

```text id="r2o4nq"
❌ Hardcoding API URLs
❌ Mixing business logic in UI
❌ Ignoring loading states
❌ Not structuring JSON properly
```

---

## 🔮 Future Enhancements

* Voice assistant integration
* Push notifications
* Offline mode
* Multi-language support

---

## 🏁 Summary

```text id="6yqvlf"
Flutter = UI Layer
API Service = Communication
Backend = Intelligence
```

---

> **Mobile App = User Experience Layer**
> Fast. Clean. Interactive.
