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
from datetime import datetime, timedelta
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
    CHART_MODEL_OVERRIDE, CHART_DEEPSEEK_BASE_URL, VOICE_MODEL, VOICE_NAME, VOICE_SPEED,
    AI_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS
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
        self.audio_dir = PROJECT_ROOT / "src" / "audio"
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
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
            
            # Determine direction based on action
            if action == 'BUY':
                direction = 'BULLISH'
            elif action == 'SELL':
                direction = 'BEARISH'
            else:
                direction = 'SIDEWAYS'
            
            # Update the return dictionary to include price
            return {
                'direction': direction,
                'analysis': analysis,
                'action': action,
                'confidence': confidence,
                'market_regime': market_regime,
                'volume_trend': volume_trend,
                'price': current_price  # Add current price to the return dictionary
            }
            
        except Exception as e:
            error(f"Error in chart analysis: {str(e)}")
            traceback.print_exc()
            return None
            
    def _format_announcement(self, symbol, timeframe, analysis):
        """Format analysis into speech-friendly message"""
        try:
            if not analysis:
                return None
                
            # Convert timeframe to speech-friendly format
            friendly_timeframe = timeframe.replace('m', ' minute').replace('h', ' hour').replace('d', ' day')
                
            message = (
                f"Chart analysis for {symbol} on the {friendly_timeframe} timeframe! "
                f"The market is currently {analysis['market_regime']}. "
                f"The trend is {analysis['direction']}. {analysis['analysis']} "
                f"AI suggests to {analysis['action']} with {analysis['confidence']}% confidence! "
            )
            
            return message
            
        except Exception as e:
            error(f"Error formatting announcement: {str(e)}")
            return None
            
    def _announce(self, message):
        """Announce message using OpenAI TTS"""
        if not message:
            return
            
        try:
            info(f"Announcing: {message}")
            
            # Generate speech
            response = self.openai_client.audio.speech.create(
                model=VOICE_MODEL,
                voice=VOICE_NAME,
                input=message,
                speed=VOICE_SPEED
            )
            
            # Save audio file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_file = self.audio_dir / f"chart_alert_{timestamp}.mp3"
            
            response.stream_to_file(str(audio_file))
            
            # Play audio
            os.system(f"afplay {audio_file}")
            
        except Exception as e:
            error(f"Error in announcement: {str(e)}")
            
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
            
            # Create DataFrame and save - use the actual values from the analysis dict
            df = pd.DataFrame([{
                'symbol': symbol,
                'timeframe': timeframe,
                'signal': analysis.get('action', 'NEUTRAL'),
                'confidence': analysis.get('confidence', 50),
                'price': analysis.get('price', 0),
                'reasoning': analysis.get('analysis', ''),
                'timestamp': datetime.now().timestamp(),
                'market_regime': analysis.get('market_regime', 'NEUTRAL'),
                'direction': analysis.get('direction', 'SIDEWAYS'),
                'volume_trend': analysis.get('volume_trend', 'Unknown')
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
                # Format and announce
                message = self._format_announcement(symbol, timeframe, analysis)
                if message:
                    self._announce(message)
                    
                # Save analysis to CSV - this now captures all values correctly
                self._save_analysis_to_csv(symbol, timeframe, analysis, address)
                    
                # Print analysis summary
                info(f"Analysis result for {symbol} {timeframe}:")
                info(f"Market Regime: {analysis['market_regime']}")
                info(f"Direction: {analysis['direction']}")
                info(f"Action: {analysis['action']}")
                info(f"Confidence: {analysis['confidence']}%")
                info(f"Analysis: {analysis['analysis']}")
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
            try:
                self.run_monitoring_cycle()
                info(f"Sleeping for {CHECK_INTERVAL_MINUTES} minutes")
                time.sleep(CHECK_INTERVAL_MINUTES * 60)
                
            except KeyboardInterrupt:
                info("Chart Analysis Agent shutting down gracefully")
                break
            except Exception as e:
                error(f"Error in main loop: {str(e)}")
                time.sleep(60)  # Sleep for a minute before retrying

if __name__ == "__main__":
    # Create and run the agent
    info("Chart Analysis Agent Starting Up")
    info("Monitoring symbols: " + ', '.join(SYMBOLS))
    agent = ChartAnalysisAgent()
    
    # Run the continuous monitoring cycle
    agent.run()