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

from app.routers import verification, batches

# ... (Previous imports)

# Include Routers
app.include_router(verification.router)
app.include_router(batches.router)

from fastapi.staticfiles import StaticFiles
import os

# Mount Static Files
static_dir = os.path.join(os.path.dirname(__file__), "../static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Routes ---
@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))

from fastapi.responses import FileResponse
