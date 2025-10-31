import requests
import json
import time

# Test script for Heroku Rasa deployment
HEROKU_APP_URL = "https://expobeton-rasa-db7b1977a90f.herokuapp.com"

def test_root_endpoint():
    """Test the root endpoint"""
    try:
        response = requests.get(HEROKU_APP_URL, timeout=10)
        print(f"Root endpoint status: {response.status_code}")
        print(f"Root endpoint response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing root endpoint: {e}")
        return False

def test_health_endpoint():
    """Test the health check endpoint"""
    try:
        response = requests.get(f"{HEROKU_APP_URL}/health", timeout=10)
        print(f"Health endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Health endpoint response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing health endpoint: {e}")
        return False

def test_status_endpoint():
    """Test the status endpoint"""
    try:
        response = requests.get(f"{HEROKU_APP_URL}/status", timeout=10)
        print(f"Status endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Status endpoint response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing status endpoint: {e}")
        return False

def test_rasa_endpoint():
    """Test the Rasa API endpoint"""
    try:
        response = requests.get(f"{HEROKU_APP_URL}/version", timeout=10)
        print(f"Rasa version endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Rasa version: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing Rasa endpoint: {e}")
        return False

def main():
    print(f"Testing Rasa deployment at {HEROKU_APP_URL}")
    print("=" * 50)
    
    tests = [
        ("Root Endpoint", test_root_endpoint),
        ("Health Check", test_health_endpoint),
        ("Status Check", test_status_endpoint),
        ("Rasa Version", test_rasa_endpoint)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nTesting {test_name}...")
        result = test_func()
        results.append((test_name, result))
        time.sleep(1)  # Small delay between requests
    
    print("\n" + "=" * 50)
    print("Test Results:")
    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("All tests passed! Your deployment is working correctly.")
    else:
        print("Some tests failed. Please check your deployment configuration.")

if __name__ == "__main__":
    main()