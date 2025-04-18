import sys
import time
from src import nice_funcs as n

def test_token_price():
    """Test the token_price function with various tokens"""
    
    # Test tokens - SOL and other popular tokens
    tokens = {
        "SOL": "So11111111111111111111111111111111111111112",
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        "MNDE": "MNDEFzGvMt87ueuHvVU9VcTqsAP5b3fTGPsHuuPA5ey"
    }
    
    print("Testing token_price function with various tokens...")
    
    for name, address in tokens.items():
        print(f"\nTesting {name} ({address})...")
        
        # Test with default behavior (using cache)
        start_time = time.time()
        price = n.token_price(address)
        elapsed = time.time() - start_time
        
        print(f"Price: ${price} (fetched in {elapsed:.2f}s)")
        
        # Test with force_refresh=True (bypassing cache)
        start_time = time.time()
        price_refresh = n.token_price(address, force_refresh=True)
        elapsed = time.time() - start_time
        
        print(f"Price (force refresh): ${price_refresh} (fetched in {elapsed:.2f}s)")
        
        # Test individual API functions
        print(f"\nTesting individual API sources for {name}:")
        
        # Jupiter
        try:
            start_time = time.time()
            price = n.get_real_time_price_jupiter(address)
            elapsed = time.time() - start_time
            print(f"- Jupiter: ${price} (in {elapsed:.2f}s)")
        except Exception as e:
            print(f"- Jupiter: Error - {str(e)}")
        
        # Raydium
        try:
            start_time = time.time()
            price = n.get_real_time_price_raydium_token(address)
            elapsed = time.time() - start_time
            print(f"- Raydium: ${price} (in {elapsed:.2f}s)")
        except Exception as e:
            print(f"- Raydium: Error - {str(e)}")
        
        # Orca
        try:
            start_time = time.time()
            price = n.get_real_time_price_orca(address)
            elapsed = time.time() - start_time
            print(f"- Orca: ${price} (in {elapsed:.2f}s)")
        except Exception as e:
            print(f"- Orca: Error - {str(e)}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_token_price() 