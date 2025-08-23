#!/usr/bin/env python3
"""
Simple entry point for Helios AI Agents service.
This follows the standard Cloud Run pattern of having a dedicated entry point.
"""

from helios.server_ai_agents import app

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host='0.0.0.0', port=port)
