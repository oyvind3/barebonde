"""
Barebonde Backend - FastAPI main entry point
Landbruksplattform for norske bønder og små landbruksforetak i norge
"""

import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.api.routes import health, farms, accounting, auth, me, subscriptions, profile, onboarding, settings as farm_settings, invitations, customers, sales_invoices
from app.middleware.rate_limiter import setup_rate_limiting


class JSONStringMiddleware(BaseHTTPMiddleware):
    """Middleware to handle JSON sent as string in text/plain content-type.
    
    This is a temporary fix for frontend sending JSON.stringify'd objects
    instead of proper JSON objects.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Only process POST/PUT/PATCH requests with text/plain that contain JSON
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "text/plain" in content_type:
                body = await request.body()
                try:
                    # Try to parse as JSON
                    parsed = json.loads(body.decode("utf-8"))
                    if isinstance(parsed, dict):
                        # Replace the request body with parsed JSON
                        request._body = json.dumps(parsed).encode("utf-8")
                        request.headers._list = [
                            (k.encode(), v.encode()) if isinstance(k, str) else (k, v)
                            for k, v in request.headers.items()
                            if k.lower() != "content-length"
                        ]
                        request.headers._list.append((b"content-type", b"application/json"))
                        request.headers._list.append((b"content-length", str(len(request._body)).encode()))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass  # Not valid JSON, continue as-is
        
        return await call_next(request)


app = FastAPI(
    title="Barebonde API",
    description="Regnskapsplattform for landbruksvirksomheter",
    version="0.1.0",
)

# Handle JSON sent as string workaround - MUST be before CORS
app.add_middleware(JSONStringMiddleware)

# CORS configuration - MUST be after JSONStringMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting - critical for production security
setup_rate_limiting(app)

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
app.include_router(customers.router, prefix="/api", tags=["Customers"])
app.include_router(sales_invoices.router, prefix="/api", tags=["Sales invoices"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Barebonde API",
        "version": "0.1.0",
        "docs": "/docs"
    }
