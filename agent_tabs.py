class CopyBotTab(QWidget):
    """Tab for configuring and controlling CopyBot Agent"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Import settings before setup_ui
        try:
            # Load CopyBot runtime settings from config
            from src.config import COPYBOT_INTERVAL_MINUTES, PORTFOLIO_ANALYSIS_PROMPT
            from src.config import FILTER_MODE, ENABLE_PERCENTAGE_FILTER, PERCENTAGE_THRESHOLD
            from src.config import ENABLE_AMOUNT_FILTER, AMOUNT_THRESHOLD
            from src.config import ENABLE_ACTIVITY_FILTER, ACTIVITY_WINDOW_HOURS
            from src.config import API_SLEEP_SECONDS, API_TIMEOUT_SECONDS, API_MAX_RETRIES
            
            # Store config values
            self.interval_minutes = COPYBOT_INTERVAL_MINUTES
            self.analysis_prompt = PORTFOLIO_ANALYSIS_PROMPT
            self.filter_mode_val = FILTER_MODE
            self.pct_filter_enabled = ENABLE_PERCENTAGE_FILTER
            self.pct_threshold = PERCENTAGE_THRESHOLD
            self.amount_filter_enabled = ENABLE_AMOUNT_FILTER
            self.amount_threshold_val = AMOUNT_THRESHOLD
            self.activity_filter_enabled = ENABLE_ACTIVITY_FILTER
            self.activity_window = ACTIVITY_WINDOW_HOURS
            self.api_sleep_val = float(API_SLEEP_SECONDS)
            self.api_timeout_val = int(API_TIMEOUT_SECONDS)
            self.max_retries_val = int(API_MAX_RETRIES)
            
            # Load continuous mode if it exists, otherwise default to False
            try:
                from src.config import COPYBOT_CONTINUOUS_MODE
                self.continuous_mode = COPYBOT_CONTINUOUS_MODE
            except ImportError:
                self.continuous_mode = False
                
            # Load skip first run setting if it exists, otherwise default to True
            try:
                from src.config import COPYBOT_SKIP_ANALYSIS_ON_FIRST_RUN
                self.skip_analysis = COPYBOT_SKIP_ANALYSIS_ON_FIRST_RUN
            except ImportError:
                self.skip_analysis = True
                
        except ImportError as e:
            print(f"Error importing config settings: {e}")
            # Set default values if config import fails
            self.interval_minutes = 18
            self.continuous_mode = False
            self.skip_analysis = True
            self.filter_mode_val = "Dynamic"
            self.pct_filter_enabled = True
            self.pct_threshold = 0.1
            self.amount_filter_enabled = True
            self.amount_threshold_val = 5000
            self.activity_filter_enabled = False
            self.activity_window = 1
            self.api_sleep_val = 1.0
            self.api_timeout_val = 30
            self.max_retries_val = 5
            
            # Default portfolio analysis prompt
            self.analysis_prompt = """
You are Anarcho Capital's CopyBot Agent 🌙

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
        
        # Setup UI with loaded values
        self.setup_ui()
        
        # Initialize fields from config after UI setup
        try:
            # Set values in UI components
            self.update_interval.setValue(self.interval_minutes)
            self.run_mode.setChecked(self.continuous_mode)
            self.skip_first_run.setChecked(self.skip_analysis)
            
            # Set the prompt text from config
            self.prompt_text.setPlainText(self.analysis_prompt)
            
            # Set filter settings
            index = self.filter_mode.findText(self.filter_mode_val)
            if index >= 0:
                self.filter_mode.setCurrentIndex(index)
                
            self.percentage_filter.setChecked(self.pct_filter_enabled)
            self.percentage_threshold.setValue(float(self.pct_threshold))
            self.amount_filter.setChecked(self.amount_filter_enabled)
            self.amount_threshold.setValue(int(self.amount_threshold_val))
            self.activity_filter.setChecked(self.activity_filter_enabled)
            self.activity_window.setValue(int(self.activity_window))
            
            # Initialize the state of the interval input based on the loop mode
            self.toggle_interval_input(self.run_mode.isChecked())
            
        except Exception as e:
            print(f"Error loading config settings: {e}")
        
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
        
        # Create scroll area first - IMPORTANT: MUST be defined before it's used
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Create scroll widget and layout
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 1. AI Prompt Section
        ai_group = QGroupBox("AI Prompt")
        ai_layout = QVBoxLayout(ai_group)
        
        # AI Prompt - Create text editor but don't set text (will be loaded from config)
        self.prompt_text = QTextEdit()
        self.prompt_text.setMinimumHeight(200)
        ai_layout.addWidget(self.prompt_text)
        
        scroll_layout.addWidget(ai_group)
        
        # 2. Agent Runtime Configuration
        agent_group = QGroupBox("CobyBot Agent Runtime")
        agent_layout = QGridLayout(agent_group)
        
        # Update/Refresh Interval
        self.run_mode = QCheckBox("Loop Mode")
        self.run_mode.setToolTip("When enabled, CopyBot will run continuously instead of on a fixed schedule")
        agent_layout.addWidget(self.run_mode, 0, 0)
        
        # Add the new skip analysis checkbox on the first run (same row, column 1)
        self.skip_first_run = QCheckBox("Skip Analysis on First Run")
        self.skip_first_run.setToolTip("When enabled, CopyBot will only fetch tokens on the first run without analyzing or executing trades")
        agent_layout.addWidget(self.skip_first_run, 1, 0)
        
        agent_layout.addWidget(QLabel("CopyBot Interval (minutes):"), 2, 0)
        self.update_interval = QSpinBox()
        self.update_interval.setRange(1, 1440)  # 1 minute to 24 hours
        self.update_interval.setValue(5)  # Default from ACTIVE_AGENTS in main.py
        self.update_interval.setToolTip("Time between CopyBot runs (in minutes)")
        agent_layout.addWidget(self.update_interval, 2, 1)
        
        # Add this connection - it will disable the update_interval when continuous mode is checked
        self.run_mode.toggled.connect(self.toggle_interval_input)
        
        # API Request Configuration
        agent_layout.addWidget(QLabel("Sleep Between API Calls (seconds):"), 3, 0)
        self.api_sleep = QDoubleSpinBox()
        self.api_sleep.setRange(0.1, 10)
        self.api_sleep.setValue(self.api_sleep_val)  # Set from config
        self.api_sleep.setSingleStep(0.1)
        self.api_sleep.setToolTip("Delay between API calls to avoid rate limits")
        agent_layout.addWidget(self.api_sleep, 3, 1)
        
        agent_layout.addWidget(QLabel("API Timeout (seconds):"), 4, 0)
        self.api_timeout = QSpinBox()
        self.api_timeout.setRange(5, 60)
        self.api_timeout.setValue(self.api_timeout_val)  # Set from config
        self.api_timeout.setToolTip("Maximum time to wait for API responses")
        agent_layout.addWidget(self.api_timeout, 4, 1)
        
        agent_layout.addWidget(QLabel("Max API Retries:"), 5, 0)
        self.max_retries = QSpinBox()
        self.max_retries.setRange(1, 10)
        self.max_retries.setValue(self.max_retries_val)  # Set from config
        self.max_retries.setToolTip("Maximum number of retry attempts for failed API calls")
        agent_layout.addWidget(self.max_retries, 5, 1)
        
        scroll_layout.addWidget(agent_group)
        
        # Token Tracking Filter Settings
        filter_group = QGroupBox("Token Tracking Filter Settings")
        filter_layout = QGridLayout(filter_group)
        
        # Filter Mode
        filter_layout.addWidget(QLabel("Filter Mode:"), 0, 0)
        self.filter_mode_enabled = QCheckBox("Enable Filter Mode")
        self.filter_mode_enabled.setChecked(True)  # Default enabled
        filter_layout.addWidget(self.filter_mode_enabled, 0, 1)
        
        self.filter_mode = QComboBox()
        self.filter_mode.addItems(["Dynamic", "Monitored Tokens"])
        self.filter_mode.setCurrentText(FILTER_MODE)  # Set from config
        self.filter_mode.setToolTip("Dynamic: Filter tokens based on percentage of portfolio\nMonitored Tokens: Only include tokens from list")
        filter_layout.addWidget(self.filter_mode, 1, 1)
        filter_layout.addWidget(QLabel("Mode:"), 1, 0)
        
        # Percentage Filter
        self.percentage_filter = QCheckBox("Enable Percentage Filter")
        self.percentage_filter.setChecked(ENABLE_PERCENTAGE_FILTER)
        filter_layout.addWidget(self.percentage_filter, 2, 0)
        
        self.percentage_threshold = QDoubleSpinBox()
        self.percentage_threshold.setRange(0.1, 50.0)
        self.percentage_threshold.setValue(PERCENTAGE_THRESHOLD)
        self.percentage_threshold.setSuffix("%")
        self.percentage_threshold.setToolTip("Minimum percentage of wallet's total portfolio value")
        filter_layout.addWidget(self.percentage_threshold, 2, 1)
        
        # Amount Filter
        self.amount_filter = QCheckBox("Enable Amount Filter")
        self.amount_filter.setChecked(ENABLE_AMOUNT_FILTER)
        filter_layout.addWidget(self.amount_filter, 3, 0)
        
        self.amount_threshold = QSpinBox()
        self.amount_threshold.setRange(1, 1000000)
        self.amount_threshold.setValue(AMOUNT_THRESHOLD)
        self.amount_threshold.setSuffix(" USD")
        self.amount_threshold.setToolTip("Minimum USD value of a token to be considered")
        filter_layout.addWidget(self.amount_threshold, 3, 1)
        
        # Activity Filter
        self.activity_filter = QCheckBox("Filter by Recent Activity")
        self.activity_filter.setChecked(ENABLE_ACTIVITY_FILTER)
        filter_layout.addWidget(self.activity_filter, 4, 0)
        
        self.activity_window = QSpinBox()
        self.activity_window.setRange(1, 72)
        self.activity_window.setValue(ACTIVITY_WINDOW_HOURS)
        self.activity_window.setSuffix(" hours")
        self.activity_window.setToolTip("Only track tokens with activity in this time window")
        filter_layout.addWidget(self.activity_window, 4, 1)
        
        # Connect filter toggles to enable/disable their respective inputs
        self.filter_mode_enabled.toggled.connect(self.toggle_filter_mode)
        self.percentage_filter.toggled.connect(self.toggle_percentage_filter)
        self.amount_filter.toggled.connect(self.toggle_amount_filter)
        self.activity_filter.toggled.connect(self.toggle_activity_filter)
        
        # Initialize the state of filter settings
        self.toggle_filter_mode(self.filter_mode_enabled.isChecked())
        self.toggle_percentage_filter(self.percentage_filter.isChecked())
        self.toggle_amount_filter(self.amount_filter.isChecked())
        self.toggle_activity_filter(self.activity_filter.isChecked())
        
        scroll_layout.addWidget(filter_group)
        
        # Add Wallets to Track section
        wallets_group = QGroupBox("Wallets to Track")
        wallets_layout = QVBoxLayout(wallets_group)
        
        # Wallet Addresses
        wallets_label = QLabel("Wallet Addresses (one per line):")
        wallets_layout.addWidget(wallets_label)
        
        self.wallets_to_track = QTextEdit()
        self.wallets_to_track.setPlaceholderText("Enter wallet addresses to track, one per line")
        
        # Load wallet addresses from config
        from src.scripts.token_list_tool import WALLETS_TO_TRACK
        wallets_text = "\n".join(WALLETS_TO_TRACK)
        self.wallets_to_track.setPlainText(wallets_text)
        
        self.wallets_to_track.setMinimumHeight(80)
        wallets_layout.addWidget(self.wallets_to_track)
        scroll_layout.addWidget(wallets_group)
        
        # Add Monitored Tokens section
        tokens_group = QGroupBox("Monitored Tokens")
        tokens_layout = QVBoxLayout(tokens_group)
        
        # Token Addresses
        tokens_label = QLabel("Token Addresses (one per line):")
        tokens_layout.addWidget(tokens_label)
        
        self.monitored_tokens = QTextEdit()
        self.monitored_tokens.setPlaceholderText("Enter token addresses to monitor, one per line")
        
        # Load monitored tokens from config
        from src.config import MONITORED_TOKENS
        tokens_text = "\n".join(MONITORED_TOKENS)
        self.monitored_tokens.setPlainText(tokens_text)
        
        self.monitored_tokens.setMinimumHeight(80)
        tokens_layout.addWidget(self.monitored_tokens)
        scroll_layout.addWidget(tokens_group)
        
        # Add Excluded Tokens section
        excluded_group = QGroupBox("Excluded Tokens")
        excluded_layout = QVBoxLayout(excluded_group)
        
        # Tokens to never trade
        excluded_label = QLabel("The following tokens are excluded from trading:")
        excluded_layout.addWidget(excluded_label)
        
        # Create a read-only text display for excluded tokens
        self.excluded_tokens_display = QTextEdit()
        self.excluded_tokens_display.setReadOnly(True)
        self.excluded_tokens_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(0, 0, 0, 180);
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 2px;
                padding: 5px;
            }}
        """)
        
        # Load excluded tokens from config, but clean up duplicates
        from src.config import EXCLUDED_TOKENS, USDC_ADDRESS, SOL_ADDRESS
        
        # Create a set of unique values for additional excluded tokens
        additional_tokens = []
        for token in EXCLUDED_TOKENS:
            # Skip USDC and SOL - they'll be displayed in the read-only field
            if token != USDC_ADDRESS and token != SOL_ADDRESS and token not in ["USDC_ADDRESS", "SOL_ADDRESS"]:
                additional_tokens.append(token)
        
        # Set the display for fixed excluded tokens (USDC and SOL only)
        excluded_text = "USDC: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v\n"
        excluded_text += "SOL: So11111111111111111111111111111111111111111"
        
        self.excluded_tokens_display.setPlainText(excluded_text)
        self.excluded_tokens_display.setMinimumHeight(80)
        excluded_layout.addWidget(self.excluded_tokens_display)
        
        # Additional tokens to exclude label
        additional_label = QLabel("Additional tokens to exclude:")
        excluded_layout.addWidget(additional_label)
        
        # Additional tokens text box - populate with the additional tokens found in config
        self.additional_excluded = QTextEdit()
        self.additional_excluded.setPlaceholderText("Enter additional token addresses to exclude")
        self.additional_excluded.setMaximumHeight(60)
        # Set the additional tokens from config
        if additional_tokens:
            self.additional_excluded.setPlainText("\n".join(additional_tokens))
        excluded_layout.addWidget(self.additional_excluded)
        
        # Note about SOL and USDC
        note_label = QLabel("Note: SOL and USDC are automatically excluded and cannot be traded.")
        note_label.setStyleSheet(f"color: {CyberpunkColors.WARNING}; font-weight: bold;")
        excluded_layout.addWidget(note_label)
        
        scroll_layout.addWidget(excluded_group)

        # Add save button
        save_button = NeonButton("Save CopyBot Configuration", CyberpunkColors.SUCCESS)
        save_button.clicked.connect(self.save_config)
        scroll_layout.addWidget(save_button)
        
        # Create scroll area
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
    def save_config(self):
        """Save the CopyBot configuration to config.py"""
        try:
            # Get correct path to config.py
            config_path = os.path.join(get_project_root(), 'src', 'config.py')
            
            # Read existing config file
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # Update CopyBot-specific values in the config content
            config_content = self.collect_config(config_content)
            
            # Write updated config back to file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            # Update main.py to always match config.py values
            try:
                import re
                main_py_path = os.path.join(get_project_root(), 'src', 'main.py')
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    main_content = f.read()
                    
                # Always update the copybot interval in ACTIVE_AGENTS to match config.py
                pattern = r"'copybot':\s*{\s*'active':\s*True,\s*'interval':\s*\d+"
                replacement = f"'copybot': {{'active': True, 'interval': {self.update_interval.value()}"
                main_content = re.sub(pattern, replacement, main_content)
                
                # Always update continuous mode check in main.py
                # Find the copybot check in the main while loop
                copybot_check_pattern = r"if \(copybot and \n\s*\(.*\)\):"
                copybot_check_replacement = f"if (copybot and \n                    (COPYBOT_CONTINUOUS_MODE or (current_time - last_run['copybot']).total_seconds() >= ACTIVE_AGENTS['copybot']['interval'] * 60)):"
                
                if re.search(copybot_check_pattern, main_content):
                    main_content = re.sub(copybot_check_pattern, copybot_check_replacement, main_content)
                
                # Update next run message for continuous mode
                copybot_next_run_pattern = r"next_run_time = \(current_time \+ timedelta\(minutes=ACTIVE_AGENTS\['copybot'\]\['interval'\]\)\)\.strftime\('%H:%M:%S'\)"
                copybot_next_run_replacement = "next_run_time = \"Continuous Mode\" if COPYBOT_CONTINUOUS_MODE else (current_time + timedelta(minutes=ACTIVE_AGENTS['copybot']['interval'])).strftime('%H:%M:%S')"
                
                if re.search(copybot_next_run_pattern, main_content):
                    main_content = re.sub(copybot_next_run_pattern, copybot_next_run_replacement, main_content)
                
                # Save changes to main.py
                with open(main_py_path, 'w', encoding='utf-8') as f:
                    f.write(main_content)
                    
            except Exception as e:
                print(f"Warning: Could not update copybot settings in main.py: {str(e)}")
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
            
            # Silently restart the agent in the background without asking
            main_window = self.parent().parent()
            if main_window and hasattr(main_window, 'restart_agent'):
                main_window.console.append_message("Configuration saved. Applying changes to CopyBot...", "system")
                main_window.restart_agent("copybot")
            
            # Simple notification that the configuration has been saved
            QMessageBox.information(self, "Saved", "CopyBot configuration has been updated.")
            
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
    
    def collect_config(self, config_content):
        """Collect CopyBot settings without saving to file - used by global save function"""
        # Portfolio Analysis Prompt
        prompt_text = self.prompt_text.toPlainText().strip()
        config_content = self.update_config_value(config_content, "PORTFOLIO_ANALYSIS_PROMPT", prompt_text, multiline=True)
            
        # Update filter settings
        config_content = self.update_config_value(config_content, "FILTER_MODE", f'"{self.filter_mode.currentText()}"')
        config_content = self.update_config_value(config_content, "ENABLE_PERCENTAGE_FILTER", str(self.percentage_filter.isChecked()))
        config_content = self.update_config_value(config_content, "PERCENTAGE_THRESHOLD", str(self.percentage_threshold.value()))
        config_content = self.update_config_value(config_content, "ENABLE_AMOUNT_FILTER", str(self.amount_filter.isChecked()))
        config_content = self.update_config_value(config_content, "AMOUNT_THRESHOLD", str(self.amount_threshold.value()))
        config_content = self.update_config_value(config_content, "ENABLE_ACTIVITY_FILTER", str(self.activity_filter.isChecked()))
        config_content = self.update_config_value(config_content, "ACTIVITY_WINDOW_HOURS", str(self.activity_window.value()))
            
        # Update runtime mode
        config_content = self.update_config_value(config_content, "COPYBOT_CONTINUOUS_MODE", str(self.run_mode.isChecked()))
        config_content = self.update_config_value(config_content, "COPYBOT_INTERVAL_MINUTES", str(self.update_interval.value()))
        config_content = self.update_config_value(config_content, "COPYBOT_SKIP_ANALYSIS_ON_FIRST_RUN", str(self.skip_first_run.isChecked()))
        
        # Update API settings
        config_content = self.update_config_value(config_content, "API_SLEEP_SECONDS", str(self.api_sleep.value()))
        config_content = self.update_config_value(config_content, "API_TIMEOUT_SECONDS", str(self.api_timeout.value()))
        config_content = self.update_config_value(config_content, "API_MAX_RETRIES", str(self.max_retries.value()))
        
        # Update monitored tokens list
        tokens_text = self.monitored_tokens.toPlainText().strip()
        if tokens_text:
            tokens_list = [token.strip() for token in tokens_text.split('\n') if token.strip()]
            # Create the monitored tokens string
            monitored_tokens_str = "MONITORED_TOKENS = [\n"
            for token in tokens_list:
                monitored_tokens_str += f"    '{token}',\n"
            monitored_tokens_str += "]"
            
            # Update the config
            import re
            pattern = r"MONITORED_TOKENS\s*=\s*\[[^\]]*\]"
            if re.search(pattern, config_content, re.DOTALL):
                config_content = re.sub(pattern, monitored_tokens_str, config_content, flags=re.DOTALL)
            else:
                config_content += f"\n\n{monitored_tokens_str}\n"
        
        # Update excluded tokens list
        excluded_tokens_text = self.additional_excluded.toPlainText().strip()
        excluded_tokens_list = []
        if excluded_tokens_text:
            excluded_tokens_list = [token.strip() for token in excluded_tokens_text.split('\n') if token.strip()]
        
        # Update EXCLUDED_TOKENS in config.py
        from src.config import USDC_ADDRESS, SOL_ADDRESS
        
        # Make sure USDC and SOL are in the list
        excluded_tokens_str = "EXCLUDED_TOKENS = [USDC_ADDRESS, SOL_ADDRESS"
        for token in excluded_tokens_list:
            if token != USDC_ADDRESS and token != SOL_ADDRESS:
                excluded_tokens_str += f", '{token}'"
        excluded_tokens_str += "]"
        
        # Replace EXCLUDED_TOKENS in config.py
        import re
        pattern = r"EXCLUDED_TOKENS\s*=\s*\[[^\]]*\]"
        if re.search(pattern, config_content, re.DOTALL):
            config_content = re.sub(pattern, excluded_tokens_str, config_content, flags=re.DOTALL)
        else:
            config_content += f"\n\n{excluded_tokens_str}\n"
        
        # Update wallets to track
        wallets_text = self.wallets_to_track.toPlainText().strip()
        if wallets_text:
            wallet_list = [wallet.strip() for wallet in wallets_text.split('\n') if wallet.strip()]
            
            # Create the wallets string
            wallets_str = "WALLETS_TO_TRACK = [\n"
            for wallet in wallet_list:
                wallets_str += f"    \"{wallet}\",\n"
            wallets_str += "    # Add more wallets here as needed\n]"
            
            # Replace WALLETS_TO_TRACK in config.py
            import re
            pattern = r"WALLETS_TO_TRACK\s*=\s*WALLETS_TO_TRACK\s*=\s*\[[^\]]*\]"
            if re.search(pattern, config_content, re.DOTALL):
                config_content = re.sub(pattern, f"WALLETS_TO_TRACK = {wallets_str}", config_content, flags=re.DOTALL)
            else:
                pattern = r"WALLETS_TO_TRACK\s*=\s*\[[^\]]*\]"
                if re.search(pattern, config_content, re.DOTALL):
                    config_content = re.sub(pattern, wallets_str, config_content, flags=re.DOTALL)
                else:
                    config_content += f"\n\n{wallets_str}\n"
                    
            # Also update token_list_tool.py
            try:
                import os
                token_list_tool_path = os.path.join(get_project_root(), 'src', 'scripts', 'token_list_tool.py')
                if os.path.exists(token_list_tool_path):
                    with open(token_list_tool_path, 'r', encoding='utf-8') as f:
                        tool_content = f.read()
                    
                    # Replace in token_list_tool.py
                    pattern = r"WALLETS_TO_TRACK\s*=\s*\[[^\]]*\]"
                    if re.search(pattern, tool_content, re.DOTALL):
                        tool_content = re.sub(pattern, wallets_str, tool_content, flags=re.DOTALL)
                        
                        # Write updated token_list_tool.py back to file
                        with open(token_list_tool_path, 'w', encoding='utf-8') as f:
                            f.write(tool_content)
            except Exception as e:
                print(f"Warning: Could not update wallets in token_list_tool.py: {str(e)}")
        
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
    
    def toggle_activity_filter(self, checked):
        """Enable or disable the activity window input based on the activity filter checkbox"""
        self.activity_window.setEnabled(checked)
        if checked:
            self.activity_window.setStyleSheet("")
        else:
            self.activity_window.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: rgba(224, 224, 224, 100);
                    border: 1px solid rgba(0, 255, 255, 100);
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)


class RiskManagementTab(QWidget):
    """Tab for configuring and controlling Risk Management Agent"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            # Load Risk Management settings from config
            from src.config import (
                CASH_PERCENTAGE, MAX_POSITION_PERCENTAGE, MINIMUM_BALANCE_USD,
                USE_PERCENTAGE, MAX_LOSS_PERCENT, MAX_GAIN_PERCENT, MAX_LOSS_USD,
                MAX_GAIN_USD, MAX_LOSS_GAIN_CHECK_HOURS, SLEEP_AFTER_CLOSE,
                usd_size, max_usd_order_size, tx_sleep, slippage, PRIORITY_FEE,
                orders_per_open, DAYSBACK_4_DATA, DATA_TIMEFRAME, PAPER_TRADING_ENABLED,
                PAPER_INITIAL_BALANCE, PAPER_TRADING_SLIPPAGE, PAPER_TRADING_RESET_ON_START,
                RISK_CONTINUOUS_MODE, RISK_CHECK_INTERVAL_MINUTES, RISK_OVERRIDE_PROMPT
            )
            
            # Store config values
            self.cash_pct = CASH_PERCENTAGE
            self.max_pos_pct = MAX_POSITION_PERCENTAGE
            self.min_bal_usd = MINIMUM_BALANCE_USD
            self.use_pct = USE_PERCENTAGE
            self.max_loss_percent = MAX_LOSS_PERCENT
            self.max_gain_percent = MAX_GAIN_PERCENT
            self.max_loss_dollars = MAX_LOSS_USD
            self.max_gain_dollars = MAX_GAIN_USD
            self.check_hours = MAX_LOSS_GAIN_CHECK_HOURS
            self.sleep_seconds = SLEEP_AFTER_CLOSE
            self.order_size = usd_size
            self.max_order_size = max_usd_order_size
            self.tx_sleep_val = tx_sleep
            self.slippage_val = slippage
            self.priority_fee_val = PRIORITY_FEE
            self.orders_per_open_val = orders_per_open
            self.days_back_val = DAYSBACK_4_DATA
            self.data_tf = DATA_TIMEFRAME
            self.paper_trading = PAPER_TRADING_ENABLED
            self.paper_balance = PAPER_INITIAL_BALANCE
            self.paper_slippage = PAPER_TRADING_SLIPPAGE
            self.paper_reset = PAPER_TRADING_RESET_ON_START
            self.continuous_mode = RISK_CONTINUOUS_MODE
            self.risk_interval = RISK_CHECK_INTERVAL_MINUTES
            self.risk_prompt = RISK_OVERRIDE_PROMPT
            
        except ImportError as e:
            print(f"Error importing config settings: {e}")
            # Set default values if config import fails
            self.cash_pct = 20
            self.max_pos_pct = 10
            self.min_bal_usd = 100
            self.use_pct = True
            self.max_loss_percent = 20
            self.max_gain_percent = 100
            self.max_loss_dollars = 25
            self.max_gain_dollars = 25
            self.check_hours = 24
            self.sleep_seconds = 900
            self.order_size = 25
            self.max_order_size = 3
            self.tx_sleep_val = 15
            self.slippage_val = 199
            self.priority_fee_val = 100000
            self.orders_per_open_val = 3
            self.days_back_val = 3
            self.data_tf = '15m'
            self.paper_trading = False
            self.paper_balance = 1000
            self.paper_slippage = 100
            self.paper_reset = False
            self.continuous_mode = False
            self.risk_interval = 10
            self.risk_prompt = """You are Anarcho Capital's Risk Management Agent 🌙

Your task is to analyze the current portfolio and market conditions to determine if any positions should be closed based on risk management rules.

Data provided:
1. Current portfolio positions and their performance
2. Recent price action and market data
3. Risk management thresholds and settings

Analyze and respond with one of:
CLOSE - When risk thresholds are clearly violated
HOLD - When positions are within acceptable risk parameters
URGENT - When immediate action is needed regardless of thresholds

Your response must include:
- Risk assessment for each position
- Explanation of violated thresholds (if any)
- Assessment of market conditions
- Clear recommendation with confidence level

Remember: Preserving capital is your primary objective."""
        
        # Setup UI with loaded values
        self.setup_ui()
        
        # Initialize fields from config after UI setup
        try:
            # Set values in UI components
            self.risk_check_interval.setValue(self.risk_interval)
            self.cash_percentage.setValue(self.cash_pct)
            self.max_position_percentage.setValue(self.max_pos_pct)
            self.min_balance_usd.setValue(self.min_bal_usd)
            self.use_percentage.setChecked(self.use_pct)
            self.max_loss_pct.setValue(self.max_loss_percent)
            self.max_gain_pct.setValue(self.max_gain_percent)
            self.max_loss_usd.setValue(self.max_loss_dollars)
            self.max_gain_usd.setValue(self.max_gain_dollars)
            self.max_loss_gain_check_hours.setValue(self.check_hours)
            self.sleep_after_close.setValue(self.sleep_seconds)
            self.usd_size.setValue(self.order_size)
            self.max_usd_order_size.setValue(self.max_order_size)
            self.tx_sleep.setValue(self.tx_sleep_val)
            self.slippage.setValue(self.slippage_val)
            self.priority_fee.setValue(self.priority_fee_val)
            self.orders_per_open.setValue(self.orders_per_open_val)
            self.days_back.setValue(self.days_back_val)
            
            # Set the prompt text from config
            self.prompt_text.setPlainText(self.risk_prompt)
            
            # Set data timeframe combobox
            index = self.data_timeframe.findText(self.data_tf)
            if index >= 0:
                self.data_timeframe.setCurrentIndex(index)
                
            # Set paper trading values
            self.paper_trading_enabled.setChecked(self.paper_trading)
            self.paper_initial_balance.setValue(self.paper_balance)
            self.paper_trading_slippage.setValue(self.paper_slippage)
            self.paper_trading_reset_on_start.setChecked(self.paper_reset)
            self.risk_continuous_mode.setChecked(self.continuous_mode)
            
            # Update UI state based on loaded settings
            self.toggle_risk_interval_input(self.risk_continuous_mode.isChecked())
            self.toggle_limit_inputs(self.use_percentage.isChecked())
            
        except Exception as e:
            print(f"Error loading config settings: {e}")

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
            QSpinBox, QComboBox {{
                min-width: 100px;
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
        
        # AI Prompt Section
        ai_group = QGroupBox("AI Prompt")
        ai_layout = QVBoxLayout(ai_group)
        
        # AI Prompt - Create text editor but don't set text (will be loaded from config)
        self.prompt_text = QTextEdit()
        self.prompt_text.setMinimumHeight(200)
        ai_layout.addWidget(self.prompt_text)
        
        scroll_layout.addWidget(ai_group)
        
        # Risk Agent Runtime Settings - New dedicated section
        risk_runtime_group = QGroupBox("Risk Agent Runtime")
        risk_runtime_layout = QGridLayout(risk_runtime_group)

        # Risk Agent Continuous Mode
        self.risk_continuous_mode = QCheckBox("Loop Mode")
        self.risk_continuous_mode.setToolTip("When enabled, Risk Agent will run continuously instead of on interval")
        try:
            from src.config import RISK_CONTINUOUS_MODE
            self.risk_continuous_mode.setChecked(RISK_CONTINUOUS_MODE)
        except ImportError:
            # Setting doesn't exist yet, default to False
            self.risk_continuous_mode.setChecked(False)
        risk_runtime_layout.addWidget(self.risk_continuous_mode, 0, 0, 1, 2)
        
        # Connect continuous mode toggle to disable interval input when checked
        self.risk_continuous_mode.toggled.connect(self.toggle_risk_interval_input)
        
        # Risk Agent Interval
        risk_runtime_layout.addWidget(QLabel("Risk Interval (minutes):"), 1, 0)
        self.risk_check_interval = QSpinBox()
        self.risk_check_interval.setRange(1, 120)
        self.risk_check_interval.setValue(10)  # Default value, will be updated in __init__
        self.risk_check_interval.setToolTip("How often Risk Agent checks portfolio (in minutes)")
        risk_runtime_layout.addWidget(self.risk_check_interval, 1, 1)
        
        
        scroll_layout.addWidget(risk_runtime_group)
        
        # 2. Risk Management Parameters
        risk_group = QGroupBox("Risk Management Parameters")
        risk_group.setObjectName("risk_group")
        risk_layout = QGridLayout(risk_group)

        # Cash Reserve %
        risk_layout.addWidget(QLabel("Cash Reserve %:"), 0, 0)
        self.cash_percentage = QSpinBox()
        self.cash_percentage.setRange(0, 100)
        self.cash_percentage.setValue(20)  # Default value, will be updated in __init__
        self.cash_percentage.setToolTip("Minimum % to keep in USDC as safety buffer (0-100)")
        risk_layout.addWidget(self.cash_percentage, 0, 1)
        
        # Max Position %
        risk_layout.addWidget(QLabel("Max Position %:"), 1, 0)
        self.max_position_percentage = QSpinBox()
        self.max_position_percentage.setRange(1, 100)
        self.max_position_percentage.setValue(10)  # Default value, will be updated in __init__
        self.max_position_percentage.setToolTip("Maximum % allocation per position (0-100)")
        risk_layout.addWidget(self.max_position_percentage, 1, 1)
        
        # Minimum Balance USD
        risk_layout.addWidget(QLabel("Minimum Balance (USD):"), 2, 0)
        self.min_balance_usd = QDoubleSpinBox()
        self.min_balance_usd.setRange(0, 10000)
        self.min_balance_usd.setValue(100)  # Default value, will be updated in __init__
        self.min_balance_usd.setDecimals(2)
        self.min_balance_usd.setToolTip("If balance falls below this, risk agent will consider closing all positions")
        risk_layout.addWidget(self.min_balance_usd, 2, 1)
        
        # Use percentage based limits
        risk_layout.addWidget(QLabel("Use Percentage Based Limits:"), 3, 0)
        self.use_percentage = QCheckBox("Use Percentage Based Limits")
        self.use_percentage.setChecked(True)  # Default value, will be updated in __init__
        self.use_percentage.stateChanged.connect(self.toggle_limit_inputs)
        self.use_percentage.setToolTip("If True, use percentage-based limits. If False, use USD-based limits")
        risk_layout.addWidget(self.use_percentage, 3, 0, 1, 2)
        
        # Max Loss (%)
        risk_layout.addWidget(QLabel("Max Loss (%):"), 4, 0)
        self.max_loss_pct = QSpinBox()
        self.max_loss_pct.setRange(1, 100)
        self.max_loss_pct.setValue(20)  # Default value, will be updated in __init__
        self.max_loss_pct.setToolTip("Maximum loss as percentage (e.g., 20 = 20% loss)")
        risk_layout.addWidget(self.max_loss_pct, 4, 1)
        
        # Max Gain (%)
        risk_layout.addWidget(QLabel("Max Gain (%):"), 5, 0)
        self.max_gain_pct = QSpinBox()
        self.max_gain_pct.setRange(1, 1000)
        self.max_gain_pct.setValue(200)  # Default value, will be updated in __init__
        self.max_gain_pct.setToolTip("Maximum gain as percentage (e.g., 200 = 200% gain)")
        risk_layout.addWidget(self.max_gain_pct, 5, 1)
        
        # Max Loss (USD)
        risk_layout.addWidget(QLabel("Max Loss (USD):"), 6, 0)
        self.max_loss_usd = QDoubleSpinBox()
        self.max_loss_usd.setRange(0, 10000)
        self.max_loss_usd.setValue(25)  # Default value, will be updated in __init__
        self.max_loss_usd.setDecimals(2)
        self.max_loss_usd.setToolTip("Maximum loss in USD before stopping trading")
        risk_layout.addWidget(self.max_loss_usd, 6, 1)
        
        # Max Gain (USD)
        risk_layout.addWidget(QLabel("Max Gain (USD):"), 7, 0)
        self.max_gain_usd = QDoubleSpinBox()
        self.max_gain_usd.setRange(0, 10000)
        self.max_gain_usd.setValue(25)  # Default value, will be updated in __init__
        self.max_gain_usd.setDecimals(2)
        self.max_gain_usd.setToolTip("Maximum gain in USD before stopping trading")
        risk_layout.addWidget(self.max_gain_usd, 7, 1)
        
        # Max Loss/Gain Check Hours
        risk_layout.addWidget(QLabel("Max Loss/Gain Check Hours:"), 8, 0)
        self.max_loss_gain_check_hours = QSpinBox()
        self.max_loss_gain_check_hours.setRange(1, 168)  # Up to 7 days
        self.max_loss_gain_check_hours.setValue(24)  # Default value, will be updated in __init__
        self.max_loss_gain_check_hours.setToolTip("How far back to check for max loss/gain limits (in hours)")
        risk_layout.addWidget(self.max_loss_gain_check_hours, 8, 1)
        
        # Sleep After Close
        risk_layout.addWidget(QLabel("Sleep After Close (seconds):"), 9, 0)
        self.sleep_after_close = QSpinBox()
        self.sleep_after_close.setRange(1, 3600)  # Up to 1 hour
        self.sleep_after_close.setValue(900)  # Default value, will be updated in __init__
        self.sleep_after_close.setToolTip("Prevent overtrading - wait time after closing a position")
        risk_layout.addWidget(self.sleep_after_close, 9, 1)
        
        
        scroll_layout.addWidget(risk_group)
        
        # 3. Position Size Settings
        position_group = QGroupBox("Position Size Settings")
        position_layout = QGridLayout(position_group)
        
        # Default Order Size (USD)
        position_layout.addWidget(QLabel("Default Order Size (USD):"), 0, 0)
        self.usd_size = QDoubleSpinBox()
        self.usd_size.setRange(1, 1000)
        self.usd_size.setValue(25)  # Default value, will be updated in __init__
        self.usd_size.setDecimals(2)
        self.usd_size.setToolTip("Default size for new positions (in USD)")
        position_layout.addWidget(self.usd_size, 0, 1)
        
        # Max Order Size (USD)
        position_layout.addWidget(QLabel("Max Order Size (USD):"), 1, 0)
        self.max_usd_order_size = QDoubleSpinBox()
        self.max_usd_order_size.setRange(1, 1000)
        self.max_usd_order_size.setValue(3)  # Default value, will be updated in __init__
        self.max_usd_order_size.setDecimals(2)
        self.max_usd_order_size.setToolTip("Maximum size for individual orders (in USD)")
        position_layout.addWidget(self.max_usd_order_size, 1, 1)
        
        # Transaction Sleep (seconds)
        position_layout.addWidget(QLabel("TX Sleep (seconds):"), 2, 0)
        self.tx_sleep = QDoubleSpinBox()
        self.tx_sleep.setRange(0, 60)
        self.tx_sleep.setValue(15)  # Default value, will be updated in __init__
        self.tx_sleep.setDecimals(1)
        self.tx_sleep.setToolTip("Sleep between transactions (in seconds)")
        position_layout.addWidget(self.tx_sleep, 2, 1)
        
        # Slippage (in basis points)
        position_layout.addWidget(QLabel("Slippage (bps):"), 3, 0)
        self.slippage = QSpinBox()
        self.slippage.setRange(10, 1000)
        self.slippage.setValue(199)  # Default value, will be updated in __init__
        self.slippage.setToolTip("Slippage tolerance (100 = 1%)")
        position_layout.addWidget(self.slippage, 3, 1)
        
        # Priority Fee
        position_layout.addWidget(QLabel("Priority Fee:"), 4, 0)
        self.priority_fee = QSpinBox()
        self.priority_fee.setRange(0, 1000000)
        self.priority_fee.setValue(100000)  # Default value, will be updated in __init__
        self.priority_fee.setToolTip("Priority fee for transactions (~0.02 USD at current SOL prices)")
        position_layout.addWidget(self.priority_fee, 4, 1)
        
        # Orders Per Open
        position_layout.addWidget(QLabel("Orders Per Open:"), 5, 0)
        self.orders_per_open = QSpinBox()
        self.orders_per_open.setRange(1, 10)
        self.orders_per_open.setValue(3)  # Default value, will be updated in __init__
        self.orders_per_open.setToolTip("Number of orders to split position into for better fill rates")
        position_layout.addWidget(self.orders_per_open, 5, 1)
        
        scroll_layout.addWidget(position_group)
        
        # 4. Data Collection Settings
        data_group = QGroupBox("Data Collection Settings")
        data_layout = QGridLayout(data_group)
        
        # Days Back for Data
        data_layout.addWidget(QLabel("Days Back for Data:"), 0, 0)
        self.days_back = QSpinBox()
        self.days_back.setRange(1, 30)
        self.days_back.setValue(3)  # DAYSBACK_4_DATA = 3
        self.days_back.setToolTip("How many days of historical data to collect")
        data_layout.addWidget(self.days_back, 0, 1)
        
        # Data Timeframe
        data_layout.addWidget(QLabel("Data Timeframe:"), 1, 0)
        self.data_timeframe = QComboBox()
        timeframes = ['1m', '3m', '5m', '15m', '30m', '1H', '2H', '4H', '6H', '8H', '12H', '1D', '3D', '1W', '1M']
        self.data_timeframe.addItems(timeframes)
        self.data_timeframe.setCurrentText('15m')  # DATA_TIMEFRAME = '15'
        self.data_timeframe.setToolTip("Timeframe for data collection (1m to 1M)")
        data_layout.addWidget(self.data_timeframe, 1, 1)
        
        scroll_layout.addWidget(data_group)
        
        # Add Paper Trading Settings section to RiskManagementTab.setup_ui() after data_group

        # Paper Trading Settings 📝
        paper_group = QGroupBox("Paper Trading Settings")
        paper_layout = QGridLayout(paper_group)

        # Enable Paper Trading
        paper_layout.addWidget(QLabel("Enable Paper Trading:"), 0, 0)
        self.paper_trading_enabled = QCheckBox()
        self.paper_trading_enabled.setChecked(False)  # Default value, will be updated in __init__
        self.paper_trading_enabled.setToolTip("Toggle paper trading mode on/off")
        paper_layout.addWidget(self.paper_trading_enabled, 0, 1)

        # Initial Balance
        paper_layout.addWidget(QLabel("Initial Balance (USD):"), 1, 0)
        self.paper_initial_balance = QDoubleSpinBox()
        self.paper_initial_balance.setRange(10, 10000)
        self.paper_initial_balance.setValue(1000)  # Default value, will be updated in __init__
        self.paper_initial_balance.setDecimals(2)
        self.paper_initial_balance.setToolTip("Initial paper trading balance in USD")
        paper_layout.addWidget(self.paper_initial_balance, 1, 1)

        # Paper Trading Slippage
        paper_layout.addWidget(QLabel("Paper Trading Slippage (bps):"), 2, 0)
        self.paper_trading_slippage = QSpinBox()
        self.paper_trading_slippage.setRange(0, 500)
        self.paper_trading_slippage.setValue(100)  # Default value, will be updated in __init__
        self.paper_trading_slippage.setToolTip("Simulated slippage for paper trades (100 = 1%)")
        paper_layout.addWidget(self.paper_trading_slippage, 2, 1)

        # Reset on Start
        paper_layout.addWidget(QLabel("Reset On Start:"), 3, 0)
        self.paper_trading_reset_on_start = QCheckBox()
        self.paper_trading_reset_on_start.setChecked(False)  # Default value, will be updated in __init__
        self.paper_trading_reset_on_start.setToolTip("Whether to reset paper portfolio on app start")
        paper_layout.addWidget(self.paper_trading_reset_on_start, 3, 1)

        scroll_layout.addWidget(paper_group)
        
        # Add save button
        save_button = NeonButton("Save Risk Configuration", CyberpunkColors.TERTIARY)
        save_button.clicked.connect(self.save_config)
        scroll_layout.addWidget(save_button)
        
        # Create scroll area
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # Initialize visibility based on current settings
        self.toggle_limit_inputs(self.use_percentage.isChecked())

    def toggle_limit_inputs(self, checked):
        """Toggle between USD and percentage-based limit inputs"""
        if checked:
            # Show percentage fields, hide USD fields
            self.max_loss_pct.setVisible(True)
            self.max_gain_pct.setVisible(True)
            self.max_loss_usd.setVisible(False)
            self.max_gain_usd.setVisible(False)
            
            # Get the labels in the grid layout
            risk_layout = self.findChild(QGroupBox, "risk_group").layout()
            risk_layout.itemAtPosition(4, 0).widget().setVisible(True)  # Max Loss (%) label
            risk_layout.itemAtPosition(5, 0).widget().setVisible(True)  # Max Gain (%) label
            risk_layout.itemAtPosition(6, 0).widget().setVisible(False)  # Max Loss (USD) label
            risk_layout.itemAtPosition(7, 0).widget().setVisible(False)  # Max Gain (USD) label
        else:
            # Show USD fields, hide percentage fields
            self.max_loss_pct.setVisible(False)
            self.max_gain_pct.setVisible(False)
            self.max_loss_usd.setVisible(True)
            self.max_gain_usd.setVisible(True)
            
            # Get the labels in the grid layout
            risk_layout = self.findChild(QGroupBox, "risk_group").layout()
            risk_layout.itemAtPosition(4, 0).widget().setVisible(False)  # Max Loss (%) label
            risk_layout.itemAtPosition(5, 0).widget().setVisible(False)  # Max Gain (%) label
            risk_layout.itemAtPosition(6, 0).widget().setVisible(True)  # Max Loss (USD) label
            risk_layout.itemAtPosition(7, 0).widget().setVisible(True)  # Max Gain (USD) label
    
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
    
    def update_prompt_value(self, content, key, prompt_text):
        """Update a prompt value in the config file with proper multi-line formatting"""
        import re
        # Match the entire assignment including the triple-quoted string
        pattern = rf'{key}\s*=\s*"""[\s\S]*?"""'
        
        # Clean prompt text: strip all leading/trailing whitespace, then add exactly one newline at start and end
        cleaned_prompt = prompt_text.strip()
        replacement = f'{key} = """\n{cleaned_prompt}\n"""'
        
        if re.search(pattern, content, re.DOTALL):
            return re.sub(pattern, replacement, content, re.DOTALL)
        else:
            # If the key doesn't exist, add it to the end of the file
            return f'{content}\n{key} = """\n{cleaned_prompt}\n"""'
    
    def save_config(self):
        """Save risk management settings to config.py"""
        try:
            # Check if paper trading mode is being changed
            current_paper_trading_setting = False
            try:
                from src import config
                current_paper_trading_setting = getattr(config, "PAPER_TRADING_ENABLED", False)
            except:
                pass
            
            # Store if we need to restart agents due to paper trading change
            paper_trading_changed = current_paper_trading_setting != self.paper_trading_enabled.isChecked()
            
            # Update config.py with settings
            config_path = os.path.join(get_project_root(), 'src', 'config.py')

            # Read existing config file
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
    
            # Update values in the config content
            config_content = self.collect_config(config_content)
            
            # Write updated config back to file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            # Direct fix: Update the risk interval value directly in the config.py file
            self.ensure_risk_interval_updated()
            
            # Update main.py with the continuous mode and interval settings
            try:
                import re
                main_py_path = os.path.join(get_project_root(), 'src', 'main.py')
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    main_content = f.read()
                    
                # Always update interval, even in continuous mode
                pattern = r"'risk':\s*{\s*'active':\s*True,\s*'interval':\s*\d+"
                replacement = f"'risk': {{'active': True, 'interval': {self.risk_check_interval.value()}"
                main_content = re.sub(pattern, replacement, main_content)
                
                # Always update continuous mode check in main.py
                # Find the risk check in the main while loop
                risk_check_pattern = r"if \(risk_agent and \n\s*\(.*\)\):"
                risk_check_replacement = f"if (risk_agent and \n                    (RISK_CONTINUOUS_MODE or (current_time - last_run['risk']).total_seconds() >= ACTIVE_AGENTS['risk']['interval'] * 60))"
                
                if re.search(risk_check_pattern, main_content):
                    main_content = re.sub(risk_check_pattern, risk_check_replacement, main_content)
                
                # Update next run message for continuous mode
                risk_next_run_pattern = r"next_run_time = \(current_time \+ timedelta\(minutes=ACTIVE_AGENTS\['risk'\]\['interval'\]\)\)\.strftime\('%H:%M:%S'\)"
                risk_next_run_replacement = "next_run_time = \"Continuous Mode\" if RISK_CONTINUOUS_MODE else (current_time + timedelta(minutes=ACTIVE_AGENTS['risk']['interval'])).strftime('%H:%M:%S')"
                
                if re.search(risk_next_run_pattern, main_content):
                    main_content = re.sub(risk_next_run_pattern, risk_next_run_replacement, main_content)
                
                # Save changes to main.py
                with open(main_py_path, 'w', encoding='utf-8') as f:
                    f.write(main_content)
                
            except Exception as e:
                print(f"Warning: Could not update risk settings in main.py: {str(e)}")
            
            # Update risk agent prompt if it has changed
            try:
                risk_agent_path = os.path.join(get_project_root(), 'src', 'agents', 'risk_agent.py')
                with open(risk_agent_path, 'r', encoding='utf-8') as f:
                    risk_agent_content = f.read()
                    
                # Create prompt text with proper escaping
                prompt_text = self.prompt_text.toPlainText().strip()
                
                # Update the RISK_OVERRIDE_PROMPT in risk_agent.py
                updated_content = re.sub(r'RISK_OVERRIDE_PROMPT\s*=\s*"""[\s\S]*?"""', f'RISK_OVERRIDE_PROMPT = """\n{prompt_text}\n"""', risk_agent_content, flags=re.DOTALL)
                
                with open(risk_agent_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
            except Exception as e:
                print(f"Warning: Could not update risk agent prompt: {str(e)}")
            
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
                main_window.console.append_message("Configuration saved. Applying changes to Risk Agent...", "system")
                main_window.restart_agent("risk")
                main_window.restart_agent("dca")
                main_window.restart_agent("chart_analysis")
            
            # Simple notification that the configuration has been saved
            QMessageBox.information(self, "Saved", "Risk Management configuration has been updated.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
    
    def ensure_risk_interval_updated(self):
        """
        Special method to ensure RISK_CHECK_INTERVAL_MINUTES is properly updated everywhere.
        This is a direct fix for the issue where the interval keeps reverting to 5760.
        """
        try:
            interval_value = self.risk_check_interval.value()
            
            # Update the config.py file directly
            config_path = os.path.join(get_project_root(), 'src', 'config.py')
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use a more specific pattern to avoid false positives
            pattern = r'RISK_CHECK_INTERVAL_MINUTES\s*=\s*\d+'
            replacement = f'RISK_CHECK_INTERVAL_MINUTES = {interval_value}'
            
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Successfully updated RISK_CHECK_INTERVAL_MINUTES to {interval_value} in config.py")
            else:
                print("Warning: Could not find RISK_CHECK_INTERVAL_MINUTES in config.py")
                
            # Also update risk_agent.py if there's any direct reference to this value
            risk_agent_path = os.path.join(get_project_root(), 'src', 'agents', 'risk_agent.py')
            if os.path.exists(risk_agent_path):
                with open(risk_agent_path, 'r', encoding='utf-8') as f:
                    agent_content = f.read()
                
                # Check if there's a hardcoded value there
                hardcoded_pattern = r'check_interval\s*=\s*timedelta\(minutes=(\d+)\)'
                if re.search(hardcoded_pattern, agent_content):
                    # Replace direct hardcoded value (if any)
                    agent_content = re.sub(hardcoded_pattern, f'check_interval = timedelta(minutes=RISK_CHECK_INTERVAL_MINUTES)', agent_content)
                    with open(risk_agent_path, 'w', encoding='utf-8') as f:
                        f.write(agent_content)
                    print("Updated any hardcoded interval values in risk_agent.py")
                    
        except Exception as e:
            print(f"Error ensuring risk interval update: {str(e)}")
    
    def collect_config(self, config_content):
        """Collect risk management settings without saving to file - used by global save function"""
        # Update values in the config content
        config_content = self.update_config_value(config_content, "CASH_PERCENTAGE", str(self.cash_percentage.value()))
        config_content = self.update_config_value(config_content, "MAX_POSITION_PERCENTAGE", str(self.max_position_percentage.value()))
        config_content = self.update_config_value(config_content, "MINIMUM_BALANCE_USD", str(self.min_balance_usd.value()))
        config_content = self.update_config_value(config_content, "USE_PERCENTAGE", str(self.use_percentage.isChecked()))
        config_content = self.update_config_value(config_content, "MAX_LOSS_PERCENT", str(self.max_loss_pct.value()))
        config_content = self.update_config_value(config_content, "MAX_GAIN_PERCENT", str(self.max_gain_pct.value()))
        config_content = self.update_config_value(config_content, "MAX_LOSS_USD", str(self.max_loss_usd.value()))
        config_content = self.update_config_value(config_content, "MAX_GAIN_USD", str(self.max_gain_usd.value()))
        config_content = self.update_config_value(config_content, "MAX_LOSS_GAIN_CHECK_HOURS", str(self.max_loss_gain_check_hours.value()))
        config_content = self.update_config_value(config_content, "SLEEP_AFTER_CLOSE", str(self.sleep_after_close.value()))
        
        # Update position size settings
        config_content = self.update_config_value(config_content, "usd_size", str(self.usd_size.value()))
        config_content = self.update_config_value(config_content, "max_usd_order_size", str(self.max_usd_order_size.value()))
        config_content = self.update_config_value(config_content, "tx_sleep", str(self.tx_sleep.value()))
        config_content = self.update_config_value(config_content, "slippage", str(self.slippage.value()))
        
        # Update both PRIORITY_FEE and priority_fee to keep them in sync
        priority_fee_value = str(self.priority_fee.value())
        config_content = self.update_config_value(config_content, "PRIORITY_FEE", priority_fee_value)
        config_content = self.update_config_value(config_content, "priority_fee", priority_fee_value)
        
        config_content = self.update_config_value(config_content, "orders_per_open", str(self.orders_per_open.value()))
        
        # Update data collection settings
        config_content = self.update_config_value(config_content, "DAYSBACK_4_DATA", str(self.days_back.value()))
        config_content = self.update_config_value(config_content, "DATA_TIMEFRAME", f"'{self.data_timeframe.currentText()}'")
        
        # Update paper trading settings
        config_content = self.update_config_value(config_content, "PAPER_TRADING_ENABLED", str(self.paper_trading_enabled.isChecked()))
        config_content = self.update_config_value(config_content, "PAPER_INITIAL_BALANCE", str(self.paper_initial_balance.value()))
        config_content = self.update_config_value(config_content, "PAPER_TRADING_SLIPPAGE", str(self.paper_trading_slippage.value()))
        config_content = self.update_config_value(config_content, "PAPER_TRADING_RESET_ON_START", str(self.paper_trading_reset_on_start.isChecked()))
        
        # Risk Agent Runtime Settings - Make sure to save the risk interval
        config_content = self.update_config_value(config_content, "RISK_CONTINUOUS_MODE", str(self.risk_continuous_mode.isChecked()))
        
        # Always update the risk check interval value, even in continuous mode
        risk_interval_value = str(self.risk_check_interval.value())
        config_content = self.update_config_value(config_content, "RISK_CHECK_INTERVAL_MINUTES", risk_interval_value)
        
        # Update the RISK_OVERRIDE_PROMPT using the update_prompt_value method
        prompt_text = self.prompt_text.toPlainText()
        config_content = self.update_prompt_value(config_content, "RISK_OVERRIDE_PROMPT", prompt_text)
        
        return config_content

    def toggle_risk_interval_input(self, checked):
        """Enable or disable the risk interval input based on continuous mode"""
        self.risk_check_interval.setDisabled(checked)
        if checked:
            self.risk_check_interval.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: rgba(224, 224, 224, 100);
                    border: 1px solid rgba(0, 255, 255, 100);
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)
        else:
            self.risk_check_interval.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: {CyberpunkColors.TEXT_LIGHT};
                    border: 1px solid {CyberpunkColors.PRIMARY};
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)