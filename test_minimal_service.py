#!/usr/bin/env python3
"""
Minimal test service to isolate deployment issues
"""
from fastapi import FastAPI

app = FastAPI(title="Minimal Test Service")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
