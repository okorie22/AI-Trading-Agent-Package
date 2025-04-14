class ConfigurationTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
            QLineEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 2px;
                padding: 2px;
            }}
            QSlider::handle {{
                background-color: {CyberpunkColors.PRIMARY};
            }}
            QSlider::groove:horizontal {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
        """)

class ConfigEditor(QWidget):
    """Widget for editing configuration values"""
    config_saved = Signal(dict)
    
    def __init__(self, config_data=None, parent=None):
        super().__init__(parent)
        self.config_data = config_data or {}
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create scrollable form
        form_layout = QGridLayout()
        row = 0
        
        # Create widgets for each config item
        self.widgets = {}
        
        # Group similar settings
        groups = {
            "AI Settings": ["AI_MODEL", "AI_MAX_TOKENS", "AI_TEMPERATURE"],
            "Risk Management": ["CASH_PERCENTAGE", "MAX_POSITION_PERCENTAGE", "MINIMUM_BALANCE_USD", "USE_AI_CONFIRMATION"],
            "DCA & Staking": ["STAKING_ALLOCATION_PERCENTAGE", "DCA_INTERVAL_MINUTES", "TAKE_PROFIT_PERCENTAGE", "FIXED_DCA_AMOUNT"],
            "Agent Intervals": ["SLEEP_BETWEEN_RUNS_MINUTES", "CHART_CHECK_INTERVAL_MINUTES"],
            "Wallet Settings": ["address", "symbol"]
        }
        
        for group_name, keys in groups.items():
            # Add group header
            group_label = QLabel(group_name)
            group_label.setStyleSheet(f"""
                font-family: 'Orbitron', sans-serif;
                font-size: 16px;
                font-weight: bold;
                color: {CyberpunkColors.PRIMARY};
                padding-top: 10px;
            """)
            form_layout.addWidget(group_label, row, 0, 1, 2)
            row += 1
            
            # Add settings in this group
            for key in keys:
                if key in self.config_data:
                    value = self.config_data[key]
                    label = QLabel(key.replace("_", " ").title() + ":")
                    
                    # Create appropriate widget based on value type
                    if isinstance(value, bool):
                        widget = QCheckBox()
                        widget.setChecked(value)
                    elif isinstance(value, int):
                        if key in ["AI_TEMPERATURE", "CASH_PERCENTAGE", "MAX_POSITION_PERCENTAGE", 
                                  "STAKING_ALLOCATION_PERCENTAGE", "TAKE_PROFIT_PERCENTAGE"]:
                            widget = QSlider(Qt.Horizontal)
                            widget.setRange(0, 100)
                            widget.setValue(value)
                        else:
                            widget = QLineEdit(str(value))
                    elif isinstance(value, float):
                        widget = QLineEdit(str(value))
                    elif isinstance(value, str):
                        if key == "AI_MODEL":
                            widget = QComboBox()
                            models = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
                            widget.addItems(models)
                            current_index = widget.findText(value)
                            if current_index >= 0:
                                widget.setCurrentIndex(current_index)
                        else:
                            widget = QLineEdit(value)
                    else:
                        widget = QLineEdit(str(value))
                    
                    form_layout.addWidget(label, row, 0)
                    form_layout.addWidget(widget, row, 1)
                    self.widgets[key] = widget
                    row += 1
            
            # Add separator
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            separator.setStyleSheet(f"background-color: {CyberpunkColors.PRIMARY}; max-height: 1px;")
            form_layout.addWidget(separator, row, 0, 1, 2)
            row += 1
        
        # Add form to layout
        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        
        # Add scrollable area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(form_widget)
        layout.addWidget(scroll_area)
        
        # Add save button
        save_button = NeonButton("Save Configuration", CyberpunkColors.SUCCESS)
        save_button.clicked.connect(self.save_config)
        layout.addWidget(save_button)
        
    def save_config(self):
        """Save configuration values from widgets"""
        updated_config = {}
        
        for key, widget in self.widgets.items():
            if isinstance(widget, QCheckBox):
                updated_config[key] = widget.isChecked()
            elif isinstance(widget, QSlider):
                updated_config[key] = widget.value()
            elif isinstance(widget, QComboBox):
                updated_config[key] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                # Try to convert to appropriate type
                value = widget.text()
                original_value = self.config_data.get(key)
                
                if isinstance(original_value, int):
                    try:
                        updated_config[key] = int(value)
                    except ValueError:
                        updated_config[key] = original_value
                elif isinstance(original_value, float):
                    try:
                        updated_config[key] = float(value)
                    except ValueError:
                        updated_config[key] = original_value
                else:
                    updated_config[key] = value
        
        # Emit signal with updated config
        self.config_saved.emit(updated_config)
        
        # Show confirmation
        QMessageBox.information(self, "Configuration Saved", 
                               "Configuration has been saved successfully.")

class ApiKeyEditor(QWidget):
    """Widget for securely editing API keys and credentials"""
    keys_saved = Signal()
    
    def __init__(self, env_path=None, parent=None):
        super().__init__(parent)
        # Use the universal project root function
        project_root = get_project_root()
        self.env_path = env_path or os.path.join(project_root, '.env')
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Add explanation text
        info_label = QLabel(
            "Enter your API keys below. These settings are stored in your .env file and "
            "are required for the trading system to function properly."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Create form layout for keys
        form_widget = QWidget()
        form_layout = QGridLayout(form_widget)
        
        # Group API keys by service
        key_groups = {
            "Trading APIs": [
                "BIRDEYE_API_KEY", 
                "RPC_ENDPOINT", 
                "COINGECKO_API_KEY"
            ],
            "AI Service Keys": [
                "ANTHROPIC_KEY", 
                "OPENAI_KEY", 
                "DEEPSEEK_KEY"
            ],
            "Blockchain Keys": [
                "SOLANA_PRIVATE_KEY", 
                "DEFAULT_WALLET_ADDRESS"
            ]
        }
        
        # Load current .env values
        env_values = self.load_env_values()
        
        # Create widgets for each key
        self.key_fields = {}
        row = 0
        
        for group_name, keys in key_groups.items():
            # Add group header
            group_label = QLabel(group_name)
            group_label.setStyleSheet(f"""
                font-family: 'Orbitron', sans-serif;
                font-size: 16px;
                font-weight: bold;
                color: {CyberpunkColors.PRIMARY};
                padding-top: 10px;
            """)
            form_layout.addWidget(group_label, row, 0, 1, 2)
            row += 1
            
            for key in keys:
                # Create label
                label = QLabel(f"{key}:")
                
                # Create input field (password field for sensitive keys)
                is_sensitive = "KEY" in key or "SECRET" in key or "PRIVATE" in key or "PASSWORD" in key or "ENDPOINT" in key or "ADDRESS" in key
                field = QLineEdit(env_values.get(key, ""))
                
                if is_sensitive:
                    field.setEchoMode(QLineEdit.Password)
                    # Add show/hide button
                    show_button = QPushButton("👁️")
                    show_button.setFixedWidth(30)
                    show_button.setCheckable(True)
                    show_button.clicked.connect(lambda checked, f=field: f.setEchoMode(
                        QLineEdit.Normal if checked else QLineEdit.Password))
                    form_layout.addWidget(label, row, 0)
                    field_layout = QHBoxLayout()
                    field_layout.addWidget(field)
                    field_layout.addWidget(show_button)
                    form_layout.addLayout(field_layout, row, 1)
                else:
                    form_layout.addWidget(label, row, 0)
                    form_layout.addWidget(field, row, 1)
                
                self.key_fields[key] = field
                row += 1
            
            # Add separator
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            separator.setStyleSheet(f"background-color: {CyberpunkColors.PRIMARY}; max-height: 1px;")
            form_layout.addWidget(separator, row, 0, 1, 2)
            row += 1
        
        # Add scrollable area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(form_widget)
        layout.addWidget(scroll_area)
        
        # Add save and test buttons
        button_layout = QHBoxLayout()
        
        test_button = NeonButton("Test Connections", CyberpunkColors.PRIMARY)
        test_button.clicked.connect(self.test_connections)
        
        save_button = NeonButton("Save API Keys", CyberpunkColors.SUCCESS)
        save_button.clicked.connect(self.save_keys)
        
        button_layout.addWidget(test_button)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)
        
        # Set stylesheet
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
            }}
            QLineEdit {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 2px;
                padding: 8px;
            }}
            QLabel {{
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
            QGroupBox {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: 1px solid {CyberpunkColors.PRIMARY};
                margin-top: 10px;
                padding: 15px;
            }}
            QGroupBox::title {{
                color: {CyberpunkColors.PRIMARY};
                subcontrol-origin: margin;
                left: 10px;
            }}
            QPushButton[objectName="eyeButton"] {{
                background-color: transparent;
                border: none;
                color: {CyberpunkColors.PRIMARY};
            }}
            QPushButton[objectName="eyeButton"]:hover {{
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
        """)
        
    def load_env_values(self):
        """Load current values from .env file with proper encoding handling"""
        values = {}
        try:
            if os.path.exists(self.env_path):
                # Try UTF-8 encoding first, which handles most special characters
                with open(self.env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            values[key.strip()] = value.strip()
            return values
        except UnicodeDecodeError:
            # If UTF-8 fails, try another encoding
            try:
                with open(self.env_path, 'r', encoding='latin-1') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            values[key.strip()] = value.strip()
                return values
            except Exception as e:
                print(f"Error loading .env values with latin-1 encoding: {str(e)}")
                return {}
        except Exception as e:
            print(f"Error loading .env values: {str(e)}")
            return {}
    
    def save_keys(self):
        """Save API keys to .env file"""
        try:
            # Create backup of current .env
            if os.path.exists(self.env_path):
                backup_path = f"{self.env_path}.bak"
                with open(self.env_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            # Load existing .env content to preserve comments and structure
            env_content = []
            if os.path.exists(self.env_path):
                with open(self.env_path, 'r', encoding='utf-8') as f:
                    env_content = f.readlines()
            
            # Update env_content with collected values
            env_content = self.collect_env_values(env_content)
            
            # Write updated content
            with open(self.env_path, 'w', encoding='utf-8') as f:
                f.writelines(env_content)
            
            # Emit signal that keys were saved
            self.keys_saved.emit()
            
            # Get the main window instance
            main_window = self.parent().parent()
            if main_window and hasattr(main_window, 'agent_threads'):
                # Get list of currently running agents
                running_agents = []
                for agent_name, thread in main_window.agent_threads.items():
                    if thread and thread.isRunning():
                        running_agents.append(agent_name)
                
                if running_agents:
                    main_window.console.append_message("API keys saved. Applying changes to running agents...", "system")
                    
                    # Restart each running agent
                    for agent_name in running_agents:
                        main_window.restart_agent(agent_name)
                    
                    main_window.console.append_message("All affected agents have been restarted with new API settings.", "success")
                
                # Simple notification that the configuration has been saved
                QMessageBox.information(self, "Saved", "API keys have been updated and applied.")
            else:
                QMessageBox.information(self, "Saved", "API keys have been saved successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving API keys: {str(e)}")
    
    def collect_env_values(self, env_content):
        """Collect API key values without saving to file - used by save function"""
        updated_keys = set()
        
        # Process each key field
        for key, field in self.key_fields.items():
            value = field.text()
            key_found = False
            
            # Update existing keys
            for i, line in enumerate(env_content):
                if line.strip() and not line.strip().startswith('#') and '=' in line:
                    line_key = line.strip().split('=', 1)[0].strip()
                    if line_key == key:
                        env_content[i] = f"{key}={value}\n"
                        key_found = True
                        break
            
            # Add new keys if not found
            if not key_found:
                env_content.append(f"{key}={value}\n")
            
            updated_keys.add(key)
            
        return env_content

    def test_connections(self):
        """Test API connections with the provided keys"""
        # Save keys first
        self.save_keys()
        
        success_count = 0
        failure_count = 0
        results = []
        
        # Test Anthropic
        anthropic_key = self.key_fields.get("ANTHROPIC_KEY", QLineEdit()).text()
        if anthropic_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_key)
                client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}]
                )
                results.append(("✅ Anthropic API: Connected successfully", True))
                success_count += 1
            except Exception as e:
                results.append((f"❌ Anthropic API: {str(e)}", False))
                failure_count += 1
        
        # Test OpenAI
        openai_key = self.key_fields.get("OPENAI_KEY", QLineEdit()).text()
        if openai_key:
            try:
                import openai
                client = openai.OpenAI(api_key=openai_key)
                client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10
                )
                results.append(("✅ OpenAI API: Connected successfully", True))
                success_count += 1
            except Exception as e:
                results.append((f"❌ OpenAI API: {str(e)}", False))
                failure_count += 1
        
        # Test Birdeye
        birdeye_key = self.key_fields.get("BIRDEYE_API_KEY", QLineEdit()).text()
        if birdeye_key:
            try:
                import requests
                headers = {"X-API-KEY": birdeye_key}
                response = requests.get(
                    "https://public-api.birdeye.so/public/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=1",
                    headers=headers
                )
                if response.status_code == 200:
                    results.append(("✅ Birdeye API: Connected successfully", True))
                    success_count += 1
                else:
                    results.append((f"❌ Birdeye API: Status code {response.status_code}", False))
                    failure_count += 1
            except Exception as e:
                results.append((f"❌ Birdeye API: {str(e)}", False))
                failure_count += 1
        
        # Display results
        result_dialog = QDialog(self)
        result_dialog.setWindowTitle("API Connection Test Results")
        result_dialog.setMinimumWidth(400)
        
        dialog_layout = QVBoxLayout(result_dialog)
        
        # Add summary
        summary = QLabel(f"Tests completed: {success_count} successful, {failure_count} failed")
        dialog_layout.addWidget(summary)
        
        # Add results
        for message, success in results:
            label = QLabel(message)
            label.setStyleSheet(f"color: {'green' if success else 'red'}")
            dialog_layout.addWidget(label)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(result_dialog.accept)
        dialog_layout.addWidget(close_button)
        
        result_dialog.exec_()

class AIConfigTab(QWidget):
    """Tab for configuring AI models and settings across all agents"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load current configuration values before setup_ui
        try:
            # Load AI settings from config.py
            from src.config import (
                AI_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS,
                COPYBOT_MIN_CONFIDENCE, COPYBOT_WALLET_ACTION_WEIGHT,
                BUY_CONFIDENCE_THRESHOLD, SELL_CONFIDENCE_THRESHOLD, 
                USE_AI_CONFIRMATION, ENABLE_CHART_ANALYSIS, ENABLE_STAKING_AI,
                RISK_LOSS_CONFIDENCE_THRESHOLD, RISK_GAIN_CONFIDENCE_THRESHOLD,
                COPYBOT_MODEL_OVERRIDE, CHART_MODEL_OVERRIDE, DCA_MODEL_OVERRIDE, RISK_MODEL_OVERRIDE,
                ENABLE_AI_ANALYSIS
            )
            
            # Store values
            self.ai_model = AI_MODEL
            self.ai_temperature = AI_TEMPERATURE
            self.ai_max_tokens = AI_MAX_TOKENS
            self.copybot_min_confidence = COPYBOT_MIN_CONFIDENCE
            self.copybot_wallet_action_weight = COPYBOT_WALLET_ACTION_WEIGHT
            self.buy_confidence_threshold = BUY_CONFIDENCE_THRESHOLD
            self.sell_confidence_threshold = SELL_CONFIDENCE_THRESHOLD
            self.use_ai_confirmation = USE_AI_CONFIRMATION
            self.enable_chart_analysis = ENABLE_CHART_ANALYSIS
            self.enable_staking_ai = ENABLE_STAKING_AI
            self.risk_loss_confidence_threshold = RISK_LOSS_CONFIDENCE_THRESHOLD
            self.risk_gain_confidence_threshold = RISK_GAIN_CONFIDENCE_THRESHOLD
            self.enable_ai_analysis = ENABLE_AI_ANALYSIS
            
            # Store model overrides
            self.copybot_model_override = COPYBOT_MODEL_OVERRIDE
            self.chart_model_override = CHART_MODEL_OVERRIDE
            self.dca_model_override = DCA_MODEL_OVERRIDE
            self.risk_model_override = RISK_MODEL_OVERRIDE
            
            # Track if we have overrides enabled
            self.copybot_override_enabled = COPYBOT_MODEL_OVERRIDE != AI_MODEL
            self.chart_override_enabled = CHART_MODEL_OVERRIDE != AI_MODEL
            self.staking_override_enabled = DCA_MODEL_OVERRIDE != AI_MODEL
            self.risk_override_enabled = RISK_MODEL_OVERRIDE != AI_MODEL
            
        except ImportError as e:
            print(f"Error importing AI config settings: {e}")
            # Set default values if import fails
            self.ai_model = "claude-3-haiku-20240307"
            self.ai_temperature = 0.8
            self.ai_max_tokens = 1024
            self.copybot_min_confidence = 80
            self.copybot_wallet_action_weight = 0.6
            self.buy_confidence_threshold = 60
            self.sell_confidence_threshold = 85
            self.use_ai_confirmation = True
            self.enable_chart_analysis = True
            self.enable_staking_ai = True
            self.enable_ai_analysis = True  # Default to enabled
            self.risk_loss_confidence_threshold = 90
            self.risk_gain_confidence_threshold = 60
            
            # Default model overrides
            self.copybot_model_override = "deepseek-reasoner"
            self.chart_model_override = "deepseek-reasoner"
            self.dca_model_override = "claude-3-haiku-20240307"
            self.risk_model_override = "claude-3-haiku-20240307"
            
            # Default override states
            self.copybot_override_enabled = True
            self.chart_override_enabled = True
            self.staking_override_enabled = False
            self.risk_override_enabled = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the AI configuration UI"""
        layout = QVBoxLayout(self)
        
        # Set the color scheme to blue and black
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
            QSlider::groove:horizontal {{
                border: 1px solid {CyberpunkColors.PRIMARY};
                height: 8px;
                background: {CyberpunkColors.BACKGROUND};
                margin: 2px 0;
            }}
            QSlider::handle:horizontal {{
                background: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }}
        """)
        
        # Create scroll area for all settings
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 1. Global AI Settings Section
        global_group = QGroupBox("Global AI Settings (Default for all agents)")
        global_layout = QVBoxLayout(global_group)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Default AI Model:"))
        self.global_model_combo = QComboBox()
        self.global_model_combo.addItems([
            "claude-3-haiku-20240307", 
            "claude-3-sonnet-20240229", 
            "claude-3-opus-20240229",
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4"
        ])
        self.global_model_combo.setCurrentText(self.ai_model)
        model_layout.addWidget(self.global_model_combo)
        global_layout.addLayout(model_layout)
        
        # Temperature setting
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Default Temperature:"))
        self.global_temp_slider = QSlider(Qt.Horizontal)
        self.global_temp_slider.setRange(0, 100)
        self.global_temp_slider.setValue(int(self.ai_temperature * 100))
        self.global_temp_slider.setTickPosition(QSlider.TicksBelow)
        self.global_temp_slider.setTickInterval(10)
        self.global_temp_label = QLabel(f"{self.ai_temperature:.1f}")
        self.global_temp_slider.valueChanged.connect(
            lambda v: self.global_temp_label.setText(f"{v/100:.1f}")
        )
        temp_layout.addWidget(self.global_temp_slider)
        temp_layout.addWidget(self.global_temp_label)
        global_layout.addLayout(temp_layout)
        
        # Max tokens setting
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(QLabel("Default Max Tokens:"))
        self.global_tokens_spin = QSpinBox()
        self.global_tokens_spin.setRange(100, 4000)
        self.global_tokens_spin.setValue(self.ai_max_tokens)
        self.global_tokens_spin.setSingleStep(100)
        tokens_layout.addWidget(self.global_tokens_spin)
        global_layout.addLayout(tokens_layout)
        
        scroll_layout.addWidget(global_group)
        
        # 2. CopyBot Agent Settings
        copybot_group = QGroupBox("CopyBot Agent AI Settings")
        copybot_layout = QVBoxLayout(copybot_group)
        
        # Enable/Disable AI for CopyBot
        self.copybot_ai_enabled = QCheckBox("Enable AI Analysis for CopyBot")
        self.copybot_ai_enabled.setChecked(self.enable_ai_analysis)
        copybot_layout.addWidget(self.copybot_ai_enabled)
        
        # Override global settings
        self.copybot_override = QCheckBox("Override Global Settings")
        self.copybot_override.setChecked(self.copybot_override_enabled)
        copybot_layout.addWidget(self.copybot_override)
        
        # Specific model
        copybot_model_layout = QHBoxLayout()
        copybot_model_layout.addWidget(QLabel("CopyBot AI Model:"))
        self.copybot_model_combo = QComboBox()
        self.copybot_model_combo.addItems([
            "claude-3-haiku-20240307", 
            "claude-3-sonnet-20240229", 
            "claude-3-opus-20240229",
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4"
        ])
        self.copybot_model_combo.setCurrentText(self.copybot_model_override)
        copybot_model_layout.addWidget(self.copybot_model_combo)
        copybot_layout.addLayout(copybot_model_layout)
        
        # Confidence threshold setting
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Analysis Confidence Threshold:"))
        self.copybot_confidence_slider = QSlider(Qt.Horizontal)
        self.copybot_confidence_slider.setRange(0, 100)
        self.copybot_confidence_slider.setValue(self.copybot_min_confidence)
        self.copybot_confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.copybot_confidence_slider.setTickInterval(10)
        self.copybot_confidence_label = QLabel(f"{self.copybot_min_confidence}%")
        self.copybot_confidence_slider.valueChanged.connect(
            lambda v: self.copybot_confidence_label.setText(f"{v}%")
        )
        confidence_layout.addWidget(self.copybot_confidence_slider)
        confidence_layout.addWidget(self.copybot_confidence_label)
        copybot_layout.addLayout(confidence_layout)
        
        # Wallet action weight setting
        wallet_weight_layout = QHBoxLayout()
        wallet_weight_layout.addWidget(QLabel("Wallet Action Weight:"))
        self.wallet_action_weight_slider = QSlider(Qt.Horizontal)
        self.wallet_action_weight_slider.setRange(0, 100)
        self.wallet_action_weight_slider.setValue(int(self.copybot_wallet_action_weight * 100))
        self.wallet_action_weight_slider.setTickPosition(QSlider.TicksBelow)
        self.wallet_action_weight_slider.setTickInterval(10)
        self.wallet_action_weight_label = QLabel(f"{int(self.copybot_wallet_action_weight * 100)}%")
        self.wallet_action_weight_slider.valueChanged.connect(
            lambda v: self.wallet_action_weight_label.setText(f"{v}%")
        )
        wallet_weight_layout.addWidget(self.wallet_action_weight_slider)
        wallet_weight_layout.addWidget(self.wallet_action_weight_label)
        copybot_layout.addLayout(wallet_weight_layout)
        
        
        scroll_layout.addWidget(copybot_group)
        
        # 3. Combined Chart Analysis & DCA System Settings
        dca_chart_group = QGroupBox("Advance DCA System AI Settings")
        dca_chart_layout = QVBoxLayout(dca_chart_group)
        
        # Enable/disable AI chart analysis recommendations
        self.chart_analysis_enabled = QCheckBox("Enable AI Chart Analysis Recommendations")
        self.chart_analysis_enabled.setChecked(self.enable_chart_analysis)
        dca_chart_layout.addWidget(self.chart_analysis_enabled)
        
        # Override global settings
        self.chart_override = QCheckBox("Override Global Settings")
        self.chart_override.setChecked(self.chart_override_enabled)
        dca_chart_layout.addWidget(self.chart_override)
        
        # Specific model
        chart_model_layout = QHBoxLayout()
        chart_model_layout.addWidget(QLabel("Chart Analysis AI Model:"))
        self.chart_model_combo = QComboBox()
        self.chart_model_combo.addItems([
            "claude-3-haiku-20240307", 
            "claude-3-sonnet-20240229", 
            "claude-3-opus-20240229",
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4"
        ])
        self.chart_model_combo.setCurrentText(self.chart_model_override)
        chart_model_layout.addWidget(self.chart_model_combo)
        dca_chart_layout.addLayout(chart_model_layout)
        
        # Add a divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet(f"background-color: {CyberpunkColors.PRIMARY}; max-height: 1px;")
        dca_chart_layout.addWidget(divider)
        
        # Add Staking AI Analysis section
        # Enable/disable AI staking analysis
        self.staking_analysis_enabled = QCheckBox("Enable AI Staking Analysis")
        self.staking_analysis_enabled.setChecked(self.enable_staking_ai)
        dca_chart_layout.addWidget(self.staking_analysis_enabled)
        
        # Override global settings for staking
        self.staking_override = QCheckBox("Override Global Settings for Staking")
        self.staking_override.setChecked(self.staking_override_enabled)
        dca_chart_layout.addWidget(self.staking_override)
        
        # Specific model for staking
        staking_model_layout = QHBoxLayout()
        staking_model_layout.addWidget(QLabel("Staking Analysis AI Model:"))
        self.staking_model_combo = QComboBox()
        self.staking_model_combo.addItems([
            "claude-3-haiku-20240307", 
            "claude-3-sonnet-20240229", 
            "claude-3-opus-20240229",
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4"
        ])
        self.staking_model_combo.setCurrentText(self.dca_model_override)
        staking_model_layout.addWidget(self.staking_model_combo)
        dca_chart_layout.addLayout(staking_model_layout)
        
        # Confidence thresholds for DCA
        buy_confidence_layout = QHBoxLayout()
        buy_confidence_layout.addWidget(QLabel("Buy Signal Confidence Threshold:"))
        self.dca_buy_confidence_slider = QSlider(Qt.Horizontal)
        self.dca_buy_confidence_slider.setRange(0, 100)
        self.dca_buy_confidence_slider.setValue(self.buy_confidence_threshold)
        self.dca_buy_confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.dca_buy_confidence_slider.setTickInterval(10)
        self.dca_buy_confidence_label = QLabel(f"{self.buy_confidence_threshold}%")
        self.dca_buy_confidence_slider.valueChanged.connect(
            lambda v: self.dca_buy_confidence_label.setText(f"{v}%")
        )
        buy_confidence_layout.addWidget(self.dca_buy_confidence_slider)
        buy_confidence_layout.addWidget(self.dca_buy_confidence_label)
        dca_chart_layout.addLayout(buy_confidence_layout)
        
        sell_confidence_layout = QHBoxLayout()
        sell_confidence_layout.addWidget(QLabel("Sell Signal Confidence Threshold:"))
        self.dca_sell_confidence_slider = QSlider(Qt.Horizontal)
        self.dca_sell_confidence_slider.setRange(0, 100)
        self.dca_sell_confidence_slider.setValue(self.sell_confidence_threshold)
        self.dca_sell_confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.dca_sell_confidence_slider.setTickInterval(10)
        self.dca_sell_confidence_label = QLabel(f"{self.sell_confidence_threshold}%")
        self.dca_sell_confidence_slider.valueChanged.connect(
            lambda v: self.dca_sell_confidence_label.setText(f"{v}%")
        )
        sell_confidence_layout.addWidget(self.dca_sell_confidence_slider)
        sell_confidence_layout.addWidget(self.dca_sell_confidence_label)
        dca_chart_layout.addLayout(sell_confidence_layout)
        
        scroll_layout.addWidget(dca_chart_group)
        
        # 5. Risk Agent Settings
        risk_group = QGroupBox("Risk Management Agent AI Settings")
        risk_layout = QVBoxLayout(risk_group)
        
        # AI confirmation for position closing
        self.risk_ai_confirmation = QCheckBox("Use AI Confirmation Before Closing Positions")
        self.risk_ai_confirmation.setChecked(self.use_ai_confirmation)
        risk_layout.addWidget(self.risk_ai_confirmation)
        
        # Override global settings
        self.risk_override = QCheckBox("Override Global Settings")
        self.risk_override.setChecked(self.risk_override_enabled)
        risk_layout.addWidget(self.risk_override)
        
        # Specific model for risk agent
        risk_model_layout = QHBoxLayout()
        risk_model_layout.addWidget(QLabel("Risk Agent AI Model:"))
        self.risk_model_combo = QComboBox()
        self.risk_model_combo.addItems([
            "claude-3-haiku-20240307", 
            "claude-3-sonnet-20240229", 
            "claude-3-opus-20240229",
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4"
        ])
        self.risk_model_combo.setCurrentText(self.risk_model_override)
        risk_model_layout.addWidget(self.risk_model_combo)
        risk_layout.addLayout(risk_model_layout)
        
        # Risk Loss Confidence threshold setting
        risk_loss_confidence_layout = QHBoxLayout()
        risk_loss_confidence_layout.addWidget(QLabel("Risk Loss Confidence Threshold:"))
        self.risk_loss_confidence_slider = QSlider(Qt.Horizontal)
        self.risk_loss_confidence_slider.setRange(0, 100)
        self.risk_loss_confidence_slider.setValue(self.risk_loss_confidence_threshold)
        self.risk_loss_confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.risk_loss_confidence_slider.setTickInterval(10)
        self.risk_loss_confidence_label = QLabel(f"{self.risk_loss_confidence_threshold}%")
        self.risk_loss_confidence_slider.valueChanged.connect(
            lambda v: self.risk_loss_confidence_label.setText(f"{v}%")
        )
        risk_loss_confidence_layout.addWidget(self.risk_loss_confidence_slider)
        risk_loss_confidence_layout.addWidget(self.risk_loss_confidence_label)
        risk_layout.addLayout(risk_loss_confidence_layout)
        
        # Risk Gain Confidence threshold setting
        risk_gain_confidence_layout = QHBoxLayout()
        risk_gain_confidence_layout.addWidget(QLabel("Risk Gain Confidence Threshold:"))
        self.risk_gain_confidence_slider = QSlider(Qt.Horizontal)
        self.risk_gain_confidence_slider.setRange(0, 100)
        self.risk_gain_confidence_slider.setValue(self.risk_gain_confidence_threshold)
        self.risk_gain_confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.risk_gain_confidence_slider.setTickInterval(10)
        self.risk_gain_confidence_label = QLabel(f"{self.risk_gain_confidence_threshold}%")
        self.risk_gain_confidence_slider.valueChanged.connect(
            lambda v: self.risk_gain_confidence_label.setText(f"{v}%")
        )
        risk_gain_confidence_layout.addWidget(self.risk_gain_confidence_slider)
        risk_gain_confidence_layout.addWidget(self.risk_gain_confidence_label)
        risk_layout.addLayout(risk_gain_confidence_layout)
        
        scroll_layout.addWidget(risk_group)
        
        # Add save button
        save_button = NeonButton("Save AI Configuration", CyberpunkColors.SUCCESS)
        save_button.clicked.connect(self.save_config)
        scroll_layout.addWidget(save_button)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
    
    def save_config(self):
        """Save AI configuration to config.py"""
        try:
            # Get correct path to config.py
            config_path = os.path.join(get_project_root(), 'src', 'config.py')
            
            # Read existing config file
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # Update AI configuration values in the config content
            config_content = self.collect_config(config_content)
            
            # Write updated config back to file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            # Force reload config module to apply changes immediately
            import sys
            import importlib
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            try:
                from src import config
                importlib.reload(config)
            except Exception as e:
                print(f"Warning: Could not reload configuration module: {str(e)}")
            
            # Determine which agents might be affected by the changes
            affected_agents = []
            if self.copybot_override.isChecked() or self.global_model_combo.currentText() != "claude-3-haiku-20240307":
                affected_agents.append("copybot")
            if self.chart_override.isChecked() or self.chart_analysis_enabled.isChecked():
                affected_agents.append("chart_analysis")
                affected_agents.append("dca")
            if self.staking_override.isChecked() or self.staking_analysis_enabled.isChecked():
                affected_agents.append("dca")
            if self.risk_override.isChecked() or self.risk_ai_confirmation.isChecked():
                affected_agents.append("risk_management")

            # Restart the affected agents for changes to take effect
            main_window = self.parent().parent()
            if main_window and hasattr(main_window, 'restart_agent') and affected_agents:
                main_window.console.append_message("AI configuration saved. Applying changes to affected agents...", "system")
                
                for agent_name in affected_agents:
                    main_window.restart_agent(agent_name)
                
                main_window.console.append_message("All affected agents have been restarted with new AI settings.", "success")
            
            # Simple notification that the configuration has been saved
            QMessageBox.information(self, "Saved", "AI configuration has been updated.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
    
    def collect_config(self, config_content):
        """Collect AI settings without saving to file - used by save function"""
        # Update the global AI values
        config_content = self.update_config_value(config_content, "AI_MODEL", f'"{self.global_model_combo.currentText()}"')
        config_content = self.update_config_value(config_content, "AI_TEMPERATURE", f"{float(self.global_temp_slider.value()) / 100}")
        config_content = self.update_config_value(config_content, "AI_MAX_TOKENS", f"{self.global_tokens_spin.value()}")
        
        # Update CopyBot AI values
        config_content = self.update_config_value(config_content, "COPYBOT_MIN_CONFIDENCE", f"{self.copybot_confidence_slider.value()}")
        config_content = self.update_config_value(config_content, "ENABLE_AI_ANALYSIS", f"{self.copybot_ai_enabled.isChecked()}")
        config_content = self.update_config_value(config_content, "COPYBOT_WALLET_ACTION_WEIGHT", f"{float(self.wallet_action_weight_slider.value()) / 100}")
        
        # Update DCA & Chart Analysis AI values
        config_content = self.update_config_value(config_content, "BUY_CONFIDENCE_THRESHOLD", f"{self.dca_buy_confidence_slider.value()}")
        config_content = self.update_config_value(config_content, "SELL_CONFIDENCE_THRESHOLD", f"{self.dca_sell_confidence_slider.value()}")
        
        # Update Risk Management AI values
        config_content = self.update_config_value(config_content, "USE_AI_CONFIRMATION", f"{self.risk_ai_confirmation.isChecked()}")
        config_content = self.update_config_value(config_content, "RISK_LOSS_CONFIDENCE_THRESHOLD", f"{self.risk_loss_confidence_slider.value()}")
        config_content = self.update_config_value(config_content, "RISK_GAIN_CONFIDENCE_THRESHOLD", f"{self.risk_gain_confidence_slider.value()}")
        
        # Add feature flags for AI capabilities
        config_content = self.update_config_value(config_content, "ENABLE_CHART_ANALYSIS", f"{self.chart_analysis_enabled.isChecked()}")
        config_content = self.update_config_value(config_content, "ENABLE_STAKING_AI", f"{self.staking_analysis_enabled.isChecked()}")
        
        # Add model override settings
        if self.copybot_override.isChecked():
            config_content = self.update_config_value(config_content, "COPYBOT_MODEL_OVERRIDE", f'"{self.copybot_model_combo.currentText()}"')
        else:
            config_content = self.update_config_value(config_content, "COPYBOT_MODEL_OVERRIDE", f'"{self.global_model_combo.currentText()}"')
        
        if self.chart_override.isChecked():
            config_content = self.update_config_value(config_content, "CHART_MODEL_OVERRIDE", f'"{self.chart_model_combo.currentText()}"')
        else:
            config_content = self.update_config_value(config_content, "CHART_MODEL_OVERRIDE", f'"{self.global_model_combo.currentText()}"')
        
        if self.staking_override.isChecked():
            config_content = self.update_config_value(config_content, "DCA_MODEL_OVERRIDE", f'"{self.staking_model_combo.currentText()}"')
        else:
            config_content = self.update_config_value(config_content, "DCA_MODEL_OVERRIDE", f'"{self.global_model_combo.currentText()}"')
        
        if self.risk_override.isChecked():
            config_content = self.update_config_value(config_content, "RISK_MODEL_OVERRIDE", f'"{self.risk_model_combo.currentText()}"')
        else:
            config_content = self.update_config_value(config_content, "RISK_MODEL_OVERRIDE", f'"{self.global_model_combo.currentText()}"')
        
        return config_content

    def update_config_value(self, content, key, value, multiline=False):
        """Helper function to update a value in the config file content"""
        import re
        
        # If this is a multiline value (like a prompt), handle differently
        if multiline:
            # Match the entire assignment including the triple-quoted string
            pattern = rf'{key}\s*=\s*"""[\s\S]*?"""'
            replacement = f'{key} = {value}'
            
            if re.search(pattern, content, re.DOTALL):
                return re.sub(pattern, replacement, content, flags=re.DOTALL)
            else:
                # If the key doesn't exist, add it to the end of the file
                return f'{content}\n{key} = {value}'
        
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