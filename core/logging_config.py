# core/logging_config.py

import os
import logging
import logging.handlers
from datetime import datetime

def setup_logging(log_level=logging.INFO, log_dir="logs"):
    """
    Set up comprehensive logging configuration with file output and rotation.
    
    Args:
        log_level: Logging level (default: INFO)
        log_dir: Directory to store log files (default: "logs")
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with simple format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Main application log file with rotation
    app_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    app_handler.setLevel(log_level)
    app_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_handler)
    
    # Error log file for errors and above
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'error.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Cache operations log
    cache_logger = logging.getLogger('cache')
    cache_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'cache.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=2,
        encoding='utf-8'
    )
    cache_handler.setLevel(logging.DEBUG)
    cache_handler.setFormatter(detailed_formatter)
    cache_logger.addHandler(cache_handler)
    cache_logger.setLevel(logging.DEBUG)
    cache_logger.propagate = False  # Don't send to root logger
    
    # Error recovery log
    error_recovery_logger = logging.getLogger('error_recovery')
    error_recovery_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'error_recovery.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_recovery_handler.setLevel(logging.DEBUG)
    error_recovery_handler.setFormatter(detailed_formatter)
    error_recovery_logger.addHandler(error_recovery_handler)
    error_recovery_logger.setLevel(logging.DEBUG)
    error_recovery_logger.propagate = True  # Also send to root logger
    
    # WebSocket log
    websocket_logger = logging.getLogger('websocket')
    websocket_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'websocket.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=2,
        encoding='utf-8'
    )
    websocket_handler.setLevel(logging.DEBUG)
    websocket_handler.setFormatter(detailed_formatter)
    websocket_logger.addHandler(websocket_handler)
    websocket_logger.setLevel(logging.DEBUG)
    websocket_logger.propagate = False  # Don't send to root logger
    
    # API calls log (for tool usage)
    api_logger = logging.getLogger('api_calls')
    api_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'api_calls.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(detailed_formatter)
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)
    api_logger.propagate = False  # Don't send to root logger
    
    # Log the logging setup
    logging.info(f"Logging configured - Level: {logging.getLevelName(log_level)}, Directory: {log_dir}")
    logging.info(f"Log files: app.log, error.log, cache.log, error_recovery.log, websocket.log, api_calls.log")
    
    return {
        'app': root_logger,
        'cache': cache_logger,
        'error_recovery': error_recovery_logger,
        'websocket': websocket_logger,
        'api_calls': api_logger
    }

def get_logger(name):
    """Get a logger with the specified name."""
    return logging.getLogger(name)