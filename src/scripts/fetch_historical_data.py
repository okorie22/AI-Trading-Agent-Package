import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from src import config
from dotenv import load_dotenv
from src.scripts.logger import debug, info, warning, error, critical
import os
import sys

load_dotenv()

# CoinGecko API URL
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/{}/market_chart"

# Birdeye API URL (for additional data if needed)
BIRDEYE_URL = "https://public-api.birdeye.so/public/price?address={}"

# Function to get tracked wallet tokens (used in dynamic mode)
def get_tracked_wallet_tokens():
    try:
        # Import here to avoid circular imports
        from src import nice_funcs as n
        
        tracked_tokens = set()
        # Get tracked wallets from config
        tracked_wallets = []
        
        # First check if TRACKED_WALLETS exists in config
        if hasattr(config, 'TRACKED_WALLETS') and config.TRACKED_WALLETS:
            tracked_wallets = config.TRACKED_WALLETS
        # Otherwise use the default wallet from config
        elif hasattr(config, 'address'):
            tracked_wallets = [config.address]
        else:
            # Last resort fallback
            warning("No tracked wallets found in config, using empty list")
            
        info(f"Using {len(tracked_wallets)} tracked wallets")
            
        # Get tokens from each wallet
        for wallet in tracked_wallets:
            try:
                wallet_tokens = n.get_wallet_tokens(wallet)
                if wallet_tokens:
                    tracked_tokens.update(wallet_tokens)
                    debug(f"Found {len(wallet_tokens)} tokens in wallet {wallet}", file_only=True)
            except Exception as e:
                warning(f"Could not fetch tokens for wallet {wallet}: {str(e)}")
                
        return list(tracked_tokens)
    except Exception as e:
        error(f"Error getting tracked wallet tokens: {str(e)}")
        return []

# Determine which tokens to use based on dynamic mode
ALL_TOKENS = set()

# If dynamic mode is enabled, try to get all tokens from tracked wallets
if hasattr(config, 'DYNAMIC_MODE') and config.DYNAMIC_MODE:
    info("Dynamic mode enabled - attempting to fetch all tokens from tracked wallets")
    wallet_tokens = get_tracked_wallet_tokens()
    if wallet_tokens:
        ALL_TOKENS.update(wallet_tokens)
        info(f"Found {len(wallet_tokens)} tokens in tracked wallets")
    else:
        warning("Could not fetch wallet tokens, falling back to configured tokens")

# Also add tokens from config lists (either as backup or in addition)
# Add explicitly monitored tokens 
if hasattr(config, 'MONITORED_TOKENS'):
    ALL_TOKENS.update(config.MONITORED_TOKENS)
# Add DCA tokens if defined
if hasattr(config, 'DCA_MONITORED_TOKENS'):
    ALL_TOKENS.update(config.DCA_MONITORED_TOKENS)
# Add tokens from TOKEN_MAP if defined
if hasattr(config, 'TOKEN_MAP'):
    ALL_TOKENS.update(config.TOKEN_MAP.keys())
# Add tokens from TOKEN_TO_HL_MAPPING if defined
if hasattr(config, 'TOKEN_TO_HL_MAPPING'):
    ALL_TOKENS.update(config.TOKEN_TO_HL_MAPPING.keys())
    
# Exclude any tokens marked as excluded
if hasattr(config, 'EXCLUDED_TOKENS'):
    for excluded in config.EXCLUDED_TOKENS:
        if excluded in ALL_TOKENS:
            ALL_TOKENS.remove(excluded)

# Convert to list for iteration
TOKENS = list(ALL_TOKENS)

# Time range for historical data (in days)
DAYS = 365  # 1 year of data

# Output CSV file
OUTPUT_FILE = "../data/historical_data.csv"

# Then use environment variable
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

def fetch_coingecko_data(token_id, days):
    """
    Fetch historical price data from CoinGecko.
    """
    # Basic parameters common to both APIs
    params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily",
    }
    
    # Determine if using Pro API (usually starts with CG-)
    headers = {}
    api_url = COINGECKO_URL.format(token_id)
    
    # Check if API key looks like a Pro API key
    if COINGECKO_API_KEY and COINGECKO_API_KEY.startswith("CG-"):
        # Use Pro API
        headers["x-cg-pro-api-key"] = COINGECKO_API_KEY
        # Modify the URL to use Pro API endpoint
        api_url = api_url.replace("api.coingecko.com", "pro-api.coingecko.com")
    else:
        # Use Free Demo API
        params["x_cg_demo_api_key"] = COINGECKO_API_KEY
    
    # Make the request with appropriate params and headers
    response = requests.get(api_url, params=params, headers=headers)
    
    if response.status_code != 200:
        error(f"CoinGecko API error: {response.status_code}")
        debug(f"Response: {response.text}", file_only=True)
        return None
    else:
        data = response.json()
        prices = data["prices"]
        return prices

def fetch_birdeye_data(token_id):
    """
    Fetch historical price data from Birdeye.
    """
    response = requests.get(BIRDEYE_URL.format(token_id))
    if response.status_code == 200:
        data = response.json()
        prices = [(entry["timestamp"], entry["price"]) for entry in data["data"]]
        return prices
    else:
        error(f"Birdeye API error for {token_id}: {response.status_code}")
        return None

def save_to_csv(data, filename):
    """
    Save historical data to a CSV file.
    """
    df = pd.DataFrame(data, columns=["timestamp", "price"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df[["date", "price"]]
    df.to_csv(filename, index=False)
    info(f"Data saved to {filename}")

def main():
    all_data = []
    
    info(f"Starting historical data fetch for {len(TOKENS)} tokens")
    debug(f"Token list: {TOKENS}", file_only=True)
    
    for token in TOKENS:
        info(f"Fetching data for {token}")
        prices = fetch_coingecko_data(token, DAYS)
        if not prices:
            warning(f"Falling back to Birdeye for {token}")
            prices = fetch_birdeye_data(token)
        
        if prices:
            for price in prices:
                all_data.append({
                    "token": token,
                    "timestamp": price[0],
                    "price": price[1]
                })
        time.sleep(1)  # Avoid hitting API rate limits
    
    # Save all data to CSV
    save_to_csv(all_data, OUTPUT_FILE)
    info(f"Completed data fetch for {len(TOKENS)} tokens")

if __name__ == "__main__":
    main()