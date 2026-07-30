#!/bin/bash

# Barebonde Backend - Development server

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run FastAPI development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
