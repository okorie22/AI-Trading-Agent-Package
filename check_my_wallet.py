import os
import sys
from dotenv import load_dotenv

# Load environment variables for RPC endpoint
load_dotenv()

# Add the project root to path to ensure modules can be imported
sys.path.append(".")

# Import the enhanced functions from nice_funcs
from src.nice_funcs import get_wallet_tokens_with_value, get_wallet_total_value

def main():
    # Try to import config to get the wallet address
    try:
        from src.config import address as wallet_address
        if not wallet_address:
            wallet_address = input("Enter your wallet address: ")
    except ImportError:
        # If config isn't available, prompt for the wallet address
        wallet_address = input("Enter your wallet address: ")
    
    print(f"Using wallet address: {wallet_address}")
    
    # Get tokens from the wallet using the enhanced function
    tokens = get_wallet_tokens_with_value(wallet_address)
    
    # Calculate total value
    total_value = sum(token["usd_value"] for token in tokens)
    
    # Display results
    print("\n== YOUR WALLET TOKENS ==")
    if tokens:
        print(f"Total wallet value: ${total_value:.2f}")
        print(f"Total number of tokens: {len(tokens)}")
        
        print("\nTop 10 tokens by value:")
        for i, token in enumerate(tokens[:10], 1):
            print(f"{i}. Token: {token['mint']}")
            print(f"   Balance: {token['balance']}")
            print(f"   Price: ${token['price']:.6f}")
            print(f"   Value: ${token['usd_value']:.2f}")
            print()
            
        # Show the total count of small value tokens
        small_tokens = [t for t in tokens if t['usd_value'] < 0.01]
        if small_tokens:
            print(f"+ {len(small_tokens)} tokens with value less than $0.01")
    else:
        print("No tokens found or error fetching tokens")

if __name__ == "__main__":
    main() 