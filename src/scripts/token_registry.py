import os
import json
import requests
import time
from datetime import datetime
import pandas as pd

class TokenRegistry:
    def __init__(self):
        self.registry_file = os.path.join(os.getcwd(), "src/data/token_registry.json")
        self.registry = self.load_registry()
        self.last_update = self.registry.get('last_update', 0)
        
    def load_registry(self):
        """Load the token registry from file or create new one"""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Failed to load registry: {str(e)}")
        
        # Initialize empty registry
        return {
            'last_update': 0,
            'tokens': {},
            'sources': []
        }
        
    def save_registry(self):
        """Save registry to disk"""
        self.registry['last_update'] = int(time.time())
        try:
            os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
            print(f"✅ Token registry saved with {len(self.registry['tokens'])} tokens")
        except Exception as e:
            print(f"❌ Failed to save registry: {str(e)}")
            
    def update_registry(self, force=False):
        """Update registry from multiple sources"""
        now = int(time.time())
        if not force and (now - self.last_update) < 86400:  # Update once per day
            return
            
        # Update from Jupiter
        self._update_from_jupiter()
        
        # Update from Birdeye
        self._update_from_birdeye()
        
        # Update from Solana token list
        self._update_from_solana_registry()
        
        # Save updated registry
        self.save_registry()
        
    def _update_from_jupiter(self):
        """Update registry from Jupiter token list"""
        try:
            response = requests.get("https://token.jup.ag/all")
            if response.status_code == 200:
                tokens = response.json()
                self.registry['sources'].append({
                    'name': 'jupiter',
                    'timestamp': datetime.now().isoformat(),
                    'count': len(tokens)
                })
                
                for token in tokens:
                    address = token.get('address')
                    if not address:
                        continue
                        
                    if address not in self.registry['tokens']:
                        self.registry['tokens'][address] = {
                            'name': token.get('name', f"Unknown-{address[:4]}"),
                            'symbol': token.get('symbol', '???'),
                            'decimals': token.get('decimals', 9),
                            'logo': token.get('logoURI', ''),
                            'sources': ['jupiter']
                        }
                    else:
                        existing = self.registry['tokens'][address]
                        existing['sources'] = list(set(existing.get('sources', []) + ['jupiter']))
                
                print(f"✅ Added/updated {len(tokens)} tokens from Jupiter")
        except Exception as e:
            print(f"❌ Jupiter update failed: {str(e)}")
            
    def _update_from_birdeye(self):
        """Update registry from Birdeye trending tokens"""
        try:
            url = "https://public-api.birdeye.so/public/tokenlist/trending_tokens"
            headers = {"X-API-KEY": os.getenv("BIRDEYE_API_KEY")}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                tokens = data.get('data', {}).get('tokens', [])
                self.registry['sources'].append({
                    'name': 'birdeye',
                    'timestamp': datetime.now().isoformat(),
                    'count': len(tokens)
                })
                
                for token in tokens:
                    address = token.get('address')
                    if not address:
                        continue
                        
                    if address not in self.registry['tokens']:
                        self.registry['tokens'][address] = {
                            'name': token.get('name', f"Unknown-{address[:4]}"),
                            'symbol': token.get('symbol', '???'),
                            'decimals': token.get('decimals', 9),
                            'logo': token.get('logoUrl', ''),
                            'sources': ['birdeye']
                        }
                    else:
                        existing = self.registry['tokens'][address]
                        existing['sources'] = list(set(existing.get('sources', []) + ['birdeye']))
                
                print(f"✅ Added/updated {len(tokens)} tokens from Birdeye")
        except Exception as e:
            print(f"❌ Birdeye update failed: {str(e)}")

    def _update_from_solana_registry(self):
        """Update from main Solana token registry"""
        try:
            url = "https://cdn.jsdelivr.net/gh/solana-labs/token-list@main/src/tokens/solana.tokenlist.json"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                tokens = data.get('tokens', [])
                self.registry['sources'].append({
                    'name': 'solana_registry',
                    'timestamp': datetime.now().isoformat(),
                    'count': len(tokens)
                })
                
                for token in tokens:
                    address = token.get('address')
                    if not address:
                        continue
                        
                    if address not in self.registry['tokens']:
                        self.registry['tokens'][address] = {
                            'name': token.get('name', f"Unknown-{address[:4]}"),
                            'symbol': token.get('symbol', '???'),
                            'decimals': token.get('decimals', 9),
                            'logo': token.get('logoURI', ''),
                            'sources': ['solana_registry']
                        }
                    else:
                        existing = self.registry['tokens'][address]
                        existing['sources'] = list(set(existing.get('sources', []) + ['solana_registry']))
                
                print(f"✅ Added/updated {len(tokens)} tokens from Solana registry")
        except Exception as e:
            print(f"❌ Solana registry update failed: {str(e)}")
            
    def get_token_info(self, mint_address):
        """Get token info from registry"""
        return self.registry['tokens'].get(mint_address, {
            'name': f"Unknown-{mint_address[:4]}...{mint_address[-4:]}",
            'symbol': '???',
            'decimals': 9,
            'logo': '',
            'sources': []
        }) 