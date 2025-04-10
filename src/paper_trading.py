"""
Moon Dev's Paper Trading Module
Provides a wrapper around trading functions for paper trading
"""

import os
import json
import time
import pandas as pd
from datetime import datetime
import sqlite3
from pathlib import Path
from src.scripts.logger import debug, info, warning, error, critical

# Import configuration and original functions
from src.config import (
    PAPER_TRADING_ENABLED, 
    PAPER_INITIAL_BALANCE, 
    PAPER_TRADING_SLIPPAGE,
    PAPER_TRADING_RESET_ON_START
)
import src.nice_funcs as real_trading

# Create data directory if it doesn't exist
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(data_dir, exist_ok=True)

# SQLite database for paper trading
DB_PATH = os.path.join(data_dir, 'paper_trading.db')

# Initialize paper trading database
def init_db():
    """Initialize the paper trading database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS paper_balance (
        token_address TEXT PRIMARY KEY,
        token_symbol TEXT,
        amount REAL,
        last_updated TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS paper_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP,
        token_address TEXT,
        token_symbol TEXT,
        action TEXT,
        amount REAL,
        price REAL,
        usd_value REAL,
        tx_id TEXT
    )
    ''')
    
    # Initialize USDC balance if not exists
    cursor.execute('''
    INSERT OR IGNORE INTO paper_balance (token_address, token_symbol, amount, last_updated)
    VALUES (?, ?, ?, ?)
    ''', ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "USDC", PAPER_INITIAL_BALANCE, datetime.now()))
    
    conn.commit()
    conn.close()

# Reset paper trading (clear all data and reset to initial state)
def reset_paper_trading():
    """Reset paper trading to initial state"""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    info("Paper trading reset to initial state")

# Initialize DB if needed or reset if configured
if not os.path.exists(DB_PATH) or PAPER_TRADING_RESET_ON_START:
    reset_paper_trading()
else:
    init_db()  # Make sure tables exist

# Paper trading wrappers
def get_token_balance(token_address):
    """Paper trading wrapper for get_token_balance"""
    if not PAPER_TRADING_ENABLED:
        return real_trading.get_token_balance(token_address)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT amount FROM paper_balance WHERE token_address = ?", (token_address,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return 0
    except Exception as e:
        error(f"Error in paper trading get_token_balance: {str(e)}")
        return 0

def get_token_balance_usd(token_address):
    """Paper trading wrapper for get_token_balance_usd"""
    if not PAPER_TRADING_ENABLED:
        return real_trading.get_token_balance_usd(token_address)
    
    try:
        balance = get_token_balance(token_address)
        if balance <= 0:
            return 0
            
        # Get token price (use real price data)
        price = real_trading.token_price(token_address)
        if price is None:
            return 0
            
        # Calculate USD value
        usd_value = balance * price
        return usd_value
    except Exception as e:
        error(f"Error in paper trading get_token_balance_usd: {str(e)}")
        return 0

def market_buy(token, amount, slippage):
    """Paper trading wrapper for market_buy"""
    if not PAPER_TRADING_ENABLED:
        return real_trading.market_buy(token, amount, slippage)
    
    try:
        info(f"PAPER TRADING: Executing market buy for {token}")
        
        # Convert amount from USDC lamports to actual USDC
        usdc_amount = float(amount) / 1_000_000  # USDC has 6 decimals
        
        # Check if we have enough USDC balance
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get USDC balance
        cursor.execute("SELECT amount FROM paper_balance WHERE token_address = ?", 
                      ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",))
        usdc_balance = cursor.fetchone()
        
        if not usdc_balance or usdc_balance[0] < usdc_amount:
            warning(f"PAPER TRADING: Insufficient USDC balance for buy")
            conn.close()
            return None
        
        # Get token price
        token_price = real_trading.token_price(token)
        if token_price is None:
            warning(f"PAPER TRADING: Could not get token price")
            conn.close()
            return None
        
        # Apply simulated slippage
        adjusted_price = token_price * (1 + (PAPER_TRADING_SLIPPAGE / 10000))
        
        # Calculate token amount with slippage
        token_amount = usdc_amount / adjusted_price
        
        # Update USDC balance
        cursor.execute("UPDATE paper_balance SET amount = amount - ?, last_updated = ? WHERE token_address = ?", 
                      (usdc_amount, datetime.now(), "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"))
        
        # Update or insert token balance
        cursor.execute("SELECT amount FROM paper_balance WHERE token_address = ?", (token,))
        token_balance = cursor.fetchone()
        
        if token_balance:
            cursor.execute("UPDATE paper_balance SET amount = amount + ?, last_updated = ? WHERE token_address = ?", 
                          (token_amount, datetime.now(), token))
        else:
            # Get symbol if available
            token_symbol = "Unknown"
            for addr, details in real_trading.TOKEN_MAP.items():
                if addr == token:
                    token_symbol = details[0]
                    break
            
            cursor.execute("INSERT INTO paper_balance (token_address, token_symbol, amount, last_updated) VALUES (?, ?, ?, ?)", 
                          (token, token_symbol, token_amount, datetime.now()))
        
        # Generate fake transaction ID
        tx_id = f"paper_tx_{int(time.time())}_{token[:8]}"
        
        # Record transaction
        cursor.execute('''
        INSERT INTO paper_transactions 
        (timestamp, token_address, token_symbol, action, amount, price, usd_value, tx_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now(), token, token_symbol if 'token_symbol' in locals() else "Unknown", 
              "BUY", token_amount, adjusted_price, usdc_amount, tx_id))
        
        conn.commit()
        conn.close()
        
        info(f"PAPER TRADING: Buy executed - {token_amount:.4f} tokens at ${adjusted_price:.6f}")
        debug(f"PAPER TRADING TX: {tx_id}")
        
        return tx_id
    except Exception as e:
        error(f"Error in paper trading market_buy: {str(e)}")
        return None

def market_sell(token, amount, slippage):
    """Paper trading wrapper for market_sell"""
    if not PAPER_TRADING_ENABLED:
        return real_trading.market_sell(token, amount, slippage)
    
    try:
        info(f"PAPER TRADING: Executing market sell for {token}")
        
        # Get token decimals to convert amount from lamports to actual tokens
        decimals = real_trading.get_decimals(token)
        token_amount = float(amount) / (10 ** decimals)
        
        # Check if we have enough token balance
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get token balance and symbol
        cursor.execute("SELECT amount, token_symbol FROM paper_balance WHERE token_address = ?", (token,))
        token_data = cursor.fetchone()
        
        if not token_data or token_data[0] < token_amount:
            warning(f"PAPER TRADING: Insufficient token balance for sell")
            conn.close()
            return None
        
        token_balance = token_data[0]
        token_symbol = token_data[1] if token_data[1] else "Unknown"
        
        # Get token price
        token_price = real_trading.token_price(token)
        if token_price is None:
            warning(f"PAPER TRADING: Could not get token price")
            conn.close()
            return None
        
        # Apply simulated slippage
        adjusted_price = token_price * (1 - (PAPER_TRADING_SLIPPAGE / 10000))
        
        # Calculate USDC amount with slippage
        usdc_amount = token_amount * adjusted_price
        
        # Update token balance
        if token_balance - token_amount <= 0.000001:  # Effectively zero
            cursor.execute("DELETE FROM paper_balance WHERE token_address = ?", (token,))
        else:
            cursor.execute("UPDATE paper_balance SET amount = amount - ?, last_updated = ? WHERE token_address = ?", 
                          (token_amount, datetime.now(), token))
        
        # Update USDC balance
        cursor.execute("SELECT amount FROM paper_balance WHERE token_address = ?", 
                      ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",))
        usdc_balance = cursor.fetchone()
        
        if usdc_balance:
            cursor.execute("UPDATE paper_balance SET amount = amount + ?, last_updated = ? WHERE token_address = ?", 
                          (usdc_amount, datetime.now(), "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"))
        else:
            cursor.execute("INSERT INTO paper_balance (token_address, token_symbol, amount, last_updated) VALUES (?, ?, ?, ?)", 
                          ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "USDC", usdc_amount, datetime.now()))
        
        # Generate fake transaction ID
        tx_id = f"paper_tx_{int(time.time())}_{token[:8]}"
        
        # Record transaction
        cursor.execute('''
        INSERT INTO paper_transactions 
        (timestamp, token_address, token_symbol, action, amount, price, usd_value, tx_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now(), token, token_symbol, "SELL", token_amount, adjusted_price, usdc_amount, tx_id))
        
        conn.commit()
        conn.close()
        
        info(f"PAPER TRADING: Sell executed - {token_amount:.4f} tokens at ${adjusted_price:.6f}")
        debug(f"PAPER TRADING TX: {tx_id}")
        
        return tx_id
    except Exception as e:
        error(f"Error in paper trading market_sell: {str(e)}")
        return None

def ai_entry(token, amount):
    """Paper trading wrapper for ai_entry"""
    if not PAPER_TRADING_ENABLED:
        return real_trading.ai_entry(token, amount)
    
    try:
        info(f"PAPER TRADING: AI entry for {token} with ${amount:.2f}")
        
        # Convert amount to USDC lamports
        usdc_lamports = int(float(amount) * 1_000_000)  # USDC has 6 decimals
        
        # Execute with the market_buy function
        result = market_buy(token, str(usdc_lamports), PAPER_TRADING_SLIPPAGE)
        
        return result is not None  # Return success boolean like the real function
    except Exception as e:
        error(f"Error in paper trading ai_entry: {str(e)}")
        return False

def chunk_kill(token_mint_address, max_usd_order_size, slippage):
    """Paper trading wrapper for chunk_kill"""
    if not PAPER_TRADING_ENABLED:
        return real_trading.chunk_kill(token_mint_address, max_usd_order_size, slippage)
    
    try:
        info(f"PAPER TRADING: Executing chunk_kill for {token_mint_address}")
        
        # Get token balance
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT amount, token_symbol FROM paper_balance WHERE token_address = ?", (token_mint_address,))
        token_data = cursor.fetchone()
        conn.close()
        
        if not token_data or token_data[0] <= 0:
            warning(f"PAPER TRADING: No position to close")
            return False
        
        token_amount = token_data[0]
        token_symbol = token_data[1] if token_data[1] else "Unknown"
        
        # Get token decimals
        decimals = real_trading.get_decimals(token_mint_address)
        
        # Calculate lamports
        token_lamports = int(token_amount * (10 ** decimals))
        
        # Execute the sell
        result = market_sell(token_mint_address, token_lamports, slippage)
        
        return result is not None  # Return success boolean
    except Exception as e:
        error(f"Error in paper trading chunk_kill: {str(e)}")
        return False

def get_position(token_mint_address):
    """Paper trading wrapper for get_position"""
    if not PAPER_TRADING_ENABLED:
        return real_trading.get_position(token_mint_address)
    
    return get_token_balance(token_mint_address)

def get_paper_portfolio():
    """Get the complete paper trading portfolio"""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM paper_balance", conn)
        
        # Add USD value column
        df['USD Value'] = df.apply(lambda row: row['amount'] * real_trading.token_price(row['token_address']) 
                                  if real_trading.token_price(row['token_address']) else 0, axis=1)
        
        conn.close()
        return df
    except Exception as e:
        error(f"Error getting paper portfolio: {str(e)}")
        return pd.DataFrame()

def get_paper_transactions(limit=100):
    """Get recent paper trading transactions"""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT * FROM paper_transactions ORDER BY timestamp DESC LIMIT {limit}", conn)
        conn.close()
        return df
    except Exception as e:
        error(f"Error getting paper transactions: {str(e)}")
        return pd.DataFrame()

def get_portfolio_value():
    """Paper trading wrapper for get_portfolio_value
    Calculates total portfolio value from paper trading database"""
    if not PAPER_TRADING_ENABLED:
        # If paper trading is not enabled, we don't handle this case here
        # The RiskAgent will use its own implementation
        return None
    
    try:
        # Get the paper trading portfolio
        df = get_paper_portfolio()
        
        # Calculate total value by summing the USD Value column
        if df is not None and not df.empty and 'USD Value' in df.columns:
            total_value = df['USD Value'].sum()
            info(f"Paper trading portfolio value: ${total_value:.2f}")
            return total_value
        else:
            # Return the initial balance if no portfolio data exists yet
            info(f"Using initial paper balance: ${PAPER_INITIAL_BALANCE:.2f}")
            return PAPER_INITIAL_BALANCE
            
    except Exception as e:
        error(f"Error calculating paper trading portfolio value: {str(e)}")
        # Default to the initial balance on error
        return PAPER_INITIAL_BALANCE

# Export original functions with same names for consistency when not in paper trading mode
token_price = real_trading.token_price