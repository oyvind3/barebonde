"""
Barebonde Backend - FastAPI main entry point
Landbruksplattform for norske bønder og små landbruksforetak i norge
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import health, farms, accounting, auth
from app.db.cosmos_client import init_cosmos_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print(f"Starting Barebonde API - Environment: {settings.env}")
    print("Initializing Cosmos DB...")
    await init_cosmos_db()
    
    yield
    
    # Shutdown
    print("Shutting down Barebonde API")


app = FastAPI(
    title="Barebonde API",
    description="Regnskapsplattform for landbruksvirksomheter",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(farms.router, prefix="/api/farms", tags=["Farms"])
app.include_router(accounting.router, prefix="/api/accounting", tags=["Accounting"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Barebonde API",
        "version": "0.1.0",
        "docs": "/docs"
    }
