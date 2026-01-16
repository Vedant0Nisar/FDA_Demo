import requests
import time
import sys
import uuid
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("=== Testing FastAPI Endpoints V2 (Unique Batch) ===\n")
    
    # Wait for server to be up
    print("Waiting for API to Start...")
    try:
        r = requests.get(f"{BASE_URL}/")
        if r.status_code == 200:
            print("API is Online!")
        else:
            print(f"API returned {r.status_code}")
    except:
        print("Error: API is NOT responding. Make sure uvicorn is running.")
        sys.exit(1)

    # Generate Unique Batch ID
    batch_id = f"BATCH-{int(time.time())}"
    print(f"\nUsing Batch ID: {batch_id}")

    # 1. Test Batch Creation
    print("\n[1] Testing POST /batches (Create New Batch)")
    new_batch = {
        "batch_id": batch_id,
        "product_gtin": "GTIN-PARA-500", 
        "manufacturer_license": "LIC-ABC-001",
        "mfg_date": "2025-05-01",
        "exp_date": "2027-05-01",
        "batch_size": 5000
    }
    
    try:
        r = requests.post(f"{BASE_URL}/batches/", json=new_batch)
        if r.status_code == 201:
            data = r.json()
            print(f"    -> Success! Batch Created.")
            print(f"    -> Hash: {data['hash']}")
            print(f"    -> QR Code generated: {len(data['qr_code_base64'])} chars")
        else:
            print(f"    -> Failed: {r.status_code} - {r.text}")
            sys.exit(1)
    except Exception as e:
        print(f"    -> Exception: {e}")
        sys.exit(1)

    # 2. Test Verification (Authentic)
    print("\n[2] Testing POST /verify (Authentic)")
    verify_payload = {"batch_id": batch_id}
    r = requests.post(f"{BASE_URL}/verify/", json=verify_payload)
    data = r.json()
    print(f"    -> Status: {data.get('status')}")
    
    if data.get('status') == 'AUTHENTIC':
        print("    -> PASS")
    else:
        print(f"    -> FAIL (Expected AUTHENTIC, got {data.get('status')})")

    # 3. Test Event Chain
    print("\n[3] Testing POST /batches/events (Update Status)")
    event_payload = {
        "action_type": "SHIPPED",
        "description": "Shipped to Distribution Center",
        "location": {"lat": 19.0760, "long": 72.8777},
        "user_id": 1,
        "department_id": 1
    }
    
    r = requests.post(f"{BASE_URL}/batches/{batch_id}/events", json=event_payload)
    if r.status_code == 201:
        data = r.json()
        print(f"    -> Success! Status Updated to: {data.get('current_status')}")
        print(f"    -> Event Hash: {data.get('hash')}")
        
    else:
        print(f"    -> Failed: {r.status_code} - {r.text}")

    print("\n=== API Test V2 Complete ===")

if __name__ == "__main__":
    test_api()
