from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date, datetime

# --- Shared ---
class GeoLocation(BaseModel):
    lat: float
    long: float

# --- Requests ---
class BatchCreateRequest(BaseModel):
    batch_id: str = Field(..., description="Unique Batch Identifier, e.g., BATCH-001")
    product_gtin: str = Field(..., description="Global Trade Item Number of the product")
    manufacturer_license: str = Field(..., description="License number of the manufacturer")
    mfg_date: date
    exp_date: date
    batch_size: int
    
class VerifyRequest(BaseModel):
    batch_id: str
    location: Optional[GeoLocation] = None
    scanned_by: str = "Unknown"

class BatchEventRequest(BaseModel):
    action_type: str = Field(..., description="Type of action: SHIPPED, RECEIVED, SOLD, etc.")
    description: str = Field(..., description="Human readable description")
    location: Optional[GeoLocation] = None
    user_id: int = Field(1, description="ID of the user performing the action")
    department_id: int = Field(1, description="ID of the department")
    
    # Logistics Details
    vehicle_id: Optional[str] = None
    ingress_quality: Optional[str] = None
    egress_quality: Optional[str] = None
    temperature: Optional[str] = None
    notes: Optional[str] = None


# --- Responses ---
class VerificationResponse(BaseModel):
    status: str # AUTHENTIC, COUNTERFEIT, WARNING
    message: str
    product_name: Optional[str] = None
    exp_date: Optional[date] = None
    timestamp: datetime

class BatchResponse(BaseModel):
    batch_id: str
    current_status: str
    hash: Optional[str] = None
    qr_code_base64: Optional[str] = None
