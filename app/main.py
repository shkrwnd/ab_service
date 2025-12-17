
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import experiments, assignments, events, results

# from starlette.middleware.trustedhost import TrustedHostMiddleware
# from fastapi.responses import RedirectResponse

app = FastAPI(
    title="A/B Testing API",
    description="API for managing experiments, user assignments, and tracking events",
    version="1.0.0"
)

# TODO: lock down origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com"])
# app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(experiments.router)
app.include_router(assignments.router)
app.include_router(events.router)
app.include_router(results.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup (create tables etc)."""
    init_db()
    print("Database initialized")  # TODO: Replace with proper logging
    # await some_async_init()



@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy"}


