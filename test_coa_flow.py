import requests
import time
import sys
import base64

BASE_URL = "http://127.0.0.1:8000"

def test_coa_workflow():
    print("=== Testing COA & FDA Approval Workflow ===\n")

    # 1. Create Batch
    batch_id = f"BATCH-COA-{int(time.time())}"
    print(f"[1] Creating Batch: {batch_id}")
    
    payload = {
        "batch_id": batch_id,
        "product_gtin": "GTIN-PARA-500", 
        "manufacturer_license": "LIC-ABC-001",
        "mfg_date": "2025-06-01",
        "exp_date": "2027-06-01",
        "batch_size": 10000
    }
    
    try:
        r = requests.post(f"{BASE_URL}/batches/", json=payload)
        if r.status_code == 201:
            data = r.json()
            print(f"    -> Success. Status: {data['current_status']}")
            if data['current_status'] != 'QUARANTINE':
                print(f"    -> FAIL: Expected QUARANTINE, got {data['current_status']}")
                return
        else:
            print(f"    -> FAIL: {r.status_code} - {r.text}")
            return
    except Exception as e:
        print(f"    -> ERROR: {e}")
        return

    # 2. Generate COA
    print(f"\n[2] Generating COA for {batch_id}")
    coa_payload = {
        "batch_id": batch_id,
        "analysis_results": {
            "description": "White Tablet",
            "assay": "99.5%",
            "ph": "6.1"
        },
        "signature_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
        "conclusion": "Complies with USP"
    }

    r = requests.post(f"{BASE_URL}/batches/{batch_id}/coa", json=coa_payload)
    if r.status_code == 201:
        print("    -> Success: COA Generated")
    else:
         print(f"    -> FAIL: {r.status_code} - {r.text}")
         return

    # 3. Check Pending Status (Via FDA View logic - inferred)
    # We can check the batch detail directly via DB or assume it's pending if status didn't change.
    
    # 4. Approve Batch
    print(f"\n[3] Approving Batch (FDA)")
    approval_payload = {"status": "APPROVED", "comments": "Looks good"}
    r = requests.post(f"{BASE_URL}/batches/{batch_id}/approve", json=approval_payload)
    
    if r.status_code == 200:
        print(f"    -> Success: Batch Approved")
    else:
        print(f"    -> FAIL: {r.status_code} - {r.text}")
        return

    # 5. Verify Release Status
    # Re-fetch or check verification endpoint
    print(f"\n[4] Verifying Final Status")
    # Using verify endpoint as proxy
    verify_res = requests.post(f"{BASE_URL}/verify/", json={"batch_id": batch_id})
    v_data = verify_res.json()
    print(f"    -> Verify Endpoint Status: {v_data['status']}")
    
    # Check COA Get
    coa_res = requests.get(f"{BASE_URL}/batches/{batch_id}/coa")
    if coa_res.status_code == 200:
        c_data = coa_res.json()
        print(f"    -> COA Retrieved: {c_data['conclusion']}")
        print(f"    -> Is Released: {c_data['is_released']}")
        
        if c_data['is_released']:
             print("\n=== TEST PASSED: Full Workflow Verified ===")
        else:
             print("\n=== TEST FAILED: Batch not marked as released in COA record ===")

    else:
        print(f"    -> FAIL: Could not retrieve COA {coa_res.status_code}")

if __name__ == "__main__":
    test_coa_workflow()
