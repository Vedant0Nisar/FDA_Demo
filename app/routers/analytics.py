from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from app.database import get_db
from app.services.analytics import AnalyticsService

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics & Traceability"]
)

@router.get("/trace/{batch_id}")
def get_batch_trace_tree(batch_id: str, db: RealDictCursor = Depends(get_db)):
    """
    Returns a hierarchical tree of the batch's journey, 
    calculating stock at every node (Manufacturer -> C&F -> Distributor -> Pharmacy).
    """
    tree = AnalyticsService.build_supply_chain_tree(batch_id, db)
    
    if not tree:
        raise HTTPException(status_code=404, detail="Batch not found")
        
    # Run Integrity Check
    integrity_errors = AnalyticsService.check_conservation_of_mass(tree)
    
    return {
        "batch_id": batch_id,
        "tree": tree,
        "integrity_status": "Valid" if not integrity_errors else "Integrity Violation",
        "alerts": integrity_errors
    }
