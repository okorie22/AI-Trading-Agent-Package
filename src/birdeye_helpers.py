"""
BirdEye API Helper Functions
Provides functions for interacting with the BirdEye API for token price and metadata
"""

import os
import requests
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv
from src.scripts.logger import debug, info, warning, error

# Load environment variables
load_dotenv()

# Get API key from .env
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
API_TIMEOUT = 10  # seconds
API_RETRY_DELAY = 1  # seconds
MAX_RETRIES = 3

# Cache to minimize repeated API calls
TOKEN_PRICE_CACHE = {}
TOKEN_METADATA_CACHE = {}
CACHE_EXPIRY = 300  # seconds (5 minutes)

def _get_cached_data(cache: Dict, key: str) -> Tuple[bool, Any]:
    """Check if we have valid cached data for the given key"""
    if key in cache:
        timestamp, data = cache[key]
        if time.time() - timestamp < CACHE_EXPIRY:
            return True, data
    return False, None

def _add_to_cache(cache: Dict, key: str, data: Any) -> None:
    """Add data to cache with current timestamp"""
    cache[key] = (time.time(), data)

def clear_cache() -> None:
    """Clear the token price and metadata caches"""
    global TOKEN_PRICE_CACHE, TOKEN_METADATA_CACHE
    TOKEN_PRICE_CACHE = {}
    TOKEN_METADATA_CACHE = {}
    debug("BirdEye API cache cleared")

def is_api_available() -> bool:
    """Check if the BirdEye API is available with the current key"""
    if not BIRDEYE_API_KEY:
        warning("No BirdEye API key found in environment variables")
        return False
    
    try:
        # Simple test request - get top token by volume
        url = "https://public-api.birdeye.so/public/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=1"
        headers = {"X-API-KEY": BIRDEYE_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                return True
    except Exception as e:
        error(f"Error checking BirdEye API availability: {str(e)}")
    
    return False

def get_token_price(token_address: str, force_refresh: bool = False) -> Optional[float]:
    """
    Get token price from BirdEye API with caching
    
    Args:
        token_address: The token mint address
        force_refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Float price or None if not available
    """
    # Check cache if not forcing refresh
    if not force_refresh:
        has_cache, cached_price = _get_cached_data(TOKEN_PRICE_CACHE, token_address)
        if has_cache:
            debug(f"Using cached price for {token_address[:6]}...")
            return cached_price
    
    # If no API key, return None early
    if not BIRDEYE_API_KEY:
        warning("Cannot fetch token price: No BirdEye API key available")
        return None
    
    debug(f"Fetching price from BirdEye API for {token_address[:6]}...")
    
    for attempt in range(MAX_RETRIES):
        try:
            url = f"https://public-api.birdeye.so/public/price?address={token_address}"
            headers = {"X-API-KEY": BIRDEYE_API_KEY}
            
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    price = data.get("data", {}).get("value", 0)
                    if price:
                        # Cache the result
                        _add_to_cache(TOKEN_PRICE_CACHE, token_address, price)
                        return float(price)
                else:
                    msg = data.get("message", "Unknown error")
                    warning(f"BirdEye API error fetching price: {msg}")
            else:
                warning(f"BirdEye API HTTP error: {response.status_code}")
                
                # If rate limited, wait longer before retry
                if response.status_code == 429:
                    time.sleep(API_RETRY_DELAY * 3)
                    continue
            
            # For other errors, wait standard delay
            time.sleep(API_RETRY_DELAY)
            
        except Exception as e:
            error(f"Exception fetching token price: {str(e)}")
            time.sleep(API_RETRY_DELAY)
    
    # If we get here, all retries failed
    warning(f"Failed to fetch price for {token_address} after {MAX_RETRIES} attempts")
    return None

def get_token_metadata(token_address: str, force_refresh: bool = False) -> Optional[Dict]:
    """
    Get token metadata from BirdEye API with caching
    
    Args:
        token_address: The token mint address
        force_refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Dictionary with token metadata or None if not available
    """
    # Check cache if not forcing refresh
    if not force_refresh:
        has_cache, cached_metadata = _get_cached_data(TOKEN_METADATA_CACHE, token_address)
        if has_cache:
            debug(f"Using cached metadata for {token_address[:6]}...")
            return cached_metadata
    
    # If no API key, return None early
    if not BIRDEYE_API_KEY:
        warning("Cannot fetch token metadata: No BirdEye API key available")
        return None
    
    debug(f"Fetching metadata from BirdEye API for {token_address[:6]}...")
    
    for attempt in range(MAX_RETRIES):
        try:
            url = f"https://public-api.birdeye.so/public/tokenlist?address={token_address}"
            headers = {"X-API-KEY": BIRDEYE_API_KEY}
            
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False) and data.get("data"):
                    metadata = data.get("data", {})
                    # Cache the result
                    _add_to_cache(TOKEN_METADATA_CACHE, token_address, metadata)
                    return metadata
                else:
                    msg = data.get("message", "Unknown error") 
                    warning(f"BirdEye API error fetching metadata: {msg}")
            else:
                warning(f"BirdEye API HTTP error: {response.status_code}")
                
                # If rate limited, wait longer before retry
                if response.status_code == 429:
                    time.sleep(API_RETRY_DELAY * 3)
                    continue
            
            # For other errors, wait standard delay
            time.sleep(API_RETRY_DELAY)
            
        except Exception as e:
            error(f"Exception fetching token metadata: {str(e)}")
            time.sleep(API_RETRY_DELAY)
    
    # If we get here, all retries failed
    warning(f"Failed to fetch metadata for {token_address} after {MAX_RETRIES} attempts")
    return None

def get_token_markets(token_address: str) -> Optional[Dict]:
    """
    Get token market information from BirdEye API
    
    Args:
        token_address: The token mint address
        
    Returns:
        Dictionary with market information or None if not available
    """
    # No caching for market data as it changes frequently
    
    # If no API key, return None early
    if not BIRDEYE_API_KEY:
        warning("Cannot fetch token markets: No BirdEye API key available")
        return None
    
    debug(f"Fetching market data from BirdEye API for {token_address[:6]}...")
    
    for attempt in range(MAX_RETRIES):
        try:
            url = f"https://public-api.birdeye.so/public/market_depth?address={token_address}"
            headers = {"X-API-KEY": BIRDEYE_API_KEY}
            
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    return data.get("data", {})
                else:
                    msg = data.get("message", "Unknown error")
                    warning(f"BirdEye API error fetching markets: {msg}")
            else:
                warning(f"BirdEye API HTTP error: {response.status_code}")
                
                # If rate limited, wait longer before retry
                if response.status_code == 429:
                    time.sleep(API_RETRY_DELAY * 3)
                    continue
            
            # For other errors, wait standard delay
            time.sleep(API_RETRY_DELAY)
            
        except Exception as e:
            error(f"Exception fetching token markets: {str(e)}")
            time.sleep(API_RETRY_DELAY)
    
    # If we get here, all retries failed
    warning(f"Failed to fetch markets for {token_address} after {MAX_RETRIES} attempts")
    return None

def extract_token_info(token_address: str) -> Dict[str, Any]:
    """
    Comprehensive function to get all available token information
    
    Args:
        token_address: The token mint address
        
    Returns:
        Dictionary with combined token information
    """
    # Get metadata and price in parallel
    metadata = get_token_metadata(token_address)
    price = get_token_price(token_address)
    
    # Build comprehensive info object
    token_info = {
        "mint": token_address,
        "price": price or 0,
        "name": "Unknown Token",
        "symbol": "UNK",
        "decimals": 9,  # Default for most Solana tokens
        "logo": "",
        "coingeckoId": None,
        "twitter": None,
        "website": None,
        "data_source": "BirdEye API"
    }
    
    # Update with metadata if available
    if metadata:
        token_info.update({
            "name": metadata.get("name", token_info["name"]),
            "symbol": metadata.get("symbol", token_info["symbol"]),
            "decimals": metadata.get("decimals", token_info["decimals"]),
            "logo": metadata.get("logoURI", token_info["logo"]),
            "coingeckoId": metadata.get("coingeckoId", token_info["coingeckoId"]),
            "twitter": metadata.get("twitter", token_info["twitter"]),
            "website": metadata.get("website", token_info["website"]),
        })
    
    return token_info 