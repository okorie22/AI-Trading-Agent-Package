"""
Token Price Helper
Provides functions for getting token price and metadata using multiple APIs:
1. BirdEye API (with correct /defi/ endpoint formatting)
2. Jupiter API (as a reliable fallback)

This module automatically manages API fallbacks and caching.
"""

import os
import requests
import json
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("token_price_helper")

# API Keys and configuration
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
API_TIMEOUT = 10  # seconds
API_RETRY_DELAY = 2  # seconds
MAX_RETRIES = 3

# Cache settings
CACHE_EXPIRY = 300  # seconds (5 minutes)
TOKEN_PRICE_CACHE = {}  # {token_address: (timestamp, price)}
TOKEN_METADATA_CACHE = {}  # {token_address: (timestamp, metadata)}

def clear_cache():
    """Clear all cache data"""
    global TOKEN_PRICE_CACHE, TOKEN_METADATA_CACHE
    TOKEN_PRICE_CACHE = {}
    TOKEN_METADATA_CACHE = {}
    logger.info("Cache cleared")

def _is_cache_valid(cache_entry):
    """Check if a cache entry is valid (not expired)"""
    if not cache_entry:
        return False
    timestamp, _ = cache_entry
    return (time.time() - timestamp) < CACHE_EXPIRY

def _make_request(url, headers=None, params=None, method="GET", data=None, timeout=API_TIMEOUT):
    """Make an HTTP request with retries and error handling"""
    if headers is None:
        headers = {}
    
    for attempt in range(MAX_RETRIES):
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            else:
                logger.error(f"Unsupported method: {method}")
                return None
            
            # Check if request was successful
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Request failed with status {response.status_code}: {url}")
                
                # Add delay before retrying, longer for rate limiting
                if response.status_code == 429:  # Rate limit
                    time.sleep(API_RETRY_DELAY * 2)
                else:
                    time.sleep(API_RETRY_DELAY)
                    
        except Exception as e:
            logger.warning(f"Request error ({attempt+1}/{MAX_RETRIES}): {str(e)}")
            time.sleep(API_RETRY_DELAY)
    
    # If we get here, all retries failed
    logger.error(f"All {MAX_RETRIES} attempts failed for URL: {url}")
    return None

def _get_token_price_birdeye(token_address: str) -> Optional[float]:
    """Get token price from BirdEye API"""
    if not BIRDEYE_API_KEY:
        logger.warning("BirdEye API key not set")
        return None
    
    # Use the correct endpoint format from the documentation
    url = f"https://public-api.birdeye.so/defi/price"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    params = {"address": token_address}
    
    logger.debug(f"Requesting BirdEye price for {token_address[:8]}...")
    data = _make_request(url, headers=headers, params=params)
    
    if data and data.get("success"):
        price_data = data.get("data", {})
        if isinstance(price_data, dict) and "value" in price_data:
            price = price_data["value"]
            logger.info(f"Got BirdEye price for {token_address[:8]}: ${price}")
            return float(price)
        elif isinstance(price_data, float) or isinstance(price_data, int):
            # Handle case where price is returned directly
            logger.info(f"Got BirdEye price for {token_address[:8]}: ${price_data}")
            return float(price_data)
    
    logger.warning(f"Failed to get price from BirdEye for {token_address[:8]}")
    return None

def _get_token_price_jupiter(token_address: str) -> Optional[float]:
    """Get token price from Jupiter API"""
    url = f"https://price.jup.ag/v4/price?ids={token_address}"
    
    logger.debug(f"Requesting Jupiter price for {token_address[:8]}...")
    data = _make_request(url)
    
    if data and "data" in data and token_address in data["data"]:
        token_data = data["data"][token_address]
        if token_data and "price" in token_data:
            price = token_data["price"]
            logger.info(f"Got Jupiter price for {token_address[:8]}: ${price}")
            return float(price)
    
    # Try Jupiter v6 API as an alternative
    try:
        url = f"https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111111&outputMint={token_address}&amount=1000000000"
        data = _make_request(url)
        
        if data and "outAmount" in data:
            # This is approximating the price calculation from a SOL to token swap quote
            # 1 SOL to X tokens, so price = 1/X SOL per token
            out_amount = int(data["outAmount"])
            token_decimals = data.get("outputDecimal", 9)  # Default to 9 decimals for SPL tokens
            price_in_sol = 1 / (out_amount / (10 ** token_decimals))
            
            # Get SOL price to convert to USD
            sol_price_url = "https://price.jup.ag/v4/price?ids=So11111111111111111111111111111111111111111"
            sol_data = _make_request(sol_price_url)
            
            if sol_data and "data" in sol_data and "So11111111111111111111111111111111111111111" in sol_data["data"]:
                sol_price = sol_data["data"]["So11111111111111111111111111111111111111111"]["price"]
                price_in_usd = price_in_sol * sol_price
                logger.info(f"Got Jupiter v6 price for {token_address[:8]}: ${price_in_usd}")
                return float(price_in_usd)
    except Exception as e:
        logger.warning(f"Jupiter v6 price calculation failed: {str(e)}")
    
    logger.warning(f"Failed to get price from Jupiter for {token_address[:8]}")
    return None

def _get_token_metadata_birdeye(token_address: str) -> Optional[Dict]:
    """Get token metadata from BirdEye API"""
    if not BIRDEYE_API_KEY:
        logger.warning("BirdEye API key not set")
        return None
    
    # Try token list specific query first
    url = f"https://public-api.birdeye.so/defi/tokenlist"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    params = {"address": token_address}
    
    logger.debug(f"Requesting BirdEye metadata for {token_address[:8]}...")
    data = _make_request(url, headers=headers, params=params)
    
    if data and data.get("success") and data.get("data"):
        metadata = data["data"]
        logger.info(f"Got BirdEye metadata for {token_address[:8]}")
        return metadata
    
    # Try token overview for more data (might require higher tier)
    url = f"https://public-api.birdeye.so/defi/token_overview"
    params = {"address": token_address}
    
    data = _make_request(url, headers=headers, params=params)
    
    if data and data.get("success") and data.get("data"):
        metadata = data["data"]
        logger.info(f"Got BirdEye token overview for {token_address[:8]}")
        return metadata
    
    logger.warning(f"Failed to get metadata from BirdEye for {token_address[:8]}")
    return None

def _get_token_metadata_jupiter(token_address: str) -> Optional[Dict]:
    """Get token metadata from Jupiter API"""
    # Try specific token endpoint first
    url = f"https://token.jup.ag/tokens/{token_address}"
    
    logger.debug(f"Requesting Jupiter metadata for {token_address[:8]}...")
    data = _make_request(url)
    
    if data:
        logger.info(f"Got Jupiter metadata for {token_address[:8]}")
        return data
    
    # Try searching in the full token list
    url = "https://token.jup.ag/all"
    all_tokens = _make_request(url)
    
    if all_tokens:
        for token in all_tokens:
            if token.get("address") == token_address:
                logger.info(f"Found {token_address[:8]} in Jupiter token list")
                return token
    
    logger.warning(f"Failed to get metadata from Jupiter for {token_address[:8]}")
    return None

def get_token_price(token_address: str, force_refresh: bool = False) -> Optional[float]:
    """
    Get token price using available APIs with caching
    
    Args:
        token_address: The token mint address
        force_refresh: If True, bypass cache and get fresh data
        
    Returns:
        Float price or None if not available
    """
    # Check cache if not forcing refresh
    if not force_refresh and token_address in TOKEN_PRICE_CACHE:
        if _is_cache_valid(TOKEN_PRICE_CACHE[token_address]):
            timestamp, price = TOKEN_PRICE_CACHE[token_address]
            logger.debug(f"Using cached price for {token_address[:8]}")
            return price
    
    # Try BirdEye first
    price = _get_token_price_birdeye(token_address)
    
    # Fall back to Jupiter if BirdEye fails
    if price is None:
        price = _get_token_price_jupiter(token_address)
    
    # Update cache if we got a price
    if price is not None:
        TOKEN_PRICE_CACHE[token_address] = (time.time(), price)
        return price
    
    logger.error(f"All price sources failed for {token_address[:8]}")
    return None

def get_token_metadata(token_address: str, force_refresh: bool = False) -> Optional[Dict]:
    """
    Get token metadata using available APIs with caching
    
    Args:
        token_address: The token mint address
        force_refresh: If True, bypass cache and get fresh data
        
    Returns:
        Dict with token metadata or None if not available
    """
    # Check cache if not forcing refresh
    if not force_refresh and token_address in TOKEN_METADATA_CACHE:
        if _is_cache_valid(TOKEN_METADATA_CACHE[token_address]):
            timestamp, metadata = TOKEN_METADATA_CACHE[token_address]
            logger.debug(f"Using cached metadata for {token_address[:8]}")
            return metadata
    
    # Try BirdEye first
    metadata = _get_token_metadata_birdeye(token_address)
    
    # Fall back to Jupiter if BirdEye fails
    if metadata is None:
        metadata = _get_token_metadata_jupiter(token_address)
    
    # Update cache if we got metadata
    if metadata is not None:
        TOKEN_METADATA_CACHE[token_address] = (time.time(), metadata)
        return metadata
    
    logger.error(f"All metadata sources failed for {token_address[:8]}")
    return None

def get_token_info(token_address: str) -> Dict[str, Any]:
    """
    Get comprehensive token information combining price and metadata
    
    Args:
        token_address: The token mint address
        
    Returns:
        Dict with combined token information
    """
    # Get metadata and price
    metadata = get_token_metadata(token_address)
    price = get_token_price(token_address)
    
    # Build a normalized structure to handle differences between APIs
    token_info = {
        "address": token_address,
        "price": price or 0,
        "name": "Unknown Token",
        "symbol": "UNK",
        "decimals": 9,  # Default for most SPL tokens
        "logo": None,
        "last_updated": datetime.now().isoformat(),
    }
    
    # Update with metadata if available
    if metadata:
        # Handle both Jupiter and BirdEye formats
        if "name" in metadata:
            token_info["name"] = metadata["name"]
        if "symbol" in metadata:
            token_info["symbol"] = metadata["symbol"]
        if "decimals" in metadata:
            token_info["decimals"] = metadata["decimals"]
        if "logoURI" in metadata:
            token_info["logo"] = metadata["logoURI"]
        elif "logo" in metadata:
            token_info["logo"] = metadata["logo"]
        
        # Add raw metadata for advanced use
        token_info["raw_metadata"] = metadata
    
    return token_info

def test_apis():
    """Test both APIs and print results"""
    print("Testing Token Price Helper APIs...")
    
    test_tokens = [
        "So11111111111111111111111111111111111111111",  # SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    ]
    
    for token in test_tokens:
        print(f"\nTesting token: {token}")
        
        # Test BirdEye directly
        print("\nBirdEye API:")
        price = _get_token_price_birdeye(token)
        print(f"  Price: {price}")
        metadata = _get_token_metadata_birdeye(token)
        print(f"  Metadata: {metadata is not None}")
        
        # Test Jupiter directly
        print("\nJupiter API:")
        price = _get_token_price_jupiter(token)
        print(f"  Price: {price}")
        metadata = _get_token_metadata_jupiter(token)
        print(f"  Metadata: {metadata is not None}")
        
        # Test combined function
        print("\nCombined Function:")
        token_info = get_token_info(token)
        print(f"  Name: {token_info['name']}")
        print(f"  Symbol: {token_info['symbol']}")
        print(f"  Price: {token_info['price']}")
        
        print("-" * 50)

if __name__ == "__main__":
    # Run tests if script is executed directly
    test_apis() 