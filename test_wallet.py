import os
from dotenv import load_dotenv
from src.nice_funcs import get_wallet_tokens_with_value, get_wallet_total_value

# Load environment variables
load_dotenv()

# Get wallet address from config
wallet_address = os.getenv('DEFAULT_WALLET_ADDRESS')
print(f"Testing wallet: {wallet_address}")

# Direct RPC call to fetch tokens
print("\nFetching wallet tokens with our enhanced function...")
tokens = get_wallet_tokens_with_value(wallet_address)

if tokens:
    print(f"Found {len(tokens)} tokens in wallet")
    total_value = sum(token["usd_value"] for token in tokens)
    print(f"Total wallet value: ${total_value:.2f}")
    
    # Display top tokens by value
    print("\nTop tokens by value:")
    for i, token in enumerate(sorted(tokens, key=lambda x: x["usd_value"], reverse=True)[:5], 1):
        print(f"{i}. {token['mint']} - ${token['usd_value']:.6f} (Balance: {token['balance']})")
else:
    print("No tokens found in wallet or error occurred")

# Try to specifically check for SOL
print("\nSpecifically checking for SOL...")
sol_address = "So11111111111111111111111111111111111111112"
sol_tokens = [t for t in tokens if t["mint"] == sol_address]
if sol_tokens:
    print(f"Found SOL with value: ${sol_tokens[0]['usd_value']:.6f}")
else:
    print("No SOL found in wallet") 