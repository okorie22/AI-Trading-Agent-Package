import sys
import json
from src import nice_funcs as n
from src.scripts.token_list_tool import TokenAccountTracker
import os

def test_unknown_tokens():
    """Test handling of tokens with unknown prices"""
    
    print("\n==== Testing Unknown Price Handling ====")
    
    # Problem tokens from previous tests
    problem_tokens = {
        "Token1": "VFdxjTdFzXrYr3ivWyf64NuXo9U7vdPK7AG7idnNZJV",
        "Token2": "CR2L1ob96JGWQkdFbt8rLwqdLLmqFwjcNGL2eFBn1RPt",
        "Token3": "2HdzfUiFWfZHZ544ynffeneuibbDK6biCdjovejr8ez9",
        "Token4": "C94njgTrKMQBmgqe23EGLrtPgfvcjWtqBBvGQ7Cjiank"
    }
    
    print("\n1. Testing get_token_price function:")
    for name, address in problem_tokens.items():
        price = n.get_token_price(address, force_refresh=True)
        if price is None:
            print(f"[PASS] {name} ({address[:8]}...): Price correctly returned as None")
        else:
            print(f"[FAIL] {name} ({address[:8]}...): Price returned as {price}, expected None")
    
    # Test a known token (SOL)
    sol_address = "So11111111111111111111111111111111111111112"
    sol_price = n.get_token_price(sol_address, force_refresh=True)
    if sol_price is not None and sol_price > 0:
        print(f"[PASS] SOL: Price correctly returned as ${sol_price}")
    else:
        print(f"[FAIL] SOL: Price returned as {sol_price}, expected a positive number")
    
    print("\n2. Testing TokenAccountTracker's filter_relevant_tokens:")
    # Setup a mock token account list with both known and unknown price tokens
    token_accounts = [
        {
            "mint": sol_address,
            "amount": 1.0,
            "decimals": 9,
            "raw_amount": 1000000000,
            "wallet_address": "DummyWallet123"
        },
        {
            "mint": problem_tokens["Token1"],
            "amount": 1000.0,
            "decimals": 9,
            "raw_amount": 1000000000000,
            "wallet_address": "DummyWallet123"
        }
    ]
    
    # Set up the token tracker
    os.environ["RPC_ENDPOINT"] = "https://api.mainnet-beta.solana.com"  # Use a public RPC endpoint for testing
    tracker = TokenAccountTracker()
    
    # Filter the tokens and see if unknown price tokens are included
    filtered_tokens = tracker.filter_relevant_tokens(token_accounts)
    
    # Check if both tokens are in the filtered result
    found_sol = False
    found_unknown = False
    for token in filtered_tokens:
        if token["mint"] == sol_address:
            found_sol = True
            if token["price"] is not None and token["price"] != "Unknown":
                print(f"[PASS] SOL token price is correctly set: ${token['price']}")
            else:
                print(f"[FAIL] SOL token price should be a number, got: {token['price']}")
        
        if token["mint"] == problem_tokens["Token1"]:
            found_unknown = True
            if token["price"] == "Unknown":
                print(f"[PASS] Unknown token price is correctly set to 'Unknown'")
            else:
                print(f"[FAIL] Unknown token price should be 'Unknown', got: {token['price']}")
    
    if found_sol:
        print("[PASS] SOL token was included in filtered results")
    else:
        print("[FAIL] SOL token was not found in filtered results")
        
    if found_unknown:
        print("[PASS] Unknown price token was included in filtered results")
    else:
        print("[FAIL] Unknown price token was not found in filtered results")
    
    print("\n==== Test Complete ====")

if __name__ == "__main__":
    test_unknown_tokens() 