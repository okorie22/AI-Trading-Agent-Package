class DCAStakingTab(QWidget):
    """Tab for configuring and controlling DCA & Staking Agent with Chart Analysis integration"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
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
        
        # Create scroll area for all settings
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 1. AI Prompt Section (from Chart Analysis Agent)
        ai_group = QGroupBox("Chart Analysis AI Prompt")
        ai_layout = QVBoxLayout(ai_group)
        
        # AI Prompt
        self.prompt_text = QTextEdit()
        # This is the CHART_ANALYSIS_PROMPT from chart_analysis_agent.py
        prompt_text = """You must respond in exactly 3 lines:
Line 1: Only write BUY, SELL, or NOTHING
Line 2: One short reason why
Line 3: Only write "Confidence: X%" where X is 0-100

Analyze the chart data for {symbol} {timeframe}:

{chart_data}

Remember:
- Look for confluence between multiple indicators
- Volume should confirm price action
- Consider the timeframe context
"""
        self.prompt_text.setPlainText(prompt_text)
        self.prompt_text.setMinimumHeight(200)
        ai_layout.addWidget(self.prompt_text)
        
        scroll_layout.addWidget(ai_group)
        

        # 2. Chart Analysis Settings
        chart_group = QGroupBox("Chart Analysis Settings")
        chart_layout = QGridLayout(chart_group)

        # Check Interval
        chart_layout.addWidget(QLabel("Check Interval (minutes):"), 3, 0)
        self.check_interval = QSpinBox()
        self.check_interval.setRange(10, 1440)
        self.check_interval.setValue(10)  # Default from config.py
        self.check_interval.setToolTip("Interval between chart analysis cycles (10 minutes to 24 hours)")
        chart_layout.addWidget(self.check_interval, 3, 1)
                
        # Timeframes - Changed from QLineEdit to QComboBox
        chart_layout.addWidget(QLabel("Timeframe:"), 1, 0)  # Changed label to singular
        self.timeframes = QComboBox()
        self.timeframes.addItems(['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M'])
        self.timeframes.setCurrentText('4h')  # Default timeframe
        self.timeframes.setToolTip("Select the timeframe for chart analysis")
        chart_layout.addWidget(self.timeframes, 1, 1)
        
        # Lookback Bars
        chart_layout.addWidget(QLabel("Lookback Bars:"), 2, 0)
        self.lookback_bars = QSpinBox()
        self.lookback_bars.setRange(50, 500)
        self.lookback_bars.setValue(100)  # Default from config.py
        self.lookback_bars.setToolTip("Number of candles to analyze")
        chart_layout.addWidget(self.lookback_bars, 2, 1)
        
        
        # Indicators
        chart_layout.addWidget(QLabel("Indicators:"), 4, 0)
        self.indicators = QLineEdit("20EMA,50EMA,100EMA,200SMA,MACD,RSI,ATR")
        self.indicators.setPlaceholderText("available indicators 20EMA,50EMA,100EMA,200SMA,MACD,RSI,ATR")
        self.indicators.setToolTip("Comma-separated list of indicators to display")
        chart_layout.addWidget(self.indicators, 4, 1)
        
        # Chart Model Override
        chart_layout.addWidget(QLabel("Chart Model Override:"), 5, 0)
        self.model_override = QComboBox()
        self.model_override.addItems([
            "claude-3-haiku-20240307", 
            "claude-3-sonnet-20240229", 
            "claude-3-opus-20240229",
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4"
        ])
        self.model_override.setCurrentText("deepseek-reasoner")  # Default model for chart analysis
        chart_layout.addWidget(self.model_override, 5, 1)
        
        scroll_layout.addWidget(chart_group)
        
        # 3. DCA Settings
        dca_group = QGroupBox("DCA Settings")
        dca_layout = QGridLayout(dca_group)
        
        # DCA Interval
        dca_layout.addWidget(QLabel("DCA Interval (minutes):"), 1, 0)
        self.dca_interval = QSpinBox()
        self.dca_interval.setRange(60, 10080)  # 1 hour to 7 days
        self.dca_interval.setValue(720)  # Default from config.py (12 hours)
        dca_layout.addWidget(self.dca_interval, 1, 1)

        # Take Profit Percentage
        dca_layout.addWidget(QLabel("Take Profit (%):"), 2, 0)
        self.take_profit = QSpinBox()
        self.take_profit.setRange(10, 1000)
        self.take_profit.setValue(200)  # Default from config.py
        dca_layout.addWidget(self.take_profit, 2, 1)
        
        # Fixed DCA Amount
        dca_layout.addWidget(QLabel("Fixed DCA Amount (USD):"), 3, 0)
        self.fixed_dca_amount = QSpinBox()
        self.fixed_dca_amount.setRange(0, 1000)
        self.fixed_dca_amount.setValue(10)  # Default from config.py
        self.fixed_dca_amount.setToolTip("0 for dynamic DCA, or set a fixed amount")
        dca_layout.addWidget(self.fixed_dca_amount, 3, 1)

        # Staking Allocation
        dca_layout.addWidget(QLabel("Staking Allocation (%):"), 0, 0)
        self.staking_allocation = QSpinBox()
        self.staking_allocation.setRange(0, 100)
        self.staking_allocation.setValue(30)  # Default from config.py
        dca_layout.addWidget(self.staking_allocation, 0, 1)
        
        
        
        scroll_layout.addWidget(dca_group)
        
        # 4. Staking Settings
        staking_group = QGroupBox("Staking Settings")
        staking_layout = QGridLayout(staking_group)
        
        # Staking Mode
        staking_layout.addWidget(QLabel("Staking Mode:"), 0, 0)
        self.staking_mode = QComboBox()
        self.staking_mode.addItems(["separate", "auto_convert"])
        self.staking_mode.setCurrentText("separate")  # Default from config.py
        staking_layout.addWidget(self.staking_mode, 0, 1)
        
        # Auto-Convert Threshold
        staking_layout.addWidget(QLabel("Auto-Convert Threshold (USD):"), 1, 0)
        self.auto_convert_threshold = QSpinBox()
        self.auto_convert_threshold.setRange(1, 100)
        self.auto_convert_threshold.setValue(10)  # Default from config.py
        staking_layout.addWidget(self.auto_convert_threshold, 1, 1)
        
        # Min Conversion Amount
        staking_layout.addWidget(QLabel("Min Conversion Amount (USD):"), 2, 0)
        self.min_conversion_amount = QSpinBox()
        self.min_conversion_amount.setRange(1, 50)
        self.min_conversion_amount.setValue(5)  # Default from config.py
        staking_layout.addWidget(self.min_conversion_amount, 2, 1)
        
        # Max Convert Percentage
        staking_layout.addWidget(QLabel("Max Convert Percentage (%):"), 3, 0)
        self.max_convert_percentage = QSpinBox()
        self.max_convert_percentage.setRange(1, 100)
        self.max_convert_percentage.setValue(25)  # Default from config.py
        staking_layout.addWidget(self.max_convert_percentage, 3, 1)
        
        # Staking Protocols
        staking_layout.addWidget(QLabel("Staking Protocols:"), 4, 0)
        self.staking_protocols = QLineEdit("marinade,jito")  # Default from config.py
        self.staking_protocols.setToolTip("Comma-separated list of supported staking protocols")
        staking_layout.addWidget(self.staking_protocols, 4, 1)
        
        scroll_layout.addWidget(staking_group)
        
                # 5. Token Mapping
        token_group = QGroupBox("DCA Monitor Tokens")
        token_layout = QVBoxLayout(token_group)
        
        token_layout.addWidget(QLabel("Token Map (Solana address : symbol,hyperliquid_symbol):"))
        self.token_map = QTextEdit()
        # Default from config.py TOKEN_MAP
        default_tokens = """9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump: FART,FARTCOIN
HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC: AI16Z,AI16Z
So11111111111111111111111111111111111111112: SOL,SOL"""
        self.token_map.setPlainText(default_tokens)
        self.token_map.setMaximumHeight(150)
        token_layout.addWidget(self.token_map)
        
        scroll_layout.addWidget(token_group)
        
        # Add save button
        save_button = NeonButton("Save DCA/Staking Configuration", CyberpunkColors.SUCCESS)
        save_button.clicked.connect(self.save_config)
        scroll_layout.addWidget(save_button)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
    def save_config(self):
        """Save the configuration to a file or update global variables"""
        try:
            # Update config.py with DCA/Staking settings
            config_path = os.path.join(get_project_root(), 'src', 'config.py') 

            # Read existing config file
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # Update DCA/Staking values in the config content
            config_content = self.update_config_value(config_content, "STAKING_ALLOCATION_PERCENTAGE", str(self.staking_allocation.value()))
            config_content = self.update_config_value(config_content, "DCA_INTERVAL_MINUTES", str(self.dca_interval.value()))
            config_content = self.update_config_value(config_content, "TAKE_PROFIT_PERCENTAGE", str(self.take_profit.value()))
            config_content = self.update_config_value(config_content, "FIXED_DCA_AMOUNT", str(self.fixed_dca_amount.value()))
            
            # Update Chart Analysis settings - Now using single timeframe from dropdown
            timeframes_text = self.timeframes.currentText()
            timeframes_value = f"['{timeframes_text}']"  # Single timeframe in list
            config_content = self.update_config_value(config_content, "TIMEFRAMES", timeframes_value)
            config_content = self.update_config_value(config_content, "LOOKBACK_BARS", str(self.lookback_bars.value()))
            config_content = self.update_config_value(config_content, "CHECK_INTERVAL_MINUTES", str(self.check_interval.value()))
            
            # Update Staking settings
            config_content = self.update_config_value(config_content, "STAKING_MODE", f'"{self.staking_mode.currentText()}"')
            config_content = self.update_config_value(config_content, "AUTO_CONVERT_THRESHOLD", str(self.auto_convert_threshold.value()))
            config_content = self.update_config_value(config_content, "MIN_CONVERSION_AMOUNT", str(self.min_conversion_amount.value()))
            config_content = self.update_config_value(config_content, "MAX_CONVERT_PERCENTAGE", str(self.max_convert_percentage.value()))
            protocols_text = self.staking_protocols.text()
            protocols_list = protocols_text.split(',')
            protocols_formatted = '", "'.join(protocols_list)
            protocols_value = f'["{protocols_formatted}"]'
            config_content = self.update_config_value(config_content, "STAKING_PROTOCOLS", protocols_value)
            
            # Parse and update TOKEN_MAP
            token_map_lines = self.token_map.toPlainText().strip().split('\n')
            token_map_dict = {}
            
            for line in token_map_lines:
                if ':' in line:
                    address, symbols = line.split(':', 1)
                    address = address.strip()
                    symbols = symbols.strip()
                    if ',' in symbols:
                        symbol, hl_symbol = symbols.split(',', 1)
                        token_map_dict[address] = (symbol.strip(), hl_symbol.strip())
            
            # Update TOKEN_MAP
            token_map_str = "TOKEN_MAP = {\n"
            for address, (symbol, hl_symbol) in token_map_dict.items():
                token_map_str += f"    '{address}': ('{symbol}', '{hl_symbol}'),\n"
            token_map_str += "}"
            
            # Update config_content with TOKEN_MAP
            config_content = self.update_token_map(config_content, "TOKEN_MAP", token_map_str)
            
            # Then update DCA_MONITORED_TOKENS
            dca_tokens_str = "list(TOKEN_MAP.keys())"  # Use this reference to avoid duplication
            config_content = self.update_config_value(config_content, "DCA_MONITORED_TOKENS", dca_tokens_str)
            
            # Update prompt in config.py
            prompt_text = self.prompt_text.toPlainText()
            config_content = self.update_config_value(config_content, "CHART_ANALYSIS_PROMPT", f'"""\n{prompt_text}\n"""')
            config_content = self.update_config_value(config_content, "CHART_MODEL_OVERRIDE", f'"{self.model_override.currentText()}"')
            
            # Write the file once after all changes
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            # Reload the configuration module to apply changes immediately
            import sys
            import importlib
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            try:
                from src import config
                importlib.reload(config)
            except Exception as e:
                print(f"Warning: Could not reload configuration module: {str(e)}")
            
            # Silently restart relevant agents in the background
            main_window = self.parent().parent()
            if main_window and hasattr(main_window, 'restart_agent'):
                main_window.console.append_message("Configuration saved. Applying changes to DCA/Staking system...", "system")
                # Restart both related agents silently
                main_window.restart_agent("dca_staking")
                main_window.restart_agent("chart_analysis")
            
            # Simple notification that the configuration has been saved
            QMessageBox.information(self, "Saved", "DCA/Staking configuration has been updated.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
            
    def update_config_value(self, content, key, value, multiline=False):
        """Helper function to update a value in the config file content"""
        import re
        if multiline:
            # Pattern for multiline content (dictionaries, lists, or triple-quoted strings)
            pattern = rf"{key}\s*=\s*(?:{{[^}}]*}}|\[[^\]]*\]|\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?''')"
            replacement = f"{key} = {value}"
            # Use re.DOTALL to make . match newlines, and make sure to include all of the content
            return re.sub(pattern, replacement, content, flags=re.DOTALL)
        else:
            # For simple single-line values
            pattern = rf"{key}\s*=\s*[^\n]*"
            replacement = f"{key} = {value}"
            return re.sub(pattern, replacement, content)
    
    def update_token_map(self, content, key, value):
        """Special handling for TOKEN_MAP and similar complex structures"""
        import re
        # More specific pattern for TOKEN_MAP
        pattern = rf"{key}\s*=\s*TOKEN_MAP\s*=\s*{{[\s\S]*?}}"
        if re.search(pattern, content, re.DOTALL):
            return re.sub(pattern, f"{key} = {value}", content, flags=re.DOTALL)
        
        # Regular pattern as fallback
        pattern = rf"{key}\s*=\s*{{[\s\S]*?}}"
        return re.sub(pattern, f"{key} = {value}", content, flags=re.DOTALL)
    