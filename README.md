# AI Trading Desktop Application

A sophisticated desktop application for automated cryptocurrency trading with a cyberpunk-themed UI. This application provides real-time wallet tracking, trading agent automation, and portfolio management for cryptocurrency traders.

![Trading Desktop App](https://via.placeholder.com/800x450?text=AI+Trading+Desktop+App+Screenshot)

## Features

- 🤖 **AI-Powered Trading Agents**: Multiple automated trading strategies
  - Copy Trading Agent - Mirror trades from tracked wallets
  - Risk Management Agent - Apply trading rules and portfolio rebalancing
  - DCA/Staking Agent - Dollar-cost averaging and staking automation
  - Chart Analysis Agent - Technical analysis for trading decisions

- 📈 **Portfolio Management**:
  - Real-time portfolio visualization
  - PnL tracking and performance metrics
  - Risk management and position sizing

- 🔍 **Wallet Tracking**:
  - Track multiple wallet addresses
  - Real-time token balance updates
  - Change detection and transaction monitoring

- 📊 **Data Analysis**:
  - Token price monitoring
  - Performance analytics
  - Historical data tracking

- 📱 **Modern Cyberpunk UI**:
  - Sleek, neon-themed interface
  - Real-time dashboards
  - Agent status monitoring

## System Requirements

- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended)
- Windows 10/11, macOS, or Linux
- Internet connection

## Installation

### Option 1: Run from Source

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/trading_desktop_app.git
   cd trading_desktop_app
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python run.py
   ```

### Option 2: Build Executable

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/trading_desktop_app.git
   cd trading_desktop_app
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the build script:
   ```bash
   python build.py
   ```

4. The executable will be created in the `dist/AI_Trading_System` directory

## Configuration

The application uses several configuration files:

1. `.env` - Environment variables and API keys
   - Copy `.env.example` to `.env` and add your API keys
   - Required for wallet tracking and exchange integrations

2. `src/config.py` - Application settings
   - Controls trading behavior and risk parameters
   - Agent-specific configurations

## Trading Agents

### Copy Trading Agent
Monitors specified wallets and mirrors their trading activity based on configurable filters.

### Risk Management Agent
Applies risk management rules to your portfolio, including stop-loss, take-profit, and position sizing.

### DCA/Staking Agent
Automates dollar-cost averaging strategies and token staking operations.

### Chart Analysis Agent
Performs technical analysis on token charts to generate trading signals.

## Usage

1. Start the application
2. Configure your wallet addresses and API keys
3. Set up your preferred trading agents
4. Monitor your portfolio and agent activities

## Paper Trading Mode

The application offers a paper trading mode for testing strategies without risking real assets:

1. Enable paper trading in the Risk Management tab
2. Set your virtual portfolio balance
3. Test strategies in a simulated environment

## Development

### Project Structure

- `run.py` - Main application entry point
- `src/` - Core functionality and modules
  - `agents/` - Trading agent implementations
  - `scripts/` - Utility scripts
  - `models/` - Data models
  - `frontend/` - UI components
- `data/` - Data storage and cache

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Use at your own risk. Cryptocurrency trading involves significant risk and can result in the loss of your invested capital. The creators of this application are not responsible for any financial losses incurred through its use.
