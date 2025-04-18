import requests
import json
import time
import os
from datetime import datetime

def load_tokens_from_cache():
    """Load tokens from artificial_memory_d.json cache file"""
    try:
        cache_file = "src/data/artificial_memory_d.json"
        with open(cache_file, "r") as f:
            cache_data = json.load(f)
        
        # Extract token mints from the cache
        token_mints = set()
        
        # Handle the nested structure of the cache file
        data = cache_data.get('data', {}).get('data', {})
        if not data:
            data = cache_data.get('data', {})
            
        for wallet_address, tokens in data.items():
            for token in tokens:
                token_mints.add(token.get('mint'))
        
        return list(token_mints)
    except Exception as e:
        print(f"Error loading tokens from cache: {str(e)}")
        return []

def test_raydium_price(token_address):
    """Test Raydium API for token price"""
    try:
        url = f"https://api.raydium.io/v2/main/price?mint={token_address}"
        response = requests.get(url, timeout=5)  # Reduce timeout to 5 seconds
        
        if response.status_code == 200:
            data = response.json()
            
            # Check different possible response formats
            if 'data' in data and 'price' in data.get('data', {}):
                price = data['data']['price']
                return True, price
            elif token_address in data:
                price = data[token_address]
                return True, price
            elif 'price' in data:
                price = data['price']
                return True, price
            else:
                return False, "No price data in response"
        else:
            return False, f"API error: {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Error: {str(e)}"

def test_orca_price(token_address):
    """Test Orca API for token price"""
    try:
        # First try direct token endpoint
        url = f"https://api.orca.so/v2/solana/token?address={token_address}"
        response = requests.get(url, timeout=5)  # Reduce timeout to 5 seconds
        
        if response.status_code == 200:
            data = response.json()
            if 'price' in data:
                return True, data['price']
            elif 'value' in data:
                return True, data['value']
            
        # Skip tokens list lookup for now to speed up process
        return False, "Token not found or no price data"
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Error: {str(e)}"

def test_pumpfun_price(token_address):
    """Test Pump.fun API for token price"""
    try:
        # First try the documented endpoint
        url = f"https://pump.fun/api/price/{token_address}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'SOL' in data:
                return True, f"SOL: {data.get('SOL')}, USD: {data.get('USD')}"
            else:
                return False, "No price data in response"
        
        # Try alternative endpoint 1
        url2 = f"https://api.pumpfunapi.org/price/{token_address}"
        try:
            response = requests.get(url2, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'SOL' in data or 'USD' in data:
                    sol_price = data.get('SOL', 'N/A')
                    usd_price = data.get('USD', 'N/A')
                    return True, f"SOL: {sol_price}, USD: {usd_price}"
        except:
            pass  # Silently continue if this fails
        
        # Try alternative endpoint 2
        url3 = f"https://pumpapi.fun/api/token/{token_address}/price"
        try:
            response = requests.get(url3, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, dict):
                    return True, f"Data: {str(data)[:50]}..."
        except:
            pass  # Silently continue if this fails
            
        return False, f"Not found on any Pump.fun endpoint"
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    print(f"===== Testing Multiple Price APIs =====")
    print(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=====================================")
    
    # Only test SOL (which should work) and a few specific problem tokens
    token_mints = [
        "So11111111111111111111111111111111111111112",  # SOL token address
        "VFdxjTdFzXrYr3ivWyf64NuXo9U7vdPK7AG7idnNZJV",  # Problem Token1
        "CR2L1ob96JGWQkdFbt8rLwqdLLmqFwjcNGL2eFBn1RPt",  # Problem Token2
        "DycFB5CXEvEngK1B7GVrXsj3Uz7GecQUZXeSVLsFpump"   # Problem Token6 with "pump" in name
    ]
    
    print(f"Testing {len(token_mints)} tokens")
    
    # Test each token with multiple APIs
    results = {
        "raydium": {"found": 0, "not_found": 0},
        "orca": {"found": 0, "not_found": 0},
        "pumpfun": {"found": 0, "not_found": 0}
    }
    
    # Test each token with multiple APIs
    for i, token_address in enumerate(token_mints, 1):
        print(f"\n{'-'*50}")
        print(f"Testing token {i}/{len(token_mints)}: {token_address}")
        
        # Test Raydium
        raydium_success, raydium_result = test_raydium_price(token_address)
        if raydium_success:
            print(f"[SUCCESS] Raydium: ${raydium_result}")
            results["raydium"]["found"] += 1
        else:
            print(f"[FAILED] Raydium: {raydium_result}")
            results["raydium"]["not_found"] += 1
        
        # Test Orca
        orca_success, orca_result = test_orca_price(token_address)
        if orca_success:
            print(f"[SUCCESS] Orca: ${orca_result}")
            results["orca"]["found"] += 1
        else:
            print(f"[FAILED] Orca: {orca_result}")
            results["orca"]["not_found"] += 1
        
        # Test Pump.fun
        pumpfun_success, pumpfun_result = test_pumpfun_price(token_address)
        if pumpfun_success:
            print(f"[SUCCESS] Pump.fun: {pumpfun_result}")
            results["pumpfun"]["found"] += 1
        else:
            print(f"[FAILED] Pump.fun: {pumpfun_result}")
            results["pumpfun"]["not_found"] += 1
        
        # Add a delay to avoid rate limiting
        time.sleep(1)
    
    # Print summary
    print(f"\n{'-'*50}")
    print(f"SUMMARY")
    print(f"{'-'*50}")
    print(f"Total tokens tested: {len(token_mints)}")
    print(f"Raydium: {results['raydium']['found']} found, {results['raydium']['not_found']} not found")
    print(f"Orca: {results['orca']['found']} found, {results['orca']['not_found']} not found")
    print(f"Pump.fun: {results['pumpfun']['found']} found, {results['pumpfun']['not_found']} not found")
    
    # Show unique coverage
    only_raydium = [token for token in token_mints 
                   if test_raydium_price(token)[0] and not test_orca_price(token)[0] and not test_pumpfun_price(token)[0]]
    only_orca = [token for token in token_mints 
                if not test_raydium_price(token)[0] and test_orca_price(token)[0] and not test_pumpfun_price(token)[0]]
    only_pumpfun = [token for token in token_mints 
                   if not test_raydium_price(token)[0] and not test_orca_price(token)[0] and test_pumpfun_price(token)[0]]
    
    print(f"\nUnique coverage:")
    print(f"Only found on Raydium: {len(only_raydium)} tokens")
    print(f"Only found on Orca: {len(only_orca)} tokens")
    print(f"Only found on Pump.fun: {len(only_pumpfun)} tokens")
    
    # Make recommendation
    print(f"\nRECOMMENDATION:")
    apis_to_use = []
    if results['raydium']['found'] > 0:
        apis_to_use.append("Raydium")
    if results['orca']['found'] > 0:
        apis_to_use.append("Orca")
    if results['pumpfun']['found'] > 0:
        apis_to_use.append("Pump.fun")
    
    if len(apis_to_use) > 0:
        print(f"Based on the test results, you should use the following APIs for price data:")
        for api in apis_to_use:
            print(f"- {api}")
    else:
        print(f"None of the tested APIs provided price data for your tokens.")

if __name__ == "__main__":
    main() 