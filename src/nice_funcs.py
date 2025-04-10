"""
Moon Dev's Nice Functions - A collection of utility functions for trading
Built with love by Moon Dev
"""

from dotenv import load_dotenv
import os
from functools import lru_cache
import time
from src.scripts.logger import debug, info, warning, error, critical

# Load .env file
load_dotenv()

# Fetch API key
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

# Check if it's loaded
if not BIRDEYE_API_KEY:
    raise ValueError("BIRDEYE_API_KEY not found in environment variables!")


from src.config import *
import requests
import pandas as pd
import pprint
import re as reggie
import sys
import os
import time
import json
import numpy as np
import datetime
import pandas_ta as ta
from datetime import datetime, timedelta
from termcolor import colored, cprint
import solders
from dotenv import load_dotenv
import shutil
import atexit
from src.scripts.fetch_historical_data import fetch_coingecko_data
import base58
import csv


# Load environment variables
load_dotenv()

# Get API keys from environment
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
if not BIRDEYE_API_KEY:
    raise ValueError("🚨 BIRDEYE_API_KEY not found in environment variables!")

sample_address = "2yXTyarttn2pTZ6cwt4DqmrRuBw1G7pmFv9oT6MStdKP"

BASE_URL = "https://public-api.birdeye.so/defi"

# Add this price cache dictionary
_price_cache = {}
_price_cache_expiry = {}
CACHE_EXPIRY_SECONDS = 60  # Cache prices for 60 seconds

def token_price(token_address, force_refresh=False):
    """
    Get the current price of a token in USD
    
    Args:
        token_address (str): The mint address of the token
        force_refresh (bool): Whether to force refresh the price or use cached value
        
    Returns:
        float: Current price in USD or None if not found/error
    """
    try:
        # Use cache unless force_refresh is True
        global _price_cache, _price_cache_expiry
        current_time = time.time()
        
        # Return cached price if available and not expired
        if not force_refresh and token_address in _price_cache:
            if current_time < _price_cache_expiry.get(token_address, 0):
                return _price_cache[token_address]
        
        # First try BirdEye API (most reliable for current prices)
        try:
            birdeye_api_key = os.getenv("BIRDEYE_API_KEY", "")
            if birdeye_api_key:
                headers = {"X-API-KEY": birdeye_api_key}
                url = f"https://public-api.birdeye.so/public/price?address={token_address}"
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", False):
                        price = data.get("data", {}).get("value", 0)
                        if price:
                            # Cache the price
                            _price_cache[token_address] = float(price)
                            _price_cache_expiry[token_address] = current_time + CACHE_EXPIRY_SECONDS
                            return float(price)
        except Exception as be_error:
            warning(f"BirdEye price lookup failed: {str(be_error)}")
                    
        # Fallback to Jupiter API (good alternative source)
        try:
            info(f"Falling back to Jupiter API for price...")
            jupiter_url = f"https://price.jup.ag/v4/price?ids={token_address}"
            response = requests.get(jupiter_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                price_data = data.get("data", {}).get(token_address)
                if price_data:
                    price = price_data.get("price", 0)
                    if price:
                        # Cache the price
                        _price_cache[token_address] = float(price)
                        _price_cache_expiry[token_address] = current_time + CACHE_EXPIRY_SECONDS
                        return float(price)
        except Exception as jupiter_e:
            warning(f"Jupiter price lookup failed: {str(jupiter_e)}")
            
        # Try another fallback for common tokens
        try:
            info(f"Trying additional price sources...")
            # For SOL, we can use CoinGecko
            if token_address == "So11111111111111111111111111111111111111112":
                try:
                    response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        sol_price = data.get("solana", {}).get("usd", 0)
                        if sol_price:
                            # Cache the price
                            _price_cache[token_address] = float(sol_price)
                            _price_cache_expiry[token_address] = current_time + CACHE_EXPIRY_SECONDS
                            return float(sol_price)
                except Exception as cg_e:
                    warning(f"CoinGecko lookup failed: {str(cg_e)}")
            
            # For USDC, return 1.0 (it's a stablecoin)
            if token_address == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v":
                _price_cache[token_address] = 1.0
                _price_cache_expiry[token_address] = current_time + CACHE_EXPIRY_SECONDS
                return 1.0
        except Exception as other_e:
            warning(f"Alternative price source failed: {str(other_e)}")
        
        # If we get here, return None to indicate failure
        warning(f"Could not get price for token {token_address}")
        return None
        
    except Exception as e:
        error(f"Error getting token price: {str(e)}")
        return None

def get_real_time_price_jupiter(token_address):
    url = f"https://quote-api.jup.ag/v6/price?ids={token_address}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('data', {}).get(token_address, {}).get('price', None)
    return None

def get_real_time_price_raydium(token_address):
    url = f"https://api.raydium.io/v1/token/{token_address}/price"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('price', None)
    else:
        error(f"Raydium API failed for {token_address}: HTTP {response.status_code}")
        return None

def get_real_time_price_orca(token_address):
    url = f"https://api.orca.so/v1/token/{token_address}/price"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('price', None)
    else:
        error(f"Orca API failed for {token_address}: HTTP {response.status_code}")
        return None

def get_real_time_price_pyth(token_address):
    url = f"https://api.pyth.network/v1/price/{token_address}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('price', None)
    else:
        error(f"Pyth API failed for {token_address}: HTTP {response.status_code}")
        return None

def get_real_time_price_chainlink(token_address):
    url = f"https://api.chain.link/v1/price/{token_address}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('price', None)
    else:
        error(f"Chainlink API failed for {token_address}: HTTP {response.status_code}")
        return None

def get_real_time_price_serum(token_address):
    url = f"https://api.serum.io/v1/trades/{token_address}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('price', None)
    return None

def get_real_time_price_coingecko(token_address):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_address}&vs_currencies=usd"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get(token_address, {}).get('usd', None)
    else:
        error(f"CoinGecko API failed for {token_address}: HTTP {response.status_code}")
        return None

def get_real_time_price_solanafm(token_address):
    url = f"https://api.solana.fm/v1/tokens/{token_address}/price"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('price', None)
    else:
        error(f"SolanaFM API failed for {token_address}: HTTP {response.status_code}")
        return None

# Create temp directory and register cleanup
os.makedirs('temp_data', exist_ok=True)

def cleanup_temp_data():
    if os.path.exists('temp_data'):
        info("Moon Dev cleaning up temporary data...")
        shutil.rmtree('temp_data')

atexit.register(cleanup_temp_data)

# Custom function to print JSON in a human-readable format
def print_pretty_json(data):
    pp = pprint.PrettyPrinter(indent=4)
    debug(pp.pformat(data), file_only=True)

# Function to print JSON in a human-readable format - assuming you already have it as print_pretty_json
# Helper function to find URLs in text
def find_urls(string):
    # Regex to extract URLs
    return reggie.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)

# UPDATED TO RMEOVE THE OTHER ONE so now we can just use this filter instead of filtering twice
def token_overview(address):
    """
    Fetch token overview for a given address and return structured information, including specific links,
    and assess if any price change suggests a rug pull.
    """

    info(f'Getting the token overview for {address}')
    overview_url = f"{BASE_URL}/token_overview?address={address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}

    response = requests.get(overview_url, headers=headers)
    result = {}

    if response.status_code == 200:
        overview_data = response.json().get('data', {})

        # Retrieve buy1h, sell1h, and calculate trade1h
        buy1h = overview_data.get('buy1h', 0)
        sell1h = overview_data.get('sell1h', 0)
        trade1h = buy1h + sell1h

        # Add the calculated values to the result
        result['buy1h'] = buy1h
        result['sell1h'] = sell1h
        result['trade1h'] = trade1h

        # Calculate buy and sell percentages
        total_trades = trade1h  # Assuming total_trades is the sum of buy and sell
        buy_percentage = (buy1h / total_trades * 100) if total_trades else 0
        sell_percentage = (sell1h / total_trades * 100) if total_trades else 0
        result['buy_percentage'] = buy_percentage
        result['sell_percentage'] = sell_percentage

        # Check if trade1h is bigger than MIN_TRADES_LAST_HOUR
        result['minimum_trades_met'] = True if trade1h >= MIN_TRADES_LAST_HOUR else False

        # Extract price changes over different timeframes
        price_changes = {k: v for k, v in overview_data.items() if 'priceChange' in k}
        result['priceChangesXhrs'] = price_changes

        # Check for rug pull indicator
        rug_pull = any(value < -80 for key, value in price_changes.items() if value is not None)
        result['rug_pull'] = rug_pull
        if rug_pull:
            warning("Warning: Price change percentage below -80%, potential rug pull")

        # Extract other metrics
        unique_wallet2hr = overview_data.get('uniqueWallet24h', 0)
        v24USD = overview_data.get('v24hUSD', 0)
        watch = overview_data.get('watch', 0)
        view24h = overview_data.get('view24h', 0)
        liquidity = overview_data.get('liquidity', 0)

        # Add the retrieved data to result
        result.update({
            'uniqueWallet2hr': unique_wallet2hr,
            'v24USD': v24USD,
            'watch': watch,
            'view24h': view24h,
            'liquidity': liquidity,
        })

        # Extract and process description links if extensions are not None
        extensions = overview_data.get('extensions', {})
        description = extensions.get('description', '') if extensions else ''
        urls = find_urls(description)
        links = []
        for url in urls:
            if 't.me' in url:
                links.append({'telegram': url})
            elif 'twitter.com' in url:
                links.append({'twitter': url})
            elif 'youtube' not in url:  # Assume other URLs are for website
                links.append({'website': url})

        # Add extracted links to result
        result['description'] = links


        # Return result dictionary with all the data
        return result
    else:
        error(f"Failed to retrieve token overview for address {address}: HTTP status code {response.status_code}")
        return None


def token_security_info(address):

    '''

    bigmatter
​freeze authority is like renouncing ownership on eth

    Token Security Info:
{   'creationSlot': 242801308,
    'creationTime': 1705679481,
    'creationTx': 'ZJGoayaNDf2dLzknCjjaE9QjqxocA94pcegiF1oLsGZ841EMWBEc7TnDKLvCnE8cCVfkvoTNYCdMyhrWFFwPX6R',
    'creatorAddress': 'AGWdoU4j4MGJTkSor7ZSkNiF8oPe15754hsuLmwcEyzC',
    'creatorBalance': 0,
    'creatorPercentage': 0,
    'freezeAuthority': None,
    'freezeable': None,
    'isToken2022': False,
    'isTrueToken': None,
    'lockInfo': None,
    'metaplexUpdateAuthority': 'AGWdoU4j4MGJTkSor7ZSkNiF8oPe15754hsuLmwcEyzC',
    'metaplexUpdateAuthorityBalance': 0,
    'metaplexUpdateAuthorityPercent': 0,
    'mintSlot': 242801308,
    'mintTime': 1705679481,
    'mintTx': 'ZJGoayaNDf2dLzknCjjaE9QjqxocA94pcegiF1oLsGZ841EMWBEc7TnDKLvCnE8cCVfkvoTNYCdMyhrWFFwPX6R',
    'mutableMetadata': True,
    'nonTransferable': None,
    'ownerAddress': None,
    'ownerBalance': None,
    'ownerPercentage': None,
    'preMarketHolder': [],
    'top10HolderBalance': 357579981.3372284,
    'top10HolderPercent': 0.6439307358062863,
    'top10UserBalance': 138709981.9366756,
    'top10UserPercent': 0.24978920911102176,

    '''
    # Send a GET request to the token_security endpoint with the token address and API key
    security_url = f"{BASE_URL}/token_security?address={address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}

    response = requests.get(security_url, headers=headers)

    if response.status_code == 200:
        security_data = response.json().get('data', {})
        return security_data
    else:
        error("Failed to retrieve token security info:", response.status_code)
        return None

def token_creation_info(address):
    '''
    creationStamp: 1706064023
    creator: "2tBhLa37nL4ahPLzUMRwcQ3mqTb3aQz5Uy3jYHjJbpsN"
    supply: 44444000000
    
    '''
    # Send a GET request to the token_creation endpoint with the token address and API key
    creation_url = f"{BASE_URL}/token_creation?address={address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}

    response = requests.get(creation_url, headers=headers)

    if response.status_code == 200:
        creation_data = response.json().get('data', {})
        return creation_data
    else:
        error("Failed to retrieve token creation info:", response.status_code)
        return None

def market_sell(QUOTE_TOKEN, amount, slippage):
    try:
        # Get USDC token mint address
        token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        SLIPPAGE = slippage
        KEY = n.get_key()
        http_client = n.get_client()
        
        # Convert amount to string if int/float
        if isinstance(amount, (int, float)):
            amount = str(amount)
            
        info(f"Preparing to sell {amount} units of {QUOTE_TOKEN[:8]}... for USDC")
            
        # Get quote from Jupiter
        quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token}&amount={amount}&slippageBps={SLIPPAGE}'
        quote_response = requests.get(quote_url, timeout=15)
        
        if quote_response.status_code != 200:
            error(f"Failed to get quote: HTTP {quote_response.status_code}")
            return None
            
        quote = quote_response.json()
        if not quote or "data" not in quote:
            error("Invalid quote response from Jupiter")
            return None
            
        # Create swap transaction
        try:
            txRes = requests.post(
                'https://quote-api.jup.ag/v6/swap',
                headers={"Content-Type": "application/json"},
                timeout=15,
                json={
                    "quoteResponse": quote,
                    "userPublicKey": str(KEY.pubkey()),
                    "prioritizationFeeLamports": PRIORITY_FEE
                }
            )
            
            if txRes.status_code != 200:
                error(f"Failed to create swap transaction: HTTP {txRes.status_code}")
                return None
                
            tx_data = txRes.json()
            if not tx_data or "swapTransaction" not in tx_data:
                error("Invalid swap transaction response")
                return None
                
            swapTx = base64.b64decode(tx_data['swapTransaction'])
        except Exception as e:
            error(f"Error creating swap transaction: {str(e)}")
            return None
            
        # Sign and send transaction
        try:
            tx1 = VersionedTransaction.from_bytes(swapTx)
            tx = VersionedTransaction(tx1.message, [KEY])
            
            txId = http_client.send_raw_transaction(
                bytes(tx), 
                TxOpts(skip_preflight=True)
            ).value
            
            info(f"Sell transaction sent: https://solscan.io/tx/{str(txId)}")
            return str(txId)
        except Exception as e:
            error(f"Error sending transaction: {str(e)}")
            return None
            
    except Exception as e:
        error(f"Error in market_sell: {str(e)}")
        return None

def get_time_range():

    now = datetime.now()
    ten_days_earlier = now - timedelta(days=10)
    time_to = int(now.timestamp())
    time_from = int(ten_days_earlier.timestamp())
    #print(time_from, time_to)

    return time_from, time_to

import math
def round_down(value, decimals):
    factor = 10 ** decimals
    return math.floor(value * factor) / factor


def get_time_range(days_back):

    now = datetime.now()
    ten_days_earlier = now - timedelta(days=days_back)
    time_to = int(now.timestamp())
    time_from = int(ten_days_earlier.timestamp())
    #print(time_from, time_to)

    return time_from, time_to

def get_data(address, days_back_4_data, timeframe):
    time_from, time_to = get_time_range(days_back_4_data)

    # Check temp data first
    temp_file = f"temp_data/{address}_latest.csv"
    if os.path.exists(temp_file):
        debug(f"Found cached data for {address[:4]}")
        return pd.read_csv(temp_file)

    url = f"https://public-api.birdeye.so/defi/ohlcv?address={address}&type={timeframe}&time_from={time_from}&time_to={time_to}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        json_response = response.json()
        items = json_response.get('data', {}).get('items', [])

        processed_data = [{
            'Datetime (UTC)': datetime.utcfromtimestamp(item['unixTime']).strftime('%Y-%m-%d %H:%M:%S'),
            'Open': item['o'],
            'High': item['h'],
            'Low': item['l'],
            'Close': item['c'],
            'Volume': item['v']
        } for item in items]

        df = pd.DataFrame(processed_data)

        # Remove any rows with dates far in the future
        current_date = datetime.now()
        df['datetime_obj'] = pd.to_datetime(df['Datetime (UTC)'])
        df = df[df['datetime_obj'] <= current_date]
        df = df.drop('datetime_obj', axis=1)

        # Pad if needed
        if len(df) < 40:
            warning(f"Padding data to ensure minimum 40 rows for analysis")
            rows_to_add = 40 - len(df)
            first_row_replicated = pd.concat([df.iloc[0:1]] * rows_to_add, ignore_index=True)
            df = pd.concat([first_row_replicated, df], ignore_index=True)

        info(f"Data Analysis Ready! Processing {len(df)} candles")

        # Always save to temp for current run
        df.to_csv(temp_file)
        debug(f"Cached data for {address[:4]}")

        # Calculate indicators
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA40'] = ta.sma(df['Close'], length=40)

        df['Price_above_MA20'] = df['Close'] > df['MA20']
        df['Price_above_MA40'] = df['Close'] > df['MA40']
        df['MA20_above_MA40'] = df['MA20'] > df['MA40']

        return df
    else:
        error(f"Failed to fetch data for address {address}. Status code: {response.status_code}")
        if response.status_code == 401:
            warning("Check your BIRDEYE_API_KEY in .env file!")
        
        # Fallback to CoinGecko
        info(f"Falling back to CoinGecko for {address}...")
        prices = fetch_coingecko_data(address, days_back_4_data)
        if prices:
            df = pd.DataFrame(prices, columns=["timestamp", "price"])
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df[["date", "price"]]
            df.to_csv(temp_file)
            debug(f"Cached data from CoinGecko for {address[:4]}")
            return df
        else:
            return pd.DataFrame()



def fetch_wallet_holdings_og(address, min_value=0.01):
    """
    Fetch wallet token holdings data
    
    Args:
        address (str): Wallet address to check
        min_value (float): Minimum USD value of tokens to include
        
    Returns:
        pd.DataFrame: Dataframe with token holdings data or empty dataframe if none
    """
    try:
        url = f"https://public-api.birdeye.so/v1/wallet/tokens?address={address}"
        headers = {"X-API-KEY": os.getenv("BIRDEYE_API_KEY")}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            warning(f"Failed to fetch wallet data: HTTP {response.status_code}")
            return pd.DataFrame()
            
        data = response.json()
        if data.get("success", False) is False:
            warning("API reported error in fetching wallet data")
            return pd.DataFrame()
            
        tokens = data.get("data", {}).get("items", [])
        if not tokens:
            warning("No wallet holdings to display.")
            return pd.DataFrame()
            
        # Process token data
        holdings = []
        for token in tokens:
            symbol = token.get("symbol", "Unknown")
            amount = float(token.get("balance", 0))
            price = float(token.get("price", 0))
            value = float(token.get("value", 0))
            
            if value >= min_value:
                holdings.append({
                    "Token": symbol,
                    "Address": token.get("address", ""),
                    "Amount": amount,
                    "Price": price,
                    "USD Value": value
                })
                
        if not holdings:
            warning("No tokens above minimum value threshold.")
            return pd.DataFrame()
            
        df = pd.DataFrame(holdings)
        df = df.sort_values(by="USD Value", ascending=False).reset_index(drop=True)
        return df
    except Exception as e:
        error(f"Error fetching wallet holdings: {str(e)}")
        return pd.DataFrame()

def fetch_wallet_token_single(address, token_mint_address):

    df = fetch_wallet_holdings_og(address)

    # filter by token mint address
    df = df[df['Mint Address'] == token_mint_address]

    return df

def get_position(token_mint_address):
    """
    Get the balance of a specific token in the wallet
    """
    # Get current wallet token holdings
    dataframe = fetch_wallet_holdings_og(address)
    
    # If the DataFrame is empty, return 0
    if dataframe.empty:
        warning("The DataFrame is empty. No positions to show.")
        return 0  # Indicating no balance found

    # Ensure 'Mint Address' column is treated as string for reliable comparison
    dataframe['Mint Address'] = dataframe['Mint Address'].astype(str)

    # Check if the token mint address exists in the DataFrame
    if dataframe['Mint Address'].isin([token_mint_address]).any():
        # Get the balance for the specified token
        balance = dataframe.loc[dataframe['Mint Address'] == token_mint_address, 'Amount'].iloc[0]
        return balance
    else:
        # If the token mint address is not found in the DataFrame, return a message indicating so
        warning("Token mint address not found in the wallet.")
        return 0  # Indicating no balance found


def get_decimals(token_mint_address):
    import requests
    import base64
    import json
    # Solana Mainnet RPC endpoint
    url = "https://api.mainnet-beta.solana.com/"
    headers = {"Content-Type": "application/json"}

    # Request payload to fetch account information
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [
            token_mint_address,
            {
                "encoding": "jsonParsed"
            }
        ]
    })

    # Make the request to Solana RPC
    response = requests.post(url, headers=headers, data=payload)
    response_json = response.json()

    # Parse the response to extract the number of decimals
    decimals = response_json['result']['value']['data']['parsed']['info']['decimals']
    #print(f"Decimals for {token_mint_address[-4:]} token: {decimals}")

    return decimals

def pnl_close(token_mint_address):
    """
    Check if a position should be closed based on profit or loss thresholds
    """
    info(f'Checking if it\'s time to exit for {token_mint_address[:4]}...')
    
    # Get current position
    balance = get_position(token_mint_address)

    # Get current price of token
    price = token_price(token_mint_address)

    usd_value = balance * price

    tp = sell_at_multiple * USDC_SIZE
    sl = ((1+stop_loss_percentage) * USDC_SIZE)
    sell_size = balance
    decimals = get_decimals(token_mint_address)

    sell_size = int(sell_size * 10 **decimals)

    while usd_value > tp:
        info(f'Token {token_mint_address[:4]} value is {usd_value} and take profit is {tp} - closing position')
        try:
            market_sell(token_mint_address, sell_size)
            info(f'Executed order for {token_mint_address[:4]} selling {sell_size}')
            time.sleep(2)
            market_sell(token_mint_address, sell_size)
            info(f'Executed order for {token_mint_address[:4]} selling {sell_size}')
            time.sleep(2)
            market_sell(token_mint_address, sell_size)
            info(f'Executed order for {token_mint_address[:4]} selling {sell_size}')
            time.sleep(15)
        except Exception as e:
            error(f'Order error: {str(e)} - trying again')
            time.sleep(2)

        balance = get_position(token_mint_address)
        price = token_price(token_mint_address)
        usd_value = balance * price
        tp = sell_at_multiple * USDC_SIZE
        sell_size = balance
        sell_size = int(sell_size * 10 **decimals)
        debug(f'USD Value is {usd_value} | TP is {tp}')

    # Check for stop loss condition
    if usd_value != 0:
        while usd_value < sl and usd_value > 0:
            sell_size = balance
            sell_size = int(sell_size * 10 **decimals)

            warning(f'Token {token_mint_address[:4]} value is {usd_value} and stop loss is {sl} - closing position at a loss')
            try:
                market_sell(token_mint_address, sell_size)
                info(f'Executed order for {token_mint_address[:4]} selling {sell_size}')
                time.sleep(1)
                market_sell(token_mint_address, sell_size)
                info(f'Executed order for {token_mint_address[:4]} selling {sell_size}')
                time.sleep(1)
                market_sell(token_mint_address, sell_size)
                info(f'Executed order for {token_mint_address[:4]} selling {sell_size}')
                time.sleep(15)
            except Exception as e:
                error(f'Order error: {str(e)} - trying again')

            balance = get_position(token_mint_address)
            price = token_price(token_mint_address)
            usd_value = balance * price
            tp = sell_at_multiple * USDC_SIZE
            sl = ((1+stop_loss_percentage) * USDC_SIZE)
            sell_size = balance

            sell_size = int(sell_size * 10 **decimals)
            debug(f'Balance: {balance}, Price: {price}, USD Value: {usd_value}, TP: {tp}, Sell size: {sell_size}, Decimals: {decimals}', file_only=True)

            # Break the loop if usd_value is 0
            if usd_value == 0:
                info(f'Successfully closed {token_mint_address[:4]} position - adding to do not overtrade list')
                with open('dont_overtrade.txt', 'a') as file:
                    file.write(token_mint_address + '\n')
                break
        else:
            debug(f'Token {token_mint_address[:4]} value is {usd_value} and take profit is {tp} - not closing')
    else:
        debug(f'Token {token_mint_address[:4]} value is {usd_value} and take profit is {tp} - not closing')

def chunk_kill(token_address, pct_each_chunk=30):
    """
    Sell a token position in chunks to minimize price impact
    
    Args:
        token_address (str): Token address to sell
        pct_each_chunk (int): Percentage of remaining position to sell in each chunk
        
    Returns:
        bool: True if position was fully exited, False otherwise
    """
    try:
        # Get initial position
        token_amount = get_token_balance(token_address)
        if token_amount <= 0:
            warning("No position found to exit")
            return False
        
        # Get current price and value
        price = token_price(token_address)
        current_usd_value = token_amount * price
        
        # Log initial position
        info(f"Initial position: {token_amount:.2f} tokens (${current_usd_value:.2f})")
        
        # Calculate chunk size
        chunk_size = token_amount * (pct_each_chunk / 100)
        
        # Log chunk strategy
        info(f"Splitting remaining position into chunks of {chunk_size:.2f} tokens")
        
        # Execute 3 chunks
        for i in range(3):
            try:
                info(f"Executing sell chunk {i+1}/3...")
                market_sell(token_address, chunk_size)
                info(f"Sell chunk {i+1}/3 complete")
            except Exception as e:
                error(f"Error in sell chunk: {str(e)}")
                continue
                
        # Check if position is fully closed
        token_amount = get_token_balance(token_address)
        if token_amount <= 0:
            info("Position successfully closed!")
            return True
            
        # Log remaining position
        current_usd_value = token_amount * price
        info(f"Remaining position: {token_amount:.2f} tokens (${current_usd_value:.2f})")
        
        # Continue to close if more than 5% of initial position remains
        info("Position still open - continuing to close...")
        
        # Check final status
        if get_token_balance(token_address) <= 0:
            info("Position successfully closed!")
            return True
        
        return False
        
    except Exception as e:
        error(f"Error during position exit: {str(e)}")
        return False

def sell_token(token_mint_address, amount, slippage):
    """Sell a specific amount of tokens"""
    try:
        info(f"Selling {amount:.2f} tokens...")
        market_sell(token_mint_address, int(amount), slippage)
        return True
    except Exception as e:
        error(f"Error selling token: {str(e)}")
        return False

def kill_switch(token_mint_address):
    """Close a position completely"""
    # Check if the token is excluded from trading
    if token_mint_address in EXCLUDED_TOKENS:
        warning(f"Skipping kill switch for excluded token at {token_mint_address}")
        return
            
    # Check if we're already in a cooldown period for this token
    dont_trade_file = 'dont_overtrade.txt'
    dont_trade_list = []
    if os.path.exists(dont_trade_file):
        with open(dont_trade_file, 'r') as file:
            dont_trade_list = [line.strip() for line in file.readlines()]
            
    if token_mint_address in dont_trade_list:
        warning(f"Token {token_mint_address[:8]} in cooldown period, skipping")
        return

    # Get current position
    balance = get_position(token_mint_address)
    price = token_price(token_mint_address)
    usd_value = balance * price

    if usd_value <= 0.1:
        debug(f"No significant position for {token_mint_address[:8]} (${usd_value:.2f})")
        return
        
    info(f"Closing position for {token_mint_address[:8]} worth ${usd_value:.2f}")
    
    # Calculate sell size with proper precision
    decimals = get_decimals(token_mint_address)
    sell_size = balance
    sell_size = int(sell_size * 10**decimals)
    
    try:
        # Execute sell orders
        for i in range(3):  # Try multiple orders for better execution
            market_sell(token_mint_address, sell_size, slippage)
            info(f"Order {i+1}/3 submitted for {token_mint_address[:8]} selling {sell_size}")
            time.sleep(1)
        
        # Wait for orders to settle
            time.sleep(15)

        # Check if position is closed
        remaining = get_position(token_mint_address)
        if remaining > 0:
            warning(f"Position not fully closed, remaining: {remaining}")
            # Try one more time with updated balance
            sell_size = int(remaining * 10**decimals)
            market_sell(token_mint_address, sell_size, slippage)
        
        # Add to cooldown list
        with open(dont_trade_file, 'a') as file:
            file.write(token_mint_address + '\n')
            
        info(f"Position closed for {token_mint_address[:8]}")
        
    except Exception as e:
        error(f"Error in kill switch: {str(e)}")
        
    # Final check
    final_balance = get_position(token_mint_address)
    if final_balance > 0:
        warning(f"Failed to fully close position for {token_mint_address[:8]}, remaining: {final_balance}")
    else:
        info(f"Successfully closed position for {token_mint_address[:8]}")

def close_all_positions():
    """
    Close all open positions except for tokens in the dont_trade_list
    """
    # Get all positions
    open_positions = fetch_wallet_holdings_og(address)

    # Load the list of tokens that should not be traded
    dont_trade_list = EXCLUDED_TOKENS  # Start with excluded tokens
    
    # Add tokens from dont_overtrade.txt if it exists
    if os.path.exists('dont_overtrade.txt'):
        with open('dont_overtrade.txt', 'r') as file:
            dont_trade_list.extend([line.strip() for line in file.readlines()])
    
    info(f"Closing all positions except for {len(dont_trade_list)} excluded tokens")
    
    # Loop through all positions and close them
    for index, row in open_positions.iterrows():
        token_mint_address = row['Mint Address']

        # Check if the current token mint address is in the exclusion list
        if token_mint_address in dont_trade_list:
            debug(f"Skipping excluded token at {token_mint_address[:8]}")
            continue  # Skip this token

        info(f"Closing position for {token_mint_address[:8]}")
        kill_switch(token_mint_address)
    
    info("All eligible positions closed")

def delete_dont_overtrade_file():
    """
    Delete the dont_overtrade.txt file to reset token cooldown periods
    """
    if os.path.exists('dont_overtrade.txt'):
        os.remove('dont_overtrade.txt')
        info('dont_overtrade.txt has been deleted')
    else:
        debug('The dont_overtrade.txt file does not exist')

def supply_demand_zones(token_address, timeframe, limit):
    """
    Calculate supply and demand zones for a token
    """
    info('Starting supply and demand zone calculations')

    sd_df = pd.DataFrame()

    time_from, time_to = get_time_range()

    df = get_data(token_address, time_from, time_to, timeframe)

    # only keep the data for as many bars as limit says
    df = df[-limit:]

    # Calculate support and resistance, excluding the last two rows for the calculation
    if len(df) > 2:  # Check if DataFrame has more than 2 rows to avoid errors
        df['support'] = df[:-2]['Close'].min()
        df['resis'] = df[:-2]['Close'].max()
    else:  # If DataFrame has 2 or fewer rows, use the available 'close' prices for calculation
        df['support'] = df['Close'].min()
        df['resis'] = df['Close'].max()

    supp = df.iloc[-1]['support']
    resis = df.iloc[-1]['resis']

    df['supp_lo'] = df[:-2]['Low'].min()
    supp_lo = df.iloc[-1]['supp_lo']

    df['res_hi'] = df[:-2]['High'].max()
    res_hi = df.iloc[-1]['res_hi']

    sd_df[f'dz'] = [supp_lo, supp]
    sd_df[f'sz'] = [res_hi, resis]

    debug('Supply and demand zones calculated', file_only=True)
    debug(sd_df.to_string(), file_only=True)

    return sd_df


def elegant_entry(symbol, buy_under):
    """
    Place orders to enter a position when price is below a threshold
    """
    pos = get_position(symbol)
    price = token_price(symbol)
    pos_usd = pos * price
    size_needed = usd_size - pos_usd
    if size_needed > max_usd_order_size: 
        chunk_size = max_usd_order_size
    else: 
        chunk_size = size_needed

    chunk_size = int(chunk_size * 10**6)
    chunk_size = str(chunk_size)

    debug(f'Chunk size: {chunk_size}')

    if pos_usd > (.97 * usd_size):
        info('Position filled')
        return

    # Debug information
    debug(f'Position: {round(pos,2)}, Price: {round(price,8)}, USD Value: ${round(pos_usd,2)}')
    debug(f'Buy threshold: {buy_under}')
    
    while pos_usd < (.97 * usd_size) and (price < buy_under):
        info(f'Position: {round(pos,2)}, Price: {round(price,8)}, USD Value: ${round(pos_usd,2)}')

        try:
            for i in range(orders_per_open):
                market_buy(symbol, chunk_size, slippage)
                info(f'Chunk buy submitted for {symbol[:4]}, size: {chunk_size}')
                time.sleep(1)

            time.sleep(tx_sleep)

            pos = get_position(symbol)
            price = token_price(symbol)
            pos_usd = pos * price
            size_needed = usd_size - pos_usd
            if size_needed > max_usd_order_size: 
                chunk_size = max_usd_order_size
            else: 
                chunk_size = size_needed
            chunk_size = int(chunk_size * 10**6)
            chunk_size = str(chunk_size)

        except Exception as e:
            try:
                warning(f'Order failed, retrying in 30 seconds - Error: {str(e)}')
                time.sleep(30)
                for i in range(orders_per_open):
                    market_buy(symbol, chunk_size, slippage)
                    info(f'Retry chunk buy submitted for {symbol[:4]}, size: {chunk_size}')
                    time.sleep(1)

                time.sleep(tx_sleep)
                pos = get_position(symbol)
                price = token_price(symbol)
                pos_usd = pos * price
                size_needed = usd_size - pos_usd
                if size_needed > max_usd_order_size: 
                    chunk_size = max_usd_order_size
                else: 
                    chunk_size = size_needed
                chunk_size = int(chunk_size * 10**6)
                chunk_size = str(chunk_size)

            except Exception as e:
                error(f'Final error in buy process: {str(e)} - manual intervention needed')
                time.sleep(10)
                break

        pos = get_position(symbol)
        price = token_price(symbol)
        pos_usd = pos * price
        size_needed = usd_size - pos_usd

def breakout_entry(symbol, BREAKOUT_PRICE):
    """
    Place orders to enter a position when price breaks above a threshold
    """
    pos = get_position(symbol)
    price = token_price(symbol)
    pos_usd = pos * price
    size_needed = usd_size - pos_usd
    if size_needed > max_usd_order_size: 
        chunk_size = max_usd_order_size
    else: 
        chunk_size = size_needed

    chunk_size = int(chunk_size * 10**6)
    chunk_size = str(chunk_size)

    debug(f'Chunk size: {chunk_size}')

    if pos_usd > (.97 * usd_size):
        info('Position filled')
        return

    # Debug information
    debug(f'Position: {round(pos,2)}, Price: {round(price,8)}, USD Value: ${round(pos_usd,2)}')
    debug(f'Breakout price: {BREAKOUT_PRICE}')
    
    while pos_usd < (.97 * usd_size) and (price > BREAKOUT_PRICE):
        info(f'Position: {round(pos,2)}, Price: {round(price,8)}, USD Value: ${round(pos_usd,2)}')

        try:
            for i in range(orders_per_open):
                market_buy(symbol, chunk_size, slippage)
                info(f'Chunk buy submitted for {symbol[:4]}, size: {chunk_size}')
                time.sleep(1)

            time.sleep(tx_sleep)

            pos = get_position(symbol)
            price = token_price(symbol)
            pos_usd = pos * price
            size_needed = usd_size - pos_usd
            if size_needed > max_usd_order_size: 
                chunk_size = max_usd_order_size
            else: 
                chunk_size = size_needed
            chunk_size = int(chunk_size * 10**6)
            chunk_size = str(chunk_size)

        except Exception as e:
            try:
                warning(f'Order failed, retrying in 30 seconds - Error: {str(e)}')
                time.sleep(30)
                for i in range(orders_per_open):
                    market_buy(symbol, chunk_size, slippage)
                    info(f'Retry chunk buy submitted for {symbol[:4]}, size: {chunk_size}')
                    time.sleep(1)

                time.sleep(tx_sleep)
                pos = get_position(symbol)
                price = token_price(symbol)
                pos_usd = pos * price
                size_needed = usd_size - pos_usd
                if size_needed > max_usd_order_size: 
                    chunk_size = max_usd_order_size
                else: 
                    chunk_size = size_needed
                chunk_size = int(chunk_size * 10**6)
                chunk_size = str(chunk_size)

            except Exception as e:
                error(f'Final error in buy process: {str(e)} - manual intervention needed')
                time.sleep(10)
                break

        pos = get_position(symbol)
        price = token_price(symbol)
        pos_usd = pos * price
        size_needed = usd_size - pos_usd
        if size_needed > max_usd_order_size: 
            chunk_size = max_usd_order_size
        else: 
            chunk_size = size_needed
        chunk_size = int(chunk_size * 10**6)
        chunk_size = str(chunk_size)

def ai_entry(symbol, amount):
    """AI agent entry function for Moon Dev's trading system"""
    info("AI Trading Agent initiating position entry")
    
    # amount passed in is the target allocation (up to 30% of usd_size)
    target_size = amount  # This could be up to $3 (30% of $10)
    
    pos = get_position(symbol)
    price = token_price(symbol)
    pos_usd = pos * price
    
    info(f"Target allocation: ${target_size:.2f} USD (max 30% of ${usd_size})")
    info(f"Current position: ${pos_usd:.2f} USD")
    
    # Check if we're already at or above target
    if pos_usd >= (target_size * 0.97):
        info("Position already at or above target size")
        return
        
    # Calculate how much more we need to buy
    size_needed = target_size - pos_usd
    if size_needed <= 0:
        info("No additional size needed")
        return
        
    # For order execution, we'll chunk into max_usd_order_size pieces
    if size_needed > max_usd_order_size: 
        chunk_size = max_usd_order_size
    else: 
        chunk_size = size_needed

    chunk_size = int(chunk_size * 10**6)
    chunk_size = str(chunk_size)
    
    info(f"Entry chunk size: {chunk_size} (chunking ${size_needed:.2f} into ${max_usd_order_size:.2f} orders)")

    while pos_usd < (target_size * 0.97):
        info(f"AI Agent executing entry for {symbol[:8]}...")
        debug(f"Position: {round(pos,2)} | Price: {round(price,8)} | USD Value: ${round(pos_usd,2)}")

        try:
            for i in range(orders_per_open):
                market_buy(symbol, chunk_size, slippage)
                info(f"AI Agent placed order {i+1}/{orders_per_open} for {symbol[:8]}")
                time.sleep(1)

            time.sleep(tx_sleep)
            
            # Update position info
            pos = get_position(symbol)
            price = token_price(symbol)
            pos_usd = pos * price
            
            # Break if we're at or above target
            if pos_usd >= (target_size * 0.97):
                break
                
            # Recalculate needed size
            size_needed = target_size - pos_usd
            if size_needed <= 0:
                break
                
            # Determine next chunk size
            if size_needed > max_usd_order_size: 
                chunk_size = max_usd_order_size
            else: 
                chunk_size = size_needed
            chunk_size = int(chunk_size * 10**6)
            chunk_size = str(chunk_size)

        except Exception as e:
            try:
                warning("AI Agent retrying order in 30 seconds...")
                time.sleep(30)
                for i in range(orders_per_open):
                    market_buy(symbol, chunk_size, slippage)
                    info(f"AI Agent retry order {i+1}/{orders_per_open} for {symbol[:8]}")
                    time.sleep(1)

                time.sleep(tx_sleep)
                pos = get_position(symbol)
                price = token_price(symbol)
                pos_usd = pos * price
                
                if pos_usd >= (target_size * 0.97):
                    break
                    
                size_needed = target_size - pos_usd
                if size_needed <= 0:
                    break
                    
                if size_needed > max_usd_order_size: 
                    chunk_size = max_usd_order_size
                else: 
                    chunk_size = size_needed
                chunk_size = int(chunk_size * 10**6)
                chunk_size = str(chunk_size)

            except Exception as e:
                error("AI Agent encountered critical error, manual intervention needed")
                return

    info("AI Agent completed position entry")

def get_token_balance(token_address):
    """
    Get token balance for the configured wallet
    """
    try:
        # Check if address is configured
        if not address or address.strip() == "":
            warning("No wallet address configured, cannot get balance")
            return 0
            
        # Create RPC client
        http_client = Client(os.getenv("RPC_ENDPOINT", "https://api.mainnet-beta.solana.com"))
        
        # Handle SOL native token specially
        if token_address == "So11111111111111111111111111111111111111112":  # SOL
            try:
                response = http_client.get_balance(address)
                if hasattr(response, 'value') and response.value is not None:
                    # Convert from lamports to SOL
                    return float(response.value) / 1_000_000_000
                return 0
            except Exception as e:
                warning(f"Error getting SOL balance: {str(e)}")
                return 0
            
        # For SPL tokens, use BirdEye API which is more reliable
        try:
            birdeye_api_key = os.getenv("BIRDEYE_API_KEY", "")
            if not birdeye_api_key:
                warning("No BirdEye API key configured")
                return 0
                
            headers = {"X-API-KEY": birdeye_api_key}
            url = f"https://public-api.birdeye.so/public/tokenbalance?address={address}&mint={token_address}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                balance = data.get("data", {}).get("balance", 0)
                return float(balance)
            else:
                warning(f"Error fetching token balance from BirdEye: HTTP {response.status_code}")
                
        except Exception as e:
            warning(f"Error with BirdEye API: {str(e)}")
        
        # Fallback to direct RPC call if BirdEye fails
        try:
            # For SPL tokens, we need to find the token account first
            token_accounts_response = http_client.get_token_accounts_by_owner(
                address,
                {"mint": token_address}
            )
            
            if not hasattr(token_accounts_response, 'value') or not token_accounts_response.value:
                return 0  # No token account found
                
            # Get the token account address from the first account
            token_account = token_accounts_response.value[0].pubkey
            
            # Now get the balance
            token_info_response = http_client.get_token_account_balance(token_account)
            if not hasattr(token_info_response, 'value') or not token_info_response.value:
                return 0
                
            # Get the amount and decimals
            token_info = token_info_response.value
            amount = float(token_info.amount)
            decimals = token_info.decimals
            
            # Convert to human-readable format
            balance = amount / (10 ** decimals)
            return balance
        except Exception as e:
            warning(f"Error with RPC token balance: {str(e)}")
            return 0
            
    except Exception as e:
        error(f"Error getting token balance: {str(e)}")
        return 0

def partial_kill(token_mint_address, percentage, max_usd_order_size, slippage):
    """
    Sell a specific percentage of a token position
    
    Args:
        token_mint_address (str): The mint address of the token to sell
        percentage (float): The percentage of the position to sell (0.0-1.0)
        max_usd_order_size (float): Maximum USD size per order
        slippage (int): Slippage tolerance
        
    Returns:
        bool: True if successfully sold, False otherwise
    """
    try:
        info(f"Executing partial sell for {token_mint_address}")
        info(f"Selling {percentage*100:.1f}% of position")
        
        # Validate percentage
        if percentage <= 0 or percentage > 1:
            error(f"Invalid percentage: {percentage}. Must be between 0 and 1.")
            return False
            
        # Get token balance in lamports
        balance_info = get_position(token_mint_address)
        if balance_info is None:
            error(f"Could not fetch balance for {token_mint_address}")
            return False
            
        token_balance = balance_info.get("amount", 0)
        if token_balance <= 0:
            warning(f"No balance to sell for {token_mint_address}")
            return False
            
        # Calculate amount to sell
        amount_to_sell = token_balance * percentage
        decimals = get_decimals(token_mint_address)
        
        # Get USD value of token for logging
        token_price = n.token_price(token_mint_address)
        if token_price:
            usd_amount = (amount_to_sell / (10 ** decimals)) * token_price
            info(f"Selling {amount_to_sell / (10 ** decimals)} tokens (${usd_amount:.2f})")
        else:
            info(f"Selling {amount_to_sell / (10 ** decimals)} tokens (price unavailable)")
            
        # If selling more than 95%, just use the full chunk_kill function
        if percentage > 0.95:
            info("Percentage > 95%, using full chunk_kill instead")
            return chunk_kill(token_mint_address, max_usd_order_size, slippage)
            
        # For smaller amounts, sell the exact percentage
        # Calculate the sell amount in native units
        amount_in_native = int(amount_to_sell)
        
        # If amount is too small, don't proceed
        if amount_in_native <= 0:
            warning("Calculated amount to sell is too small")
            return False
            
        # Execute the sale using market_sell or in chunks if needed
        if usd_amount and usd_amount > max_usd_order_size:
            info(f"USD amount (${usd_amount:.2f}) exceeds max order size (${max_usd_order_size})")
            info(f"Splitting into multiple chunks")
            
            # Calculate how many chunks we need
            num_chunks = int(usd_amount / max_usd_order_size) + 1
            chunk_percentage = percentage / num_chunks
            
            # Execute sale in chunks
            success = True
            for i in range(num_chunks):
                info(f"Executing chunk {i+1}/{num_chunks}")
                chunk_amount = token_balance * chunk_percentage
                chunk_result = sell_token(token_mint_address, int(chunk_amount), slippage)
                if not chunk_result:
                    success = False
                time.sleep(1)  # Small delay between chunks
                
            return success
        else:
            # Sell in one go
            return sell_token(token_mint_address, amount_in_native, slippage)
            
    except Exception as e:
        error(f"Error in partial_kill: {str(e)}")
        return False

def stake_sol_marinade(amount):
    """
    Stake SOL using Marinade Finance
    
    Args:
        amount (float): Amount of SOL to stake
            
    Returns:
        str: Transaction ID if successful, None on failure
    """
    try:
        import base64
        from solders.keypair import Keypair
        from solders.transaction import VersionedTransaction
        from solana.rpc.api import Client
        from solana.rpc.types import TxOpts
        
        info(f"Staking {amount} SOL via Marinade Finance...")
            
        # Setup key and client
        key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
        http_client = Client(os.getenv("RPC_ENDPOINT"))
        
        # Define Marinade staking program
        marinade_program = "MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD"
        
        # Convert SOL amount to lamports
        lamports_amount = int(amount * 10**9)
        
        # Create transaction (simplified - need to use actual Marinade SDK or API)
        transaction_url = f"https://api.marinade.finance/v1/staking/deposit?amount={lamports_amount}&wallet={key.pubkey()}"
        
        # This is a placeholder - in a real implementation, you'd use the Marinade SDK
        # to create and sign the transaction properly
        response = requests.get(transaction_url, timeout=15)
                
        if response.status_code != 200:
            error(f"Failed to create staking transaction: HTTP {response.status_code}")
            return None
            
        transaction_data = response.json()
        if "serializedTransaction" not in transaction_data:
            error("Invalid response from Marinade API")
            return None
            
        # Deserialize transaction
        serialized_tx = base64.b64decode(transaction_data["serializedTransaction"])
        tx = VersionedTransaction.from_bytes(serialized_tx)
        
        # Sign and send transaction
        signed_tx = VersionedTransaction(tx.message, [key])
        tx_id = http_client.send_raw_transaction(bytes(signed_tx), TxOpts(skip_preflight=True)).value
        
        info(f"Staking transaction sent! https://solscan.io/tx/{str(tx_id)}")
        return str(tx_id)
            
    except Exception as e:
        error(f"Error staking SOL: {str(e)}")
        return None

def market_buy(token, amount, slippage):
    """
    Buy a token with USDC using Jupiter API
    
    Args:
        token (str): The token address to buy
        amount (str or int): The amount of USDC to spend (in lamports/native units)
        slippage (int): Slippage tolerance in basis points (100 = 1%)
        
    Returns:
        str: Transaction ID if successful, None on failure which evaluates to False in conditionals
    """
    try:
        import requests
        import json
        import base64
        from solders.keypair import Keypair
        from solders.transaction import VersionedTransaction
        from solana.rpc.api import Client
        from solana.rpc.types import TxOpts

        KEY = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
        if not KEY:
            raise ValueError("SOLANA_PRIVATE_KEY not found in environment variables!")
            
        SLIPPAGE = slippage # 5000 is 50%, 500 is 5% and 50 is .5%
        QUOTE_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" # USDC

        http_client = Client(os.getenv("RPC_ENDPOINT"))
        if not http_client:
            raise ValueError("RPC_ENDPOINT not found in environment variables!")
            
        info(f"Preparing to buy token {token[:8]} with {amount} USDC")
        
        # Convert amount to string if it's not already
        if not isinstance(amount, str):
            amount = str(amount)
            
        # Get quote from Jupiter
        quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}&outputMint={token}&amount={amount}&slippageBps={SLIPPAGE}'
        quote_response = requests.get(quote_url, timeout=15)
        
        if quote_response.status_code != 200:
            error(f"Failed to get quote: HTTP {quote_response.status_code}")
            return None
            
        quote = quote_response.json()
        if not quote or "data" not in quote:
            error("Invalid quote response from Jupiter")
            return None
            
        # Create swap transaction
        try:
            txRes = requests.post(
                'https://quote-api.jup.ag/v6/swap',
                headers={"Content-Type": "application/json"},
                timeout=15,
                json={
                    "quoteResponse": quote,
                    "userPublicKey": str(KEY.pubkey()),
                    "prioritizationFeeLamports": PRIORITY_FEE
                }
            )
            
            if txRes.status_code != 200:
                error(f"Failed to create swap transaction: HTTP {txRes.status_code}")
                return None
                
            tx_data = txRes.json()
            if not tx_data or "swapTransaction" not in tx_data:
                error("Invalid swap transaction response")
                return None
                
            swapTx = base64.b64decode(tx_data['swapTransaction'])
        except Exception as e:
            error(f"Error creating swap transaction: {str(e)}")
            return None
            
        # Sign and send transaction
        try:
            tx1 = VersionedTransaction.from_bytes(swapTx)
            tx = VersionedTransaction(tx1.message, [KEY])
            
            txId = http_client.send_raw_transaction(
                bytes(tx), 
                TxOpts(skip_preflight=True)
            ).value
            
            info(f"Buy transaction sent: https://solscan.io/tx/{str(txId)}")
            return str(txId)
        except Exception as e:
            error(f"Error sending transaction: {str(e)}")
            return None
            
    except Exception as e:
        error(f"Error in market_buy: {str(e)}")
        return None

def get_token_balance_usd(token_address, display_token_name=None):
    """
    Get the USD value of a token balance from your wallet
    
    Args:
        token_address (str): Token address to check
        display_token_name (str, optional): Custom name to display for the token
        
    Returns:
        float: USD value of the token balance
    """
    try:
        from web3 import Web3
        import json
        
        # Connect to an Ethereum node
        web3 = Web3(Web3.HTTPProvider(os.getenv("ETH_RPC_URL")))
        if not web3.is_connected():
            error("Failed to connect to Ethereum node")
            return 0
            
        # Get private key and derive address
        private_key = os.getenv("ETHEREUM_PRIVATE_KEY")
        if not private_key:
            error("Ethereum private key not found in environment variables")
            return 0
            
        account = web3.eth.account.from_key(private_key)
        wallet_address = account.address
        
        # ERC20 Token ABI for balance, decimals, and symbol
        token_abi = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}]')
        
        # Create contract instance
        token_contract = web3.eth.contract(address=token_address, abi=token_abi)
        
        # Get token balance
        balance = token_contract.functions.balanceOf(wallet_address).call()
        
        # Get token decimals and symbol
        try:
            decimals = token_contract.functions.decimals().call()
            token_symbol = token_contract.functions.symbol().call() if not display_token_name else display_token_name
        except Exception as e:
            warning(f"Could not get token details: {str(e)}")
            decimals = 18
            token_symbol = display_token_name if display_token_name else token_address[:8]
        
        # Convert to human-readable format
        balance_float = balance / (10 ** decimals)
        
        if balance_float == 0:
            info(f"No {token_symbol} balance found in wallet")
            return 0
            
        # Get token price
        token_price = get_token_price(token_address)
        if token_price is None or token_price == 0:
            warning(f"Could not get price for {token_symbol}")
            return 0
            
        # Calculate USD value
        usd_value = balance_float * token_price
        
        info(f"Balance: {balance_float:.4f} {token_symbol} = ${usd_value:.2f}")
        return usd_value
        
    except Exception as e:
        error(f"Error getting token balance in USD: {str(e)}")
        return 0

def check_balances_and_approve(token_address, eth_client=None):
    """
    Check balances and approve tokens for trading on Uniswap
    
    Args:
        token_address (str): The token address to check and approve
        eth_client: Optional Ethereum client
        
    Returns:
        bool: True if approved or already has allowance, False otherwise
    """
    try:
        if eth_client is None:
            from web3 import Web3
            web3 = Web3(Web3.HTTPProvider(os.getenv("ETH_RPC_URL")))
            eth_client = web3
        
        if eth_client is None:
            error("No Ethereum client available")
            return False
        
        # Uniswap V3 router address
        router_address = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"
        
        # Get private key
        private_key = os.getenv("ETHEREUM_PRIVATE_KEY")
        if not private_key:
            error("Ethereum private key not found in environment variables")
            return False
            
        # Get wallet address
        account = eth_client.eth.account.from_key(private_key)
        wallet_address = account.address
        
        # Get token contract
        token_abi = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"payable":true,"stateMutability":"payable","type":"fallback"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}]')
        token_contract = eth_client.eth.contract(address=token_address, abi=token_abi)
        
        # Check ETH balance
        eth_balance = eth_client.eth.get_balance(wallet_address)
        eth_balance_in_eth = eth_client.from_wei(eth_balance, 'ether')
        info(f"ETH Balance: {eth_balance_in_eth} ETH")
        
        # Check token balance
        try:
            token_balance = token_contract.functions.balanceOf(wallet_address).call()
            token_decimals = token_contract.functions.decimals().call()
            token_symbol = token_contract.functions.symbol().call()
            token_balance_formatted = token_balance / (10 ** token_decimals)
            info(f"Token Balance: {token_balance_formatted} {token_symbol}")
        except Exception as e:
            warning(f"Error getting token balance: {str(e)}")
            return False
        
        # Check allowance
        allowance = token_contract.functions.allowance(wallet_address, router_address).call()
        if allowance > 0:
            info(f"Token already approved with allowance: {allowance / (10 ** token_decimals)}")
            return True
            
        # If no allowance, approve max amount
        info("No allowance found, approving token for trading")
        max_amount = 2**256 - 1
        
        # Create approval transaction
        try:
            nonce = eth_client.eth.get_transaction_count(wallet_address)
            txn = token_contract.functions.approve(router_address, max_amount).build_transaction({
                'from': wallet_address,
                'gas': 100000,
                'gasPrice': eth_client.eth.gas_price,
                'nonce': nonce,
            })
            
            # Sign and send transaction
            signed_txn = eth_client.eth.account.sign_transaction(txn, private_key)
            tx_hash = eth_client.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_receipt = eth_client.eth.wait_for_transaction_receipt(tx_hash)
            
            if tx_receipt.status == 1:
                info(f"Approval successful: {eth_client.to_hex(tx_hash)}")
                return True
            else:
                error("Approval transaction failed")
                return False
                
        except Exception as e:
            error(f"Error approving token: {str(e)}")
            return False
            
    except Exception as e:
        error(f"Error in check_balances_and_approve: {str(e)}")
        return False

def uni_buy(token, amount, slippage=0.5):
    """
    Buy a token with ETH or USDC using Uniswap
    
    Args:
        token (str): The token address to buy
        amount (str or float): The amount of ETH/USDC to spend
        slippage (float): Slippage tolerance in percentage (0.5 = 0.5%)
        
    Returns:
        str: Transaction hash if successful, None on failure
    """
    try:
        import time
        from web3 import Web3

        # Setup web3
        web3 = Web3(Web3.HTTPProvider(os.getenv("ETH_RPC_URL")))
        if not web3.is_connected():
            error("Failed to connect to Ethereum node")
            return None

        # Setup account
        private_key = os.getenv("ETHEREUM_PRIVATE_KEY")
        if not private_key:
            error("Ethereum private key not found in environment variables")
            return None
            
        account = web3.eth.account.from_key(private_key)
        wallet_address = account.address
        
        # Uniswap V3 router address
        router_address = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"
        
        # WETH token address
        weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        
        # USDC token address
        usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        
        # Determine input token (ETH or USDC)
        if float(amount) < 10:  # Small amount likely means ETH
            input_token = weth_address
            input_amount = web3.to_wei(float(amount), 'ether')
            info(f"Buying with {amount} ETH")
        else:  # Larger amount likely means USDC
            input_token = usdc_address
            # USDC has 6 decimals
            input_amount = int(float(amount) * 10**6)
            info(f"Buying with {amount} USDC")
            
            # Check for approval
            approved = check_balances_and_approve(usdc_address, web3)
            if not approved:
                error("USDC not approved for trading")
                return None
        
        # Router ABI for exact input single
        router_abi = json.loads('[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct ISwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]')
        
        router_contract = web3.eth.contract(address=router_address, abi=router_abi)
        
        # Get token info
        token_contract = web3.eth.contract(
            address=token,
            abi=json.loads('[{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}]')
        )
        
        try:
            token_symbol = token_contract.functions.symbol().call()
            token_decimals = token_contract.functions.decimals().call()
            info(f"Token: {token_symbol} ({token_decimals} decimals)")
        except Exception as e:
            warning(f"Could not get token info: {str(e)}")
            token_symbol = token[:8]
            token_decimals = 18
        
        # Calculate minimum amount out with slippage
        # This is simplified - in a real implementation, you'd fetch the current price
        amountOutMinimum = 1  # This should be calculated based on current price and slippage
        
        # Set deadline 20 minutes from now
        deadline = int(time.time() + 1200)
        
        # Create swap parameters
        swap_params = {
            'tokenIn': input_token,
            'tokenOut': token,
            'fee': 3000,  # 0.3% fee tier
            'recipient': wallet_address,
            'deadline': deadline,
            'amountIn': input_amount,
            'amountOutMinimum': amountOutMinimum,
            'sqrtPriceLimitX96': 0
        }
        
        # Get transaction count for nonce
        nonce = web3.eth.get_transaction_count(wallet_address)
        
        # Get gas price
        gas_price = web3.eth.gas_price
        
        try:
            # If buying with ETH, we need to wrap it first
            if input_token == weth_address:
                # Create transaction
                tx = {
                    'from': wallet_address,
                    'to': router_address,
                    'value': input_amount,
                    'gas': 500000,  # Set appropriate gas limit
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'data': router_contract.encodeABI(fn_name='exactInputSingle', args=[swap_params])
                }
            else:
                # Create transaction
                tx = {
                    'from': wallet_address,
                    'to': router_address,
                    'value': 0,
                    'gas': 500000,  # Set appropriate gas limit
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'data': router_contract.encodeABI(fn_name='exactInputSingle', args=[swap_params])
                }
            
            # Sign transaction
            signed_tx = web3.eth.account.sign_transaction(tx, private_key)
            
            # Send transaction
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            info(f"Buy transaction sent: {web3.to_hex(tx_hash)}")
            
            # Wait for confirmation
            try:
                receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if receipt.status == 1:
                    info(f"Transaction confirmed: https://etherscan.io/tx/{web3.to_hex(tx_hash)}")
                    return web3.to_hex(tx_hash)
                else:
                    error("Transaction failed")
                    return None
            except Exception as e:
                warning(f"Transaction pending, could not get receipt: {str(e)}")
                return web3.to_hex(tx_hash)
                
        except Exception as e:
            error(f"Error sending transaction: {str(e)}")
            return None
            
    except Exception as e:
        error(f"Error in uni_buy: {str(e)}")
        return None

def get_token_price(token_address):
    """
    Get the current price of a token in USD using multiple price APIs
    
    Args:
        token_address (str): Token address to check
        
    Returns:
        float: Token price in USD or None if not found
    """
    try:
        # Try CoinGecko first
        try:
            import requests
            
            # Map address format to correct chain ID
            if token_address.startswith("0x"):  # Ethereum style address
                chain_id = "ethereum"
            else:  # Solana style address
                chain_id = "solana"
                
            url = f"https://api.coingecko.com/api/v3/simple/token_price/{chain_id}?contract_addresses={token_address}&vs_currencies=usd"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and token_address.lower() in data:
                    price = data[token_address.lower()].get('usd')
                    if price:
                        info(f"Got price from CoinGecko: ${price}")
                        return float(price)
        except Exception as e:
            warning(f"CoinGecko price fetch failed: {str(e)}")
        
        # Try 1inch API (for Ethereum tokens)
        if token_address.startswith("0x"):
            try:
                url = f"https://api.1inch.io/v5.0/1/quote?fromTokenAddress={token_address}&toTokenAddress=0xdAC17F958D2ee523a2206206994597C13D831ec7&amount=1000000000000000000"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and 'toTokenAmount' in data:
                        # USDT (0xdAC17F958D2ee523a2206206994597C13D831ec7) has 6 decimals
                        price = int(data['toTokenAmount']) / (10**6)
                        info(f"Got price from 1inch: ${price}")
                        return float(price)
            except Exception as e:
                warning(f"1inch price fetch failed: {str(e)}")
                
        # Try Uniswap if it's an Ethereum token
        if token_address.startswith("0x"):
            try:
                # This is simplified - in a real implementation you'd use the Uniswap SDK or Graph API
                warning("Uniswap price fetch not implemented yet")
            except Exception as e:
                warning(f"Uniswap price fetch failed: {str(e)}")
                
        # Try Jupiter if it's a Solana token
        if not token_address.startswith("0x"):
            try:
                from solana.rpc.api import Client
                
                # USDC mint
                usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                
                # Setup Solana client
                solana_client = Client(os.getenv("RPC_ENDPOINT"))
                
                # Jupiter API endpoint for quotes
                url = f"https://quote-api.jup.ag/v6/quote?inputMint={token_address}&outputMint={usdc_mint}&amount=1000000000&slippageBps=50"
                
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and 'data' in data and 'outAmount' in data['data']:
                        # USDC has 6 decimals
                        price = int(data['data']['outAmount']) / (10**6)
                        info(f"Got price from Jupiter: ${price}")
                        return float(price)
            except Exception as e:
                warning(f"Jupiter price fetch failed: {str(e)}")
                
        # If all methods fail
        warning(f"Could not get price for token {token_address[:8]}")
        return None
        
    except Exception as e:
        error(f"Error in get_token_price: {str(e)}")
        return None

def save_token_history(token_address, amount, price, trade_type="BUY", notes=""):
    """
    Save token trade history to CSV file
    
    Args:
        token_address (str): Token address
        amount (float): Amount of tokens
        price (float): Price in USD
        trade_type (str): Trade type (BUY or SELL)
        notes (str): Additional notes about the trade
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        import os
        import csv
        import datetime
        
        # Get the project root directory
        project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        
        # Create the history directory if it doesn't exist
        history_dir = os.path.join(project_root, "data", "history")
        os.makedirs(history_dir, exist_ok=True)
        
        # Create the history file path
        history_file = os.path.join(history_dir, "trade_history.csv")
        
        # Check if the file exists
        file_exists = os.path.isfile(history_file)
        
        # Get token symbol if available
        symbol = "Unknown"
        for addr, details in TOKEN_MAP.items():
            if addr == token_address:
                symbol = details[0]
                break
        
        # Get current timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate total value
        total_value = float(amount) * float(price)
        
        # Create a row for the CSV
        row = [timestamp, token_address, symbol, amount, price, total_value, trade_type, notes]
        
        # Write to the CSV file
        with open(history_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            
            # Write header if the file doesn't exist
            if not file_exists:
                writer.writerow(["Timestamp", "TokenAddress", "Symbol", "Amount", "Price", "TotalValue", "Type", "Notes"])
                
            # Write the data row
            writer.writerow(row)
            
        info(f"Trade history saved: {trade_type} {amount} {symbol} at ${price} (${total_value:.2f})")
        return True
        
    except Exception as e:
        error(f"Error saving token history: {str(e)}")
        return False

def unstake_sol_marinade(amount):
    """
    Unstake SOL from Marinade Finance
    
    Args:
        amount (float): Amount of mSOL to unstake
        
    Returns:
        str: Transaction ID if successful, None on failure
    """
    try:
        import base64
        from solders.keypair import Keypair
        from solders.transaction import VersionedTransaction
        from solana.rpc.api import Client
        from solana.rpc.types import TxOpts
        
        info(f"Unstaking {amount} SOL from Marinade Finance...")
        
        # Setup key and client
        key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
        http_client = Client(os.getenv("RPC_ENDPOINT"))
        
        # Define Marinade staking program
        marinade_program = "MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD"
        
        # Convert SOL amount to lamports
        lamports_amount = int(amount * 10**9)
        
        # Create transaction (simplified - need to use actual Marinade SDK or API)
        transaction_url = f"https://api.marinade.finance/v1/staking/liquid-unstake?amount={lamports_amount}&wallet={key.pubkey()}"
        
        # This is a placeholder - in a real implementation, you'd use the Marinade SDK
        # to create and sign the transaction properly
        response = requests.get(transaction_url, timeout=15)
        
        if response.status_code != 200:
            error(f"Failed to create unstaking transaction: HTTP {response.status_code}")
            return None
            
        transaction_data = response.json()
        if "serializedTransaction" not in transaction_data:
            error("Invalid response from Marinade API")
            return None
            
        # Deserialize transaction
        serialized_tx = base64.b64decode(transaction_data["serializedTransaction"])
        tx = VersionedTransaction.from_bytes(serialized_tx)
        
        # Sign and send transaction
        signed_tx = VersionedTransaction(tx.message, [key])
        tx_id = http_client.send_raw_transaction(bytes(signed_tx), TxOpts(skip_preflight=True)).value
        
        info(f"Unstaking transaction sent! https://solscan.io/tx/{str(tx_id)}")
        return str(tx_id)
        
    except Exception as e:
        error(f"Error unstaking SOL: {str(e)}")
        return None

def stake_sol_lido(amount):
    """
    Stake SOL using Lido Finance
    
    Args:
        amount (float): Amount of SOL to stake
        
    Returns:
        str: Transaction ID if successful, None on failure
    """
    try:
        import base64
        from solders.keypair import Keypair
        from solders.transaction import VersionedTransaction
        from solana.rpc.api import Client
        from solana.rpc.types import TxOpts
        
        info(f"Staking {amount} SOL via Lido...")
        
        # Setup key and client
        key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
        http_client = Client(os.getenv("RPC_ENDPOINT"))
        
        # Define Lido staking program
        lido_program = "CrX7kMhLC3cSsXJdT7JDgqrRVWGnUpX3gfEfxxU2NVLi"
        
        # Convert SOL amount to lamports
        lamports_amount = int(amount * 10**9)
        
        # Create transaction (simplified - need to use actual Lido SDK or API)
        transaction_url = f"https://api.solana.lido.fi/v1/stake?amount={lamports_amount}&wallet={key.pubkey()}"
        
        # This is a placeholder - in a real implementation, you'd use the Lido SDK
        # to create and sign the transaction properly
        response = requests.get(transaction_url, timeout=15)
        
        if response.status_code != 200:
            error(f"Failed to create staking transaction: HTTP {response.status_code}")
            return None
            
        transaction_data = response.json()
        if "serializedTransaction" not in transaction_data:
            error("Invalid response from Lido API")
            return None
            
        # Deserialize transaction
        serialized_tx = base64.b64decode(transaction_data["serializedTransaction"])
        tx = VersionedTransaction.from_bytes(serialized_tx)
        
        # Sign and send transaction
        signed_tx = VersionedTransaction(tx.message, [key])
        tx_id = http_client.send_raw_transaction(bytes(signed_tx), TxOpts(skip_preflight=True)).value
        
        info(f"Staking transaction sent! https://solscan.io/tx/{str(tx_id)}")
        return str(tx_id)
        
    except Exception as e:
        error(f"Error staking SOL: {str(e)}")
        return None

def unstake_sol_lido(amount):
    """
    Unstake SOL from Lido Finance
    
    Args:
        amount (float): Amount of stSOL to unstake
        
    Returns:
        str: Transaction ID if successful, None on failure
    """
    try:
        import base64
        from solders.keypair import Keypair
        from solders.transaction import VersionedTransaction
        from solana.rpc.api import Client
        from solana.rpc.types import TxOpts
        
        info(f"Unstaking {amount} SOL from Lido...")
        
        # Setup key and client
        key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
        http_client = Client(os.getenv("RPC_ENDPOINT"))
        
        # Define Lido staking program
        lido_program = "CrX7kMhLC3cSsXJdT7JDgqrRVWGnUpX3gfEfxxU2NVLi"
        
        # Convert SOL amount to lamports
        lamports_amount = int(amount * 10**9)
        
        # Create transaction (simplified - need to use actual Lido SDK or API)
        transaction_url = f"https://api.solana.lido.fi/v1/unstake?amount={lamports_amount}&wallet={key.pubkey()}"
        
        # This is a placeholder - in a real implementation, you'd use the Lido SDK
        # to create and sign the transaction properly
        response = requests.get(transaction_url, timeout=15)
        
        if response.status_code != 200:
            error(f"Failed to create unstaking transaction: HTTP {response.status_code}")
            return None
            
        transaction_data = response.json()
        if "serializedTransaction" not in transaction_data:
            error("Invalid response from Lido API")
            return None
            
        # Deserialize transaction
        serialized_tx = base64.b64decode(transaction_data["serializedTransaction"])
        tx = VersionedTransaction.from_bytes(serialized_tx)
        
        # Sign and send transaction
        signed_tx = VersionedTransaction(tx.message, [key])
        tx_id = http_client.send_raw_transaction(bytes(signed_tx), TxOpts(skip_preflight=True)).value
        
        info(f"Unstaking transaction sent! https://solscan.io/tx/{str(tx_id)}")
        return str(tx_id)
        
    except Exception as e:
        error(f"Error unstaking SOL: {str(e)}")
        return None

def stake_sol_jito(amount):
    """
    Stake SOL using Jito
    
    Args:
        amount (float): Amount of SOL to stake
        
    Returns:
        str: Transaction ID if successful, None on failure
    """
    try:
        info(f"Staking {amount} SOL via Jito...")
        
        # Jito doesn't have a direct staking API yet
        warning("Jito staking currently requires manual staking via their webapp")
        info("Visit https://jito.network/staking to stake your SOL")
        info("A direct API integration will be added in the future")
        
        return None
        
    except Exception as e:
        error(f"Error staking SOL: {str(e)}")
        return None