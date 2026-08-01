"""
Azure Functions entry point for Barebonde Backend
Wraps the FastAPI application for Azure Functions runtime
"""

import azure.functions as func
from main import app as fastapi_app

# Create Azure Functions app wrapper
app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
