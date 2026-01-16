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
    """
    try:
        # Call the stored procedure
        # verify_product returns: (status, message, product_name, exp_date)
        db.callproc('verify_product', [request.batch_id])
        result = db.fetchone()
        
        if not result:
             raise HTTPException(status_code=404, detail="Verification process returned no result.")

        # The result from RealDictCursor might look different depending on psycopg2 version
        # verify_product returns a TABLE, so fetchone gives a dict
        
        return VerificationResponse(
            status=result['status'],
            message=result['message'],
            product_name=result['product_name'],
            exp_date=result['exp_date'],
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log will be handled by global handler, but we re-raise for 500
        raise RuntimeError(f"Database error during verification: {e}")
