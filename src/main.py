"""
Moon Dev's AI Trading System
Main entry point for running trading agents

Staking Configuration:
- SOL staking is controlled by the STAKING_MODE option in config.py
- "separate" mode (default): Only stakes SOL already in your wallet
- "auto_convert" mode: Can automatically sell some tokens to maintain SOL staking allocation
- Staking rewards are automatically reinvested
"""

import os
import sys
from termcolor import cprint
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
from colorama import init, Fore, Back, Style 
from src.scripts.logger import debug, info, warning, error, critical, system
import threading
init()

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Now we can import from the src module correctly
from src.config import *
from src.config import RISK_CONTINUOUS_MODE, COPYBOT_CONTINUOUS_MODE

# Load environment variables
load_dotenv()

# Debugging: Log API key (but not showing the full key for security)
api_key = os.getenv("BIRDEYE_API_KEY")
if api_key:
    masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "***"
    debug(f"Birdeye API Key loaded: {masked_key}", file_only=True)
else:
    warning("Birdeye API Key not found in environment variables")

# Import agents
from src.agents.risk_agent import RiskAgent
from src.agents.copybot_agent import CopyBotAgent
from src.agents.dca_staking_agent import DCAAgent
from src.agents.chartanalysis_agent import ChartAnalysisAgent

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # This tells TensorFlow to be quiet!
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # This stops the "oneDNN" messages.

# Agent Configuration with their intervals in minutes
ACTIVE_AGENTS = {
    'risk': {
        'active': True,      # Risk management agent
        'interval': RISK_CHECK_INTERVAL_MINUTES      # in minutes
    },
    'copybot': {
        'active': True,      # CopyBot agent
        'interval': COPYBOT_INTERVAL_MINUTES  # From config.py (defaults to 5 minutes)
    },
    'dca_staking': {
        'active': True,      # DCA & Staking agent
        'interval': DCA_INTERVAL_MINUTES  # From config.py (defaults to 720 minutes)
    },
    'chart_analysis': {
        'active': True,      # Chart Analysis agent
        'interval': CHECK_INTERVAL_MINUTES  # From config.py (defaults to 10 minutes)
    }
}

def run_agents():
    """Run all active agents on their own schedules"""
    try:
        # Initialize active agents
        risk_agent = RiskAgent() if ACTIVE_AGENTS['risk']['active'] else None
        copybot_agent = CopyBotAgent() if ACTIVE_AGENTS['copybot']['active'] else None
        dca_agent = DCAAgent() if ACTIVE_AGENTS['dca_staking']['active'] else None
        chart_agent = ChartAnalysisAgent() if ACTIVE_AGENTS['chart_analysis']['active'] else None
        
        # Track last run time for each agent
        last_run = {
            'risk': datetime.now() - timedelta(minutes=ACTIVE_AGENTS['risk']['interval']),
            'copybot': datetime.now() - timedelta(minutes=ACTIVE_AGENTS['copybot']['interval']),
            'dca_staking': datetime.now() - timedelta(minutes=ACTIVE_AGENTS['dca_staking']['interval']),
            'chart_analysis': datetime.now() - timedelta(minutes=ACTIVE_AGENTS['chart_analysis']['interval'])
        }
        
        # Run agents continuously, each respecting their own interval
        while True:
            try:
                current_time = datetime.now()
                
                # Risk Management
                if (risk_agent and 
                    (RISK_CONTINUOUS_MODE or  # Run if continuous mode is on
                     (current_time - last_run['risk']).total_seconds() >= ACTIVE_AGENTS['risk']['interval'] * 60)):
                    info("Running Risk Management...")
                    risk_agent.run()
                    last_run['risk'] = current_time
                    next_run_time = "Continuous Mode" if RISK_CONTINUOUS_MODE else (current_time + timedelta(minutes=ACTIVE_AGENTS['risk']['interval'])).strftime('%H:%M:%S')
                    info(f"Risk Management complete. Next run at: {next_run_time}")
                
                # CopyBot Analysis
                if (copybot_agent and 
                    (COPYBOT_CONTINUOUS_MODE or  # Run if continuous mode is on
                     (current_time - last_run['copybot']).total_seconds() >= ACTIVE_AGENTS['copybot']['interval'] * 60)):  # Or if interval elapsed
                    info("Running CopyBot Portfolio Analysis...")
                    copybot_agent.run_analysis_cycle()
                    last_run['copybot'] = current_time
                    next_run_str = "Continuous Mode" if COPYBOT_CONTINUOUS_MODE else (current_time + timedelta(minutes=ACTIVE_AGENTS['copybot']['interval'])).strftime('%H:%M:%S')
                    info(f"CopyBot Analysis complete. Next run at: {next_run_str}")
                
                # Chart Analysis
                if (chart_agent and 
                    (current_time - last_run['chart_analysis']).total_seconds() >= ACTIVE_AGENTS['chart_analysis']['interval'] * 60):
                    info("Running Chart Analysis...")
                    chart_agent.run_monitoring_cycle()  # Run a single cycle, not continuous
                    last_run['chart_analysis'] = current_time
                    next_run_time = (current_time + timedelta(minutes=ACTIVE_AGENTS['chart_analysis']['interval'])).strftime('%H:%M:%S')
                    info(f"Chart Analysis complete. Next run at: {next_run_time}")

                # DCA & Staking
                if (dca_agent and 
                    (current_time - last_run['dca_staking']).total_seconds() >= ACTIVE_AGENTS['dca_staking']['interval'] * 60):
                    info("Running DCA & Staking Analysis...")
                    dca_agent.run_dca_cycle()  # Run a single cycle, not continuous
                    last_run['dca_staking'] = current_time
                    next_run_time = (current_time + timedelta(minutes=ACTIVE_AGENTS['dca_staking']['interval'])).strftime('%H:%M:%S')
                    info(f"DCA & Staking complete. Next run at: {next_run_time}")
                
                # Sleep for 1 minute before checking intervals again
                time.sleep(60)
                
                # Print a heartbeat every 5 minutes
                if current_time.minute % 5 == 0 and current_time.second < 2:
                    info("System heartbeat - All agents running on schedule")
                    info("Next agent runs:")
                    for agent, details in ACTIVE_AGENTS.items():
                        if details['active']:
                            next_run = last_run[agent] + timedelta(minutes=details['interval'])
                            time_until = (next_run - current_time).total_seconds() / 60
                            info(f"  • {agent.title()}: {next_run.strftime('%H:%M:%S')} (in {time_until:.1f} minutes)")

            except Exception as e:
                error(f"Error running agents: {str(e)}")
                info("Continuing to next cycle...")
                time.sleep(60)  # Sleep for 1 minute on error before retrying

    except KeyboardInterrupt:
        info("Gracefully shutting down...")
    except Exception as e:
        critical(f"Fatal error in main loop: {str(e)}")
        raise

if __name__ == "__main__":
    system("Moon Dev AI Agent Trading System Starting...")
    system("Active Agents and their Intervals:")
    for agent, details in ACTIVE_AGENTS.items():
        status = "ON" if details['active'] else "OFF"
        interval = details['interval']
        interval_str = f"{interval} minutes"
        if interval >= 60:
            hours = interval // 60
            minutes = interval % 60
            interval_str = f"{hours} hour{'s' if hours > 1 else ''}"
            if minutes > 0:
                interval_str += f" {minutes} minute{'s' if minutes > 1 else ''}"
        
        system(f"  • {agent.title()}: {status} (Every {interval_str})")

    run_agents()