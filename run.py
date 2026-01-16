import uvicorn
import os

if __name__ == "__main__":
    print("🚀 Starting PharmTrace Drug Traceability System...")
    print("🔗 URL: http://127.0.0.1:8000")
    
    # Run the FastAPI app
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
