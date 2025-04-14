"""
Anarcho Capital's OHLCV Data Collector
Collects Open-High-Low-Close-Volume data for specified tokens
Built with love by Anarcho Capital
"""

from src.config import *
from src import nice_funcs as n
import pandas as pd
from datetime import datetime
import os
from termcolor import colored, cprint
import time
from src.scripts.fetch_historical_data import fetch_coingecko_data
from src.scripts.logger import debug, info, warning, error, critical
import numpy as np
import requests
import random
import socket
socket.setdefaulttimeout(15)  # Increase timeout

# Token name cache
TOKEN_NAMES = {
    'VFdxjTdFzXrYr3ivWyf64NuXo9U7vdPK7AG7idnNZJV': 'SolChicks',
    'CR2L1ob96JGWQkdFbt8rLwqdLLmqFwjcNGL2eFBn1RPt': 'CHILL GUY',
    '2HdzfUiFWfZHZ544ynffeneuibbDK6biCdjovejr8ez9': 'MOODENG',
    'C94njgTrKMQBmgqe23EGLrtPgfvcjWtqBBvGQ7Cjiank': 'WIF',
    '67mTTGnVRunoSLGitgRGK2FJp5cT1KschjzWH9zKc3r': 'BONK',
    '9YnfbEaXPaPmoXnKZFmNH8hzcLyjbRf56MQP7oqGpump': 'PUMP',
    'DayN9FxpLAeiVrFQnRxwjKq7iVQxTieVGybhyXvSpump': 'PUMP',
    'Caykk3E1qZM6QBf82A2bZZiaLGntefrt4VAJXDWQ8Gm2': 'ETH',
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 'USDC',
    'So11111111111111111111111111111111111111111': 'SOL'
}

def get_token_name(token_address):
    """Get token name with enhanced fallback"""
    # Check local cache first
    if token_address in TOKEN_NAMES:
        return TOKEN_NAMES[token_address]
    
    # Try Jupiter API for token info
    try:
        url = "https://token.jup.ag/all"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            tokens = response.json()
            for token in tokens:
                if token.get('address') == token_address:
                    name = token.get('name', f"Unknown-{token_address[:4]}")
                    TOKEN_NAMES[token_address] = name
                    return name
    except Exception as e:
        warning(f"Jupiter token info error: {str(e)}")
    
    # Try Birdeye token info
    try:
        headers = {"X-API-KEY": os.getenv("BIRDEYE_API_KEY", "9ca8697fa5974150a760c7d7ad9310e3")}
        url = f"https://public-api.birdeye.so/public/tokenlist?address={token_address}"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('data', {}).get('name'):
                name = data['data']['name']
                TOKEN_NAMES[token_address] = name
                return name
    except Exception as e:
        warning(f"Birdeye token info error: {str(e)}")
    
    # Fallback to abbreviated address
    name = f"Token-{token_address[:4]}..{token_address[-4:]}"
    TOKEN_NAMES[token_address] = name
    return name

def collect_token_data(token_address, suppress_logs=False):
    """Collects OHLCV data for a specific token"""
    try:
        token_name = get_token_name(token_address)
        
        # Modify print statements to be conditional
        if not suppress_logs:
            info(f"Collecting market data for {token_address[:6]}")
        
        # Step 1: Try Birdeye API (primary source)
        try:
            debug(f"Attempting Birdeye data for {token_name}", file_only=True)
            headers = {"X-API-KEY": os.getenv("BIRDEYE_API_KEY", "9ca8697fa5974150a760c7d7ad9310e3")}
            url = f"https://public-api.birdeye.so/public/candle?address={token_address}&type=day&limit=14"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data'):
                    candles = data['data']
                    if candles:
                        # Convert Birdeye format to our dataframe
                        df = pd.DataFrame(candles)
                        df['date'] = pd.to_datetime(df['time'], unit='s')
                        df['name'] = token_name
                        df['source'] = 'Birdeye'  # Add source information
                        info(f"Birdeye data found for {token_name}")
                        return df
        except Exception as e:
            warning(f"Birdeye data failed: {str(e)}")
        
        # Step 2: Try CoinGecko as fallback
        try:
            info(f"Falling back to CoinGecko for {token_name}")
            # Call the imported fetch_coingecko_data function
            coingecko_data = fetch_coingecko_data(token_address, 14)
            if coingecko_data is not None and len(coingecko_data) > 0:
                # Convert CoinGecko format to our dataframe
                df = pd.DataFrame(coingecko_data, columns=['timestamp', 'price'])
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['close'] = df['price']
                df['open'] = df['price']
                df['high'] = df['price'] * 1.01  # Estimate
                df['low'] = df['price'] * 0.99   # Estimate
                df['volume'] = 100000            # Placeholder
                df['name'] = token_name
                df['source'] = 'CoinGecko'  # Add source information
                
                # Add technical indicators
                df['MA20'] = df['close'].rolling(window=min(7, len(df))).mean()
                df['MA40'] = df['close'].rolling(window=min(10, len(df))).mean()
                df['MA20'] = df['MA20'].fillna(df['close'])
                df['MA40'] = df['MA40'].fillna(df['close'])
                df['ABOVE_MA20'] = df['close'] > df['MA20']
                df['ABOVE_MA40'] = df['close'] > df['MA40']
                
                info(f"CoinGecko data found for {token_name}")
                return df
        except Exception as e:
            warning(f"CoinGecko fallback failed: {str(e)}")
        
        # Step 3: Generate synthetic data as last resort
        warning(f"All API sources failed. Generating synthetic data for {token_name}")
        return generate_synthetic_data(token_address, 14)
    except Exception as e:
        if not suppress_logs:
            error(f"Error collecting data for {token_address}: {str(e)}")
        return None

def generate_synthetic_data(token_address, days=14):
    """Generate synthetic OHLCV data for testing"""
    # Try to get current price (or use fallback)
    current_price = 1.0
    try:
        # Import within function to avoid circular imports
        from src import nice_funcs as n
        current_price = n.get_token_price(token_address) or 1.0
    except Exception:
        pass
    
    # Get token name
    token_name = get_token_name(token_address)
    
    # Create date range
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days)
    
    # Generate price data with trend and volatility
    base_price = current_price
    trend = random.choice([-0.01, 0.01])  # Slight downtrend or uptrend
    volatility = random.uniform(0.02, 0.10)  # Random volatility
    
    # Generate price series with some randomness
    closes = []
    for i in range(days):
        # Random daily movement with trend
        daily_change = trend + random.normalvariate(0, volatility)
        # Ensure price doesn't go negative
        base_price = max(0.00001, base_price * (1 + daily_change))
        closes.append(base_price)
    
    # Create OHLCV data
    df = pd.DataFrame({
        'date': dates,
        'price': closes,
        'open': [p * (1 - random.uniform(0, 0.02)) for p in closes],
        'high': [p * (1 + random.uniform(0, 0.03)) for p in closes],
        'low': [p * (1 - random.uniform(0, 0.03)) for p in closes],
        'close': closes,
        'volume': [random.uniform(10000, 1000000) * p for p in closes],
        'name': [token_name] * days,
        'source': ['Synthetic'] * days  # Add source information
    })
    
    # Add simple technical indicators
    df['MA20'] = df['close'].rolling(window=min(7, len(df))).mean()
    df['MA40'] = df['close'].rolling(window=min(10, len(df))).mean()
    
    # Fill NaN values in moving averages for first few rows
    df['MA20'] = df['MA20'].fillna(df['close'])
    df['MA40'] = df['MA40'].fillna(df['close'])
    
    # Boolean indicators
    df['ABOVE_MA20'] = df['close'] > df['MA20']
    df['ABOVE_MA40'] = df['close'] > df['MA40']
    
    # Reset index and return
    df = df.reset_index(drop=True)
    
    return df

def collect_all_tokens(token_list=None):
    """Collect data for multiple tokens"""
    if token_list is None:
        token_list = MONITORED_TOKENS
    
    all_data = {}
    for token in token_list:
        data = collect_token_data(token)
        if data is not None and not data.empty:
            all_data[token] = data
            debug(f"Data collected for {get_token_name(token)}", file_only=True)
        # Avoid rate limits
        time.sleep(1)
    
    info(f"Collected data for {len(all_data)} tokens")
    return all_data

if __name__ == "__main__":
    try:
        collect_all_tokens()
    except KeyboardInterrupt:
        info("OHLCV Collector shutting down gracefully")
    except Exception as e:
        error(f"Error: {str(e)}")
        warning("Check the logs and try again") 