import os
import json
import requests
from typing import List, Dict
import time
from datetime import datetime, timedelta
from src import nice_funcs as n
from concurrent.futures import ThreadPoolExecutor  # For parallel processing
import pandas as pd  # For data manipulation
from src.config import MONITORED_TOKENS, DYNAMIC_MODE, previous_monitored_tokens, previous_mode, FILTER_MODE, PERCENTAGE_THRESHOLD, AMOUNT_THRESHOLD, ENABLE_PERCENTAGE_FILTER, ENABLE_AMOUNT_FILTER, ENABLE_ACTIVITY_FILTER, ACTIVITY_WINDOW_HOURS, WALLETS_TO_TRACK, API_SLEEP_SECONDS, API_TIMEOUT_SECONDS, API_MAX_RETRIES
from src.scripts.logger import logger, debug, info, warning, error, critical, system, log_print  # Import logging utilities


class TokenAccountTracker:
    def __init__(self):
        self.TOKEN_CACHE = {}
        self.rpc_endpoint = os.getenv("RPC_ENDPOINT")
        if not self.rpc_endpoint:
            raise ValueError("Please set RPC_ENDPOINT environment variable!")
        info("Connected to Helius RPC endpoint... Moon Dev is ready!")

        # Check if BirdEye API is available
        self.birdeye_available = self.check_birdeye_api_available()

        # Dynamic vs Monitored Mode cache separation
        self.cache_file = os.path.join(
            os.getcwd(), 
            "src/data/artificial_memory_d.json" if DYNAMIC_MODE 
            else "src/data/artificial_memory_m.json"
        )
        debug(f"Cache file: {self.cache_file}", file_only=True)

    def check_birdeye_api_available(self):
        """Simple check if BirdEye API is available"""
        birdeye_api_key = os.getenv("BIRDEYE_API_KEY")
        if not birdeye_api_key:
            return False
            
        try:
            # Make a lightweight request to test availability
            url = "https://public-api.birdeye.so/public/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=1"
            headers = {"X-API-KEY": birdeye_api_key}
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT_SECONDS)
            
            if response.status_code == 200 and response.json().get("success", False):
                return True
            return False
        except:
            return False

    def get_token_price(self, mint):
        """Get token price from BirdEye if available, otherwise return 1"""
        if not self.birdeye_available:
            return 1
            
        try:
            birdeye_api_key = os.getenv("BIRDEYE_API_KEY")
            url = f"https://public-api.birdeye.so/public/price?address={mint}"
            headers = {"X-API-KEY": birdeye_api_key}
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT_SECONDS)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    price = data.get("data", {}).get("value", 0)
                    if price:
                        return float(price)
            return 1  # Default fallback
        except:
            return 1  # Default fallback on error

    def get_token_metadata(self, mint):
        """Get token metadata using Helius RPC"""
        try:
            # Use Helius RPC to get token metadata
            payload = {
                "jsonrpc": "2.0",
                "id": "moon-dev-metadata",
                "method": "getAccountInfo",
                "params": [
                    mint,
                    {"encoding": "jsonParsed"}
                ]
            }
            
            response = requests.post(self.rpc_endpoint, json=payload, timeout=API_TIMEOUT_SECONDS)
            if response.status_code == 200:
                data = response.json()
                if "result" in data and data["result"]["value"]:
                    # Extract metadata
                    account_data = data["result"]["value"]
                    program_id = account_data.get("owner")
                    
                    # Check if it's a token account
                    if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                        parsed_data = account_data.get("data", {}).get("parsed", {}).get("info", {})
                        return {
                            "symbol": parsed_data.get("symbol", "UNK"),
                            "name": parsed_data.get("name", "Unknown Token")
                        }
            
            # Return default values if metadata not found
            return {"symbol": "UNK", "name": "Unknown Token"}
        except:
            return {"symbol": "UNK", "name": "Unknown Token"}

    def load_cache(self):
        """Return tuple: (cached_data, cache_empty_status)"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    cached_data = json.load(f)
                global previous_mode, previous_monitored_tokens
                previous_mode = cached_data.get('mode')
                previous_monitored_tokens = cached_data.get('previous_monitored_tokens', [])
                # Return data + cache_was_empty status
                return cached_data.get('data', {}), False
            except Exception as e:
                error(f"Error loading cache: {str(e)}")
                return {}, True  # Consider cache empty if load failed
        return {}, True  # Cache file doesn't exist

    def save_cache(self, data):
        """Save wallet data to a mode-specific cache file."""
        debug(f"Saving data to {self.cache_file}...", file_only=True)
        try:
            cache_data = {
                'mode': DYNAMIC_MODE,
                'data': data,
                'previous_monitored_tokens': previous_monitored_tokens.copy(),
                'timestamp': datetime.now().isoformat()

            }
            with open(self.cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)
            debug(f"Data saved to {self.cache_file}!", file_only=True)
        except Exception as e:
            error(f"Error saving cache: {str(e)}")

    def get_token_balances(self, wallet_address: str) -> List[Dict]:
        """Fetch balances for specific tokens in MONITORED_TOKENS."""
        info(f"Fetching token balances for {wallet_address}...")
        
        balances = []
        found_count = 0
        not_found_count = 0
        
        for token in MONITORED_TOKENS:
            payload = {
                "jsonrpc": "2.0",
                "id": "moon-dev-rocks",
                "method": "getTokenAccountsByOwner",
                "params": [
                    wallet_address,
                    {"mint": token},
                    {"encoding": "jsonParsed"}
                ]
            }
            try:
                response = requests.post(self.rpc_endpoint, json=payload)
                response.raise_for_status()
                data = response.json()

                if "result" in data and data["result"]["value"]:
                    parsed_data = data["result"]["value"][0]["account"]["data"]["parsed"]["info"]
                    amount = float(parsed_data["tokenAmount"]["uiAmountString"])
                    decimals = parsed_data["tokenAmount"]["decimals"]
                    balances.append({
                        "mint": token,
                        "amount": amount,
                        "decimals": decimals,
                        "raw_amount": int(amount * (10 ** decimals)),  # Calculate raw_amount
                        "timestamp": datetime.now().isoformat(),
                        "wallet_address": wallet_address  # Include wallet address
                    })
                    found_count += 1
                else:
                    not_found_count += 1
            except Exception as e:
                not_found_count += 1
                debug(f"Error fetching token {token}: {str(e)}", file_only=True)
            
            time.sleep(API_SLEEP_SECONDS)  # Be nice to the API 😊
        
        info(f"Found {found_count} token balances, {not_found_count} tokens not found for {wallet_address}")
        return balances

    def get_current_token_accounts(self, wallet_address: str) -> List[Dict]:
        """Fetch all token accounts for a wallet address."""
        info(f"Fetching token accounts for {wallet_address[:4]}...")  # Show first 4 chars for privacy
        
        payload = {
            "jsonrpc": "2.0",
            "id": "moon-dev",
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }

        try:
            response = requests.post(self.rpc_endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

            if "result" not in data or not data["result"]["value"]:
                warning(f"No token accounts found for {wallet_address[:4]}")
                return []

            token_accounts = []
            zero_balance_count = 0
            
            for account in data["result"]["value"]:
                account_info = account["account"]["data"]["parsed"]["info"]
                if int(account_info["tokenAmount"]["amount"]) == 0:
                    zero_balance_count += 1
                    continue  # Skip tokens with zero balance
                
                token_accounts.append({
                    "mint": account_info["mint"],
                    "amount": float(account_info["tokenAmount"]["uiAmount"]),
                    "raw_amount": int(account_info["tokenAmount"]["amount"]),
                    "decimals": account_info["tokenAmount"]["decimals"],
                    "timestamp": datetime.now().isoformat(),
                    "wallet_address": wallet_address  # Include the wallet address
                })

            total_accounts = len(data["result"]["value"])
            info(f"Found {len(token_accounts)} token accounts for {wallet_address[:4]}")
            if zero_balance_count > 0:
                debug(f"Skipped {zero_balance_count} tokens with zero balance", file_only=True)
                
            return token_accounts

        except requests.exceptions.RequestException as e:
            error(f"RPC request failed: {str(e)}")
            return []
        except KeyError as e:
            error(f"Invalid response format: {str(e)}")
            return []
        except Exception as e:
            error(f"Unexpected error: {str(e)}")
            return []

    def get_wallet_activity(self, wallet_address, mint=None, dynamic_threshold=True, max_lookback_minutes=60):
        """
        Fetch and analyze the wallet's transaction history to detect buys and sells.
        
        Parameters:
            wallet_address (str): The wallet address to analyze.
            mint (str, optional): Specific token mint address to filter activity. Default is None (all tokens).
            dynamic_threshold (bool): If True, use a dynamic threshold based on recent activity. Default is True.
            max_lookback_minutes (int): Maximum lookback time in minutes for dynamic threshold. Default is 60 minutes.
        
        Returns:
            dict: A dictionary containing buy/sell activity for the wallet.
        """
        debug(f"Fetching transaction history for wallet {wallet_address[:4]}...", file_only=True)
        # We need to make sure BASE_URL and BIRDEYE_API_KEY are properly defined
        BASE_URL = "https://public-api.birdeye.so/public"
        BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
        
        if not BIRDEYE_API_KEY:
            warning("Warning: BIRDEYE_API_KEY not set, cannot check recent activity")
            return {"buys": [], "sells": []}
        
        url = f"{BASE_URL}/transaction_history?address={wallet_address}"
        headers = {"X-API-KEY": BIRDEYE_API_KEY}
        current_time = int(datetime.now().timestamp())
        
        # Calculate dynamic lookback time based on recent activity
        if dynamic_threshold:
            # Start with a small lookback window (e.g., 5 minutes)
            lookback_minutes = 5
            while lookback_minutes <= max_lookback_minutes:
                lookback_time = int((datetime.now() - timedelta(minutes=lookback_minutes)).timestamp())
                params = {
                    "time_from": lookback_time,
                    "time_to": current_time,
                    "limit": 100  # Limit to the most recent 100 transactions
                }
                if mint:
                    params["mint"] = mint

                try:
                    response = requests.get(url, headers=headers, params=params, timeout=API_TIMEOUT_SECONDS)
                    if response.status_code == 200:
                        transactions = response.json().get("data", {}).get("items", [])
                        if transactions:  # Stop if we find transactions
                            break
                    else:
                        debug(f"Failed to fetch wallet activity: HTTP {response.status_code}", file_only=True)
                        return {}
                except Exception as e:
                    debug(f"Error fetching wallet activity: {str(e)}", file_only=True)
                    return {}

                # Increase lookback time incrementally (e.g., 5, 10, 15, ..., up to max_lookback_minutes)
                lookback_minutes += 5
        else:
            # Use a fixed lookback window (e.g., 1 hour)
            lookback_time = int((datetime.now() - timedelta(hours=1)).timestamp())
            params = {
                "time_from": lookback_time,
                "time_to": current_time,
                "limit": 100
            }
            if mint:
                params["mint"] = mint

            try:
                response = requests.get(url, headers=headers, params=params, timeout=API_TIMEOUT_SECONDS)
                if response.status_code != 200:
                    debug(f"Failed to fetch wallet activity: HTTP {response.status_code}", file_only=True)
                    return {}
                transactions = response.json().get("data", {}).get("items", [])
            except Exception as e:
                debug(f"Error fetching wallet activity: {str(e)}", file_only=True)
                return {}

        # Parse transactions
        activity = {"buys": [], "sells": []}
        for tx in transactions:
            tx_type = tx.get("type")  # e.g., "buy", "sell"
            token_mint = tx.get("tokenMint")
            amount = float(tx.get("amount", 0))
            timestamp = tx.get("timestamp")

            if tx_type == "buy":
                activity["buys"].append({
                    "mint": token_mint,
                    "amount": amount,
                    "timestamp": timestamp
                })
            elif tx_type == "sell":
                activity["sells"].append({
                    "mint": token_mint,
                    "amount": amount,
                    "timestamp": timestamp
                })

        debug(f"Detected {len(activity['buys'])} buys and {len(activity['sells'])} sells in the last {lookback_minutes} minutes.", file_only=True)
        return activity

    def get_token_data(self, mint: str) -> Dict:
        """Get token details including name, symbol and price"""
        # Get metadata from Helius RPC
        metadata = self.get_token_metadata(mint)
        
        # Get price from BirdEye if available, otherwise price=1
        price = self.get_token_price(mint)
        
        return {
            "mint": mint,
            "name": metadata.get("name", "Unknown Token"),
            "symbol": metadata.get("symbol", "UNK"),
            "price": price,
            "logo": "",
            "market_cap": 0
        }

    def calculate_total_portfolio_value(self, token_accounts: List[Dict]) -> float:
        """Calculate the total USD value of the wallet's portfolio."""
        total_value = 0
        for account in token_accounts:
            mint = account["mint"]
            balance = account["amount"]
            price = self.get_token_price(mint)
            if price is not None:
                total_value += balance * price
        return total_value

    def fetch_with_backoff(url, max_retries=None, timeout=None):
        """Fetch data with exponential backoff retry logic"""
        max_retries = max_retries or API_MAX_RETRIES
        timeout = timeout or API_TIMEOUT_SECONDS
        retries = 0
        while retries < max_retries:
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                debug(f"Error fetching data: {str(e)}. Retrying in {2 ** retries} seconds...", file_only=True)
                time.sleep(2 ** retries)  # Exponential backoff
                retries += 1
        raise Exception(f"Max retries ({max_retries}) reached. Failed to fetch data.")

    def filter_relevant_tokens(self, token_accounts: List[Dict]) -> List[Dict]:
        """Filter out irrelevant tokens based on wallet-specific activity."""
        relevant_tokens = []

        # Calculate total portfolio value (needed for percentage-based filter)
        total_portfolio_value = 0
        if FILTER_MODE == "Dynamic":
            for account in token_accounts:
                mint = account["mint"]
                balance = account["amount"]
                price = self.get_token_price(mint)
                if price is not None:
                    total_portfolio_value += balance * price

        info(f"Total Portfolio Balance: ${total_portfolio_value:.2f}")

        # Filter tokens based on the selected mode
        skipped_tokens = 0
        wallet = token_accounts[0].get("wallet_address", "Unknown") if token_accounts else "Unknown"
        
        for account in token_accounts:
            mint = account["mint"]
            balance = account["amount"]
            price = self.get_token_price(mint)
            if price is None:
                skipped_tokens += 1
                continue

            # Get token metadata (symbol, name)
            metadata = self.get_token_metadata(mint)

            usd_value = balance * price

            # Skip tokens with very small balances (e.g., less than $10)
            if usd_value < 10:  # Adjust the threshold as needed
                skipped_tokens += 1
                continue

            # Apply the selected filter
            if FILTER_MODE == "Dynamic":
                # Percentage-based filter (only apply if enabled)
                if ENABLE_PERCENTAGE_FILTER:
                    percentage_of_portfolio = (usd_value / total_portfolio_value) * 100
                    if percentage_of_portfolio < PERCENTAGE_THRESHOLD:
                        skipped_tokens += 1
                        continue
            elif FILTER_MODE == "Monitored Tokens":
                # Only include tokens from MONITORED_TOKENS list
                if mint not in MONITORED_TOKENS:
                    skipped_tokens += 1
                    continue
                # Amount threshold filter (only apply if enabled)
                if ENABLE_AMOUNT_FILTER and usd_value < AMOUNT_THRESHOLD:
                    skipped_tokens += 1
                    continue
            else:
                raise ValueError(f"Invalid FILTER_MODE: {FILTER_MODE}. Use 'Dynamic' or 'Monitored Tokens'.")

            # Check if there's recent activity for this token (only if filter is enabled)
            if ENABLE_ACTIVITY_FILTER:
                try:
                    activity_window_hours = ACTIVITY_WINDOW_HOURS
                    if activity_window_hours > 0:
                        # Get wallet activity for this specific token mint
                        activity = self.get_wallet_activity(wallet_address=account.get("wallet_address"),
                                                          mint=mint,
                                                          max_lookback_minutes=activity_window_hours * 60)
                        
                        # Check if there were any buys or sells within the time window
                        has_recent_activity = (len(activity.get("buys", [])) > 0 or 
                                              len(activity.get("sells", [])) > 0)
                        
                        if not has_recent_activity:
                            debug(f"Skipping {mint} due to no activity in the last {activity_window_hours} hours", file_only=True)
                            skipped_tokens += 1
                            continue
                except Exception as e:
                    debug(f"Error checking activity for {mint}: {str(e)}", file_only=True)
                    # If error checking activity, continue anyway

            # Add token to relevant list with metadata
            relevant_tokens.append({
                "mint": mint,
                "amount": balance,
                "price": price,
                "symbol": metadata.get("symbol", "UNK"),
                "name": metadata.get("name", "Unknown Token"),
                "decimals": account.get("decimals", 9),  # Default to 9 if missing
                "raw_amount": account.get("raw_amount", int(balance * (10 ** account.get("decimals", 9)))),  # Calculate raw_amount if missing
                'timestamp': datetime.now().isoformat(),
                "wallet_address": account.get("wallet_address", wallet)  # Keep the wallet address for reference
            })

            time.sleep(API_SLEEP_SECONDS)  # 1-second delay between API calls

        # Make sure to print the found/skipped summary (this is what will appear in the UI)
        found_tokens = len(relevant_tokens)
        info(f"Found {found_tokens} relevant tokens, skipped {skipped_tokens} tokens")
        
        return relevant_tokens

    def detect_changes(self, cached_results, current_results):
        """Detect changes in token balances, including new, removed, and modified tokens."""
        changes = {}
        
        # Extract actual wallet data from cache structure
        cached_data = cached_results.get('data', {}) if isinstance(cached_results, dict) else cached_results
        
        for wallet in WALLETS_TO_TRACK:
            # Create maps for easier lookups with all needed data
            previous_tokens = {t["mint"]: t for t in cached_data.get(wallet, [])}
            current_tokens = {t["mint"]: t for t in current_results.get(wallet, [])}

            wallet_changes = {
                "new": {},
                "removed": {},
                "modified": {}
            }

            # Detect new tokens
            for mint, token_data in current_tokens.items():
                if mint not in previous_tokens:
                    wallet_changes["new"][mint] = {
                        "amount": int(token_data["raw_amount"]),
                        "symbol": token_data.get("symbol", "UNK"),
                        "name": token_data.get("name", "Unknown Token")
                    }

            # Detect removed tokens
            for mint, token_data in previous_tokens.items():
                if mint not in current_tokens:
                    wallet_changes["removed"][mint] = {
                        "amount": int(token_data["raw_amount"]),
                        "symbol": token_data.get("symbol", "UNK"),
                        "name": token_data.get("name", "Unknown Token")
                    }

            # Detect modified tokens with percentage change
            for mint, curr_data in current_tokens.items():
                prev_data = previous_tokens.get(mint)
                if prev_data is not None:
                    curr_amount = int(curr_data["raw_amount"])
                    prev_amount = int(prev_data["raw_amount"])
                    
                    if prev_amount != curr_amount:
                        change = curr_amount - prev_amount
                        pct = (change / prev_amount * 100) if prev_amount != 0 else 0
                        wallet_changes["modified"][mint] = {
                            "previous_amount": prev_amount,
                            "current_amount": curr_amount,
                            "change": change,
                            "pct_change": round(pct, 2),
                            "symbol": curr_data.get("symbol", "UNK"),
                            "name": curr_data.get("name", "Unknown Token")
                        }

            # Only add to changes if there are actual changes
            if any(wallet_changes.values()):
                changes[wallet] = wallet_changes
                
                # Log detailed changes at debug level only
                num_new = len(wallet_changes["new"])
                num_removed = len(wallet_changes["removed"])
                num_modified = len(wallet_changes["modified"])
                
                if num_new > 0 or num_removed > 0 or num_modified > 0:
                    debug(f"Changes for wallet {wallet[:4]}: {num_new} new, {num_removed} removed, {num_modified} modified", file_only=True)
                    
                    if num_new > 0:
                        for mint, token_data in wallet_changes["new"].items():
                            symbol = token_data.get("symbol", "UNK")
                            info(f"NEW: {symbol} token detected in wallet {wallet[:4]}")
                    
                    if num_modified > 0:
                        for mint, token_data in wallet_changes["modified"].items():
                            symbol = token_data.get("symbol", "UNK")
                            change_pct = token_data.get("pct_change", 0)
                            if change_pct > 0:
                                info(f"INCREASE: {symbol} increased by {change_pct:.2f}% in wallet {wallet[:4]}")
                            else:
                                info(f"DECREASE: {symbol} decreased by {abs(change_pct):.2f}% in wallet {wallet[:4]}")

        return changes

    def track_all_wallets(self):
        """Track token accounts for all wallets in the WALLETS_TO_TRACK list."""
        global previous_monitored_tokens, previous_mode, MONITORED_TOKENS

        system("Moon Dev's Token Tracker starting up...")
        info(f"Tracking {len(WALLETS_TO_TRACK)} wallets...")

        # Load cache and check if it was newly created
        cached_results, cache_was_empty = self.load_cache()

        # Normalize token lists to handle formatting issues
        previous_monitored_tokens = [str(token).strip() for token in previous_monitored_tokens]
        MONITORED_TOKENS = [str(token).strip() for token in MONITORED_TOKENS]
                
        # More robust change detection
        mode_changed = previous_mode != DYNAMIC_MODE
        tokens_changed = sorted(MONITORED_TOKENS) != sorted(previous_monitored_tokens)

        if mode_changed or tokens_changed or cache_was_empty:
            if mode_changed:
                info("Mode changed.")
            if tokens_changed:
                info("Monitored tokens list changed.")
            if cache_was_empty:
                info("Cache was empty/missing.")
            
            # Reset only when necessary
            cached_results = {}
            previous_monitored_tokens = MONITORED_TOKENS.copy()
            previous_mode = DYNAMIC_MODE
            
            # Save updated state immediately
            self.save_cache(cached_results)
        else:
            debug("No Mode or Token List change detected.", file_only=True)

        results = {}
        changes = {}
        wallet_stats = {}  # Store wallet-specific stats

        # Create a dictionary to track seen wallets (to prevent duplicate logs)
        processed_wallets = set()

        def fetch_wallet_data(wallet):
            """Helper function to fetch data for a single wallet."""
            if wallet in processed_wallets:
                return wallet, [], {'found': 0, 'skipped': 0}
            
            processed_wallets.add(wallet)
            
            if DYNAMIC_MODE:
                info(f"Fetching all token accounts for {wallet}...")
                token_accounts = self.get_current_token_accounts(wallet)
                
                # Get the initial count before filtering 
                total_tokens = len(token_accounts)
                
                # Apply filtering
                filtered_tokens = self.filter_relevant_tokens(token_accounts)
                
                # Calculate stats
                found_tokens = len(filtered_tokens)
                skipped_tokens = total_tokens - found_tokens
                
                # Ensure the stats are properly displayed with wallet address
                info(f"Found {found_tokens} relevant tokens, skipped {skipped_tokens} tokens for {wallet[:4]}")
                
                # Print a clearer stats line for the UI to parse - Keep this as print for UI parsing
                print(f"TOKEN_STATS: {wallet[:4]} - Found: {found_tokens}, Skipped: {skipped_tokens}")
                
                stats = {'found': found_tokens, 'skipped': skipped_tokens, 'total': total_tokens}
                
                return wallet, filtered_tokens, stats
            else:
                info(f"Fetching token balances for {wallet}...")
                token_balances = self.get_token_balances(wallet)
                
                # Count total valid tokens
                total_valid_tokens = sum(1 for t in token_balances if t['mint'] in MONITORED_TOKENS)
                
                # Filter tokens
                filtered_tokens = [t for t in token_balances if t['mint'] in MONITORED_TOKENS and t['amount'] > 0]
                
                # Calculate stats
                found_tokens = len(filtered_tokens)
                skipped_tokens = total_valid_tokens - found_tokens
                
                # Ensure the stats are properly displayed with wallet address
                info(f"Found {found_tokens} relevant tokens, skipped {skipped_tokens} tokens for {wallet[:4]}")
                
                # Print a clearer stats line for the UI to parse - Keep this as print for UI parsing
                print(f"TOKEN_STATS: {wallet[:4]} - Found: {found_tokens}, Skipped: {skipped_tokens}")
                
                stats = {'found': found_tokens, 'skipped': skipped_tokens, 'total': total_valid_tokens}
                
                return wallet, filtered_tokens, stats

        # Use ThreadPoolExecutor with a small number of workers
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(fetch_wallet_data, wallet): wallet for wallet in WALLETS_TO_TRACK}
            for future in futures:
                wallet, parsed_accounts, stats = future.result()
                if parsed_accounts:  # Only add if we have results
                    results[wallet] = parsed_accounts
                wallet_stats[wallet] = stats  # Store stats for this wallet
                time.sleep(API_SLEEP_SECONDS)  # Add a delay between API calls to avoid rate limits

        # Detect changes after fetching current results
        changes = self.detect_changes(cached_results, results)
        if changes:
            info("Change detected!")
            for wallet, change in changes.items():
                debug(f"Wallet: {wallet}", file_only=True)
                debug(f"New Tokens: {change['new']}", file_only=True)
                debug(f"Removed Tokens: {change['removed']}", file_only=True)
                debug(f"Modified Tokens: {change['modified']}", file_only=True)
        else:
            info("No changes detected this round.")

        # Prepare cache data with mode information
        cache_data = {
            'mode': DYNAMIC_MODE,        # Store current mode
            'data': results,             # Store wallet data
            'wallet_stats': wallet_stats # Store wallet stats data
        }

        # Save the updated data for next time
        try:
            self.save_cache(cache_data)
        except Exception as e:
            error(f"Failed to save cache: {str(e)}")
        
        return results  # Ensure the method always returns a dictionary

def main():
    tracker = TokenAccountTracker()
    tracker.track_all_wallets()

if __name__ == "__main__":
    main()