"""
🌙 Moon Dev's Risk Management Agent
Built with love by Moon Dev 🚀
"""

# Import necessary modules
import anthropic
import os
import pandas as pd
import json
from termcolor import colored, cprint
from dotenv import load_dotenv
import openai
from src import config
from src import nice_funcs as n
from src import paper_trading
from src.scripts.ohlcv_collector import collect_all_tokens
from datetime import datetime, timedelta
import time
from src.config import *
from src.agents.base_agent import BaseAgent
import traceback
import re
from src.scripts.logger import logger, debug, info, warning, error, critical, system

# Import leverage utilities if available
try:
    from src.scripts.leverage_utils import get_hl_positions, get_hl_symbol
    LEVERAGE_UTILS_AVAILABLE = True
except ImportError:
    LEVERAGE_UTILS_AVAILABLE = False
    warning("Leverage utilities not available. Risk agent will not monitor leverage positions.")

# Load environment variables
load_dotenv()

class RiskAgent(BaseAgent):
    def __init__(self):
        """Initialize Moon Dev's Risk Agent 🛡️"""
        super().__init__('risk')  # Initialize base agent with type
        
        # Set AI parameters - use config values
        self.ai_model = config.AI_MODEL
        self.ai_temperature = config.AI_TEMPERATURE
        self.ai_max_tokens = config.AI_MAX_TOKENS
        
        info(f"Using AI Model: {self.ai_model}")
        
        load_dotenv()
        
        # Get API keys
        openai_key = os.getenv("OPENAI_KEY")
        anthropic_key = os.getenv("ANTHROPIC_KEY")
        deepseek_key = os.getenv("DEEPSEEK_KEY")
        
        if not openai_key:
            raise ValueError("OPENAI_KEY not found in environment variables!")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_KEY not found in environment variables!")
            
        # Check if leverage trading is enabled
        self.leverage_mode = config.TRADING_MODE.lower() == "leverage"
        if self.leverage_mode:
            if LEVERAGE_UTILS_AVAILABLE:
                info("Leverage trading mode detected - will monitor leverage positions")
            else:
                warning("Leverage trading mode detected but utilities not available")
                warning("Risk agent will only monitor spot positions")
            
        # Initialize OpenAI client for DeepSeek
        if deepseek_key and RISK_MODEL_OVERRIDE.lower() in ["deepseek-chat", "deepseek-reasoner"]:
            self.deepseek_client = openai.OpenAI(
                api_key=deepseek_key,
                base_url=RISK_DEEPSEEK_BASE_URL
            )
            info(f"DeepSeek model initialized with {RISK_MODEL_OVERRIDE}!")
        else:
            self.deepseek_client = None
            
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=anthropic_key)
        
        self.override_active = False
        self.last_override_check = None
        
        # Initialize start balance using portfolio value
        self.start_balance = self.get_portfolio_value()
        info(f"Initial Portfolio Balance: ${self.start_balance:.2f}")
        
        self.current_value = self.start_balance
        info("Risk Agent initialized!")
        
    def get_all_monitored_tokens(self):
        """Get comprehensive list of tokens to monitor from all sources"""
        try:
            info("\nBuilding comprehensive token monitoring list...")
            
            all_tokens = set()
            
            # 1. Add tokens from MONITORED_TOKENS list
            monitored_count = 0
            for token in config.MONITORED_TOKENS:
                if token not in config.EXCLUDED_TOKENS:
                    all_tokens.add(token)
                    monitored_count += 1
            debug(f"Added {monitored_count} tokens from MONITORED_TOKENS")
                    
            # 2. Add tokens from DCA_MONITORED_TOKENS
            dca_count = 0
            for token in config.DCA_MONITORED_TOKENS:
                if token not in config.EXCLUDED_TOKENS and token not in all_tokens:
                    all_tokens.add(token)
                    dca_count += 1
            debug(f"Added {dca_count} tokens from DCA_MONITORED_TOKENS")
                    
            # 3. Add tokens from hyperliquid mapping if hyperliquid is enabled
            # Modified to check for both USE_HYPERLIQUID and TRADING_MODE = 'leverage'
            leverage_count = 0
            if config.USE_HYPERLIQUID or config.TRADING_MODE.lower() == "leverage":
                for token_address in config.TOKEN_TO_HL_MAPPING.keys():
                    if token_address not in config.EXCLUDED_TOKENS and token_address not in all_tokens:
                        all_tokens.add(token_address)
                        leverage_count += 1
                if leverage_count > 0:
                    info(f"Added {leverage_count} tokens from leverage trading mapping")
            
            # 4. If in DYNAMIC_MODE, look at actual wallet holdings
            wallet_count = 0
            if config.DYNAMIC_MODE:
                try:
                    # Fetch all tokens in wallet
                    positions = n.fetch_wallet_holdings_og(config.address)
                    for _, row in positions.iterrows():
                        token_address = row['Mint Address']
                        if token_address not in config.EXCLUDED_TOKENS and token_address not in all_tokens:
                            all_tokens.add(token_address)
                            wallet_count += 1
                    debug(f"Added {wallet_count} tokens from wallet holdings")
                except Exception as e:
                    error(f"Error fetching wallet holdings: {str(e)}")
                
            # 5. Check TOKEN_MAP for any additional tokens
            token_map_count = 0
            for token_address in config.TOKEN_MAP.keys():
                if token_address not in config.EXCLUDED_TOKENS and token_address not in all_tokens:
                    all_tokens.add(token_address)
                    token_map_count += 1
            debug(f"Added {token_map_count} tokens from TOKEN_MAP")
                
            # Log the results
            info(f"Total tokens to monitor: {len(all_tokens)}")
            if self.leverage_mode and LEVERAGE_UTILS_AVAILABLE:
                info("🔄 Monitoring both spot and leverage positions")
            return list(all_tokens)
            
        except Exception as e:
            error(f"Error building token list: {str(e)}")
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)
            # Fallback to just MONITORED_TOKENS
            return config.MONITORED_TOKENS

    def get_portfolio_value(self):
        """Calculate total portfolio value in USD"""
        try:
            info("\nPortfolio Value Calculator Starting...")
            
            # Check if paper trading is enabled
            try:
                from src.config import PAPER_TRADING_ENABLED
                if PAPER_TRADING_ENABLED:
                    # Use paper trading wrapper to get portfolio value
                    paper_value = paper_trading.get_portfolio_value()
                    if paper_value is not None:
                        info(f"Using paper trading portfolio value: ${paper_value:.2f}")
                        return paper_value
            except ImportError:
                # If can't import the config, continue with real portfolio calculation
                pass
            
            # Original implementation for real trading
            # Get full list of tokens to monitor
            tokens_to_check = self.get_all_monitored_tokens()
            
            # Use the batch method to check all token balances
            total_value, _ = self.batch_check_token_balances(tokens_to_check)
            
            return total_value
            
        except Exception as e:
            error(f"Error calculating portfolio value: {str(e)}")
            debug("Full error trace:", file_only=True)
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)
            return 0.0

    def log_daily_balance(self):
        """Log portfolio value if not logged in past check period"""
        try:
            debug("\nChecking if we need to log daily balance...")
            
            # Create data directory if it doesn't exist
            os.makedirs('src/data', exist_ok=True)
            balance_file = 'src/data/portfolio_balance.csv'
            debug(f"Using balance file: {balance_file}")
            
            # Check if we already have a recent log
            if os.path.exists(balance_file):
                debug("Found existing balance log file")
                df = pd.read_csv(balance_file)
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    last_log = df['timestamp'].max()
                    hours_since_log = (datetime.now() - last_log).total_seconds() / 3600
                    
                    debug(f"Hours since last log: {hours_since_log:.1f}")
                    debug(f"Max hours between checks: {config.MAX_LOSS_GAIN_CHECK_HOURS}")
                    
                    if hours_since_log < config.MAX_LOSS_GAIN_CHECK_HOURS:
                        info(f"Recent balance log found ({hours_since_log:.1f} hours ago)")
                        return
            else:
                debug("Creating new balance log file")
                df = pd.DataFrame(columns=['timestamp', 'balance'])
            
            # Get current portfolio value
            debug("\nGetting fresh portfolio value...")
            current_value = self.get_portfolio_value()
            
            # Add new row
            new_row = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'balance': current_value
            }
            debug(f"Adding new balance record: {new_row}")
            
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
            # Save updated log
            df.to_csv(balance_file, index=False)
            info(f"New portfolio balance logged: ${current_value:.2f}")
            
        except Exception as e:
            error(f"Error logging balance: {str(e)}")
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)

    def get_position_data(self, token):
        """Get recent market data for a token"""
        try:
            # Get 8h of 15m data
            data_15m = n.get_data(token, 0.33, '15m')  # 8 hours = 0.33 days
            
            # Get 2h of 5m data
            data_5m = n.get_data(token, 0.083, '5m')   # 2 hours = 0.083 days
            
            return {
                '15m': data_15m.to_dict() if data_15m is not None else None,
                '5m': data_5m.to_dict() if data_5m is not None else None
            }
        except Exception as e:
            warning(f"Error getting data for {token}: {str(e)}")
            return None

    def should_override_limit(self, limit_type):
        """Ask AI if we should override the limit based on recent market data"""
        try:
            # Only check every X minutes according to config
            check_interval = timedelta(minutes=RISK_CHECK_INTERVAL_MINUTES)
            if (self.last_override_check and 
                datetime.now() - self.last_override_check < check_interval):
                return self.override_active
            
            # Get current positions first
            positions = n.fetch_wallet_holdings_og(address)
            
            # Get comprehensive token list to monitor
            all_monitored_tokens = self.get_all_monitored_tokens()
            
            # Filter for tokens that are in our monitoring list and not excluded
            positions = positions[
                positions['Mint Address'].isin(all_monitored_tokens) & 
                ~positions['Mint Address'].isin(EXCLUDED_TOKENS)
            ]
            
            if positions.empty:
                warning("No monitored positions found to analyze")
                return False
            
            # Collect data only for monitored tokens we have positions in
            position_data = {}
            for _, row in positions.iterrows():
                token = row['Mint Address']
                current_value = row['USD Value']
                
                if current_value > 0:  # Double check we have a position
                    info(f"Getting market data for monitored position: {token}")
                    token_data = self.get_position_data(token)
                    if token_data:
                        position_data[token] = {
                            'value_usd': current_value,
                            'data': token_data
                        }
            
            if not position_data:
                warning("Could not get market data for any monitored positions")
                return False
                
            # Format data for AI analysis
            prompt = RISK_OVERRIDE_PROMPT.format(
                limit_type=limit_type,
                position_data=json.dumps(position_data, indent=2)
            )
            
            info("AI Agent analyzing market data...")
            
            # Use DeepSeek if configured
            if self.deepseek_client and RISK_MODEL_OVERRIDE.lower() in ["deepseek-chat", "deepseek-reasoner"]:
                info(f"Using {RISK_MODEL_OVERRIDE} for analysis...")
                response = self.deepseek_client.chat.completions.create(
                    model=RISK_MODEL_OVERRIDE.lower(),
                    messages=[
                        {"role": "system", "content": "You are Moon Dev's Risk Management AI. Analyze positions and respond with OVERRIDE or RESPECT_LIMIT."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature,
                    stream=False
                )
                response_text = response.choices[0].message.content.strip()
            else:
                # Use Claude as before
                info("Using Claude for analysis...")
                message = self.client.messages.create(
                    model=self.ai_model,
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                response_text = str(message.content)
            
            # Handle TextBlock format if using Claude
            if 'TextBlock' in response_text:
                match = re.search(r"text='([^']*)'", response_text)
                if match:
                    response_text = match.group(1)
            
            self.last_override_check = datetime.now()
            
            # Check for OVERRIDE or RESPECT_LIMIT decision
            has_override = "OVERRIDE" in response_text.upper()
            
            # Extract confidence score
            confidence_score = 0
            confidence_pattern = r"(\d{1,3})%\s+confidence"
            match = re.search(confidence_pattern, response_text)
            if match:
                confidence_score = int(match.group(1))
                info(f"Detected confidence score: {confidence_score}%")
            else:
                warning("No confidence score detected in AI response")
            
            # Determine required confidence based on limit type
            required_confidence = RISK_LOSS_CONFIDENCE_THRESHOLD if "LOSS" in limit_type.upper() else RISK_GAIN_CONFIDENCE_THRESHOLD
            info(f"Required confidence for {limit_type}: {required_confidence}%")
            
            # Make decision based on confidence threshold
            self.override_active = False
            if has_override and confidence_score >= required_confidence:
                self.override_active = True
                info(f"Override approved with {confidence_score}% confidence (threshold: {required_confidence}%)")
            elif has_override:
                warning(f"Override rejected: {confidence_score}% confidence below threshold of {required_confidence}%")
            else:
                warning("AI recommended to respect limit")
            
            # Print the AI's reasoning with model info
            info("\nRisk Agent Analysis:")
            info(f"Using model: {'DeepSeek' if self.deepseek_client else 'Claude'}")
            # Log full response to file only, but provide a summary to console
            logger.debug(f"Full AI response:\n{response_text}", file_only=True)
            
            if self.override_active:
                warning("\nRisk Agent suggests keeping positions open")
            else:
                warning("\nRisk Agent recommends closing positions")
            
            return self.override_active
            
        except Exception as e:
            error(f"Error in override check: {str(e)}")
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)
            return False

    def check_pnl_limits(self):
        """Check if PnL limits have been hit"""
        try:
            self.current_value = self.get_portfolio_value()
            
            # Prevent division by zero when checking percentage changes
            if USE_PERCENTAGE and self.start_balance == 0:
                debug("Skipping percentage PnL check - start balance is zero")
                return False
                
            if USE_PERCENTAGE:
                # Calculate percentage change
                percent_change = ((self.current_value - self.start_balance) / self.start_balance) * 100
                
                if percent_change <= -MAX_LOSS_PERCENT:
                    warning("\nMAXIMUM LOSS PERCENTAGE REACHED")
                    warning(f"Loss: {percent_change:.2f}% (Limit: {MAX_LOSS_PERCENT}%)")
                    return True
                    
                if percent_change >= MAX_GAIN_PERCENT:
                    info("\nMAXIMUM GAIN PERCENTAGE REACHED")
                    info(f"Gain: {percent_change:.2f}% (Limit: {MAX_GAIN_PERCENT}%)")
                    return True
                    
            else:
                # Calculate USD change
                usd_change = self.current_value - self.start_balance
                
                if usd_change <= -MAX_LOSS_USD:
                    warning("\nMAXIMUM LOSS USD REACHED")
                    warning(f"Loss: ${abs(usd_change):.2f} (Limit: ${MAX_LOSS_USD:.2f})")
                    return True
                    
                if usd_change >= MAX_GAIN_USD:
                    info("\nMAXIMUM GAIN USD REACHED")
                    info(f"Gain: ${usd_change:.2f} (Limit: ${MAX_GAIN_USD:.2f})")
                    return True
            
            return False
            
        except Exception as e:
            error(f"Error checking PnL limits: {e}")
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)
            return False

    def close_all_positions(self):
        """Close all monitored positions except USDC and SOL"""
        try:
            info("\nClosing monitored positions...")
            
            # Get all positions
            positions = n.fetch_wallet_holdings_og(address)
            
            # Get comprehensive token list to monitor
            all_monitored_tokens = self.get_all_monitored_tokens()
            
            # Debug print to see what we're working with
            debug("\nCurrent positions:", file_only=True)
            logger.debug(f"Current positions:\n{positions.head()}", file_only=True)
            debug("\nAll monitored tokens:", file_only=True)
            logger.debug(f"All monitored tokens:\n{all_monitored_tokens}", file_only=True)
            
            # Filter for tokens that are both in all_monitored_tokens and not in EXCLUDED_TOKENS
            positions = positions[
                positions['Mint Address'].isin(all_monitored_tokens) & 
                ~positions['Mint Address'].isin(EXCLUDED_TOKENS)
            ]
            
            if positions.empty:
                info("No monitored positions to close")
                return
                
            # Close each monitored position
            for _, row in positions.iterrows():
                token = row['Mint Address']
                value = row['USD Value']
                
                info(f"\nClosing position: {token} (${value:.2f})")
                try:
                    n.chunk_kill(token, max_usd_order_size, slippage)
                    info(f"Successfully closed position for {token}")
                except Exception as e:
                    error(f"Error closing position for {token}: {str(e)}")
                    
            info("\nAll monitored positions closed")
            
        except Exception as e:
            error(f"Error in close_all_positions: {str(e)}")
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)

    def check_risk_limits(self):
        """Check if any risk limits have been breached"""
        try:
            # Get current PnL
            current_pnl = self.get_current_pnl()
            current_balance = self.get_portfolio_value()
            
            info(f"\nCurrent PnL: ${current_pnl:.2f}")
            info(f"Current Balance: ${current_balance:.2f}")
            info(f"Minimum Balance Limit: ${MINIMUM_BALANCE_USD:.2f}")
            
            # Check minimum balance limit
            if current_balance < MINIMUM_BALANCE_USD:
                warning(f"ALERT: Current balance ${current_balance:.2f} is below minimum ${MINIMUM_BALANCE_USD:.2f}")
                self.handle_limit_breach("MINIMUM_BALANCE", current_balance)
                return True
            
            # Check PnL limits
            if USE_PERCENTAGE:
                if abs(current_pnl) >= MAX_LOSS_PERCENT:
                    warning(f"PnL limit reached: {current_pnl}%")
                    self.handle_limit_breach("PNL_PERCENT", current_pnl)
                    return True
            else:
                if abs(current_pnl) >= MAX_LOSS_USD:
                    warning(f"PnL limit reached: ${current_pnl:.2f}")
                    self.handle_limit_breach("PNL_USD", current_pnl)
                    return True
                    
            info("All risk limits OK")
            return False
            
        except Exception as e:
            error(f"Error checking risk limits: {str(e)}")
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)
            return False
            
    def handle_limit_breach(self, breach_type, current_value):
        """Handle breached risk limits with AI consultation if enabled"""
        try:
            # If AI confirmation is disabled, close positions immediately
            if not USE_AI_CONFIRMATION:
                warning(f"\n{breach_type} limit breached! Closing all positions immediately...")
                info(f"(AI confirmation disabled in config)")
                self.close_all_positions()
                return
                
            # Get all current positions using fetch_wallet_holdings_og
            positions_df = n.fetch_wallet_holdings_og(address)
            
            # Get comprehensive token list to monitor
            all_monitored_tokens = self.get_all_monitored_tokens()
            
            # Filter for positions that are in our monitoring lists
            positions_df = positions_df[
                positions_df['Mint Address'].isin(all_monitored_tokens) & 
                ~positions_df['Mint Address'].isin(EXCLUDED_TOKENS)
            ]
            
            # Prepare breach context
            if breach_type == "MINIMUM_BALANCE":
                context = f"Current balance (${current_value:.2f}) has fallen below minimum balance limit (${MINIMUM_BALANCE_USD:.2f})"
            elif breach_type == "PNL_USD":
                context = f"Current PnL (${current_value:.2f}) has exceeded USD limit (${MAX_LOSS_USD:.2f})"
            else:
                context = f"Current PnL ({current_value}%) has exceeded percentage limit ({MAX_LOSS_PERCENT}%)"
            
            # Format positions for AI
            positions_str = "\nCurrent Positions:\n"
            for _, row in positions_df.iterrows():
                if row['USD Value'] > 0:
                    positions_str += f"- {row['Mint Address']}: {row['Amount']} (${row['USD Value']:.2f})\n"
                    
            # Get AI recommendation
            prompt = f"""
RISK LIMIT BREACH ALERT

{context}

{positions_str}

Should we close all positions immediately? Consider:
1. Market conditions
2. Position sizes
3. Recent price action
4. Risk of further losses

Respond with:
CLOSE_ALL or HOLD_POSITIONS
Then explain your reasoning.
"""
            # Use DeepSeek if configured
            if self.deepseek_client and RISK_MODEL_OVERRIDE.lower() in ["deepseek-chat", "deepseek-reasoner"]:
                info(f"Using {RISK_MODEL_OVERRIDE} for analysis...")
                response = self.deepseek_client.chat.completions.create(
                    model=RISK_MODEL_OVERRIDE.lower(),
                    messages=[
                        {"role": "system", "content": "You are Moon Dev's Risk Management AI. Analyze the breach and decide whether to close positions."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature,
                    stream=False
                )
                response_text = response.choices[0].message.content.strip()
            else:
                # Use Claude as before
                info("Using Claude for analysis...")
                message = self.client.messages.create(
                    model=self.ai_model,
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                response_text = str(message.content)
            
            # Handle TextBlock format if using Claude
            if 'TextBlock' in response_text:
                match = re.search(r"text='([^']*)'", response_text)
                if match:
                    response_text = match.group(1)
            
            info("\nAI Risk Assessment:")
            debug("=" * 50, file_only=True)
            debug(f"Using model: {'DeepSeek' if self.deepseek_client else 'Claude'}", file_only=True)
            logger.debug(f"Full AI response:\n{response_text}", file_only=True)
            debug("=" * 50, file_only=True)
            
            # Parse decision
            decision = response_text.split('\n')[0].strip()
            
            if decision == "CLOSE_ALL":
                warning("AI recommends closing all positions!")
                self.close_all_positions()
            else:
                info("AI recommends holding positions despite breach")
                
        except Exception as e:
            error(f"Error handling limit breach: {str(e)}")
            # Default to closing positions on error
            warning("Error in AI consultation - defaulting to close all positions")
            self.close_all_positions()

    def get_current_pnl(self):
        """Calculate current PnL based on start balance"""
        try:
            current_value = self.get_portfolio_value()
            debug(f"\nStart Balance: ${self.start_balance:.2f}")
            debug(f"Current Value: ${current_value:.2f}")
            
            # Calculate absolute PnL in USD
            pnl = current_value - self.start_balance
            
            # Add percentage info if possible
            if self.start_balance > 0:
                pnl_pct = (pnl / self.start_balance) * 100
                debug(f"Current PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
            else:
                debug(f"Current PnL: ${pnl:.2f} (N/A%)")
                
            return pnl
            
        except Exception as e:
            error(f"Error calculating PnL: {str(e)}")
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)
            return 0.0

    def batch_check_token_balances(self, tokens_to_check):
        """Check multiple token balances in a batch to minimize API calls and reduce error messages"""
        total_value = 0.0
        balances = {}
        
        # Skip empty token lists
        if not tokens_to_check:
            return total_value, balances
            
        try:
            # Log start of batch check
            debug(f"Batch checking balances for {len(tokens_to_check)} tokens", file_only=True)
            
            # Get USDC balance first (handle separately as it's important)
            if config.USDC_ADDRESS in tokens_to_check:
                try:
                    usdc_value = n.get_token_balance_usd(config.USDC_ADDRESS)
                    if usdc_value > 0:
                        info(f"USDC Value: ${usdc_value:.2f}")
                        total_value += usdc_value
                        balances[config.USDC_ADDRESS] = usdc_value
                    tokens_to_check.remove(config.USDC_ADDRESS)  # Remove from list to avoid double processing
                except Exception as e:
                    # Only log USDC errors at debug level since they're common
                    debug(f"Error getting USDC balance: {str(e)}", file_only=True)
            
            # Process remaining tokens in batches
            found_tokens = 0
            errors = 0
            
            for token in tokens_to_check:
                try:
                    # Check spot balances first
                    token_value = n.get_token_balance_usd(token)
                    token_has_value = token_value > 0
                    
                    # Check leverage positions if available
                    leverage_value = 0
                    if LEVERAGE_UTILS_AVAILABLE and config.TRADING_MODE.lower() == "leverage":
                        # Try to get Hyperliquid symbol for this token
                        hl_symbol = get_hl_symbol(token)
                        if hl_symbol:
                            # Get leverage positions
                            positions = get_hl_positions()
                            if positions and hl_symbol in positions:
                                pos = positions[hl_symbol]
                                leverage_value = pos.get('size', 0) * pos.get('current_price', 0)
                                if leverage_value > 0:
                                    info(f"Found {hl_symbol} leverage position worth: ${leverage_value:.2f}")
                                    token_has_value = True
                    
                    # Combine spot and leverage values
                    combined_value = token_value + leverage_value
                    
                    if token_has_value:
                        found_tokens += 1
                        if token_value > 0:
                            info(f"Found {token[:8]} spot position worth: ${token_value:.2f}")
                        
                        total_value += combined_value
                        balances[token] = combined_value
                except Exception:
                    # Silently count errors but don't log each one
                    errors += 1
            
            # Only log summary of errors rather than individual messages
            if errors > 0:
                debug(f"Encountered {errors} errors checking token balances", file_only=True)
                
            debug(f"Found {found_tokens} tokens with non-zero balances", file_only=True)
            info(f"Total Portfolio Value: ${total_value:.2f}")
            
            return total_value, balances
            
        except Exception as e:
            error(f"Error in batch token balance check: {str(e)}")
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)
            return 0.0, {}

    def run(self):
        """Run the risk agent (implements BaseAgent interface)"""
        try:
            # Get current PnL
            current_pnl = self.get_current_pnl()
            current_balance = self.get_portfolio_value()
            
            info(f"\nCurrent PnL: ${current_pnl:.2f}")
            info(f"Current Balance: ${current_balance:.2f}")
            info(f"Minimum Balance Limit: ${MINIMUM_BALANCE_USD:.2f}")
            
            # Skip checking limits if we have zero balance and using percentage-based limits
            if USE_PERCENTAGE and self.start_balance == 0:
                debug("Skipping percentage PnL check in run() - start balance is zero")
                return False
            
            # Check minimum balance limit
            if current_balance < MINIMUM_BALANCE_USD:
                warning(f"ALERT: Current balance ${current_balance:.2f} is below minimum ${MINIMUM_BALANCE_USD:.2f}")
                self.handle_limit_breach("MINIMUM_BALANCE", current_balance)
                return True
            
            # Check PnL limits
            if USE_PERCENTAGE:
                if abs(current_pnl) >= MAX_LOSS_PERCENT:
                    warning(f"PnL limit reached: {current_pnl}%")
                    self.handle_limit_breach("PNL_PERCENT", current_pnl)
                    return True
            else:
                if abs(current_pnl) >= MAX_LOSS_USD:
                    warning(f"PnL limit reached: ${current_pnl:.2f}")
                    self.handle_limit_breach("PNL_USD", current_pnl)
                    return True
                    
            info("All risk limits OK")
            return False
            
        except Exception as e:
            error(f"Error checking risk limits: {str(e)}")
            logger.error(f"Error: {str(e)}\n{traceback.format_exc()}", file_only=True)
            return False

def main():
    """Main function to run the risk agent"""
    system("Risk Agent Starting...")
    
    agent = RiskAgent()
    
    while True:
        try:
            # Always try to log balance (function will check if 12 hours have passed)
            agent.log_daily_balance()
            
            # Always check PnL limits
            agent.check_pnl_limits()
            
            # Sleep for 5 minutes before next check
            time.sleep(300)
                
        except KeyboardInterrupt:
            info("\nRisk Agent shutting down gracefully...")
            break
        except Exception as e:
            error(f"Error: {str(e)}")
            warning("Moon Dev suggests checking the logs and trying again!")
            time.sleep(300)  # Still sleep on error

if __name__ == "__main__":
    main()

