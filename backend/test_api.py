"""
Simple test script for FinArmor API
Run: python test_api.py
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name):
    print(f"\n{BLUE}{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}{RESET}")

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_response(response):
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

# Test Variables
test_email = f"test_{int(datetime.now().timestamp())}@example.com"
test_password = "TestPassword123!"
access_token = None

def test_health():
    """Test health check endpoint"""
    print_test("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print_success(f"Server healthy - MongoDB connected")
            print_response(response)
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Connection failed: {str(e)}")

def test_register():
    """Test user registration"""
    global access_token
    print_test("User Registration")
    
    payload = {
        "name": "Test User",
        "email": test_email,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=payload)
        if response.status_code == 200:
            print_success("Registration successful")
            data = response.json()
            access_token = data.get("access_token")
            if access_token:
                print_success(f"Token received (first 50 chars): {access_token[:50]}...")
            print_response(response)
        else:
            print_error(f"Registration failed with status {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

def test_login():
    """Test user login"""
    global access_token
    print_test("User Login")
    
    payload = {
        "email": test_email,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        if response.status_code == 200:
            print_success("Login successful")
            data = response.json()
            access_token = data.get("access_token")
            if access_token:
                print_success(f"Token received (first 50 chars): {access_token[:50]}...")
            print_response(response)
        else:
            print_error(f"Login failed with status {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

def test_get_user():
    """Test get user profile"""
    print_test("Get User Profile")
    
    if not access_token:
        print_error("No access token available. Run registration/login first.")
        return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/user/me", headers=headers)
        if response.status_code == 200:
            print_success("User profile retrieved")
            print_response(response)
        else:
            print_error(f"Failed with status {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

def test_update_user():
    """Test update user profile"""
    print_test("Update User Profile")
    
    if not access_token:
        print_error("No access token available. Run registration/login first.")
        return
    
    payload = {
        "name": "Updated Name",
        "age": 28,
        "employment_type": "Software Engineer",
        "location": "New York"
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.put(f"{BASE_URL}/user/update", json=payload, headers=headers)
        if response.status_code == 200:
            print_success("User profile updated")
            print_response(response)
        else:
            print_error(f"Update failed with status {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

def test_finance_update():
    """Test finance data update"""
    print_test("Update Finance Data")
    
    if not access_token:
        print_error("No access token available. Run registration/login first.")
        return
    
    payload = {
        "income": 5000.0,
        "expenses": 2000.0,
        "savings": 1500.0,
        "debt": 500.0,
        "emi": 200.0
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.post(f"{BASE_URL}/finance/update", json=payload, headers=headers)
        if response.status_code == 200:
            print_success("Finance data updated")
            print_response(response)
        else:
            print_error(f"Update failed with status {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

def test_finance_analysis():
    """Test finance analysis"""
    print_test("Get Finance Analysis")
    
    if not access_token:
        print_error("No access token available. Run registration/login first.")
        return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/finance/analysis", headers=headers)
        if response.status_code == 200:
            print_success("Finance analysis retrieved")
            print_response(response)
        else:
            print_error(f"Failed with status {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

def test_ask_query():
    """Test ask query"""
    print_test("Ask Query")
    
    if not access_token:
        print_error("No access token available. Run registration/login first.")
        return
    
    payload = {
        "question": "How can I improve my financial situation?"
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.post(f"{BASE_URL}/query/ask", json=payload, headers=headers)
        if response.status_code == 200:
            print_success("Query processed")
            print_response(response)
        else:
            print_error(f"Query failed with status {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

def test_query_history():
    """Test get query history"""
    print_test("Get Query History")
    
    if not access_token:
        print_error("No access token available. Run registration/login first.")
        return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/query/history", headers=headers)
        if response.status_code == 200:
            print_success("Query history retrieved")
            print_response(response)
        else:
            print_error(f"Failed with status {response.status_code}")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

if __name__ == "__main__":
    print(f"\n{BLUE}FinArmor API Test Suite{RESET}")
    print(f"Testing: {BASE_URL}\n")
    
    # Run all tests
    test_health()
    test_register()
    test_login()
    test_get_user()
    test_update_user()
    test_finance_update()
    test_finance_analysis()
    test_ask_query()
    test_query_history()
    
    print(f"\n{BLUE}{'='*60}")
    print("All tests completed!")
    print(f"{'='*60}{RESET}\n")
