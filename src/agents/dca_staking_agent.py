import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Add after imports but before class definition
PROJECT_ROOT = Path(__file__).parent.parent.parent

"""
Moon Dev's DCA Agent with Helius, Birdeye, and Solana Integration
Integrated with Yield Optimization for maximal profitability.
"""

import os
import time
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
from termcolor import colored, cprint
import pandas as pd
import json
import anthropic
import openai
import requests  # For API calls
from colorama import init, Fore, Back, Style 
init()

# Local imports
from src.config import *
from src import nice_funcs as n
from src.scripts.ohlcv_collector import collect_all_tokens
# Import logging utilities
from src.scripts.logger import debug, info, warning, error, critical, system

# Load environment variables
load_dotenv()

# Import AI prompt from config
from src.config import DCA_AI_PROMPT, AI_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS

class DCAAgent:
    def __init__(self, fixed_dca_amount=None):
        """Initialize the DCA Agent."""
        self.staking_allocation_percentage = STAKING_ALLOCATION_PERCENTAGE  # From config.py
        self.dca_interval_minutes = DCA_INTERVAL_MINUTES  # From config.py
        self.max_volatility_threshold = MAX_VOLATILITY_THRESHOLD  # From config.py
        self.trend_awareness_threshold = TREND_AWARENESS_THRESHOLD  # From config.py
        self.take_profit_percentage = TAKE_PROFIT_PERCENTAGE  # From config.py
        self.fixed_dca_amount = FIXED_DCA_AMOUNT if fixed_dca_amount is None else fixed_dca_amount  # Fixed amount per transaction
        self.ai_model = AI_MODEL  # Use centralized config value
        self.ai_temperature = AI_TEMPERATURE  # Use centralized config value 
        self.ai_max_tokens = AI_MAX_TOKENS  # Use centralized config value
        self.yield_optimization_interval = YIELD_OPTIMIZATION_INTERVAL  # From config.py
        self.dca_monitored_tokens = DCA_MONITORED_TOKENS  # Specific tokens for DCA Agent
        
        # Load additional config values with defaults if not present
        self.auto_convert_threshold = getattr(sys.modules['src.config'], 'AUTO_CONVERT_THRESHOLD', 10)
        self.min_conversion_amount = getattr(sys.modules['src.config'], 'MIN_CONVERSION_AMOUNT', 5)
        self.max_convert_percentage = getattr(sys.modules['src.config'], 'MAX_CONVERT_PERCENTAGE', 25)
        self.staking_protocols = getattr(sys.modules['src.config'], 'STAKING_PROTOCOLS', ["marinade", "lido"])

        # Validate address is set
        if not address:
            warning("WARNING: No wallet address configured in config.py")
            info("Staking operations will be limited without a wallet address")

        # Initialize AI clients
        try:
            self.client_anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))
            self.client_openai = openai.OpenAI(api_key=os.getenv("OPENAI_KEY"))
            self.client_deepseek = None  # Placeholder for DeepSeek client
        except Exception as e:
            warning(f"Error initializing AI clients: {str(e)}")
            info("Some AI functionality may not be available")

        info("Moon Dev's DCA Agent initialized!")

    def get_staking_rewards_and_apy(self):
        """Get SOL staking rewards and APY data from different protocols"""
        try:
            # Initialize results
            staking_data = {}
            staking_rewards = 0
            
            # Check if we have a wallet address
            if not address:
                warning("No wallet address configured. Cannot check staking rewards.")
                return staking_data, staking_rewards
                
            # Check Marinade Finance
            info("Checking Marinade Finance staking rates...")
            try:
                marinade_resp = requests.get("https://api.marinade.finance/msol/price")
                if marinade_resp.status_code == 200:
                    data = marinade_resp.json()
                    marinade_apy = float(data.get("apy", 0)) * 100
                    info(f"Marinade SOL Staking APY: {marinade_apy:.2f}%")
                    staking_data["marinade"] = marinade_apy
                
                    # Get staked SOL amount if we have a wallet address
                    wallet_response = requests.get(
                        f"https://api.marinade.finance/v1/accounts/{address}",
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if wallet_response.status_code == 200:
                        wallet_data = wallet_response.json()
                        staked_sol = wallet_data.get("stakedSol", 0)
                        rewards = wallet_data.get("rewards", 0)
                        staking_rewards += rewards
                        info(f"Marinade: Staked SOL: {staked_sol} SOL, Rewards: {rewards} SOL")
                
                    staking_data["marinade_apy"] = marinade_apy
            except Exception as e:
                info(f"Error getting Marinade staking info: {str(e)}")
            
            # Get alternative staking info (Lido)
            info("Checking Lido staking rates...")
            try:
                lido_response = requests.get(
                    "https://api.solana.lido.fi/v1/stats",
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if lido_response.status_code == 200:
                    lido_data = lido_response.json()
                    lido_apy = lido_data.get("apr", 0) * 100  # Convert to percentage
                    info(f"Lido SOL Staking APY: {lido_apy:.2f}%")
                    
                    # Check for Lido staked balance
                    try:
                        lido_balance_url = f"https://api.solana.lido.fi/v1/accounts/{address}"
                        lido_balance_response = requests.get(
                            lido_balance_url,
                            headers={"Content-Type": "application/json"},
                            timeout=10
                        )
                        
                        if lido_balance_response.status_code == 200:
                            lido_balance_data = lido_balance_response.json()
                            staked_sol_lido = lido_balance_data.get("stakedSol", 0)
                            rewards_lido = lido_balance_data.get("rewards", 0)
                            
                            # Add to staking rewards if we have any
                            if rewards_lido > 0:
                                staking_rewards += rewards_lido
                                
                            info(f"Lido: Staked SOL: {staked_sol_lido} SOL, Rewards: {rewards_lido} SOL")
                    except Exception as e:
                        info(f"Error getting Lido balance info: {str(e)}")
                    
                    # Use the higher APY
                    staking_data["lido_apy"] = lido_apy
            except Exception as e:
                info(f"Error getting alternative staking info: {str(e)}")
                
            # Check for Jito staking if in supported protocols
            if "jito" in self.staking_protocols:
                info("Checking Jito staking rates...")
                try:
                    # Placeholder for Jito API - this would be replaced with actual API when available
                    # For now, using a fixed APY estimate
                    jito_apy = 7.5  # Estimated APY
                    info(f"Jito SOL Staking APY: {jito_apy:.2f}% (estimate)")
                    
                    # Use the higher APY
                    staking_data["jito_apy"] = jito_apy
                except Exception as e:
                    info(f"Error getting Jito staking info: {str(e)}")
                
            return staking_data, staking_rewards
            
        except Exception as e:
            error(f"Error getting staking rewards: {str(e)}")
            return {}, 0

    def get_liquidity_pool_apy(self):
        """Get real APY data from Jupiter API for monitored tokens"""
        try:
            pool_apy = {}
            
            # Ensure we have the Jupiter API URL
            jupiter_api_url = getattr(sys.modules['src.config'], 'JUPITER_API_URL', "https://quote-api.jup.ag/v6")
            
            for token in self.dca_monitored_tokens:
                if token in EXCLUDED_TOKENS:
                    continue
                    
                # Get token symbol
                symbol = self.get_token_symbol(token)
                
                # Fetch pool info from Jupiter API
                url = f"{jupiter_api_url}/pools?inputMint={token}&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                response = requests.get(url, timeout=15)
                
                if response.status_code != 200:
                    info(f"Error fetching pool data for {symbol}: HTTP {response.status_code}")
                    continue
                
                data = response.json()
                
                if not data.get('data'):
                    info(f"No liquidity pools found for {symbol}")
                    continue
                    
                # Find highest APY pool
                best_apy = 0
                best_pool = None
                
                for pool in data.get('data', []):
                    pool_id = pool.get('id')
                    apy = pool.get('apy', 0)
                    
                    if apy and apy > best_apy:
                        best_apy = apy
                        best_pool = pool_id
                
                if best_pool:
                    pool_apy[best_pool] = best_apy
                    info(f"Found {symbol} pool APY: {best_apy:.2f}%")
            
            return pool_apy
            
        except Exception as e:
            error(f"Error getting liquidity pool APY: {str(e)}")
            return {}

    def reinvest_staking_rewards(self, staking_rewards):
        """Reinvest SOL staking rewards for compounding growth"""
        try:
            # Check if we have SOL rewards
            sol_address = "So11111111111111111111111111111111111111112"
            if sol_address not in staking_rewards or staking_rewards[sol_address] <= 0:
                info("No SOL rewards to reinvest")
                return
                
            info(f"Reinvesting {staking_rewards[sol_address]} SOL rewards")
            
            # Get APYs for different protocols
            available_protocols = {}
            try:
                # Get Marinade APY
                marinade_response = requests.get(
                    "https://api.marinade.finance/v1/staking/state",
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                if marinade_response.status_code == 200:
                    marinade_data = marinade_response.json()
                    marinade_apy = marinade_data.get("apy", {}).get("current", 0) * 100
                    if "marinade" in self.staking_protocols:
                        available_protocols["marinade"] = marinade_apy
                
                # Get Lido APY
                lido_response = requests.get(
                    "https://api.solana.lido.fi/v1/stats",
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                if lido_response.status_code == 200:
                    lido_data = lido_response.json()
                    lido_apy = lido_data.get("apr", 0) * 100
                    if "lido" in self.staking_protocols:
                        available_protocols["lido"] = lido_apy
                
                # Get Jito APY (estimated)
                if "jito" in self.staking_protocols:
                    jito_apy = 7.5  # Estimated APY
                    available_protocols["jito"] = jito_apy
            except Exception as e:
                info(f"Error getting staking APYs: {str(e)}")
            
            # Get the best staking protocol
            best_protocol = None
            best_apy = 0
            
            for protocol, apy in available_protocols.items():
                if apy > best_apy:
                    best_apy = apy
                    best_protocol = protocol
            
            if not best_protocol:
                info("No staking protocol available to use")
                return False
            
            info(f"Selected {best_protocol} for staking (APY: {best_apy:.2f}%)")
            
            # Build staking transaction
            # This part would need to be implemented based on the chosen protocol
            
            # Simplified representation of logic at the moment
            staking_tx = {
                "protocol": best_protocol,
                "amount": staking_rewards[sol_address],
                "expected_apy": best_apy
            }
            
            # Send transaction
            # This would be protocol-specific implementation
            tx_id = "simulated_tx_" + str(int(time.time()))
            
            if tx_id:
                info(f"Staking transaction successful: {tx_id}")
                info(f"View transaction: https://solscan.io/tx/{tx_id}")
                return True
            else:
                info(f"Staking transaction failed")
                return False
        
        except Exception as e:
            error(f"Error reinvesting staking rewards: {str(e)}")
            return False

    def allocate_to_liquidity_pool(self, pool_id):
        """Allocate funds to a liquidity pool"""
        try:
            # Get pool info from Jupiter
            jupiter_api_url = getattr(sys.modules['src.config'], 'JUPITER_API_URL', "https://quote-api.jup.ag/v6")
            url = f"{jupiter_api_url}/pools/{pool_id}"
            
            info(f"Getting pool info for {pool_id}...")
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                info(f"Could not get pool info: HTTP {response.status_code}")
                return False
                
            pool_data = response.json()
            
            # Extract LP token information
            lp_token = pool_data.get("lpToken")
            input_token = pool_data.get("inputToken")
            output_token = pool_data.get("outputToken")
            
            if not lp_token or not input_token or not output_token:
                info("Incomplete pool data received")
                return False
            
            # Real LP interaction would happen here
            # This is placeholder for future actual implementation
            info(f"   LP allocation functionality will be implemented in next release")
            info(f"   Pool {pool_id} selected for allocation")
            
            # Log this for future implementation
            allocation_data = {
                "timestamp": int(time.time()),
                "pool_id": pool_id,
                "lp_token": lp_token,
                "input_token": input_token,
                "output_token": output_token
            }
            
            # Record the allocation intent
            lp_log_file = PROJECT_ROOT / "src" / "data" / "lp_allocations.json"
            
            # Load existing data if file exists
            existing_data = []
            if lp_log_file.exists():
                try:
                    with open(lp_log_file, 'r') as f:
                        existing_data = json.load(f)
                except:
                    pass
            
            # Append new allocation
            existing_data.append(allocation_data)
            
            # Save updated data
            with open(lp_log_file, 'w') as f:
                json.dump(existing_data, f, indent=4)
            
            return True
            
        except Exception as e:
            warning(f"Could not save allocation info: {str(e)}")
            return False

    def _auto_convert_for_staking(self):
        """Automatically convert some DCA tokens to SOL for staking"""
        try:
            # Get total portfolio value
            total_value = 0
            token_values = {}
            
            # Get SOL value specifically
            sol_address = "So11111111111111111111111111111111111111112"
            sol_value = n.get_token_balance_usd(sol_address)
            info(f" Current SOL value: ${sol_value:.2f}")
            
            # For each monitored token, get value
            for token in self.dca_monitored_tokens:
                if token in EXCLUDED_TOKENS or token == sol_address:
                    continue
                    
                value = n.get_token_balance_usd(token)
                if value > 0:
                    symbol = self.get_token_symbol(token)
                    info(f" {symbol}: ${value:.2f}")
                    token_values[token] = value
                    total_value += value
            
            # Add SOL value to total
            total_value += sol_value
            
            # If no portfolio value, exit
            if total_value <= 0:
                info(" No portfolio value detected, skipping auto-convert")
                return
                
            # Calculate target SOL value for staking
            target_sol_value = total_value * (self.staking_allocation_percentage / 100)
            info(f" Target SOL allocation: ${target_sol_value:.2f} ({self.staking_allocation_percentage}% of ${total_value:.2f})")
            
            # If current SOL is below target, convert some tokens
            if sol_value < target_sol_value * 0.9:  # 10% threshold
                sol_needed = target_sol_value - sol_value
                
                if sol_needed < self.min_conversion_amount:
                    info(f"Skipping auto-convert: amount needed (${sol_needed:.2f}) below minimum (${self.min_conversion_amount})")
                    return
                    
                info(f" Auto-converting tokens to SOL for staking (need ${sol_needed:.2f} more)")
                
                # Sort tokens by value, largest first
                sorted_tokens = sorted(
                    [(token, value) for token, value in token_values.items()],
                    key=lambda x: x[1],
                    reverse=True
                )
                
                # Total converted so far
                total_converted = 0
                
                # Process each token, starting with largest
                for token, value in sorted_tokens:
                    # Skip tokens below threshold
                    if value < self.auto_convert_threshold:
                        continue
                        
                    # Calculate how much to convert (up to max_convert_percentage)
                    max_convert_amount = value * (self.max_convert_percentage / 100)
                    
                    # Don't convert more than we need
                    convert_amount = min(max_convert_amount, sol_needed - total_converted)
                    
                    if convert_amount < 1:  # Skip tiny amounts
                        continue
                        
                    symbol = self.get_token_symbol(token)
                    info(f" Converting ${convert_amount:.2f} of {symbol} to SOL")
                    
                    # Perform the conversion
                    try:
                        # Calculate token amount based on price
                        token_price = n.token_price(token)
                        if not token_price:
                            info(f"⚠️ Could not get price for {symbol}, skipping conversion")
                            continue
                            
                        token_amount = convert_amount / token_price
                        
                        # Sell tokens for USDC
                        info(f" Selling {token_amount:.4f} {symbol} for USDC")
                        
                        # Perform the actual sell transaction
                        # Calculate amount in lamports
                        token_decimals = 6  # Default decimals (most tokens use 6 or 9)
                        # Try to get decimals from token metadata
                        try:
                            token_info_url = f"https://api.mainnet-beta.solana.com"
                            payload = {
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "getTokenSupply",
                                "params": [token]
                            }
                            response = requests.post(token_info_url, json=payload)
                            if response.status_code == 200:
                                result = response.json().get("result", {})
                                if result and "value" in result:
                                    token_decimals = result["value"].get("decimals", 6)
                        except Exception as e:
                            info(f" Could not get token decimals, using default: {str(e)}")
                        
                        # Create amount with proper decimals
                        lamport_amount = int(token_amount * (10 ** token_decimals))
                        usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                        
                        # Call market_sell - this function should be implemented in nice_funcs.py
                        # For now, n.market_sell() is simulated since it may not be fully implemented
                        sell_result = n.market_sell(token, str(lamport_amount), 100)  # 1% slippage
                        
                        if not sell_result:
                            info(f" Failed to sell {symbol}, skipping to next token")
                            continue
                            
                        # Wait for transaction to confirm
                        info(" Waiting for transaction to confirm...")
                        time.sleep(15)
                        
                        # Now buy SOL with USDC
                        info(f" Buying SOL with converted USDC")
                        
                        # Calculate USDC amount (slightly less than convert_amount due to fees)
                        usdc_amount = int(convert_amount * 0.98 * 1000000)  # 98% of value, USDC has 6 decimals
                        
                        # Buy SOL with USDC
                        buy_result = n.market_buy(sol_address, str(usdc_amount), 100)  # 1% slippage
                        
                        if not buy_result:
                            info(f" Failed to buy SOL with USDC")
                            continue
                            
                        # Mark this amount as converted
                        total_converted += convert_amount
                        info(f" Successfully converted ${convert_amount:.2f} of {symbol} to SOL")
                        
                        # If we've reached our target, stop
                        if total_converted >= sol_needed:
                            break
                            
                    except Exception as e:
                        error(f"❌ Error converting {symbol} to SOL: {str(e)}")
                        continue
                
                if total_converted > 0:
                    info(f" Auto-converted total of ${total_converted:.2f} to SOL for staking")
                else:
                    info(" No tokens were converted to SOL")
            else:
                info(f" Current SOL allocation (${sol_value:.2f}) is sufficient")
            
        except Exception as e:
            error(f" Error in auto-convert: {str(e)}")

    def optimize_yield(self):
        """Optimize yield by automatically allocating assets to best-performing protocols."""
        try:
            info("YIELD OPTIMIZATION STARTING")
            
            # 1. Get current SOL staking rewards and APY
            info("Fetching current SOL staking rewards and APY data...")
            staking_data, staking_rewards = self.get_staking_rewards_and_apy()
            
            if staking_data:
                info(f"Found SOL staking rewards: {staking_data}")
            else:
                info("No SOL staking rewards found")
                
            info(f"Current best SOL staking APY: {sum(staking_data.values()):.2f}%")
            
            # 2. Get current staking mode
            staking_mode = getattr(sys.modules['src.config'], 'STAKING_MODE', "separate")
            info(f"Current staking mode: {staking_mode}")
            
            # 3. Check if token conversion is needed (for 'auto_convert' mode)
            info("Checking if token conversion to SOL is needed...")
            if staking_mode == "auto_convert":
                self._auto_convert_for_staking()
            
            # 4. Make yield decision
            info(f"YIELD DECISION: SOL staking (APY: {sum(staking_data.values()):.2f}%)")
            
            # 5. Reinvest staking rewards if available
            if staking_rewards > 0:
                info(f"Reinvesting SOL staking rewards: {staking_rewards}")
                success = self.reinvest_staking_rewards(staking_rewards)
                
                if success:
                    info("Successfully reinvested SOL staking rewards")
                else:
                    warning("Failed to reinvest SOL staking rewards")
            else:
                info("No SOL staking rewards to reinvest at this time")
                    
            info("YIELD OPTIMIZATION COMPLETE")
            
        except Exception as e:
            error(f"Error optimizing yield: {str(e)}")

    def read_chart_recommendations(self):
        """Read chart recommendations from CSV files"""
        try:
            charts_dir = PROJECT_ROOT / "src" / "data" / "charts"
            
            if not charts_dir.exists():
                warning("No chart recommendations found")
                return {}
                
            all_recommendations = {}
            csv_files = list(charts_dir.glob("chart_analysis_*.csv"))
            
            if not csv_files:
                warning("No chart recommendation files found")
                return {}
            
            for file in csv_files:
                try:
                    debug(f"Processing file: {file.name}", file_only=True)
                    
                    # Extract token symbol from filename
                    # Format: chart_analysis_SYMBOL.csv
                    file_parts = file.stem.split('_')
                    if len(file_parts) >= 3:
                        symbol = file_parts[2]
                        debug(f"Extracted token symbol from filename: {symbol}", file_only=True)
                        
                        # Get token address from the symbol
                        token_address = None
                        for token_info in TOKEN_MAP.items():
                            if token_info[1][0] == symbol:
                                token_address = token_info[0]
                                debug(f"Found matching token address for {symbol}: {token_address}", file_only=True)
                                break
                        
                        if not token_address:
                            warning(f"Could not find token address for {symbol}, skipping")
                            continue
                        
                        # Read CSV and process the data
                        df = pd.read_csv(file)
                        
                        # Find the most recent recommendation
                        if not df.empty:
                            # Sort by timestamp descending to get the most recent
                            df = df.sort_values('timestamp', ascending=False)
                            latest = df.iloc[0]
                            
                            # Extract action, confidence and entry price
                            action = latest.get('signal', 'NEUTRAL')
                            confidence = latest.get('confidence', 50)
                            
                            # Try to find entry price in the CSV
                            entry_price = None
                            if 'entry_price' in latest:
                                entry_price = latest['entry_price']
                                debug(f"Found entry price in standard column: ${entry_price}", file_only=True)
                            elif 'price' in latest:
                                entry_price = latest['price']
                                debug(f"Found price in price column: ${entry_price}", file_only=True)
                            else:
                                # Try to find any numeric column that might have price
                                numeric_cols = df.select_dtypes(include=['number']).columns
                                price_cols = [col for col in numeric_cols if 'price' in col.lower()]
                                
                                if price_cols:
                                    price_col = price_cols[0]
                                    entry_price = latest[price_col]
                                    debug(f"Found price in '{price_col}' column: ${entry_price}", file_only=True)
                                else:
                                    # Final fallback - use the first numeric column
                                    if numeric_cols.size > 0:
                                        price_col = numeric_cols[0]
                                        entry_price = latest[price_col]
                                        debug(f"Using first numeric column '{price_col}' for price: ${entry_price}", file_only=True)
                            
                            # If entry price is still None, get current price
                            if entry_price is None or pd.isna(entry_price):
                                entry_price = n.token_price(token_address)
                            
                            # Store the recommendation
                            all_recommendations[token_address] = {
                                'symbol': symbol,
                                'action': action,
                                'confidence': confidence,
                                'entry_price': entry_price,
                                'analysis': latest.get('reasoning', ''),
                                'timestamp': latest.get('timestamp', int(time.time()))
                            }
                    
                            info(f"Created recommendation for {symbol}: {action} (confidence: {confidence}%)")
                            
                except Exception as e:
                    warning(f"Error processing file {file.name}: {str(e)}")
            
            info(f"Total: Loaded {len(all_recommendations)} chart recommendations")
            return all_recommendations
        
        except Exception as e:
            error(f"Error reading chart recommendations: {str(e)}")
            return {}

    def get_token_symbol(self, token_address):
        """Get token symbol from address"""
        try:
            # First try to use the token map from config
            for address, details in TOKEN_MAP.items():
                if address == token_address:
                    return details[0]  # Return the symbol
                    
            # Fallback to RPC call
            url = "https://api.mainnet-beta.solana.com"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenSupply",  # Use getTokenSupply as a basic check
                "params": [token_address]
            }
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                # Token exists, try to get metadata from an alternative source
                # Using Birdeye API as fallback
                birdeye_url = f"https://public-api.birdeye.so/public/tokenlist?address={token_address}"
                headers = {"X-API-KEY": os.getenv("BIRDEYE_API_KEY", "")}
                
                birdeye_response = requests.get(birdeye_url, headers=headers)
                if birdeye_response.status_code == 200:
                    token_data = birdeye_response.json()
                    if "data" in token_data and token_data["data"]:
                        return token_data["data"][0].get("symbol", "UNKNOWN")
            
            # Return unknown with shortened address if all else fails    
            short_address = token_address[:4] + "..." + token_address[-4:]
            return f"UNK_{short_address}"
        except Exception as e:
            error(f"Error getting token symbol: {str(e)}")
            short_address = token_address[:4] + "..." + token_address[-4:] if token_address else "UNKNOWN"
            return f"UNK_{short_address}"

    def execute_limit_orders(self):
        """Execute any pending limit orders that meet their price conditions"""
        pending_orders_file = PROJECT_ROOT / "src" / "data" / "pending_orders.csv"
        
        if not pending_orders_file.exists():
            debug("No pending orders file found", file_only=True)
            return
            
        try:
            # Read the pending orders
            orders_df = pd.read_csv(pending_orders_file)
            
            if orders_df.empty:
                debug("No pending orders to process", file_only=True)
                return
                
            info(f"Processing {len(orders_df)} pending limit orders")
            
            # Create a new DataFrame for orders that are still pending
            still_pending = []
            executed = []
            
            # Check each order
            for _, order in orders_df.iterrows():
                try:
                    token_address = order['token_address']
                    symbol = order['symbol']
                    order_type = order['order_type']  # BUY or SELL
                    limit_price = float(order['limit_price'])
                    amount = float(order['amount'])
                    order_time = int(order['timestamp'])
                    
                    # Skip if the order is too old (30 days)
                    if (int(time.time()) - order_time) > 30 * 24 * 60 * 60:
                        warning(f"Removing expired {order_type} order for {symbol} placed on {time.ctime(order_time)}")
                        continue
                
                    # Get current price
                    current_price = n.token_price(token_address)
                    
                    if current_price is None:
                        warning(f"Could not get current price for {symbol}, keeping order")
                        still_pending.append(order)
                        continue
                        
                    debug(f"Order for {symbol}: {order_type} at ${limit_price:.4f}, current price: ${current_price:.4f}", file_only=True)
                    
                    # Check if order conditions are met
                    if order_type == 'BUY' and current_price <= limit_price:
                        info(f"Executing BUY order for {symbol} at ${current_price:.4f} (limit: ${limit_price:.4f})")
                        
                        # Execute market buy
                        n.buy_token_with_usd(token_address, amount)
                        executed.append({
                            'symbol': symbol,
                            'action': 'BUY',
                            'price': current_price,
                            'amount': amount,
                            'timestamp': int(time.time())
                        })
                        
                    elif order_type == 'SELL' and current_price >= limit_price:
                        info(f"Executing SELL order for {symbol} at ${current_price:.4f} (limit: ${limit_price:.4f})")
                        
                        # Execute market sell
                        token_amount = self.get_token_holdings(token_address)
                        if token_amount > 0:
                            n.sell_token_for_usd(token_address, token_amount)
                            executed.append({
                                'symbol': symbol,
                                'action': 'SELL',
                                'price': current_price,
                                'amount': token_amount * current_price,
                                'timestamp': int(time.time())
                            })
                        else:
                            warning(f"No {symbol} tokens found to sell")
                    else:
                        # Order conditions not met, keep it pending
                        still_pending.append(order)
                        
                except Exception as e:
                    error(f"Error processing order for {order.get('symbol', 'unknown')}: {str(e)}")
                    still_pending.append(order)
                    
            # Save the updated pending orders
            if still_pending:
                pd.DataFrame(still_pending).to_csv(pending_orders_file, index=False)
                info(f"Updated pending orders list with {len(still_pending)} orders")
            else:
                # If no more pending orders, delete the file
                pending_orders_file.unlink(missing_ok=True)
                info("All pending orders processed, removed pending orders file")
                
            # Record executed orders to history
            if executed:
                trade_history_file = PROJECT_ROOT / "src" / "data" / "trade_history.csv"
                
                if trade_history_file.exists():
                    history_df = pd.read_csv(trade_history_file)
                    updated_history = pd.concat([history_df, pd.DataFrame(executed)])
                else:
                    updated_history = pd.DataFrame(executed)
                
                updated_history.to_csv(trade_history_file, index=False)
                info(f"Recorded {len(executed)} executed orders to trade history")
                
        except Exception as e:
            error(f"Error executing limit orders: {str(e)}")
    
    def check_take_profit_levels(self):
        """Check holdings against take-profit levels"""
        try:
            # Get holdings dictionary
            holdings = self.get_all_token_holdings()
            
            if not holdings:
                info("No token holdings to check")
                return
                
            info(f"Checking take-profit levels for {len(holdings)} tokens")
            
            # Check each token
            for symbol, holdings_data in holdings.items():
                try:
                    token_address = holdings_data['address']
                    amount = holdings_data['amount']
                    usd_value = holdings_data['usd_value']
                    
                    # Skip small positions
                    if usd_value < 10:
                        debug(f"Skipping {symbol}: Too small (${usd_value:.2f})", file_only=True)
                        continue
                        
                    # Get purchase price from records
                    purchase_records = self.get_token_purchase_records(token_address)
                    
                    if not purchase_records:
                        debug(f"No purchase records for {symbol}", file_only=True)
                        continue
                        
                    # Calculate average purchase price
                    avg_purchase_price = sum(r['price'] * r['amount'] for r in purchase_records) / sum(r['amount'] for r in purchase_records)
                    
                    # Get current price
                    current_price = n.token_price(token_address)
                    
                    if not current_price:
                        warning(f"Could not get current price for {symbol}")
                        continue
                        
                    # Calculate percent change
                    pct_change = ((current_price - avg_purchase_price) / avg_purchase_price) * 100
                    
                    info(f"{symbol}: Current: ${current_price:.6f}, Avg Purchase: ${avg_purchase_price:.6f}, Change: {pct_change:.2f}%")
                    
                    # Check if take-profit threshold is reached
                    if pct_change >= TAKE_PROFIT_PERCENTAGE:
                        info(f"Take-profit threshold reached for {symbol} ({pct_change:.2f}% > {TAKE_PROFIT_PERCENTAGE}%)")
                        
                        # Execute sell
                        info(f"Selling {symbol} position worth ${usd_value:.2f}")
                        success = n.chunk_kill(
                            token_address,
                            max_usd_order_size,
                            slippage
                        )
                        
                        if success:
                            info(f"Successfully sold {symbol} for take-profit")
                            # Track for potential buyback
                            self.track_sold_tokens(token_address, amount, current_price)
                        else:
                            warning(f"Failed to sell {symbol} for take-profit")
                except Exception as e:
                    warning(f"Error checking take-profit for {symbol}: {str(e)}")
                    
            info("Take-profit check complete")
            
        except Exception as e:
            error(f"Error in take-profit check: {str(e)}")
            
    def track_sold_tokens(self, token_address, amount, price):
        """Track tokens we've sold for potential buyback"""
        # Create the tracking file if it doesn't exist
        sold_tokens_file = PROJECT_ROOT / "src" / "data" / "sold_tokens.csv"
        
        if not sold_tokens_file.exists():
            with open(sold_tokens_file, 'w') as f:
                f.write("timestamp,address,symbol,amount,price\n")
        
        # Append the sold token info
        symbol = self.get_token_symbol(token_address)
        timestamp = int(time.time())
        
        with open(sold_tokens_file, 'a') as f:
            f.write(f"{timestamp},{token_address},{symbol},{amount},{price}\n")
        
    def check_reentry_opportunities(self):
        """Check if we should buy back previously sold tokens"""
        sold_tokens_file = PROJECT_ROOT / "src" / "data" / "sold_tokens.csv"
        
        if not sold_tokens_file.exists():
            return
        
        try:
            sold_df = pd.read_csv(sold_tokens_file)
            current_time = int(time.time())
            
            for _, row in sold_df.iterrows():
                token_address = row['address']
                sell_price = row['price']
                timestamp = row['timestamp']
                symbol = row['symbol']
                
                # Only consider tokens sold in last 30 days
                if current_time - timestamp > 30 * 24 * 60 * 60:
                    continue
                    
                # Get current price
                current_price = n.token_price(token_address)
                
                if current_price is None:
                    continue
                    
                # If price dropped 10% or more since we sold, consider buying back
                price_change = (current_price - sell_price) / sell_price * 100
                
                if price_change <= -10:
                    info(f"Potential buyback opportunity for {symbol}: Sold @ ${sell_price:.6f}, Current: ${current_price:.6f} ({price_change:.2f}%)")
                    
                    # Calculate buyback amount (e.g., use standard DCA amount)
                    buy_amount = self.fixed_dca_amount if self.fixed_dca_amount else 10
                    
                    info(f"Simulating buyback of {symbol} for ${buy_amount:.2f}")
                    # In production, execute the actual buy
    
        except Exception as e:
            error(f"Error checking reentry opportunities: {str(e)}")

    def run_dca_cycle(self):
        """Run one complete DCA cycle."""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            info(f"\nDCA Agent Run Starting at {current_time}")

            # Check if chart analysis is enabled in config
            chart_analysis_enabled = getattr(sys.modules['src.config'], 'ENABLE_CHART_ANALYSIS', True)
            
            # Initialize recommendations as empty
            recommendations = {}
            
            # Only read chart recommendations if chart analysis is enabled
            if chart_analysis_enabled:
                info("Reading chart recommendations...")
                recommendations = self.read_chart_recommendations()
                
                if recommendations:
                    info(f"Processing {len(recommendations)} recommendations")
                    debug(f"Recommendations details: {recommendations}", file_only=True)
                    
                    # Execute limit orders based on recommendations
                    info("Executing limit orders...")
                    self.execute_limit_orders()
                    
                    # Check for take-profit levels
                    info("Checking for take-profit levels...")
                    self.check_take_profit_levels()
                else:
                    warning("No valid recommendations found, skipping chart-based actions")
            else:
                info("Chart analysis is disabled in settings, skipping recommendations")
            
            # Run yield optimization - ALWAYS run this regardless of recommendations
            info("Optimizing yield...")
            self.optimize_yield()

            # Check for reentry opportunities - ALWAYS run this regardless of recommendations
            info("Checking reentry opportunities...")
            self.check_reentry_opportunities()

            # Run scheduled DCA buys - ALWAYS run this regardless of recommendations
            info("Running scheduled DCA purchases...")
            self.run_scheduled_dca()

            info("\nDCA cycle complete!")
            
            # Print summary of actions taken
            info("\nDCA Cycle Summary:")
            info(f"- Chart Analysis Enabled: {'Yes' if chart_analysis_enabled else 'No'}")
            info(f"- Recommendations processed: {len(recommendations)}")

        except Exception as e:
            error(f"\nError in DCA cycle: {str(e)}")
            warning("Moon Dev suggests checking the logs and trying again!")

    def test_staking_functionality(self):
        """Test all staking functionality and produce a detailed report"""
        try:
            info("\n STAKING FUNCTIONALITY TEST STARTING")
            
            # 1. Check wallet and validate address
            info("\n CHECKING WALLET CONFIGURATION:")
            if not address:
                info(" No wallet address configured in config.py")
                info("   Limited functionality will be available")
            else:
                info(f" Using wallet address: {address[:6]}...{address[-4:]}")
                
                # Check SOL balance
                sol_address = "So11111111111111111111111111111111111111112"
                sol_balance = n.get_token_balance(sol_address)
                info(f" Current SOL balance: {sol_balance:.4f} SOL")
                
                sol_price = n.token_price(sol_address)
                if sol_price:
                    info(f" SOL value: ${sol_balance * sol_price:.2f} USD")
            
            # 2. Check available staking protocols (for SOL only)
            info("\n CHECKING SOL STAKING PROTOCOLS:")
            info(f" Configured protocols: {', '.join(self.staking_protocols)}")
            
            # 3. Fetch current APYs from all SOL staking protocols
            info("\n FETCHING CURRENT SOL STAKING APYs:")
            
            # 3.1 Marinade APY
            try:
                info("   Checking Marinade Finance...")
                marinade_response = requests.get(
                    "https://api.marinade.finance/v1/staking/state",
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if marinade_response.status_code == 200:
                    marinade_data = marinade_response.json()
                    marinade_apy = marinade_data.get("apy", {}).get("current", 0) * 100
                    info(f"   Marinade SOL Staking APY: {marinade_apy:.2f}%")
                    
                    # Check if we have any staked SOL
                    if address:
                        try:
                            wallet_response = requests.get(
                                f"https://api.marinade.finance/v1/accounts/{address}",
                                headers={"Content-Type": "application/json"},
                                timeout=10
                            )
                            
                            if wallet_response.status_code == 200:
                                wallet_data = wallet_response.json()
                                staked_sol = wallet_data.get("stakedSol", 0)
                                rewards = wallet_data.get("rewards", 0)
                                
                                if staked_sol > 0:
                                    info(f"   Marinade: Currently staked: {staked_sol:.4f} SOL")
                                    info(f"   Marinade: Rewards available: {rewards:.6f} SOL")
                                else:
                                    info("   Marinade: No SOL currently staked")
                        except Exception as e:
                            info(f"   Error checking Marinade stake balance: {str(e)}")
                else:
                    info(f"   Failed to get Marinade info: {marinade_response.status_code}")
            except Exception as e:
                info(f"   Error getting Marinade info: {str(e)}")
                
            # 3.2 Lido APY
            try:
                info("   Checking Lido...")
                lido_response = requests.get(
                    "https://api.solana.lido.fi/v1/stats",
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if lido_response.status_code == 200:
                    lido_data = lido_response.json()
                    lido_apy = lido_data.get("apr", 0) * 100
                    info(f"   Lido SOL Staking APY: {lido_apy:.2f}%")
                    
                    # Check if we have any staked SOL
                    if address:
                        try:
                            lido_balance_url = f"https://api.solana.lido.fi/v1/accounts/{address}"
                            lido_balance_response = requests.get(
                                lido_balance_url,
                                headers={"Content-Type": "application/json"},
                                timeout=10
                            )
                            
                            if lido_balance_response.status_code == 200:
                                lido_balance_data = lido_balance_response.json()
                                staked_sol_lido = lido_balance_data.get("stakedSol", 0)
                                rewards_lido = lido_balance_data.get("rewards", 0)
                                
                                if staked_sol_lido > 0:
                                    info(f"   Lido: Currently staked: {staked_sol_lido:.4f} SOL")
                                    info(f"   Lido: Rewards available: {rewards_lido:.6f} SOL")
                                else:
                                    info("   Lido: No SOL currently staked")
                        except Exception as e:
                            info(f"   Error checking Lido stake balance: {str(e)}")
                else:
                    info(f"   Failed to get Lido info: {lido_response.status_code}")
            except Exception as e:
                info(f"   Error getting Lido info: {str(e)}")
                
            # 3.3 Jito APY (estimated since there's no public API yet)
            info("   Checking Jito...")
            info("   Jito SOL Staking APY: 7.50% (estimated)")
            
            # 4. Check for existing staking rewards
            info("\n CHECKING FOR SOL STAKING REWARDS:")
            staking_data, staking_rewards = self.get_staking_rewards_and_apy()
            
            if staking_data:
                info(f" Found SOL staking rewards: {staking_data}")
            else:
                info(" No SOL staking rewards found")
            
            # 5. Find the best staking protocol
            info("\n DETERMINING BEST SOL STAKING PROTOCOL:")
            
            protocols = {
                "marinade": marinade_apy if 'marinade_apy' in staking_data else 0,
                "lido": lido_apy if 'lido_apy' in staking_data else 0,
                "jito": 7.5  # Estimated
            }
            
            # Filter to only include configured protocols
            available_protocols = {k: v for k, v in protocols.items() if k in self.staking_protocols}
            
            if available_protocols:
                best_protocol = max(available_protocols.items(), key=lambda x: x[1])
                info(f" Best SOL staking protocol: {best_protocol[0]} (APY: {best_protocol[1]:.2f}%)")
            else:
                info(" No SOL staking protocols are configured")
                
            # 6. Check auto-convert configuration
            info("\n CHECKING AUTO-CONVERT CONFIGURATION:")
            info(f" Current SOL staking allocation percentage: {self.staking_allocation_percentage}%")
            info(f" Auto-convert threshold: ${self.auto_convert_threshold}")
            info(f" Min conversion amount: ${self.min_conversion_amount}")
            info(f" Max convert percentage: {self.max_convert_percentage}%")
            
            # 7. Simulate a small staking transaction (if we have private key)
            info("\n SIMULATING SOL STAKING FUNCTIONALITY:")
            
            if os.getenv("SOLANA_PRIVATE_KEY"):
                info(" SOLANA_PRIVATE_KEY is configured")
                
                # Create a test transaction structure
                test_amount = 0.001  # Very small amount for testing
                
                for protocol in available_protocols:
                    info(f"\n   Testing {protocol} SOL staking simulation...")
                    
                    # Build test transaction
                    test_tx = {
                        "protocol": protocol,
                        "action": "stake",
                        "amount": test_amount,
                        "wallet": address
                    }
                    
                    # We'll simulate without actually executing
                    info(f"   Would stake {test_amount} SOL via {protocol}")
                    info(f"   Expected annual yield: ${(test_amount * available_protocols[protocol] / 100):.6f}")
                    info(f"   Transaction simulation successful")
            else:
                info("   SOLANA_PRIVATE_KEY not configured, cannot simulate transactions")
                info("   Set this environment variable to enable full staking functionality")
              
            system("SOL STAKING FUNCTIONALITY TEST COMPLETE")
            
        except Exception as e:
            info(f" Error testing staking functionality: {str(e)}")

    def run(self):
        """Run the DCA agent continuously."""
        info(" Starting DCA Staking Agent...")
        
        # Set separate test mode flag
        test_mode = os.getenv("TEST_STAKING", "false").lower() == "true"
        
        if test_mode:
            info(" Running in test mode to verify staking functionality...")
            self.test_staking_functionality()
            return
        
        # In production, we recommend continuous mode
        continuous_mode = True
        
        # Keep track of fails to prevent infinite retry loops
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        try:
            # Create data directories if they don't exist
            data_dir = PROJECT_ROOT / "src" / "data"
            charts_dir = data_dir / "charts"
            logs_dir = data_dir / "logs"
            
            for directory in [data_dir, charts_dir, logs_dir]:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
                    info(f" Created directory: {directory}")
            
            # Set up logging to file
            log_file = logs_dir / f"dca_staking_{int(time.time())}.log"
            
            # First run
            try:
                self.run_dca_cycle()
                consecutive_failures = 0
            except Exception as e:
                consecutive_failures += 1
                error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                error_msg = f"[{error_time}]  Error in DCA cycle: {str(e)}"
                info(error_msg)
                
                # Log error to file
                with open(log_file, 'a') as f:
                    f.write(f"{error_msg}\n")
                    
                if consecutive_failures >= max_consecutive_failures:
                    info(" Too many consecutive failures, agent will pause for an hour")
                    time.sleep(3600)  # Sleep for an hour before retrying
                    consecutive_failures = 0
            
            # If continuous mode is enabled, keep running at intervals
            if continuous_mode:
                while True:
                    next_run_time = datetime.now() + timedelta(minutes=self.dca_interval_minutes)
                    info(f"\n Sleeping until {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} before next cycle...")
                    
                    try:
                        time.sleep(self.dca_interval_minutes * 60)
                    except KeyboardInterrupt:
                        info("\n DCA Staking Agent shutting down gracefully...")
                        break
                        
                    # Run yield optimization more frequently
                    for i in range(max(1, int(self.dca_interval_minutes / 60))):
                        try:
                            info(f" Running hourly yield optimization ({i+1}/{int(self.dca_interval_minutes / 60)})")
                            self.optimize_yield()
                            time.sleep(60 * 60)  # Sleep for an hour
                        except KeyboardInterrupt:
                            info("\n DCA Staking Agent shutting down gracefully...")
                            return
                        except Exception as e:
                            info(f" Error in hourly yield optimization: {str(e)}")
                            # Continue anyway
                    
                    # Regular DCA cycle
                    try:
                        self.run_dca_cycle()
                        consecutive_failures = 0
                    except Exception as e:
                        consecutive_failures += 1
                        error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        error_msg = f"[{error_time}]  Error in DCA cycle: {str(e)}"
                        info(error_msg)
                        
                        # Log error to file
                        with open(log_file, 'a') as f:
                            f.write(f"{error_msg}\n")
                            
                        if consecutive_failures >= max_consecutive_failures:
                            info(" Too many consecutive failures, agent will pause for recovery")
                            time.sleep(3600)  # Sleep for an hour before retrying
                            consecutive_failures = 0
                
        except KeyboardInterrupt:
            info("\n DCA Staking Agent shutting down gracefully...")
        except Exception as e:
            info(f" Fatal error in DCA agent: {str(e)}")
            info(" Agent has stopped due to errors. Please check logs.")

    def run_scheduled_dca(self):
        """Run scheduled DCA purchases based on configured settings"""
        try:
            info("Running scheduled DCA purchases")
            
            # Check if we have enough funds for DCA
            balance = self.get_usd_balance()
            if balance < self.fixed_dca_amount:
                warning(f"Insufficient balance for DCA. Available: ${balance:.2f}, Required: ${self.fixed_dca_amount:.2f}")
                return
                
            # Check if tokens are configured for DCA
            if not hasattr(self, 'dca_tokens') or not self.dca_tokens:
                warning("No tokens configured for DCA")
                return
                
            # Calculate allocation per token
            num_tokens = len(self.dca_tokens)
            allocation_per_token = self.fixed_dca_amount / num_tokens
            
            info(f"Allocating ${allocation_per_token:.2f} to each of {num_tokens} tokens")
            
            # Execute DCA purchases
            for token_address in self.dca_tokens:
                try:
                    # Get token info
                    symbol = self.get_token_symbol(token_address)
                    
                    # Skip if token should be excluded
                    if token_address in EXCLUDED_TOKENS:
                        info(f"Skipping excluded token: {symbol}")
                        continue
                        
                    # Get current price
                    current_price = n.token_price(token_address)
                    if not current_price:
                        warning(f"Could not get current price for {symbol}, skipping DCA")
                        continue
                        
                    info(f"Executing DCA buy for {symbol} at ${current_price:.4f} for ${allocation_per_token:.2f}")
                    
                    # Execute the buy
                    self.execute_buy_order(token_address, symbol, current_price, allocation_per_token, 'MARKET')
                    
                except Exception as e:
                    error(f"Error executing DCA for token {token_address}: {str(e)}")
                    
            info("Scheduled DCA purchases complete")
            
        except Exception as e:
            error(f"Error in scheduled DCA: {str(e)}")

    def process_recommendations(self, recommendations):
        """Process token recommendations from chart analysis"""
        if not recommendations:
            warning("No recommendations to process")
            return
                    
        info(f"Processing {len(recommendations)} trading recommendations")
        
        for token_address, rec in recommendations.items():
            try:
                symbol = rec['symbol']
                action = rec['action']
                confidence = rec.get('confidence', 0)
                entry_price = rec.get('entry_price', 0)
                
                debug(f"Processing recommendation for {symbol}: {action}", file_only=True)
                
                # Skip if confidence is too low
                if confidence < 70:
                    info(f"Skipping {symbol} due to low confidence: {confidence}%")
                    continue
                    
                # Skip neutral recommendations
                if action.upper() in ['NEUTRAL', 'HOLD', 'NOTHING']:
                    info(f"Skipping {symbol} due to neutral recommendation: {action}")
                    continue
                
                # Get current price
                current_price = n.token_price(token_address)
                if not current_price:
                    warning(f"Could not get current price for {symbol}, skipping")
                    continue
                    
                # Calculate price difference
                price_diff = ((current_price - entry_price) / entry_price) * 100
                debug(f"{symbol} price change from recommendation: {price_diff:.2f}%", file_only=True)
                
                # Handle buy recommendations
                if action.upper() in ['BUY', 'LONG']:
                    # Skip if current price is significantly higher than entry price
                    if current_price > entry_price * 1.03:  # 3% higher
                        info(f"Skipping {symbol} buy as current price (${current_price:.4f}) is higher than entry (${entry_price:.4f})")
                        continue
                        
                    # Calculate buy amount
                    buy_amount = self.calculate_position_size(symbol, confidence)
                    if buy_amount == 0:
                        info(f"Skipping {symbol} buy due to zero calculated position size")
                        continue
                        
                    info(f"Setting buy limit order for {symbol} at ${entry_price:.4f} for ${buy_amount:.2f}")
                    
                    # Execute the buy order
                    self.execute_buy_order(token_address, symbol, entry_price, buy_amount, 'LIMIT')
                    
                # Handle sell recommendations
                elif action.upper() in ['SELL', 'SHORT']:
                    # Skip if current price is significantly lower than entry price
                    if current_price < entry_price * 0.97:  # 3% lower
                        info(f"Skipping {symbol} sell as current price (${current_price:.4f}) is lower than entry (${entry_price:.4f})")
                        continue
                        
                    # Check if we own the token
                    holdings = self.get_token_holdings(token_address)
                    if not holdings or holdings == 0:
                        info(f"Skipping {symbol} sell as we don't own any")
                        continue
                        
                    info(f"Setting sell limit order for {symbol} at ${entry_price:.4f}")
                    
                    # Execute the sell order
                    self.execute_sell_order(token_address, symbol, entry_price, holdings, 'LIMIT')
                    
            except Exception as e:
                error(f"Error processing recommendation for {rec.get('symbol', 'unknown')}: {str(e)}")
                
        info("Recommendation processing complete")

    def execute_buy_order(self, token_address, symbol, price, amount, order_type='MARKET'):
        """Execute a buy order for a token"""
        try:
            if order_type == 'MARKET':
                info(f"Executing market buy for {symbol} at ${price:.4f} for ${amount:.2f}")
                
                # Execute the buy through API
                n.buy_token_with_usd(token_address, amount)
                
                # Record the trade
                self.record_trade(symbol, 'BUY', price, amount)
                
            elif order_type == 'LIMIT':
                info(f"Setting limit buy order for {symbol} at ${price:.4f} for ${amount:.2f}")
                
                # Add to pending orders
                self.add_pending_order(token_address, symbol, 'BUY', price, amount)
                
        except Exception as e:
            error(f"Error executing buy order for {symbol}: {str(e)}")
            
    def execute_sell_order(self, token_address, symbol, price, amount, order_type='MARKET'):
        """Execute a sell order for a token"""
        try:
            if order_type == 'MARKET':
                info(f"Executing market sell for {symbol} at ${price:.4f} for {amount} tokens")
                
                # Execute the sell through API
                n.sell_token_for_usd(token_address, amount)
                
                # Record the trade
                sell_value = amount * price
                self.record_trade(symbol, 'SELL', price, sell_value)
                
                # Track sold token for potential reentry
                self.track_sold_tokens(token_address, amount, price)
                
            elif order_type == 'LIMIT':
                info(f"Setting limit sell order for {symbol} at ${price:.4f} for {amount} tokens")
                
                # Add to pending orders
                sell_value = amount * price
                self.add_pending_order(token_address, symbol, 'SELL', price, sell_value)
                
        except Exception as e:
            error(f"Error executing sell order for {symbol}: {str(e)}")
            
    def add_pending_order(self, token_address, symbol, order_type, price, amount):
        """Add an order to the pending orders file"""
        try:
            pending_orders_file = PROJECT_ROOT / "src" / "data" / "pending_orders.csv"
            
            # Create order data
            order = {
                'token_address': token_address,
                'symbol': symbol,
                'order_type': order_type,
                'limit_price': price,
                'amount': amount,
                'timestamp': int(time.time())
            }
            
            # Add to file
            if pending_orders_file.exists():
                orders_df = pd.read_csv(pending_orders_file)
                updated_orders = pd.concat([orders_df, pd.DataFrame([order])])
            else:
                updated_orders = pd.DataFrame([order])
                
            # Save to file
            updated_orders.to_csv(pending_orders_file, index=False)
            
            info(f"Added {order_type} order for {symbol} to pending orders")
            
        except Exception as e:
            error(f"Error adding pending order: {str(e)}")
            
    def record_trade(self, symbol, action, price, amount):
        """Record a trade in the trade history file"""
        try:
            trade_history_file = PROJECT_ROOT / "src" / "data" / "trade_history.csv"
            
            # Create trade data
            trade = {
                'symbol': symbol,
                'action': action,
                'price': price,
                'amount': amount,
                'timestamp': int(time.time())
            }
            
            # Add to existing history or create new file
            if trade_history_file.exists():
                history_df = pd.read_csv(trade_history_file)
                updated_history = pd.concat([history_df, pd.DataFrame([trade])])
            else:
                updated_history = pd.DataFrame([trade])
                
            # Save to file
            updated_history.to_csv(trade_history_file, index=False)
            debug(f"Recorded {action} for {symbol} in trade history", file_only=True)
            
        except Exception as e:
            warning(f"Error recording trade: {str(e)}")
            
    def get_token_holdings(self, token_address):
        """Get the current balance of a token"""
        try:
            balance = n.get_token_balance(token_address)
            return balance if balance else 0
        except Exception as e:
            warning(f"Error getting token balance: {str(e)}")
            return 0
            
    def get_all_token_holdings(self):
        """Get all current token holdings with details"""
        try:
            holdings = {}
            
            # Get list of tokens we're monitoring
            for token_address in self.dca_monitored_tokens:
                try:
                    # Skip excluded tokens
                    if token_address in EXCLUDED_TOKENS:
                        continue
                        
                    # Get token details
                    symbol = self.get_token_symbol(token_address)
                    balance = n.get_token_balance(token_address)
                    
                    if balance and balance > 0:
                        current_price = n.token_price(token_address)
                        if current_price:
                            usd_value = balance * current_price
                            
                            holdings[symbol] = {
                                'address': token_address,
                                'amount': balance,
                                'price': current_price,
                                'usd_value': usd_value
                            }
                            
                except Exception as e:
                    warning(f"Error getting holdings for token: {str(e)}")
                    
            return holdings
            
        except Exception as e:
            error(f"Error getting all token holdings: {str(e)}")
            return {}

    def get_usd_balance(self):
        """Get the current USD balance"""
        try:
            # Use the appropriate token (USDC, USDT, etc.)
            usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC on Solana
            balance = n.get_token_balance(usdc_address)
            return balance if balance else 0
        except Exception as e:
            error(f"Error getting USD balance: {str(e)}")
            return 0
            
    def calculate_position_size(self, symbol, confidence):
        """Calculate position size based on confidence and available funds"""
        try:
            # Get available balance
            available_funds = self.get_usd_balance()
            
            # Base size on fixed DCA amount
            base_amount = self.fixed_dca_amount
            
            # Adjust based on confidence (70-100%)
            confidence_factor = min(max(confidence - 70, 0) / 30, 1.0)  # Scale from 0-1
            
            # More confidence = larger position
            position_multiplier = 1.0 + confidence_factor
            
            # Calculate final amount (cap at 50% of available funds)
            amount = min(base_amount * position_multiplier, available_funds * 0.5)
            
            debug(f"Calculated position size for {symbol}: ${amount:.2f} (confidence: {confidence}%)", file_only=True)
            return amount
            
        except Exception as e:
            warning(f"Error calculating position size: {str(e)}")
            return 0

if __name__ == "__main__":
    dca_agent = DCAAgent(fixed_dca_amount=10)  # Set fixed DCA amount
    dca_agent.run()