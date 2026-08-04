"""
Barebonde Backend - FastAPI main entry point
Landbruksplattform for norske bønder og små landbruksforetak i norge
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import health, farms, accounting, auth, me, subscriptions, profile, onboarding, settings as farm_settings, invitations


app = FastAPI(
    title="Barebonde API",
    description="Regnskapsplattform for landbruksvirksomheter",
    version="0.1.0",
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
app.include_router(me.router, prefix="/api", tags=["Identity"])
app.include_router(profile.router, prefix="/api", tags=["Profile"])
app.include_router(onboarding.router, prefix="/api", tags=["Onboarding"])
app.include_router(farms.router, prefix="/api/farms", tags=["Farms"])
app.include_router(subscriptions.router, prefix="/api", tags=["Subscriptions"])
app.include_router(farm_settings.router, prefix="/api", tags=["Farm settings"])
app.include_router(invitations.router, prefix="/api", tags=["Invitations"])
app.include_router(accounting.router, tags=["Accounting"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Barebonde API",
        "version": "0.1.0",
        "docs": "/docs"
    }
