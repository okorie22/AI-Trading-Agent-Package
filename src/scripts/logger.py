import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from datetime import datetime
from src import config

# Convert string level to logging.LEVEL constant
def get_log_level(level_string):
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    return levels.get(level_string.upper(), logging.INFO)

# Get log levels from config
FILE_LOG_LEVEL = get_log_level(config.LOG_LEVEL)
CONSOLE_LOG_LEVEL = get_log_level(config.CONSOLE_LOG_LEVEL)

# Set up logger
logger = logging.getLogger("moon_dev")
logger.setLevel(logging.DEBUG)  # Capture all levels, filters happen at handlers

# Create logs directory if it doesn't exist
if config.LOG_TO_FILE:
    os.makedirs(config.LOG_DIRECTORY, exist_ok=True)
    log_path = os.path.join(config.LOG_DIRECTORY, config.LOG_FILENAME)
    
    # Create file handler for logging to file
    file_handler = RotatingFileHandler(
        log_path, 
        maxBytes=config.LOG_MAX_SIZE_MB * 1024 * 1024,
        backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(FILE_LOG_LEVEL)
    
    # Create formatter and add it to the handler
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Add the handler to the logger
    logger.addHandler(file_handler)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(CONSOLE_LOG_LEVEL)

# Create a simpler formatter for console (no need for logger name)
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)

# Add the handler to the logger
logger.addHandler(console_handler)

# Console output interface (to be set by the UI)
console_output = None

# Set console output reference - called by UI
def set_console_output(output_widget):
    global console_output
    console_output = output_widget
    
# Utility logging functions
def debug(message, console_only=False, file_only=False):
    logger.debug(message)
    if console_output and config.SHOW_DEBUG_IN_CONSOLE and not file_only:
        console_output.append_message(message, "debug")

def info(message, console_only=False, file_only=False):
    logger.info(message)
    if console_output and not file_only:
        console_output.append_message(message, "info")
        
def warning(message, console_only=False, file_only=False):
    logger.warning(message)
    if console_output and not file_only:
        console_output.append_message(message, "warning")
        
def error(message, console_only=False, file_only=False):
    logger.error(message)
    if console_output and not file_only:
        console_output.append_message(message, "error")
        
def critical(message, console_only=False, file_only=False):
    logger.critical(message)
    if console_output and not file_only:
        console_output.append_message(message, "error")

def system(message, console_only=False, file_only=False):
    """Special log for system messages in UI"""
    logger.info(f"[SYSTEM] {message}")
    if console_output and not file_only:
        console_output.append_message(message, "system")

# Helper function for transitioning from print to logging
def log_print(message, level="INFO"):
    """Replacement for print() statements during transition to logging"""
    if level.upper() == "DEBUG":
        debug(message)
    elif level.upper() == "INFO":
        info(message)
    elif level.upper() == "WARNING":
        warning(message)
    elif level.upper() == "ERROR":
        error(message)
    elif level.upper() == "CRITICAL":
        critical(message)
    elif level.upper() == "SYSTEM":
        system(message)
    else:
        info(message)
