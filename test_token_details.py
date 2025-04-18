import sys
import time
import requests
import json
import os
from datetime import datetime
from src import nice_funcs as n

# Add parent directory to path to import the src module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import only the functions that exist in nice_funcs
from src.nice_funcs import (
    get_token_price,
    token_overview
)

# Define debug functions locally
DEBUG_LEVEL = 5  # Maximum debug level
DEBUG_TO_STDOUT = True  # Print debug to stdout

def debug(message, file_only=False):
    """Print debug messages"""
    if DEBUG_TO_STDOUT:
        print(f"DEBUG: {message}")

def set_debug_level(level):
    """Set debug level"""
    global DEBUG_LEVEL
    DEBUG_LEVEL = level
    print(f"Debug level set to {level}")

def set_debug_to_stdout(value):
    """Set debug output to stdout"""
    global DEBUG_TO_STDOUT
    DEBUG_TO_STDOUT = value
    print(f"Debug to stdout set to {value}")

# Define missing API functions locally
def get_real_time_price_birdeye(token_address):
    """Get token price from BirdEye API"""
    try:
        birdeye_api_key = os.getenv("BIRDEYE_API_KEY")
        if not birdeye_api_key:
            return None
            
        url = f"https://public-api.birdeye.so/public/price?address={token_address}"
        headers = {"X-API-KEY": birdeye_api_key}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                price = data.get("data", {}).get("value", 0)
                if price:
                    return float(price)
        return None
    except Exception as e:
        print(f"BirdEye API error: {str(e)}")
        return None

def get_real_time_price_jupiter(token_address):
    """Get token price from Jupiter API"""
    try:
        url = f"https://price.jup.ag/v4/price?ids={token_address}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and token_address in data['data']:
                price_data = data['data'][token_address]
                if price_data and 'price' in price_data and price_data['price'] is not None:
                    return float(price_data['price'])
        return None
    except Exception as e:
        print(f"Jupiter API error: {str(e)}")
        return None

def get_real_time_price_raydium_token(token_address):
    """Get token price from Raydium API"""
    try:
        url = f"https://api.raydium.io/v2/main/price?mint={token_address}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Try different response formats
            if 'data' in data and isinstance(data['data'], dict) and 'price' in data['data']:
                return float(data['data']['price'])
            elif token_address in data:
                return float(data[token_address])
            elif 'price' in data:
                return float(data['price'])
            
        return None
    except Exception as e:
        print(f"Raydium API error: {str(e)}")
        return None

def get_real_time_price_orca(token_address):
    """Get token price from Orca API"""
    try:
        url = "https://api.orca.so/v2/solana/tokens"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            tokens_data = response.json()
            
            # Handle different response formats
            if isinstance(tokens_data, dict) and 'data' in tokens_data and isinstance(tokens_data['data'], list):
                tokens_list = tokens_data['data']
            elif isinstance(tokens_data, list):
                tokens_list = tokens_data
            else:
                return None
            
            # Find the token with matching address
            for token in tokens_list:
                if token.get("address") == token_address:
                    # Try different price fields
                    if 'priceUsdc' in token and token['priceUsdc'] is not None:
                        return float(token['priceUsdc'])
                    elif 'price' in token and token['price'] is not None:
                        return float(token['price'])
                    elif 'value' in token and token['value'] is not None:
                        return float(token['value'])
            
        return None
    except Exception as e:
        print(f"Orca API error: {str(e)}")
        return None

def get_real_time_price_pumpfun(token_address):
    """Get token price from Pump.fun API"""
    try:
        # Use token_price function which is already imported
        price = n.get_real_time_price_pumpfun(token_address) if hasattr(n, 'get_real_time_price_pumpfun') else None
        return price
    except Exception as e:
        print(f"Pump.fun API error: {str(e)}")
        return None

# Define get_token_metadata function since it's not in nice_funcs
def get_token_metadata(token_address):
    """Get token metadata using token_overview function"""
    try:
        # Use token_overview function which returns metadata
        overview = token_overview(token_address)
        if overview and 'metadata' in overview:
            metadata = overview['metadata']
            return {
                'name': metadata.get('name', 'Unknown Token'),
                'symbol': metadata.get('symbol', 'UNK')
            }
        return {'name': 'Unknown Token', 'symbol': 'UNK'}
    except Exception as e:
        print(f"[FAILED] Error getting token metadata: {str(e)}")
        return {'name': 'Unknown Token', 'symbol': 'UNK'}

# List of token addresses to test
TEST_TOKENS = [
    "So11111111111111111111111111111111111111112",  # SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "7EYnhQoR9YM3N7UoaKRoA44Uy8JeaZV3qyouov87awMs",  # Pump Fun token
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # Raydium (RAY)
]

# Add some tokens that had issues
PROBLEM_TOKENS = [
    "8UaGbxQbV9v2rXxWSSyHV6LR3p6bNH6PaUVWbUnMB9Za",  # Sample problematic token
    "7qbRF6YsyGuLUVs6Y1q64bdVrfe4ZcUUz1JRdoVNUJnm",  # Another problematic token
    "BpqoekK7MwFrCBs7JV8vHFZv2BSFC6sGVsfuN6p3W44D",  # Another problematic token
]

def test_token_details():
    """Test specific token addresses that weren't working in the main app"""
    
    # Problem tokens from the logs
    problem_tokens = {
        "Token1": "VFdxjTdFzXrYr3ivWyf64NuXo9U7vdPK7AG7idnNZJV",
        "Token2": "CR2L1ob96JGWQkdFbt8rLwqdLLmqFwjcNGL2eFBn1RPt",
        "Token3": "2HdzfUiFWfZHZ544ynffeneuibbDK6biCdjovejr8ez9",
        "Token4": "C94njgTrKMQBmgqe23EGLrtPgfvcjWtqBBvGQ7Cjiank",
        "Token5": "7PU5nufFpFNhsbuiLH2JqhWkNvbuurNLY1X7tHttSBc9",
        "Token6": "DycFB5CXEvEngK1B7GVrXsj3Uz7GecQUZXeSVLsFpump",
    }
    
    print("Testing problem token addresses...")
    
    for name, address in problem_tokens.items():
        print(f"\n{'='*50}")
        print(f"Testing {name} ({address})...")
        print(f"{'='*50}")
        
        # Check with BirdEye API first (most comprehensive)
        print("\n1. BirdEye API Check:")
        try:
            birdeye_api_key = n.BIRDEYE_API_KEY
            url = f"https://public-api.birdeye.so/public/price?address={address}"
            headers = {"X-API-KEY": birdeye_api_key}
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    price = data.get("data", {}).get("value", 0)
                    print(f"[SUCCESS] Token found in BirdEye! Price: ${price}")
                else:
                    print(f"[FAILED] Token not found in BirdEye or has no price data")
                    print(f"Response: {json.dumps(data)[:300]}...")
            else:
                print(f"[FAILED] BirdEye API error: {response.status_code}")
        except Exception as e:
            print(f"[FAILED] Error checking BirdEye API: {str(e)}")
            
        # Check if token exists in Jupiter API
        print("\n2. Jupiter API Check:")
        try:
            jupiter_url = f"https://lite-api.jup.ag/price/v2?ids={address}"
            response = requests.get(jupiter_url, timeout=10)
            
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and address in data['data'] and data['data'][address] is not None:
                    price = data['data'][address].get('price')
                    print(f"[SUCCESS] Token found in Jupiter! Price: ${price}")
                else:
                    print(f"[FAILED] Token not found in Jupiter or has no price data")
            else:
                print(f"[FAILED] Jupiter API error: {response.status_code}")
        except Exception as e:
            print(f"[FAILED] Error checking Jupiter API: {str(e)}")
            
        # Check with Raydium API
        print("\n3. Raydium API Check:")
        try:
            raydium_url = f"https://api.raydium.io/v2/main/price?mint={address}"
            response = requests.get(raydium_url, timeout=10)
            
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                price_found = False
                
                if 'data' in data and isinstance(data['data'], dict) and 'price' in data['data']:
                    price = data['data']['price']
                    price_found = True
                    print(f"[SUCCESS] Token found in Raydium (format 1)! Price: ${price}")
                elif address in data:
                    price = data[address]
                    price_found = True
                    print(f"[SUCCESS] Token found in Raydium (format 2)! Price: ${price}")
                elif 'price' in data:
                    price = data['price']
                    price_found = True
                    print(f"[SUCCESS] Token found in Raydium (format 3)! Price: ${price}")
                    
                if not price_found:
                    print(f"[FAILED] Token not found in Raydium or has no price data")
                    print(f"Response structure: {list(data.keys())}")
            else:
                print(f"[FAILED] Raydium API error: {response.status_code}")
        except Exception as e:
            print(f"[FAILED] Error checking Raydium API: {str(e)}")
            
        # Check Orca API
        print("\n4. Orca API Check:")
        try:
            orca_url = f"https://api.orca.so/v2/solana/tokens"
            response = requests.get(orca_url, timeout=10)
            
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                tokens_data = response.json()
                
                # Handle different response formats
                if isinstance(tokens_data, dict) and 'data' in tokens_data and isinstance(tokens_data['data'], list):
                    tokens_list = tokens_data['data']
                    print(f"Found {len(tokens_list)} tokens in Orca response (new format)")
                elif isinstance(tokens_data, list):
                    tokens_list = tokens_data
                    print(f"Found {len(tokens_list)} tokens in Orca response (old format)")
                else:
                    print(f"Unexpected Orca API response format: {type(tokens_data)}")
                    tokens_list = []
                
                # Find the token with matching address
                token_found = False
                for token in tokens_list:
                    if token.get("address") == address:
                        token_found = True
                        token_name = token.get("metadata", {}).get("name", "Unknown")
                        token_symbol = token.get("metadata", {}).get("symbol", "UNK")
                        print(f"[SUCCESS] Token found in Orca! Name: {token_name}, Symbol: {token_symbol}")
                        
                        # Try different price fields
                        if 'priceUsdc' in token and token['priceUsdc'] is not None:
                            price = token['priceUsdc']
                            print(f"[SUCCESS] Price (priceUsdc): ${price}")
                        elif 'price' in token and token['price'] is not None:
                            price = token['price']
                            print(f"[SUCCESS] Price (price): ${price}")
                        elif 'value' in token and token['value'] is not None:
                            price = token['value']
                            print(f"[SUCCESS] Price (value): ${price}")
                        else:
                            print("[UNKNOWN] Token found but no price available")
                        break
                
                if not token_found:
                    print(f"[FAILED] Token not found in Orca token list")
            else:
                print(f"[FAILED] Orca API error: {response.status_code}")
        except Exception as e:
            print(f"[FAILED] Error checking Orca API: {str(e)}")
            
        # Try getting a swap quote (last resort)
        print("\n5. Jupiter Swap Quote Check:")
        try:
            # Use USDC as output token
            usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            url = f"https://quote-api.jup.ag/v6/quote?inputMint={address}&outputMint={usdc_address}&amount=1000000000&slippageBps=50"
            response = requests.get(url, timeout=10)
            
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                
                if "outAmount" in data and data.get("outAmount") and "inAmount" in data and data.get("inAmount"):
                    out_amount = float(data.get("outAmount")) / 1000000  # USDC decimals is 6
                    in_amount = float(data.get("inAmount")) / 1000000000  # Assuming 9 decimals
                    price = out_amount / in_amount
                    print(f"[SUCCESS] Got swap quote! Calculated price: ${price}")
                    print(f"   outAmount: {data.get('outAmount')}, inAmount: {data.get('inAmount')}")
                else:
                    print(f"[FAILED] Could not get meaningful swap quote")
                    print(f"Response data keys: {list(data.keys())}")
            else:
                print(f"[FAILED] Jupiter quote API error: {response.status_code}")
                if response.status_code == 400:
                    print("   This usually means the token doesn't have a trading pair with USDC")
                try:
                    error_data = response.json()
                    print(f"   Error message: {error_data.get('error', 'No error message')}")
                except:
                    pass
        except Exception as e:
            print(f"[FAILED] Error checking Jupiter quote API: {str(e)}")
            
        # Check SPL Token Registry
        print("\n6. Check Solana token registry:")
        try:
            url = f"https://cdn.jsdelivr.net/gh/solana-labs/token-list@main/src/tokens/solana.tokenlist.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                token_list = response.json()
                tokens = token_list.get("tokens", [])
                
                token_found = False
                for token in tokens:
                    if token.get("address") == address:
                        token_found = True
                        print(f"[SUCCESS] Token found in Solana token registry!")
                        print(f"   Name: {token.get('name')}")
                        print(f"   Symbol: {token.get('symbol')}")
                        print(f"   Decimals: {token.get('decimals')}")
                        print(f"   Tags: {token.get('tags', [])}")
                        break
                
                if not token_found:
                    print(f"[FAILED] Token not found in official Solana token registry")
                    print(f"   This might be an unofficial/new token or a fake token")
            else:
                print(f"[FAILED] Error fetching Solana token registry: {response.status_code}")
        except Exception as e:
            print(f"[FAILED] Error checking Solana token registry: {str(e)}")
        
        # Summary
        print("\n7. Final verdict:")
        price = n.token_price(address, force_refresh=True)
        if price is not None and price > 0.00000001:
            print(f"[SUCCESS] Successfully obtained price from our fallback system: ${price}")
        else:
            print(f"[FAILED] Could not obtain price from ANY source, including all fallbacks")
            print("   Possible reasons:")
            print("   1. Token has no liquidity or trading pairs")
            print("   2. Token might be very new or not listed on DEXes")
            print("   3. Token might be a fake/scam token")
            print("   4. Token might require on-chain RPC queries to get price")

def check_token(token_address):
    """Run a comprehensive check on a single token address."""
    print(f"\nTesting token address: {token_address}")
    
    # Check metadata first
    print("\nFetching token metadata...")
    try:
        metadata = get_token_metadata(token_address)
        if metadata and 'name' in metadata and 'symbol' in metadata:
            print(f"[SUCCESS] Token metadata: {metadata['name']} ({metadata['symbol']})")
        else:
            print(f"[FAILED] Could not retrieve metadata for {token_address}")
    except Exception as e:
        print(f"[FAILED] Error retrieving metadata: {str(e)}")
    
    # Try getting price from different sources individually
    print("\nTesting BirdEye API...")
    try:
        price = get_real_time_price_birdeye(token_address)
        if price:
            print(f"[SUCCESS] BirdEye price: ${price}")
        else:
            print(f"[FAILED] BirdEye returned no price")
    except Exception as e:
        print(f"[FAILED] BirdEye API error: {str(e)}")
    
    print("\nTesting Jupiter API...")
    try:
        price = get_real_time_price_jupiter(token_address)
        if price:
            print(f"[SUCCESS] Jupiter price: ${price}")
        else:
            print(f"[FAILED] Jupiter returned no price")
    except Exception as e:
        print(f"[FAILED] Jupiter API error: {str(e)}")
    
    print("\nTesting Raydium API...")
    try:
        price = get_real_time_price_raydium_token(token_address)
        if price:
            print(f"[SUCCESS] Raydium price: ${price}")
        else:
            print(f"[FAILED] Raydium returned no price")
    except Exception as e:
        print(f"[FAILED] Raydium API error: {str(e)}")
    
    print("\nTesting Orca API...")
    try:
        price = get_real_time_price_orca(token_address)
        if price:
            print(f"[SUCCESS] Orca price: ${price}")
        else:
            print(f"[FAILED] Orca returned no price")
    except Exception as e:
        print(f"[FAILED] Orca API error: {str(e)}")

    print("\nTesting Pump.fun API...")
    try:
        price = get_real_time_price_pumpfun(token_address)
        if price:
            print(f"[SUCCESS] Pump.fun price: ${price}")
        else:
            print(f"[FAILED] Pump.fun returned no price")
    except Exception as e:
        print(f"[FAILED] Pump.fun API error: {str(e)}")
    
    # Test the main get_token_price function which tries all sources
    print("\nTesting combined price fetching...")
    try:
        price = get_token_price(token_address)
        if price and price != "UNK":
            print(f"[SUCCESS] Combined price fetching returned: ${price}")
        else:
            print(f"[FAILED] Combined price fetching failed, returned: {price}")
    except Exception as e:
        print(f"[FAILED] Combined price fetching error: {str(e)}")
    
    print("\n" + "-"*50)

def main():
    """Main function to test token details functionality."""
    print("Starting token details test...\n")
    
    # Test standard tokens
    for token in TEST_TOKENS:
        check_token(token)
    
    # Test problematic tokens
    print("\n=== TESTING PROBLEMATIC TOKENS ===\n")
    for token in PROBLEM_TOKENS:
        check_token(token)

def test_specific_token(token_address):
    """Run a focused test on a single token address with maximum debugging."""
    print(f"\n=== DETAILED API TESTING FOR TOKEN: {token_address} ===\n")
    
    # Print current time
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get metadata for context
    try:
        metadata = get_token_metadata(token_address)
        if metadata and 'name' in metadata and 'symbol' in metadata:
            print(f"Token identified as: {metadata['name']} ({metadata['symbol']})")
        else:
            print(f"Could not identify token {token_address}")
    except Exception as e:
        print(f"Error retrieving metadata: {str(e)}")
    
    # Test each price API in sequence with detailed debugging
    
    print("\n--- BirdEye API Test ---")
    birdeye_start = time.time()
    birdeye_price = get_real_time_price_birdeye(token_address)
    birdeye_time = time.time() - birdeye_start
    print(f"BirdEye API response time: {birdeye_time:.2f} seconds")
    print(f"BirdEye price result: {birdeye_price}")
    
    print("\n--- Jupiter API Test ---")
    jupiter_start = time.time()
    jupiter_price = get_real_time_price_jupiter(token_address)
    jupiter_time = time.time() - jupiter_start
    print(f"Jupiter API response time: {jupiter_time:.2f} seconds")
    print(f"Jupiter price result: {jupiter_price}")
    
    print("\n--- Raydium API Test ---")
    raydium_start = time.time()
    raydium_price = get_real_time_price_raydium_token(token_address)
    raydium_time = time.time() - raydium_start
    print(f"Raydium API response time: {raydium_time:.2f} seconds")
    print(f"Raydium price result: {raydium_price}")
    
    print("\n--- Orca API Test ---")
    orca_start = time.time()
    orca_price = get_real_time_price_orca(token_address)
    orca_time = time.time() - orca_start
    print(f"Orca API response time: {orca_time:.2f} seconds")
    print(f"Orca price result: {orca_price}")
    
    print("\n--- Pump.fun API Test ---")
    pumpfun_start = time.time()
    pumpfun_price = get_real_time_price_pumpfun(token_address)
    pumpfun_time = time.time() - pumpfun_start
    print(f"Pump.fun API response time: {pumpfun_time:.2f} seconds")
    print(f"Pump.fun price result: {pumpfun_price}")
    
    print("\n--- Combined Price Test ---")
    combined_start = time.time()
    combined_price = get_token_price(token_address)
    combined_time = time.time() - combined_start
    print(f"Combined price function response time: {combined_time:.2f} seconds")
    print(f"Combined price result: {combined_price}")
    
    # Summary
    print("\n=== RESULTS SUMMARY ===")
    print(f"Token: {token_address}")
    if metadata and 'name' in metadata and 'symbol' in metadata:
        print(f"Name: {metadata['name']} ({metadata['symbol']})")
    print(f"BirdEye: ${birdeye_price if birdeye_price else 'None'} ({birdeye_time:.2f}s)")
    print(f"Jupiter: ${jupiter_price if jupiter_price else 'None'} ({jupiter_time:.2f}s)")
    print(f"Raydium: ${raydium_price if raydium_price else 'None'} ({raydium_time:.2f}s)")
    print(f"Orca: ${orca_price if orca_price else 'None'} ({orca_time:.2f}s)")
    print(f"Pump.fun: ${pumpfun_price if pumpfun_price else 'None'} ({pumpfun_time:.2f}s)")
    print(f"Combined: ${combined_price if combined_price and combined_price != 'UNK' else 'None'} ({combined_time:.2f}s)")
    print("\n" + "="*50)

if __name__ == "__main__":
    # If an argument is provided, test that specific token
    if len(sys.argv) > 1:
        test_specific_token(sys.argv[1])
    else:
        main() 