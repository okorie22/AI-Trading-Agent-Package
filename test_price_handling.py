import sys
from src import nice_funcs as n

def test_price_function():
    """Test just the modified price function behavior"""
    
    print("\n===== Testing Price Function Behavior =====")
    
    # Problem tokens from previous tests
    problem_tokens = [
        "VFdxjTdFzXrYr3ivWyf64NuXo9U7vdPK7AG7idnNZJV",
        "CR2L1ob96JGWQkdFbt8rLwqdLLmqFwjcNGL2eFBn1RPt",
        "2HdzfUiFWfZHZ544ynffeneuibbDK6biCdjovejr8ez9"
    ]
    
    # Check if SOL price works (should return a value)
    sol_address = "So11111111111111111111111111111111111111112"
    print(f"SOL price test:")
    sol_price = n.get_token_price(sol_address)
    print(f" - Result: {sol_price}")
    print(f" - Type: {type(sol_price)}")
    print(f" - {'SUCCESS' if sol_price is not None and sol_price > 0 else 'FAILED'}")
    
    # Check problem tokens (should return None)
    print("\nProblem tokens test:")
    for token in problem_tokens:
        price = n.get_token_price(token)
        print(f"Token {token[:8]}...")
        print(f" - Result: {price}")
        print(f" - Type: {type(price)}")
        print(f" - {'SUCCESS' if price is None else 'FAILED'}")
    
    # Test Pump.fun function directly
    print("\nPump.fun direct API test:")
    pump_token = "DycFB5CXEvEngK1B7GVrXsj3Uz7GecQUZXeSVLsFpump"
    price = n.get_real_time_price_pumpfun(pump_token)
    print(f" - Result: {price}")
    print(f" - Type: {type(price)}")
    print(f" - {'SUCCESS' if price is not None else 'FAILED'}")
    
    print("\n===== Test Complete =====")

if __name__ == "__main__":
    test_price_function() 