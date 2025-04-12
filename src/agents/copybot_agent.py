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
import time
import traceback
import re
import pandas as pd
import numpy as np
from datetime import datetime
import json
from typing import List, Dict, Optional, Union, Tuple, Any

# Add the directory containing token_list_tool.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Now import token_list_tool
from src.scripts.token_list_tool import TokenAccountTracker

# Rest of your imports
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
            self.callbacks = []
        
        def emit(self, *args):
            for callback in self.callbacks:
                callback(*args)
        
        def connect(self, callback):
            """Add the callback function to the list of callbacks"""
            self.callbacks.append(callback)

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
    order_executed = Signal(str, str, str, float, float, float, object, str, str, str)  # agent_name, action, token, amount, entry_price, exit_price, pnl, wallet_address, mint_address, ai_analysis
    
    def __init__(self):
        """Initialize the CopyBot agent with multiple LLM options"""
        super().__init__()  # Initialize QObject
        load_dotenv()
        
        # Add market data cache to avoid collecting data more than once
        self.market_data_cache = {}
        
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
        
        # Load chat models for AI analysis
        self.models = {
            "claude-3-haiku-20240307": None,
            "claude-3-sonnet-20240229": None,
            "gpt-4-turbo": None,
            "deepseek-reasoner": None
        }
        self.model_name = config.AI_MODEL
        
        # AI analysis availability
        self.ai_analysis_available = os.getenv("ENABLE_AI_ANALYSIS", "true").lower() == "true"
        
        # Get trading mode
        self.trading_mode = "spot"  # Default to spot trading
        try:
            self.trading_mode = os.getenv("TRADING_MODE", "spot").lower()
        except:
            pass
        
        # Check for leverage trading availability
        self.leverage_available = False
        try:
            from src.leverage import init_hl, get_hl_positions, get_hl_symbol, hl_entry, hl_exit
            self.leverage_available = True
            if self.ai_analysis_available:
                info("with multi-model support!", end=" ")
            info(f"with {self.trading_mode.upper()} trading")
        except Exception as e:
            debug(f"Failed to load leverage trading: {e}", file_only=True)
            if self.ai_analysis_available:
                info("with multi-model support!")
            else:
                info("")
        
    def load_portfolio_data(self, existing_wallet_results=None, changes=None):
        """Load current copybot portfolio data from tracked wallets"""
        try:
            # Use existing wallet results if provided (from run_analysis_cycle)
            wallet_results = existing_wallet_results
            
            # If no existing results were provided, try to get cached data first
            if wallet_results is None:
                # Don't call track_all_wallets again - it should already be called in run_analysis_cycle
                # Use the existing TokenAccountTracker to get the cached data
                tracker = TokenAccountTracker()
                cached_data, _ = tracker.load_cache()
                
                # The cache structure is different from what we need, extract the actual data
                wallet_results = cached_data.get('data', {})
                
                # If no data exists, try to get fresh data but only as a last resort
                if not wallet_results:
                    debug("No cached wallet data found, fetching fresh data", file_only=True)
                    wallet_results = tracker.track_all_wallets()

            # Ensure wallet_results is a dictionary
            if not isinstance(wallet_results, dict):
                warning("Invalid wallet results format. Expected a dictionary.")
                return False
            
            # Create a set of tokens to process if changes are provided
            tokens_to_process = set()
            if changes:
                for wallet, wallet_changes in changes.items():
                    # Add new tokens
                    for token_mint in wallet_changes.get('new', {}):
                        tokens_to_process.add(token_mint)
                    # Add removed tokens
                    for token_mint in wallet_changes.get('removed', {}):
                        tokens_to_process.add(token_mint)
                    # Add modified tokens
                    for token_mint in wallet_changes.get('modified', {}):
                        tokens_to_process.add(token_mint)
                        
                info(f"Processing only {len(tokens_to_process)} tokens with detected changes")
                
            # Convert the wallet results into a DataFrame that matches the expected format
            portfolio_data = []
            for wallet, tokens in wallet_results.items():
                debug(f"Processing {len(tokens)} tokens for wallet: {wallet}", file_only=True)
                for token in tokens:
                    token_mint = token['mint']
                    
                    # Skip tokens not in the changes list if changes are provided
                    if changes and token_mint not in tokens_to_process:
                        continue
                        
                    debug(f"Token mint: {token_mint}", file_only=True)
                    
                    # Check if token data is already in the cache
                    usd_value = 0
                    name = 'Unknown'
                    
                    if hasattr(self, 'market_data_cache') and token_mint in self.market_data_cache:
                        # Use cached data
                        token_data = self.market_data_cache[token_mint]
                        debug(f"Using cached market data for {token_mint}", file_only=True)
                        
                        if token_data is not None and not token_data.empty:
                            if 'price' in token_data.columns:
                                usd_value = token_data['price'].iloc[-1] * float(token['amount'])
                            if 'name' in token_data.columns:
                                name = token_data['name'].iloc[-1]
                    else:
                        # Fetch token data only if not in cache
                        debug(f"Fetching market data for {token_mint}", file_only=True)
                        token_data = collect_token_data(token_mint)
                        
                        # Cache the data for future use
                        if not hasattr(self, 'market_data_cache'):
                            self.market_data_cache = {}
                        
                        if token_data is not None:
                            self.market_data_cache[token_mint] = token_data
                            
                            if not token_data.empty:
                                if 'price' in token_data.columns:
                                    usd_value = token_data['price'].iloc[-1] * float(token['amount'])
                                if 'name' in token_data.columns:
                                    name = token_data['name'].iloc[-1]
                    
                    portfolio_data.append({
                        'Mint Address': token_mint,
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
            # Select the model based on settings hierarchy:
            # 1. Use agent-specific override if set
            # 2. Otherwise fall back to global AI model
            selected_model = config.COPYBOT_MODEL_OVERRIDE if config.COPYBOT_MODEL_OVERRIDE != "0" else self.ai_model
            
            info(f"Using AI model: {selected_model}")
            
            # Use the appropriate client based on the selected model
            if "deepseek" in selected_model.lower() and self.deepseek_client:
                # Use DeepSeek client with the exact model specified
                info(f"Using DeepSeek {selected_model} model for analysis...")
                response = self.deepseek_client.chat.completions.create(
                    model=selected_model,  # Use the exact selected model, not hardcoded
                    messages=[
                        {"role": "system", "content": "You are Moon Dev's CopyBot Agent. Analyze portfolio data and recommend BUY, SELL, or NOTHING."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature
                )
                return response.choices[0].message.content
                
            elif selected_model.startswith("gpt-") and self.openai_client:
                info(f"Using OpenAI {selected_model} model for analysis...")
                response = self.openai_client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": "You are Moon Dev's CopyBot Agent. Analyze portfolio data and recommend BUY, SELL, or NOTHING."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature
                )
                return response.choices[0].message.content
                
            elif self.anthropic_client:
                # For Claude models
                info(f"Using Claude {selected_model} model for analysis...")
                message = self.anthropic_client.messages.create(
                    model=selected_model,
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
                raise ValueError(f"No AI client available for model: {selected_model}. Please check your API keys.")
                
        except Exception as e:
            warning(f"Error getting AI response: {str(e)}")
            return "NOTHING\nError: Could not get AI analysis. No action recommended."
            
    def analyze_position(self, token, token_status=None, wallet_action=None, pct_change=None):
        """Analyze a single portfolio position with wallet action context"""

        try:
            if token in config.EXCLUDED_TOKENS:
                warning(f"Skipping analysis for excluded token: {token}")
                return None

            # Check if token exists in portfolio_df
            position_data = self.portfolio_df[self.portfolio_df['Mint Address'] == token]
            
            # Special handling for removed tokens that might not be in portfolio_df anymore
            if position_data.empty and token_status == "removed":
                warning(f"Token {token} was removed and is not in current portfolio - creating synthetic data for analysis")
                # Create synthetic position data for analysis
                position_data = pd.DataFrame([{
                    'Mint Address': token,
                    'Amount': 0,  # Amount is zero since it was removed
                    'USD Value': 0,  # USD value is zero
                    'name': f"Removed Token ({token[:6]}...)",  # Use shortened token mint as name
                }])
            elif position_data.empty:
                warning(f"No portfolio data for token: {token}")
                return None
                
            info(f"\nAnalyzing position for {position_data['name'].values[0]}...")
            debug(f"Current Amount: {position_data['Amount'].values[0]}", file_only=True)
            debug(f"USD Value: ${position_data['USD Value'].values[0]:.2f}", file_only=True)
            
            # Add wallet action context if available
            if token_status:
                debug(f"Token Status: {token_status}, Percentage Change: {pct_change}", file_only=True)

            # Get token market data - USE CACHE
            debug(f"Getting market data for token: {token}", file_only=True)
            token_market_data = None
            
            # Check cache first - this is the important part!
            if token in self.market_data_cache:
                debug(f"Using cached market data for {token}", file_only=True)
                token_market_data = self.market_data_cache[token]
            else:
                # Only collect if not in cache
                debug(f"Collecting market data for {token}", file_only=True)
                token_market_data = collect_token_data(token)
                
                # Cache the data for future reference
                if token_market_data is not None:
                    self.market_data_cache[token] = token_market_data
            
            # If no data available (either from cache or collection)
            if token_market_data is None or (isinstance(token_market_data, pd.DataFrame) and token_market_data.empty):
                warning("No market data found")
                token_market_data = "No market data available"

            # Prepare wallet action context for the AI prompt
            wallet_context = ""
            action_weight = 0
            
            if token_status == "new":
                wallet_context = "IMPORTANT: The tracked wallet has just BOUGHT this token. This is a STRONG BUY signal."
                action_weight = config.COPYBOT_WALLET_ACTION_WEIGHT  # Weight toward BUY
            elif token_status == "removed":
                wallet_context = "IMPORTANT: The tracked wallet has SOLD ALL holdings of this token. This is a STRONG SELL signal."
                action_weight = -config.COPYBOT_WALLET_ACTION_WEIGHT  # Weight toward SELL
            elif token_status == "modified" and pct_change is not None:
                # Fix the logic - ensure pct_change is treated correctly
                # Positive pct_change means the wallet INCREASED holdings (BUY signal)
                # Negative pct_change means the wallet DECREASED holdings (SELL signal)
                
                # Add debug logging to verify the value
                debug(f"Processing modified token with pct_change = {pct_change}", file_only=True)
                
                # Use absolute value check first to determine magnitude
                abs_pct_change = abs(pct_change)
                
                # Check if token amount actually increased or decreased based on pct_change sign
                if pct_change > 0:
                    # Wallet INCREASED position - BUY signal
                    if abs_pct_change > 20:
                        wallet_context = f"IMPORTANT: The tracked wallet has SIGNIFICANTLY INCREASED holdings of this token by {abs_pct_change:.2f}%. This is a STRONG BUY signal."
                        action_weight = config.COPYBOT_WALLET_ACTION_WEIGHT * 0.9  # 90% weight toward BUY
                    else:
                        wallet_context = f"IMPORTANT: The tracked wallet has slightly increased holdings of this token by {abs_pct_change:.2f}%. This suggests a BUY signal."
                        action_weight = config.COPYBOT_WALLET_ACTION_WEIGHT * 0.5  # 50% weight toward BUY
                else:
                    # Wallet DECREASED position - SELL signal
                    if abs_pct_change > 20:
                        wallet_context = f"IMPORTANT: The tracked wallet has SIGNIFICANTLY DECREASED holdings of this token by {abs_pct_change:.2f}%. This is a STRONG SELL signal."
                        action_weight = -config.COPYBOT_WALLET_ACTION_WEIGHT * 0.9  # 90% weight toward SELL
                    else:
                        wallet_context = f"IMPORTANT: The tracked wallet has slightly decreased holdings of this token by {abs_pct_change:.2f}%. This suggests a SELL signal."
                        action_weight = -config.COPYBOT_WALLET_ACTION_WEIGHT * 0.5  # 50% weight toward SELL
            
            # Prepare context for LLM with wallet action context
            full_prompt = f"""
{wallet_context}

Your analysis should confirm or reject this signal based on market data, but give significant weight ({int(config.COPYBOT_WALLET_ACTION_WEIGHT*100)}%) to the wallet's action.

{config.PORTFOLIO_ANALYSIS_PROMPT.format(
    portfolio_data=position_data.to_string(),
    market_data=token_market_data
)}

Based on the wallet's action and your analysis, recommend: 
BUY (if you confirm the wallet's buy signal)
SELL (if you confirm the wallet's sell signal)
NOTHING (only if you have strong evidence against the wallet's action)

Confidence should reflect your agreement with the wallet's action, with higher confidence when your analysis agrees.
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
            
            # Extract confidence with proper regex and validation
            confidence = 0
            for line in lines:
                if 'confidence' in line.lower():
                    try:
                        # Look for patterns like "confidence: 65%" or "65% confidence"
                        match = re.search(r'confidence:?\s*(\d{1,3})\s*%|(\d{1,3})\s*%\s*confidence', line.lower())
                        if match:
                            # Use the first non-None group
                            confidence_str = match.group(1) if match.group(1) else match.group(2)
                            confidence = int(confidence_str)
                            # Validate the range
                            if confidence < 0 or confidence > 100:
                                warning(f"Invalid confidence value: {confidence}. Setting to default 50%.")
                                confidence = 50
                            break
                        else:
                            # Fallback to traditional method but with validation
                            digits = ''.join(filter(str.isdigit, line))
                            if digits:
                                # Check if the number is reasonable (between 0-100)
                                if len(digits) <= 3 and int(digits) <= 100:
                                    confidence = int(digits)
                                else:
                                    # If too large, try to extract just 2-3 digits that might be the confidence
                                    if len(digits) >= 2:
                                        # Try the first 2-3 digits
                                        potential_confidence = int(digits[:2]) if len(digits) >= 2 else int(digits)
                                        if potential_confidence <= 100:
                                            confidence = potential_confidence
                                        else:
                                            confidence = 50
                                    else:
                                        confidence = 50
                    except:
                        warning("Error parsing confidence value, using default 50%.")
                        confidence = 50
            
            # Final validation to ensure confidence is in range 0-100
            if confidence < 0 or confidence > 100:
                warning(f"Confidence value out of range: {confidence}. Clamping to 0-100.")
                confidence = max(0, min(confidence, 100))
            
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
                ai_analysis = row['reasoning'].split('\n')[0] if row['reasoning'] else "No analysis"

                if confidence < config.COPYBOT_MIN_CONFIDENCE:
                    warning(f"Skipping {token}: Confidence {confidence}% below threshold")
                    continue
                
                info(f"\nProcessing {action} for {token}...")
                
                try:
                    # Defaults for wallet address and token symbol
                    wallet_address = ""
                    token_symbol = "Unknown"
                    token_name = "Unknown"
                    
                    # Try to get wallet address from changes if available
                    if changes:
                        for wallet, wallet_changes in changes.items():
                            for change_type in ['new', 'modified', 'removed']:
                                if change_type in wallet_changes and token in wallet_changes[change_type]:
                                    wallet_address = wallet
                                    token_symbol = wallet_changes[change_type][token].get('symbol', 'Unknown')
                                    token_name = wallet_changes[change_type][token].get('name', 'Unknown')
                                    break
                            if wallet_address:
                                break
                    
                    # Get token price from the cache first
                    current_price = 0
                    try:
                        # Use the cached market data if available
                        if token in self.market_data_cache:
                            token_data = self.market_data_cache[token]
                            if isinstance(token_data, pd.DataFrame) and not token_data.empty and 'price' in token_data.columns:
                                current_price = token_data['price'].iloc[-1]
                                debug(f"Using cached price {current_price} for {token}", file_only=True)
                        
                        # If we didn't get a price from the cache, use zero
                        if current_price == 0:
                            warning(f"No valid price found for {token}")
                    except Exception as e:
                        warning(f"Error getting price for {token}: {str(e)}")
                    
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
                                    # Emit trade signal
                                    self.order_executed.emit(
                                        "copybot", "BUY", token_name or token, margin_amount, 
                                        current_price, None, None, wallet_address, token, ai_analysis
                                    )
                                else:
                                    warning(f"Leverage trade execution failed for {token} ({hl_symbol})")
                                    
                            elif action == "SELL":
                                info(f"Closing leveraged position on {hl_symbol}")
                                
                                # Calculate current position size and value before exit for PnL
                                positions = get_hl_positions()
                                position_amount = 0
                                position_value = 0
                                entry_price = 0
                                
                                if positions and hl_symbol in positions:
                                    position = positions[hl_symbol]
                                    position_amount = position.get('size', 0)
                                    current_price = position.get('current_price', 0)
                                    entry_price = position.get('entry_price', 0) if 'entry_price' in position else current_price
                                    position_value = position_amount * current_price
                                
                                # Execute the leveraged sell (full exit)
                                success = hl_exit(hl_symbol)
                                
                                if success:
                                    info(f"Successfully closed position on {token} ({hl_symbol})")
                                    
                                    # Calculate PnL
                                    pnl_value = 0
                                    pnl_percent = 0
                                    
                                    if position_amount > 0 and entry_price > 0:
                                        # Calculate approximate PnL
                                        pnl_value = position_amount * (current_price - entry_price)
                                        pnl_percent = ((current_price / entry_price) - 1) * 100
                                    
                                    # Emit trade signal
                                    self.order_executed.emit(
                                        "copybot", "SELL", token_name or token, position_amount, 
                                        entry_price, current_price, (pnl_value, pnl_percent), 
                                        wallet_address, token, ai_analysis
                                    )
                                else:
                                    warning(f"Failed to close position on {token} ({hl_symbol})")
                                
                            continue  # Skip to next token after leverage trading
                        else:
                            warning(f"No hyperliquid symbol found for {token}, using spot trading instead")
                            # Fall through to standard spot trading
                            
                    # Get current position value (spot trading path)
                    current_position = n.get_token_balance_usd(token)
                    position_amount = n.get_token_balance(token)
                    
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
                            # Emit trade signal
                            self.order_executed.emit(
                                "copybot", "BUY", token_name or token, amount_to_buy, 
                                current_price, None, None, wallet_address, token, ai_analysis
                            )
                        else:
                            warning(f"Trade execution failed for {token}")
                                
                    elif action == "SELL":
                        if current_position > 0:
                            info(f"Selling position worth ${current_position:.2f}")
                            
                            # Remember the token price before selling
                            entry_price = 0
                            if position_amount > 0:
                                entry_price = current_position / position_amount
                            
                            # Execute the sell using nice_funcs
                            success = n.chunk_kill(
                                token,
                                config.max_usd_order_size,  # From config.py
                                config.slippage  # From config.py
                            )
                            
                            if success:
                                info(f"Successfully sold {token}")
                                
                                # Calculate PnL (we don't have the original buy price, so use current_price as best guess)
                                pnl_value = None
                                pnl_percent = None
                                
                                # Use the cached price data - no need to fetch again
                                try:
                                    exit_price = current_price  # Use the price we already have
                                    
                                    # Calculate PnL if we have both prices
                                    if entry_price > 0 and exit_price > 0:
                                        pnl_value = position_amount * (exit_price - entry_price)
                                        pnl_percent = ((exit_price / entry_price) - 1) * 100
                                except Exception as e:
                                    warning(f"Error calculating PnL for {token}: {str(e)}")
                                
                                # Emit trade signal
                                self.order_executed.emit(
                                    "copybot", "SELL", token_name or token, position_amount, 
                                    entry_price, current_price, 
                                    (pnl_value, pnl_percent) if pnl_value is not None else None,
                                    wallet_address, token, ai_analysis
                                )
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
        """Execute trades by mirroring the tracked wallets when AI analysis is unavailable"""
        try:
            info("\nExecuting mirror trades based on wallet changes...")
            
            # First check if necessary functions exist in nice_funcs
            has_partial_kill = hasattr(n, 'partial_kill')
            if not has_partial_kill:
                warning("partial_kill function not found in nice_funcs. Will use chunk_kill for all sells.")
            
            # If changes weren't passed in, we need to fetch them
            if changes is None or wallet_results is None:
                info("No changes provided, fetching fresh data...")
                tracker = TokenAccountTracker()
                cached_results, _ = tracker.load_cache()
                wallet_results = tracker.track_all_wallets()
                changes = tracker.detect_changes(cached_results, wallet_results)
            
            if not changes:
                info("No changes to mirror!")
                return False
            
            # Process each wallet's changes
            for wallet, wallet_changes in changes.items():
                info(f"\nProcessing changes for wallet {wallet[:8]}...")
                
                # Process new tokens (potential buys)
                for token_mint, details in wallet_changes.get('new', {}).items():
                    token_name = details.get('name', 'Unknown Token')
                    symbol = details.get('symbol', 'UNK')
                    price = details.get('price', 0)
                    amount = details.get('amount', 0)
                    
                    info(f"New token detected: {symbol} ({token_name}) - BUY signal")
                    self.analyze_position(token_mint, token_status="new")
                    
                    # Calculate desired position based on the wallets' percentage allocation
                    wallet_position_value = details.get('usd_value', 0)
                    
                    # Skip small positions
                    if wallet_position_value < config.min_position_usd:
                        info(f"Position too small for {symbol} (${wallet_position_value:.2f} < ${config.min_position_usd:.2f}) - skipping")
                        continue
                    
                    # Calculate our desired position
                    desired_position = wallet_position_value * config.position_scale
                    
                    # Buy the token
                    try:
                        # Use buy_token_usd from nice_funcs to buy the token
                        info(f"Buying {symbol} worth ${desired_position:.2f}")
                        
                        success = False
                        try:
                            success = n.buy_token_usd(
                                token_mint,
                                desired_position,
                                config.max_usd_order_size,
                                config.slippage
                            )
                        except Exception as e:
                            warning(f"Error buying {symbol}: {e}")
                            continue
                            
                        if success:
                            info(f"Successfully bought {symbol}")
                            
                            # Emit trade signal to UI
                            self.order_executed.emit(
                                "copybot", "BUY", token_name, desired_position / price if price else 0,
                                price, price, None, wallet, token_mint,
                                f"Mirror Trading: New token in wallet {wallet[:8]}..."
                            )
                        else:
                            warning(f"Failed to buy {symbol}")
                    except Exception as e:
                        warning(f"Error buying {symbol}: {e}")
                
                # Process removed tokens (potential sells)
                for token_mint, details in wallet_changes.get('removed', {}).items():
                    token_name = details.get('name', 'Unknown Token') 
                    symbol = details.get('symbol', 'UNK')
                    
                    info(f"Removed token detected: {symbol} ({token_name}) - SELL signal")
                    self.analyze_position(token_mint, token_status="removed")
                    
                    # Get our current position
                    current_position = n.get_token_balance_usd(token_mint)
                    if current_position <= 0:
                        info(f"No position to sell for {symbol}")
                        continue
                    
                    # We should sell all of this token since the wallet removed it
                    try:
                        info(f"Selling all {symbol} (${current_position:.2f})")
                        success = n.chunk_kill(token_mint, config.max_usd_order_size, config.slippage)
                        
                        if success:
                            info(f"Successfully sold all {symbol}")
                            
                            # Emit trade signal
                            self.order_executed.emit(
                                "copybot", "SELL", token_name, n.get_token_balance(token_mint),
                                0, 0, None, wallet, token_mint,
                                f"Mirror Trading: Token removed from wallet {wallet[:8]}..."
                            )
                        else:
                            warning(f"Failed to sell {symbol}")
                    except Exception as e:
                        warning(f"Error selling {symbol}: {e}")
                
                # Process modified tokens
                for token_mint, details in wallet_changes.get('modified', {}).items():
                    token_name = details.get('name', 'Unknown Token')
                    symbol = details.get('symbol', 'UNK')
                    pct_change = details.get('pct_change', 0)
                    
                    # Check if we have a position to modify
                    current_position = n.get_token_balance_usd(token_mint)
                    position_amount = n.get_token_balance(token_mint)
                    
                    if current_position > 0:
                        # Auto-adjust the token in mirror mode
                        if pct_change > 0:
                            info(f"Modified token detected: {symbol} ({token_name}) - {pct_change:.2f}% INCREASE")
                        else:
                            info(f"Modified token detected: {symbol} ({token_name}) - {abs(pct_change):.2f}% DECREASE")
                        
                        # Get current price
                        current_price = current_position / position_amount if position_amount > 0 else 0
                        
                        # Get historical entry price if available
                        entry_price = n.get_entry_price(token_mint) or current_price
                        
                        if pct_change > 0:
                            # Wallet INCREASED position - BUY signal
                            # Calculate how much to buy based on pct_change
                            buy_percentage = pct_change / 100
                            
                            # Don't exceed max allocation
                            max_allocation = config.max_token_allocation
                            current_allocation = current_position / n.get_total_balance()
                            
                            if current_allocation >= max_allocation:
                                info(f"Already at maximum allocation for {symbol} ({current_allocation*100:.2f}% >= {max_allocation*100:.2f}%) - skipping buy")
                                continue
                            
                            info(f"Increasing position by {pct_change:.2f}% - Buying {buy_percentage*100:.2f}% more")
                            
                            # Calculate amount to buy
                            amount_to_buy = current_position * buy_percentage
                            
                            # Skip if amount is too small
                            if amount_to_buy < config.min_position_usd:
                                info(f"Buy amount too small for {symbol} (${amount_to_buy:.2f} < ${config.min_position_usd:.2f}) - skipping")
                                continue
                            
                            try:
                                success = n.buy_token_usd(
                                    token_mint,
                                    amount_to_buy,
                                    config.max_usd_order_size,
                                    config.slippage
                                )
                                
                                if success:
                                    info(f"Successfully bought more {symbol}")
                                    
                                    # Emit trade signal
                                    self.order_executed.emit(
                                        "copybot", "BUY", token_name, amount_to_buy / current_price if current_price else 0,
                                        entry_price, current_price, None, wallet, token_mint,
                                        f"Mirror Trading: Position increased by {pct_change:.2f}% in wallet {wallet[:8]}..."
                                    )
                                else:
                                    warning(f"Failed to buy more {symbol}")
                            except Exception as e:
                                warning(f"Error buying more {symbol}: {e}")
                        else:
                            # Wallet DECREASED position - SELL signal
                            # Calculate percentage to sell based on pct_change
                            sell_percentage = abs(pct_change) / 100
                            
                            # Never sell more than what we have
                            sell_percentage = min(sell_percentage, 1.0)
                            
                            if sell_percentage > 0:
                                info(f"Decreasing position by {abs(pct_change):.2f}% - Selling {sell_percentage*100:.2f}%")
                                try:
                                    success = False
                                    amount_to_sell = position_amount * sell_percentage
                                    
                                    if has_partial_kill:
                                        success = n.partial_kill(token_mint, sell_percentage, config.max_usd_order_size, config.slippage)
                                    else:
                                        # If we don't have partial_kill, and the sell is significant (>50%), do a full sale
                                        if sell_percentage > 0.5:
                                            success = n.chunk_kill(token_mint, config.max_usd_order_size, config.slippage)
                                        else:
                                            warning(f"No partial_kill available and sell percentage is only {sell_percentage*100:.2f}% - skipping")
                                            success = False
                                                
                                    if success:
                                        info(f"Successfully sold portion of {symbol}")
                                        
                                        # Calculate PnL
                                        pnl_value = None
                                        pnl_percent = None
                                        
                                        if entry_price > 0 and current_price > 0:
                                            pnl_value = amount_to_sell * (current_price - entry_price)
                                            pnl_percent = ((current_price / entry_price) - 1) * 100
                                        
                                        # Emit trade signal with mirror trading context
                                        mirror_context = f"Mirror Trading: Position decreased by {abs(pct_change):.2f}% in wallet {wallet[:8]}..."
                                        self.order_executed.emit(
                                            "copybot", "SELL", token_name, amount_to_sell,
                                            entry_price, current_price, 
                                            (pnl_value, pnl_percent) if pnl_value is not None else None,
                                            wallet, token_mint, mirror_context
                                        )
                                    else:
                                        warning(f"Failed to sell portion of {symbol}")
                                except Exception as e:
                                    warning(f"Error selling portion of {symbol}: {e}")
                            
                            # In AI mode, we would want to analyze the position
                            self.analyze_position(token_mint, token_status="modified", pct_change=pct_change)
                    else:
                        info(f"No position to modify for {symbol}")
            
            info("\nMirror trade execution complete!")
            return True
            
        except Exception as e:
            warning(f"Error executing mirror trades: {str(e)}")
            return False
            
    def run_analysis_cycle(self):
        """Run one cycle of analysis and trading"""
        try:
            # Track start time for performance monitoring
            start_time = time.time()
            
            # Initialize or clear market data cache for fresh data this cycle
            if not hasattr(self, 'market_data_cache'):
                self.market_data_cache = {}
            else:
                # Only clear if we want fresh data every cycle
                refresh_data = getattr(config, 'REFRESH_MARKET_DATA_EVERY_CYCLE', False)
                if refresh_data:
                    info("\nClearing market data cache for fresh analysis")
                    self.market_data_cache = {}
                else:
                    info("\nReusing existing market data cache")
            
            # Instead of creating a token tracker here, use the existing one from token_list_tool.py
            info("\nRunning wallet token tracker...")
            tracker = TokenAccountTracker()
            
            # Get cached data before any updates
            cache_data, _ = tracker.load_cache()
            
            # Call track_all_wallets to refresh cached data - Do this ONLY ONCE
            wallet_results = tracker.track_all_wallets()
            
            # Process the changes (wallets that have added or removed tokens)
            changes = tracker.detect_changes(cache_data, wallet_results)
            
            # Check if any changes were detected
            has_changes = False
            for wallet, wallet_changes in changes.items():
                if wallet_changes:
                    has_changes = True
                    self.changes_detected.emit(changes)
                    info(f"\nDetected {len(wallet_changes.get('new', {}))} new tokens, {len(wallet_changes.get('removed', {}))} removed tokens, and {len(wallet_changes.get('modified', {}))} modified tokens in wallet {wallet}")
                    break
            
            # If no changes detected, skip the rest of the cycle
            if not has_changes:
                info("\nNo changes detected in any tracked wallets. Skipping analysis.")
                elapsed = time.time() - start_time
                info(f"Analysis cycle completed in {elapsed:.2f} seconds")
                return
            
            # Based on our analysis mode, decide how to proceed
            if self.ai_analysis_available:
                info("\nRunning AI Portfolio Analysis Mode...")
                
                # Reset the recommendations DataFrame for this cycle
                self.recommendations_df = pd.DataFrame(columns=['token', 'action', 'confidence', 'reasoning'])
                
                # Load portfolio data ONCE for this cycle - but only if we have changes to analyze
                # Pass the wallet_results we already have to avoid redundant fetching
                self.load_portfolio_data(wallet_results, changes)
                
                # If we have no portfolio data, there's nothing to analyze
                if self.portfolio_df.empty:
                    info("No portfolio data to analyze")
                    elapsed = time.time() - start_time
                    info(f"Analysis cycle completed in {elapsed:.2f} seconds")
                    return
                
                # Analyze ONLY tokens with changes detected
                info("\nAnalyzing ONLY tokens with detected changes...")
                for wallet, wallet_changes in changes.items():
                    # Process new tokens with context
                    for token_mint, details in wallet_changes.get('new', {}).items():
                        token_name = details.get('name', 'Unknown Token')
                        symbol = details.get('symbol', 'UNK')
                        info(f"Analyzing new token: {symbol} ({token_name}) - BUY signal from wallet")
                        self.analyze_position(token_mint, token_status="new")
                    
                    # Process removed tokens with context
                    for token_mint, details in wallet_changes.get('removed', {}).items():
                        token_name = details.get('name', 'Unknown Token')
                        symbol = details.get('symbol', 'UNK')
                        info(f"Analyzing removed token: {symbol} ({token_name}) - SELL signal from wallet")
                        self.analyze_position(token_mint, token_status="removed")
                    
                    # Process modified tokens with context
                    for token_mint, details in wallet_changes.get('modified', {}).items():
                        token_name = details.get('name', 'Unknown Token')
                        symbol = details.get('symbol', 'UNK')
                        pct_change = details.get('pct_change', 0)
                        change_direction = "increased" if pct_change > 0 else "decreased"
                        
                        # Add more detailed logging for troubleshooting
                        debug(f"Token details for {symbol}:", file_only=True)
                        debug(f"  Previous amount: {details.get('previous_amount', 'N/A')}", file_only=True)
                        debug(f"  Current amount: {details.get('current_amount', 'N/A')}", file_only=True)
                        debug(f"  Change amount: {details.get('change', 'N/A')}", file_only=True)
                        debug(f"  Percentage change: {pct_change} ({change_direction})", file_only=True)
                        
                        info(f"Analyzing modified token: {symbol} ({token_name}) - {abs(pct_change):.2f}% {change_direction} in wallet")
                        self.analyze_position(token_mint, token_status="modified", pct_change=pct_change)
                
                # Execute position updates based on AI recommendations
                info("\nExecuting position updates based on AI recommendations...")
                self.execute_position_updates(wallet_results, changes)
            else:
                # Mirror Trading Mode - straight copy wallet actions
                info("\nRunning Mirror Trading Mode...")
                self.mirror_mode_active.emit(True)
                
                if has_changes:
                    info("\nMirroring wallet changes...")
                    # Execute trades by mirroring tracked wallets
                    self.execute_mirror_trades(wallet_results, changes)
                else:
                    info("No changes to mirror in wallets.")
                
                self.mirror_mode_active.emit(False)
            
            # Clean up
            elapsed = time.time() - start_time
            info(f"Analysis cycle completed in {elapsed:.2f} seconds")
            
        except Exception as e:
            warning(f"Error in analysis cycle: {str(e)}")
            # Log full traceback to the log file
            error(traceback.format_exc(), file_only=True)

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