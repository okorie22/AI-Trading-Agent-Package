class CopyBotTab(QWidget):
    """Tab for configuring and controlling CopyBot Agent"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # Set initial values from config
        try:
            # Load CopyBot runtime settings from config
            from src.config import COPYBOT_INTERVAL_MINUTES
            self.update_interval.setValue(COPYBOT_INTERVAL_MINUTES)
            
            # Load continuous mode if it exists, otherwise default to False
            try:
                from src.config import COPYBOT_CONTINUOUS_MODE
                self.run_mode.setChecked(COPYBOT_CONTINUOUS_MODE)
            except ImportError:
                self.run_mode.setChecked(False)
                
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
        
        # Create scroll area for all settings
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 1. AI Prompt Section
        ai_group = QGroupBox("AI Prompt")
        ai_layout = QVBoxLayout(ai_group)
        
        # AI Prompt
        self.prompt_text = QTextEdit()
        prompt_text = """
You are Moon Dev's CopyBot Agent 🌙

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
        self.prompt_text.setPlainText(prompt_text)
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
        
        agent_layout.addWidget(QLabel("CopyBot Interval (minutes):"), 1, 0)
        self.update_interval = QSpinBox()
        self.update_interval.setRange(1, 1440)  # 1 minute to 24 hours
        self.update_interval.setValue(5)  # Default from ACTIVE_AGENTS in main.py
        self.update_interval.setToolTip("Time between CopyBot runs (in minutes)")
        agent_layout.addWidget(self.update_interval, 1, 1)
        
        # Add this connection - it will disable the update_interval when continuous mode is checked
        self.run_mode.toggled.connect(self.toggle_interval_input)
        
        # API Request Configuration
        agent_layout.addWidget(QLabel("Sleep Between API Calls (seconds):"), 2, 0)
        self.api_sleep = QDoubleSpinBox()
        self.api_sleep.setRange(0.1, 10)
        self.api_sleep.setValue(1.0)  # Default from token_list_tool.py
        self.api_sleep.setSingleStep(0.1)
        self.api_sleep.setToolTip("Delay between API calls to avoid rate limits")
        agent_layout.addWidget(self.api_sleep, 2, 1)
        
        agent_layout.addWidget(QLabel("API Timeout (seconds):"), 3, 0)
        self.api_timeout = QSpinBox()
        self.api_timeout.setRange(5, 60)
        self.api_timeout.setValue(30)
        self.api_timeout.setToolTip("Maximum time to wait for API responses")
        agent_layout.addWidget(self.api_timeout, 3, 1)
        
        agent_layout.addWidget(QLabel("Max API Retries:"), 4, 0)
        self.max_retries = QSpinBox()
        self.max_retries.setRange(1, 10)
        self.max_retries.setValue(5)  # Default from fetch_with_backoff
        self.max_retries.setToolTip("Maximum number of retry attempts for failed API calls")
        agent_layout.addWidget(self.max_retries, 4, 1)
        
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
        from src.config import EXCLUDED_TOKENS
        # Create a set of unique values after converting everything to strings
        unique_tokens = set()
        for token in EXCLUDED_TOKENS:
            # Skip variable references, only display actual addresses
            if token not in ["USDC_ADDRESS", "SOL_ADDRESS"]:
                unique_tokens.add(token)
        
        # Always add these explicitly with labels
        excluded_text = "USDC: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v\n"
        excluded_text += "SOL: So11111111111111111111111111111111111111111\n"
        # Add any other unique tokens
        for token in unique_tokens:
            if (token != "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" and 
                token != "So11111111111111111111111111111111111111111"):
                excluded_text += f"{token}\n"
        
        self.excluded_tokens_display.setPlainText(excluded_text)
        self.excluded_tokens_display.setMinimumHeight(80)
        excluded_layout.addWidget(self.excluded_tokens_display)
        
        # Additional tokens to exclude label
        additional_label = QLabel("Additional tokens to exclude:")
        excluded_layout.addWidget(additional_label)
        
        # Additional tokens text box
        self.additional_excluded = QTextEdit()
        self.additional_excluded.setPlaceholderText("Enter additional token addresses to exclude")
        self.additional_excluded.setMaximumHeight(60)
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
        scroll_area = QScrollArea()
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
            # Portfolio Analysis Prompt
            prompt_text = self.prompt_text.toPlainText()
            config_content = self.update_config_value(config_content, "PORTFOLIO_ANALYSIS_PROMPT", f'"""\n{prompt_text}\n"""')
            
            # Update filter settings
            config_content = self.update_config_value(config_content, "FILTER_MODE", f'"{self.filter_mode.currentText()}"')
            config_content = self.update_config_value(config_content, "ENABLE_PERCENTAGE_FILTER", str(self.percentage_filter.isChecked()))
            config_content = self.update_config_value(config_content, "PERCENTAGE_THRESHOLD", str(self.percentage_threshold.value()))
            config_content = self.update_config_value(config_content, "ENABLE_AMOUNT_FILTER", str(self.amount_filter.isChecked()))
            config_content = self.update_config_value(config_content, "AMOUNT_THRESHOLD", str(self.amount_threshold.value()))
            config_content = self.update_config_value(config_content, "ENABLE_ACTIVITY_FILTER", str(self.activity_filter.isChecked()))
            config_content = self.update_config_value(config_content, "ACTIVITY_WINDOW_HOURS", str(self.activity_window.value()))
            
            # Update token lists
            # 1. Wallets to track
            wallets_text = self.wallets_to_track.toPlainText()
            wallets_list = [line.strip() for line in wallets_text.strip().split('\n') if line.strip()]
            wallets_str = "WALLETS_TO_TRACK = [\n"
            for wallet in wallets_list:
                wallets_str += f'    "{wallet}",\n'
            wallets_str += "    # Add more wallets here as needed\n]"
            config_content = self.update_config_value(config_content, "WALLETS_TO_TRACK", wallets_str, multiline=True)
            
            # 2. Monitored tokens
            monitored_text = self.monitored_tokens.toPlainText()
            monitored_list = [line.strip() for line in monitored_text.strip().split('\n') if line.strip()]
            monitored_str = "[\n"
            for token in monitored_list:
                monitored_str += f'    \'{token}\',\n'
            monitored_str += "]"
            config_content = self.update_config_value(config_content, "MONITORED_TOKENS", monitored_str, multiline=True)
            
            # 3. Excluded tokens - now we only save additional tokens since the core ones are hardcoded
            additional_text = self.additional_excluded.toPlainText()
            additional_list = []
            if additional_text.strip():
                additional_list = [line.strip() for line in additional_text.strip().split('\n') if line.strip()]
            
            # Format the excluded tokens list - always include the core tokens
            excluded_str = "[USDC_ADDRESS, SOL_ADDRESS, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111111'"
            for token in additional_list:
                if token.strip():
                    excluded_str += f', \'{token}\''
            excluded_str += "]"
            config_content = self.update_config_value(config_content, "EXCLUDED_TOKENS", excluded_str)
            
            # Update runtime settings
            config_content = self.update_config_value(config_content, "COPYBOT_INTERVAL_MINUTES", str(self.update_interval.value()))
            
            # Add or update COPYBOT_CONTINUOUS_MODE in config.py
            if "COPYBOT_CONTINUOUS_MODE" not in config_content:
                # If COPYBOT_CONTINUOUS_MODE doesn't exist in config.py, add it after COPYBOT_INTERVAL_MINUTES
                pattern = r"COPYBOT_INTERVAL_MINUTES\s*=\s*\d+"
                if re.search(pattern, config_content):
                    replacement = f"COPYBOT_INTERVAL_MINUTES = {self.update_interval.value()}\n# CopyBot Continuous Mode (overrides interval when True)\nCOPYBOT_CONTINUOUS_MODE = {str(self.run_mode.isChecked())}"
                    config_content = re.sub(pattern, replacement, config_content)
                else:
                    # If we can't find COPYBOT_INTERVAL_MINUTES for some reason, just append to the end
                    config_content += f"\n# CopyBot Runtime Settings\nCOPYBOT_INTERVAL_MINUTES = {self.update_interval.value()}\nCOPYBOT_CONTINUOUS_MODE = {str(self.run_mode.isChecked())}"
            else:
                # If it already exists, just update its value
                config_content = self.update_config_value(config_content, "COPYBOT_CONTINUOUS_MODE", str(self.run_mode.isChecked()))
            
            # Update other API settings
            config_content = self.update_config_value(config_content, "API_SLEEP_SECONDS", str(self.api_sleep.value()))
            config_content = self.update_config_value(config_content, "API_TIMEOUT_SECONDS", str(self.api_timeout.value()))
            config_content = self.update_config_value(config_content, "API_MAX_RETRIES", str(self.max_retries.value()))
            
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
                
                # Check if main.py already imports COPYBOT_CONTINUOUS_MODE
                if "COPYBOT_CONTINUOUS_MODE" not in main_content:
                    # Add import statement if necessary
                    if "from src.config import " in main_content:
                        # Modify existing import
                        import_pattern = r"from src\.config import (.*)"
                        match = re.search(import_pattern, main_content)
                        if match:
                            imports = match.group(1).strip()
                            if "COPYBOT_INTERVAL_MINUTES" in imports:
                                # Replace the import line to include both
                                replacement = f"from src.config import {imports}, COPYBOT_CONTINUOUS_MODE"
                                main_content = re.sub(import_pattern, replacement, main_content)
                            else:
                                # Add COPYBOT_INTERVAL_MINUTES and COPYBOT_CONTINUOUS_MODE
                                replacement = f"from src.config import {imports}, COPYBOT_INTERVAL_MINUTES, COPYBOT_CONTINUOUS_MODE"
                                main_content = re.sub(import_pattern, replacement, main_content)
                    else:
                        # Add new import
                        main_content = main_content.replace("from src.config import *", 
                                                            "from src.config import *, COPYBOT_CONTINUOUS_MODE")
                
                # Save changes to main.py
                with open(main_py_path, 'w', encoding='utf-8') as f:
                    f.write(main_content)
                
            except Exception as e:
                print(f"Warning: Could not fully update main.py: {str(e)}")
            
            # Reload the configuration module to apply changes immediately
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
        
    def update_config_value(self, content, key, value, multiline=False):
        """Helper function to update a value in the config file content"""
        import re
        
        # Special handling for PORTFOLIO_ANALYSIS_PROMPT to avoid duplication
        if key == "PORTFOLIO_ANALYSIS_PROMPT":
            # Find the entire block from PORTFOLIO_ANALYSIS_PROMPT = """ to the closing """
            pattern = rf"{key}\s*=\s*\"\"\"[\s\S]*?\"\"\""
            
            # If the pattern exists, replace it completely
            if re.search(pattern, content, re.DOTALL):
                replacement = f"{key} = {value}"
                return re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # For other multiline content
        if multiline:
            # More specific pattern that won't create duplicates
            pattern = rf"{key}\s*=\s*(?:{key}\s*=\s*)?(?:{{[^}}]*}}|\[[^\]]*\]|\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?''')"
            
            # Check if the pattern exists before replacing
            if re.search(pattern, content, re.DOTALL):
                replacement = f"{key} = {value}"
                return re.sub(pattern, replacement, content, flags=re.DOTALL)
            else:
                # Fall back to simpler pattern if the key doesn't exist in expected format
                pattern = rf"{key}\s*=.*?(?=\n\n|\n[^\n]+=|\Z)"
                if re.search(pattern, content, re.DOTALL):
                    replacement = f"{key} = {value}"
                    return re.sub(pattern, replacement, content, flags=re.DOTALL)
                else:
                    # If key doesn't exist at all, append it
                    return content + f"\n\n{key} = {value}"
        else:
            # For simple single-line values, use a more precise pattern
            pattern = rf"{key}\s*=\s*[^\n]*"
            replacement = f"{key} = {value}"
            return re.sub(pattern, replacement, content)

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