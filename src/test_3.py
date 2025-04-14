import logging
from PySide6.QtWidgets import QLayout  # Add this import for QLayout

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the constant from test_2.py or define it here
AGENT_CARD_FIXED_HEIGHT = 180

class AgentStatusCard(NeonFrame):
    def __init__(self, agent_name, color, parent=None):
        super().__init__(color, parent)
        self.agent_name = agent_name
        self.color = QColor(color)
        self.status = "Inactive"
        self.last_run = "Never"
        self.next_run = "Not scheduled"
        self.resize_scheduled = False
        
        logging.debug(f"AgentStatusCard.__init__: Initializing card for {agent_name}")
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)  # Reduce spacing between elements
        
        # Agent name header
        self.name_label = QLabel(agent_name)
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-family: 'Orbitron', sans-serif;
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.name_label)
        
        # Status indicator
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_label = QLabel(self.status)
        self.status_label.setStyleSheet(f"color: {CyberpunkColors.DANGER};")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Last run
        last_run_layout = QHBoxLayout()
        last_run_layout.addWidget(QLabel("Last Run:"))
        self.last_run_label = QLabel(self.last_run)
        last_run_layout.addWidget(self.last_run_label)
        last_run_layout.addStretch()
        layout.addLayout(last_run_layout)
        
        # Next run
        next_run_layout = QHBoxLayout()
        next_run_layout.addWidget(QLabel("Next Run:"))
        self.next_run_label = QLabel(self.next_run)
        next_run_layout.addWidget(self.next_run_label)
        next_run_layout.addStretch()
        layout.addLayout(next_run_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: 1px solid {color};
                border-radius: 2px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = NeonButton("Start", CyberpunkColors.SUCCESS)
        self.stop_button = NeonButton("Stop", CyberpunkColors.DANGER)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)
        
        # Set default styling
        self.setStyleSheet(f"""
            QLabel {{
                color: {CyberpunkColors.TEXT_LIGHT};
                font-family: 'Rajdhani', sans-serif;
            }}
        """)
        
        # Explicitly set size policy to prevent stretching
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # Set fixed height using the constant
        self.setMaximumHeight(AGENT_CARD_FIXED_HEIGHT)
        self.setFixedHeight(AGENT_CARD_FIXED_HEIGHT)
        # Set fixed size policy to make it more strict
        self.setMinimumHeight(AGENT_CARD_FIXED_HEIGHT)
        
        logging.debug(f"AgentStatusCard.__init__: Set fixed height to {AGENT_CARD_FIXED_HEIGHT} for {agent_name}")
        
        # Start a timer to enforce size constraints - use a slightly faster interval
        self.size_timer = QTimer(self)
        self.size_timer.timeout.connect(self.enforce_size_constraints)
        self.size_timer.start(100)  # Check every 100ms
        
        # Add layout constraint to prevent vertical growth
        layout.setSizeConstraint(QLayout.SetFixedSize)
        
    def enforce_size_constraints(self):
        """Enforce size constraints to prevent expansion"""
        current_height = self.height()
        
        # Only log if height is wrong or has changed
        if current_height != AGENT_CARD_FIXED_HEIGHT:
            logging.warning(f"AgentStatusCard.enforce_size_constraints: Height expanded to {current_height} for {self.agent_name}, resetting to {AGENT_CARD_FIXED_HEIGHT}")
            
            # Avoid scheduling multiple resets - only reset if no reset is already scheduled
            if not self.resize_scheduled:
                self.resize_scheduled = True
                # Apply reset in the next event loop iteration to avoid layout conflicts
                QTimer.singleShot(0, self.reset_height)
            
    def reset_height(self):
        """Reset height to fixed value"""
        try:
            self.setFixedHeight(AGENT_CARD_FIXED_HEIGHT)
            self.updateGeometry()  # Force layout recalculation
            logging.debug(f"AgentStatusCard.reset_height: Reset {self.agent_name} height to {AGENT_CARD_FIXED_HEIGHT}")
        finally:
            self.resize_scheduled = False
            
    def resizeEvent(self, event):
        """Handle resize events"""
        old_size = event.oldSize()
        new_size = event.size()
        
        # Only log if height changed
        if old_size.height() != new_size.height():
            logging.debug(f"AgentStatusCard.resizeEvent: {self.agent_name} resized from {old_size.width()}x{old_size.height()} to {new_size.width()}x{new_size.height()}")
        
        super().resizeEvent(event)
        
        # Reset fixed height if it changed, but don't keep scheduling resets if already scheduled
        if new_size.height() != AGENT_CARD_FIXED_HEIGHT and not self.resize_scheduled:
            logging.warning(f"AgentStatusCard.resizeEvent: Height changed to {new_size.height()} for {self.agent_name}, scheduling reset to {AGENT_CARD_FIXED_HEIGHT}")
            self.resize_scheduled = True
            QTimer.singleShot(0, self.reset_height)
        
    def showEvent(self, event):
        """Handle show events"""
        logging.debug(f"AgentStatusCard.showEvent: {self.agent_name} shown with height {self.height()}")
        super().showEvent(event)
        
        # Apply fixed height when shown
        if self.height() != AGENT_CARD_FIXED_HEIGHT:
            logging.debug(f"AgentStatusCard.showEvent: Setting fixed height to {AGENT_CARD_FIXED_HEIGHT} for {self.agent_name}")
            self.setFixedHeight(AGENT_CARD_FIXED_HEIGHT)
            self.updateGeometry()  # Force layout recalculation
        
    def start_agent(self):
        logging.debug(f"AgentStatusCard.start_agent: Starting agent {self.agent_name}")
        self.status = "Active"
        self.status_label.setText(self.status)
        self.status_label.setStyleSheet(f"color: {CyberpunkColors.SUCCESS};")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Update last run time
        self.last_run = datetime.now().strftime("%H:%M:%S")
        self.last_run_label.setText(self.last_run)
        
        # Update next run time (example: 30 minutes from now)
        next_run_time = datetime.now() + timedelta(minutes=30)
        self.next_run = next_run_time.strftime("%H:%M:%S")
        self.next_run_label.setText(self.next_run)
        
        # Simulate progress - faster completion
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()  # Stop existing timer if it's running
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(50)  # Make it faster (50ms instead of 100ms)
        
        # Ensure height is correct after starting
        self.setFixedHeight(AGENT_CARD_FIXED_HEIGHT)
        
    def stop_agent(self):
        logging.debug(f"AgentStatusCard.stop_agent: Stopping agent {self.agent_name}")
        # Immediately update UI to show stopping state
        self.status = "Stopping..."
        self.status_label.setText(self.status)
        self.status_label.setStyleSheet(f"color: {CyberpunkColors.WARNING};")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        # Immediately clear progress bar
        self.progress_bar.setValue(0)
        
        # Stop timer if running
        if hasattr(self, 'timer') and self.timer.isActive():
            logging.debug(f"AgentStatusCard.stop_agent: Stopping progress timer for {self.agent_name}")
            self.timer.stop()
        
        # Queue actual stop to happen after UI updates
        QTimer.singleShot(100, self._complete_stop)
        
        # Ensure height is correct after stopping
        self.setFixedHeight(AGENT_CARD_FIXED_HEIGHT)
    
    def _complete_stop(self):
        logging.debug(f"AgentStatusCard._complete_stop: Completing stop for {self.agent_name}")
        # Complete the stop process after UI has updated
        self.status = "Inactive"
        self.status_label.setText(self.status)
        self.status_label.setStyleSheet(f"color: {CyberpunkColors.DANGER};")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Ensure progress bar is reset
        self.progress_bar.setValue(0)
        
        # Ensure height is correct after complete stop
        self.setFixedHeight(AGENT_CARD_FIXED_HEIGHT)
        
    def update_progress(self):
        current_value = self.progress_bar.value()
        if current_value >= 100:
            # Stop the timer once we reach 100% instead of resetting to 0
            if hasattr(self, 'timer') and self.timer.isActive():
                logging.debug(f"AgentStatusCard.update_progress: Reached 100% for {self.agent_name}, stopping timer")
                self.timer.stop()
        else:
            # Update faster for a quick flash - increase the increment
            new_value = current_value + 5  # Increment by 5 instead of 1 for faster progress
            logging.debug(f"AgentStatusCard.update_progress: Updating progress for {self.agent_name}: {current_value} -> {new_value}")
            self.progress_bar.setValue(new_value)
            
    def update_status(self, status_data):
        """Update card with real agent status data"""
        logging.debug(f"AgentStatusCard.update_status: Updating status for {self.agent_name}: {status_data}")
        
        # Force stop any running timer first to prevent race conditions
        if hasattr(self, 'timer') and self.timer.isActive():
            logging.debug(f"AgentStatusCard.update_status: Stopping running timer for {self.agent_name}")
            self.timer.stop()
            
        if 'status' in status_data:
            self.status = status_data['status']
            self.status_label.setText(self.status)
            if self.status == "Active" or self.status == "Running":
                self.status_label.setStyleSheet(f"color: {CyberpunkColors.SUCCESS};")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
            else:
                self.status_label.setStyleSheet(f"color: {CyberpunkColors.DANGER};")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                # Always reset progress bar when not active
                if self.status != "Running" and self.status != "Active":
                    logging.debug(f"AgentStatusCard.update_status: Resetting progress bar for {self.agent_name} (status: {self.status})")
                    self.progress_bar.setValue(0)
                
        if 'last_run' in status_data:
            self.last_run = status_data['last_run']
            self.last_run_label.setText(self.last_run)
            
        if 'next_run' in status_data:
            self.next_run = status_data['next_run']
            self.next_run_label.setText(self.next_run)
            
        if 'progress' in status_data:
            # Only update progress bar if status is Active or Running
            if self.status == "Active" or self.status == "Running":
                logging.debug(f"AgentStatusCard.update_status: Setting progress for {self.agent_name} to {status_data['progress']}%")
                self.progress_bar.setValue(status_data['progress'])
            else:
                logging.debug(f"AgentStatusCard.update_status: Resetting progress bar for {self.agent_name} (status: {self.status})")
                self.progress_bar.setValue(0)
        
        # Always ensure height is correct after any status update
        current_height = self.height()
        if current_height != AGENT_CARD_FIXED_HEIGHT:
            logging.warning(f"AgentStatusCard.update_status: Height incorrect ({current_height}) for {self.agent_name}, fixing to {AGENT_CARD_FIXED_HEIGHT}")
            self.setFixedHeight(AGENT_CARD_FIXED_HEIGHT)
            self.updateGeometry()  # Force layout recalculation
                
    @Slot(str, int)
    def update_status_from_params(self, status, progress=None, last_run=None, next_run=None):
        """Update status directly from parameters for thread-safe updates"""
        logging.debug(f"AgentStatusCard.update_status_from_params: Updating {self.agent_name} with status={status}, progress={progress}")
        
        status_data = {"status": status}
        if progress is not None:
            status_data["progress"] = progress
        if last_run is not None:
            status_data["last_run"] = last_run
        if next_run is not None:
            status_data["next_run"] = next_run
            
        self.update_status(status_data)



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