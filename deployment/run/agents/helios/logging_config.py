#!/usr/bin/env python3
"""
Centralized logging configuration for Helios system
Configures both standard Python logging and loguru for structured JSON output
Compatible with Google Cloud Logging for production observability
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

# Configure loguru for structured JSON logging
try:
    from loguru import logger
    
    # Remove default handler
    logger.remove()
    
    # Custom JSON formatter for Cloud Logging compatibility
    def json_formatter(record: Dict[str, Any]) -> str:
        """Format log records as JSON for Cloud Logging"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record["time"].timestamp()).isoformat(),
            "severity": record["level"].name.upper(),
            "message": record["message"],
            "service": "helios",
            "service_type": record.get("extra", {}).get("service_type", "unknown"),
            "trace_id": record.get("extra", {}).get("trace_id"),
            "user_id": record.get("extra", {}).get("user_id"),
            "operation": record.get("extra", {}).get("operation"),
            "duration_ms": record.get("extra", {}).get("duration_ms"),
            "resource_type": record.get("extra", {}).get("resource_type"),
            "resource_id": record.get("extra", {}).get("resource_id"),
            "error_code": record.get("extra", {}).get("error_code"),
            "error_details": record.get("extra", {}).get("error_details"),
            "context": record.get("extra", {}).get("context", {}),
        }
        
        # Add exception info if present
        if record.get("exception"):
            log_entry["exception"] = {
                "type": type(record["exception"]).__name__,
                "message": str(record["exception"]),
                "traceback": record.get("extra", {}).get("traceback")
            }
        
        # Remove None values for cleaner JSON
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        
        return json.dumps(log_entry, ensure_ascii=False)
    
    # Add structured JSON handler for stdout with proper serialization
    logger.add(
        sys.stdout,
        format=json_formatter,
        level="INFO",
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
        catch=True
    )
    
    # Add error handler for stderr with JSON serialization
    logger.add(
        sys.stderr,
        format=json_formatter,
        level="ERROR",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True
    )
    
    # Add Cloud Logging specific sink for production environments
    # This ensures logs are properly formatted for Google Cloud Logging
    def cloud_logging_sink(message):
        """Sink for Cloud Logging integration that ensures proper JSON formatting"""
        try:
            # Parse the message to ensure it's valid JSON
            parsed = json.loads(message)
            # Output to stdout for Cloud Logging to capture
            print(message, flush=True)
        except json.JSONDecodeError:
            # Fallback to raw message if JSON parsing fails
            print(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "severity": "WARNING",
                "message": "Log message could not be parsed as JSON",
                "raw_message": message,
                "service": "helios"
            }), flush=True)
    
    logger.add(
        cloud_logging_sink,
        format=json_formatter,
        level="DEBUG",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        catch=True,
        filter=lambda record: record["level"].no >= logger.level("INFO").no
    )
    
    # Don't intercept standard logging to avoid conflicts with Uvicorn
    # This prevents the KeyError: '"timestamp"' issue
    # Let Uvicorn handle its own logging naturally
    
except ImportError:
    # Fallback to standard logging if loguru is not available
    logger = logging.getLogger(__name__)
    
    # Configure standard logging for JSON output
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "severity": record.levelname,
                "message": record.getMessage(),
                "service": "helios",
                "logger": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            
            if record.exc_info:
                log_entry["exception"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1])
                }
            
            return json.dumps(log_entry, ensure_ascii=False)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Add console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # Add error handler
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)

def get_logger(name: str = None):
    """Get a logger instance with structured logging capabilities"""
    if name:
        return logger.bind(logger_name=name)
    return logger

def log_with_context(logger_instance, level: str, message: str, **context):
    """Log a message with structured context"""
    logger_instance.bind(**context).log(level, message)

def log_error(logger_instance, message: str, error: Exception = None, **context):
    """Log an error with structured context and exception details"""
    if error:
        context.update({
            "error_code": type(error).__name__,
            "error_details": str(error),
            "traceback": getattr(error, '__traceback__', None)
        })
    
    logger_instance.bind(**context).error(message)

# Export the configured logger
__all__ = ['logger', 'get_logger', 'log_with_context', 'log_error']
