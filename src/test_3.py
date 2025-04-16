class DCAStakingTab(QWidget):
    """Tab for configuring and controlling DCA & Staking Agent with Chart Analysis integration"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Import settings before setup_ui
        try:
            # Load DCA & Staking settings from config
            from src.config import (STAKING_ALLOCATION_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, 
                                   FIXED_DCA_AMOUNT, USE_DYNAMIC_ALLOCATION, 
                                   DCA_INTERVAL_MINUTES, DCA_INTERVAL_UNIT, DCA_INTERVAL_VALUE,
                                   DCA_RUN_AT_ENABLED, DCA_RUN_AT_TIME,
                                   STAKING_MODE, AUTO_CONVERT_THRESHOLD, MIN_CONVERSION_AMOUNT,
                                   MAX_CONVERT_PERCENTAGE, STAKING_PROTOCOLS,
                                   CHART_INTERVAL_UNIT, CHART_INTERVAL_VALUE,
                                   CHART_RUN_AT_ENABLED, CHART_RUN_AT_TIME,
                                   TIMEFRAMES, LOOKBACK_BARS, CHART_INDICATORS,
                                   CHART_STYLE, CHART_VOLUME_PANEL, ENABLE_FIBONACCI, FIBONACCI_LEVELS,
                                   FIBONACCI_LOOKBACK_PERIODS, YIELD_OPTIMIZATION_INTERVAL,
                                   YIELD_OPTIMIZATION_INTERVAL_UNIT, YIELD_OPTIMIZATION_INTERVAL_VALUE,
                                   YIELD_OPTIMIZATION_RUN_AT_ENABLED, YIELD_OPTIMIZATION_RUN_AT_TIME,
                                   CHART_ANALYSIS_PROMPT, DCA_AI_PROMPT, TOKEN_MAP, DCA_MONITORED_TOKENS)
                                   
            # Store config values
            self.staking_allocation_value = STAKING_ALLOCATION_PERCENTAGE
            self.take_profit_value = TAKE_PROFIT_PERCENTAGE
            self.fixed_dca_amount_value = FIXED_DCA_AMOUNT
            self.use_dynamic_allocation_value = USE_DYNAMIC_ALLOCATION
            self.dca_interval_minutes_value = DCA_INTERVAL_MINUTES
            self.dca_interval_unit_value = DCA_INTERVAL_UNIT
            self.dca_interval_value_value = DCA_INTERVAL_VALUE
            self.dca_run_at_enabled_value = DCA_RUN_AT_ENABLED
            self.dca_run_at_time_value = DCA_RUN_AT_TIME
            
            self.staking_mode_value = STAKING_MODE
            self.auto_convert_threshold_value = AUTO_CONVERT_THRESHOLD
            self.min_conversion_amount_value = MIN_CONVERSION_AMOUNT
            self.max_convert_percentage_value = MAX_CONVERT_PERCENTAGE
            self.staking_protocols_value = STAKING_PROTOCOLS
            
            self.chart_interval_unit_value = CHART_INTERVAL_UNIT
            self.chart_interval_value_value = CHART_INTERVAL_VALUE
            self.chart_run_at_enabled_value = CHART_RUN_AT_ENABLED
            self.chart_run_at_time_value = CHART_RUN_AT_TIME
            
            self.timeframes_value = TIMEFRAMES
            self.lookback_bars_value = LOOKBACK_BARS
            self.chart_indicators_value = CHART_INDICATORS
            self.chart_style_value = CHART_STYLE
            self.chart_volume_panel_value = CHART_VOLUME_PANEL
            
            self.enable_fibonacci_value = ENABLE_FIBONACCI
            self.fibonacci_levels_value = FIBONACCI_LEVELS
            self.fibonacci_lookback_value = FIBONACCI_LOOKBACK_PERIODS
            
            self.yield_optimization_interval_value = YIELD_OPTIMIZATION_INTERVAL
            self.yield_optimization_interval_unit_value = YIELD_OPTIMIZATION_INTERVAL_UNIT
            self.yield_optimization_interval_value_value = YIELD_OPTIMIZATION_INTERVAL_VALUE
            self.yield_optimization_run_at_enabled_value = YIELD_OPTIMIZATION_RUN_AT_ENABLED
            self.yield_optimization_run_at_time_value = YIELD_OPTIMIZATION_RUN_AT_TIME
            
            self.chart_analysis_prompt_value = CHART_ANALYSIS_PROMPT
            self.dca_ai_prompt_value = DCA_AI_PROMPT
            
        except ImportError as e:
            print(f"Error importing config settings: {e}")
            # Set default values if config import fails
            self.staking_allocation_value = 30
            self.take_profit_value = 200
            self.fixed_dca_amount_value = 10
            self.use_dynamic_allocation_value = False
            self.dca_interval_minutes_value = 1020
            self.dca_interval_unit_value = "Hour(s)"
            self.dca_interval_value_value = 17
            self.dca_run_at_enabled_value = True
            self.dca_run_at_time_value = "09:00"
            
            self.staking_mode_value = "separate"
            self.auto_convert_threshold_value = 10
            self.min_conversion_amount_value = 5
            self.max_convert_percentage_value = 25
            self.staking_protocols_value = ["marinade", "jito"]
            
            self.chart_interval_unit_value = "Hour(s)"
            self.chart_interval_value_value = 2
            self.chart_run_at_enabled_value = True
            self.chart_run_at_time_value = "09:00"
            
            self.timeframes_value = ['4h']
            self.lookback_bars_value = 100
            self.chart_indicators_value = ['20EMA', '50EMA', '100EMA', '200SMA', 'MACD', 'RSI']
            self.chart_style_value = 'yahoo'
            self.chart_volume_panel_value = True
            
            self.enable_fibonacci_value = True
            self.fibonacci_levels_value = [0.236, 0.382, 0.5, 0.618, 0.786]
            self.fibonacci_lookback_value = 60
            
            self.yield_optimization_interval_value = 432000
            self.yield_optimization_interval_unit_value = "Day(s)"
            self.yield_optimization_interval_value_value = 5
            self.yield_optimization_run_at_enabled_value = True
            self.yield_optimization_run_at_time_value = "09:00"
            
            # Default Chart Analysis Prompt
            self.chart_analysis_prompt_value = """
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

For optimal entry price calculation:
- For BUY: Look for support levels (EMAs, recent lows) and adjust using ATR
- For SELL: Look for resistance levels (EMAs, recent highs) and adjust using ATR
- If indicators are limited, use price action and volatility to establish entry zones
- Provide a specific price number, not a range

Make your own independent assessment.
"""
            
            # Default DCA & Staking AI Prompt
            self.dca_ai_prompt_value = """
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
            
        # Setup UI with loaded values
        self.setup_ui()
        
        try:
            # Set values in UI components
            self.staking_allocation.setValue(self.staking_allocation_value)
            self.take_profit.setValue(self.take_profit_value)
            self.fixed_dca_amount.setValue(self.fixed_dca_amount_value)
            self.dca_interval_value.setValue(self.dca_interval_value_value)
            self.dca_interval_unit.setCurrentText(self.dca_interval_unit_value)
            self.dca_run_at_enabled.setChecked(self.dca_run_at_enabled_value)
            
            # Parse and set DCA run at time
            if self.dca_run_at_time_value and ":" in self.dca_run_at_time_value:
                hour_str, minute_str = self.dca_run_at_time_value.split(":")
                hour = int(hour_str)
                minute = int(minute_str)
                self.dca_run_at_time.setTime(QTime(hour, minute))
                
            self.use_dynamic_allocation.setChecked(self.use_dynamic_allocation_value)
            self.toggle_fixed_dca_amount()
            
            # Set staking mode
            index = self.staking_mode.findText(self.staking_mode_value)
            if index >= 0:
                self.staking_mode.setCurrentIndex(index)
                
            # Set chart analysis settings
            self.chart_interval_value.setValue(self.chart_interval_value_value)
            self.chart_interval_unit.setCurrentText(self.chart_interval_unit_value)
            self.chart_run_at_enabled.setChecked(self.chart_run_at_enabled_value)
            
            # Parse and set chart run at time
            if self.chart_run_at_time_value and ":" in self.chart_run_at_time_value:
                hour_str, minute_str = self.chart_run_at_time_value.split(":")
                hour = int(hour_str)
                minute = int(minute_str)
                self.chart_run_at_time.setTime(QTime(hour, minute))
                
            # Set timeframes
            if isinstance(self.timeframes_value, list) and self.timeframes_value:
                if len(self.timeframes_value) > 0:
                    self.timeframes.setCurrentText(self.timeframes_value[0])
                
            self.lookback_bars.setValue(self.lookback_bars_value)
            
            # Set chart indicators
            if isinstance(self.chart_indicators_value, list) and self.chart_indicators_value:
                self.indicators.setText(",".join(self.chart_indicators_value))
                
            # Set chart style
            index = self.chart_style.findText(self.chart_style_value)
            if index >= 0:
                self.chart_style.setCurrentIndex(index)
                
            self.show_volume.setChecked(self.chart_volume_panel_value)
            self.enable_fibonacci.setChecked(self.enable_fibonacci_value)
            
            # Set fibonacci levels
            if isinstance(self.fibonacci_levels_value, list) and self.fibonacci_levels_value:
                self.fibonacci_levels.setText(", ".join([str(level) for level in self.fibonacci_levels_value]))
                
            self.fibonacci_lookback.setValue(self.fibonacci_lookback_value)
            
            # Set staking settings
            index = self.staking_mode.findText(self.staking_mode_value)
            if index >= 0:
                self.staking_mode.setCurrentIndex(index)
                
            self.auto_convert_threshold.setValue(self.auto_convert_threshold_value)
            self.min_conversion_amount.setValue(self.min_conversion_amount_value)
            self.max_convert_percentage.setValue(self.max_convert_percentage_value)
            
            # Set staking protocols
            if isinstance(self.staking_protocols_value, list) and self.staking_protocols_value:
                self.staking_protocols.setText(",".join(self.staking_protocols_value))
                
            # Set yield optimization settings
            # Instead of converting QSpinBox to int, we're using the stored value directly
            if hasattr(self, 'yield_optimization_interval_value_value'):
                if isinstance(self.yield_optimization_interval_value_value, (int, float, str)):
                    try:
                        # Make sure we have a numeric value
                        value = int(self.yield_optimization_interval_value_value)
                        self.yield_optimization_value.setValue(value)
                    except (ValueError, TypeError):
                        # Default to 1 if conversion fails
                        self.yield_optimization_value.setValue(1)
                else:
                    # Default to 1 if not a valid type
                    self.yield_optimization_value.setValue(1)
            else:
                # Default to 1 if attribute doesn't exist
                self.yield_optimization_value.setValue(1)
                
            if hasattr(self, 'yield_optimization_interval_unit_value'):
                self.yield_optimization_unit.setCurrentText(self.yield_optimization_interval_unit_value)
                
            if hasattr(self, 'yield_optimization_run_at_enabled_value'):
                self.yield_optimization_run_at_enabled.setChecked(self.yield_optimization_run_at_enabled_value)
            
            # Parse and set yield optimization run at time
            if self.yield_optimization_run_at_time_value and isinstance(self.yield_optimization_run_at_time_value, str) and ":" in self.yield_optimization_run_at_time_value:
                hour_str, minute_str = self.yield_optimization_run_at_time_value.split(":")
                hour = int(hour_str)
                minute = int(minute_str)
                self.yield_optimization_run_at_time.setTime(QTime(hour, minute))
            
            # Set prompt texts
            self.prompt_text.setPlainText(self.chart_analysis_prompt_value)
            self.staking_prompt_text.setPlainText(self.dca_ai_prompt_value)
            
            # Set advanced settings (if they exist in the UI)
            # These are being moved to another tab, so we should only try to set them if they still exist
            if hasattr(self, 'buy_confidence'):
                try:
                    self.buy_confidence.setValue(getattr(self, 'buy_confidence_value', 50))
                except Exception:
                    pass
                    
            if hasattr(self, 'sell_confidence'):
                try:
                    self.sell_confidence.setValue(getattr(self, 'sell_confidence_value', 75))
                except Exception:
                    pass
                    
            if hasattr(self, 'buy_multiplier'):
                try:
                    self.buy_multiplier.setValue(getattr(self, 'buy_multiplier_value', 1.5))
                except Exception:
                    pass
                    
            if hasattr(self, 'max_sell_percentage'):
                try:
                    self.max_sell_percentage.setValue(getattr(self, 'max_sell_percentage_value', 25))
                except Exception:
                    pass
            
            # Load token map from config
            try:
                # Format TOKEN_MAP into the text format expected by the UI
                token_map_lines = []
                for token_address, (symbol, hl_symbol) in TOKEN_MAP.items():
                    token_map_lines.append(f"{token_address}: {symbol},{hl_symbol}")
                self.token_map.setPlainText("\n".join(token_map_lines))
            except Exception as e:
                print(f"Error loading TOKEN_MAP from config: {e}")
                # Use default value already set in setup_ui
            
        except Exception as e:
            print(f"Error loading config settings: {e}")
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Set the main widget to expand with the window
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
            }}
            QScrollArea {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QComboBox {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 2px;
                padding: 2px;
                min-width: 635px;
            }}
            QSpinBox, QComboBox, QDoubleSpinBox, QTimeEdit {{
                min-width: 635px;
            }}
            QGroupBox {{
                border: 1px solid {CyberpunkColors.PRIMARY};
                margin-top: 1.5ex;
                color: {CyberpunkColors.PRIMARY};
            }}
            QLabel {{
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
            QCheckBox {{
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {CyberpunkColors.PRIMARY};
            }}
        """)
        
        # Create scroll area first - IMPORTANT: MUST be defined before it's used
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Create scroll widget and layout
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 1. AI Prompt Section (from Chart Analysis Agent)
        ai_group = QGroupBox("Chart Analysis AI Prompt")
        ai_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        ai_layout = QVBoxLayout(ai_group)
        
        # AI Prompt
        self.prompt_text = QTextEdit()
        self.prompt_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Use the prompt value loaded from config, or use the default if not available
        if hasattr(self, 'chart_analysis_prompt_value') and self.chart_analysis_prompt_value:
            self.prompt_text.setPlainText(self.chart_analysis_prompt_value)
        else:
            # Default Chart Analysis Prompt
            default_prompt = """
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

For optimal entry price calculation:
- For BUY: Look for support levels (EMAs, recent lows) and adjust using ATR
- For SELL: Look for resistance levels (EMAs, recent highs) and adjust using ATR
- If indicators are limited, use price action and volatility to establish entry zones
- Provide a specific price number, not a range

Make your own independent assessment.
"""
            self.prompt_text.setPlainText(default_prompt)
            
        self.prompt_text.setMinimumHeight(200)
        ai_layout.addWidget(self.prompt_text)
        
        scroll_layout.addWidget(ai_group)
        
        # Add Staking AI Prompt section
        staking_ai_group = QGroupBox("Staking AI Prompt")
        staking_ai_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        staking_ai_layout = QVBoxLayout(staking_ai_group)
        
        # Staking AI Prompt
        self.staking_prompt_text = QTextEdit()
        self.staking_prompt_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Use the staking prompt value loaded from config, or use the default if not available
        if hasattr(self, 'dca_ai_prompt_value') and self.dca_ai_prompt_value:
            self.staking_prompt_text.setPlainText(self.dca_ai_prompt_value)
        else:
            # Default DCA AI Prompt
            default_staking_prompt = """
You are Anarcho Capital Staking Bot, an advanced AI designed to analyze staking opportunities and optimize yield on the Solana blockchain.

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
            self.staking_prompt_text.setPlainText(default_staking_prompt)
            
        self.staking_prompt_text.setMinimumHeight(200)
        staking_ai_layout.addWidget(self.staking_prompt_text)
        
        scroll_layout.addWidget(staking_ai_group)
        
        # 2. Chart Analysis Settings
        chart_group = QGroupBox("Chart Analysis Settings")
        chart_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        chart_layout = QGridLayout(chart_group)
        
        # Chart Interval
        chart_layout.addWidget(QLabel("Chart Interval:"), 0, 0)
        chart_interval_widget = QWidget()
        chart_interval_layout = QHBoxLayout(chart_interval_widget)
        chart_interval_layout.setContentsMargins(0, 0, 0, 0)
        # Set minimum width on container widget
        chart_interval_widget.setMinimumWidth(635)
        chart_interval_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.chart_interval_value = QSpinBox()
        self.chart_interval_value.setRange(1, 30)
        self.chart_interval_value.setValue(2)
        self.chart_interval_value.setToolTip("Number of time units between chart analysis cycles")
        self.chart_interval_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.chart_interval_unit = QComboBox()
        self.chart_interval_unit.addItems(["Hour(s)", "Day(s)", "Week(s)", "Month(s)"])
        self.chart_interval_unit.setCurrentText("Hour(s)")
        self.chart_interval_unit.setToolTip("Time unit for chart analysis interval")
        self.chart_interval_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        chart_interval_layout.addWidget(self.chart_interval_value)
        chart_interval_layout.addWidget(self.chart_interval_unit)
        chart_layout.addWidget(chart_interval_widget, 0, 1)

        # Add scheduled time setting for Chart Analysis
        chart_layout.addWidget(QLabel("Run At Time:"), 1, 0)
        chart_time_widget = QWidget()
        chart_time_layout = QHBoxLayout(chart_time_widget)
        chart_time_layout.setContentsMargins(0, 0, 0, 0)
        # Set minimum width on container widget
        chart_time_widget.setMinimumWidth(635)
        chart_time_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.chart_run_at_enabled = QCheckBox("Enabled")
        self.chart_run_at_enabled.setChecked(getattr(sys.modules['src.config'], 'CHART_RUN_AT_ENABLED', False))
        self.chart_run_at_enabled.setToolTip("When enabled, chart analysis will run at the specified time")

        self.chart_run_at_time = QTimeEdit()
        self.chart_run_at_time.setDisplayFormat("HH:mm")
        self.chart_run_at_time.setTime(QTime(9, 0))
        self.chart_run_at_time.setToolTip("Time of day to run chart analysis")
        self.chart_run_at_time.setStyleSheet(f"""
            color: {CyberpunkColors.TEXT_LIGHT};
            background-color: {CyberpunkColors.BACKGROUND};
            selection-color: {CyberpunkColors.TEXT_WHITE};
            selection-background-color: {CyberpunkColors.PRIMARY};
        """)

        chart_time_layout.addWidget(self.chart_run_at_enabled)
        chart_time_layout.addWidget(self.chart_run_at_time)
        chart_layout.addWidget(chart_time_widget, 1, 1)

        # Timeframes
        chart_layout.addWidget(QLabel("Timeframe:"), 2, 0)
        self.timeframes = QComboBox()
        self.timeframes.addItems(['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M'])
        self.timeframes.setCurrentText('4h')
        self.timeframes.setToolTip("Select the timeframe for chart analysis")
        self.timeframes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        chart_layout.addWidget(self.timeframes, 2, 1)
        
        # Lookback Bars
        chart_layout.addWidget(QLabel("Lookback Bars:"), 3, 0)
        self.lookback_bars = QSpinBox()
        self.lookback_bars.setRange(50, 500)
        self.lookback_bars.setValue(100)
        self.lookback_bars.setToolTip("Number of candles to analyze")
        self.lookback_bars.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        chart_layout.addWidget(self.lookback_bars, 3, 1)
        
        # Indicators
        chart_layout.addWidget(QLabel("Indicators:"), 4, 0)
        self.indicators = QLineEdit("20EMA,50EMA,100EMA,200SMA,MACD,RSI,ATR")
        self.indicators.setPlaceholderText("available indicators 20EMA,50EMA,100EMA,200SMA,MACD,RSI,ATR")
        self.indicators.setToolTip("Comma-separated list of indicators to display")
        self.indicators.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        chart_layout.addWidget(self.indicators, 4, 1)
        
        # Chart Style
        chart_layout.addWidget(QLabel("Chart Style:"), 5, 0)
        self.chart_style = QComboBox()
        self.chart_style.addItems(['yahoo', 'tradingview', 'plotly', 'matplotlib'])
        self.chart_style.setCurrentText('yahoo')
        self.chart_style.setToolTip("Select the visual style for chart rendering")
        self.chart_style.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        chart_layout.addWidget(self.chart_style, 5, 1)
        
        # Show Volume
        volume_widget = QWidget()
        volume_layout = QHBoxLayout(volume_widget)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        # Set minimum width on container widget
        volume_widget.setMinimumWidth(635)
        volume_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.show_volume = QCheckBox("Show Volume Panel")
        self.show_volume.setChecked(True)
        self.show_volume.setToolTip("Display volume information in chart")
        self.show_volume.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        volume_layout.addWidget(self.show_volume)
        volume_layout.addStretch()
        
        chart_layout.addWidget(QLabel("Volume Display:"), 6, 0)
        chart_layout.addWidget(volume_widget, 6, 1)
        
        # Add Fibonacci retracement settings
        # Enable Fibonacci toggle
        fibonacci_enable_widget = QWidget()
        fibonacci_enable_layout = QHBoxLayout(fibonacci_enable_widget)
        fibonacci_enable_layout.setContentsMargins(0, 0, 0, 0)
        # Set minimum width on container widget
        fibonacci_enable_widget.setMinimumWidth(635)
        fibonacci_enable_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.enable_fibonacci = QCheckBox("Enable Fibonacci")
        self.enable_fibonacci.setChecked(True)
        self.enable_fibonacci.setToolTip("Use Fibonacci retracement for entry price calculations")
        self.enable_fibonacci.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        fibonacci_enable_layout.addWidget(self.enable_fibonacci)
        fibonacci_enable_layout.addStretch()
        
        chart_layout.addWidget(QLabel("Fibonacci Retracement:"), 7, 0)
        chart_layout.addWidget(fibonacci_enable_widget, 7, 1)
        
        # Fibonacci Levels
        chart_layout.addWidget(QLabel("Fibonacci Levels:"), 8, 0)
        self.fibonacci_levels = QLineEdit("0.236, 0.382, 0.5, 0.618, 0.786")
        self.fibonacci_levels.setToolTip("Comma-separated list of Fibonacci retracement levels")
        self.fibonacci_levels.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        chart_layout.addWidget(self.fibonacci_levels, 8, 1)
        
        # Fibonacci Lookback Periods
        chart_layout.addWidget(QLabel("Fibonacci Lookback Periods:"), 9, 0)
        self.fibonacci_lookback = QSpinBox()
        self.fibonacci_lookback.setRange(10, 200)
        self.fibonacci_lookback.setValue(60)
        self.fibonacci_lookback.setToolTip("Number of candles to look back for finding swing points")
        self.fibonacci_lookback.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        chart_layout.addWidget(self.fibonacci_lookback, 9, 1)
        
        scroll_layout.addWidget(chart_group)
        
        # 3. DCA Settings
        dca_group = QGroupBox("DCA Settings")
        dca_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        dca_layout = QGridLayout(dca_group)
        
        # DCA Interval
        dca_layout.addWidget(QLabel("DCA Interval:"), 0, 0)
        interval_widget = QWidget()
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        # Set minimum width on container widget
        interval_widget.setMinimumWidth(635)
        interval_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.dca_interval_value = QSpinBox()
        self.dca_interval_value.setRange(1, 30)
        self.dca_interval_value.setValue(12)
        self.dca_interval_value.setToolTip("Number of time units between DCA operations")
        self.dca_interval_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.dca_interval_unit = QComboBox()
        self.dca_interval_unit.addItems(["Hour(s)", "Day(s)", "Week(s)", "Month(s)"])
        self.dca_interval_unit.setCurrentText("Hour(s)")
        self.dca_interval_unit.setToolTip("Time unit for DCA interval")
        self.dca_interval_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        interval_layout.addWidget(self.dca_interval_value)
        interval_layout.addWidget(self.dca_interval_unit)
        dca_layout.addWidget(interval_widget, 0, 1)

        # Add scheduled time setting for DCA
        dca_layout.addWidget(QLabel("Run At Time:"), 1, 0)
        time_widget = QWidget()
        time_layout = QHBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        # Set minimum width on container widget
        time_widget.setMinimumWidth(635)
        time_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.dca_run_at_enabled = QCheckBox("Enabled")
        self.dca_run_at_enabled.setChecked(getattr(sys.modules['src.config'], 'DCA_RUN_AT_ENABLED', False))
        self.dca_run_at_enabled.setToolTip("When enabled, DCA will run at the specified time")

        self.dca_run_at_time = QTimeEdit()
        self.dca_run_at_time.setDisplayFormat("HH:mm")
        self.dca_run_at_time.setTime(QTime(9, 0))
        self.dca_run_at_time.setToolTip("Time of day to run DCA operations")
        self.dca_run_at_time.setStyleSheet(f"""
            color: {CyberpunkColors.TEXT_LIGHT};
            background-color: {CyberpunkColors.BACKGROUND};
            selection-color: {CyberpunkColors.TEXT_WHITE};
            selection-background-color: {CyberpunkColors.PRIMARY};
        """)

        time_layout.addWidget(self.dca_run_at_enabled)
        time_layout.addWidget(self.dca_run_at_time)
        dca_layout.addWidget(time_widget, 1, 1)

        # Staking Allocation
        dca_layout.addWidget(QLabel("Staking Allocation (%):"), 2, 0)
        self.staking_allocation = QSpinBox()
        self.staking_allocation.setRange(0, 100)
        self.staking_allocation.setValue(30)
        self.staking_allocation.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        dca_layout.addWidget(self.staking_allocation, 2, 1)
        
        # Take Profit Percentage
        dca_layout.addWidget(QLabel("Take Profit (%):"), 3, 0)
        self.take_profit = QSpinBox()
        self.take_profit.setRange(10, 1000)
        self.take_profit.setValue(200)
        self.take_profit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        dca_layout.addWidget(self.take_profit, 3, 1)
        
        # Fixed DCA Amount
        dca_layout.addWidget(QLabel("Fixed DCA Amount (USD):"), 4, 0)
        self.fixed_dca_amount = QSpinBox()
        self.fixed_dca_amount.setRange(0, 1000)
        self.fixed_dca_amount.setValue(10)
        self.fixed_dca_amount.setToolTip("0 for dynamic DCA, or set a fixed amount")
        self.fixed_dca_amount.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        dca_layout.addWidget(self.fixed_dca_amount, 4, 1)
        
        # Dynamic Allocation Toggle
        dca_layout.addWidget(QLabel("Use Dynamic Allocation:"), 5, 0)
        
        # Create a container widget similar to other checkbox containers
        dynamic_alloc_widget = QWidget()
        dynamic_alloc_layout = QHBoxLayout(dynamic_alloc_widget)
        dynamic_alloc_layout.setContentsMargins(0, 0, 0, 0)
        dynamic_alloc_widget.setMinimumWidth(635)
        dynamic_alloc_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.use_dynamic_allocation = QCheckBox()
        self.use_dynamic_allocation.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Try to load dynamic allocation setting from config
        try:
            from src.config import USE_DYNAMIC_ALLOCATION
            self.use_dynamic_allocation.setChecked(USE_DYNAMIC_ALLOCATION)
        except ImportError:
            self.use_dynamic_allocation.setChecked(False)
            
        self.use_dynamic_allocation.setToolTip("When enabled, uses dynamic allocation based on MAX_POSITION_PERCENTAGE instead of fixed amount")
        self.use_dynamic_allocation.stateChanged.connect(self.toggle_fixed_dca_amount)
        
        dynamic_alloc_layout.addWidget(self.use_dynamic_allocation)
        dynamic_alloc_layout.addStretch()
        
        dca_layout.addWidget(dynamic_alloc_widget, 5, 1)
        
        scroll_layout.addWidget(dca_group)
        
        # 4. Staking Settings
        staking_group = QGroupBox("Staking Settings")
        staking_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        staking_layout = QGridLayout(staking_group)
        
        # Staking Mode
        staking_layout.addWidget(QLabel("Staking Mode:"), 0, 0)
        self.staking_mode = QComboBox()
        self.staking_mode.addItems(["separate", "auto_convert"])
        self.staking_mode.setCurrentText("separate")
        self.staking_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        staking_layout.addWidget(self.staking_mode, 0, 1)
        
        # Auto-Convert Threshold
        staking_layout.addWidget(QLabel("Auto-Convert Threshold (USD):"), 1, 0)
        self.auto_convert_threshold = QSpinBox()
        self.auto_convert_threshold.setRange(1, 100)
        self.auto_convert_threshold.setValue(10)
        self.auto_convert_threshold.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        staking_layout.addWidget(self.auto_convert_threshold, 1, 1)
        
        # Min Conversion Amount
        staking_layout.addWidget(QLabel("Min Conversion Amount (USD):"), 2, 0)
        self.min_conversion_amount = QSpinBox()
        self.min_conversion_amount.setRange(1, 50)
        self.min_conversion_amount.setValue(5)
        self.min_conversion_amount.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        staking_layout.addWidget(self.min_conversion_amount, 2, 1)
        
        # Max Convert Percentage
        staking_layout.addWidget(QLabel("Max Convert Percentage (%):"), 3, 0)
        self.max_convert_percentage = QSpinBox()
        self.max_convert_percentage.setRange(1, 100)
        self.max_convert_percentage.setValue(25)
        self.max_convert_percentage.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        staking_layout.addWidget(self.max_convert_percentage, 3, 1)
        
        # Staking Protocols
        staking_layout.addWidget(QLabel("Staking Protocols:"), 4, 0)
        self.staking_protocols = QLineEdit("marinade,jito")
        self.staking_protocols.setToolTip("Comma-separated list of supported staking protocols")
        self.staking_protocols.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        staking_layout.addWidget(self.staking_protocols, 4, 1)
        
        # Yield Optimization Interval
        staking_layout.addWidget(QLabel("Yield Optimization Interval:"), 5, 0)
        yield_interval_widget = QWidget()
        yield_interval_layout = QHBoxLayout(yield_interval_widget)
        yield_interval_layout.setContentsMargins(0, 0, 0, 0)
        # Set minimum width on container widget
        yield_interval_widget.setMinimumWidth(635)
        yield_interval_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.yield_optimization_value = QSpinBox()
        self.yield_optimization_value.setRange(1, 30)
        self.yield_optimization_value.setValue(1)
        self.yield_optimization_value.setToolTip("How often to run yield optimization")
        self.yield_optimization_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.yield_optimization_unit = QComboBox()
        self.yield_optimization_unit.addItems(["Hour(s)", "Day(s)", "Week(s)", "Month(s)"])
        self.yield_optimization_unit.setCurrentText("Hour(s)")
        self.yield_optimization_unit.setToolTip("Time unit for yield optimization interval")
        self.yield_optimization_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        yield_interval_layout.addWidget(self.yield_optimization_value)
        yield_interval_layout.addWidget(self.yield_optimization_unit)
        staking_layout.addWidget(yield_interval_widget, 5, 1)

        # Add scheduled time setting for Yield Optimization
        staking_layout.addWidget(QLabel("Yield Optimization Run At Time:"), 6, 0)
        yield_time_widget = QWidget()
        yield_time_layout = QHBoxLayout(yield_time_widget)
        yield_time_layout.setContentsMargins(0, 0, 0, 0)
        # Set minimum width on container widget
        yield_time_widget.setMinimumWidth(635)
        yield_time_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.yield_optimization_run_at_enabled = QCheckBox("Enabled")
        self.yield_optimization_run_at_enabled.setChecked(self.yield_optimization_run_at_enabled_value)
        self.yield_optimization_run_at_enabled.setToolTip("When enabled, yield optimization will run at the specified time")

        self.yield_optimization_run_at_time = QTimeEdit()
        self.yield_optimization_run_at_time.setDisplayFormat("HH:mm")
        self.yield_optimization_run_at_time.setTime(QTime(9, 0))
        self.yield_optimization_run_at_time.setToolTip("Time of day to run yield optimization")
        self.yield_optimization_run_at_time.setStyleSheet(f"""
            color: {CyberpunkColors.TEXT_LIGHT};
            background-color: {CyberpunkColors.BACKGROUND};
            selection-color: {CyberpunkColors.TEXT_WHITE};
            selection-background-color: {CyberpunkColors.PRIMARY};
        """)

        yield_time_layout.addWidget(self.yield_optimization_run_at_enabled)
        yield_time_layout.addWidget(self.yield_optimization_run_at_time)
        staking_layout.addWidget(yield_time_widget, 6, 1)
        
        scroll_layout.addWidget(staking_group)
        
        # 5. Token Map
        token_group = QGroupBox("Token Map")
        token_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        token_layout = QVBoxLayout(token_group)
        
        # Token Map description
        token_map_label = QLabel("Map token addresses to symbols for display (format: address: symbol,headline_symbol)")
        token_layout.addWidget(token_map_label)
        
        # Token Map text area
        self.token_map = QTextEdit()
        self.token_map.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.token_map.setPlaceholderText("Enter token mapping, one per line\nFormat: <token_address>: <symbol>,<headline_symbol>")
        
        # Try to load TOKEN_MAP from config
        try:
            from src.config import TOKEN_MAP
            token_map_lines = []
            for token_address, (symbol, hl_symbol) in TOKEN_MAP.items():
                token_map_lines.append(f"{token_address}: {symbol},{hl_symbol}")
            self.token_map.setPlainText("\n".join(token_map_lines))
        except Exception as e:
            print(f"Error loading TOKEN_MAP from config: {e}")
            # Use empty value
            self.token_map.setPlainText("")
            
        self.token_map.setMinimumHeight(100)
        token_layout.addWidget(self.token_map)
        
        scroll_layout.addWidget(token_group)
        
        # Add save button
        save_button = NeonButton("Save DCA & Staking Configuration", CyberpunkColors.TERTIARY)
        save_button.clicked.connect(self.save_config)
        scroll_layout.addWidget(save_button)
        
        # Create scroll area to allow content to scroll both vertically and horizontally
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # Add spacer at the end of the scroll_layout to push content up
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        scroll_layout.addItem(spacer)
        
        # Ensure all QGroupBox widgets allow vertical expansion
        for i in range(scroll_layout.count()):
            item = scroll_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QGroupBox):
                item.widget().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Apply sizing policies to all layout widgets
        for row in range(chart_layout.rowCount()):
            item = chart_layout.itemAtPosition(row, 1)
            if item and item.widget():
                item.widget().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Apply sizing policies to DCA section
        for row in range(dca_layout.rowCount()):
            item = dca_layout.itemAtPosition(row, 1)
            if item and item.widget():
                item.widget().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Apply sizing policies to staking section
        for row in range(staking_layout.rowCount()):
            item = staking_layout.itemAtPosition(row, 1)
            if item and item.widget():
                item.widget().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Make the scroll area and scroll widget properly resizable
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Set the QVBoxLayout to stretch all items proportionally
        scroll_layout.setStretchFactor(ai_group, 1)
        scroll_layout.setStretchFactor(staking_ai_group, 1)
        scroll_layout.setStretchFactor(chart_group, 1)
        scroll_layout.setStretchFactor(dca_group, 1)
        scroll_layout.setStretchFactor(staking_group, 1)
        scroll_layout.setStretchFactor(token_group, 1)
        
    def toggle_fixed_dca_amount(self):
        """Enable or disable the fixed DCA amount field based on the dynamic allocation toggle"""
        self.fixed_dca_amount.setEnabled(not self.use_dynamic_allocation.isChecked())
        if self.use_dynamic_allocation.isChecked():
            self.fixed_dca_amount.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: rgba(224, 224, 224, 100);
                    border: 1px solid rgba(0, 255, 255, 100);
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)
        else:
            self.fixed_dca_amount.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: {CyberpunkColors.TEXT_LIGHT};
                    border: 1px solid {CyberpunkColors.PRIMARY};
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)
    
    def save_config(self):
        """Save the DCA & Staking configuration to config.py"""
        try:
            # Get correct path to config.py
            config_path = os.path.join(get_project_root(), 'src', 'config.py')
            
            # Read existing config file
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # Update DCA/Staking values in the config content
            config_content = self.collect_config(config_content)
            
            # Write updated config back to file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            # Update main.py to always match config.py values for DCA agent
            try:
                import re
                main_py_path = os.path.join(get_project_root(), 'src', 'main.py')
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    main_content = f.read()
                    
                # Update the DCA agent interval in ACTIVE_AGENTS to match config.py
                pattern = r"'dca':\s*{\s*'active':\s*True,\s*'interval':\s*\d+"
                
                # Convert interval from UI to minutes for the agent
                interval_value = self.dca_interval_value.value()
                interval_unit = self.dca_interval_unit.currentText()
                
                # Convert to minutes based on unit
                if interval_unit == "Hour(s)":
                    minutes = interval_value * 60
                elif interval_unit == "Day(s)":
                    minutes = interval_value * 24 * 60
                elif interval_unit == "Week(s)":
                    minutes = interval_value * 7 * 24 * 60
                elif interval_unit == "Month(s)":
                    minutes = interval_value * 30 * 24 * 60  # Approximation
                
                replacement = f"'dca': {{'active': True, 'interval': {minutes}"
                main_content = re.sub(pattern, replacement, main_content)
                
                # Update the chart analysis agent interval in ACTIVE_AGENTS
                chart_pattern = r"'chart_analysis':\s*{\s*'active':\s*True,\s*'interval':\s*\d+"
                
                # Convert chart interval from UI to minutes
                chart_interval_value = self.chart_interval_value.value()
                chart_interval_unit = self.chart_interval_unit.currentText()
                
                # Convert to minutes based on unit
                if chart_interval_unit == "Hour(s)":
                    chart_minutes = chart_interval_value * 60
                elif chart_interval_unit == "Day(s)":
                    chart_minutes = chart_interval_value * 24 * 60
                elif chart_interval_unit == "Week(s)":
                    chart_minutes = chart_interval_value * 7 * 24 * 60
                elif chart_interval_unit == "Month(s)":
                    chart_minutes = chart_interval_value * 30 * 24 * 60  # Approximation
                
                chart_replacement = f"'chart_analysis': {{'active': True, 'interval': {chart_minutes}"
                main_content = re.sub(chart_pattern, chart_replacement, main_content)
                
                # Save changes to main.py
                with open(main_py_path, 'w', encoding='utf-8') as f:
                    f.write(main_content)
                    
            except Exception as e:
                print(f"Warning: Could not update DCA & Chart Analysis settings in main.py: {str(e)}")
                # Continue anyway - the settings in config.py are still updated
            
            # Force reload config module to apply changes immediately
            import sys
            import importlib
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            try:
                from src import config
                importlib.reload(config)
            except Exception as e:
                print(f"Warning: Could not reload configuration module: {str(e)}")
            
            # Update chart_analysis and dca prompts
            try:
                # Update chart analysis prompt
                chart_agent_path = os.path.join(get_project_root(), 'src', 'agents', 'chart_analysis_agent.py')
                if os.path.exists(chart_agent_path):
                    with open(chart_agent_path, 'r', encoding='utf-8') as f:
                        chart_agent_content = f.read()
                    
                    # Create prompt text with proper escaping
                    prompt_text = self.prompt_text.toPlainText().strip()
                    
                    # Update the CHART_ANALYSIS_PROMPT in chart_analysis_agent.py
                    import re
                    chart_agent_content = re.sub(r'CHART_ANALYSIS_PROMPT\s*=\s*"""[\s\S]*?"""', f'CHART_ANALYSIS_PROMPT = """\n{prompt_text}\n"""', chart_agent_content, flags=re.DOTALL)
                    
                    with open(chart_agent_path, 'w', encoding='utf-8') as f:
                        f.write(chart_agent_content)
                
                # Update DCA staking prompt
                dca_agent_path = os.path.join(get_project_root(), 'src', 'agents', 'dca_staking_agent.py')
                if os.path.exists(dca_agent_path):
                    with open(dca_agent_path, 'r', encoding='utf-8') as f:
                        dca_agent_content = f.read()
                    
                    # Create prompt text with proper escaping
                    staking_prompt_text = self.staking_prompt_text.toPlainText().strip()
                    
                    # Update the DCA_AI_PROMPT in dca_staking_agent.py
                    dca_agent_content = re.sub(r'DCA_AI_PROMPT\s*=\s*"""[\s\S]*?"""', f'DCA_AI_PROMPT = """\n{staking_prompt_text}\n"""', dca_agent_content, flags=re.DOTALL)
                    
                    with open(dca_agent_path, 'w', encoding='utf-8') as f:
                        f.write(dca_agent_content)
            except Exception as e:
                print(f"Warning: Could not update agent prompts: {str(e)}")
            
            # Restart the DCA and Chart Analysis agents for changes to take effect
            main_window = self.parent().parent()
            if main_window and hasattr(main_window, 'restart_agent'):
                main_window.console.append_message("Configuration saved. Applying changes to DCA & Staking Agent...", "system")
                main_window.restart_agent("dca")
                main_window.restart_agent("chart_analysis")
            
            # Simple notification that the configuration has been saved
            QMessageBox.information(self, "Saved", "DCA & Staking configuration has been updated.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
    
    def collect_config(self, config_content):
        """Collect DCA & staking settings without saving to file - used by global save function"""
        
        # Update dynamic allocation setting
        dynamic_allocation = "True" if self.use_dynamic_allocation.isChecked() else "False"
        config_content = self.update_config_value(config_content, "USE_DYNAMIC_ALLOCATION", dynamic_allocation)
        
        # Update staking allocation percentage
        config_content = self.update_config_value(config_content, "STAKING_ALLOCATION_PERCENTAGE", str(self.staking_allocation.value()))
        
        # Update take profit percentage
        config_content = self.update_config_value(config_content, "TAKE_PROFIT_PERCENTAGE", str(self.take_profit.value()))
        
        # Update fixed DCA amount
        config_content = self.update_config_value(config_content, "FIXED_DCA_AMOUNT", str(self.fixed_dca_amount.value()))
        
        # Update DCA interval
        dca_interval_value = self.dca_interval_value.value()
        dca_interval_unit = self.dca_interval_unit.currentText()
        
        config_content = self.update_config_value(config_content, "DCA_INTERVAL_VALUE", str(dca_interval_value))
        config_content = self.update_config_value(config_content, "DCA_INTERVAL_UNIT", f'"{dca_interval_unit}"')
        
        # Calculate and update DCA interval minutes based on unit selection
        minutes = dca_interval_value
        if dca_interval_unit == "Hour(s)":
            minutes *= 60
        elif dca_interval_unit == "Day(s)":
            minutes *= 1440  # 24 * 60
        elif dca_interval_unit == "Week(s)":
            minutes *= 10080  # 7 * 24 * 60
        elif dca_interval_unit == "Month(s)":
            minutes *= 43200  # 30 * 24 * 60
            
        config_content = self.update_config_value(config_content, "DCA_INTERVAL_MINUTES", str(minutes))
        
        # Update DCA run at time settings
        dca_run_at_enabled = "True" if self.dca_run_at_enabled.isChecked() else "False"
        config_content = self.update_config_value(config_content, "DCA_RUN_AT_ENABLED", dca_run_at_enabled)
        
        dca_run_at_time = self.dca_run_at_time.time().toString("HH:mm")
        config_content = self.update_config_value(config_content, "DCA_RUN_AT_TIME", f'"{dca_run_at_time}"')
        
        # Update yield optimization settings
        yield_optimization_value = self.yield_optimization_value.value()
        yield_optimization_unit = self.yield_optimization_unit.currentText()
        
        # Calculate seconds based on unit selection
        seconds = yield_optimization_value * 3600  # Default to hours
        if yield_optimization_unit == "Hour(s)":
            seconds = yield_optimization_value * 3600
        elif yield_optimization_unit == "Day(s)":
            seconds = yield_optimization_value * 86400  # 24 * 3600
        elif yield_optimization_unit == "Week(s)":
            seconds = yield_optimization_value * 604800  # 7 * 24 * 3600
            
        config_content = self.update_config_value(config_content, "YIELD_OPTIMIZATION_INTERVAL", str(seconds))
        config_content = self.update_config_value(config_content, "YIELD_OPTIMIZATION_INTERVAL_VALUE", str(yield_optimization_value))
        config_content = self.update_config_value(config_content, "YIELD_OPTIMIZATION_INTERVAL_UNIT", f'"{yield_optimization_unit}"')
        
        # Update yield optimization run at time settings
        yield_run_at_enabled = "True" if self.yield_optimization_run_at_enabled.isChecked() else "False"
        config_content = self.update_config_value(config_content, "YIELD_OPTIMIZATION_RUN_AT_ENABLED", yield_run_at_enabled)
        
        yield_run_at_time = self.yield_optimization_run_at_time.time().toString("HH:mm")
        config_content = self.update_config_value(config_content, "YIELD_OPTIMIZATION_RUN_AT_TIME", f'"{yield_run_at_time}"')
        
        # Update staking mode and related settings
        config_content = self.update_config_value(config_content, "STAKING_MODE", f"'{self.staking_mode.currentText()}'")
        config_content = self.update_config_value(config_content, "AUTO_CONVERT_THRESHOLD", str(self.auto_convert_threshold.value()))
        config_content = self.update_config_value(config_content, "MIN_CONVERSION_AMOUNT", str(self.min_conversion_amount.value()))
        config_content = self.update_config_value(config_content, "MAX_CONVERT_PERCENTAGE", str(self.max_convert_percentage.value()))
        
        # Update staking protocols
        staking_protocols_text = self.staking_protocols.text()
        staking_protocols_list = [p.strip() for p in staking_protocols_text.split(',') if p.strip()]
        staking_protocols_formatted = '", "'.join(staking_protocols_list)
        staking_protocols_value = f'["{staking_protocols_formatted}"]'
        config_content = self.update_config_value(config_content, "STAKING_PROTOCOLS", staking_protocols_value)
        
        # Update chart run at time settings
        chart_run_at_enabled = "True" if self.chart_run_at_enabled.isChecked() else "False"
        config_content = self.update_config_value(config_content, "CHART_RUN_AT_ENABLED", chart_run_at_enabled)
        
        chart_run_at_time = self.chart_run_at_time.time().toString("HH:mm")
        config_content = self.update_config_value(config_content, "CHART_RUN_AT_TIME", f'"{chart_run_at_time}"')
        
        # Update chart display settings
        timeframes_text = self.timeframes.currentText()
        timeframes_list = [tf.strip() for tf in timeframes_text.split(',') if tf.strip()]
        timeframes_formatted = "', '".join(timeframes_list)
        timeframes_value = f"['{timeframes_formatted}']"
        config_content = self.update_config_value(config_content, "TIMEFRAMES", timeframes_value)
        
        config_content = self.update_config_value(config_content, "LOOKBACK_BARS", str(self.lookback_bars.value()))
        
        # Update chart indicators
        indicators_text = self.indicators.text()
        indicators_list = [ind.strip() for ind in indicators_text.split(',') if ind.strip()]
        indicators_formatted = "', '".join(indicators_list)
        indicators_value = f"['{indicators_formatted}']"
        config_content = self.update_config_value(config_content, "CHART_INDICATORS", indicators_value)
        
        # Update chart style
        config_content = self.update_config_value(config_content, "CHART_STYLE", f"'{self.chart_style.currentText()}'")
        config_content = self.update_config_value(config_content, "CHART_VOLUME_PANEL", str(self.show_volume.isChecked()))
        
        # Update Fibonacci settings
        fibonacci_enabled = "True" if self.enable_fibonacci.isChecked() else "False"
        config_content = self.update_config_value(config_content, "ENABLE_FIBONACCI", fibonacci_enabled)
        
        # Parse and update Fibonacci levels
        fibonacci_levels_text = self.fibonacci_levels.text()
        fibonacci_levels_list = [float(level.strip()) for level in fibonacci_levels_text.split(',')]
        fibonacci_levels_str = str(fibonacci_levels_list)
        config_content = self.update_config_value(config_content, "FIBONACCI_LEVELS", fibonacci_levels_str)
        
        config_content = self.update_config_value(config_content, "FIBONACCI_LOOKBACK_PERIODS", str(self.fibonacci_lookback.value()))
        
        # Remove the buy/sell confidence threshold settings as they're handled in another tab
        # config_content = self.update_config_value(config_content, "BUY_CONFIDENCE_THRESHOLD", str(self.buy_confidence.value()))
        # config_content = self.update_config_value(config_content, "SELL_CONFIDENCE_THRESHOLD", str(self.sell_confidence.value()))
        # config_content = self.update_config_value(config_content, "BUY_MULTIPLIER", str(self.buy_multiplier.value()))
        # config_content = self.update_config_value(config_content, "MAX_SELL_PERCENTAGE", str(self.max_sell_percentage.value()))
        
        # Update chart interval settings
        chart_interval_value = self.chart_interval_value.value()
        chart_interval_unit = self.chart_interval_unit.currentText()
        
        config_content = self.update_config_value(config_content, "CHART_INTERVAL_VALUE", str(chart_interval_value))
        config_content = self.update_config_value(config_content, "CHART_INTERVAL_UNIT", f'"{chart_interval_unit}"')
        
        # Calculate and update check interval minutes
        minutes = chart_interval_value
        if chart_interval_unit == "Hour(s)":
            minutes *= 60
        elif chart_interval_unit == "Day(s)":
            minutes *= 1440  # 24 * 60
        elif chart_interval_unit == "Week(s)":
            minutes *= 10080  # 7 * 24 * 60
            
        config_content = self.update_config_value(config_content, "CHART_ANALYSIS_INTERVAL_MINUTES", str(minutes))
        
        # Save the AI prompts
        chart_analysis_prompt = self.prompt_text.toPlainText().strip()
        config_content = self.update_config_value(config_content, "CHART_ANALYSIS_PROMPT", chart_analysis_prompt, multiline=True)
        
        staking_prompt = self.staking_prompt_text.toPlainText().strip()
        config_content = self.update_config_value(config_content, "DCA_AI_PROMPT", staking_prompt, multiline=True)
        
        # Save the token map
        token_map_text = self.token_map.toPlainText()
        token_map_entries = token_map_text.strip().split('\n')
        
        token_map_str = "TOKEN_MAP = {\n"
        for entry in token_map_entries:
            if ':' in entry:
                address, symbols = entry.split(':', 1)
                address = address.strip()
                symbols = symbols.strip()
                if ',' in symbols:
                    token_symbol, hl_symbol = symbols.split(',', 1)
                    token_symbol = token_symbol.strip()
                    hl_symbol = hl_symbol.strip()
                    token_map_str += f"    '{address}': ('{token_symbol}', '{hl_symbol}'),\n"
                else:
                    # Handle case where only one symbol is provided
                    token_symbol = symbols.strip()
                    token_map_str += f"    '{address}': ('{token_symbol}', '{token_symbol}'),\n"
        token_map_str += "}"
        
        # Replace TOKEN_MAP in config.py
        import re
        pattern = r"TOKEN_MAP\s*=\s*TOKEN_MAP\s*=\s*\{[^\}]*\}"
        if re.search(pattern, config_content, re.DOTALL):
            config_content = re.sub(pattern, f"TOKEN_MAP = TOKEN_MAP = {token_map_str}", config_content, flags=re.DOTALL)
        else:
            pattern = r"TOKEN_MAP\s*=\s*\{[^\}]*\}"
            if re.search(pattern, config_content, re.DOTALL):
                config_content = re.sub(pattern, token_map_str, config_content, flags=re.DOTALL)
            else:
                config_content += f"\n\n{token_map_str}\n"
                
        # Also update DCA_MONITORED_TOKENS based on the token map
        address_list = []
        for entry in token_map_entries:
            if ':' in entry:
                address = entry.split(':', 1)[0].strip()
                address_list.append(address)
                
        # Ensure no duplicates in the list
        address_list = list(dict.fromkeys(address_list))
        
        # Create the DCA_MONITORED_TOKENS assignment
        dca_tokens_str = "DCA_MONITORED_TOKENS = [\n"
        for address in address_list:
            dca_tokens_str += f"    '{address}',\n"
        dca_tokens_str += "]"
        
        # Replace DCA_MONITORED_TOKENS in config.py
        pattern = r"DCA_MONITORED_TOKENS\s*=\s*\[[^\]]*\]"
        matches = re.findall(pattern, config_content, re.DOTALL)
        if matches and len(matches) >= 2:
            # If there are two occurrences, update both
            for _ in range(len(matches)):
                config_content = re.sub(pattern, dca_tokens_str, config_content, count=1, flags=re.DOTALL)
        elif matches:
            # Update the existing occurrence
            config_content = re.sub(pattern, dca_tokens_str, config_content, flags=re.DOTALL)
        else:
            # Add a new occurrence
            config_content += f"\n\n{dca_tokens_str}\n"
        
        # Also add the variant that references TOKEN_MAP in case that's being used
        config_content = re.sub(r"DCA_MONITORED_TOKENS\s*=\s*list\(TOKEN_MAP\.keys\(\)\)", 
                              "DCA_MONITORED_TOKENS = list(TOKEN_MAP.keys())", config_content)
        
        return config_content
        
    def update_config_value(self, content, key, value, multiline=False):
        """Helper function to update a value in the config file content"""
        import re
        
        # If this is a multiline value (like a prompt), handle differently
        if multiline:
            # Match the entire assignment including the triple-quoted string
            pattern = rf'{key}\s*=\s*"""[\s\S]*?"""'
            
            # For multiline values, clean up the input to prevent adding extra newlines
            if isinstance(value, str):
                # Strip whitespace but ensure exactly one newline before and after content
                cleaned_value = value.strip()
                replacement = f'{key} = """\n{cleaned_value}\n"""'
            else:
                replacement = f'{key} = {value}'
            
            if re.search(pattern, content, re.DOTALL):
                return re.sub(pattern, replacement, content, flags=re.DOTALL)
            else:
                # If the key doesn't exist, add it to the end of the file
                return f'{content}\n{key} = {replacement}'
        
        # Regular single-line value
        else:
            # Look for the key with optional whitespace
            pattern = rf'{key}\s*=\s*[^#\n]+'
            replacement = f'{key} = {value}'
            # Use regex to replace the value
            if re.search(pattern, content):
                return re.sub(pattern, replacement, content)
            else:
                # If the key doesn't exist, add it to the end of the file
                return f"{content}\n{replacement}"

    def toggle_interval_input(self, checked):
        """Enable or disable the update interval input based on continuous mode"""
        self.update_interval.setDisabled(checked)
        if checked:
            self.update_interval.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: rgba(224, 224, 224, 100);
                    border: 1px solid rgba(0, 255, 255, 100);
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)
        else:
            self.update_interval.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: {CyberpunkColors.TEXT_LIGHT};
                    border: 1px solid {CyberpunkColors.PRIMARY};
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)
            
    def toggle_filter_mode(self, checked):
        """Enable or disable the filter mode dropdown based on the filter mode enabled checkbox"""
        self.filter_mode.setEnabled(checked)
        if checked:
            self.filter_mode.setStyleSheet("")
        else:
            self.filter_mode.setStyleSheet(f"""
                QComboBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: rgba(224, 224, 224, 100);
                    border: 1px solid rgba(0, 255, 255, 100);
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)

    def toggle_percentage_filter(self, checked):
        """Enable or disable the percentage threshold input based on the percentage filter checkbox"""
        self.percentage_threshold.setEnabled(checked)
        if checked:
            self.percentage_threshold.setStyleSheet("")
        else:
            self.percentage_threshold.setStyleSheet(f"""
                QDoubleSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: rgba(224, 224, 224, 100);
                    border: 1px solid rgba(0, 255, 255, 100);
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)
    
    def toggle_amount_filter(self, checked):
        """Enable or disable the amount threshold input based on the amount filter checkbox"""
        self.amount_threshold.setEnabled(checked)
        if checked:
            self.amount_threshold.setStyleSheet("")
        else:
            self.amount_threshold.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: rgba(224, 224, 224, 100);
                    border: 1px solid rgba(0, 255, 255, 100);
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)