from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routers import auth, pdf, users

# 1. Create the Database Tables
models.Base.metadata.create_all(bind=engine)

# 2. Initialize the App
app = FastAPI(
    title="PDF Q&A API",
    description="Backend for PDF Q&A RAG Application",
    version="1.0.0"
)

# 3. Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://pdf-qa-azure.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Include Routers
# This brings in all our endpoints from the separate files
app.include_router(auth.router)
app.include_router(pdf.router)
app.include_router(users.router)

# 5. Health Check
@app.get("/", tags=["Health"])
async def health_check():
    from database import SQLALCHEMY_DATABASE_URL
    db_type = "PostgreSQL" if SQLALCHEMY_DATABASE_URL.startswith("postgresql") else "SQLite"
    return {
        "status": "online",
        "message": "PDF Q&A Backend is running successfully!",
        "database": db_type,
        "version": "1.0.1"
    }
