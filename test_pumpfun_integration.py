import sys
import time
from src import nice_funcs as n

def test_pumpfun_integration():
    """Test the new Pump.fun integration functions"""
    
    print("Testing Pump.fun price API integration...")
    
    # Problem tokens from previous tests
    problem_tokens = {
        "Token1": "VFdxjTdFzXrYr3ivWyf64NuXo9U7vdPK7AG7idnNZJV",
        "Token2": "CR2L1ob96JGWQkdFbt8rLwqdLLmqFwjcNGL2eFBn1RPt",
        "Token3": "2HdzfUiFWfZHZ544ynffeneuibbDK6biCdjovejr8ez9",
        "Token4": "C94njgTrKMQBmgqe23EGLrtPgfvcjWtqBBvGQ7Cjiank",
        "Token5": "7PU5nufFpFNhsbuiLH2JqhWkNvbuurNLY1X7tHttSBc9",
        "Token6": "DycFB5CXEvEngK1B7GVrXsj3Uz7GecQUZXeSVLsFpump",  # This one worked with Pump.fun
    }
    
    # Add SOL as a reference token (should work with all APIs)
    problem_tokens["SOL"] = "So11111111111111111111111111111111111111112"
    
    for name, address in problem_tokens.items():
        print(f"\n{'='*50}")
        print(f"Testing {name} ({address})...")
        print(f"{'='*50}")
        
        # Test price lookup using different methods
        print("\n1. Default token_price function (uses all sources):")
        try:
            start_time = time.time()
            price = n.token_price(address, force_refresh=True)
            elapsed = time.time() - start_time
            
            if price is not None and price > 0:
                print(f"[SUCCESS] Found price: ${price} (in {elapsed:.2f}s)")
            else:
                print(f"[FAILED] No price found (in {elapsed:.2f}s)")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
        
        # Test direct Pump.fun lookup
        print("\n2. Direct Pump.fun API lookup:")
        try:
            start_time = time.time()
            price = n.get_real_time_price_pumpfun(address)
            elapsed = time.time() - start_time
            
            if price is not None and price > 0:
                print(f"[SUCCESS] Found price on Pump.fun: ${price} (in {elapsed:.2f}s)")
            else:
                print(f"[FAILED] No price found on Pump.fun (in {elapsed:.2f}s)")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
        
        # Test market buy function (transaction generation only)
        if name == "Token6" or name == "SOL":  # Only test with tokens we expect to work
            print("\n3. Test market_buy_pumpfun transaction generation:")
            try:
                # Small SOL amount for testing
                amount_sol = 0.01
                result = n.market_buy_pumpfun(address, amount_sol)
                
                if result.get("success"):
                    print(f"[SUCCESS] Generated transaction successfully")
                    print(f"Status: {result.get('status')}")
                    print(f"Note: {result.get('note')}")
                else:
                    print(f"[FAILED] Could not generate transaction")
                    print(f"Error: {result.get('error')}")
            except Exception as e:
                print(f"[ERROR] {str(e)}")
        
        # Add a delay to avoid rate limiting
        time.sleep(1)
    
    print("\n" + "="*50)
    print("RECOMMENDATIONS:")
    print("="*50)
    print("1. For tokens not found on major DEXes, use the Pump.fun API")
    print("2. The token_price function now automatically tries Pump.fun if other sources fail")
    print("3. For trading tokens only available on Pump.fun, use market_buy_pumpfun/market_sell_pumpfun")
    print("4. You'll need to implement transaction signing with your wallet to complete trades")

if __name__ == "__main__":
    test_pumpfun_integration() 