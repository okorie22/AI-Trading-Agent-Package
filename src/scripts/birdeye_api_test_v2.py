"""
BirdEye API Tester (Updated with correct endpoints)
Tests the connection to BirdEye API using the documented endpoints from the accessibility table

Usage:
    python src/scripts/birdeye_api_test_v2.py
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

# Test tokens - SOL, BONK, and USDC
TEST_TOKENS = [
    "So11111111111111111111111111111111111111111",  # SOL
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
]

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(colored(f" {text} ", "cyan", attrs=["bold"]))
    print("=" * 60)

def make_request(url, headers=None, params=None, method="GET", data=None, timeout=10):
    """Make a request and pretty print the results"""
    if headers is None:
        headers = {}
    
    print(colored(f"Request: {method} {url}", "yellow"))
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    if params:
        print(f"Params: {json.dumps(params, indent=2)}")
    
    if data:
        print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
        else:
            print(colored(f"Unsupported method: {method}", "red"))
            return None
        
        print(colored(f"Response Status: {response.status_code}", "yellow"))
        
        # Check if response is JSON
        try:
            response_json = response.json()
            # Pretty print the response
            response_text = json.dumps(response_json, indent=2)
            if len(response_text) > 1000:
                response_text = response_text[:1000] + "... (truncated)"
            print(colored("Response Body (JSON):", "yellow"))
            print(response_text)
            return response.status_code, response_json
        except Exception as e:
            # If not JSON, print text
            response_text = response.text
            if len(response_text) > 1000:
                response_text = response_text[:1000] + "... (truncated)"
            print(colored("Response Text (not JSON):", "yellow"))
            print(response_text)
            print(colored(f"Exception parsing JSON: {str(e)}", "red"))
            return response.status_code, None
    except Exception as e:
        print(colored(f"Exception making request: {str(e)}", "red"))
        return None, None

def test_documented_endpoints():
    """Test the documented endpoints from the BirdEye API documentation"""
    print_header("TESTING DOCUMENTED ENDPOINTS")
    
    # Base URL
    base_url = "https://public-api.birdeye.so"
    
    # Set up standard headers
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    
    # Test token list endpoint (should be available on all tiers)
    print_header("TOKEN LIST ENDPOINT")
    tokenlist_url = f"{base_url}/defi/tokenlist"
    make_request(tokenlist_url, headers=headers)
    
    # Test price endpoint with SOL (should be available on all tiers)
    print_header("PRICE ENDPOINT")
    price_url = f"{base_url}/defi/price?address={TEST_TOKENS[0]}"
    make_request(price_url, headers=headers)
    
    # Test historical price endpoint (should be available on all tiers)
    print_header("HISTORICAL PRICE ENDPOINT")
    history_url = f"{base_url}/defi/history_price?address={TEST_TOKENS[0]}&type=day&limit=7"
    make_request(history_url, headers=headers)
    
    # Test token overview endpoint (only available on Starter tier and above)
    print_header("TOKEN OVERVIEW ENDPOINT")
    overview_url = f"{base_url}/defi/token_overview?address={TEST_TOKENS[0]}"
    make_request(overview_url, headers=headers)
    
    # Test token security endpoint (only available on Starter tier and above)
    print_header("TOKEN SECURITY ENDPOINT")
    security_url = f"{base_url}/defi/token_security?address={TEST_TOKENS[0]}"
    make_request(security_url, headers=headers)

def test_auth_methods():
    """Test different authentication methods"""
    print_header("TESTING AUTHENTICATION METHODS")
    
    # Base domain and endpoint from the documentation
    domain = "https://public-api.birdeye.so"
    endpoint = "/defi/tokenlist"
    
    # Try with different auth methods
    auth_methods = [
        {"headers": {"X-API-KEY": BIRDEYE_API_KEY}, "name": "X-API-KEY Header"},
        {"headers": {"Authorization": f"Bearer {BIRDEYE_API_KEY}"}, "name": "Bearer Token"},
        {"headers": {"X-API-Key": BIRDEYE_API_KEY}, "name": "X-API-Key Header (Capital K)"},
        {"headers": {"x-api-key": BIRDEYE_API_KEY}, "name": "x-api-key Header (lowercase)"},
    ]
    
    for method in auth_methods:
        print(colored(f"\nTesting with {method['name']}...", "yellow"))
        make_request(f"{domain}{endpoint}", headers=method["headers"])
        time.sleep(1)

def test_all_tokens():
    """Test price endpoint with all test tokens"""
    print_header("TESTING PRICE WITH MULTIPLE TOKENS")
    
    base_url = "https://public-api.birdeye.so"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    
    for token in TEST_TOKENS:
        print(colored(f"\nTesting token: {token}", "yellow"))
        price_url = f"{base_url}/defi/price?address={token}"
        make_request(price_url, headers=headers)
        time.sleep(1)

def test_fallback_apis():
    """Test fallback APIs for comparison"""
    print_header("TESTING FALLBACK APIs")
    
    # Jupiter API is working reliably in your codebase
    print_header("JUPITER API PRICE")
    token = TEST_TOKENS[0]  # SOL
    make_request(f"https://price.jup.ag/v4/price?ids={token}")
    
    print_header("JUPITER API TOKEN INFO")
    make_request("https://token.jup.ag/all")
    
    # Test a specific token query in Jupiter
    print_header("JUPITER API SPECIFIC TOKEN")
    make_request(f"https://token.jup.ag/tokens/{token}")

def main():
    """Main function"""
    print_header("BIRDEYE API TESTER v2")
    print(f"API Key: {BIRDEYE_API_KEY[:4]}...{BIRDEYE_API_KEY[-4:]}")
    
    # Test the documented endpoints
    test_documented_endpoints()
    
    # Test with different auth methods
    test_auth_methods()
    
    # Test all tokens
    test_all_tokens()
    
    # Test fallback APIs
    test_fallback_apis()
    
    print_header("SUMMARY")
    print(colored("This tool tested BirdEye API endpoints based on the official documentation.", "yellow"))
    print("The documentation shows that /defi/tokenlist and /defi/price should be available on all tiers.")
    print("If these endpoints are not working, your API key may be invalid or expired.")
    print("The Jupiter API is available as a reliable fallback for both price and token metadata.")
    
if __name__ == "__main__":
    main() 