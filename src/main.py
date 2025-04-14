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
from importlib import reload
init()

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Import config module
from src import config

# Now we can import from the src module correctly
from src.config import *

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

def get_agent_interval(agent_name):
    """Get the interval for an agent from config.py, ensuring fresh values"""
    # Reload config to get the most up-to-date values
    reload(config)
    
    if agent_name == 'risk':
        # Specifically use RISK_CHECK_INTERVAL_MINUTES for the risk agent only
        return config.RISK_CHECK_INTERVAL_MINUTES
    elif agent_name == 'copybot':
        return config.COPYBOT_INTERVAL_MINUTES
    elif agent_name == 'dca_staking':
        return config.DCA_INTERVAL_MINUTES
    elif agent_name == 'chart_analysis':
        # Use CHART_ANALYSIS_INTERVAL_MINUTES for chart analysis
        return config.CHART_ANALYSIS_INTERVAL_MINUTES
    else:
        return 15  # Default fallback

def get_active_agents():
    """Return a dictionary of active agents with their current intervals"""
    return {
        'risk': {
            'active': True,
            'interval': get_agent_interval('risk')
        },
        'copybot': {
            'active': True,
            'interval': get_agent_interval('copybot')
        },
        'dca_staking': {
            'active': True,
            'interval': get_agent_interval('dca_staking')
        },
        'chart_analysis': {
            'active': True,
            'interval': get_agent_interval('chart_analysis')
        }
    }

# Always use the dynamic function to get the latest agent configuration
ACTIVE_AGENTS = get_active_agents()

def should_run_now(agent_name, last_run_time):
    """Determine if an agent should run now based on its scheduling configuration"""
    # Get fresh agent interval configuration
    current_interval = get_agent_interval(agent_name)
    
    if agent_name == 'dca_staking':
        # Check if DCA run_at_time is enabled and it's the right time
        reload(config)  # Reload to get latest values
        run_at_enabled = config.DCA_RUN_AT_ENABLED
        if run_at_enabled:
            run_at_time = config.DCA_RUN_AT_TIME
            now = datetime.now()
            hour, minute = map(int, run_at_time.split(":"))
            scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Run if within 5 minutes of scheduled time
            time_diff = abs((now - scheduled_time).total_seconds())
            if time_diff <= 300:  # 5 minutes
                return True
        else:
            # Check interval from last run
            reload(config)  # Reload to get latest values
            interval_unit = config.DCA_INTERVAL_UNIT
            interval_value = config.DCA_INTERVAL_VALUE
            return is_interval_elapsed(interval_unit, interval_value, last_run_time)
    
    elif agent_name == 'chart_analysis':
        # Check if Chart Analysis run_at_time is enabled and it's the right time
        reload(config)  # Reload to get latest values
        run_at_enabled = config.CHART_RUN_AT_ENABLED
        if run_at_enabled:
            run_at_time = config.CHART_RUN_AT_TIME
            now = datetime.now()
            hour, minute = map(int, run_at_time.split(":"))
            scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Run if within 5 minutes of scheduled time
            time_diff = abs((now - scheduled_time).total_seconds())
            if time_diff <= 300:  # 5 minutes
                return True
        else:
            # Check interval from last run
            reload(config)  # Reload to get latest values
            interval_unit = config.CHART_INTERVAL_UNIT
            interval_value = config.CHART_INTERVAL_VALUE
            return is_interval_elapsed(interval_unit, interval_value, last_run_time)
    
    # Default case for other agents (Risk, CopyBot)
    current_time = datetime.now()
    seconds_since_last_run = (current_time - last_run_time).total_seconds()
    return seconds_since_last_run >= current_interval * 60

def is_interval_elapsed(interval_unit, interval_value, last_run_time):
    """Check if the specified interval has elapsed since the last run time"""
    now = datetime.now()
    elapsed_seconds = (now - last_run_time).total_seconds()
    
    # Convert interval to seconds based on unit
    if interval_unit == "Hour(s)":
        interval_seconds = interval_value * 60 * 60
    elif interval_unit == "Day(s)":
        interval_seconds = interval_value * 24 * 60 * 60
    elif interval_unit == "Week(s)":
        interval_seconds = interval_value * 7 * 24 * 60 * 60
    elif interval_unit == "Month(s)":
        interval_seconds = interval_value * 30 * 24 * 60 * 60  # Approximation
    else:
        # Default to hours if unit is unknown
        interval_seconds = interval_value * 60 * 60
    
    return elapsed_seconds >= interval_seconds

def get_next_run_time(agent_name, last_run_time):
    """Calculate when an agent should next run based on its schedule"""
    reload(config)  # Reload to get latest values
    
    if agent_name == 'dca_staking':
        run_at_enabled = config.DCA_RUN_AT_ENABLED
        if run_at_enabled:
            # Calculate next occurrence of the scheduled time
            run_at_time = config.DCA_RUN_AT_TIME
            now = datetime.now()
            hour, minute = map(int, run_at_time.split(":"))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If the scheduled time has already passed today, move to next occurrence
            if next_run < now:
                interval_unit = config.DCA_INTERVAL_UNIT
                interval_value = config.DCA_INTERVAL_VALUE
                
                if interval_unit == "Hour(s)":
                    next_run = next_run + timedelta(hours=interval_value)
                elif interval_unit == "Day(s)":
                    next_run = next_run + timedelta(days=interval_value)
                elif interval_unit == "Week(s)":
                    next_run = next_run + timedelta(weeks=interval_value)
                elif interval_unit == "Month(s)":
                    # Approximation for months
                    next_run = next_run + timedelta(days=30 * interval_value)
            
            return next_run
        else:
            # Use interval-based calculation
            interval_unit = config.DCA_INTERVAL_UNIT
            interval_value = config.DCA_INTERVAL_VALUE
            return calculate_next_run_from_interval(interval_unit, interval_value, last_run_time)
    
    elif agent_name == 'chart_analysis':
        run_at_enabled = config.CHART_RUN_AT_ENABLED
        if run_at_enabled:
            # Calculate next occurrence of the scheduled time
            run_at_time = config.CHART_RUN_AT_TIME
            now = datetime.now()
            hour, minute = map(int, run_at_time.split(":"))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If the scheduled time has already passed today, move to next occurrence
            if next_run < now:
                interval_unit = config.CHART_INTERVAL_UNIT
                interval_value = config.CHART_INTERVAL_VALUE
                
                if interval_unit == "Hour(s)":
                    next_run = next_run + timedelta(hours=interval_value)
                elif interval_unit == "Day(s)":
                    next_run = next_run + timedelta(days=interval_value)
                elif interval_unit == "Week(s)":
                    next_run = next_run + timedelta(weeks=interval_value)
                elif interval_unit == "Month(s)":
                    # Approximation for months
                    next_run = next_run + timedelta(days=30 * interval_value)
            
            return next_run
        else:
            # Use interval-based calculation
            interval_unit = config.CHART_INTERVAL_UNIT
            interval_value = config.CHART_INTERVAL_VALUE
            return calculate_next_run_from_interval(interval_unit, interval_value, last_run_time)
    
    # Default case for other agents - get fresh interval for risk and copybot
    current_interval = get_agent_interval(agent_name)
    return last_run_time + timedelta(minutes=current_interval)

def calculate_next_run_from_interval(interval_unit, interval_value, last_run_time):
    """Calculate the next run time based on the interval unit and value"""
    if interval_unit == "Hour(s)":
        return last_run_time + timedelta(hours=interval_value)
    elif interval_unit == "Day(s)":
        return last_run_time + timedelta(days=interval_value)
    elif interval_unit == "Week(s)":
        return last_run_time + timedelta(weeks=interval_value)
    elif interval_unit == "Month(s)":
        # Approximate a month as 30 days
        return last_run_time + timedelta(days=30 * interval_value)
    else:
        # Default to hours if unit is unknown
        return last_run_time + timedelta(hours=interval_value)

def run_agents():
    """Run all active agents on their own schedules"""
    try:
        # Always get fresh config values
        reload(config)
        ACTIVE_AGENTS = get_active_agents()
        
        # Initialize active agents
        risk_agent = RiskAgent() if ACTIVE_AGENTS['risk']['active'] else None
        copybot_agent = CopyBotAgent() if ACTIVE_AGENTS['copybot']['active'] else None
        dca_agent = DCAAgent() if ACTIVE_AGENTS['dca_staking']['active'] else None
        chart_agent = ChartAnalysisAgent() if ACTIVE_AGENTS['chart_analysis']['active'] else None
        
        # Initialize last run times to NOW to prevent immediate execution
        current_time = datetime.now()
        last_run = {
            'risk': current_time,
            'copybot': current_time,
            'dca_staking': current_time,
            'chart_analysis': current_time
        }
        
        # Calculate and log the next run time for each agent
        system("Next scheduled run times:")
        for agent, details in ACTIVE_AGENTS.items():
            if details['active']:
                if agent in ['chart_analysis', 'dca_staking']:
                    next_run = get_next_run_time(agent, last_run[agent])
                    time_until = (next_run - current_time).total_seconds() / 60
                    system(f"  • {agent.title()}: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (in {time_until:.1f} minutes)")
                else:
                    # Get fresh interval values
                    current_interval = get_agent_interval(agent)
                    next_run = last_run[agent] + timedelta(minutes=current_interval)
                    time_until = (next_run - current_time).total_seconds() / 60
                    system(f"  • {agent.title()}: {next_run.strftime('%H:%M:%S')} (in {time_until:.1f} minutes)")
        
        # Run agents continuously, each respecting their own interval
        while True:
            try:
                current_time = datetime.now()
                
                # Always reload config at the start of each loop to get fresh values
                reload(config)
                
                # Risk Management - get fresh values from config
                if (risk_agent and 
                    (config.RISK_CONTINUOUS_MODE or  # Run if continuous mode is on
                     (current_time - last_run['risk']).total_seconds() >= get_agent_interval('risk') * 60)):
                    info("Running Risk Management...")
                    risk_agent.run()
                    last_run['risk'] = current_time
                    next_run_time = "Continuous Mode" if config.RISK_CONTINUOUS_MODE else (current_time + timedelta(minutes=get_agent_interval('risk'))).strftime('%H:%M:%S')
                    info(f"Risk Management complete. Next run at: {next_run_time}")
                
                # CopyBot Analysis - get fresh values from config
                if (copybot_agent and 
                    (config.COPYBOT_CONTINUOUS_MODE or  # Run if continuous mode is on
                     (current_time - last_run['copybot']).total_seconds() >= get_agent_interval('copybot') * 60)):
                    info("Running CopyBot Portfolio Analysis...")
                    copybot_agent.run_analysis_cycle()
                    last_run['copybot'] = current_time
                    next_run_str = "Continuous Mode" if config.COPYBOT_CONTINUOUS_MODE else (current_time + timedelta(minutes=get_agent_interval('copybot'))).strftime('%H:%M:%S')
                    info(f"CopyBot Analysis complete. Next run at: {next_run_str}")
                
                # Chart Analysis
                if chart_agent and should_run_now('chart_analysis', last_run['chart_analysis']):
                    info("Running Chart Analysis...")
                    chart_agent.run_monitoring_cycle()  # Run a single cycle, not continuous
                    last_run['chart_analysis'] = current_time
                    next_run = get_next_run_time('chart_analysis', current_time)
                    next_run_time = next_run.strftime('%Y-%m-%d %H:%M:%S')
                    info(f"Chart Analysis complete. Next run at: {next_run_time}")

                # DCA & Staking
                if dca_agent and should_run_now('dca_staking', last_run['dca_staking']):
                    info("Running DCA & Staking Analysis...")
                    dca_agent.run_dca_cycle()  # Run a single cycle, not continuous
                    last_run['dca_staking'] = current_time
                    next_run = get_next_run_time('dca_staking', current_time)
                    next_run_time = next_run.strftime('%Y-%m-%d %H:%M:%S')
                    info(f"DCA & Staking complete. Next run at: {next_run_time}")
                
                # Sleep for 1 minute before checking intervals again
                time.sleep(60)
                
                # Print a heartbeat every 5 minutes
                if current_time.minute % 5 == 0 and current_time.second < 2:
                    info("System heartbeat - All agents running on schedule")
                    info("Next agent runs:")
                    for agent in ['risk', 'copybot', 'dca_staking', 'chart_analysis']:
                        if agent in ['chart_analysis', 'dca_staking']:
                            next_run = get_next_run_time(agent, last_run[agent])
                            time_until = (next_run - current_time).total_seconds() / 60
                            info(f"  • {agent.title()}: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (in {time_until:.1f} minutes)")
                        else:
                            current_interval = get_agent_interval(agent)
                            next_run = last_run[agent] + timedelta(minutes=current_interval)
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
    # Always get fresh config values
    reload(config)
    ACTIVE_AGENTS = get_active_agents()
    
    system("Active Agents and their Intervals:")
    for agent in ['risk', 'copybot', 'dca_staking', 'chart_analysis']:
        status = "ON"  # All agents are active by default
        
        if agent == 'dca_staking':
            run_at_enabled = config.DCA_RUN_AT_ENABLED
            if run_at_enabled:
                run_at_time = config.DCA_RUN_AT_TIME
                interval_unit = config.DCA_INTERVAL_UNIT
                interval_value = config.DCA_INTERVAL_VALUE
                interval_str = f"At {run_at_time} every {interval_value} {interval_unit}"
            else:
                interval_unit = config.DCA_INTERVAL_UNIT
                interval_value = config.DCA_INTERVAL_VALUE
                interval_str = f"Every {interval_value} {interval_unit}"
        
        elif agent == 'chart_analysis':
            run_at_enabled = config.CHART_RUN_AT_ENABLED
            if run_at_enabled:
                run_at_time = config.CHART_RUN_AT_TIME
                interval_unit = config.CHART_INTERVAL_UNIT
                interval_value = config.CHART_INTERVAL_VALUE
                interval_str = f"At {run_at_time} every {interval_value} {interval_unit}"
            else:
                interval_unit = config.CHART_INTERVAL_UNIT
                interval_value = config.CHART_INTERVAL_VALUE
                interval_str = f"Every {interval_value} {interval_unit}"
        
        else:
            # For risk and copybot, use the latest values from config
            interval = get_agent_interval(agent)
            interval_str = f"{interval} minutes"
            if interval >= 60:
                hours = interval // 60
                minutes = interval % 60
                interval_str = f"{hours} hour{'s' if hours > 1 else ''}"
                if minutes > 0:
                    interval_str += f" {minutes} minute{'s' if minutes > 1 else ''}"
        
        system(f"  • {agent.title()}: {status} ({interval_str})")

    run_agents()