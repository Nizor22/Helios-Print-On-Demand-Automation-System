#!/usr/bin/env python3
"""
Centralized logging configuration for Helios system
Configures structured JSON logging compatible with Google Cloud Logging
Ensures all log levels include meaningful content
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

class StructuredJSONFormatter(logging.Formatter):
    """JSON formatter for structured logging compatible with Google Cloud Logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log entry with required fields
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
            "service": "helios",
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from record.extra (this is the key fix!)
        if hasattr(record, 'extra') and record.extra:
            log_entry.update(record.extra)
        
        # Add custom attributes that might be set on the logger
        if hasattr(record, 'service_type'):
            log_entry["service_type"] = record.service_type
        if hasattr(record, 'trace_id'):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'operation'):
            log_entry["operation"] = record.operation
        if hasattr(record, 'duration_ms'):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, 'resource_type'):
            log_entry["resource_type"] = record.resource_type
        if hasattr(record, 'resource_id'):
            log_entry["resource_id"] = record.resource_id
        if hasattr(record, 'error_code'):
            log_entry["error_code"] = record.error_code
        if hasattr(record, 'error_details'):
            log_entry["error_details"] = record.error_details
        if hasattr(record, 'context'):
            log_entry["context"] = record.context
        
        # Remove None values for cleaner JSON
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)

def setup_logging(service_name: str = "helios", log_level: str = "INFO") -> logging.Logger:
    """Setup structured logging for the service"""
    
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = StructuredJSONFormatter()
    
    # Console handler (stdout) for all levels
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    # Error handler (stderr) for errors only
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)
    
    # Set propagate to False to prevent duplicate logs
    logger.propagate = False
    
    return logger

def get_logger(name: str = None, service_type: str = None) -> logging.Logger:
    """Get a configured logger instance with structured logging capabilities"""
    
    if name is None:
        name = "helios"
    
    logger = setup_logging(name)
    
    # Add custom attributes for structured logging
    if service_type:
        logger.service_type = service_type
    
    return logger

def log_with_context(logger_instance: logging.Logger, level: str, message: str, **context):
    """Log a message with structured context"""
    
    # Create a log record with extra context
    extra = {}
    for key, value in context.items():
        if hasattr(logger_instance, key):
            setattr(logger_instance, key, value)
        extra[key] = value
    
    # Log with extra context
    if level.upper() == "DEBUG":
        logger_instance.debug(message, extra=extra)
    elif level.upper() == "INFO":
        logger_instance.info(message, extra=extra)
    elif level.upper() == "WARNING":
        logger_instance.warning(message, extra=extra)
    elif level.upper() == "ERROR":
        logger_instance.error(message, extra=extra)
    elif level.upper() == "CRITICAL":
        logger_instance.critical(message, extra=extra)
    else:
        logger_instance.info(message, extra=extra)

def log_error(logger_instance: logging.Logger, message: str, error: Exception = None, **context):
    """Log an error with structured context and exception details"""
    
    if error:
        context.update({
            "error_code": type(error).__name__,
            "error_details": str(error),
            "error_type": "exception"
        })
    
    log_with_context(logger_instance, "ERROR", message, **context)

# Initialize default logger
default_logger = setup_logging("helios", "INFO")

# Export the configured logger and functions
__all__ = ['default_logger', 'get_logger', 'log_with_context', 'log_error', 'setup_logging']
