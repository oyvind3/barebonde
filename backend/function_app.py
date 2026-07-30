"""
Azure Functions entry point for Barebonde Backend
Wraps the FastAPI application for Azure Functions runtime
"""

import azure.functions as func
from main import app as fastapi_app

# Create Azure Functions app wrapper
app = func.AsgiRequest(fastapi_app)
