from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import logging

from app.database import lifespan_db

# Configure Logging
logger = logging.getLogger("fda_api")

app = FastAPI(
    title="FDA Traceability API",
    description="Blockchain-enabled Pharmaceutical Tracking & Verification System",
    version="1.0.0",
    lifespan=lifespan_db,
    debug=True
)

# CORS Middleware (Allow all for demo purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Exception Handlers ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()} - Body: {exc.body}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid data format provided.", "errors": exc.errors()},
    )

# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     logger.error(f"Global Exception: {str(exc)}", exc_info=True)
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content={"detail": "An internal server error occurred. Please contact support."},
#     )

from app.routers import verification, batches, mobile, analytics

# ... (Previous imports)

# Include Routers
app.include_router(verification.router)
app.include_router(batches.router)
app.include_router(mobile.router)
app.include_router(analytics.router)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os

# Mount Static Files
static_dir = os.path.join(os.path.dirname(__file__), "../static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Configure Templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

from fastapi import APIRouter, Depends
from app.database import get_db
from psycopg2.extras import RealDictCursor

# --- UI Routes ---

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: RealDictCursor = Depends(get_db)):
    # Fetch stats for Regulator
    db.execute("SELECT COUNT(*) as total FROM batches")
    total_batches = db.fetchone()['total']
    
    # Simple compliance rate (mock or based on events)
    stats = {
        "batches": total_batches,
        "compliance": 98.7,
        "pending": 0,
        "recalls": 0
    }
    return templates.TemplateResponse("dashboard.html", {"request": request, "role": "Regulator", "stats": stats})

@app.get("/manufacturer", response_class=HTMLResponse)
async def manufacturer_ui(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "role": "Manufacturer"})

@app.get("/cnf", response_class=HTMLResponse)
async def cnf_ui(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "role": "C&F Agent"})

@app.get("/distributor", response_class=HTMLResponse)
async def distributor_ui(request: Request, db: RealDictCursor = Depends(get_db)):
    # Fetch batches relevant for distributors
    db.execute("""
        SELECT b.*, p.name as drug_name 
        FROM batches b
        JOIN products p ON b.product_id = p.product_id
        WHERE b.current_status NOT IN ('SOLD_TO_CONSUMER', 'RECEIVED_AT_STORE')
    """)
    batches = db.fetchall()
    return templates.TemplateResponse("dashboard.html", {"request": request, "role": "Distributor", "batches": batches})

@app.get("/fda_cdf", response_class=HTMLResponse)
async def fda_cdf_ui(request: Request, db: RealDictCursor = Depends(get_db)):
    # Fetch all events as an audit log for FDA
    db.execute("""
        SELECT e.*, b.batch_id, u.username
        FROM batch_events e
        JOIN batches b ON e.batch_id = b.batch_id
        LEFT JOIN users u ON e.user_id = u.user_id
        ORDER BY e.timestamp DESC LIMIT 50
    """)
    events = db.fetchall()
    return templates.TemplateResponse("dashboard.html", {"request": request, "role": "FDA CDF", "events": events})

@app.get("/pharmacist", response_class=HTMLResponse)
async def pharmacist_ui(request: Request, db: RealDictCursor = Depends(get_db)):
    from datetime import date
    today = date.today()
    # Fetch mock prescriptions or recent sales
    prescriptions = [
        {"patient": "Sipho", "drug": "Flue-Combo", "batch": "BATCH-5400", "date": "2025-09-13"},
        {"patient": "John Smith", "drug": "Insulin Glargine", "batch": "BATCH-003", "date": "2025-08-02"},
    ]
    # Also fetch batches at store
    db.execute("""
        SELECT b.*, p.name as drug_name 
        FROM batches b
        JOIN products p ON b.product_id = p.product_id
        WHERE b.current_status = 'RECEIVED_AT_STORE'
    """)
    inventory = db.fetchall()
    return templates.TemplateResponse("dashboard.html", {"request": request, "role": "Pharmacist", "prescriptions": prescriptions, "inventory": inventory, "today": today})

@app.get("/verify", response_class=HTMLResponse)
async def verify_ui(request: Request):
    return templates.TemplateResponse("verify.html", {"request": request, "active_page": "verify"})
