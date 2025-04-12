"""
Moon Dev's Chart Analysis Agent
Built with love by Moon Dev

Chuck the Chart Agent generates and analyzes trading charts using AI vision capabilities.
"""

import os
import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, time
from pathlib import Path
import time
from dotenv import load_dotenv
import anthropic
import openai
from src import nice_funcs as n
from src import nice_funcs_hl as hl
from src.agents.base_agent import BaseAgent
from src.config import (
    DCA_MONITORED_TOKENS, TIMEFRAMES, LOOKBACK_BARS, CHECK_INTERVAL_MINUTES,
    CHART_INDICATORS, CHART_STYLE, CHART_VOLUME_PANEL, CHART_ANALYSIS_PROMPT,
    CHART_MODEL_OVERRIDE, CHART_DEEPSEEK_BASE_URL,
    AI_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS,
    ENABLE_FIBONACCI, FIBONACCI_LEVELS, FIBONACCI_LOOKBACK_PERIODS,
    CHART_RUN_AT_ENABLED, CHART_RUN_AT_TIME, CHART_INTERVAL_UNIT, CHART_INTERVAL_VALUE
)
import traceback
import base64
from io import BytesIO
import re
from colorama import init, Fore, Back, Style 
from src.scripts.ohlcv_collector import collect_token_data
from src.scripts.logger import debug, info, warning, error, critical, system
init()

# Import additional config settings
from src import config
import requests

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Initialize later when needed
DCA_MONITORED_TOKENS_WITH_SYMBOLS = None
SYMBOLS = []

def fetch_token_symbol(token_address):
    url = "https://api.mainnet-beta.solana.com"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenMetadata",
        "params": [token_address]
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        return data.get("result", {}).get("symbol", "UNKNOWN")
    return "UNKNOWN"

class ChartAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__('chartanalysis')
        self.token_map = config.TOKEN_MAP
        
        # Set up monitored tokens with both symbols
        self.dca_tokens = [
            {
                "address": address,
                "symbol": details[0],
                "hl_symbol": details[1]
            } for address, details in self.token_map.items()
        ]
        
        # Set up directories
        self.charts_dir = PROJECT_ROOT / "src" / "data" / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        
        # Load environment variables
        load_dotenv()
        
        # Initialize API clients
        openai_key = os.getenv("OPENAI_KEY")
        anthropic_key = os.getenv("ANTHROPIC_KEY")
        deepseek_key = os.getenv("DEEPSEEK_KEY")
        
        if not openai_key or not anthropic_key:
            raise ValueError("API keys not found in environment variables!")
            
        # Initialize OpenAI client (for TTS and possibly for analysis)
        self.openai_client = openai.OpenAI(api_key=openai_key)
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=anthropic_key)
        
        # Initialize DeepSeek client if key exists
        if deepseek_key:
            self.deepseek_client = openai.OpenAI(
                api_key=deepseek_key,
                base_url=CHART_DEEPSEEK_BASE_URL
            )
            info("DeepSeek model available")
        else:
            self.deepseek_client = None
            warning("No DeepSeek API key found. DeepSeek models will not be available")
        
        # Set AI parameters - use config values
        self.ai_model = config.AI_MODEL
        self.ai_temperature = config.AI_TEMPERATURE
        self.ai_max_tokens = config.AI_MAX_TOKENS
        
        info("Chart Analysis Agent initialized")
        
        # Log which model we'll use (override or default)
        if CHART_MODEL_OVERRIDE != "0":
            info(f"Using AI Model Override: {CHART_MODEL_OVERRIDE}")
        else:
            info(f"Using AI Model: {self.ai_model}")
        
        info(f"Analyzing {len(TIMEFRAMES)} timeframes: {', '.join(TIMEFRAMES)}")
        info(f"Using indicators: {', '.join(CHART_INDICATORS)}")
        
    def _calculate_indicators(self, data):
        """Calculate all required indicators"""
        # Moving Averages
        data['20EMA'] = data['close'].ewm(span=20, adjust=False).mean()
        data['50EMA'] = data['close'].ewm(span=50, adjust=False).mean()
        data['100EMA'] = data['close'].ewm(span=100, adjust=False).mean()
        data['200SMA'] = data['close'].rolling(window=200).mean()
        
        # MACD
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp1 - exp2
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['ATR'] = true_range.rolling(window=14).mean()
        
        return data
    
    def _detect_market_regime(self, data):
        """Detect market regime (trending, sideways, stable)"""
        # Calculate metrics
        atr = data['ATR'].iloc[-1]
        avg_atr = data['ATR'].mean()
        price_change_20 = data['close'].iloc[-1] - data['close'].iloc[-20]
        rsi = data['RSI'].iloc[-1]
        volume_change = data['volume'].iloc[-10:].mean() / data['volume'].iloc[-20:-10].mean()

        # Trend Strength Calculation
        trend_strength = (data['20EMA'] - data['50EMA']).iloc[-1] / avg_atr

        # Regime Detection
        if (atr > avg_atr * 1.3 and 
            abs(trend_strength) > 0.5 and 
            volume_change > 1.2):
            return "STRONG_TREND"
        
        elif (atr < avg_atr * 0.7 and 
              abs(price_change_20) < avg_atr and 
              40 <= rsi <= 60):
            return "SIDEWAYS"
        
        elif (atr > avg_atr * 1.7 or 
              volume_change > 2.0):
            return "VOLATILE_BREAKOUT"
        
        else:
            return "NEUTRAL"
    
    def _generate_chart(self, symbol, timeframe, data):
        """Generate a chart using mplfinance"""
        try:
            # Prepare data
            df = data.copy()
            df.index = pd.to_datetime(df.index)
            
            # Check if data is valid
            if df.empty:
                error("No data available for chart generation")
                return None
                
            # Calculate indicators
            df = self._calculate_indicators(df)
            
            # Create addplot for indicators
            ap = []
            colors = ['blue', 'orange', 'purple', 'green', 'red']
            for i, indicator in enumerate(['20EMA', '50EMA', '100EMA', '200SMA']):
                if indicator in CHART_INDICATORS and indicator in df.columns and not df[indicator].isna().all():
                    ap.append(mpf.make_addplot(df[indicator], color=colors[i]))
            
            # MACD
            if 'MACD' in CHART_INDICATORS and 'MACD' in df.columns:
                ap.append(mpf.make_addplot(df['MACD'], panel=1, color='blue', secondary_y=False))
                ap.append(mpf.make_addplot(df['MACD_Signal'], panel=1, color='orange', secondary_y=False))
            
            # RSI
            if 'RSI' in CHART_INDICATORS and 'RSI' in df.columns:
                ap.append(mpf.make_addplot(df['RSI'], panel=2, color='purple', ylim=(0, 100), secondary_y=False))
            
            # Add Fibonacci levels if enabled
            if ENABLE_FIBONACCI:
                # Detect if we're in an uptrend or downtrend based on last 20 candles
                recent_data = df.iloc[-20:]
                uptrend = recent_data['close'].iloc[-1] > recent_data['close'].iloc[0]
                
                # Calculate Fibonacci levels
                fib_levels = self._calculate_fibonacci_levels(df, is_uptrend=uptrend)
                
                if fib_levels:
                    # Create horizontal lines for Fibonacci levels
                    for level, price in fib_levels.items():
                        if level in [0.0, 1.0]:  # Skip the extremes (0% and 100%)
                            continue
                            
                        # Create a DataFrame with the Fibonacci level price repeated
                        fib_df = pd.DataFrame(
                            index=df.index,
                            data={'fib_{:.3f}'.format(level): [price] * len(df)}
                        )
                        
                        # Determine color based on level
                        if level == 0.5:
                            fib_color = 'red'  # 50% is often most important
                        elif level == 0.618:
                            fib_color = 'goldenrod'  # Golden ratio
                        else:
                            fib_color = 'gray'
                            
                        # Add to plot with reduced opacity and dashed style
                        ap.append(mpf.make_addplot(
                            fib_df['fib_{:.3f}'.format(level)], 
                            color=fib_color,
                            linestyle='dashed',
                            width=1,
                            alpha=0.6
                        ))
            
            # Save chart
            filename = f"{symbol}_{timeframe}_{int(time.time())}.png"
            chart_path = self.charts_dir / filename
            
            # Create the chart
            mpf.plot(df,
                    type='candle',
                    style=CHART_STYLE,
                    volume=CHART_VOLUME_PANEL,
                    addplot=ap if ap else None,
                    title=f"\n{symbol} {timeframe} Chart Analysis",
                    savefig=chart_path)
            
            return chart_path
            
        except Exception as e:
            error(f"Error generating chart: {str(e)}")
            traceback.print_exc()
            return None
            
    def _calculate_fibonacci_levels(self, data, is_uptrend=True):
        """Calculate Fibonacci retracement levels based on recent price action
        
        Args:
            data (DataFrame): Price data with OHLC columns
            is_uptrend (bool): If True, calculate retracement for uptrend (high to low)
                               If False, calculate retracement for downtrend (low to high)
        
        Returns:
            dict: Fibonacci levels with their corresponding prices
        """
        try:
            # Use a subset of data for finding swing points
            lookback = min(FIBONACCI_LOOKBACK_PERIODS, len(data) - 1)
            subset = data.iloc[-lookback:]
            
            if is_uptrend:  # For uptrend, find highest high and lowest low after it
                # Find the highest high in the lookback period
                highest = subset['high'].max()
                highest_idx = subset['high'].idxmax()
                
                # Find the lowest low after the highest high
                if isinstance(highest_idx, (int, np.integer)):
                    # If index is numeric position
                    lows_after = subset.iloc[subset.index.get_loc(highest_idx):]['low']
                else:
                    # If index is datetime or other
                    lows_after = subset.loc[highest_idx:]['low']
                    
                if len(lows_after) > 0:
                    lowest = lows_after.min()
                else:
                    # Fallback: use recent low
                    lowest = subset['low'].min()
                    
                # Price range
                price_range = highest - lowest
                
                # Calculate Fibonacci levels (retracements from high to low)
                levels = {}
                for level in FIBONACCI_LEVELS:
                    levels[level] = highest - (price_range * level)
                
                # Add 0% and 100% levels
                levels[0.0] = highest
                levels[1.0] = lowest
                
                return levels
                
            else:  # For downtrend, find lowest low and highest high after it
                # Find the lowest low in the lookback period
                lowest = subset['low'].min()
                lowest_idx = subset['low'].idxmin()
                
                # Find the highest high after the lowest low
                if isinstance(lowest_idx, (int, np.integer)):
                    # If index is numeric position
                    highs_after = subset.iloc[subset.index.get_loc(lowest_idx):]['high']
                else:
                    # If index is datetime or other
                    highs_after = subset.loc[lowest_idx:]['high']
                    
                if len(highs_after) > 0:
                    highest = highs_after.max()
                else:
                    # Fallback: use recent high
                    highest = subset['high'].max()
                    
                # Price range
                price_range = highest - lowest
                
                # Calculate Fibonacci levels (retracements from low to high)
                levels = {}
                for level in FIBONACCI_LEVELS:
                    levels[level] = lowest + (price_range * level)
                
                # Add 0% and 100% levels
                levels[0.0] = lowest
                levels[1.0] = highest
                
                return levels
                
        except Exception as e:
            error(f"Error calculating Fibonacci levels: {str(e)}")
            traceback.print_exc()
            return None

    def _calculate_entry_price(self, data, action, market_regime):
        """Calculate optimal entry price based on available indicators and market regime"""
        try:
            current_price = data['close'].iloc[-1]
            entry_price = current_price  # Default fallback
            
            # Check which indicators are available
            has_ema = '20EMA' in data.columns and not data['20EMA'].isna().all()
            has_atr = 'ATR' in data.columns and not data['ATR'].isna().all()
            has_macd = 'MACD' in data.columns and not data['MACD'].isna().all()
            has_rsi = 'RSI' in data.columns and not data['RSI'].isna().all()
            
            # Get recent price levels
            recent_high = data['high'].iloc[-10:].max()
            recent_low = data['low'].iloc[-10:].min()
            
            # Calculate Fibonacci levels if enabled
            fib_levels = None
            if ENABLE_FIBONACCI:
                # For BUY, we want to use retracement from an uptrend (high to low)
                # For SELL, we want to use retracement from a downtrend (low to high)
                if action == 'BUY':
                    fib_levels = self._calculate_fibonacci_levels(data, is_uptrend=True)
                elif action == 'SELL':
                    fib_levels = self._calculate_fibonacci_levels(data, is_uptrend=False)
                
                # Log Fibonacci levels for debugging
                if fib_levels:
                    debug("Fibonacci levels:", file_only=True)
                    for level, price in sorted(fib_levels.items()):
                        debug(f"  {level:.3f}: {price:.4f}", file_only=True)
            
            # Different calculation based on action type (BUY or SELL)
            if action == 'BUY':
                # Default buffer size based on market regime and ATR if available
                buffer_size = 0.02  # Default 2% buffer
                
                if has_atr:
                    atr = data['ATR'].iloc[-1]
                    # Adjust buffer based on market regime
                    if market_regime == "STRONG_TREND":
                        buffer_size = atr * 0.5  # Smaller buffer in strong trend
                    elif market_regime == "SIDEWAYS":
                        buffer_size = atr * 1.0  # Medium buffer in sideways market
                    elif market_regime == "VOLATILE_BREAKOUT":
                        buffer_size = atr * 1.5  # Larger buffer in volatile market
                    else:  # NEUTRAL
                        buffer_size = atr * 0.8
                elif not has_atr:
                    # Fallback using percentage of price if ATR not available
                    if market_regime == "STRONG_TREND":
                        buffer_size = current_price * 0.01  # 1% buffer
                    elif market_regime == "SIDEWAYS":
                        buffer_size = current_price * 0.02  # 2% buffer
                    elif market_regime == "VOLATILE_BREAKOUT":
                        buffer_size = current_price * 0.03  # 3% buffer
                    else:  # NEUTRAL
                        buffer_size = current_price * 0.015  # 1.5% buffer
                
                # Use Fibonacci levels if available and price is above the 0.618 level
                if fib_levels and current_price > fib_levels.get(0.618, 0):
                    # Find the best Fibonacci level to use as entry
                    # For BUY, we want the highest fib level below current price
                    best_fib_level = None
                    best_fib_price = 0
                    
                    for level, price in fib_levels.items():
                        if price < current_price and price > best_fib_price:
                            best_fib_level = level
                            best_fib_price = price
                    
                    if best_fib_level is not None:
                        # Use the highest Fibonacci level below current price
                        # Adjust based on market regime - closer to price in trending,
                        # closer to fib level in sideways
                        if market_regime == "STRONG_TREND":
                            # In strong trend, enter closer to current price
                            entry_price = current_price - buffer_size
                        else:
                            # In other regimes, use the Fibonacci level with a small buffer
                            # based on ATR to increase chance of getting filled
                            entry_price = best_fib_price + (buffer_size * 0.25)
                        
                        info(f"Using Fibonacci {best_fib_level:.3f} level for BUY entry: ${best_fib_price:.4f}")
                    else:
                        # Fallback to indicator-based entry if no suitable fib level
                        entry_price = current_price - buffer_size
                
                # If no suitable Fibonacci level or not enabled, use indicators
                else:
                    # Calculate entry based on available indicators
                    if has_ema:
                        # Find the highest EMA below current price to use as support
                        emas = []
                        for ema in ['20EMA', '50EMA', '100EMA', '200SMA']:
                            if ema in data.columns and not data[ema].isna().all():
                                ema_value = data[ema].iloc[-1]
                                if ema_value < current_price:
                                    emas.append(ema_value)
                        
                        if emas:
                            # Use the highest EMA below price as support level
                            support_level = max(emas)
                            # Entry price is between current price and support, biased by market regime
                            if market_regime == "STRONG_TREND":
                                # In strong trend, enter closer to current price
                                entry_price = current_price - buffer_size * 0.7
                            else:
                                # Otherwise try to get a better entry closer to support
                                entry_price = max(support_level, current_price - buffer_size)
                        else:
                            # If no EMAs below price, use recent low as support
                            entry_price = max(recent_low, current_price - buffer_size)
                            
                    elif has_macd and not has_ema:
                        # Use MACD for entry if EMAs not available
                        macd = data['MACD'].iloc[-1]
                        macd_signal = data['MACD_Signal'].iloc[-1]
                        
                        if macd > macd_signal:
                            # Stronger buy signal - use smaller buffer
                            entry_price = current_price - buffer_size * 0.7
                        else:
                            # Weaker buy signal - wait for deeper pullback
                            entry_price = current_price - buffer_size * 1.2
                            
                    elif has_rsi and not (has_ema or has_macd):
                        # Use RSI for entry if other indicators not available
                        rsi = data['RSI'].iloc[-1]
                        
                        if rsi < 30:
                            # Oversold - good entry point, use smaller buffer
                            entry_price = current_price - buffer_size * 0.5
                        elif rsi > 70:
                            # Overbought - wait for pullback, use larger buffer
                            entry_price = current_price - buffer_size * 1.5
                        else:
                            # Normal RSI - standard buffer
                            entry_price = current_price - buffer_size
                    else:
                        # Minimal indicators available - use price action only
                        entry_price = current_price - buffer_size
                    
            elif action == 'SELL':
                # Similar logic for SELL but reversed
                buffer_size = 0.02  # Default 2% buffer
                
                if has_atr:
                    atr = data['ATR'].iloc[-1]
                    if market_regime == "STRONG_TREND":
                        buffer_size = atr * 0.5
                    elif market_regime == "SIDEWAYS":
                        buffer_size = atr * 1.0
                    elif market_regime == "VOLATILE_BREAKOUT":
                        buffer_size = atr * 1.5
                    else:  # NEUTRAL
                        buffer_size = atr * 0.8
                elif not has_atr:
                    if market_regime == "STRONG_TREND":
                        buffer_size = current_price * 0.01
                    elif market_regime == "SIDEWAYS":
                        buffer_size = current_price * 0.02
                    elif market_regime == "VOLATILE_BREAKOUT":
                        buffer_size = current_price * 0.03
                    else:  # NEUTRAL
                        buffer_size = current_price * 0.015
                
                # Use Fibonacci levels if available and price is below the 0.382 level
                # (0.382 is often a resistance level in downtrends)
                if fib_levels and current_price < fib_levels.get(0.382, float('inf')):
                    # Find the best Fibonacci level to use as entry
                    # For SELL, we want the lowest fib level above current price
                    best_fib_level = None
                    best_fib_price = float('inf')
                    
                    for level, price in fib_levels.items():
                        if price > current_price and price < best_fib_price:
                            best_fib_level = level
                            best_fib_price = price
                    
                    if best_fib_level is not None:
                        # Use the lowest Fibonacci level above current price
                        # Adjust based on market regime - closer to price in trending,
                        # closer to fib level in sideways
                        if market_regime == "STRONG_TREND":
                            # In strong trend, enter closer to current price
                            entry_price = current_price + buffer_size
                        else:
                            # In other regimes, use the Fibonacci level with a small buffer
                            # based on ATR to increase chance of getting filled
                            entry_price = best_fib_price - (buffer_size * 0.25)
                        
                        info(f"Using Fibonacci {best_fib_level:.3f} level for SELL entry: ${best_fib_price:.4f}")
                    else:
                        # Fallback to indicator-based entry if no suitable fib level
                        entry_price = current_price + buffer_size
                
                # If no suitable Fibonacci level or not enabled, use indicators
                else:
                    # Calculate entry based on available indicators
                    if has_ema:
                        # Find the lowest EMA above current price to use as resistance
                        emas = []
                        for ema in ['20EMA', '50EMA', '100EMA', '200SMA']:
                            if ema in data.columns and not data[ema].isna().all():
                                ema_value = data[ema].iloc[-1]
                                if ema_value > current_price:
                                    emas.append(ema_value)
                        
                        if emas:
                            # Use the lowest EMA above price as resistance level
                            resistance_level = min(emas)
                            # Entry price is between current price and resistance, biased by market regime
                            if market_regime == "STRONG_TREND":
                                # In strong trend, enter closer to current price
                                entry_price = current_price + buffer_size * 0.7
                            else:
                                # Otherwise try to get a better entry closer to resistance
                                entry_price = min(resistance_level, current_price + buffer_size)
                        else:
                            # If no EMAs above price, use recent high as resistance
                            entry_price = min(recent_high, current_price + buffer_size)
                            
                    elif has_macd and not has_ema:
                        # Use MACD for entry if EMAs not available
                        macd = data['MACD'].iloc[-1]
                        macd_signal = data['MACD_Signal'].iloc[-1]
                        
                        if macd < macd_signal:
                            # Stronger sell signal - use smaller buffer
                            entry_price = current_price + buffer_size * 0.7
                        else:
                            # Weaker sell signal - wait for higher bounce
                            entry_price = current_price + buffer_size * 1.2
                            
                    elif has_rsi and not (has_ema or has_macd):
                        # Use RSI for entry if other indicators not available
                        rsi = data['RSI'].iloc[-1]
                        
                        if rsi > 70:
                            # Overbought - good exit point, use smaller buffer
                            entry_price = current_price + buffer_size * 0.5
                        elif rsi < 30:
                            # Oversold - wait for bounce, use larger buffer
                            entry_price = current_price + buffer_size * 1.5
                        else:
                            # Normal RSI - standard buffer
                            entry_price = current_price + buffer_size
                    else:
                        # Minimal indicators available - use price action only
                        entry_price = current_price + buffer_size
            else:
                # For NOTHING action, just return current price
                entry_price = current_price
                
            # Final check to ensure entry price is reasonable (not negative or too far from current price)
            if entry_price <= 0:
                entry_price = current_price * 0.95  # Default to 5% below current price if calculation fails
                
            # Don't allow entry prices more than 10% away from current price (sanity check)
            max_distance = current_price * 0.1
            if abs(entry_price - current_price) > max_distance:
                if entry_price < current_price:
                    entry_price = current_price - max_distance
                else:
                    entry_price = current_price + max_distance
                    
            return entry_price
            
        except Exception as e:
            error(f"Error calculating entry price: {str(e)}")
            return data['close'].iloc[-1]  # Return current price as fallback

    def _analyze_chart(self, symbol, timeframe, data):
        """Analyze chart data using specified AI model"""
        try:
            # Detect market regime
            market_regime = self._detect_market_regime(data)
            
            # Get volume trend
            volume_trend = 'Increasing' if data['volume'].iloc[-1] > data['volume'].mean() else 'Decreasing'
            
            # Get current price
            current_price = data['close'].iloc[-1]
            
            # Format the chart data
            chart_data = (
                f"Recent price action (last 5 candles):\n{data.tail(5).to_string()}\n\n"
                f"Technical Indicators:\n"
                f"- 20EMA: {data['20EMA'].iloc[-1]:.2f}\n"
                f"- 50EMA: {data['50EMA'].iloc[-1]:.2f}\n"
                f"- 100EMA: {data['100EMA'].iloc[-1]:.2f}\n"
                f"- 200SMA: {data['200SMA'].iloc[-1]:.2f}\n"
                f"- MACD: {data['MACD'].iloc[-1]:.2f}\n"
                f"- MACD Signal: {data['MACD_Signal'].iloc[-1]:.2f}\n"
                f"- RSI: {data['RSI'].iloc[-1]:.2f}\n"
                f"- ATR: {data['ATR'].iloc[-1]:.2f}\n"
                f"Current price: {current_price:.2f}\n"
                f"24h High: {data['high'].max():.2f}\n"
                f"24h Low: {data['low'].min():.2f}\n"
                f"Volume trend: {volume_trend}\n"
                f"Market Regime: {market_regime}"
            )
            
            # Add previous recommendation analysis
            filepath = os.path.join('src/data/charts', f'chart_analysis_{symbol}.csv')
            if os.path.exists(filepath):
                try:
                    prev_df = pd.read_csv(filepath)
                    if not prev_df.empty:
                        # Get last recommendation
                        last_rec = prev_df.iloc[-1]
                        last_rec_time = datetime.fromtimestamp(last_rec['timestamp'])
                        time_diff = (datetime.now() - last_rec_time).total_seconds() / 3600  # in hours
                        
                        # Add to chart data
                        chart_data += f"\n\nPrevious analysis ({time_diff:.1f} hours ago):\n"
                        chart_data += f"Signal: {last_rec['signal']}, Confidence: {last_rec['confidence']}%\n"
                        chart_data += f"Price then: {last_rec['price']:.4f}, Current: {current_price:.4f}, "
                        chart_data += f"Change: {((current_price/last_rec['price'])-1)*100:.2f}%\n"
                        chart_data += f"Previous entry price suggestion: {last_rec['entry_price']:.4f}\n"
                        
                        # Add performance of that recommendation
                        if last_rec['signal'] == 'BUY':
                            performance = ((current_price/last_rec['price'])-1)*100
                            chart_data += f"Performance since recommendation: {performance:.2f}%\n"
                        elif last_rec['signal'] == 'SELL':
                            performance = ((last_rec['price']/current_price)-1)*100
                            chart_data += f"Performance since recommendation: {performance:.2f}%\n"
                        
                        # Get recent history (last 3 signals that were different from each other)
                        if len(prev_df) >= 3:
                            unique_signals = []
                            signal_history = []
                            
                            for idx in range(len(prev_df)-1, -1, -1):
                                rec = prev_df.iloc[idx]
                                if rec['signal'] not in unique_signals:
                                    unique_signals.append(rec['signal'])
                                    signal_history.append({
                                        'timestamp': datetime.fromtimestamp(rec['timestamp']),
                                        'signal': rec['signal'],
                                        'price': rec['price'],
                                        'confidence': rec['confidence']
                                    })
                                    
                                if len(unique_signals) >= 3:
                                    break
                            
                            if len(signal_history) > 1:
                                chart_data += "\nRecent signal history:\n"
                                for rec in signal_history:
                                    time_ago = (datetime.now() - rec['timestamp']).total_seconds() / 3600
                                    chart_data += f"- {time_ago:.1f}h ago: {rec['signal']} at ${rec['price']:.4f} (Confidence: {rec['confidence']}%)\n"
                
                    # Calculate trend consistency - how many consistent recommendations in a row
                    if len(prev_df) >= 2:
                        last_signal = prev_df.iloc[-1]['signal']
                        consistent_count = 1
                        
                        for idx in range(len(prev_df)-2, -1, -1):
                            if prev_df.iloc[idx]['signal'] == last_signal:
                                consistent_count += 1
                            else:
                                break
                        
                        if consistent_count > 1:
                            chart_data += f"\nSignal consistency: {consistent_count} consecutive {last_signal} recommendations\n"
                
                except Exception as e:
                    warning(f"Error loading previous recommendation data: {str(e)}")
            
            # Prepare the context
            context = CHART_ANALYSIS_PROMPT.format(
                symbol=symbol,
                timeframe=timeframe,
                chart_data=chart_data
            )
            
            info(f"Analyzing {symbol} with AI")
            
            # Use the model specified in CHART_MODEL_OVERRIDE, or default to config settings
            if CHART_MODEL_OVERRIDE.startswith("deepseek") and self.deepseek_client:
                info(f"Using DeepSeek {CHART_MODEL_OVERRIDE} model for analysis")
                response = self.deepseek_client.chat.completions.create(
                    model=CHART_MODEL_OVERRIDE.replace("deepseek-", "deepseek-"),  # Ensure correct model name format
                    messages=[
                        {"role": "system", "content": "You are Moon Dev's Chart Analysis Agent. Analyze chart data and recommend BUY, SELL, or NOTHING."},
                        {"role": "user", "content": context}
                    ],
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature
                )
                content = response.choices[0].message.content
                
            elif CHART_MODEL_OVERRIDE.startswith("gpt-") and self.openai_client:
                info(f"Using OpenAI {CHART_MODEL_OVERRIDE} model for analysis")
                response = self.openai_client.chat.completions.create(
                    model=CHART_MODEL_OVERRIDE,
                    messages=[
                        {"role": "system", "content": "You are Moon Dev's Chart Analysis Agent. Analyze chart data and recommend BUY, SELL, or NOTHING."},
                        {"role": "user", "content": context}
                    ],
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature
                )
                content = response.choices[0].message.content
                
            else:
                # Use Claude as before (default)
                info(f"Using Claude {self.ai_model} model for analysis")
                message = self.client.messages.create(
                    model=self.ai_model,
                    max_tokens=self.ai_max_tokens,
                    temperature=self.ai_temperature,
                    messages=[{
                        "role": "user",
                        "content": context
                    }]
                )
                content = str(message.content)
                
                # Debug: Log raw response
                debug("Raw response:", file_only=True)
                debug(repr(content), file_only=True)
            
            # Clean up TextBlock formatting for Claude responses
            if isinstance(content, str) and 'TextBlock' in content:
                match = re.search(r"text='([^']*)'", content, re.IGNORECASE)
                if match:
                    content = match.group(1)
            
            # Clean up any remaining formatting
            if isinstance(content, str):
                content = content.replace('\\n', '\n')
                content = content.strip('[]')
            
            # Split into lines and process
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            if not lines:
                error("Empty response from AI")
                return None
            
            # First line should be the action
            action = lines[0].strip().upper()
            if action not in ['BUY', 'SELL', 'NOTHING']:
                warning(f"Invalid action: {action}")
                return None
            
            # Rest is analysis
            analysis = lines[1] if len(lines) > 1 else ""
            
            # Extract confidence from third line
            confidence = 50  # Default confidence
            if len(lines) > 2:
                try:
                    matches = re.findall(r'(\d+)%', lines[2])
                    if matches:
                        confidence = int(matches[0])
                except:
                    warning("Could not parse confidence, using default")
            
            # Extract AI-suggested entry price from fourth line if available
            ai_entry_price = None
            if len(lines) > 3:
                try:
                    # Look for a numeric value in the fourth line
                    price_matches = re.findall(r'[\$]?([\d\.]+)', lines[3])
                    if price_matches:
                        ai_entry_price = float(price_matches[0])
                        debug(f"AI suggested entry price: {ai_entry_price}", file_only=True)
                except Exception as e:
                    warning(f"Could not parse AI entry price: {str(e)}")
            
            # Calculate our own entry price as fallback or if AI didn't provide one
            calculated_entry_price = self._calculate_entry_price(data, action, market_regime)
            
            # Use AI's entry price if provided and reasonable, otherwise use calculated one
            entry_price = ai_entry_price if ai_entry_price and ai_entry_price > 0 else calculated_entry_price
            
            # Determine direction based on action
            if action == 'BUY':
                direction = 'BULLISH'
            elif action == 'SELL':
                direction = 'BEARISH'
            else:
                direction = 'SIDEWAYS'
            
            # Update the return dictionary to include price and entry price
            analysis_dict = {
                'direction': direction,
                'analysis': analysis,
                'action': action,
                'confidence': confidence,
                'market_regime': market_regime,
                'volume_trend': volume_trend,
                'price': current_price,  # Current price
                'entry_price': entry_price  # Optimal entry price
            }
            
            # After analyzing with AI and before saving to CSV
            if analysis and 'action' in analysis:
                # Check if there are previous recommendations
                prev_filepath = os.path.join('src/data/charts', f'chart_analysis_{symbol}.csv')
                if os.path.exists(prev_filepath):
                    prev_df = pd.read_csv(prev_filepath)
                    if not prev_df.empty:
                        last_rec = prev_df.iloc[-1]
                        last_action = last_rec['signal']
                        
                        # Log if the recommendation changed
                        if analysis['action'] != last_action:
                            info(f"Signal changed from {last_action} to {analysis['action']} for {symbol}")
                            
                            # If the recommendation flipped, check if the previous one was profitable
                            if last_rec['price'] > 0:
                                if last_action == 'BUY':
                                    profit_pct = ((current_price / last_rec['price']) - 1) * 100
                                    info(f"Previous BUY signal profit: {profit_pct:.2f}%")
                                elif last_action == 'SELL':
                                    profit_pct = ((last_rec['price'] / current_price) - 1) * 100
                                    info(f"Previous SELL signal profit: {profit_pct:.2f}%")
            
            return analysis_dict
            
        except Exception as e:
            error(f"Error in chart analysis: {str(e)}")
            traceback.print_exc()
            
    def _format_fallback_data(self, fallback_data, timeframe):
        """Format data from OHLCV collector to match Hyperliquid format"""
        try:
            if fallback_data is None or fallback_data.empty:
                return None
            
            # Create a copy of the dataframe
            df = fallback_data.copy()
            
            # Set date as index if it exists
            if 'date' in df.columns:
                df = df.set_index('date')
            
            # Ensure required columns exist
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    if col == 'volume':
                        df[col] = 100000  # Default volume
                    elif col == 'open' and 'close' in df.columns:
                        df[col] = df['close']  # Use close price if open is missing
                    elif col == 'high' and 'close' in df.columns:
                        df[col] = df['close'] * 1.01  # Estimate high as 1% above close
                    elif col == 'low' and 'close' in df.columns:
                        df[col] = df['close'] * 0.99  # Estimate low as 1% below close
                    elif 'price' in df.columns:
                        df[col] = df['price']  # Use price column if available
            
            # Make sure we have the right number of bars
            if len(df) > LOOKBACK_BARS:
                df = df.tail(LOOKBACK_BARS)
            
            return df
            
        except Exception as e:
            error(f"Error formatting fallback data: {str(e)}")
            return None

    def _save_analysis_to_csv(self, symbol, timeframe, analysis, address):
        """Save analysis to CSV with consistent filenames"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs('src/data/charts', exist_ok=True)
            
            # Use consistent filename instead of timestamp-based filename
            filename = f'chart_analysis_{symbol}.csv'
            filepath = os.path.join('src/data/charts', filename)
            
            # Calculate historical accuracy
            accuracy_data = self._calculate_recommendation_accuracy(symbol)
            
            # Create DataFrame and save - use the actual values from the analysis dict
            df = pd.DataFrame([{
                'symbol': symbol,
                'timeframe': timeframe,
                'signal': analysis.get('action', 'NEUTRAL'),
                'confidence': analysis.get('confidence', 50),
                'price': analysis.get('price', 0),
                'entry_price': analysis.get('entry_price', analysis.get('price', 0)),
                'reasoning': analysis.get('analysis', ''),
                'timestamp': datetime.now().timestamp(),
                'market_regime': analysis.get('market_regime', 'NEUTRAL'),
                'direction': analysis.get('direction', 'SIDEWAYS'),
                'volume_trend': analysis.get('volume_trend', 'Unknown'),
                'historical_accuracy': accuracy_data['accuracy'] if accuracy_data else None,
                'recommendation_performance': accuracy_data['recommendation_performance'] if accuracy_data else None
            }])
            
            debug(f"Analysis data for CSV: {df.to_dict('records')}", file_only=True)
            
            # Check if file exists to append or create new
            if os.path.exists(filepath):
                try:
                    # Read existing file
                    existing_df = pd.read_csv(filepath)
                    
                    # Check if columns match - if not, update existing file structure
                    if set(df.columns) != set(existing_df.columns):
                        # Add missing columns to existing data with default values
                        for col in df.columns:
                            if col not in existing_df.columns:
                                if col == 'market_regime':
                                    existing_df[col] = 'NEUTRAL'
                                elif col == 'direction':
                                    existing_df[col] = 'SIDEWAYS'
                                elif col == 'volume_trend':
                                    existing_df[col] = 'Unknown'
                                elif col == 'entry_price':
                                    existing_df[col] = existing_df['price']  # Use price as fallback
                                else:
                                    existing_df[col] = ''
                    
                    # Save combined data
                    updated_df = pd.concat([existing_df, df], ignore_index=True)
                    updated_df.to_csv(filepath, index=False)
                    debug(f"Updated existing analysis file with {len(updated_df)} records", file_only=True)
                except Exception as e:
                    # If error reading existing file, just overwrite with new data
                    df.to_csv(filepath, index=False)
                    warning(f"Error updating existing file, created new: {str(e)}")
            else:
                # File doesn't exist, create new
                df.to_csv(filepath, index=False)
                debug("Created new analysis file", file_only=True)
                
            info(f"Analysis saved to file: {symbol}_{timeframe}")
            
            return filepath
        except Exception as e:
            error(f"Error saving analysis to CSV: {str(e)}")
            return None
            
    def analyze_symbol(self, token_info, timeframe):
        """Analyze a single symbol on a specific timeframe"""
        try:
            symbol = token_info["symbol"]
            hl_symbol = token_info["hl_symbol"]
            address = token_info["address"]
            
            info(f"Analyzing {symbol} ({hl_symbol}) on {timeframe}")
            
            # Calculate historical accuracy
            accuracy_data = self._calculate_recommendation_accuracy(symbol)
            if accuracy_data:
                info(f"Historical recommendation accuracy for {symbol}: {accuracy_data['accuracy']:.1f}% over {accuracy_data['total_evaluated']} signals")
                info(f"Recommendation performance metric: {accuracy_data['recommendation_performance']:.2f}%")
            
            # Get market data using Hyperliquid symbol
            data = hl.get_data(
                symbol=hl_symbol,
                timeframe=timeframe,
                bars=LOOKBACK_BARS,
                add_indicators=True
            )
            
            # If Hyperliquid data is not available, use fallback
            if data is None or data.empty:
                warning(f"No Hyperliquid data available for {symbol} {timeframe}, trying fallback")
                
                # Use ohlcv_collector to get data
                fallback_data = collect_token_data(address)
                
                if fallback_data is None or fallback_data.empty:
                    error(f"No data available from any source for {symbol} {timeframe}")
                    return
                
                # Format the fallback data to match Hyperliquid format
                data = self._format_fallback_data(fallback_data, timeframe)
                
                if data is None or data.empty:
                    error(f"Failed to format fallback data for {symbol} {timeframe}")
                    return
                
                info(f"Using fallback data for {symbol} {timeframe}")
            
            # Calculate additional indicators
            data = self._calculate_indicators(data)
            
            # Generate and save chart first
            info(f"Generating chart for {symbol} {timeframe}")
            chart_path = self._generate_chart(symbol, timeframe, data)
            if chart_path:
                info(f"Chart saved to: {chart_path}")
            
            # Debug log the chart data
            debug(f"Chart Data for {symbol} {timeframe} - Last 5 Candles", file_only=True)
            
            # Log last 5 candles with proper timestamp formatting
            last_5 = data.tail(5)
            last_5.index = pd.to_datetime(last_5.index)
            for idx, row in last_5.iterrows():
                time_str = idx.strftime('%Y-%m-%d %H:%M')  # Include date and time
                debug(f"{time_str} | Open: {row['open']:.2f} | High: {row['high']:.2f} | Low: {row['low']:.2f} | Close: {row['close']:.2f} | Volume: {row['volume']:.0f}", file_only=True)
            
            debug("Technical Indicators:", file_only=True)
            debug(f"20EMA: {data['20EMA'].iloc[-1]:.2f}", file_only=True)
            debug(f"50EMA: {data['50EMA'].iloc[-1]:.2f}", file_only=True)
            debug(f"100EMA: {data['100EMA'].iloc[-1]:.2f}", file_only=True)
            debug(f"200SMA: {data['200SMA'].iloc[-1]:.2f}", file_only=True)
            debug(f"MACD: {data['MACD'].iloc[-1]:.2f}", file_only=True)
            debug(f"MACD Signal: {data['MACD_Signal'].iloc[-1]:.2f}", file_only=True)
            debug(f"RSI: {data['RSI'].iloc[-1]:.2f}", file_only=True)
            debug(f"ATR: {data['ATR'].iloc[-1]:.2f}", file_only=True)
            debug(f"24h High: {data['high'].max():.2f}", file_only=True)
            debug(f"24h Low: {data['low'].min():.2f}", file_only=True)
            debug(f"Volume Trend: {'Increasing' if data['volume'].iloc[-1] > data['volume'].mean() else 'Decreasing'}", file_only=True)
                
            # Analyze with AI
            info(f"Analyzing {symbol} {timeframe} with AI")
            analysis = self._analyze_chart(symbol, timeframe, data)
            
            if analysis and all(k in analysis for k in ['direction', 'analysis', 'action', 'confidence', 'market_regime']):
                # Save analysis to CSV - this now captures all values correctly
                self._save_analysis_to_csv(symbol, timeframe, analysis, address)
                    
                # Print analysis summary
                info(f"Analysis result for {symbol} {timeframe}:")
                info(f"Market Regime: {analysis['market_regime']}")
                info(f"Direction: {analysis['direction']}")
                info(f"Action: {analysis['action']}")
                info(f"Confidence: {analysis['confidence']}%")
                info(f"Current Price: ${analysis['price']:.4f}")
                info(f"Optimal Entry Price: ${analysis['entry_price']:.4f}")
                info(f"Analysis: {analysis['analysis']}")
                
                # Check if there are previous recommendations
                prev_filepath = os.path.join('src/data/charts', f'chart_analysis_{symbol}.csv')
                if os.path.exists(prev_filepath):
                    prev_df = pd.read_csv(prev_filepath)
                    if not prev_df.empty:
                        last_rec = prev_df.iloc[-1]
                        last_action = last_rec['signal']
                        
                        # Log if the recommendation changed
                        if analysis['action'] != last_action:
                            info(f"Signal changed from {last_action} to {analysis['action']} for {symbol}")
                            
                            # If the recommendation flipped, check if the previous one was profitable
                            if last_rec['price'] > 0:
                                if last_action == 'BUY':
                                    profit_pct = ((analysis['price'] / last_rec['price']) - 1) * 100
                                    info(f"Previous BUY signal profit: {profit_pct:.2f}%")
                                elif last_action == 'SELL':
                                    profit_pct = ((last_rec['price'] / analysis['price']) - 1) * 100
                                    info(f"Previous SELL signal profit: {profit_pct:.2f}%")
            else:
                warning(f"Invalid analysis result for {symbol}")
            
        except Exception as e:
            error(f"Error analyzing {symbol} {timeframe}: {str(e)}")
            traceback.print_exc()
            
    def _cleanup_old_charts(self):
        """Remove all existing charts from the charts directory"""
        try:
            for chart in self.charts_dir.glob("*.png"):
                chart.unlink()
            info("Cleaned up old charts")
        except Exception as e:
            error(f"Error cleaning up charts: {str(e)}")

    def run_monitoring_cycle(self):
        """Run one monitoring cycle"""
        try:
            # Clean up old charts before starting new cycle
            self._cleanup_old_charts()
            
            for token_info in self.dca_tokens:
                for timeframe in TIMEFRAMES:
                    self.analyze_symbol(token_info, timeframe)
                    time.sleep(2)  # Small delay between analyses
                    
        except Exception as e:
            error(f"Error in monitoring cycle: {str(e)}")
            
    def run(self):
        """Run the chart analysis monitor continuously"""
        info("Starting chart analysis monitoring")
        
        while True:
            current_time = datetime.now().time()
            current_date = datetime.now().date()
            
            # Check if we should run at a specific time
            if CHART_RUN_AT_ENABLED:
                # Parse the time from string "HH:MM"
                run_at_hour, run_at_minute = map(int, CHART_RUN_AT_TIME.split(':'))
                run_at_time = time(run_at_hour, run_at_minute)
                
                # Calculate time difference in minutes
                current_minutes = current_time.hour * 60 + current_time.minute
                run_at_minutes = run_at_hour * 60 + run_at_minute
                
                # If within 5 minutes of target time, run analysis
                if abs(current_minutes - run_at_minutes) <= 5:
                    self.run_monitoring_cycle()
                    
                    # Sleep for 10 minutes to avoid multiple runs near the target time
                    time.sleep(600)
                    continue
                
            # Otherwise run based on the interval
            self.run_monitoring_cycle()
            
            # Sleep based on CHECK_INTERVAL_MINUTES
            time.sleep(CHECK_INTERVAL_MINUTES * 60)

    def _calculate_recommendation_accuracy(self, symbol):
        """Calculate the accuracy of historical recommendations"""
        try:
            filepath = os.path.join('src/data/charts', f'chart_analysis_{symbol}.csv')
            if not os.path.exists(filepath):
                return None
            
            df = pd.read_csv(filepath)
            if len(df) < 3:  # Need at least a few recommendations to calculate accuracy
                return None
            
            # Add a 'correct' column
            df = df.sort_values('timestamp')
            df['correct'] = False
            df['profit_pct'] = 0.0
            
            # Loop through recommendations
            for i in range(len(df) - 1):
                current_rec = df.iloc[i]
                next_price = df.iloc[i+1]['price']
                
                # Evaluate if recommendation was correct
                if current_rec['signal'] == 'BUY':
                    profit_pct = ((next_price / current_rec['price']) - 1) * 100
                    df.at[df.index[i], 'profit_pct'] = profit_pct
                    df.at[df.index[i], 'correct'] = profit_pct > 0
                    
                elif current_rec['signal'] == 'SELL':
                    profit_pct = ((current_rec['price'] / next_price) - 1) * 100
                    df.at[df.index[i], 'profit_pct'] = profit_pct
                    df.at[df.index[i], 'correct'] = profit_pct > 0
                    
                elif current_rec['signal'] == 'NOTHING':
                    # Nothing is correct if price stayed within ±3%
                    price_change_pct = abs((next_price / current_rec['price'] - 1) * 100)
                    df.at[df.index[i], 'correct'] = price_change_pct < 3
                
            # Calculate accuracy
            accurate_recs = df['correct'].sum()
            total_evaluated = df['correct'].count() - 1  # Last one can't be evaluated yet
            
            if total_evaluated > 0:
                accuracy = (accurate_recs / total_evaluated) * 100
                df['profit_pct'].mean()
                
                return {
                    'accuracy': accuracy,
                    'recommendation_performance': df['profit_pct'].mean(),
                    'total_evaluated': total_evaluated
                }
            
            return None
            
        except Exception as e:
            error(f"Error calculating recommendation accuracy: {str(e)}")
            return None

if __name__ == "__main__":
    # Create and run the agent
    info("Chart Analysis Agent Starting Up")
    info("Monitoring symbols: " + ', '.join(SYMBOLS))
    agent = ChartAnalysisAgent()
    
    # Run the continuous monitoring cycle
    agent.run()