"""
🌙 Moon Dev's Configuration File
Built with love by Moon Dev 🚀
"""


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

#CopyBot Settings
FILTER_MODE = "Dynamic"
PERCENTAGE_THRESHOLD = 0.1
AMOUNT_THRESHOLD = 5000
ENABLE_PERCENTAGE_FILTER = False
ENABLE_AMOUNT_FILTER = False
ENABLE_ACTIVITY_FILTER = False
ACTIVITY_WINDOW_HOURS = 1

# API and Network Settings 🌐
API_SLEEP_SECONDS = 1.0
API_TIMEOUT_SECONDS = 30
API_MAX_RETRIES = 5

# List of wallets to track for CopyBot - Must be in the correct format
WALLETS_TO_TRACK = WALLETS_TO_TRACK = [
    "FXzJ6xwH2HfdKshERVAYiLh79PAUw9zC7ucngupt91ap",
    "242p259rfsb9J3X3mhnWw35UM2hfMDg14G47CQ66s9ZW",
    # Add more wallets here as needed
]

# CopyBot Portfolio Analysis Prompt - The AI prompt template for analysis
PORTFOLIO_ANALYSIS_PROMPT = """

You are Moon Dev's CopyBot Agent 🌙

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

# Model override settings for CopyBot
COPYBOT_MODEL_OVERRIDE = "deepseek-reasoner"

# CopyBot AI Configuration 
COPYBOT_MIN_CONFIDENCE = 80  # Minimum confidence percentage needed to execute trades (0-100)

# Risk Agent AI Configuration
RISK_MODEL_OVERRIDE = "0"  # "0" uses default, or: "deepseek-chat", "deepseek-reasoner", "gpt-4"
RISK_DEEPSEEK_BASE_URL = "https://api.deepseek.com"  # Base URL for DeepSeek API
RISK_CHECK_INTERVAL_MINUTES = 10
RISK_LOSS_CONFIDENCE_THRESHOLD = 90  # Minimum confidence to override max loss limits (0-100)
RISK_GAIN_CONFIDENCE_THRESHOLD = 60  # Minimum confidence to override max gain limits (0-100)

# 🛡️ Risk Override Prompt - The Secret Sauce!
RISK_OVERRIDE_PROMPT = """

You are Moon Dev's Risk Management Agent 🌙

Your task is to analyze the positions and determine if any should be closed based on the risk management parameters.

Data provided:
1. Current positions and their performance (profit/loss)
2. Risk management parameters (max loss, max gain, etc.)
3. Market data for each position

Analysis Criteria:
1. Has the position hit max loss threshold?
2. Has the position hit max gain threshold?
3. Is the position showing weakness/strength?
4. What is the overall market condition?

{position_data}
{market_data}
{risk_parameters}

Respond in this exact format:
1. First line must be one of: CLOSE, HOLD, or URGENT (in caps)
2. Then explain your reasoning, including:
   - Position performance analysis
   - Risk assessment
   - Market conditions
   - Risk management rule violations
   - Confidence level (as a percentage, e.g. 75%)

Remember: 
- Always prioritize risk management over potential gains
- Be conservative in volatile markets
- Consider both absolute and percentage-based thresholds
- Provide clear, actionable advice

"""

# Specific tokens for DCA Agent
TOKEN_MAP = TOKEN_MAP = {
    '9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump': ('FART', 'FARTCOIN'),
    'HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC': ('AI16Z', 'AI16Z'),
    'So11111111111111111111111111111111111111112': ('SOL', 'SOL'),
}

DCA_MONITORED_TOKENS = list(TOKEN_MAP.keys())

# DCA & Staking settings
STAKING_ALLOCATION_PERCENTAGE = 30
DCA_INTERVAL_MINUTES = 720
TAKE_PROFIT_PERCENTAGE = 200
FIXED_DCA_AMOUNT = 10
MAX_VOLATILITY_THRESHOLD = 0.05  # Maximum volatility threshold for risk-based sizing
TREND_AWARENESS_THRESHOLD = 50  # RSI threshold for trend awareness
YIELD_OPTIMIZATION_INTERVAL = 3600  # Run yield optimization every hour (in seconds)

# DCA & Staking AI Prompt
DCA_AI_PROMPT = """
You are Moon Dev Trading Bot, an advanced AI designed to analyze market trends, execute trades, and manage risk on the Solana blockchain. 
Your primary goal is to maximize returns while minimizing risk. You have access to real-time market data, wallet balances, and trading APIs. 
Always prioritize security and never expose sensitive information. Use the following guidelines:
1. Analyze market trends using BirdEye API.
2. Execute trades based on predefined strategies.
3. Monitor wallet balances and adjust positions accordingly.
4. Never share or log private keys or API keys.
5. Report any anomalies or potential security risks immediately.
"""

# Add these
STAKING_PROTOCOLS = ["marinade", "jito"]
MAX_SLASHING_RISK = 0.5  # Max acceptable slashing risk %
VALIDATOR_PERFORMANCE_THRESHOLD = 99  # Minimum validator uptime %

# Add Jupiter API settings
JUPITER_API_URL = "https://quote-api.jup.ag/v6"
JUPITER_FEE_ACCOUNT = "FG4Y3yX4AAchp1HvNZ7LfzFTewF2f6nDoMDCohTFrdpT"  # For referral fees

# Add these staking configuration options
STAKING_MODE = "separate"
AUTO_CONVERT_THRESHOLD = 10
MIN_CONVERSION_AMOUNT = 5
MAX_CONVERT_PERCENTAGE = 25

# Advanced DCA settings
BUY_CONFIDENCE_THRESHOLD = 50
SELL_CONFIDENCE_THRESHOLD = 75
BUY_MULTIPLIER = 1.5  # Buy 50% more than standard amount
MAX_SELL_PERCENTAGE = 25  # Maximum % of holdings to sell (caps at 25%)

# Chart Analysis Agent Settings 📊
CHECK_INTERVAL_MINUTES = 10
TIMEFRAMES = ['4h', '1d']
LOOKBACK_BARS = 100
CHART_INDICATORS = ['20EMA', '50EMA', '100EMA', '200SMA', 'MACD', 'RSI', 'ATR']  # Technical indicators to display
CHART_STYLE = 'charles'  # mplfinance style
CHART_VOLUME_PANEL = True  # Show volume panel

# Chart Analysis AI Settings
CHART_MODEL_OVERRIDE = "deepseek-reasoner"
CHART_DEEPSEEK_BASE_URL = "https://api.deepseek.com"  # Base URL for DeepSeek API

# Voice Announcement Settings for Chart Agent
VOICE_MODEL = "tts-1"  # OpenAI TTS model
VOICE_NAME = "shimmer"  # Options: alloy, echo, fable, onyx, nova, shimmer
VOICE_SPEED = 1.0  # Speed of speech (1.0 = normal)

# Chart Analysis AI Prompt
CHART_ANALYSIS_PROMPT = """
You must respond in exactly 3 lines:
Line 1: Only write BUY, SELL, or NOTHING
Line 2: One short reason why
Line 3: Only write "Confidence: X%" where X is 0-100

Analyze the chart data for {symbol} {timeframe}:

{chart_data}

Remember:
- Look for confluence between multiple indicators
- Volume should confirm price action
- Consider the timeframe context - longer timeframes (4h, 1d, 1w) are better for DCA/staking strategies
- For longer timeframes, focus on major trend direction and ignore short-term noise
- Higher confidence is needed for longer timeframe signals
"""

# 💰 Trading Configuration
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # Never trade or close
SOL_ADDRESS = "So11111111111111111111111111111111111111111"   # Never trade or close

# Create a list of addresses to exclude from trading/closing
EXCLUDED_TOKENS = [USDC_ADDRESS, SOL_ADDRESS, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111']

# Token and wallet settings
symbol = '9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump'  # input ticker symbol (FART) here for main token to focus on
address = '4wgfCBf2WwLSRKLef9iW7JXZ2AfkxUxGM4XcKpHm3Sin' # YOUR WALLET ADDRESS HERE

# Position sizing 🎯
usd_size = 25.0# account_balance * 0.085 or 0.12: Size of position to hold
max_usd_order_size = 3.0# Max order size
tx_sleep = 15.0# Sleep between transactions
slippage = 199# Slippage settings

# Paper Trading Settings 📝
PAPER_TRADING_ENABLED = False# Toggle paper trading mode on/off
PAPER_INITIAL_BALANCE = 1000.0# Initial paper trading balance in USD
PAPER_TRADING_SLIPPAGE = 100# Simulated slippage for paper trades (100 = 1%)
PAPER_TRADING_RESET_ON_START = False# Whether to reset paper portfolio on app start

# Risk Management Settings 🛡️
CASH_PERCENTAGE = 20# Minimum % to keep in USDC as safety buffer (0-100)
MAX_POSITION_PERCENTAGE = 10# Maximum % allocation per position (0-100)
STOPLOSS_PRICE = 2 # NOT USED YET 1/5/25    
BREAKOUT_PRICE = .0002 # NOT USED YET 1/5/25
SLEEP_AFTER_CLOSE = 900# Prevent overtrading

MAX_LOSS_GAIN_CHECK_HOURS = 24# How far back to check for max loss/gain limits (in hours)
SLEEP_BETWEEN_RUNS_MINUTES = 10  # How long to sleep between agent runs 🕒

# Max Loss/Gain Settings FOR RISK AGENT 1/5/25
USE_PERCENTAGE = True# If True, use percentage-based limits. If False, use USD-based limits

# USD-based limits (used if USE_PERCENTAGE is False)
MAX_LOSS_USD = 25.0# Maximum loss in USD before stopping trading
MAX_GAIN_USD = 25.0# Maximum gain in USD before stopping trading

# USD MINIMUM BALANCE RISK CONTROL
MINIMUM_BALANCE_USD = 100.0# account_balance * (1/3): If balance falls below this, risk agent will consider closing all positions
USE_AI_CONFIRMATION = True

# Percentage-based limits (used if USE_PERCENTAGE is True)
MAX_LOSS_PERCENT = 20# Maximum loss as percentage (e.g., 20 = 20% loss)
MAX_GAIN_PERCENT = 200# Maximum gain as percentage (e.g., 50 = 50% gain)

# Agent Runtime Settings ⏱️
RISK_INTERVAL_MINUTES = RISK_CHECK_INTERVAL_MINUTES  # How often Risk Agent checks portfolio (in minutes)
COPYBOT_INTERVAL_MINUTES = 30
SLEEP_BETWEEN_RUNS_MINUTES = 15  # General sleep time between agent runs 🕒

# Transaction settings ⚡
slippage = 199# 500 = 5% and 50 = .5% slippage
PRIORITY_FEE = 100000# ~0.02 USD at current SOL prices
orders_per_open = 3# Multiple orders for better fill rates

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

# Global AI Model Settings (used as fallbacks)
AI_MODEL = "claude-3-haiku-20240307"
AI_TEMPERATURE = 0.7
AI_MAX_TOKENS = 1024
DAYSBACK_4_DATA = 3
DATA_TIMEFRAME = '15m'