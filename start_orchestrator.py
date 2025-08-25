#!/usr/bin/env python3
"""
Entry point for Helios Orchestrator Service with proper error handling
"""
import sys
import os
import logging
import traceback

# Configure logging BEFORE any imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point with comprehensive error handling"""
    try:
        logger.info("Starting Helios Orchestrator Service...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Python path: {sys.path}")
        
        # Add the workspace to Python path
        workspace_path = os.path.dirname(os.path.abspath(__file__))
        if workspace_path not in sys.path:
            sys.path.insert(0, workspace_path)
            logger.info(f"Added {workspace_path} to Python path")
        
        # Now try to import
        try:
            from helios.server_orchestrator import app
            logger.info("Successfully imported orchestrator app")
        except ImportError as e:
            logger.error(f"Failed to import orchestrator app: {e}")
            logger.error(f"Import error details: {traceback.format_exc()}")
            
            # Try alternative import
            logger.info("Attempting alternative import method...")
            import helios.server_orchestrator
            app = helios.server_orchestrator.app
            logger.info("Alternative import successful")
        
        # Import uvicorn
        try:
            import uvicorn
            logger.info("Successfully imported uvicorn")
        except ImportError as e:
            logger.error(f"Failed to import uvicorn: {e}")
            raise
        
        # Get port from environment
        port = int(os.environ.get("PORT", 8080))
        logger.info(f"Starting server on port {port}")
        
        # Run the app
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True,
            use_colors=False  # Disable colors for cloud logging
        )
        
    except Exception as e:
        logger.error(f"Fatal error starting orchestrator: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()