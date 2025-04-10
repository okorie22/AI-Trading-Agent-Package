"""
Moon Dev's CopyBot Agent
Analyzes current copybot positions to identify opportunities for increased position sizes

video for copy bot: https://youtu.be/tQPRW19Qcak?si=b6rAGpz4CuXKXyzn

think about list
- not all these tokens will have OHLCV data so we need to address that some how
- good to pass in BTC/ETH data too in order to see market structure

Need an API key? for a limited time, bootcamp members get free api keys for claude, openai, helius, birdeye & quant elite gets access to the moon dev api. join here: https://algotradecamp.com
"""

import os
import sys

# Add the directory containing token_list_tool.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Now import token_list_tool
from src.scripts.token_list_tool import TokenAccountTracker

# Rest of your imports
import pandas as pd
import anthropic
import openai
from termcolor import colored, cprint
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time
import re
import src.config as config
from src import nice_funcs as n
from src.scripts.ohlcv_collector import collect_all_tokens, collect_token_data
from concurrent.futures import ThreadPoolExecutor

# Try importing PySide6 with fallback
try:
    from PySide6.QtCore import QObject, Signal
except ImportError:
    # Define dummy classes for testing
    class QObject:
        pass
    
    class Signal:
        def __init__(self, *args):
            pass
        
        def emit(self, *args):
            pass

# Import logging utilities
from src.scripts.logger import debug, info, warning, error, critical, system

# Import leverage utilities
try:
    from src.scripts.leverage_utils import (
        check_hyperliquid_available, get_hl_symbol, 
        hl_entry, hl_exit, hl_partial_exit, 
        get_hl_positions, get_funding_rates
    )
    LEVERAGE_UTILS_AVAILABLE = True
    info("Leverage trading utilities loaded")
except ImportError:
    LEVERAGE_UTILS_AVAILABLE = False
    warning("Leverage trading utilities not available")

# Constants for mirror trading functionality
MIRROR_POSITION_SCALE = 1.0  # Scale factor for position size when mirroring (1.0 = same size)
FALLBACK_POSITION_SIZE = 10.0  # Default USD amount to use when price data isn't available
DUST_THRESHOLD = 0.5  # Minimum USD value to consider for trading (ignore dust)

# Using centralized settings from config.py
DEEPSEEK_BASE_URL = "https://api.deepseek.com"  # Base URL for DeepSeek API

class CopyBotAgent(QObject):
    """Moon Dev's CopyBot Agent 🤖"""
    
    # Update the signal to include change_percent and symbol
    analysis_complete = Signal(str, str, str, str, str, str, str, str, str)  # timestamp, action, token, token_symbol, analysis, confidence, price, change_percent, token_mint
    changes_detected = Signal(dict)  # changes dictionary from TokenAccountTracker
    mirror_mode_active = Signal(bool)  # Signal to indicate mirror mode is active
    
    def __init__(self):
        """Initialize the CopyBot agent with multiple LLM options"""
        super().__init__()  # Initialize QObject
        load_dotenv()
        
        # Get API keys
        self.anthropic_key = os.getenv("ANTHROPIC_KEY")
        self.openai_key = os.getenv("OPENAI_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_KEY")
        
        # Initialize Anthropic client if key exists
        if self.anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
        else:
            self.anthropic_client = None
            warning("No Anthropic API key found. Claude models will not be available.")
        
        # Initialize OpenAI client if key exists
        if self.openai_key:
            self.openai_client = openai.OpenAI(api_key=self.openai_key)
        else:
            self.openai_client = None
            warning("No OpenAI API key found. GPT models will not be available.")
            
        # Initialize DeepSeek client if key exists
        if self.deepseek_key:
            self.deepseek_client = openai.OpenAI(
                api_key=self.deepseek_key,
                base_url=DEEPSEEK_BASE_URL
            )
        else:
            self.deepseek_client = None
            warning("No DeepSeek API key found. DeepSeek models will not be available.")
            
        # Check trading mode and leverage availability
        self.trading_mode = config.TRADING_MODE.lower()
        if self.trading_mode not in ["spot", "leverage"]:
            warning(f"Invalid TRADING_MODE: {config.TRADING_MODE}. Defaulting to 'spot'.")
            self.trading_mode = "spot"
            
        info(f"Trading Mode: {self.trading_mode.upper()}")
        
        # Check hyperliquid availability if in leverage mode
        self.leverage_available = False
        if self.trading_mode == "leverage":
            if not LEVERAGE_UTILS_AVAILABLE:
                warning("Leverage trading utilities not available. Falling back to spot trading.")
                self.trading_mode = "spot"
            elif not config.USE_HYPERLIQUID:
                warning("Hyperliquid is disabled in config. Falling back to spot trading.")
                self.trading_mode = "spot"
            else:
                # Test hyperliquid connection
                self.leverage_available = check_hyperliquid_available()
                if not self.leverage_available:
                    warning("Hyperliquid connection failed. Falling back to spot trading.")
                    self.trading_mode = "spot"
                else:
                    info("Hyperliquid connection verified. Leverage trading enabled!")
        
        # Check if necessary functions exist in nice_funcs
        self.ai_analysis_available = (
            (self.anthropic_client and config.COPYBOT_MODEL_OVERRIDE == "deepseek-reasoner") or
            (self.deepseek_client and config.COPYBOT_MODEL_OVERRIDE in ["deepseek-chat", "deepseek-reasoner"]) or
            (self.openai_client and config.COPYBOT_MODEL_OVERRIDE.startswith("gpt-"))
        )
        
        if not self.ai_analysis_available:
            warning("No AI providers available. CopyBot will run in mirror-only mode.")
            self.mirror_mode_active.emit(True)
            
        # Check for required trading functions in nice_funcs
        required_functions = ['ai_entry', 'chunk_kill', 'get_token_balance_usd']
        missing_functions = [func for func in required_functions if not hasattr(n, func)]
        if missing_functions:
            warning(f"ERROR: Missing required function(s) in nice_funcs: {', '.join(missing_functions)}")
            warning("CopyBot may not function correctly without these.")
            
        # Check for optional functions and create implementation if missing
        if not hasattr(n, 'partial_kill'):
            warning("partial_kill function not found in nice_funcs. Adding a basic implementation.")
            # Add a partial_kill implementation to nice_funcs
            def partial_kill_implementation(token, percentage, max_usd_order_size, slippage):
                """Basic implementation of partial_kill that uses chunk_kill"""
                info(f"Using basic partial_kill implementation to sell {percentage*100:.1f}% of {token}")
                # Check if we have the token balance
                balance = n.get_token_balance_usd(token)
                if balance <= 0:
                    warning(f"No balance found for {token}")
                    return False
                    
                # For now, we'll implement a simple version that just does a full sell if percentage > 0.5
                # and does nothing if percentage < 0.5
                if percentage >= 0.5:
                    info(f"Percentage {percentage*100:.1f}% >= 50%, doing full sell")
                    return n.chunk_kill(token, max_usd_order_size, slippage)
                else:
                    info(f"Percentage {percentage*100:.1f}% < 50%, skipping sell (not supported by basic implementation)")
                    return False
                    
            # Add the implementation to nice_funcs module
            setattr(n, 'partial_kill', partial_kill_implementation)
            info("Added basic partial_kill implementation")
        
        # Set AI parameters - use config values
        self.ai_model = config.AI_MODEL
        self.ai_temperature = config.AI_TEMPERATURE
        self.ai_max_tokens = config.AI_MAX_TOKENS
        
        # Model settings
        if self.ai_analysis_available:
            info(f"Using AI Model: {config.COPYBOT_MODEL_OVERRIDE if config.COPYBOT_MODEL_OVERRIDE != '0' else self.ai_model}")
        
        self.recommendations_df = pd.DataFrame(columns=['token', 'action', 'confidence', 'reasoning'])
        info("Moon Dev's CopyBot Agent initialized!" + 
              (" (Mirror mode)" if not self.ai_analysis_available else " with multi-model support!") +
              (" with LEVERAGE trading" if self.trading_mode == "leverage" else " with SPOT trading"))
        
    def load_portfolio_data(self):
        """Load current copybot portfolio data from tracked wallets"""
        try:
            tracker = TokenAccountTracker()
            wallet_results = tracker.track_all_wallets()

            # Ensure wallet_results is a dictionary
            if not isinstance(wallet_results, dict):
                warning("Invalid wallet results format. Expected a dictionary.")
                return False
                
            # Convert the wallet results into a DataFrame that matches the expected format
            portfolio_data = []
            for wallet, tokens in wallet_results.items():
                debug(f"Processing {len(tokens)} tokens for wallet: {wallet}", file_only=True)
                for token in tokens:
                    debug(f"Token mint: {token['mint']}", file_only=True)
                    # Fetch token data to get the price and name
                    token_data = collect_token_data(token['mint'])
                    if token_data is not None and not token_data.empty:
                        usd_value = token_data['price'].iloc[-1] * float(token['amount'])
                        name = token_data['name'].iloc[-1] if 'name' in token_data.columns else 'Unknown'
                    else:
                        usd_value = 0
                        name = 'Unknown'
                    
                    portfolio_data.append({
                        'Mint Address': token['mint'],
                        'Amount': float(token['amount']),
                        'USD Value': usd_value,
                        'name': name,
                    })
        

            if not portfolio_data:
                warning("No portfolio data found.")
                self.portfolio_df = pd.DataFrame(columns=['wallet', 'Mint Address', 'amount', 'decimals'])
                return False  # Return False if no data is found

            self.portfolio_df = pd.DataFrame(portfolio_data)
            info("Current copybot portfolio loaded from tracked wallets!")
            debug(f"\n{self.portfolio_df}", file_only=True)
            return True

        except Exception as e:
            error(f"Error loading portfolio data: {str(e)}")
            self.portfolio_df = pd.DataFrame(columns=['wallet', 'Mint Address', 'amount', 'decimals'])
            return False  # Return False if an error occurs
            
    def get_ai_response(self, prompt):
        """Get response from the selected AI model"""
        try:
            # Use the model specified in COPYBOT_MODEL_OVERRIDE, or default to configured model
            if config.COPYBOT_MODEL_OVERRIDE == "deepseek-reasoner" and self.deepseek_client:
                info("Using DeepSeek Chat model for analysis...")
                response = self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are Moon Dev's CopyBot Agent. Analyze portfolio data and recommend BUY, SELL, or NOTHING."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature
                )
                return response.choices[0].message.content
                
            elif config.COPYBOT_MODEL_OVERRIDE == "deepseek-reasoner" and self.deepseek_client:
                info("Using DeepSeek Reasoner model for analysis...")
                response = self.deepseek_client.chat.completions.create(
                    model="deepseek-reasoner",  # Use the reasoner model
                    messages=[
                        {"role": "system", "content": "You are Moon Dev's CopyBot Agent. Analyze portfolio data and recommend BUY, SELL, or NOTHING."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature
                )
                return response.choices[0].message.content
                
            elif config.COPYBOT_MODEL_OVERRIDE.startswith("gpt-") and self.openai_client:
                info(f"Using OpenAI {config.COPYBOT_MODEL_OVERRIDE} model for analysis...")
                response = self.openai_client.chat.completions.create(
                    model=config.COPYBOT_MODEL_OVERRIDE,
                    messages=[
                        {"role": "system", "content": "You are Moon Dev's CopyBot Agent. Analyze portfolio data and recommend BUY, SELL, or NOTHING."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature
                )
                return response.choices[0].message.content
                
            elif self.anthropic_client:
                # Default to using Claude
                info(f"Using Claude {self.ai_model} model for analysis...")
                message = self.anthropic_client.messages.create(
                    model=self.ai_model,
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                
                # Handle Claude response format
                response = message.content
                if isinstance(response, list):
                    response = '\n'.join([
                        item.text if hasattr(item, 'text') else str(item)
                        for item in response
                    ])
                return response
            else:
                raise ValueError("No AI models available. Please check your API keys.")
                
        except Exception as e:
            warning(f"Error getting AI response: {str(e)}")
            return "NOTHING\nError: Could not get AI analysis. No action recommended."
            
    def analyze_position(self, token):
        """Analyze a single portfolio position"""

        try:
            if token in config.EXCLUDED_TOKENS:
                warning(f"Skipping analysis for excluded token: {token}")
                return None

            # Check if token exists in portfolio_df
            # Get position data
            position_data = self.portfolio_df[self.portfolio_df['Mint Address'] == token]
            if position_data.empty:
                warning(f"No portfolio data for token: {token}")
                return None
                
            info(f"\nAnalyzing position for {position_data['name'].values[0]}...")
            debug(f"Current Amount: {position_data['Amount'].values[0]}", file_only=True)
            debug(f"USD Value: ${position_data['USD Value'].values[0]:.2f}", file_only=True)

            # Add this debug log
            debug(f"Fetching OHLCV data for token: {token}", file_only=True)
            try:
                # Fetch OHLCV data
                token_market_data = collect_token_data(token)
                debug("OHLCV Data Retrieved:", file_only=True)
                if token_market_data is None or token_market_data.empty:
                    warning("No OHLCV data found")
                    token_market_data = "No market data available"
                else:
                    debug("OHLCV data found:", file_only=True)
                    debug(token_market_data.head(), file_only=True)
            except Exception as e:
                warning(f"Error collecting OHLCV data: {str(e)}")
                token_market_data = "No market data available"
            
            # Prepare context for LLM
            full_prompt = f"""
{config.PORTFOLIO_ANALYSIS_PROMPT.format(
    portfolio_data=position_data.to_string(),
    market_data=token_market_data
)}
"""
            
            info("\nSending data to AI for analysis...")
            
            # Get LLM analysis using the selected model
            response = self.get_ai_response(full_prompt)
            
            # Log complete analysis to file only
            debug("AI Analysis Results:", file_only=True)
            debug("=" * 50, file_only=True)
            debug(response, file_only=True)
            debug("=" * 50, file_only=True)
            
            lines = response.split('\n')
            action = lines[0].strip() if lines else "NOTHING"
            
            # Extract confidence
            confidence = 0
            for line in lines:
                if 'confidence' in line.lower():
                    try:
                        confidence = int(''.join(filter(str.isdigit, line)))
                    except:
                        confidence = 50
            
            # Store recommendation
            reasoning = '\n'.join(lines[1:]) if len(lines) > 1 else "No detailed reasoning provided"
            self.recommendations_df = pd.concat([
                self.recommendations_df,
                pd.DataFrame([{
                    'token': token,
                    'action': action,
                    'confidence': confidence,
                    'reasoning': reasoning
                }])
            ], ignore_index=True)
            
            # Extract token name and price
            token_name = position_data['name'].values[0] if not position_data.empty else "Unknown"
            token_symbol = position_data['symbol'].values[0] if not position_data.empty and 'symbol' in position_data.columns else "UNK"
            price = f"${position_data['USD Value'].values[0] / position_data['Amount'].values[0]:.4f}" if not position_data.empty and position_data['Amount'].values[0] > 0 else "N/A"
            
            # Try to extract change percentage from the analysis
            change_percent = None
            for line in lines:
                # Look for common patterns indicating percentage change
                if any(pattern in line.lower() for pattern in ['change', 'increase', 'decrease', 'moved', 'up by', 'down by']):
                    # Try to extract percentage values
                    percentage_match = re.search(r'(\+|-)?\s*(\d+\.?\d*)%', line)
                    if percentage_match:
                        sign = percentage_match.group(1) or ''
                        value = percentage_match.group(2)
                        change_percent = f"{sign}{value}"
                        break
            
            # Generate a timestamp for the analysis
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Store the mint address
            token_mint = token
            
            # Emit the analysis_complete signal with all relevant data
            self.analysis_complete.emit(
                timestamp,
                action,
                token_name,
                token_symbol,
                reasoning.split('\n')[0] if reasoning else "No analysis",
                str(confidence),
                price,
                change_percent if change_percent else None,
                token_mint
            )
            
            info(f"\nSummary for {position_data['name'].values[0]}:")
            info(f"Action: {action}")
            info(f"Confidence: {confidence}%")
            info(f"Position Analysis Complete!")
            return response
            
        except Exception as e:
            warning(f"Error analyzing position: {str(e)}")
            return None
            
    def execute_position_updates(self, wallet_results=None, changes=None):
        """Execute position size updates based on analysis"""
        try:
            info("\nExecuting position updates...")
            
            # Check if we have any recommendations
            if self.recommendations_df.empty:
                warning("No AI recommendations available. Falling back to mirroring tracked wallets...")
                self.mirror_mode_active.emit(True)
                return self.execute_mirror_trades(wallet_results, changes)
            
            for _, row in self.recommendations_df.iterrows():
                token = row['token']
                action = row['action']
                confidence = row['confidence']

                if confidence < config.COPYBOT_MIN_CONFIDENCE:
                    warning(f"Skipping {token}: Confidence {confidence}% below threshold")
                    continue
                
                info(f"\nProcessing {action} for {token}...")
                
                try:
                    # Check if we should use leverage trading
                    if self.trading_mode == "leverage" and self.leverage_available:
                        # Get hyperliquid symbol for this token
                        hl_symbol = get_hl_symbol(token)
                        if hl_symbol:
                            info(f"Using leverage trading for {token} ({hl_symbol})")
                            
                            if action == "BUY":
                                # Calculate position size based on confidence
                                max_position = config.usd_size * (config.MAX_POSITION_PERCENTAGE / 100)
                                target_size = max_position * (confidence / 100)
                                
                                # Get current position (this is approximate since we don't have a direct way to map)
                                positions = get_hl_positions()
                                current_position = 0
                                if positions and hl_symbol in positions:
                                    current_position = positions[hl_symbol].get('size', 0) * positions[hl_symbol].get('current_price', 0)
                                    info(f"Current Leverage Position: ${current_position:.2f}")
                                else:
                                    info("No current leverage position found")
                                
                                info(f"Target Size: ${target_size:.2f}")
                                
                                # Calculate difference (margin amount needed)
                                margin_amount = target_size / config.DEFAULT_LEVERAGE
                                
                                info(f"Opening leveraged position with ${margin_amount:.2f} margin")
                                
                                # Execute the leveraged buy
                                success = hl_entry(hl_symbol, margin_amount, config.DEFAULT_LEVERAGE)
                                
                                if success:
                                    info(f"Successfully bought {token} ({hl_symbol}) with leverage")
                                else:
                                    warning(f"Leverage trade execution failed for {token} ({hl_symbol})")
                                    
                            elif action == "SELL":
                                info(f"Closing leveraged position on {hl_symbol}")
                                
                                # Execute the leveraged sell (full exit)
                                success = hl_exit(hl_symbol)
                                
                                if success:
                                    info(f"Successfully closed position on {token} ({hl_symbol})")
                                else:
                                    warning(f"Failed to close position on {token} ({hl_symbol})")
                                
                            continue  # Skip to next token after leverage trading
                        else:
                            warning(f"No hyperliquid symbol found for {token}, using spot trading instead")
                            # Fall through to standard spot trading
                            
                    # Get current position value (spot trading path)
                    current_position = n.get_token_balance_usd(token)
                    
                    if action == "BUY":
                        # Calculate position size based on confidence
                        max_position = config.usd_size * (config.MAX_POSITION_PERCENTAGE / 100)
                        target_size = max_position * (confidence / 100)
                        
                        info(f"Current Position: ${current_position:.2f}")
                        info(f"Target Size: ${target_size:.2f}")
                        
                        # Calculate difference
                        amount_to_buy = target_size - current_position
                        
                        if amount_to_buy <= 0:
                            info(f"Already at or above target size! (${current_position:.2f} > ${target_size:.2f})")
                            continue
                            
                        info(f"Buying ${amount_to_buy:.2f} of {token}")
                        
                        # Execute the buy using nice_funcs
                        success = n.ai_entry(
                            token,
                            amount_to_buy
                        )
                        
                        if success:
                            info(f"Successfully bought {token}")
                        else:
                            warning(f"Trade execution failed for {token}")
                                
                    elif action == "SELL":
                        if current_position > 0:
                            info(f"Selling position worth ${current_position:.2f}")
                            
                            # Execute the sell using nice_funcs
                            success = n.chunk_kill(
                                token,
                                config.max_usd_order_size,  # From config.py
                                config.slippage  # From config.py
                            )
                            
                            if success:
                                info(f"Successfully sold {token}")
                            else:
                                warning(f"Failed to sell {token}")
                        else:
                            info("No position to sell")
                    
                    # Sleep between trades
                    time.sleep(config.API_SLEEP_SECONDS)
                    
                except Exception as e:
                    warning(f"Error executing trade for {token}: {str(e)}")
                    continue
                
        except Exception as e:
            warning(f"Error updating positions: {str(e)}")
            # Fall back to mirror trading on error
            try:
                warning("Attempting to fall back to mirror trading due to error...")
                self.mirror_mode_active.emit(True)
                self.execute_mirror_trades(wallet_results, changes)
            except Exception as mirror_error:
                warning(f"Mirror trading fallback also failed: {str(mirror_error)}")

    def execute_mirror_trades(self, wallet_results=None, changes=None):
        """Execute trades by mirroring the tracked wallets when AI analysis is unavailable
        
        Parameters:
            wallet_results: Dictionary of wallet results from TokenAccountTracker.track_all_wallets()
            changes: Dictionary of detected changes from TokenAccountTracker.detect_changes()
            
        This function should ideally reuse the wallet_results and changes from run_analysis_cycle
        to avoid duplicate API calls and unnecessary token tracking operations.
        """
        try:
            info("\nExecuting mirror trades based on wallet changes...")
            
            # First check if necessary functions exist in nice_funcs
            has_partial_kill = hasattr(n, 'partial_kill')
            if not has_partial_kill:
                warning("partial_kill function not found in nice_funcs. Will use chunk_kill for all sells.")
            
            # If changes weren't passed in, we need to fetch them
            if changes is None or wallet_results is None:
                info("Need to fetch wallet data for mirror trading...")
                # Get token tracker
                tracker = TokenAccountTracker()
                
                # Get cached data before any updates
                cache_data, _ = tracker.load_cache()
                
                # Call track_all_wallets to detect changes
                wallet_results = tracker.track_all_wallets()
                
                # Process the changes
                changes = tracker.detect_changes(cache_data, wallet_results)
            else:
                info("Using existing wallet data for mirror trading")
            
            if not changes:
                info("No changes detected. No trades to mirror.")
                return True
                
            # Print detailed information about the changes for debugging
            debug("Detected changes structure:", file_only=True)
            for wallet, wallet_changes in changes.items():
                debug(f"Wallet: {wallet}", file_only=True)
                
                if 'new' in wallet_changes and wallet_changes['new']:
                    debug("  New tokens:", file_only=True)
                    for token, details in wallet_changes['new'].items():
                        symbol = details.get('symbol', 'UNK')
                        name = details.get('name', 'Unknown')
                        debug(f"    {symbol} ({name}): {details.get('amount', 0)}", file_only=True)
                
                if 'modified' in wallet_changes and wallet_changes['modified']:
                    debug("  Modified tokens:", file_only=True)
                    for token, details in wallet_changes['modified'].items():
                        symbol = details.get('symbol', 'UNK')
                        name = details.get('name', 'Unknown Token')
                        change_pct = details.get('pct_change', 0)
                        debug(f"    {symbol} ({name}): {change_pct}% change", file_only=True)
                
                if 'removed' in wallet_changes and wallet_changes['removed']:
                    debug("  Removed tokens:", file_only=True)
                    for token, details in wallet_changes['removed'].items():
                        symbol = details.get('symbol', 'UNK')
                        name = details.get('name', 'Unknown Token')
                        debug(f"    {symbol} ({name}): {details.get('amount', 0)}", file_only=True)
            
            # Calculate max allowed position size based on risk settings
            max_allowed_position = config.usd_size * (config.MAX_POSITION_PERCENTAGE / 100)
            info(f"Risk Management: Maximum position size = ${max_allowed_position:.2f}")
                
            # Process each wallet's changes
            for wallet, wallet_changes in changes.items():
                info(f"\nProcessing changes for wallet: {wallet}")
                
                # Process new tokens
                if 'new' in wallet_changes:
                    for token, details in wallet_changes['new'].items():
                        token_name = details.get('name', 'Unknown Token')
                        token_symbol = details.get('symbol', 'UNK')
                        info(f"Analyzing new token: {token_symbol} ({token_name})")
                        self.analyze_position(token)
                
                # Process modified tokens
                if 'modified' in wallet_changes:
                    for token, details in wallet_changes['modified'].items():
                        token_name = details.get('name', 'Unknown Token')
                        token_symbol = details.get('symbol', 'UNK')
                        info(f"Analyzing modified token: {token_symbol} ({token_name})")
                        self.analyze_position(token)
                
                # Process removed tokens (if needed)
                if 'removed' in wallet_changes:
                    for token, details in wallet_changes['removed'].items():
                        token_name = details.get('name', 'Unknown Token')
                        token_symbol = details.get('symbol', 'UNK')
                        info(f"Removed token: {token_symbol} ({token_name})")
                        # You might want to add specific handling for removed tokens
                
            info("\nMirror trade execution complete!")
            return True
            
        except Exception as e:
            warning(f"Error executing mirror trades: {str(e)}")
            return False
            
    def run_analysis_cycle(self):
        """Run a complete portfolio analysis cycle"""
        try:
            info("\nStarting CopyBot Portfolio Analysis...")
            
            # Get token tracker - THIS IS THE ONLY PLACE we should do token tracking
            tracker = TokenAccountTracker()
            info("Using single tracker instance for all operations")
            
            # Get cached data before any updates
            cache_data, _ = tracker.load_cache()
            
            # Call track_all_wallets ONCE to detect changes
            wallet_results = tracker.track_all_wallets()
            
            # Process the changes
            changes = tracker.detect_changes(cache_data, wallet_results)
            
            # Emit changes if any were detected
            if changes:
                self.changes_detected.emit(changes)
            
            # Skip analysis if no changes are detected
            if not changes:
                info("No changes detected. Skipping analysis.")
                return
            
            # Use the ai_analysis_available flag set during initialization
            if not self.ai_analysis_available:
                info("No AI client available. Running in mirror trading mode...")
                self.mirror_mode_active.emit(True)
                self.execute_mirror_trades(wallet_results, changes)
                return
                
            # Continue with AI analysis if available
            info("AI client available. Proceeding with analysis...")
            
            # Extract ONLY the tokens that have changed
            changed_tokens = set()
            for wallet, wallet_changes in changes.items():
                if 'new' in wallet_changes:
                    for token in wallet_changes['new'].keys():
                        changed_tokens.add(token)
                if 'modified' in wallet_changes:
                    for token in wallet_changes['modified'].keys():
                        changed_tokens.add(token)
                    
            
            # Process ONLY the changed tokens from wallet_results
            portfolio_data = []
            for wallet, tokens in wallet_results.items():
                for token in tokens:
                    # ONLY process tokens that have changed
                    if token['mint'] in changed_tokens:
                        debug(f"Processing changed token: {token['mint']}", file_only=True)
                        portfolio_data.append({
                            'Mint Address': token['mint'],
                            'Amount': float(token['amount']),
                            'USD Value': token['amount'] * (token.get('price', 1)),  # Use token price if available
                            'name': token.get('name', 'Unknown Token'),
                            'symbol': token.get('symbol', 'UNK')  # Include symbol from token data
                        })
            
            # Create portfolio DataFrame ONLY with changed tokens
            self.portfolio_df = pd.DataFrame(portfolio_data)
            if self.portfolio_df.empty:
                warning("No portfolio data for changed tokens.")
                # Fall back to mirroring if we can't get portfolio data
                self.mirror_mode_active.emit(True)
                self.execute_mirror_trades(wallet_results, changes)
                return
            
            info("Current portfolio of changed tokens:")
            debug(self.portfolio_df, file_only=True)
            
            # Reset recommendations DataFrame before analyzing new positions
            self.recommendations_df = pd.DataFrame(columns=['token', 'action', 'confidence', 'reasoning'])
            
            # Process wallet changes 
            for wallet, wallet_changes in changes.items():
                
                # Process new tokens
                if 'new' in wallet_changes:
                    for token, details in wallet_changes['new'].items():
                        token_name = details.get('name', 'Unknown Token')
                        token_symbol = details.get('symbol', 'UNK')
                        info(f"Analyzing new token: {token_symbol} ({token_name})")
                        self.analyze_position(token)
                
                # Process modified tokens
                if 'modified' in wallet_changes:
                    for token, details in wallet_changes['modified'].items():
                        token_name = details.get('name', 'Unknown Token')
                        token_symbol = details.get('symbol', 'UNK')
                        info(f"Analyzing modified token: {token_symbol} ({token_name})")
                        self.analyze_position(token)
                
                # Process removed tokens (if needed)
                if 'removed' in wallet_changes:
                    for token, details in wallet_changes['removed'].items():
                        token_name = details.get('name', 'Unknown Token')
                        token_symbol = details.get('symbol', 'UNK')
                        info(f"Removed token: {token_symbol} ({token_name})")
                        # You might want to add specific handling for removed tokens
                
            info("\nPortfolio analysis cycle complete!")
            
        except Exception as e:
            error(f"Error in analysis cycle: {str(e)}")
            # Try to fall back to mirror trading in case of analysis error
            try:
                warning("Attempting to fall back to mirror trading due to error...")
                self.mirror_mode_active.emit(True)
                
                # Only create a new tracker if we don't already have wallet_results and changes
                if 'wallet_results' not in locals() or 'changes' not in locals():
                    tracker = TokenAccountTracker()
                    cache_data, _ = tracker.load_cache()
                    wallet_results = tracker.track_all_wallets()
                    changes = tracker.detect_changes(cache_data, wallet_results)
                
                self.execute_mirror_trades(wallet_results, changes)
            except Exception as mirror_error:
                error(f"Mirror trading fallback also failed: {str(mirror_error)}")
                
            debug("Cleaning up temporary data...", file_only=True)
            # Explicitly clean up any large data structures
            if hasattr(self, 'portfolio_df'):
                self.portfolio_df = pd.DataFrame()
            self.recommendations_df = pd.DataFrame(columns=['token', 'action', 'confidence', 'reasoning'])

    def run(self):
        """Run the CopyBot agent - main entry point called by the UI"""
        try:
            info("Running CopyBot analysis cycle...")
            self.run_analysis_cycle()
            info("CopyBot analysis cycle completed")
        except Exception as e:
            error(f"Error running CopyBot: {str(e)}")
            import traceback
            error(traceback.format_exc())

if __name__ == "__main__":
    analyzer = CopyBotAgent()
    analyzer.run_analysis_cycle()