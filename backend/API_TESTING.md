# FinArmor API Testing Guide

## ✅ Server Status
- **MongoDB**: Connected ✓
- **Database Indexes**: Created ✓
- **Server**: Running on http://127.0.0.1:8000

## 📋 API Endpoints

### 1. Health Check
```
GET http://127.0.0.1:8000/health
```
**Response**: `{"status": "healthy", "mongodb": "connected"}`

---

## 👤 AUTH ENDPOINTS

### 2. Register User
```
POST http://127.0.0.1:8000/auth/register
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepass123"
}
```
**Response**: 
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "message": "Registration successful"
}
```

---

### 3. Login User
```
POST http://127.0.0.1:8000/auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "securepass123"
}
```
**Response**: 
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "message": "Login successful"
}
```

---

### 4. Google Login
```
POST http://127.0.0.1:8000/auth/google
Content-Type: application/json

{
  "name": "John Google",
  "email": "john.google@gmail.com"
}
```
**Response**: 
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "message": "Google login successful"
}
```

---

## 👥 USER ENDPOINTS

### 5. Get User Profile
```
GET http://127.0.0.1:8000/user/me
Authorization: Bearer <ACCESS_TOKEN>
```
**Response**: 
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "age": null,
  "employment_type": null,
  "location": null,
  "created_at": "2026-04-05T10:30:00"
}
```

---

### 6. Update User Profile
```
PUT http://127.0.0.1:8000/user/update
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json

{
  "name": "John Updated",
  "age": 28,
  "employment_type": "Software Engineer",
  "location": "New York"
}
```
**Response**: 
```json
{
  "message": "updated",
  "modified_count": 1
}
```

---

## 💰 FINANCE ENDPOINTS

### 7. Update Finance Data
```
POST http://127.0.0.1:8000/finance/update
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json

{
  "income": 5000.0,
  "expenses": 2000.0,
  "savings": 1500.0,
  "debt": 500.0,
  "emi": 200.0
}
```
**Response**: 
```json
{
  "message": "finance updated",
  "success": true
}
```

---

### 8. Get Finance Analysis
```
GET http://127.0.0.1:8000/finance/analysis
Authorization: Bearer <ACCESS_TOKEN>
```
**Response**: 
```json
{
  "income": 5000.0,
  "expenses": 2000.0,
  "savings": 3000.0,
  "goals": 1,
  "profile_completion": "80%",
  "recommendation": "Increase savings"
}
```

---

## ❓ QUERY ENDPOINTS

### 9. Ask Query
```
POST http://127.0.0.1:8000/query/ask
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json

{
  "question": "How can I save more money?"
}
```
**Response**: 
```json
{
  "answer": "AI Response: How can I save more money?",
  "success": true
}
```

---

### 10. Get Query History
```
GET http://127.0.0.1:8000/query/history
Authorization: Bearer <ACCESS_TOKEN>
```
**Response**: 
```json
[
  {
    "email": "john@example.com",
    "question": "How can I save more money?",
    "answer": "AI Response: How can I save more money?",
    "timestamp": "2026-04-05T10:30:00"
  }
]
```

---

## 🔐 Authorization

All protected endpoints require a JWT token in the header:
```
Authorization: Bearer <YOUR_ACCESS_TOKEN>
```

Tokens expire after **24 hours**.

---

## 🐛 Troubleshooting

### Internal Error on Login/Register?
1. Check server logs for detailed error messages
2. Verify all fields match the schema (name, email, password formats)
3. Ensure MongoDB is connected (check `/health` endpoint)
4. Check if user already exists (for registration)

### Token Errors?
- Token may have expired (expires in 24 hours)
- Token format invalid - must be in `Authorization: Bearer <TOKEN>` format
- Use the token from the login/register response

### MongoDB Errors?
- Check MongoDB connection: `GET /health`
- Verify email is unique (database has unique index on email)

---

## 📝 Notes

- All timestamps are in UTC format
- Email validation is enforced (must be valid email format)
- Passwords are hashed with bcrypt before storage
- User emails must be unique
