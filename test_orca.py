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
    
    # Test Orca Whirlpools price API
    print("\nTest 1: Orca Whirlpools Price API")
    price_url = f"https://api.mainnet.orca.so/v1/whirlpool/token/price?mint={sol_address}"
    print(f"URL: {price_url}")
    
    try:
        start_time = time.time()
        response = requests.get(price_url, timeout=10)
        elapsed = time.time() - start_time
        
        print(f"Response Status: {response.status_code} (in {elapsed:.2f}s)")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
            
            # Check if price data exists using the new format
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
        print(f"Error testing Orca Price API: {str(e)}")
    
    # Test with USDC
    print("\nTest 2: Orca Whirlpools Price API with USDC")
    price_url = f"https://api.mainnet.orca.so/v1/whirlpool/token/price?mint={usdc_address}"
    print(f"URL: {price_url}")
    
    try:
        response = requests.get(price_url, timeout=10)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error testing Orca API with USDC: {str(e)}")
    
    # Test BitQuery as a fallback for Orca data (for SOL specifically)
    print("\nTest 3: BitQuery GraphQL API for Orca Whirlpools data")
    bitquery_url = "https://streaming.bitquery.io/graphql"
    print(f"URL: {bitquery_url}")
    
    query = """
    query {
      Solana {
        DEXTradeByTokens(
          where: {Trade: {Currency: {MintAddress: {is: "So11111111111111111111111111111111111111112"}}, 
                          Dex: {ProgramAddress: {is: "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"}}}}
          limit: 1
          orderBy: {descending: Block_Time}
        ) {
          Trade {
            PriceAgainstSideCurrency: Price
          }
        }
      }
    }
    """
    
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(bitquery_url, json={"query": query}, headers=headers, timeout=15)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Print a more focused view of the result
            if "data" in data and "Solana" in data["data"] and "DEXTradeByTokens" in data["data"]["Solana"]:
                trades = data["data"]["Solana"]["DEXTradeByTokens"]
                if trades and len(trades) > 0:
                    print(f"Latest SOL price from Orca Whirlpools via BitQuery: {trades[0]['Trade']['PriceAgainstSideCurrency']}")
                else:
                    print("No trade data found")
            else:
                print(f"Response Data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error testing BitQuery API: {str(e)}")
    
    print("\nTest completed. Check results above to verify connectivity.")
    print("If you're having issues, check the following:")
    print("1. Ensure you have internet connectivity")
    print("2. Check if your firewall is blocking the connection")
    print("3. Try using a different network (mobile hotspot, different Wi-Fi)")
    print("4. Check if Orca API is down via their social media channels")

if __name__ == "__main__":
    test_orca_api() 