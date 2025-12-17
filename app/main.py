"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import experiments, assignments, events, results

# Create FastAPI app
app = FastAPI(
    title="A/B Testing API",
    description="API for managing experiments, user assignments, and tracking events",
    version="1.0.0"
)

# CORS middleware - useful for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(experiments.router)
app.include_router(assignments.router)
app.include_router(events.router)
app.include_router(results.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("Database initialized")  # TODO: Replace with proper logging


@app.get("/")
def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "A/B Testing API is running"}


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy"}

