import requests
import time
import json
import sys

def test_raydium_api():
    """
    Test connectivity and price fetching from Raydium's API
    """
    print("Starting Raydium API test...\n")
    
    # Test token addresses - SOL and a popular token
    sol_address = "So11111111111111111111111111111111111111112"
    usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # Test Raydium price API
    print("\nTest 1: Raydium Price API")
    price_url = f"https://api.raydium.io/v2/main/price?mint={sol_address}"
    print(f"URL: {price_url}")
    
    try:
        start_time = time.time()
        response = requests.get(price_url, timeout=10)
        elapsed = time.time() - start_time
        
        print(f"Response Status: {response.status_code} (in {elapsed:.2f}s)")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
            
            # Check if price data exists
            if 'data' in data and 'price' in data.get('data', {}):
                price = data['data']['price']
                print(f"SOL Price: ${price}")
            elif 'price' in data:
                price = data['price']
                print(f"SOL Price (alt format): ${price}")
            else:
                print("No price data found in response")
        else:
            print(f"Error Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error testing Raydium Price API: {str(e)}")
    
    # Test with USDC
    print("\nTest 2: Raydium Price API with USDC")
    price_url = f"https://api.raydium.io/v2/main/price?mint={usdc_address}"
    print(f"URL: {price_url}")
    
    try:
        response = requests.get(price_url, timeout=10)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"Error testing Raydium API with USDC: {str(e)}")
    
    # Test Raydium Trade API (optional)
    print("\nTest 3: Raydium Trade API Connectivity")
    trade_url = "https://api.raydium.io/v2/main/pairs"
    print(f"URL: {trade_url}")
    
    try:
        response = requests.get(trade_url, timeout=10)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Just print count to avoid overwhelming output
            if 'data' in data and isinstance(data['data'], list):
                print(f"Found {len(data['data'])} trading pairs")
                # Print first pair as sample
                if len(data['data']) > 0:
                    print(f"Sample pair: {json.dumps(data['data'][0], indent=2)}")
            else:
                print(f"Response Data: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"Error testing Raydium Trade API: {str(e)}")
    
    print("\nTest completed. Check results above to verify connectivity.")
    print("If you're having issues, check the following:")
    print("1. Ensure you have internet connectivity")
    print("2. Check if your firewall is blocking the connection")
    print("3. Try using a different network (mobile hotspot, different Wi-Fi)")
    print("4. Check if Raydium API is down via their social media channels")

if __name__ == "__main__":
    test_raydium_api() 