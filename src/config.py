"""
🌙 Anarcho Capital's Configuration File
Built with love by Anarcho Capital 🚀
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Logging Configuration 🔊

# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"  # Default level - less verbose than DEBUG

# Log file settings
LOG_TO_FILE = True  # Whether to save logs to file
LOG_DIRECTORY = "logs"  # Directory to store log files
LOG_FILENAME = "trading_system.log"  # Name of the log file
LOG_MAX_SIZE_MB = 10  # Maximum size of log file before rotation (in MB)
LOG_BACKUP_COUNT = 5  # Number of backup log files to keep

# UI Console logging settings
CONSOLE_LOG_LEVEL = "INFO"  # Level for console UI (can be different from file logging)
SHOW_DEBUG_IN_CONSOLE = False  # Whether to show DEBUG messages in the UI console
SHOW_TIMESTAMPS_IN_CONSOLE = True  # Whether to show timestamps in console messages

# Global AI Model Settings (used as fallbacks)
AI_MODEL = "claude-3-haiku-20240307"
AI_TEMPERATURE = 0.7
AI_MAX_TOKENS = 1024

# Agent Runtime Settings ⏱️
SLEEP_BETWEEN_RUNS_MINUTES = 15  # General sleep time between agent runs 🕒

# 💰 Trading Configuration
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # Never trade or close
SOL_ADDRESS = "So11111111111111111111111111111111111111111"   # Never trade or close

# Create a list of addresses to exclude from trading/closing
EXCLUDED_TOKENS = [USDC_ADDRESS, SOL_ADDRESS]

# Token and wallet settings
symbol = '9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump'  # input ticker symbol (FART) here for main token to focus on
# Get wallet address from environment variable 
address = os.getenv('DEFAULT_WALLET_ADDRESS')

#toggle between trackfetching all tokens on tracked wallet list or tokens shared on monitored tokens & tracked tokens list
DYNAMIC_MODE = True # Set to False to monitor only MONITORED_TOKENS
previous_mode = None  # Track mode changes globally

# Token List for Trading 📋
MONITORED_TOKENS = [
    'VFdxjTdFzXrYr3ivWyf64NuXo9U7vdPK7AG7idnNZJV',
    'CR2L1ob96JGWQkdFbt8rLwqdLLmqFwjcNGL2eFBn1RPt',
    '2HdzfUiFWfZHZ544ynffeneuibbDK6biCdjovejr8ez9',
    'C94njgTrKMQBmgqe23EGLrtPgfvcjWtqBBvGQ7Cjiank',
    '67mTTGnVRunoSLGitgRGK2FJp5cT1KschjzWH9zKc3r',
    '9YnfbEaXPaPmoXnKZFmNH8hzcLyjbRf56MQP7oqGpump',
    'DayN9FxpLAeiVrFQnRxwjKq7iVQxTieVGybhyXvSpump',
]

# Global variable to store the previous MONITORED_TOKENS list
previous_monitored_tokens = []
# Using the same list for trading
tokens_to_trade = MONITORED_TOKENS  

# List of wallets to track for CopyBot - Must be in the correct format
WALLETS_TO_TRACK = WALLETS_TO_TRACK = [
    "FXzJ6xwH2HfdKshERVAYiLh79PAUw9zC7ucngupt91ap",
    "242p259rfsb9J3X3mhnWw35UM2hfMDg14G47CQ66s9ZW",
    # Add more wallets here as needed
]

# CopyBot Runtime Mode
COPYBOT_CONTINUOUS_MODE = False
COPYBOT_INTERVAL_MINUTES = 5
COPYBOT_SKIP_ANALYSIS_ON_FIRST_RUN = False

#CopyBot Settings
FILTER_MODE = "Dynamic"
PERCENTAGE_THRESHOLD = 0.1
AMOUNT_THRESHOLD = 6000
ENABLE_PERCENTAGE_FILTER = True
ENABLE_AMOUNT_FILTER = True
ENABLE_ACTIVITY_FILTER = False
ACTIVITY_WINDOW_HOURS = 1

# CopyBot Mirror Trading Settings
COPYBOT_AUTO_BUY_NEW_TOKENS = True  # Auto-buy new tokens in mirror mode
COPYBOT_AUTO_SELL_REMOVED_TOKENS = True  # Auto-sell removed tokens
COPYBOT_WALLET_ACTION_WEIGHT = 0.6
COPYBOT_MIRROR_EXACT_PERCENTAGE = True  # Mirror exact percentage changes from tracked wallets

# API and Network Settings 🌐
API_SLEEP_SECONDS = 1.8
API_TIMEOUT_SECONDS = 37
API_MAX_RETRIES = 10

# Model override settings for CopyBot
COPYBOT_MODEL_OVERRIDE = "deepseek-reasoner"
COPYBOT_MIN_CONFIDENCE = 79
ENABLE_AI_ANALYSIS = True# Toggle for AI analysis in CopyBot

# CopyBot Portfolio Analysis Prompt - The AI prompt template for analysis
PORTFOLIO_ANALYSIS_PROMPT = """
You are Anarcho Capital's CopyBot Agent 🌙

Your task is to analyze the current copybot portfolio positions and market data to identify which positions deserve larger allocations.

Data provided:
1. Current copybot portfolio positions and their performance
2. OHLCV market data for each position
3. Technical indicators (MA20, MA40, ABOVE OR BELOW)

Analysis Criteria:
1. Position performance metrics
2. Price action and momentum
3. Volume analysis
4. Risk/reward ratio
5. Market conditions

{portfolio_data}
{market_data}

Respond in this exact format:
1. First line must be one of: BUY, SELL, or NOTHING (in caps)
2. Then explain your reasoning, including:
   - Position analysis
   - Technical analysis
   - Volume profile
   - Risk assessment
   - Market conditions
   - Confidence level (as a percentage, e.g. 75%)

Remember: 
- Do not worry about the low position size of the copybot, but more so worry about the size vs the others in the portfolio. this copy bot acts as a scanner for you to see what type of opportunties are out there and trending. 
- Look for high-conviction setups
- Consider both position performance against others in the list and market conditions
"""

# Trading Mode Configuration 🔄
TRADING_MODE = "spot"
USE_HYPERLIQUID = False
DEFAULT_LEVERAGE = 2.0
MAX_LEVERAGE = 5.0
MIRROR_WITH_LEVERAGE = False
LEVERAGE_SAFETY_BUFFER = 0.8

# Token to Hyperliquid Symbol Mapping
TOKEN_TO_HL_MAPPING = TOKEN_TO_HL_MAPPING = {
    # Format: "Solana token address": "Hyperliquid symbol",
    "So11111111111111111111111111111111111111112": "SOL",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    # Add more mappings as needed
}

#Backtesting
DAYSBACK_4_DATA = 6
DATA_TIMEFRAME = '1H'

# Paper Trading Settings 📝
PAPER_TRADING_ENABLED = False# Toggle paper trading mode on/off
PAPER_INITIAL_BALANCE = 1005.0# Initial paper trading balance in USD
PAPER_TRADING_SLIPPAGE = 104# Simulated slippage for paper trades (100 = 1%)
PAPER_TRADING_RESET_ON_START = False# Whether to reset paper portfolio on app start

# Position sizing 🎯
usd_size = 30.0# account_balance * 0.085 or 0.12: Size of position to hold
max_usd_order_size = 6.0# Max order size
tx_sleep = 18.0# Sleep between transactions
slippage = 219# 500 = 5% and 50 = .5% slippage
PRIORITY_FEE = 100006# ~0.02 USD at current SOL prices
orders_per_open = 5# Multiple orders for better fill rates

# Risk Management Settings 🛡️
CASH_PERCENTAGE = 23# Minimum % to keep in USDC as safety buffer (0-100)
MAX_POSITION_PERCENTAGE = 14# Maximum % allocation per position (0-100)
STOPLOSS_PRICE = 2 # NOT USED YET 1/5/25    
BREAKOUT_PRICE = .0002 # NOT USED YET 1/5/25
SLEEP_AFTER_CLOSE = 904# Prevent overtrading

MAX_LOSS_GAIN_CHECK_HOURS = 29# How far back to check for max loss/gain limits (in hours)
SLEEP_BETWEEN_RUNS_MINUTES = 10  # How long to sleep between agent runs 🕒

# Max Loss/Gain Settings FOR RISK AGENT 1/5/25
USE_PERCENTAGE = True# If True, use percentage-based limits. If False, use USD-based limits

# USD-based limits (used if USE_PERCENTAGE is False)
MAX_LOSS_USD = 25.0# Maximum loss in USD before stopping trading
MAX_GAIN_USD = 25.0# Maximum gain in USD before stopping trading

# Percentage-based limits (used if USE_PERCENTAGE is True)
MAX_LOSS_PERCENT = 23# Maximum loss as percentage (e.g., 20 = 20% loss)
MAX_GAIN_PERCENT = 500# Maximum gain as percentage (e.g., 50 = 50% gain)

# USD MINIMUM BALANCE RISK CONTROL
MINIMUM_BALANCE_USD = 108.0# account_balance * (1/3): If balance falls below this, risk agent will consider closing all positions

# Percentage-based limits (used if USE_PERCENTAGE is True)
MAX_LOSS_PERCENT = 23# Maximum loss as percentage (e.g., 20 = 20% loss)
MAX_GAIN_PERCENT = 500# Maximum gain as percentage (e.g., 50 = 50% gain)

# Risk Agent AI Configuration
RISK_MODEL_OVERRIDE = "deepseek-reasoner"
RISK_DEEPSEEK_BASE_URL = "https://api.deepseek.com"  # Base URL for DeepSeek API
RISK_CHECK_INTERVAL_MINUTES = 10
RISK_LOSS_CONFIDENCE_THRESHOLD = 77# Minimum confidence to override max loss limits (0-100)
RISK_GAIN_CONFIDENCE_THRESHOLD = 70# Minimum confidence to override max gain limits (0-100)
RISK_CONTINUOUS_MODE = False# When True, Risk Agent runs continuously instead of on interval
USE_AI_CONFIRMATION = True#risk agent ai confirmation

# 🛡️ Risk Override Prompt - The Secret Sauce!
RISK_OVERRIDE_PROMPT = """
You are Anarcho Capital's Risk Management Agent 📈

Your task is to analyze the current portfolio and market conditions to determine the optimal risk level for your trading strategy.

Data provided:
1. Current portfolio composition and performance
2. OHLCV market data for each position
3. Technical indicators (MA20, MA40, ABOVE OR BELOW)

Analysis Criteria:
1. Risk management metrics
2. Price action and momentum
3. Volume analysis
4. Risk/reward ratio
5. Market conditions

{portfolio_data}
{market_data}

Respond in this exact format:
1. First line must be one of: BUY, SELL, or NOTHING (in caps)
2. Then explain your reasoning, including:
   - Risk assessment
   - Technical analysis
   - Volume profile
   - Risk/reward ratio
   - Market conditions
   - Confidence level (as a percentage, e.g. 75%)

Remember: 
- Always prioritize risk management over potential gains
- Be conservative in volatile markets
- Consider both absolute and percentage-based thresholds
- Provide clear, actionable advice
"""

# Specific tokens for DCA Agent
TOKEN_MAP = TOKEN_MAP = TOKEN_MAP = TOKEN_MAP = TOKEN_MAP = TOKEN_MAP = TOKEN_MAP = TOKEN_MAP = TOKEN_MAP = TOKEN_MAP = {
    'HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC': ('AI16Z', 'AI16Z'),
    'So11111111111111111111111111111111111111112': ('SOL', 'SOL'),
    '9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump': ('FART', 'FARTCOIN'),
}

DCA_MONITORED_TOKENS = list(TOKEN_MAP.keys())

DCA_MONITORED_TOKENS = [
    'VFdxjTdFzXrYr3ivWyf64NuXo9U7vdPK7AG7idnNZJV',
    'CR2L1ob96JGWQkdFbt8rLwqdLLmqFwjcNGL2eFBn1RPt',
    '2HdzfUiFWfZHZ544ynffeneuibbDK6biCdjovejr8ez9',
    'C94njgTrKMQBmgqe23EGLrtPgfvcjWtqBBvGQ7Cjiank',
    '67mTTGnVRunoSLGitgRGK2FJp5cT1KschjzWH9zKc3r',
    '9YnfbEaXPaPmoXnKZFmNH8hzcLyjbRf56MQP7oqGpump',
    'DayN9FxpLAeiVrFQnRxwjKq7iVQxTieVGybhyXvSpump',
]

# DCA Dynamic Allocation settings
USE_DYNAMIC_ALLOCATION = False
TAKE_PROFIT_PERCENTAGE = 206
FIXED_DCA_AMOUNT = 14

# DCA & Staking settings
STAKING_ALLOCATION_PERCENTAGE = 35
DCA_INTERVAL_MINUTES = 30240
DCA_INTERVAL_UNIT = "Day(s)"
DCA_INTERVAL_VALUE = 21
DCA_RUN_AT_ENABLED = False
DCA_RUN_AT_TIME = "12:00"

# Add these
STAKING_PROTOCOLS = ["marinade", "jito"]
MAX_SLASHING_RISK = 0.5  # Max acceptable slashing risk %
VALIDATOR_PERFORMANCE_THRESHOLD = 99  # Minimum validator uptime %

# Add Jupiter API settings
JUPITER_API_URL = "https://quote-api.jup.ag/v6"
JUPITER_FEE_ACCOUNT = "FG4Y3yX4AAchp1HvNZ7LfzFTewF2f6nDoMDCohTFrdpT"  # For referral fees

# Add these staking configuration options
STAKING_MODE = 'auto_convert'
AUTO_CONVERT_THRESHOLD = 13
MIN_CONVERSION_AMOUNT = 5
MAX_CONVERT_PERCENTAGE = 25

# Add these in the DCA & Staking settings section of config.py, after YIELD_OPTIMIZATION_INTERVAL
YIELD_OPTIMIZATION_INTERVAL = 28800
YIELD_OPTIMIZATION_INTERVAL_UNIT = "Hour(s)"
YIELD_OPTIMIZATION_INTERVAL_VALUE = 8
YIELD_OPTIMIZATION_RUN_AT_ENABLED = True
YIELD_OPTIMIZATION_RUN_AT_TIME = "13:00"

# Advanced DCA settings
BUY_CONFIDENCE_THRESHOLD = 39
SELL_CONFIDENCE_THRESHOLD = 85
BUY_MULTIPLIER = 1.5  # Buy 50% more than standard amount
MAX_SELL_PERCENTAGE = 25  # Maximum % of holdings to sell (caps at 25%)

MAX_VOLATILITY_THRESHOLD = 0.05  # Maximum volatility threshold for risk-based sizing
TREND_AWARENESS_THRESHOLD = 50  # RSI threshold for trend awareness

# DCA AI Model override settings
DCA_MODEL_OVERRIDE = "deepseek-reasoner"
DCA_DEEPSEEK_BASE_URL = "https://api.deepseek.com"  # Base URL for DeepSeek API if using DeepSeek models
ENABLE_STAKING_AI = True

# Updated DCA & Staking AI Prompt with proper variables
DCA_AI_PROMPT = """
You are Anarcho Capital's Staking Agent, an advanced AI designed to analyze staking opportunities and optimize yield on the Solana blockchain.

Given the following data:
{token_list}
{staking_rewards}
{apy_data}
{market_conditions}

Provide staking and yield optimization advice following these guidelines:
1. Recommend the best staking protocol based on current APY
2. Advise on optimal allocation between staking protocols
3. Suggest if token conversion to SOL for staking is beneficial
4. Provide compound frequency recommendations 
5. Analyze risk/reward for different staking options

Your response must include:
- PROTOCOL: [protocol name]
- ALLOCATION: [percentage allocation recommendation]
- CONVERT: [YES/NO]
- COMPOUND: [frequency recommendation]
- REASONING: [brief explanation]

Current staking protocols: marinade, lido, jito
"""

# Chart Analysis Agent Settings 📊
CHART_ANALYSIS_INTERVAL_MINUTES = 180  # Renamed from CHECK_INTERVAL_MINUTES and changed default value
CHART_INTERVAL_UNIT = "Hour(s)"
CHART_INTERVAL_VALUE = 6
CHART_RUN_AT_ENABLED = True
CHART_RUN_AT_TIME = "12:00"
TIMEFRAMES = ['1d']
LOOKBACK_BARS = 104
CHART_INDICATORS = ['20EMA', '50EMA', '100EMA', '200SMA', 'MACD', 'RSI', 'ATR']#20EMA,50EMA,100EMA,200SMA,MACD,RSI,ATR
CHART_STYLE = 'yahoo'
CHART_VOLUME_PANEL = True

# Fibonacci retracement settings
ENABLE_FIBONACCI = True
FIBONACCI_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]
FIBONACCI_LOOKBACK_PERIODS = 60 # How far back to look for swing high/low points for Fibonacci calculation

# Chart Analysis AI Settings
CHART_MODEL_OVERRIDE = "deepseek-reasoner"
CHART_DEEPSEEK_BASE_URL = "https://api.deepseek.com"  # Base URL for DeepSeek API
ENABLE_CHART_ANALYSIS = True

# Voice Announcement Settings for Chart Agent
VOICE_MODEL = "tts-1"  # OpenAI TTS model
VOICE_NAME = "shimmer"  # Options: alloy, echo, fable, onyx, nova, shimmer
VOICE_SPEED = 1.0  # Speed of speech (1.0 = normal)

# Chart Analysis AI Prompt
CHART_ANALYSIS_PROMPT = """
You must respond in exactly 4 lines:
Line 1: Only write BUY, SELL, or NOTHING
Line 2: One short reason why
Line 3: Only write "Confidence: X%" where X is 0-100
Line 4: Calculate the optimal entry price level based on indicators

Analyze the chart data for {symbol} {timeframe}:

{chart_data}

Remember:
- Look for confluence between multiple indicators
- Volume should confirm price action
- Consider the timeframe context - longer timeframes (4h, 1d, 1w) are better for DCA/staking strategies
- For longer timeframes, focus on major trend direction and ignore short-term noise
- Higher confidence is needed for longer timeframe signals
- If a previous recommendation is provided, consider:
  * How the price moved after that recommendation
  * Whether the signal should be maintained or changed based on new data
  * If a previous entry price was accurate, use it to improve your estimate
  * Signal consistency is valuable - avoid flip-flopping between BUY/SELL without clear reason

For optimal entry price calculation:
- For BUY: Look for support levels (EMAs, recent lows) and adjust using ATR
- For SELL: Look for resistance levels (EMAs, recent highs) and adjust using ATR
- If indicators are limited, use price action and volatility to establish entry zones
- Provide a specific price number, not a range
- If previous entry recommendations were successful, consider similar levels

Make your own independent assessment but factor in the performance of previous recommendations.
"""


# Future variables (not active yet) 🔮
sell_at_multiple = 3
USDC_SIZE = 1
limit = 49
timeframe = '15m'
stop_loss_perctentage = -.24
EXIT_ALL_POSITIONS = False
DO_NOT_TRADE_LIST = ['777']
CLOSED_POSITIONS_TXT = '777'
minimum_trades_in_last_hour = 777

priority_fee = 100006
