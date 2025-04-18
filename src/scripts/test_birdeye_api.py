"""
BirdEye API Tester (Debug Version)
Tests the connection to BirdEye API and debugs connection issues

Usage:
    python src/scripts/test_birdeye_api.py
"""

import os
import requests
import json
from dotenv import load_dotenv
import time
from termcolor import colored
import sys

# Load environment variables
load_dotenv()

# Get API key from .env
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

if not BIRDEYE_API_KEY:
    print(colored("Error: BIRDEYE_API_KEY not found in .env file", "red"))
    exit(1)

# Test tokens - SOL, BONK, and a few others
TEST_TOKENS = [
    "So11111111111111111111111111111111111111111",  # SOL
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
]

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 50)
    print(colored(f" {text} ", "cyan", attrs=["bold"]))
    print("=" * 50)

def debug_request(url, headers, params=None, timeout=10):
    """Make a request with detailed debugging information"""
    print(colored(f"Making request to: {url}", "yellow"))
    print(f"Headers: {json.dumps(headers, indent=2)}")
    if params:
        print(f"Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        print(colored(f"Response Status: {response.status_code}", "yellow"))
        
        # Try to parse as JSON
        try:
            response_json = response.json()
            # Pretty print the first 500 characters of the response
            response_text = json.dumps(response_json, indent=2)
            if len(response_text) > 1000:
                response_text = response_text[:1000] + "... (truncated)"
            print(colored("Response Body:", "yellow"))
            print(response_text)
            return response.status_code, response_json
        except:
            # If not JSON, print text
            response_text = response.text
            if len(response_text) > 1000:
                response_text = response_text[:1000] + "... (truncated)"
            print(colored("Response Text (not JSON):", "yellow"))
            print(response_text)
            return response.status_code, None
    except Exception as e:
        print(colored(f"Request Exception: {str(e)}", "red"))
        return None, None

def test_basic_connection():
    """Test basic connectivity to the BirdEye API"""
    print_header("TESTING BASIC CONNECTION")
    
    # Test with no parameters first (just GET to base URL)
    base_url = "https://public-api.birdeye.so"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    
    print(colored("Testing connection to base URL...", "yellow"))
    debug_request(base_url, headers)
    
    # Try docs endpoint if it exists
    print(colored("\nTesting docs endpoint...", "yellow"))
    debug_request(f"{base_url}/docs", headers)
    
    # Try ping endpoint if it exists
    print(colored("\nTesting ping endpoint...", "yellow"))
    debug_request(f"{base_url}/ping", headers)

def test_api_endpoints():
    """Test various API endpoints to see which ones work"""
    print_header("TESTING VARIOUS ENDPOINTS")
    
    base_url = "https://public-api.birdeye.so"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    
    # List of endpoints to try (based on Birdeye documentation and common patterns)
    endpoints = [
        "/public/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=1",
        "/public/token_list?sort_by=v24hUSD&sort_type=desc&offset=0&limit=1",  # Alternative spelling
        "/public/price?address=So11111111111111111111111111111111111111111",
        "/public/token?address=So11111111111111111111111111111111111111111",
        "/public/token_price?address=So11111111111111111111111111111111111111111",  # Alternative
        "/public/market_depth?address=So11111111111111111111111111111111111111111",
        "/v1/public/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=1",  # Try with v1 prefix
        "/v2/public/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=1",  # Try with v2 prefix
        "/api/public/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=1",  # Try with api prefix
        "/prices/current/solana/So11111111111111111111111111111111111111111"  # Alternative format
    ]
    
    working_endpoints = []
    
    for endpoint in endpoints:
        print(colored(f"\nTesting endpoint: {endpoint}", "yellow"))
        status, data = debug_request(f"{base_url}{endpoint}", headers)
        
        if status == 200 and data and data.get("success", False):
            print(colored(f"✓ SUCCESS: {endpoint}", "green"))
            working_endpoints.append(endpoint)
        else:
            print(colored(f"✗ FAILED: {endpoint}", "red"))
        
        # Pause between requests
        time.sleep(1)
    
    if working_endpoints:
        print_header("WORKING ENDPOINTS")
        for endpoint in working_endpoints:
            print(colored(f"✓ {endpoint}", "green"))
    else:
        print_header("NO WORKING ENDPOINTS FOUND")

def check_alternative_apis():
    """Check if alternative data sources are available"""
    print_header("CHECKING ALTERNATIVE APIs")
    
    # 1. Check Helius RPC endpoint
    print(colored("\nTesting Helius RPC endpoint...", "yellow"))
    helius_key = os.getenv("RPC_ENDPOINT", "").split("?api-key=")[-1] if "helius" in os.getenv("RPC_ENDPOINT", "") else None
    
    if helius_key:
        helius_url = f"https://api.helius.xyz/v0/tokens/metadata?api-key={helius_key}"
        params = {"mintAccounts": ["So11111111111111111111111111111111111111111"]}
        headers = {"Content-Type": "application/json"}
        debug_request(helius_url, headers, params)
    else:
        print(colored("Helius API key not found in RPC_ENDPOINT", "red"))
    
    # 2. Check Jupiter API
    print(colored("\nTesting Jupiter API...", "yellow"))
    jupiter_url = "https://price.jup.ag/v4/price?ids=So11111111111111111111111111111111111111111"
    debug_request(jupiter_url, {})
    
    # 3. Check SolanaFM API
    print(colored("\nTesting SolanaFM API...", "yellow"))
    solanafm_url = "https://api.solana.fm/v0/tokens/metadata?mintAddresses=So11111111111111111111111111111111111111111"
    debug_request(solanafm_url, {})

def test_birdeye_api_with_bearer():
    """Test if the API works with a bearer token instead of X-API-KEY header"""
    print_header("TESTING WITH BEARER TOKEN")
    
    base_url = "https://public-api.birdeye.so/public/tokenlist"
    params = {"sort_by": "v24hUSD", "sort_type": "desc", "offset": "0", "limit": "1"}
    
    # Try with different auth methods
    auth_methods = [
        {"headers": {"X-API-KEY": BIRDEYE_API_KEY}, "name": "X-API-KEY Header"},
        {"headers": {"Authorization": f"Bearer {BIRDEYE_API_KEY}"}, "name": "Bearer Token"},
        {"headers": {}, "params": {**params, "api_key": BIRDEYE_API_KEY}, "name": "API Key as Query Param"}
    ]
    
    for method in auth_methods:
        print(colored(f"\nTesting with {method['name']}...", "yellow"))
        method_params = method.get("params", params)
        status, data = debug_request(base_url, method["headers"], method_params)
        
        if status == 200 and data and data.get("success", False):
            print(colored(f"✓ SUCCESS with {method['name']}", "green"))
        else:
            print(colored(f"✗ FAILED with {method['name']}", "red"))
        
        time.sleep(1)

def main():
    """Main function"""
    print_header("BIRDEYE API DEBUG TESTER")
    print(f"API Key: {BIRDEYE_API_KEY[:4]}...{BIRDEYE_API_KEY[-4:]}")
    
    # First, test basic connection
    test_basic_connection()
    
    # Test various API endpoints
    test_api_endpoints()
    
    # Test with different authentication methods
    test_birdeye_api_with_bearer()
    
    # Check alternative APIs
    check_alternative_apis()
    
    print_header("DEBUGGING COMPLETE")
    print(colored("Check the output above to identify working endpoints and authentication methods.", "yellow"))
    print("If all BirdEye endpoints are failing, consider using Jupiter or SolanaFM as alternatives.")
    
if __name__ == "__main__":
    main() 