import sys
import os
from datetime import date
from fastapi import HTTPException

# Add root to python path to allow imports
sys.path.append(os.getcwd())

from app.database import get_db
from app.routers.mobile import report_fraud, MobileReportRequest
from app.routers.verification import verify_product_endpoint
from app.models import VerifyRequest
from app.services.verification_service import VerificationService

def test_red_flag_protocol():
    print("--- Starting Red Flag Protocol Test ---")
    
    # Get DB Connection
    db_gen = get_db()
    db = next(db_gen)
    
    test_batch_id = "TEST-BATCH-RED-FLAG"
    
    try:
        # 1. Setup: Create a clean test batch
        print(f"\n1. Setting up test batch: {test_batch_id}")
        db.execute("DELETE FROM batch_events WHERE batch_id = %s", (test_batch_id,))
        db.execute("DELETE FROM alerts WHERE batch_id = %s", (test_batch_id,))
        db.execute("DELETE FROM batches WHERE batch_id = %s", (test_batch_id,))
        
        # We need a manufacturer and product to obey constraints, or we just insert minimal data if FKs allow?
        # Looking at schema, batches references products/manufacturers.
        # Let's try to pick an existing one or insert dummies.
        db.execute("SELECT product_id, manufacturer_id FROM products LIMIT 1")
        prod = db.fetchone()
        if not prod:
            print("SKIP: No products found in DB to link batch to.")
            return

        db.execute("""
            INSERT INTO batches (batch_id, product_id, manufacturer_id, mfg_date, exp_date, batch_size, current_status)
            VALUES (%s, %s, %s, CURRENT_DATE, CURRENT_DATE, 100, 'RELEASED')
        """, (test_batch_id, prod['product_id'], prod['manufacturer_id']))
        db.connection.commit()
        print("   Batch created with status 'RELEASED'")

        # 2. Simulate Inspector Reporting Fraud
        print(f"\n2. Inspector reporting fraud on {test_batch_id}...")
        report_req = MobileReportRequest(
            batch_id=test_batch_id,
            node_id="INSPECTOR-DEVICE-001",
            description="Test Fraud Report"
        )
        
        result = report_fraud(report_req, db)
        print(f"   Report Result: {result['message']}")
        
        # Verify DB status
        db.execute("SELECT current_status FROM batches WHERE batch_id = %s", (test_batch_id,))
        status = db.fetchone()['current_status']
        print(f"   DB Status after report: {status}")
        
        if status != 'UNDER_INVESTIGATION':
            print("   FAILED: Status did not update to UNDER_INVESTIGATION")
            return

        # 3. Simulate User Scanning
        print(f"\n3. User scanning {test_batch_id}...")
        verify_req = VerifyRequest(batch_id=test_batch_id, scanned_by="Tester")
        
        try:
            response = verify_product_endpoint(verify_req, db)
            print(f"   Scan Response Status: {response.status}")
            print(f"   Scan Message: {response.message}")
            
            if response.status == "UNDER_INVESTIGATION" and "SECURITY ALERT" in response.message:
                print("\n✅ PASSED: Red Flag Protocol is working correctly.")
            else:
                print(f"\n❌ FAILED: Unexpected response status or message. Got: {response.status}")
                
        except HTTPException as e:
            print(f"   HTTP Exception: {e.detail}")
        except Exception as e:
            print(f"   Unexpected Error during scan: {e}")

    except Exception as e:
        print(f"Test Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\n4. Cleaning up...")
        db.execute("DELETE FROM batch_events WHERE batch_id = %s", (test_batch_id,))
        db.execute("DELETE FROM alerts WHERE batch_id = %s", (test_batch_id,))
        db.execute("DELETE FROM batches WHERE batch_id = %s", (test_batch_id,))
        db.connection.commit()
        print("   Cleanup done.")

if __name__ == "__main__":
    test_red_flag_protocol()
