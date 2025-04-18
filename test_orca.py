import requests
import time
import json
import sys

def test_orca_api():
    """
    Test connectivity and price fetching from Orca's API
    """
    print("Starting Orca API test...\n")
    
    # Test token addresses - SOL and a popular token
    sol_address = "So11111111111111111111111111111111111111112"
    usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # Test Orca Token API
    print("\nTest 1: Orca Token API for SOL")
    price_url = f"https://api.orca.so/v2/solana/token?address={sol_address}"
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
            if 'price' in data:
                price = data['price']
                print(f"SOL Price: ${price}")
            elif 'value' in data:
                price = data['value']
                print(f"SOL Price (alt format): ${price}")
            else:
                print("No price data found in response")
        else:
            print(f"Error Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error testing Orca Token API: {str(e)}")
    
    # Test with USDC
    print("\nTest 2: Orca Token API for USDC")
    price_url = f"https://api.orca.so/v2/solana/token?address={usdc_address}"
    print(f"URL: {price_url}")
    
    try:
        response = requests.get(price_url, timeout=10)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
            
            # Check if price data exists
            if 'price' in data:
                price = data['price']
                print(f"USDC Price: ${price}")
            elif 'value' in data:
                price = data['value']
                print(f"USDC Price (alt format): ${price}")
            else:
                print("No price data found in response")
        else:
            print(f"Error Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error testing Orca API with USDC: {str(e)}")
    
    # Test general token endpoint
    print("\nTest 3: Orca Tokens List API")
    tokens_url = "https://api.orca.so/v2/solana/tokens"
    print(f"URL: {tokens_url}")
    
    try:
        response = requests.get(tokens_url, timeout=10)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Just print count to avoid overwhelming output
            if isinstance(data, list):
                print(f"Found {len(data)} tokens")
                # Print first token as sample
                if len(data) > 0:
                    print(f"Sample token: {json.dumps(data[0], indent=2)}")
            else:
                print(f"Response Data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error testing Orca Tokens API: {str(e)}")
    
    print("\nTest completed. Check results above to verify connectivity.")
    print("If you're having issues, check the following:")
    print("1. Ensure you have internet connectivity")
    print("2. Check if your firewall is blocking the connection")
    print("3. Try using a different network (mobile hotspot, different Wi-Fi)")
    print("4. Check if Orca API is down via their social media channels")

if __name__ == "__main__":
    test_orca_api() 