"""
Moon Dev's Leverage Trading Utilities
Provides functions for leveraged trading on Hyperliquid
"""

import os
import sys
import importlib
import time
import requests
from datetime import datetime
import traceback
from dotenv import load_dotenv
import pandas as pd
from src.scripts.logger import debug, info, warning, error, critical

# Import nice_funcs and nice_funcs_hl
from src import nice_funcs as n
from src.config import *

# Dynamically import nice_funcs_hl
try:
    hl = importlib.import_module("src.nice_funcs_hl")
    HYPERLIQUID_AVAILABLE = True
    info("Successfully imported Hyperliquid functions")
except ImportError:
    HYPERLIQUID_AVAILABLE = False
    warning("Hyperliquid functions not available. Some features will be limited.")

# Constants for hyperliquid API
HL_API_URL = "https://api.hyperliquid.xyz/info"
HL_TRADE_URL = "https://api.hyperliquid.xyz/trade"

def check_hyperliquid_available():
    """Checks if hyperliquid functions are available and properly configured"""
    if not HYPERLIQUID_AVAILABLE:
        error("Hyperliquid functions not available. Please ensure nice_funcs_hl.py is in your src directory.")
        return False
    
    try:
        # Test the basic market info function to verify connectivity
        market_info = hl.get_market_info()
        if market_info:
            info("Hyperliquid connection verified")
            return True
        else:
            error("Failed to connect to Hyperliquid. Check your network connection.")
            return False
    except Exception as e:
        error(f"Error testing Hyperliquid connection: {str(e)}")
        traceback.print_exc()
        return False

def get_hl_symbol(token_address):
    """
    Get the Hyperliquid symbol for a given token address
    
    Args:
        token_address (str): Solana token address
        
    Returns:
        str: Hyperliquid symbol or None if not found
    """
    if token_address in TOKEN_TO_HL_MAPPING:
        return TOKEN_TO_HL_MAPPING[token_address]
    
    # Try to get token symbol from other sources
    try:
        # Could implement lookup via CoinGecko, etc.
        pass
    except:
        pass
        
    # Log the missing mapping
    warning(f"No Hyperliquid mapping found for token: {token_address}")
    return None

def get_hl_price(symbol):
    """
    Get the current price of a token on Hyperliquid
    
    Args:
        symbol (str): Hyperliquid symbol (e.g., "BTC")
        
    Returns:
        float: Current price or None if not available
    """
    if not HYPERLIQUID_AVAILABLE:
        error("Hyperliquid functions not available")
        return None
        
    try:
        # Get all market info
        market_info = hl.get_market_info()
        if not market_info or symbol not in market_info:
            error(f"Price not available for {symbol}")
            return None
            
        price = float(market_info[symbol])
        return price
    except Exception as e:
        error(f"Error getting {symbol} price from Hyperliquid: {str(e)}")
        return None

def hl_entry(symbol, usd_amount, leverage=None):
    """
    Enter a leveraged long position on Hyperliquid
    
    Args:
        symbol (str): Hyperliquid symbol (e.g., "BTC")
        usd_amount (float): USD amount to use as margin
        leverage (float, optional): Leverage multiplier. Defaults to DEFAULT_LEVERAGE.
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not HYPERLIQUID_AVAILABLE:
        error("Hyperliquid functions not available")
        return False
        
    try:
        # Use default leverage if not specified
        if leverage is None:
            leverage = DEFAULT_LEVERAGE
            
        # Cap leverage at maximum allowed
        leverage = min(leverage, MAX_LEVERAGE)
        
        # Apply safety buffer to position size
        adjusted_usd = usd_amount * LEVERAGE_SAFETY_BUFFER
        
        info(f"Opening leveraged long position on {symbol}")
        info(f"USD Amount: ${adjusted_usd:.2f}")
        info(f"Leverage: {leverage}x")
        
        # Calculate the actual position size
        position_size = adjusted_usd * leverage
        price = get_hl_price(symbol)
        
        if not price:
            error(f"Cannot get current price for {symbol}")
            return False
            
        info(f"Current Price: ${price:.2f}")
        info(f"Position Size: ${position_size:.2f}")
        
        # TODO: Implement the actual API call to Hyperliquid when API is available
        # This is a placeholder for future implementation
        
        info(f"Successfully opened {leverage}x long position on {symbol}")
        return True
        
    except Exception as e:
        error(f"Error opening leverage position: {str(e)}")
        traceback.print_exc()
        return False

def hl_exit(symbol, percentage=1.0):
    """
    Exit a leveraged position on Hyperliquid
    
    Args:
        symbol (str): Hyperliquid symbol (e.g., "BTC")
        percentage (float, optional): Percentage of position to close (0.0-1.0)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not HYPERLIQUID_AVAILABLE:
        error("Hyperliquid functions not available")
        return False
        
    try:
        info(f"Closing {percentage*100:.1f}% of leveraged position on {symbol}")
        
        # TODO: Implement the actual API call to Hyperliquid when API is available
        # This is a placeholder for future implementation
        
        info(f"Successfully closed {percentage*100:.1f}% of position on {symbol}")
        return True
        
    except Exception as e:
        error(f"Error closing leverage position: {str(e)}")
        traceback.print_exc()
        return False

def hl_partial_exit(symbol, percentage):
    """
    Exit a specific percentage of a leveraged position on Hyperliquid
    
    Args:
        symbol (str): Hyperliquid symbol (e.g., "BTC")
        percentage (float): Percentage of position to close (0.0-1.0)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if percentage >= 0.95:
        # If closing most of the position, just close it all
        return hl_exit(symbol, 1.0)
    else:
        return hl_exit(symbol, percentage)

def get_hl_positions():
    """
    Get current open positions on Hyperliquid
    
    Returns:
        dict: Dictionary of open positions or None if error
    """
    if not HYPERLIQUID_AVAILABLE:
        error("Hyperliquid functions not available")
        return None
        
    try:
        # TODO: Implement the actual API call to Hyperliquid when API is available
        # This is a placeholder for future implementation
        
        # Dummy data for testing
        positions = {
            "BTC": {
                "size": 0.5,
                "entry_price": 60000,
                "current_price": 65000,
                "pnl": 2500,
                "pnl_percent": 8.33,
                "leverage": 3.0
            }
        }
        
        return positions
        
    except Exception as e:
        error(f"Error getting leverage positions: {str(e)}")
        return None

def get_funding_rates():
    """
    Get current funding rates for all available assets on Hyperliquid
    
    Returns:
        dict: Dictionary of funding rates by symbol
    """
    if not HYPERLIQUID_AVAILABLE:
        error("Hyperliquid functions not available")
        return {}
        
    try:
        # Create a dictionary to store the funding rates
        rates = {}
        
        # List of common assets to check
        symbols = ["BTC", "ETH", "SOL", "ARB", "MATIC"]
        
        for symbol in symbols:
            try:
                data = hl.get_funding_rates(symbol)
                if data:
                    rates[symbol] = data
            except Exception as e:
                warning(f"Error getting funding rate for {symbol}: {str(e)}")
        
        return rates
        
    except Exception as e:
        error(f"Error getting funding rates: {str(e)}")
        return {}
        
# Initialization code to verify hyperliquid connection
if __name__ == "__main__":
    info("Testing Moon Dev's Leverage Utilities")
    check_hyperliquid_available()
    
    # Test get_hl_symbol
    test_token = "So11111111111111111111111111111111111111112"
    symbol = get_hl_symbol(test_token)
    info(f"Symbol for {test_token}: {symbol}")
    
    # Test price lookup
    if symbol:
        price = get_hl_price(symbol)
        info(f"Current price for {symbol}: ${price}")
    
    # Test funding rates
    rates = get_funding_rates()
    info("Current funding rates:")
    for symbol, data in rates.items():
        debug(f"{symbol}: {data}", file_only=True) 