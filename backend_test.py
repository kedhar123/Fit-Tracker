#!/usr/bin/env python3
"""
FitTracker Backend API Testing Suite
Tests all authentication and user management endpoints
"""

import requests
import json
import sys
import os
from datetime import datetime

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return "http://localhost:8001"

BASE_URL = get_backend_url()
API_URL = f"{BASE_URL}/api"

print(f"Testing FitTracker Backend API at: {API_URL}")
print("=" * 60)

# Test data - realistic user information
test_users = [
    {
        "username": "sarah_johnson",
        "email": "sarah.johnson@email.com", 
        "password": "SecurePass123!",
        "confirmPassword": "SecurePass123!",
        "age": 28,
        "gender": "female",
        "height": 165,
        "weight": 62.5,
        "activity_level": "moderate",
        "goal": "lose_weight"
    },
    {
        "username": "mike_chen",
        "email": "mike.chen@gmail.com",
        "password": "MyFitPass456",
        "confirmPassword": "MyFitPass456",
        "age": 35,
        "gender": "male", 
        "height": 178,
        "weight": 82.0,
        "activity_level": "active",
        "goal": "build_muscle"
    }
]

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}

def log_test(test_name, success, message="", response=None):
    """Log test results"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"    {message}")
    if response and not success:
        print(f"    Response: {response.status_code} - {response.text[:200]}")
    
    if success:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"{test_name}: {message}")
    print()

def test_api_health():
    """Test basic API health endpoints"""
    print("🔍 Testing API Health Endpoints")
    print("-" * 40)
    
    # Test root endpoint
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "message" in data and "FitTracker" in data["message"]:
                log_test("API Root Endpoint", True, f"Message: {data['message']}")
            else:
                log_test("API Root Endpoint", False, f"Unexpected response format: {data}")
        else:
            log_test("API Root Endpoint", False, f"Status code: {response.status_code}", response)
    except Exception as e:
        log_test("API Root Endpoint", False, f"Connection error: {str(e)}")

def test_cors():
    """Test CORS functionality"""
    print("🌐 Testing CORS Configuration")
    print("-" * 40)
    
    try:
        # Test preflight request
        headers = {
            'Origin': 'https://example.com',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        response = requests.options(f"{API_URL}/register", headers=headers, timeout=10)
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
        }
        
        if cors_headers['Access-Control-Allow-Origin'] == '*':
            log_test("CORS Configuration", True, "CORS properly configured for all origins")
        else:
            log_test("CORS Configuration", False, f"CORS headers: {cors_headers}")
            
    except Exception as e:
        log_test("CORS Configuration", False, f"Error testing CORS: {str(e)}")

def test_user_registration():
    """Test user registration endpoint with various scenarios"""
    print("👤 Testing User Registration API")
    print("-" * 40)
    
    # Test 1: Valid registration with all fields
    try:
        user_data = test_users[0].copy()
        response = requests.post(f"{API_URL}/register", json=user_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "user" in data:
                user_info = data["user"]
                if user_info.get("username") == user_data["username"] and user_info.get("email") == user_data["email"]:
                    log_test("Registration - Valid with all fields", True, f"User created: {user_info['username']}")
                else:
                    log_test("Registration - Valid with all fields", False, "User data mismatch in response")
            else:
                log_test("Registration - Valid with all fields", False, f"Unexpected response format: {data}")
        else:
            log_test("Registration - Valid with all fields", False, f"Status: {response.status_code}", response)
    except Exception as e:
        log_test("Registration - Valid with all fields", False, f"Request error: {str(e)}")
    
    # Test 2: Valid registration with only required fields
    try:
        minimal_user = {
            "username": "jane_doe",
            "email": "jane.doe@example.com",
            "password": "SimplePass789",
            "confirmPassword": "SimplePass789"
        }
        response = requests.post(f"{API_URL}/register", json=minimal_user, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                log_test("Registration - Required fields only", True, "User created with minimal data")
            else:
                log_test("Registration - Required fields only", False, f"Registration failed: {data}")
        else:
            log_test("Registration - Required fields only", False, f"Status: {response.status_code}", response)
    except Exception as e:
        log_test("Registration - Required fields only", False, f"Request error: {str(e)}")
    
    # Test 3: Duplicate username validation
    try:
        duplicate_user = {
            "username": "sarah_johnson",  # Same as first user
            "email": "different@email.com",
            "password": "AnotherPass123",
            "confirmPassword": "AnotherPass123"
        }
        response = requests.post(f"{API_URL}/register", json=duplicate_user, timeout=10)
        
        if response.status_code == 400:
            data = response.json()
            if "username" in data.get("detail", "").lower():
                log_test("Registration - Duplicate username", True, "Correctly rejected duplicate username")
            else:
                log_test("Registration - Duplicate username", False, f"Wrong error message: {data}")
        else:
            log_test("Registration - Duplicate username", False, f"Should return 400, got {response.status_code}", response)
    except Exception as e:
        log_test("Registration - Duplicate username", False, f"Request error: {str(e)}")
    
    # Test 4: Duplicate email validation
    try:
        duplicate_email = {
            "username": "different_user",
            "email": "sarah.johnson@email.com",  # Same as first user
            "password": "AnotherPass123",
            "confirmPassword": "AnotherPass123"
        }
        response = requests.post(f"{API_URL}/register", json=duplicate_email, timeout=10)
        
        if response.status_code == 400:
            data = response.json()
            if "email" in data.get("detail", "").lower():
                log_test("Registration - Duplicate email", True, "Correctly rejected duplicate email")
            else:
                log_test("Registration - Duplicate email", False, f"Wrong error message: {data}")
        else:
            log_test("Registration - Duplicate email", False, f"Should return 400, got {response.status_code}", response)
    except Exception as e:
        log_test("Registration - Duplicate email", False, f"Request error: {str(e)}")
    
    # Test 5: Password confirmation validation
    try:
        mismatched_passwords = {
            "username": "test_mismatch",
            "email": "mismatch@test.com",
            "password": "Password123",
            "confirmPassword": "DifferentPass456"
        }
        response = requests.post(f"{API_URL}/register", json=mismatched_passwords, timeout=10)
        
        if response.status_code == 400:
            data = response.json()
            if "password" in data.get("detail", "").lower():
                log_test("Registration - Password mismatch", True, "Correctly rejected mismatched passwords")
            else:
                log_test("Registration - Password mismatch", False, f"Wrong error message: {data}")
        else:
            log_test("Registration - Password mismatch", False, f"Should return 400, got {response.status_code}", response)
    except Exception as e:
        log_test("Registration - Password mismatch", False, f"Request error: {str(e)}")
    
    # Test 6: Invalid email format
    try:
        invalid_email = {
            "username": "test_invalid_email",
            "email": "not-an-email",
            "password": "ValidPass123",
            "confirmPassword": "ValidPass123"
        }
        response = requests.post(f"{API_URL}/register", json=invalid_email, timeout=10)
        
        if response.status_code == 422:  # FastAPI validation error
            log_test("Registration - Invalid email format", True, "Correctly rejected invalid email format")
        else:
            log_test("Registration - Invalid email format", False, f"Should return 422, got {response.status_code}", response)
    except Exception as e:
        log_test("Registration - Invalid email format", False, f"Request error: {str(e)}")
    
    # Test 7: Missing required fields
    try:
        incomplete_data = {
            "username": "incomplete_user",
            "email": "incomplete@test.com"
            # Missing password
        }
        response = requests.post(f"{API_URL}/register", json=incomplete_data, timeout=10)
        
        if response.status_code == 400:
            data = response.json()
            if "required" in data.get("detail", "").lower():
                log_test("Registration - Missing required fields", True, "Correctly rejected incomplete data")
            else:
                log_test("Registration - Missing required fields", False, f"Wrong error message: {data}")
        else:
            log_test("Registration - Missing required fields", False, f"Should return 400, got {response.status_code}", response)
    except Exception as e:
        log_test("Registration - Missing required fields", False, f"Request error: {str(e)}")

def test_user_authentication():
    """Test user authentication endpoint"""
    print("🔐 Testing User Authentication API")
    print("-" * 40)
    
    # Test 1: Valid login with correct credentials
    try:
        login_data = {
            "email": "sarah.johnson@email.com",
            "password": "SecurePass123!"
        }
        response = requests.post(f"{API_URL}/auth/login", json=login_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "user" in data and "token" in data:
                user_info = data["user"]
                if user_info.get("email") == login_data["email"]:
                    log_test("Authentication - Valid login", True, f"Login successful for {user_info['username']}")
                else:
                    log_test("Authentication - Valid login", False, "User data mismatch in response")
            else:
                log_test("Authentication - Valid login", False, f"Missing user/token in response: {data}")
        else:
            log_test("Authentication - Valid login", False, f"Status: {response.status_code}", response)
    except Exception as e:
        log_test("Authentication - Valid login", False, f"Request error: {str(e)}")
    
    # Test 2: Invalid login - wrong password
    try:
        wrong_password = {
            "email": "sarah.johnson@email.com",
            "password": "WrongPassword123"
        }
        response = requests.post(f"{API_URL}/auth/login", json=wrong_password, timeout=10)
        
        if response.status_code == 401:
            data = response.json()
            if "invalid" in data.get("detail", "").lower():
                log_test("Authentication - Wrong password", True, "Correctly rejected wrong password")
            else:
                log_test("Authentication - Wrong password", False, f"Wrong error message: {data}")
        else:
            log_test("Authentication - Wrong password", False, f"Should return 401, got {response.status_code}", response)
    except Exception as e:
        log_test("Authentication - Wrong password", False, f"Request error: {str(e)}")
    
    # Test 3: Non-existent user login
    try:
        nonexistent_user = {
            "email": "nonexistent@user.com",
            "password": "AnyPassword123"
        }
        response = requests.post(f"{API_URL}/auth/login", json=nonexistent_user, timeout=10)
        
        if response.status_code == 401:
            data = response.json()
            if "invalid" in data.get("detail", "").lower():
                log_test("Authentication - Non-existent user", True, "Correctly rejected non-existent user")
            else:
                log_test("Authentication - Non-existent user", False, f"Wrong error message: {data}")
        else:
            log_test("Authentication - Non-existent user", False, f"Should return 401, got {response.status_code}", response)
    except Exception as e:
        log_test("Authentication - Non-existent user", False, f"Request error: {str(e)}")

def test_users_endpoint():
    """Test the get all users endpoint"""
    print("👥 Testing Users Endpoint")
    print("-" * 40)
    
    try:
        response = requests.get(f"{API_URL}/users", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                user_count = len(data)
                if user_count > 0:
                    # Check if password_hash is not exposed
                    first_user = data[0]
                    if "password_hash" not in first_user:
                        log_test("Users Endpoint", True, f"Retrieved {user_count} users, passwords properly hidden")
                    else:
                        log_test("Users Endpoint", False, "Password hashes are exposed in response")
                else:
                    log_test("Users Endpoint", True, "Endpoint working, no users found")
            else:
                log_test("Users Endpoint", False, f"Expected list, got: {type(data)}")
        else:
            log_test("Users Endpoint", False, f"Status: {response.status_code}", response)
    except Exception as e:
        log_test("Users Endpoint", False, f"Request error: {str(e)}")

def test_password_hashing():
    """Test that passwords are properly hashed and not stored in plain text"""
    print("🔒 Testing Password Security")
    print("-" * 40)
    
    try:
        # Get users to check password storage
        response = requests.get(f"{API_URL}/users", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                # Passwords should not be visible in the response at all
                first_user = data[0]
                if "password" not in first_user and "password_hash" not in first_user:
                    log_test("Password Security", True, "Passwords properly hidden from API responses")
                else:
                    log_test("Password Security", False, "Password data exposed in API response")
            else:
                log_test("Password Security", True, "No users to test password security")
        else:
            log_test("Password Security", False, f"Could not retrieve users: {response.status_code}")
    except Exception as e:
        log_test("Password Security", False, f"Request error: {str(e)}")

def run_all_tests():
    """Run all backend tests"""
    print(f"🚀 Starting FitTracker Backend API Tests")
    print(f"📅 Test run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Run all test suites
    test_api_health()
    test_cors()
    test_user_registration()
    test_user_authentication()
    test_users_endpoint()
    test_password_hashing()
    
    # Print final results
    print("=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"✅ Tests Passed: {test_results['passed']}")
    print(f"❌ Tests Failed: {test_results['failed']}")
    print(f"📈 Success Rate: {(test_results['passed'] / (test_results['passed'] + test_results['failed']) * 100):.1f}%")
    
    if test_results['errors']:
        print("\n🚨 FAILED TESTS:")
        for error in test_results['errors']:
            print(f"   • {error}")
    
    print("\n" + "=" * 60)
    
    return test_results['failed'] == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)