from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from fastapi.encoders import jsonable_encoder
from psycopg2.extras import RealDictCursor
from app.database import get_db
from app.models import BatchCreateRequest, BatchResponse, BatchEventRequest, COACreateRequest, FDAApprovalRequest
from app.services.blockchain import BlockchainService
from app.services.coa_service import COAService
import logging

router = APIRouter(
    prefix="/batches",
    tags=["Batches"]
)

logger = logging.getLogger(__name__)

@router.post("/", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(request: BatchCreateRequest, db: RealDictCursor = Depends(get_db)):
    try:
        with open("debug_log.txt", "a") as f:
            f.write(f"\\n[{datetime.now()}] Request Received: {request.batch_id}\\n")
            f.flush()
        
        # 1. Resolve IDs
        with open("debug_log.txt", "a") as f: f.write("DEBUG: Checking Manufacturer\\n"); f.flush()
        # Check Manufacturer
        db.execute("SELECT manufacturer_id, name FROM manufacturers WHERE license_number = %s", (request.manufacturer_license,))
        mfg = db.fetchone()
        if not mfg:
            with open("debug_log.txt", "a") as f: f.write("DEBUG: Manufacturer not found\\n"); f.flush()
            raise HTTPException(status_code=404, detail=f"Manufacturer with license '{request.manufacturer_license}' not found.")
        
        with open("debug_log.txt", "a") as f: f.write(f"DEBUG: Found Mfg: {mfg}\\n"); f.flush()
        
        # Check Product (Must belong to Manufacturer)
        db.execute("""
            SELECT product_id FROM products 
            WHERE gtin = %s AND manufacturer_id = %s
        """, (request.product_gtin, mfg['manufacturer_id']))
        prod = db.fetchone()
        if not prod:
            with open("debug_log.txt", "a") as f: f.write("DEBUG: Product not found\\n"); f.flush()
            raise HTTPException(status_code=404, detail=f"Product with GTIN '{request.product_gtin}' not registered for this manufacturer.")

        with open("debug_log.txt", "a") as f: f.write(f"DEBUG: Found Product: {prod}\\n"); f.flush()

        # 2. Check Duplicate
        db.execute("SELECT 1 FROM batches WHERE batch_id = %s", (request.batch_id,))
        if db.fetchone():
            with open("debug_log.txt", "a") as f: f.write("DEBUG: Duplicate Batch\\n"); f.flush()
            raise HTTPException(status_code=409, detail=f"Batch ID '{request.batch_id}' already exists.")

        # 3. Generate QR Code
        import qrcode
        import io
        import base64
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(request.batch_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 4. Register on Blockchain
        logger.info(f"Batch {request.batch_id} created. Registering on Blockchain...")
        details = [
            f"MFG:{request.mfg_date}", 
            f"EXP:{request.exp_date}", 
            f"SIZE:{request.batch_size}",
            f"LIC:{request.manufacturer_license}",
            f"OP:{request.operator_name or 'Unknown'}"
        ]
        tx_hash = BlockchainService.register_product(request.batch_id, f"GTIN-{request.product_gtin}", details)

        # 5. Insert into Database
        with open("debug_log.txt", "a") as f: f.write("DEBUG: Inserting Batch\\n"); f.flush()
        db.execute("""
            INSERT INTO batches (batch_id, product_id, manufacturer_id, mfg_date, exp_date, batch_size, current_status, fda_approval_status)
            VALUES (%s, %s, %s, %s, %s, %s, 'QUARANTINE', 'PENDING')
        """, (request.batch_id, prod['product_id'], mfg['manufacturer_id'], request.mfg_date, request.exp_date, request.batch_size))

        # 6. Log Genesis Event
        metadata = {
            "blockchain_hash": tx_hash, 
            "description": "Initial Batch Creation",
            "operator_name": request.operator_name,
            "location": request.location.dict() if request.location else None
        }
        
        SYSTEM_USER_ID = 1 
        SYSTEM_DEPT_ID = 1 

        from psycopg2.extras import Json
        with open("debug_log.txt", "a") as f: f.write("DEBUG: Logging Event\\n"); f.flush()
        
        # Check if column blockchain_tx_id exists, otherwise put in metadata
        try:
            db.execute("""
                INSERT INTO batch_events (batch_id, user_id, department_id, action_type, description, metadata, blockchain_tx_id)
                VALUES (%s, %s, %s, 'PRODUCED', 'Batch Created and Registered', %s, %s)
            """, (request.batch_id, SYSTEM_USER_ID, SYSTEM_DEPT_ID, Json(metadata), tx_hash))
        except Exception:
            # Fallback if specific column doesn't exist yet (though we should assume it does from recent updates)
             db.execute("""
                INSERT INTO batch_events (batch_id, user_id, department_id, action_type, description, metadata)
                VALUES (%s, %s, %s, 'PRODUCED', 'Batch Created and Registered', %s)
            """, (request.batch_id, SYSTEM_USER_ID, SYSTEM_DEPT_ID, Json(metadata)))
        
        return BatchResponse(
            batch_id=request.batch_id,
            current_status='QUARANTINE',
            hash=tx_hash,
            qr_code_base64=qr_base64
        )

    except Exception as e:
        with open("debug_log.txt", "a") as f:
            f.write(f"\\nCRITICAL ERROR: {e}\\n")
            import traceback
            traceback.print_exc(file=f)
            f.flush()
        raise e


@router.post("/{batch_id}/events", status_code=status.HTTP_201_CREATED)
def add_batch_event(batch_id: str, event: BatchEventRequest, db: RealDictCursor = Depends(get_db)):
    # 1. Check if Batch Exists
    db.execute("SELECT batch_id, current_status FROM batches WHERE batch_id = %s", (batch_id,))
    batch = db.fetchone()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # 1.1 Check Blocked Statuses
    blocked_statuses = ['QUARANTINE', 'UNDER_INVESTIGATION', 'REJECTED', 'RECALLED']
    if batch['current_status'] in blocked_statuses:
        # Check if the user is an FDA Admin trying to resolve it? (Future enhancement)
        # For now, strict block.
        raise HTTPException(
            status_code=403, 
            detail=f"Action Blocked: Batch is currently {batch['current_status']}. Please contact FDA/Compliance."
        )
        
    # 1.5 Security Integrity Check (Fail-Closed)
    from app.services.verification_service import VerificationService
    integrity = VerificationService.verify_batch_integrity(batch_id, db)
    if integrity['status'] == 'TAMPERED':
        raise HTTPException(status_code=403, detail=f"SECURITY ALERT: Batch is TAMPERED. Action blocked. {integrity['message']}")
    if integrity['status'] == 'UNKNOWN':
        # Depending on policy, we might allow manual override or block. strict = block.
        raise HTTPException(status_code=503, detail="Blockchain verification unavailable. Cannot proceed safely.")

    # 2. Log Event
    from psycopg2.extras import Json
    metadata = {
        "location": event.location.dict() if event.location else None,
        "description": event.description,
        "vehicle_id": event.vehicle_id,
        "ingress": event.ingress_quality,
        "egress": event.egress_quality,
        "notes": event.notes,
        "quantity": event.quantity,
        "operator_id": event.operator_id,
        "operator_name": event.operator_name
    }

    # Log to Real Blockchain
    timestamp = str(datetime.now())
    qty = event.quantity if event.quantity is not None else 0
    
    # Define Logic based on Role/Action
    if 'DISTRIBUTOR' in event.action_type:
        # Distributor Specific Logic
        # We map incoming fields to Distributor Contract args
        # (Assuming notes contain DistID, or we add fields to Model later. Using placeholders for now)
        tx_hash = BlockchainService.log_distributor(
            batch_id, 
            "DIST-001", # Placeholder Dist ID
            "1000",     # Capacity
            "500",      # Stock
            event.ingress_quality or "Fair",
            event.egress_quality or "Fair",
            event.notes or "No Doubt",
            qty
        )
    elif 'RETAILER' in event.action_type:
        # Retailer Specific Logic
        tx_hash = BlockchainService.log_retailer(
            batch_id,
            "RET-001",
            "Pharmacy",
            "City Chemist",
            qty,
            "Mr. Owner",
            "9999999999",
            str(datetime.now().date())
        )
    else:
        # General Movement (C&F, Shipping)
        tx_hash = BlockchainService.log_movement(
            batch_id, 
            event.ingress_quality or "N/A", 
            event.egress_quality or "N/A", 
            timestamp,
            qty
        )
    
    metadata['hash'] = tx_hash

    try:
        db.execute("""
            INSERT INTO batch_events (batch_id, user_id, department_id, action_type, description, metadata, blockchain_tx_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (batch_id, event.user_id, event.department_id, event.action_type, event.description, Json(metadata), tx_hash))
        
        # 3. Update Batch Status
        db.execute("UPDATE batches SET current_status = %s WHERE batch_id = %s", (event.action_type, batch_id))
        
        return {"status": "Event Logged", "current_status": event.action_type, "hash": tx_hash}
    except Exception as e:
        logger.error(f"Failed to log event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{batch_id}/timeline")
def get_batch_timeline(batch_id: str, db: RealDictCursor = Depends(get_db)):
    """
    Fetch the complete history of a batch.
    """
    db.execute("""
        SELECT event_id, action_type, description, timestamp, u.username, d.name as department, blockchain_tx_id, metadata
        FROM batch_events e
        LEFT JOIN users u ON e.user_id = u.user_id
        LEFT JOIN departments d ON e.department_id = d.department_id
        WHERE batch_id = %s
        ORDER BY timestamp ASC
    """, (batch_id,))
    events = db.fetchall()
    
    if not events:
        raise HTTPException(status_code=404, detail="Batch not found or no events logged.")
        
    return {"batch_id": batch_id, "events": events}

@router.post("/{batch_id}/coa", status_code=status.HTTP_201_CREATED)
def create_coa(batch_id: str, request: COACreateRequest, db: RealDictCursor = Depends(get_db)):
    try:
        # Verify batch exists and is in QUARANTINE (or Created, but we moved to Quarantine)
        db.execute("SELECT current_status FROM batches WHERE batch_id = %s", (batch_id,))
        batch = db.fetchone()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
            
        COAService.create_coa(batch_id, request.dict(), db)
        return {"status": "COA Generated", "batch_id": batch_id}
    except Exception as e:
        with open("debug_log.txt", "a") as f:
            f.write(f"\n[COA ERROR] {str(e)}\n")
            import traceback
            traceback.print_exc(file=f)
        raise e

@router.post("/{batch_id}/approve")
def approve_batch(batch_id: str, request: FDAApprovalRequest, db: RealDictCursor = Depends(get_db)):
    COAService.update_approval_status(batch_id, request.status, db)
    return {"status": "Updated", "approval_status": request.status}

@router.get("/{batch_id}/coa")
def get_coa_details(batch_id: str, db: RealDictCursor = Depends(get_db)):
    coa = COAService.get_coa(batch_id, db)
    if not coa:
        raise HTTPException(status_code=404, detail="COA not pending or found for this batch")
    return coa
