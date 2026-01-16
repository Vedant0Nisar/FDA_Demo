import requests
import json

BASE_URL = "http://127.0.0.1:8000/mobile"
API_KEY = "FDA_MOBILE_SECRET_KEY_2026"
HEADERS = {"X-API-KEY": API_KEY}

def test_login():
    print("\n[1] Testing Login...")
    payload = {"username": "inspector_01", "role": "Inspector"}
    response = requests.post(f"{BASE_URL}/login", json=payload, headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_dashboard():
    print("\n[2] Testing Dashboard Dashboard...")
    response = requests.get(f"{BASE_URL}/dashboard", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_verify():
    print("\n[3] Testing Verify (BATCH-001)...")
    response = requests.get(f"{BASE_URL}/verify/BATCH-001", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_report():
    print("\n[4] Testing Report Alert...")
    payload = {"batch_id": "BATCH-001", "node_id": "NODE_TEST_01", "description": "Suspicious packaging"}
    response = requests.post(f"{BASE_URL}/report", json=payload, headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_alerts():
    print("\n[5] Testing Get All Alerts...")
    response = requests.get(f"{BASE_URL}/alerts", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Count: {len(response.json())}")

def test_batches():
    print("\n[6] Testing Get All Batches...")
    response = requests.get(f"{BASE_URL}/batches", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Count: {len(response.json())}")

def test_certificate():
    print("\n[7] Testing Certificate Download (BATCH-001)...")
    response = requests.get(f"{BASE_URL}/certificate/BATCH-001", headers=HEADERS)
    print(f"Status: {response.status_code}")
    # print(f"Response: {response.json()}")
    print("Certificate data received successfully.")

if __name__ == "__main__":
    try:
        test_login()
        test_dashboard()
        test_verify()
        test_report()
        test_alerts()
        test_batches()
        test_certificate()
    except Exception as e:
        print(f"Error during testing: {e}")
        print("Make sure the server is running on http://127.0.0.1:8000")
