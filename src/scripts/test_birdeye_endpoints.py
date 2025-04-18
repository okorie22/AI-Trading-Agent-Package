import requests

# Your API key
API_KEY = "36ae269907a64797a8be6f76456814e5"

# Base URL options
base_urls = [
    "https://public-api.birdeye.so/defi",         # Original format
    "https://public-api.birdeye.so/public",       # Alternative format
    "https://public-api.birdeye.so"               # Root format
]

# Test token - SOL
token = "So11111111111111111111111111111111111111111"

# Try different header formats
headers_options = [
    {"X-API-KEY": API_KEY},
    {"x-api-key": API_KEY}
]

# Test endpoints
endpoints = [
    "/tokenlist",
    "/price",
    "/history_price",
    "/networks"  # Check supported networks
]

print("TESTING ALTERNATIVE BIRDEYE API ENDPOINTS")
print("-" * 50)

for base_url in base_urls:
    for headers in headers_options:
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            if endpoint == "/price" or endpoint == "/history_price":
                url += f"?address={token}"
                if endpoint == "/history_price":
                    url += "&type=day&limit=7"
                    
            print(f"\nTesting URL: {url}")
            print(f"Headers: {headers}")
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                print(f"Status: {response.status_code}")
                
                # Get first 100 chars of response to check format
                response_text = response.text[:100] + "..." if len(response.text) > 100 else response.text
                print(f"Response: {response_text}")
                
            except Exception as e:
                print(f"Error: {str(e)}")