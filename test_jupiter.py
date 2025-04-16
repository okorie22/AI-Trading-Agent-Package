import requests
import json
import time
import os
import sys

print("Starting Jupiter API test...")

try:
    print("\nSystem Information:")
    print(f"Python version: {sys.version}")
    print(f"Requests version: {requests.__version__}")
    
    # Test simple connection to Jupiter API
    print("\nTesting connection to Jupiter Price API...")
    
    # SOL token address
    sol_address = "So11111111111111111111111111111111111111112"
    
    # Test price endpoint
    print("\nTest 1: Jupiter Price API")
    price_url = f"https://lite-api.jup.ag/price/v2?ids={sol_address}"
    print(f"URL: {price_url}")
    
    start_time = time.time()
    try:
        print("Sending request...")
        price_response = requests.get(price_url, timeout=30)
        end_time = time.time()
        
        print(f"Response received in {(end_time - start_time):.2f} seconds")
        print(f"Status Code: {price_response.status_code}")
        
        if price_response.status_code == 200:
            print("SUCCESS - Jupiter Price API is working!")
            print("Content sample:")
            if len(price_response.content) > 500:
                print(price_response.content[:500])
            else:
                print(price_response.content)
        else:
            print(f"Failed - Status code: {price_response.status_code}")
            print(f"Response: {price_response.text[:200]}")
    except Exception as e:
        print(f"Error connecting to Jupiter Price API: {str(e)}")
    
    # Test quote endpoint
    print("\nTest 2: Jupiter Quote API")
    usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    quote_url = f"https://quote-api.jup.ag/v6/quote?inputMint={sol_address}&outputMint={usdc_address}&amount=1000000000&slippageBps=50"
    print(f"URL: {quote_url}")
    
    start_time = time.time()
    try:
        print("Sending request...")
        quote_response = requests.get(quote_url, timeout=30)
        end_time = time.time()
        
        print(f"Response received in {(end_time - start_time):.2f} seconds")
        print(f"Status Code: {quote_response.status_code}")
        
        if quote_response.status_code == 200:
            print("SUCCESS - Jupiter Quote API is working!")
            print("Content sample:")
            if len(quote_response.content) > 500:
                print(quote_response.content[:500])
            else:
                print(quote_response.content)
        else:
            print(f"Failed - Status code: {quote_response.status_code}")
            print(f"Response: {quote_response.text[:200]}")
    except Exception as e:
        print(f"Error connecting to Jupiter Quote API: {str(e)}")
    
    print("\nTroubleshooting suggestions:")
    print("1. Check your internet connection")
    print("2. Verify your firewall/antivirus isn't blocking the connection")
    print("3. Try using a different network (mobile hotspot, different Wi-Fi)")
    print("4. Check if Jupiter API is down: https://status.jup.ag/")
    print("5. Try to ping lite-api.jup.ag/price/v2 and quote-api.jup.ag from command line")
    
except Exception as e:
    print(f"An error occurred in the test script: {str(e)}")
    import traceback
    print(traceback.format_exc())