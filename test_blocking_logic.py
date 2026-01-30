
import requests
import time
import sys
import uuid
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_blocking_logic():
    print("=== Testing Batch Blocking Logic ===\n")
    
    # Generate Unique Batch ID
    batch_id = f"BATCH-TEST-{int(time.time())}"
    print(f"Using Batch ID: {batch_id}")

    # 1. Create Batch
    print("\n[1] Creating Batch...")
    new_batch = {
        "batch_id": batch_id,
        "product_gtin": "GTIN-PARA-500", 
        "manufacturer_license": "LIC-ABC-001",
        "mfg_date": "2025-05-01",
        "exp_date": "2027-05-01",
        "batch_size": 1000,
        "operator_name": "Test Bot"
    }
    r = requests.post(f"{BASE_URL}/batches/", json=new_batch)
    if r.status_code != 201:
        print(f"Failed to create batch: {r.text}")
        sys.exit(1)
    print("  -> Batch Created (Status: QUARANTINE)")

    # 2. Release Batch (so we can move it to 'SHIPPED' or similar, enabling us to test the blocking later?)
    # Wait, the current logic puts it in QUARANTINE.
    # To test 'UNDER_INVESTIGATION' blocking, we first need it to be in a valid state or we can just force the status update via DB/Inspector?
    # Actually, let's use the Inspector API (Mobile Report) to flag it.
    # But Inspector API requires it to be a valid batch.
    
    # Let's bypass the 'QUARANTINE' check for COA for a moment? No, we need to respect the flow.
    # Flow: Create -> COA -> Approve -> Released.
    # OR: We can just manually simulate a direct DB update to 'UNDER_INVESTIGATION' to save time testing the whole flow?
    # The Implementation Plan said: "Move it to UNDER_INVESTIGATION (simulate inspector report)".
    # The inspector report API is: POST /mobile/report
    
    # 2. Flag Batch as UNDER_INVESTIGATION via Inspector API
    print("\n[2] Reporting Batch as Inspector (Simulating Fraud Report)...")
    report_payload = {
        "batch_id": batch_id,
        "node_id": "NODE-TEST-INSPECTOR",
        "description": "Suspicious packaging"
    }
    # We need headers for mobile api key
    headers = {"X-API-Key": "FDA_MOBILE_SECRET_KEY_2026"} 
    
    r = requests.post(f"{BASE_URL}/mobile/report", json=report_payload, headers=headers)
    if r.status_code == 200:
        print("  -> Report Submitted. Batch should be UNDER_INVESTIGATION.")
    else:
        print(f"  -> Failed to report: {r.status_code} - {r.text}")
        sys.exit(1)

    # 3. Attempt to Perform Distributor Action
    print("\n[3] Attempting Distributor Action (Should be BLOCKED)...")
    event_payload = {
        "action_type": "DISTRIBUTOR_RECEIVED",
        "description": "Trying to receive blocked batch",
        "user_id": 1,
        "department_id": 1,
        "quantity": 100
    }
    
    r = requests.post(f"{BASE_URL}/batches/{batch_id}/events", json=event_payload)
    
    print(f"  -> HTTP Status: {r.status_code}")
    print(f"  -> Response: {r.text}")
    
    if r.status_code == 403:
        print("\nSUCCESS: Action was correctly BLOCKED.")
    else:
        print("\nFAILURE: Action was NOT blocked as expected.")
        sys.exit(1)

if __name__ == "__main__":
    test_blocking_logic()
