# 🛡️ Enhanced Risk Agent Documentation

## Overview
The Risk Agent monitors your token positions and manages risk based on your configuration settings. The agent will track PnL limits, minimum balance requirements, and can automatically close positions when necessary.

## Token Monitoring
The enhanced Risk Agent now comprehensively monitors tokens from **multiple sources**:

1. **MONITORED_TOKENS list** - Primary token watchlist defined in config.py
2. **DCA_MONITORED_TOKENS** - Tokens configured for Dollar Cost Averaging
3. **TOKEN_MAP entries** - Any tokens set up for mapping
4. **Hyperliquid trading pairs** - When USE_HYPERLIQUID is enabled
5. **Dynamic wallet monitoring** - All tokens in your wallet when DYNAMIC_MODE is enabled

## Key Features

### Comprehensive Monitoring
- Tracks token positions across all configured sources
- Respects DYNAMIC_MODE vs MONITORED_TOKENS settings
- Excludes tokens in the EXCLUDED_TOKENS list (typically USDC and SOL)

### Risk Management
- Monitors for maximum loss/gain limits (percentage or USD-based)
- Enforces minimum balance requirements
- Optional AI consultation before closing positions

### PnL Tracking
- Calculates profit and loss across all monitored positions
- Logs portfolio balance for tracking over time

## Configuration Options
Key settings in config.py that affect the Risk Agent:

```python
# Risk Management Settings
CASH_PERCENTAGE = 20  # Minimum % to keep in USDC
MAX_POSITION_PERCENTAGE = 10  # Maximum % allocation per position

# Max Loss/Gain Settings
USE_PERCENTAGE = True  # Use percentage-based or USD-based limits
MAX_LOSS_PERCENT = 20  # Maximum loss as percentage
MAX_GAIN_PERCENT = 200  # Maximum gain as percentage
MAX_LOSS_USD = 25  # Maximum loss in USD
MAX_GAIN_USD = 25  # Maximum gain in USD

# Minimum Balance Risk Control
MINIMUM_BALANCE_USD = 100  # Minimum account balance threshold
USE_AI_CONFIRMATION = True  # Consult AI before closing positions

# Mode Settings
DYNAMIC_MODE = True  # Monitor all wallet tokens vs only MONITORED_TOKENS
```

## How Token Monitoring Works
The agent creates a comprehensive set of tokens to monitor by:

1. Starting with base MONITORED_TOKENS list
2. Adding all DCA_MONITORED_TOKENS
3. Including all tokens from TOKEN_MAP
4. Adding tokens from hyperliquid mapping when enabled
5. In DYNAMIC_MODE, adding all tokens found in your wallet

This ensures the Risk Agent is monitoring your entire portfolio regardless of which agent created the positions.

## AI Consultation
When USE_AI_CONFIRMATION is enabled, the agent will:

1. Detect when a risk limit is breached
2. Present the scenario to an AI model (Claude or DeepSeek)
3. Get a recommendation on whether to close positions
4. Execute based on the AI's decision

This prevents premature closing of positions during temporary market fluctuations. 