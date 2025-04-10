import os
import requests

api_key = os.getenv("BIRDEYE_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get("https://api.birdeye.com/v1/example-endpoint", headers=headers)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")