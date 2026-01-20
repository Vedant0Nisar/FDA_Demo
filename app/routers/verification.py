from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extras import RealDictCursor
from app.database import get_db
from app.models import VerifyRequest, VerificationResponse
from datetime import datetime

router = APIRouter(
    prefix="/verify",
    tags=["Verification"]
)

@router.post("/", response_model=VerificationResponse)
def verify_product_endpoint(request: VerifyRequest, db: RealDictCursor = Depends(get_db)):
    """
    Scans a product Batch ID to determine if it is Authentic, Counterfeit, or Recalled.
    NOW INCLUDES: Real-time Blockchain Cross-Reference Check.
    """
    try:
        from app.services.verification_service import VerificationService
        
        # 1. Perform Security Check (The "Police" Check)
        security_check = VerificationService.verify_batch_integrity(request.batch_id, db)
        
        if security_check['status'] == "TAMPERED":
             # Immediate Stop
             return VerificationResponse(
                status="TAMPERED",
                message=security_check['message'],
                timestamp=datetime.now()
             )
        
        if security_check['status'] in ["UNKNOWN", "NOT_FOUND"]:
             raise HTTPException(status_code=404, detail=security_check['message'])

        # 2. If Authentic/Warning, get full details from DB (The "Info" Check)
        db.callproc('verify_product', [request.batch_id])
        result = db.fetchone()
        
        if not result:
             # Should be caught by service, but failsafe
             raise HTTPException(status_code=404, detail="Product not found in system.")

        # If Service said WARNING (e.g. not on chain yet), we keep that status
        final_status = security_check['status'] if security_check['status'] != "AUTHENTIC" else result['status']
        # Note: If DB proc says "EXPIRED" but Chain says "AUTHENTIC", we should trust DB for expiration logic 
        # but Chain for data integrity. 
        # Actually, let's allow the DB proc to rule on 'EXPIRED' vs 'VALID' if integrity is good.
        
        return VerificationResponse(
            status=final_status,
            message=result['message'] + f" ({security_check['message']})",
            product_name=result['product_name'],
            exp_date=result['exp_date'],
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise RuntimeError(f"Database error during verification: {e}")
