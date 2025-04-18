import requests
import json
import time

def test_apis():
    print("Testing price API endpoints...")
    sol_address = "So11111111111111111111111111111111111111112"
    
    # Test Jupiter API
    print("\n1. Testing Jupiter API")
    jupiter_url = f"https://lite-api.jup.ag/price/v2?ids={sol_address}"
    print(f"URL: {jupiter_url}")
    
    try:
        start_time = time.time()
        response = requests.get(jupiter_url, timeout=10)
        elapsed = time.time() - start_time
        
        print(f"Response Time: {elapsed:.2f}s, Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            price = None
            if 'data' in data and sol_address in data['data']:
                price = data['data'][sol_address].get('price')
            
            if price:
                print(f"✅ Jupiter API Success: SOL Price = ${price}")
            else:
                print(f"❌ Jupiter API Error: Could not find price data")
                print(f"Response: {json.dumps(data)[:300]}...")
        else:
            print(f"❌ Jupiter API Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Jupiter API Error: {str(e)}")
    
    # Test Raydium API
    print("\n2. Testing Raydium API")
    raydium_url = f"https://api.raydium.io/v2/main/price?mint={sol_address}"
    print(f"URL: {raydium_url}")
    
    try:
        start_time = time.time()
        response = requests.get(raydium_url, timeout=10)
        elapsed = time.time() - start_time
        
        print(f"Response Time: {elapsed:.2f}s, Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response structure: {list(data.keys())}")
            
            if 'data' in data and 'price' in data.get('data', {}):
                price = data['data']['price']
                print(f"✅ Raydium API Success (new format): SOL Price = ${price}")
            elif sol_address in data:
                price = data[sol_address]
                print(f"✅ Raydium API Success (old format): SOL Price = ${price}")
            else:
                print(f"❌ Raydium API Error: Could not find price data")
                print(f"Response: {json.dumps(data)[:300]}...")
        else:
            print(f"❌ Raydium API Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Raydium API Error: {str(e)}")
    
    # Test Orca API
    print("\n3. Testing Orca API")
    orca_url = f"https://api.orca.so/v2/solana/token?address={sol_address}"
    print(f"URL: {orca_url}")
    
    try:
        start_time = time.time()
        response = requests.get(orca_url, timeout=10)
        elapsed = time.time() - start_time
        
        print(f"Response Time: {elapsed:.2f}s, Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if 'price' in data:
                price = data['price']
                print(f"✅ Orca API Success: SOL Price = ${price}")
            elif 'value' in data:
                price = data['value']
                print(f"✅ Orca API Success (alt format): SOL Price = ${price}")
            else:
                print(f"❌ Orca API Error: Could not find price data")
                print(f"Response: {json.dumps(data)[:300]}...")
        else:
            print(f"❌ Orca API Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Orca API Error: {str(e)}")
    
    print("\nTest complete!")

if __name__ == "__main__":
    test_apis() 