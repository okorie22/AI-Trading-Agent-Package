# Then modify ConsoleOutput class
class ConsoleOutput(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0A0A0A;
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                font-family: 'Share Tech Mono', monospace;
                padding: 10px;
            }}
        """)
        
        # Maximum lines to prevent UI stretching
        self.max_lines = 500
        
    def append_message(self, message, message_type="info"):
        color_map = {
            "info": CyberpunkColors.TEXT_LIGHT,
            "success": CyberpunkColors.SUCCESS,
            "warning": CyberpunkColors.WARNING,
            "error": CyberpunkColors.DANGER,
            "system": CyberpunkColors.PRIMARY
        }
        color = color_map.get(message_type, CyberpunkColors.TEXT_LIGHT)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append(f'<span style="color:{color};">[{timestamp}] {message}</span>')
        
        # Limit console log size to prevent UI stretching
        doc = self.document()
        if doc.blockCount() > self.max_lines:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # Remove the newline

class PortfolioViz(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        
        # Add paper trading mode flag
        self.is_paper_trading = False
        try:
            from src.config import PAPER_TRADING_ENABLED
            self.is_paper_trading = PAPER_TRADING_ENABLED
        except:
            pass
        
        # Wallet balance label (right side)
        self.wallet_label = QLabel("CASH: $0.00", parent=self)
        self.wallet_label.setStyleSheet("""
            background-color: rgba(0, 255, 255, 30);
            color: #00FFFF;
            font-family: Rajdhani;
            font-size: 12pt;
            font-weight: bold;
            padding: 10px;
            border: 1px solid #00FFFF;
        """)
        self.wallet_label.setAlignment(Qt.AlignCenter)
        self.wallet_label.setFixedSize(220, 40)
        
        # Add cash reserve health bar (below balance label)
        self.cash_reserve_bar = QProgressBar(parent=self)
        self.cash_reserve_bar.setRange(0, 100)
        self.cash_reserve_bar.setValue(100)  # Default to full
        self.cash_reserve_bar.setTextVisible(True)
        self.cash_reserve_bar.setFormat("Cash Reserve: %p%")
        self.cash_reserve_bar.setFixedSize(220, 20)
        self.cash_reserve_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(0, 255, 255, 10);
                color: #FFFFFF;
                font-family: Rajdhani;
                font-size: 8pt;
                font-weight: bold;
                border: 1px solid #00FFFF;
                border-radius: 2px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: rgba(0, 255, 255, 80);
            }
        """)
        
        # Add PnL label (left side) with the same styling
        self.pnl_label = QLabel("PNL: $0.00", parent=self)
        self.pnl_label.setStyleSheet("""
            background-color: rgba(0, 255, 255, 30);
            color: #00FFFF;
            font-family: Rajdhani;
            font-size: 12pt;
            font-weight: bold;
            padding: 10px;
            border: 1px solid #00FFFF;
        """)
        self.pnl_label.setAlignment(Qt.AlignCenter)
        self.pnl_label.setFixedSize(220, 40)
        
        # Add refresh button
        self.refresh_button = QPushButton("🔄", parent=self)
        self.refresh_button.setToolTip("Refresh financial data")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 255, 255, 30);
                color: #00FFFF;
                font-size: 14pt;
                border: 1px solid #00FFFF;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 60);
            }
        """)
        self.refresh_button.setFixedSize(24, 24)
        
        # Position all elements
        self.wallet_label.move(self.width() - 240, 20)
        self.cash_reserve_bar.move(self.width() - 240, 65)  # Position below balance label
        self.pnl_label.move(20, 20)  # 20px from left edge
        self.refresh_button.move(self.width() - 260, 28)  # Position next to wallet label
        
        # Initialize cash reserve percentage (derived from CASH_PERCENTAGE in config)
        self.cash_reserve_pct = 100  # Default to 100%
        self.target_cash_pct = 20     # Default to 20% from config
        
        # Make sure labels get repositioned if window resizes
        self.resizeEvent = self.on_resize
        
        # Rest of your initialization code
        self.tokens = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(50)  # Update every 50ms for animation
        self.animation_offset = 0
        
    def on_resize(self, event):
        # Reposition all elements when window is resized
        self.wallet_label.move(self.width() - 240, 20)
        self.cash_reserve_bar.move(self.width() - 240, 65)  # Position below balance label
        self.pnl_label.move(20, 20)
        self.refresh_button.move(self.width() - 260, 28)  # Position next to wallet label
        
    def set_wallet_balance(self, balance):
        """Set current wallet balance for display"""
        # Add PAPER prefix if in paper trading mode
        prefix = "[P] " if self.is_paper_trading else ""
        self.wallet_label.setText(f"{prefix}CASH: ${balance:.2f}")
        
        # Change color if in paper trading mode
        if self.is_paper_trading:
            self.wallet_label.setStyleSheet(f"""
                background-color: rgba(255, 0, 255, 30);
                color: {CyberpunkColors.SECONDARY};
                font-family: Rajdhani;
                font-size: 12pt;
                font-weight: bold;
                padding: 10px;
                border: 1px solid {CyberpunkColors.SECONDARY};
            """)
        else:
            self.wallet_label.setStyleSheet(f"""
                background-color: rgba(0, 255, 255, 30);
                color: {CyberpunkColors.PRIMARY};
                font-family: Rajdhani;
                font-size: 12pt;
                font-weight: bold;
                padding: 10px;
                border: 1px solid {CyberpunkColors.PRIMARY};
            """)
        
    def set_pnl(self, pnl):
        """Set current PnL for display"""
        # Add PAPER prefix if in paper trading mode
        display_prefix = "[P] " if self.is_paper_trading else ""
        
        # Change color based on positive/negative PnL
        if pnl >= 0:
            # Paper trading modifies the color
            if self.is_paper_trading:
                self.pnl_label.setStyleSheet(f"""
                    background-color: rgba(255, 0, 255, 30);
                    color: {CyberpunkColors.SECONDARY};
                    font-family: Rajdhani;
                    font-size: 12pt;
                    font-weight: bold;
                    padding: 10px;
                    border: 1px solid {CyberpunkColors.SECONDARY};
                """)
            else:
                self.pnl_label.setStyleSheet("""
                    background-color: rgba(51, 255, 51, 30);
                    color: #33FF33;
                    font-family: Rajdhani;
                    font-size: 12pt;
                    font-weight: bold;
                    padding: 10px;
                    border: 1px solid #33FF33;
                """)
            value_prefix = "+"
        else:
            # Paper trading modifies the color
            if self.is_paper_trading:
                self.pnl_label.setStyleSheet(f"""
                    background-color: rgba(255, 0, 255, 30);
                    color: {CyberpunkColors.SECONDARY};
                    font-family: Rajdhani;
                    font-size: 12pt;
                    font-weight: bold;
                    padding: 10px;
                    border: 1px solid {CyberpunkColors.SECONDARY};
                """)
            else:
                self.pnl_label.setStyleSheet("""
                    background-color: rgba(255, 0, 51, 30);
                    color: #FF0033;
                    font-family: Rajdhani;
                    font-size: 12pt;
                    font-weight: bold;
                    padding: 10px;
                    border: 1px solid #FF0033;
                """)
            value_prefix = ""
            
        self.pnl_label.setText(f"{display_prefix}PNL: {value_prefix}${pnl:.2f}")
        
    def set_portfolio_data(self, tokens):
        """
        Set portfolio data for visualization
        tokens: list of dicts with keys: name, allocation, performance, volatility
        """
        self.tokens = tokens
        self.update()
        
    def set_paper_trading_mode(self, is_paper_trading):
        """Update paper trading mode flag"""
        self.is_paper_trading = is_paper_trading
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(CyberpunkColors.BACKGROUND))
        
        # Draw grid lines
        pen = QPen(QColor(CyberpunkColors.PRIMARY).darker(300))
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Draw horizontal grid lines
        for i in range(0, self.height(), 20):
            painter.drawLine(0, i, self.width(), i)
            
        # Draw vertical grid lines
        for i in range(0, self.width(), 20):
            painter.drawLine(i, 0, i, self.height())
            
        # Draw tokens if we have data
        if not self.tokens:
            # Draw placeholder text
            painter.setPen(QColor(CyberpunkColors.TEXT_LIGHT))
            painter.setFont(QFont("Rajdhani", 14))
            mode_text = "PAPER TRADING MODE" if self.is_paper_trading else ""
            painter.drawText(self.rect(), Qt.AlignCenter, f"Portfolio Visualization\n{mode_text}\n(No data available)")
            return
            
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) * 0.8
        
        # Update animation offset
        self.animation_offset = (self.animation_offset + 1) % 360
        
        # Draw central hub - use secondary color for paper trading
        hub_radius = 30
        hub_color = QColor(CyberpunkColors.SECONDARY if self.is_paper_trading else CyberpunkColors.PRIMARY)
        
        # Draw hub glow
        for i in range(3):
            glow_size = hub_radius + (3-i)*4
            painter.setPen(Qt.NoPen)
            glow_color = QColor(hub_color)
            glow_color.setAlpha(50 - i*15)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(int(center_x - glow_size/2), int(center_y - glow_size/2), 
                               int(glow_size), int(glow_size))
        
        # Draw hub
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(hub_color))
        painter.drawEllipse(int(center_x - hub_radius/2), int(center_y - hub_radius/2), 
                           int(hub_radius), int(hub_radius))
        
        # Draw tokens in a circular pattern
        angle_step = 360 / len(self.tokens)
        current_angle = self.animation_offset * 0.1  # Slow rotation
        
        for token in self.tokens:
            # Calculate position
            x = center_x + radius * 0.8 * math.cos(math.radians(current_angle))
            y = center_y + radius * 0.8 * math.sin(math.radians(current_angle))
            
            # Determine color based on performance and paper trading mode
            if self.is_paper_trading:
                # In paper trading mode, use purple color scheme
                color = QColor(CyberpunkColors.SECONDARY)
            else:
                # Normal mode uses existing color logic
                if token.get('performance', 0) > 0:
                    color = QColor(CyberpunkColors.SUCCESS)
                elif token.get('performance', 0) < 0:
                    color = QColor(CyberpunkColors.DANGER)
                else:
                    color = QColor(CyberpunkColors.PRIMARY)
                
            # Determine size based on allocation
            size = 10 + (token.get('allocation', 1) * 40)
            
            # Add pulsing effect based on volatility
            volatility = token.get('volatility', 0.05)
            pulse = math.sin(math.radians(self.animation_offset * 4 * volatility)) * 5
            size += pulse
            
            # Draw connection line to center
            pen = QPen(color.darker(200))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(int(center_x), int(center_y), int(x), int(y))
            
            # Draw token circle with glow effect
            # First draw glow
            for i in range(3):
                glow_size = size + (3-i)*4
                painter.setPen(Qt.NoPen)
                glow_color = QColor(color)
                glow_color.setAlpha(50 - i*15)
                painter.setBrush(QBrush(glow_color))
                painter.drawEllipse(int(x - glow_size/2), int(y - glow_size/2), 
                                   int(glow_size), int(glow_size))
            
            # Then draw main circle
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(x - size/2), int(y - size/2), int(size), int(size))
            
            # Draw token name with [P] prefix for paper trading
            token_name = token.get('name', '')
            if self.is_paper_trading:
                token_name = f"[P] {token_name}"
                
            painter.setPen(QColor(CyberpunkColors.TEXT_WHITE))
            painter.setFont(QFont("Rajdhani", 8, QFont.Bold))
            text_rect = painter.boundingRect(int(x - 50), int(y + size/2 + 5), 
                                           100, 20, Qt.AlignCenter, token_name)
            painter.drawText(text_rect, Qt.AlignCenter, token_name)
            
            # Draw allocation percentage
            allocation_text = f"{token.get('allocation', 0)*100:.1f}%"
            perf_text = f"{token.get('performance', 0)*100:+.1f}%"
            combined_text = f"{allocation_text} ({perf_text})"
            
            text_rect = painter.boundingRect(int(x - 50), int(y + size/2 + 25), 
                                           100, 20, Qt.AlignCenter, combined_text)
            painter.drawText(text_rect, Qt.AlignCenter, combined_text)
            
            current_angle += angle_step

    # Add this method to the PortfolioViz class
    def set_cash_reserve(self, reserve_pct, target_pct=None):
        """Set cash reserve percentage and update health bar
        
        Args:
            reserve_pct: Current cash reserve as percentage of total portfolio
            target_pct: Target cash reserve percentage (from config)
        """
        # Create the cash reserve bar if it doesn't exist yet
        if not hasattr(self, 'cash_reserve_bar'):
            self.cash_reserve_bar = QProgressBar(parent=self)
            self.cash_reserve_bar.setRange(0, 100)
            self.cash_reserve_bar.setValue(100)
            self.cash_reserve_bar.setTextVisible(True)
            self.cash_reserve_bar.setFormat("Cash Reserve: %p%")
            self.cash_reserve_bar.setFixedSize(220, 20)
            self.cash_reserve_bar.setStyleSheet("""
                QProgressBar {
                    background-color: rgba(0, 255, 255, 10);
                    color: #FFFFFF;
                    font-family: Rajdhani;
                    font-size: 8pt;
                    font-weight: bold;
                    border: 1px solid #00FFFF;
                    border-radius: 2px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: rgba(0, 255, 255, 80);
                }
            """)
            # Position the bar
            self.cash_reserve_bar.move(self.width() - 240, 65)
            
            # Update on_resize to handle the cash reserve bar
            original_on_resize = self.on_resize
            def new_on_resize(event):
                original_on_resize(event)
                self.cash_reserve_bar.move(self.width() - 240, 65)
            self.on_resize = new_on_resize
            
        # Calculate the target cash percentage if provided
        target = target_pct if target_pct is not None else 20
        
        # Calculate percentage of target (100% = at target, >100% = above target)
        target_ratio = min(int((reserve_pct / target) * 100), 100)
        
        # Update the progress bar
        self.cash_reserve_bar.setValue(target_ratio)
        
        # Set the format text with PAPER prefix for paper trading
        prefix = "[P] " if self.is_paper_trading else ""
        self.cash_reserve_bar.setFormat(f"{prefix}Cash Reserve: {reserve_pct:.1f}%")
        
        # Update bar color based on status and paper trading mode
        bar_color = CyberpunkColors.SECONDARY if self.is_paper_trading else CyberpunkColors.PRIMARY
        danger_color = CyberpunkColors.SECONDARY if self.is_paper_trading else CyberpunkColors.DANGER
        warning_color = CyberpunkColors.SECONDARY if self.is_paper_trading else CyberpunkColors.WARNING

        if target_ratio < 50:
            # Red/Purple if below 50% of target
            self.cash_reserve_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: rgba(255, 0, 255, 10);
                    color: #FFFFFF;
                    font-family: Rajdhani;
                    font-size: 8pt;
                    font-weight: bold;
                    border: 1px solid {danger_color};
                    border-radius: 2px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: rgba(255, 0, 255, 80);
                }}
            """) if self.is_paper_trading else self.cash_reserve_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: rgba(255, 0, 51, 10);
                    color: #FFFFFF;
                    font-family: Rajdhani;
                    font-size: 8pt;
                    font-weight: bold;
                    border: 1px solid {danger_color};
                    border-radius: 2px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: rgba(255, 0, 51, 80);
                }}
            """)
        elif target_ratio < 80:
            # Orange/Purple if between 50% and 80% of target
            self.cash_reserve_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: rgba(255, 0, 255, 10);
                    color: #FFFFFF;
                    font-family: Rajdhani;
                    font-size: 8pt;
                    font-weight: bold;
                    border: 1px solid {warning_color};
                    border-radius: 2px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: rgba(255, 0, 255, 80);
                }}
            """) if self.is_paper_trading else self.cash_reserve_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: rgba(255, 102, 0, 10);
                    color: #FFFFFF;
                    font-family: Rajdhani;
                    font-size: 8pt;
                    font-weight: bold;
                    border: 1px solid {warning_color};
                    border-radius: 2px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: rgba(255, 102, 0, 80);
                }}
            """)
        else:
            # Blue/Purple (same as other UI elements) if at least 80% of target
            self.cash_reserve_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: rgba(255, 0, 255, 10);
                    color: #FFFFFF;
                    font-family: Rajdhani;
                    font-size: 8pt;
                    font-weight: bold;
                    border: 1px solid {bar_color};
                    border-radius: 2px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: rgba(255, 0, 255, 80);
                }}
            """) if self.is_paper_trading else self.cash_reserve_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: rgba(0, 255, 255, 10);
                    color: #FFFFFF;
                    font-family: Rajdhani;
                    font-size: 8pt;
                    font-weight: bold;
                    border: 1px solid {bar_color};
                    border-radius: 2px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: rgba(0, 255, 255, 80);
                }}
            """)

class AgentStatusCard(NeonFrame):
    def __init__(self, agent_name, color, parent=None):
        super().__init__(color, parent)
        self.agent_name = agent_name
        self.color = QColor(color)
        self.status = "Inactive"
        self.last_run = "Never"
        self.next_run = "Not scheduled"
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
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
        self.setMaximumHeight(200)  # Add explicit maximum height

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        # No debug logging needed
        
    def start_agent(self):
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
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(50)  # Make it faster (50ms instead of 100ms)
        
    def stop_agent(self):
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
            self.timer.stop()
        
        # Queue actual stop to happen after UI updates
        QTimer.singleShot(100, self._complete_stop)
    
    def _complete_stop(self):
        # Complete the stop process after UI has updated
        self.status = "Inactive"
        self.status_label.setText(self.status)
        self.status_label.setStyleSheet(f"color: {CyberpunkColors.DANGER};")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Ensure progress bar is reset
        self.progress_bar.setValue(0)
        
    def update_progress(self):
        current_value = self.progress_bar.value()
        if current_value >= 100:
            # Stop the timer once we reach 100% instead of resetting to 0
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
        else:
            # Update faster for a quick flash - increase the increment
            self.progress_bar.setValue(current_value + 5)  # Increment by 5 instead of 1 for faster progress
            
    def update_status(self, status_data):
        """Update card with real agent status data"""
        # Force stop any running timer first to prevent race conditions
        if hasattr(self, 'timer') and self.timer.isActive():
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
                self.progress_bar.setValue(status_data['progress'])
            else:
                self.progress_bar.setValue(0)
                
    @Slot(str, int)
    def update_status_from_params(self, status, progress=None, last_run=None, next_run=None):
        """Update status directly from parameters for thread-safe updates"""
        status_data = {"status": status}
        if progress is not None:
            status_data["progress"] = progress
        if last_run is not None:
            status_data["last_run"] = last_run
        if next_run is not None:
            status_data["next_run"] = next_run
            
        self.update_status(status_data)
        
class AgentWorker(QObject):
    """Worker thread for running agents"""
    status_update = Signal(str, dict)  # agent_name, status_data
    console_message = Signal(str, str)  # message, message_type
    portfolio_update = Signal(list)  # token_data
    analysis_complete = Signal(str, str, str, str, str, str, str, str, str)  # timestamp, action, token, token_symbol, analysis, confidence, price, change_percent, token_mint
    changes_detected = Signal(dict)  # changes dictionary from TokenAccountTracker
    order_executed = Signal(str, str, str, float, float, bool, float, object, str, str, str)  # agent_name, action, token, amount, entry_price, is_paper_trade, exit_price, pnl, wallet_address, mint_address, ai_analysis
    
    def __init__(self, agent_name, agent_module_path, parent=None):
        super().__init__(parent)
        self.agent_name = agent_name
        self.agent_module_path = agent_module_path
        self.running = False
        self.agent = None
        self.force_run = False
        
        # Add paper trading mode flag
        try:
            # Import config to check paper trading mode
            sys.path.append(str(Path(agent_module_path).parent.parent))
            from src.config import PAPER_TRADING_ENABLED
            self.is_paper_trading = PAPER_TRADING_ENABLED
        except:
            self.is_paper_trading = False
            self.console_message.emit("Could not determine paper trading mode, defaulting to live trading", "warning")
        
    def run(self):
        """Run the agent in a separate thread"""
        self.running = True  # Set running flag at the start
        original_handlers = []
        
        # Store original minimum and maximum size
        main_window = self.parent()
        original_min_size = None
        original_max_size = None
        
        if main_window and hasattr(main_window, 'size'):
            # Store original constraints
            current_size = main_window.size()
            if hasattr(main_window, 'minimumSize'):
                original_min_size = main_window.minimumSize()
            if hasattr(main_window, 'maximumSize'):
                original_max_size = main_window.maximumSize()
            
            # Set constraints that prevent unwanted expansion but allow limited resizing
            main_window.setMinimumSize(current_size.width() - 50, current_size.height() - 50)
            main_window.setMaximumSize(current_size.width() + 50, current_size.height() + 50)
            # Do not use setFixedSize to allow for some manual resizing
            
            # Force update to ensure constraints are applied
            QApplication.processEvents()
        
        try:
            import importlib.util
            import sys
            from datetime import datetime, timedelta
            import logging
            
            # Import the agent module
            spec = importlib.util.spec_from_file_location("agent_module", self.agent_module_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["agent_module"] = module
            spec.loader.exec_module(module)
            
            # Signal start
            self.console_message.emit(f"Starting {self.agent_name}...", "info")
            
            # Redirect logging to console UI
            if hasattr(logging.getLogger(), 'handlers'):
                # Store original handlers
                original_handlers = logging.getLogger().handlers.copy()
                
                # Create a custom handler that emits signals
                class UIConsoleHandler(logging.Handler):
                    def __init__(self, signal_fn, parent_window=None):
                        super().__init__()
                        self.signal_fn = signal_fn
                        self.parent_window = parent_window
                
                    def emit(self, record):
                        log_entry = self.format(record)
                        msg_type = "error" if record.levelno >= logging.ERROR else \
                                  "warning" if record.levelno >= logging.WARNING else \
                                  "success" if "complete" in log_entry.lower() or "success" in log_entry.lower() else \
                                  "info"
                        
                        # Prevent window resizing on log messages
                        if self.parent_window and hasattr(self.parent_window, 'size'):
                            current_size = self.parent_window.size()
                            # Enforce size constraints on notable log messages for all agents
                            if "initialized" in log_entry or "starting" in log_entry.lower():
                                self.parent_window.setFixedSize(current_size)
                                QApplication.processEvents()
                                
                        self.signal_fn(log_entry, msg_type)
            
                # Clear existing handlers and add UI handler
                logging.getLogger().handlers = []
                ui_handler = UIConsoleHandler(self.console_message.emit, main_window)
                ui_handler.setFormatter(logging.Formatter('%(message)s'))
                logging.getLogger().addHandler(ui_handler)
            
            # ===== Common setup for all agents =====
            # Re-enforce window constraints before agent initialization
            if main_window and hasattr(main_window, 'size'):
                main_window.setMinimumSize(current_size.width() - 50, current_size.height() - 50)
                main_window.setMaximumSize(current_size.width() + 50, current_size.height() + 50)
                # Do not use setFixedSize to allow for some manual resizing
                
                # Force update to ensure constraints are applied
                QApplication.processEvents()
            
            # Initialize and run the appropriate agent
            if self.agent_name == "dca_staking":
                # DCA agent handling
                from src.config import (
                    DCA_INTERVAL_UNIT, 
                    DCA_INTERVAL_VALUE, 
                    DCA_RUN_AT_ENABLED,
                    DCA_RUN_AT_TIME
                )
                
                # Initialize the agent
                self.agent = module.DCAAgent()
                
                # Immediately re-enforce constraints after initialization
                if main_window and hasattr(main_window, 'size'):
                    main_window.setMinimumSize(current_size.width() - 50, current_size.height() - 50)
                    main_window.setMaximumSize(current_size.width() + 50, current_size.height() + 50)
                    # Do not use setFixedSize to allow for some manual resizing
                    
                    # Force update to ensure constraints are applied
                    QApplication.processEvents()
                
                # Connect order_executed signal if the agent has one
                if hasattr(self.agent, 'order_executed'):
                    self.agent.order_executed.connect(
                        lambda agent_name, action, token, amount, price, exit_price, pnl, wallet_address, mint_address, ai_analysis: 
                        self.order_executed.emit(agent_name, action, token, amount, price, self.is_paper_trading, exit_price, pnl, wallet_address, mint_address, ai_analysis)
                    )
                
                # Update status with correct scheduling info
                if DCA_RUN_AT_ENABLED:
                    next_run_display = f"At {DCA_RUN_AT_TIME} every {DCA_INTERVAL_VALUE} {DCA_INTERVAL_UNIT}"
                else:
                    next_run_display = f"Every {DCA_INTERVAL_VALUE} {DCA_INTERVAL_UNIT}"
                    
                status_data = {
                    "status": "Active",
                    "last_run": "Not yet run" if not self.force_run else datetime.now().strftime("%H:%M:%S"),
                    "next_run": next_run_display,
                    "progress": 100
                }
                
                # Only run on startup if force_run=True
                if self.force_run:
                    self.console_message.emit("Running DCA & Staking cycle...", "info")
                    
                    # Re-enforce size constraints before running cycle
                    if main_window and hasattr(main_window, 'size'):
                        main_window.setMinimumSize(current_size.width() - 50, current_size.height() - 50)
                        main_window.setMaximumSize(current_size.width() + 50, current_size.height() + 50)
                        # Do not use setFixedSize to allow for some manual resizing
                        
                        # Force update to ensure constraints are applied
                        QApplication.processEvents()
                        
                    self.agent.run_dca_cycle()
                    status_data["last_run"] = datetime.now().strftime("%H:%M:%S")
                
                self.status_update.emit(self.agent_name, status_data)
                
            elif self.agent_name == "risk":
                # Risk agent handling
                from src.config import RISK_CONTINUOUS_MODE
                
                # Initialize the agent
                self.agent = module.RiskAgent()
                
                # Re-enforce constraints after initialization
                if main_window and hasattr(main_window, 'size'):
                    main_window.setMinimumSize(current_size.width() - 50, current_size.height() - 50)
                    main_window.setMaximumSize(current_size.width() + 50, current_size.height() + 50)
                    # Do not use setFixedSize to allow for some manual resizing
                    
                    # Force update to ensure constraints are applied
                    QApplication.processEvents()
                
                self.console_message.emit("Running Risk Management...", "info")
                
                # Update status to running
                status_data = {
                    "status": "Running",
                    "last_run": "Starting now...",
                    "next_run": "Calculating...",
                    "progress": 10
                }
                self.status_update.emit(self.agent_name, status_data)
                
                # Only run if continuous mode or if it's the first run when force_run=True
                if RISK_CONTINUOUS_MODE or self.force_run:
                    # Re-enforce constraints before running
                    if main_window and hasattr(main_window, 'size'):
                        main_window.setMinimumSize(current_size.width() - 50, current_size.height() - 50)
                        main_window.setMaximumSize(current_size.width() + 50, current_size.height() + 50)
                        # Do not use setFixedSize to allow for some manual resizing
                        
                        # Force update to ensure constraints are applied
                        QApplication.processEvents()
                    
                    self.agent.run()
                
                # Update status
                status_data = {
                    "status": "Active",
                    "last_run": datetime.now().strftime("%H:%M:%S"),
                    "next_run": (datetime.now() + timedelta(minutes=10)).strftime("%H:%M:%S"),
                    "progress": 100
                }
                self.status_update.emit(self.agent_name, status_data)
                
            elif self.agent_name == "copybot":
                # Copybot agent handling
                from src.config import COPYBOT_CONTINUOUS_MODE, COPYBOT_INTERVAL_MINUTES
                
                # Initialize the agent
                self.agent = module.CopyBotAgent()
                
                # Re-enforce constraints after initialization
                if main_window and hasattr(main_window, 'size'):
                    main_window.setMinimumSize(current_size.width() - 50, current_size.height() - 50)
                    main_window.setMaximumSize(current_size.width() + 50, current_size.height() + 50)
                    # Do not use setFixedSize to allow for some manual resizing
                    
                    # Force update to ensure constraints are applied
                    QApplication.processEvents()
                
                # Connect portfolio_updated signal if the agent has one
                if hasattr(self.agent, 'portfolio_updated'):
                    self.agent.portfolio_updated.connect(
                        lambda tokens: self.portfolio_update.emit(tokens)
                    )
                
                # Connect order_executed signal if the agent has one
                if hasattr(self.agent, 'order_executed'):
                    self.agent.order_executed.connect(
                        lambda agent_name, action, token, amount, price, exit_price, pnl, wallet_address, mint_address, ai_analysis: 
                        self.order_executed.emit(agent_name, action, token, amount, price, self.is_paper_trading, exit_price, pnl, wallet_address, mint_address, ai_analysis)
                    )
                
                # Connect changes_detected signal if the agent has one
                if hasattr(self.agent, 'changes_detected'):
                    self.agent.changes_detected.connect(
                        lambda changes: self.changes_detected.emit(changes)
                    )
                
                # Update status to running
                status_data = {
                    "status": "Running",
                    "last_run": "Starting now...",
                    "next_run": "Calculating...",
                    "progress": 10
                }
                self.status_update.emit(self.agent_name, status_data)
                
                # Only run if continuous mode or if it's the first run when force_run=True
                if COPYBOT_CONTINUOUS_MODE or self.force_run:
                    self.console_message.emit("Running CopyBot Portfolio Analysis...", "info")
                    self.agent.run_analysis_cycle()
                
                # Update status
                status_data = {
                    "status": "Active",
                    "last_run": datetime.now().strftime("%H:%M:%S"),
                    "next_run": (datetime.now() + timedelta(minutes=COPYBOT_INTERVAL_MINUTES)).strftime("%H:%M:%S"),
                    "progress": 100
                }
                self.status_update.emit(self.agent_name, status_data)
                
            elif self.agent_name == "chart_analysis":
                # Normal processing for chart analysis agent
                from src.config import (
                    CHART_INTERVAL_UNIT, 
                    CHART_INTERVAL_VALUE, 
                    CHART_RUN_AT_ENABLED,
                    CHART_RUN_AT_TIME
                )
                
                self.agent = module.ChartAnalysisAgent()
                
                # Connect order_executed signal if the agent has one
                if hasattr(self.agent, 'order_executed'):
                    self.agent.order_executed.connect(
                        lambda agent_name, action, token, amount, price: 
                        self.order_executed.emit(agent_name, action, token, amount, price, self.is_paper_trading)
                    )
                    
                # Connect analysis_complete signal if the agent has one
                if hasattr(self.agent, 'analysis_complete'):
                    self.agent.analysis_complete.connect(
                        lambda timestamp, action, token, token_symbol, analysis, confidence, price, change_percent, token_mint: 
                        self.analysis_complete.emit(timestamp, action, token, token_symbol, analysis, confidence, price, change_percent, token_mint)
                    )
                
                # Update status with correct scheduling info
                if CHART_RUN_AT_ENABLED:
                    next_run_display = f"At {CHART_RUN_AT_TIME} every {CHART_INTERVAL_VALUE} {CHART_INTERVAL_UNIT}"
                else:
                    next_run_display = f"Every {CHART_INTERVAL_VALUE} {CHART_INTERVAL_UNIT}"
                    
                status_data = {
                    "status": "Active",
                    "last_run": "Not yet run" if not self.force_run else datetime.now().strftime("%H:%M:%S"),
                    "next_run": next_run_display,
                    "progress": 100
                }
                
                # Only run on startup if force_run=True
                if self.force_run:
                    self.console_message.emit("Running Chart Analysis cycle...", "info")
                    self.agent.run_monitoring_cycle()
                    status_data["last_run"] = datetime.now().strftime("%H:%M:%S")
                
                self.status_update.emit(self.agent_name, status_data)
                
            # Emit completion message
            if self.force_run:
                self.console_message.emit(f"{self.agent_name} completed successfully", "success")
            else:
                self.console_message.emit(f"{self.agent_name} initialized and waiting for scheduled run", "info")
            
        except Exception as e:
            self.console_message.emit(f"Error in {self.agent_name}: {str(e)}", "error")
            import traceback
            tb = traceback.format_exc()
            self.console_message.emit(f"Traceback: {tb}", "error")
            
            # Update status
            status_data = {
                "status": "Error",
                "last_run": datetime.now().strftime("%H:%M:%S"),
                "next_run": "Not scheduled",
                "progress": 0
            }
            self.status_update.emit(self.agent_name, status_data)
        
        finally:
            # Restore original size constraints after a delay
            if main_window and hasattr(main_window, 'setMaximumSize'):
                if self.agent_name == "dca_staking":
                    # For DCA agent, keep constraints longer
                    QTimer.singleShot(5000, lambda: self.restore_window_constraints(main_window, original_min_size, original_max_size))
                    # Schedule a full reset after a bit longer
                    if hasattr(main_window, 'reset_size_constraints_complete'):
                        QTimer.singleShot(5500, lambda: main_window.reset_size_constraints_complete(f"{self.agent_name} complete"))
                else:
                    # For other agents, restore sooner
                    QTimer.singleShot(2000, lambda: self.restore_window_constraints(main_window, original_min_size, original_max_size))
                    # Schedule a full reset after a bit longer
                    if hasattr(main_window, 'reset_size_constraints_complete'):
                        QTimer.singleShot(2500, lambda: main_window.reset_size_constraints_complete(f"{self.agent_name} complete"))
            
            # Restore original logging handlers
            if original_handlers:
                logging.getLogger().handlers = []
                for handler in original_handlers:
                    logging.getLogger().addHandler(handler)
            
            self.running = False

    def restore_window_constraints(self, main_window, original_min_size, original_max_size):
        """Restore original window constraints"""
        if main_window:
            # Record size before reset
            current_size = main_window.size()
            
            # First clear any fixed constraints
            main_window.setFixedSize(MAX_WIDGET_SIZE, MAX_WIDGET_SIZE)
            QApplication.processEvents()
            
            # Restore original constraints if available
            if original_min_size:
                main_window.setMinimumSize(original_min_size)
            else:
                # Set to a reasonable minimum size rather than zero
                main_window.setMinimumSize(current_size.width() - 100, current_size.height() - 100)
                
            if original_max_size:
                main_window.setMaximumSize(original_max_size)
            else:
                # Set to a reasonable maximum size rather than extreme values
                main_window.setMaximumSize(current_size.width() + 200, current_size.height() + 200)
            
            # Process events
            QApplication.processEvents()

    def reset_window_constraints(self, main_window):
        """Reset window constraints after agent initialization (legacy method)"""
        if main_window:
            current_size = main_window.size()
            main_window.setMaximumSize(16777215, 16777215)  # QWidget default max size
            main_window.resize(current_size)  # Maintain current size
            
    def stop(self):
        """Stop the agent worker"""
        if not self.running:
            # Already stopped, avoid duplicate stop attempts
            return
        
        try:
            self.running = False
            self.console_message.emit(f"Stopping {self.agent_name}...", "system")
            
            # Try to gracefully stop the agent if it has a stop method
            if self.agent and hasattr(self.agent, 'stop'):
                try:
                    self.agent.stop()
                except Exception as e:
                    self.console_message.emit(f"Error stopping agent: {str(e)}", "error")
                    
            # Signal completion
            self.console_message.emit(f"Stopped {self.agent_name}", "system")
            
            # Update status to inactive
            status_data = {
                "status": "Inactive",
                "progress": 0
            }
            self.status_update.emit(self.agent_name, status_data)
            
        except Exception as e:
            self.console_message.emit(f"Error in stop: {str(e)}", "error")

class MainWindow(QMainWindow):
    def __init__(self, config_path=None, src_path=None):
        super().__init__()
        
        # Store paths
        self.config_path = config_path
        self.src_path = src_path
        
        # Create data directory if it doesn't exist
        if self.src_path:
            data_dir = os.path.join(os.path.dirname(self.src_path), 'data')
            os.makedirs(data_dir, exist_ok=True)
        
        # Add helper method for config updates
        
        
        # Set window properties
        self.setWindowTitle("Anarcho Capital: CryptoBot System")
        self.resize(1200, 800)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Set up the dark cyberpunk theme
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(CyberpunkColors.BACKGROUND))
        dark_palette.setColor(QPalette.WindowText, QColor(CyberpunkColors.TEXT_LIGHT))
        dark_palette.setColor(QPalette.Base, QColor(CyberpunkColors.BACKGROUND))
        dark_palette.setColor(QPalette.AlternateBase, QColor("#131320"))
        dark_palette.setColor(QPalette.Text, QColor(CyberpunkColors.TEXT_LIGHT))
        self.setPalette(dark_palette)
        
        # Load configuration
        self.load_config()
        
        # Initialize RiskAgent (singleton instance for reuse)
        self.risk_agent = None
        
        # Financial data cache
        self.financial_cache = {
            'wallet_balance': 0.0,
            'pnl': 0.0,
            'last_update': None,
            'cache_duration': 60  # Cache duration in seconds
        }
        
        # Set application style
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {CyberpunkColors.BACKGROUND};
            }}
            QTabWidget::pane {{
                border: 1px solid {CyberpunkColors.PRIMARY};
                background-color: {CyberpunkColors.BACKGROUND};
            }}
            QTabBar::tab {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                padding: 8px 16px;
                margin-right: 2px;
                font-family: 'Rajdhani', sans-serif;
            }}
            QTabBar::tab:selected {{
                background-color: {CyberpunkColors.PRIMARY};
                color: {CyberpunkColors.BACKGROUND};
                font-weight: bold;
            }}
            QLabel {{
                color: {CyberpunkColors.TEXT_LIGHT};
                font-family: 'Rajdhani', sans-serif;
            }}
            QGroupBox {{
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 5px;
                margin-top: 1ex;
                font-family: 'Rajdhani', sans-serif;
                color: {CyberpunkColors.PRIMARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }}
            QScrollArea {{
                border: none;
                background-color: {CyberpunkColors.BACKGROUND};
            }}
            QScrollBar:vertical {{
                background-color: {CyberpunkColors.BACKGROUND};
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {CyberpunkColors.PRIMARY};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QLineEdit, QComboBox {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 3px;
                padding: 5px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                selection-background-color: {CyberpunkColors.PRIMARY};
                selection-color: {CyberpunkColors.BACKGROUND};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {CyberpunkColors.PRIMARY};
                height: 4px;
                background: {CyberpunkColors.BACKGROUND};
                margin: 0px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {CyberpunkColors.PRIMARY};
                border: none;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            QCheckBox {{
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CyberpunkColors.PRIMARY};
            }}
        """)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create header
        header_frame = NeonFrame(CyberpunkColors.PRIMARY)
        header_layout = QHBoxLayout(header_frame)
        
        # Logo and title
        logo_label = QLabel("🌙")
        logo_label.setStyleSheet("font-size: 24px;")
        title_label = QLabel("Anarcho CopyBot Super Agent")
        title_label.setStyleSheet(f"""
            color: {CyberpunkColors.PRIMARY};
            font-family: 'Orbitron', sans-serif;
            font-size: 24px;
            font-weight: bold;
        """)
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # System status
        self.status_label = QLabel("● SYSTEM ONLINE")
        self.status_label.setStyleSheet(f"""
            color: {CyberpunkColors.SUCCESS};
            font-family: 'Share Tech Mono', monospace;
            font-weight: bold;
        """)
        header_layout.addWidget(self.status_label)
        
        # Add header to main layout
        main_layout.addWidget(header_frame)
        
        # Create content splitter (main content and console)
        content_splitter = QSplitter(Qt.Vertical)
        
        # Main content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget for different sections
        tab_widget = QTabWidget()
        
        # Dashboard tab
        dashboard_widget = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_widget)
        
        # Portfolio visualization
        portfolio_group = QGroupBox("Portfolio Visualization")
        portfolio_layout = QVBoxLayout(portfolio_group)
        self.portfolio_viz = PortfolioViz()
        portfolio_layout.addWidget(self.portfolio_viz)
        dashboard_layout.addWidget(portfolio_group)
        
        # Connect refresh button to refresh method
        self.portfolio_viz.refresh_button.clicked.connect(lambda: self.refresh_financial_data(force=True))
        
        # Agent status cards
        agent_cards_layout = QHBoxLayout()
        
        # Create agent cards with different colors
        self.copybot_card = AgentStatusCard("CopyBot Agent", CyberpunkColors.PRIMARY)
        self.risk_card = AgentStatusCard("Risk Agent", CyberpunkColors.DANGER)
        self.dca_card = AgentStatusCard("Advanced DCA Agent", CyberpunkColors.SECONDARY)
        
        agent_cards_layout.addWidget(self.copybot_card)
        agent_cards_layout.addWidget(self.risk_card)
        agent_cards_layout.addWidget(self.dca_card)
        
        dashboard_layout.addLayout(agent_cards_layout)
        
        # Add dashboard tab
        tab_widget.addTab(dashboard_widget, "Dashboard")

         # Create and add the Orders tab
        self.orders_tab = OrdersTab()
        tab_widget.addTab(self.orders_tab, "Orders")
        
        # Add Tracker tab
        self.tracker_tab = TrackerTab()
        tab_widget.addTab(self.tracker_tab, "Tracker")

        # Add Metrics tab
        self.metrics_tab = MetricsTab()
        tab_widget.addTab(self.metrics_tab, "Metrics")

        # Add Charts Tab
        self.charts_tab = ChartsTab(self)
        tab_widget.addTab(self.charts_tab, "Charts")
        
        
        # Add tabs for each agent
        copybot_tab = CopyBotTab()
        ai_config_tab = AIConfigTab()
        
        # Add the new AI Prompt Guide tab - match your existing pattern
        ai_prompt_guide_tab = AIPromptGuideTab()
        tab_widget.addTab(ai_prompt_guide_tab, "AI Prompt Guide")
        
        # Create and add tabs for agent settings - convert to instance variables to allow access from save_all_configs
        self.copybot_tab = CopyBotTab()
        tab_widget.addTab(self.copybot_tab, "CopyBot Settings")
        
        # Create and add risk management tab
        self.risk_tab = RiskManagementTab()
        tab_widget.addTab(self.risk_tab, "Risk Management Settings")
        
        self.dca_staking_tab = DCAStakingTab()
        tab_widget.addTab(self.dca_staking_tab, "Advanced DCA Settings")
        
        ai_config_tab = AIConfigTab()
        tab_widget.addTab(ai_config_tab, "AI Settings")

        # API Keys tab
        api_keys_widget = QWidget()
        api_keys_layout = QVBoxLayout(api_keys_widget)
        self.api_key_editor = ApiKeyEditor(os.path.join(os.path.dirname(self.src_path), '.env') if self.src_path else None)
        api_keys_layout.addWidget(self.api_key_editor)
        tab_widget.addTab(api_keys_widget, "API Keys")
    
        
        # Add tab widget to content layout
        content_layout.addWidget(tab_widget)
        
        # Add content widget to splitter
        content_splitter.addWidget(content_widget)
        
        # Console output
        console_group = QGroupBox("System Console")
        console_layout = QVBoxLayout(console_group)
        self.console = ConsoleOutput()
        console_layout.addWidget(self.console)
        
        # Add console to splitter
        content_splitter.addWidget(console_group)
        
        # Set initial splitter sizes
        content_splitter.setSizes([600, 200])
        
        # Add splitter to main layout
        main_layout.addWidget(content_splitter)
        
        # Initialize with sample data
        self.initialize_sample_data()
        
        # Add initial console messages
        self.console.append_message("🌙 Anarcho Capital AI Agent Trading System Starting...", "system")
        self.console.append_message("📊 Active Agents and their Intervals:", "system")
        self.console.append_message("  • Copybot: ✅ ON", "info")
        self.console.append_message("  • Risk Management: ✅ ON", "info")
        self.console.append_message("  • DCA/Staking System: ✅ ON", "info")
        self.console.append_message("💓 System heartbeat - All agents are ready!", "success")
        
        # Add portfolio data fetching state
        self.last_portfolio_update = datetime.now() - timedelta(minutes=5)  # Force initial update
        self.portfolio_fetch_interval = 60  # Seconds between portfolio updates
        self.portfolio_fetch_errors = 0
        self.max_portfolio_errors = 5  # After this many errors, increase interval
        
        # Setup timer for simulating real-time updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.simulate_updates)
        self.update_timer.start(5000)  # Update every 5 seconds
        
        # Initialize agent dictionaries
        self.agent_threads = {}
        self.agent_thread_objects = {}
        self.agent_workers = {}
        self.agent_cards = {
            'copybot': self.copybot_card,
            'risk': self.risk_card,
            'dca_staking': self.dca_card
        }
        self.agent_menu_actions = {}

        # Connect agent card signals
        self.connect_agent_signals()

        # NOW setup agent threads
        self.setup_agent_threads()
        
        # Set up a global resize constraint check timer that runs every 10 seconds
        # This ensures that if resizing is locked, it will be freed eventually
        self.global_resize_timer = QTimer(self)
        self.global_resize_timer.timeout.connect(self.check_size_constraints)
        self.global_resize_timer.start(5000)  # Every 5 seconds
        
        # Setup menu
        self.setup_menu()
        
    def setup_dark_theme(self):
        # Set up the dark cyberpunk theme
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(CyberpunkColors.BACKGROUND))
        dark_palette.setColor(QPalette.WindowText, QColor(CyberpunkColors.TEXT_LIGHT))
        dark_palette.setColor(QPalette.Base, QColor(CyberpunkColors.BACKGROUND))
        dark_palette.setColor(QPalette.AlternateBase, QColor("#131320"))
        dark_palette.setColor(QPalette.Text, QColor(CyberpunkColors.TEXT_LIGHT))
        self.setPalette(dark_palette)
        
    def load_config(self):
        """Load configuration from file"""
        if not self.config_path:
            # Return default config
            return {
                "AI_MODEL": "claude-3-haiku-20240307",
                "AI_MAX_TOKENS": 1024,
                "AI_TEMPERATURE": 70,
                # ... other default values
            }
        
        try:
            # Try to import config module
            spec = importlib.util.spec_from_file_location("config", self.config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # Extract configuration variables
            config = {}
            for key in dir(config_module):
                if not key.startswith("__") and not key.startswith("_"):
                    config[key] = getattr(config_module, key)
            
            return config
        except Exception as e:
            # Change this line to use print instead of self.console
            print(f"Error loading configuration: {str(e)}")
            return {}
    
    def save_config(self, config_data):
        """Save configuration to file"""
        if not self.config_path:
            self.console.append_message("No configuration file specified", "warning")
            return
        
        try:
            # Create backup of original config
            backup_path = self.config_path + ".bak"
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as src, open(backup_path, 'w') as dst:
                    dst.write(src.read())
            
            # Write new config
            with open(self.config_path, 'w') as f:
                f.write("# AI Trading System Configuration\n")
                f.write("# Generated by Cyberpunk UI\n\n")
                
                for key, value in config_data.items():
                    if isinstance(value, str):
                        f.write(f'{key} = "{value}"\n')
                    else:
                        f.write(f'{key} = {value}\n')
            
            self.console.append_message("Configuration saved successfully", "success")
            
            # Update local config data
            self.config_data = config_data
            
        except Exception as e:
            self.console.append_message(f"Error saving configuration: {str(e)}", "error")
    
    def initialize_sample_data(self):
        """Initialize with real data if possible"""
        # Try to initialize RiskAgent early for data access
        self.initialize_risk_agent()
        
        # Attempt to get initial financial data
        self.refresh_financial_data()
        
        if self.src_path:
            try:
                # Import nice_funcs directly
                sys.path.append(self.src_path)
                from nice_funcs import fetch_wallet_holdings_og
                import config
                
                # Try to fetch actual portfolio data
                self.console.append_message("Initializing with real portfolio data...", "system")
                
                try:
                    # Handle possible errors from the fetch operation itself
                    portfolio = fetch_wallet_holdings_og(config.address)
                    
                    # Check if portfolio data is valid
                    if portfolio is None or portfolio.empty:
                        self.console.append_message("No wallet data found, using fallback data", "warning")
                        raise ValueError("No portfolio data available")
                    
                    tokens = []
                    for _, row in portfolio.iterrows():
                        if 'USD Value' in row and row['USD Value'] > 0:
                            token_name = row.get('Symbol', row.get('Mint Address', 'Unknown')[:6])
                            token = {
                                "name": token_name,
                                "allocation": row['USD Value'] / portfolio['USD Value'].sum() if portfolio['USD Value'].sum() > 0 else 0,
                                "performance": 0.0,
                                "volatility": 0.05
                            }
                            tokens.append(token)
                    
                    if tokens:
                        self.portfolio_viz.set_portfolio_data(tokens)
                        self.console.append_message(f"Found {len(tokens)} tokens in wallet", "success")
                        return
                    else:
                        self.console.append_message("No token data found in wallet", "warning")
                except Exception as inner_e:
                    self.console.append_message(f"Error parsing portfolio data: {str(inner_e)}", "warning")
                
            except Exception as e:
                self.console.append_message(f"Could not load real portfolio data: {str(e)}", "warning")
        
        # Still provide fallback data just in case nothing else works
        self.console.append_message("Using fallback portfolio data", "warning")
        fallback_tokens = [
            {"name": "SOL", "allocation": 1.0, "performance": 0.0, "volatility": 0.05}
        ]
        self.portfolio_viz.set_portfolio_data(fallback_tokens)
    
    def initialize_risk_agent(self):
        """Initialize the RiskAgent singleton if it doesn't exist yet"""
        if self.risk_agent is None:
            try:
                from src.agents.risk_agent import RiskAgent
                self.risk_agent = RiskAgent()
                self.console.append_message("🛡️ Risk Agent initialized for data access", "system")
            except Exception as e:
                self.console.append_message(f"Error initializing Risk Agent: {str(e)}", "error")
                
    def refresh_financial_data(self, force=False):
        """Refresh financial data from blockchain"""
        try:
            # Initialize RiskAgent if needed
            self.initialize_risk_agent()
            
            # Update paper trading mode status in visualization
            try:
                from src.config import PAPER_TRADING_ENABLED
                self.portfolio_viz.set_paper_trading_mode(PAPER_TRADING_ENABLED)
            except:
                pass
            
            # Check if cache is still valid and force is not True
            if not force and self.financial_cache['last_update']:
                time_since_update = (datetime.now() - self.financial_cache['last_update']).total_seconds()
                if time_since_update < self.financial_cache['cache_duration']:
                    # Use cached data
                    return True
            
            if self.risk_agent:
                # Get fresh data from blockchain
                self.console.append_message("📊 Fetching fresh financial data...", "info")
                
                # Get wallet balance
                wallet_balance = self.risk_agent.get_portfolio_value()
                
                # Calculate PnL
                pnl = wallet_balance - self.risk_agent.start_balance
                
                # Get USDC value for cash reserve calculation
                try:
                    from src import config
                    from src import nice_funcs as n
                    
                    # Get USDC balance for cash reserve calculation
                    usdc_value = n.get_token_balance_usd(config.USDC_ADDRESS)
                    
                    # Calculate cash reserve percentage
                    cash_reserve_pct = (usdc_value / wallet_balance * 100) if wallet_balance > 0 else 0
                    
                    # Update UI with cash reserve percentage
                    self.portfolio_viz.set_cash_reserve(cash_reserve_pct, config.CASH_PERCENTAGE)
                    
                except Exception as e:
                    self.console.append_message(f"Warning: Could not calculate cash reserves: {str(e)}", "warning")
                    # Use fallback values
                    self.portfolio_viz.set_cash_reserve(100, 20)  # Set to 100% by default

                # Update cache
                self.financial_cache['wallet_balance'] = wallet_balance
                self.financial_cache['pnl'] = pnl
                self.financial_cache['last_update'] = datetime.now()
                
                # Update UI
                self.portfolio_viz.set_wallet_balance(wallet_balance)
                self.portfolio_viz.set_pnl(pnl)
                
                self.console.append_message("✅ Financial data refreshed", "success")
                return True
            else:
                self.console.append_message("⚠️ Risk Agent not available", "warning")
                return False
        except Exception as e:
            self.console.append_message(f"Error refreshing financial data: {str(e)}", "error")
            return False
            
    def update_wallet_balance(self):
        """Update wallet balance using cached data when possible"""
        try:
            # Use cached data if available and fresh enough
            if self.financial_cache['last_update']:
                time_since_update = (datetime.now() - self.financial_cache['last_update']).total_seconds()
                if time_since_update < self.financial_cache['cache_duration']:
                    # Use cached data
                    self.portfolio_viz.set_wallet_balance(self.financial_cache['wallet_balance'])
                    return
            
            # Refresh data if cache is stale or doesn't exist
            self.refresh_financial_data()
            
        except Exception as e:
            self.console.append_message(f"Error updating wallet balance: {str(e)}", "error")
            # Use a fallback value if there's an error
            self.portfolio_viz.set_wallet_balance(0.0)
            
    def update_pnl(self):
        """Update PnL value using cached data when possible"""
        try:
            # Use cached data if available and fresh enough
            if self.financial_cache['last_update']:
                time_since_update = (datetime.now() - self.financial_cache['last_update']).total_seconds()
                if time_since_update < self.financial_cache['cache_duration']:
                    # Use cached data
                    self.portfolio_viz.set_pnl(self.financial_cache['pnl'])
                    return
            
            # Refresh data if cache is stale or doesn't exist
            self.refresh_financial_data()
            
        except Exception as e:
            self.console.append_message(f"Error updating PnL: {str(e)}", "error")
            # Use a fallback value if there's an error
            self.portfolio_viz.set_pnl(0.0)

    def simulate_updates(self):
        """Connect to real backend data instead of simulating updates with error handling"""
        try:
            # Only fetch data if more than 5 seconds have passed since last update
            current_time = time.time()
            if hasattr(self, 'last_data_update') and current_time - self.last_data_update < 5:
                return
            
            self.last_data_update = current_time
                
            # Update financial data (will use cache if possible)
            self.update_wallet_balance()
            self.update_pnl()
            
            # Refresh tracker data
            self.tracker_tab.refresh_tracked_tokens()
            
            # NOTE: Change detection is now only refreshed manually via the button click
            # to prevent loops and excessive API calls
            
        except Exception as e:
            self.console.append_message(f"Error in system update: {str(e)}", "error")
    
    def connect_agent_signals(self):
        """Connect signals for agent cards"""
        # Copybot agent
        self.copybot_card.start_button.clicked.connect(lambda: self.start_agent("copybot"))
        self.copybot_card.stop_button.clicked.connect(lambda: self.stop_agent("copybot"))

        # Connect copybot's console messages to the tracker
        if hasattr(self, 'agent_workers'):  
            for agent_name, worker in self.agent_workers.items():
                if 'copybot' in agent_name.lower():
                     worker.console_message.connect(self.handle_copybot_message)
        
        # Risk agent
        self.risk_card.start_button.clicked.connect(lambda: self.start_agent("risk"))
        self.risk_card.stop_button.clicked.connect(lambda: self.stop_agent("risk"))
        
        # DCA agent
        self.dca_card.start_button.clicked.connect(lambda: self.start_agent("dca_staking"))
        self.dca_card.stop_button.clicked.connect(lambda: self.stop_agent("dca_staking"))
    
    def setup_agent_threads(self):
        """Initialize structures for agent threads without starting them"""
        # Initialize agent dictionaries
        self.agent_threads = {}
        self.agent_thread_objects = {}
        self.agent_workers = {}

        # Just prepare agent dictionaries, don't create or start threads
        agent_module_paths = {
            'risk': os.path.join(self.src_path, 'agents', 'risk_agent.py'),
            'copybot': os.path.join(self.src_path, 'agents', 'copybot_agent.py'),
            'dca_staking': os.path.join(self.src_path, 'agents', 'dca_staking_agent.py'),
            'chart_analysis': os.path.join(self.src_path, 'agents', 'chartanalysis_agent.py')
        }
        
        # Just initialize the agent paths - don't create workers or threads yet
        for agent_name in agent_module_paths:
            self.agent_threads[agent_name] = None
            self.agent_thread_objects[agent_name] = None
            self.agent_workers[agent_name] = None

    def start_agent(self, agent_name, force_run=False):
        """Start an agent thread"""
        # Prevent window resizing during agent start
        current_size = self.size()
        
        # Apply constraints that prevent expansion but allow limited manual resizing
        # Allow 50px of resize flexibility in each dimension
        self.setMinimumSize(current_size.width() - 50, current_size.height() - 50)
        self.setMaximumSize(current_size.width() + 50, current_size.height() + 50)
        # Do not use setFixedSize to allow manual resizing
        
        # Process events to ensure constraints are applied immediately
        QApplication.processEvents()
        
        # Check if the agent is already running
        if (agent_name in self.agent_threads and 
            self.agent_threads[agent_name] is not None and 
            hasattr(self.agent_threads[agent_name], 'running') and
            self.agent_threads[agent_name].running):
            self.console.append_message(f"{agent_name} is already running", "warning")
            return
        
        # Find the agent module path
        agent_module_paths = {
            'risk': os.path.join(self.src_path, 'agents', 'risk_agent.py'),
            'copybot': os.path.join(self.src_path, 'agents', 'copybot_agent.py'),
            'dca_staking': os.path.join(self.src_path, 'agents', 'dca_staking_agent.py'),
            'chart_analysis': os.path.join(self.src_path, 'agents', 'chartanalysis_agent.py')
        }
        
        if agent_name not in agent_module_paths:
            self.console.append_message(f"Unknown agent: {agent_name}", "error")
            return
        
        # Update the UI
        if agent_name in self.agent_cards:
            self.agent_cards[agent_name].start_agent()
        
        # Create and start the worker thread
        worker = AgentWorker(agent_name, agent_module_paths[agent_name], parent=self)
        worker.force_run = force_run  # Add the force_run parameter
        worker.is_paper_trading = self.portfolio_viz.is_paper_trading
        
        # Connect signals
        worker.status_update.connect(self.update_agent_status)
        worker.console_message.connect(lambda msg, msg_type: self.console.append_message(msg, msg_type))
        worker.portfolio_update.connect(self.portfolio_viz.set_portfolio_data)
        worker.analysis_complete.connect(self.tracker_tab.add_ai_analysis)
        worker.changes_detected.connect(self.tracker_tab.process_token_changes)
        worker.order_executed.connect(self.handle_agent_order)
        
        # Store the thread and start it
        self.agent_threads[agent_name] = worker
        self.agent_thread_objects[agent_name] = QThread()
        worker.moveToThread(self.agent_thread_objects[agent_name])
        self.agent_thread_objects[agent_name].started.connect(worker.run)
        self.agent_thread_objects[agent_name].start()
        
        # Update menu actions
        if agent_name in self.agent_menu_actions:
            self.agent_menu_actions[agent_name].setText(f"Stop {agent_name.replace('_', ' ').title()}")
            self.agent_menu_actions[agent_name].triggered.disconnect()
            self.agent_menu_actions[agent_name].triggered.connect(lambda: self.stop_agent(agent_name))

        # Add this line
        self.agent_workers[agent_name] = worker
        
        # Set up size enforcement for all agents
        timer_attr_name = f"{agent_name}_size_timer"
        setattr(self, timer_attr_name, QTimer(self))
        timer = getattr(self, timer_attr_name)
        timer.timeout.connect(lambda: self.enforce_size_during_agent(current_size))
        timer.start(100)  # Check every 100ms
            
        # Stop the timer after 10 seconds
        QTimer.singleShot(10000, timer.stop)
    
    def _cleanup_agent_thread(self, agent_name):
        """Clean up agent thread resources after stopping"""
        if agent_name not in self.agent_threads:
            return
            
        thread = self.agent_thread_objects.get(agent_name)
        
        try:
            if thread and thread.isRunning():
                # Wait up to 5 seconds for thread to finish
                if not thread.wait(3000):
                    self.console.append_message(f"{agent_name} thread did not exit cleanly, forcing termination", "warning")
                    thread.terminate()
                    thread.wait()  # Wait for termination
                    
            # Update status after thread is stopped
            if agent_name in self.agent_cards:
                self.agent_cards[agent_name].update_status({"status": "Inactive", "progress": 0})
                
        except Exception as e:
            self.console.append_message(f"Error stopping {agent_name}: {str(e)}", "error")
    
    def reset_size_constraints(self, context=""):
        """Reset size constraints and record window state"""
        # Save the original size before changing constraints
        original_size = self.size()
        
        # First, clear fixed size constraint using the maximum widget size
        self.setFixedSize(MAX_WIDGET_SIZE, MAX_WIDGET_SIZE)
        QApplication.processEvents()
        
        # Reset to reasonable constraints to allow resizing
        self.setMinimumSize(original_size.width() - 100, original_size.height() - 100)
        self.setMaximumSize(original_size.width() + 200, original_size.height() + 200)
        QApplication.processEvents()
        
        # Restore to the exact original size
        self.resize(original_size)
        QApplication.processEvents()
        
        # Check if size changed significantly after processing events
        new_size = self.size()
        if abs(new_size.width() - original_size.width()) > 5 or abs(new_size.height() - original_size.height()) > 5:
            # Force window back to original size if it changed significantly
            self.resize(original_size)
            QApplication.processEvents()

    def update_agent_status(self, agent_name, status_data):
        """Update agent status card"""
        card = None
        if agent_name == "copybot":
            card = self.copybot_card
        elif agent_name == "risk":
            card = self.risk_card
        elif agent_name == "dca_staking":
            card = self.dca_card
        
        if card:
            card.update_status(status_data)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop all agent threads
        for agent_name in self.agent_threads:
            self.stop_agent(agent_name)
        
        # Accept the close event
        event.accept()

    def update_token_list_tool(self, wallets):
        """Update token_list_tool.py with new settings"""
        try:
            token_tool_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'scripts', 'token_list_tool.py')
            
            if os.path.exists(token_tool_path):
                with open(token_tool_path, 'r') as f:
                    content = f.read()
                
                # Format the wallet list for insertion
                wallet_list_str = ',\n    '.join([f'"{wallet}"' for wallet in wallets if wallet.strip()])
                wallet_list = f"""
# List of wallets to track - Add your wallet addresses here! 🎯
WALLETS_TO_TRACK = [
    {wallet_list_str}

    # Add more wallets here...
]
"""
                # Replace existing WALLETS_TO_TRACK
                import re
                pattern = r'# List of wallets to track.*?WALLETS_TO_TRACK\s*=\s*\[([\s\S]*?)\]'
                new_content = re.sub(pattern, wallet_list.strip(), content)
                
                # Add api_sleep and retry parameters
                if "fetch_with_backoff" in new_content:
                    fetch_backoff_pattern = r'def fetch_with_backoff\(url, max_retries=\d+\):'
                    new_fetch_fn = f'def fetch_with_backoff(url, max_retries={self.max_retries.value()}, timeout={self.api_timeout.value()}):'
                    new_content = re.sub(fetch_backoff_pattern, new_fetch_fn, new_content)
                    
                    # Update the function body to use timeout
                    timeout_pattern = r'response = requests\.get\(url\)'
                    new_timeout = f'response = requests.get(url, timeout={self.api_timeout.value()})'
                    new_content = re.sub(timeout_pattern, new_timeout, new_content)
                
                # Update sleep time between API calls
                sleep_pattern = r'time\.sleep\(\d+\)\s*# Be nice to the API'
                new_sleep = f'time.sleep({self.api_sleep.value()})  # Be nice to the API 😊'
                new_content = re.sub(sleep_pattern, new_sleep, new_content)
                
                # Update API service parameters
                with open(token_tool_path, 'w') as f:
                    f.write(new_content)
                
                print(f"✅ Updated token_list_tool.py with new settings and wallets")
        except Exception as e:
            print(f"⚠️ Error updating token_list_tool.py: {e}")

    def handle_copybot_message(self, message, message_type):
        """Handle messages from CopyBot agent"""
        # Log the message to console
        self.console.append_message(message, message_type)
        
        # Look for AI Analysis Results and extract information
        if hasattr(self, 'tracker_tab') and "AI Analysis Results" in message:
            import re
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Try to extract token name
            token_match = re.search(r"Summary for ([^:]+):", message)
            token = token_match.group(1).strip() if token_match else "Unknown Token"
            
            # Extract action (BUY, SELL, NOTHING)
            action_match = re.search(r"Action: (BUY|SELL|NOTHING)", message)
            action = action_match.group(1) if action_match else "UNKNOWN"
            
            # Extract confidence
            confidence_match = re.search(r"Confidence: (\d+)%", message)
            confidence = confidence_match.group(1) if confidence_match else "0"
            
            # Extract a short analysis summary - take the first line of the analysis section
            analysis_lines = message.split("AI Analysis Results:")
            if len(analysis_lines) > 1:
                analysis_section = analysis_lines[1].strip().split("\n")
                if len(analysis_section) > 2:  # First line is the separator, second is BUY/SELL/NOTHING
                    analysis = analysis_section[2].strip()
                else:
                    analysis = "No analysis provided"
            else:
                analysis = "Technical analysis suggests action"
            
            # Extract price if available
            price_match = re.search(r"current price: \$?([0-9.]+)", message, re.IGNORECASE)
            if not price_match:
                price_match = re.search(r"price: \$?([0-9.]+)", message, re.IGNORECASE)
            price = f"${price_match.group(1)}" if price_match else "N/A"
            
            # Add the analysis to the table
            self.tracker_tab.add_ai_analysis(
                timestamp,
                action,
                token,
                analysis,
                confidence,
                price
            )

    def handle_agent_order(self, agent_name, action, token, amount, entry_price, is_paper_trade=False, 
                           exit_price=None, pnl=None, wallet_address="", mint_address="", ai_analysis=""):
        """Handle order execution from any agent"""
        # Add paper trading status indicator
        status = "Paper" if is_paper_trade else "Executed"
        self.orders_tab.add_order(
            agent_name, action, token, amount, entry_price, status,
            exit_price, pnl, wallet_address, mint_address, ai_analysis
        )

    def restart_agent(self, agent_name):
        """Restart an agent (stop and then start)"""
        self.console.append_message(f"Restarting {agent_name} agent...", "system")
        
        # Get the current status before stopping
        was_running = False
        if agent_name in self.agent_threads:
            thread = self.agent_threads[agent_name]
            was_running = thread is not None and thread.isRunning()
        
        # Only restart if it was running
        if was_running:
            # Stop the agent
            self.stop_agent(agent_name)
            
            # Wait for agent to fully stop before restarting
            def delayed_restart():
                # Wait a moment for the thread to fully stop
                import time
                time.sleep(2)
                
                # Import any changes that might have been made to config
                import sys
                import importlib
                sys.path.append(get_project_root())
                try:
                    from src import config
                    importlib.reload(config)
                    self.console.append_message(f"Reloaded configuration for {agent_name}", "success")
                except Exception as e:
                    self.console.append_message(f"Error reloading configuration: {str(e)}", "error")
                
                # Clear Python cache to ensure fresh module loading
                try:
                    import shutil
                    pycache_paths = [
                        os.path.join(get_project_root(), 'src', '__pycache__'),
                        os.path.join(get_project_root(), 'src', 'agents', '__pycache__')
                    ]
                    for path in pycache_paths:
                        if os.path.exists(path):
                            shutil.rmtree(path)
                            print(f"Cleared Python cache at {path}")
                except Exception as e:
                    print(f"Warning: Could not clear Python cache: {e}")
                
                # Start the agent again
                self.start_agent(agent_name)
                self.console.append_message(f"{agent_name} agent has been restarted with new configuration", "success")
            
            # Run the restart process in a background thread
            restart_thread = threading.Thread(target=delayed_restart)
            restart_thread.daemon = True
            restart_thread.start()
            
            return True
        else:
            self.console.append_message(f"{agent_name} was not running, no need to restart", "info")
            return False

    def reset_size_constraints_complete(self, context=""):
        """Completely reset all size constraints after agent operations"""
        # Save the original size before changing constraints
        original_size = self.size()
        
        # First, ensure we completely clear any fixed size constraints
        self.setFixedSize(MAX_WIDGET_SIZE, MAX_WIDGET_SIZE)
        QApplication.processEvents()
        
        # Remove all size constraints except a minimal reasonable base
        self.setMinimumSize(400, 300)  # Reasonable minimum for UI elements
        self.setMaximumSize(MAX_WIDGET_SIZE, MAX_WIDGET_SIZE)  # Maximum possible Qt widget size
        
        # Process events to ensure constraints are applied
        QApplication.processEvents()
        
        # For debugging
        # self.console.append_message(f"Size constraints reset ({context})", "system")

    def check_size_constraints(self):
        """Periodically check and ensure size constraints aren't preventing resizing"""
        # Record current size
        current_size = self.size()
        
        # ALWAYS completely remove fixed size constraints first
        self.setFixedSize(MAX_WIDGET_SIZE, MAX_WIDGET_SIZE)
        QApplication.processEvents()
        
        # Set extremely generous min/max constraints
        # Minimum size prevents UI elements from being squished
        self.setMinimumSize(400, 300)  # Reasonable minimum size for UI elements
        self.setMaximumSize(MAX_WIDGET_SIZE, MAX_WIDGET_SIZE)  # Maximum possible
        
        # Force update to ensure constraints are applied
        QApplication.processEvents()
        
        # If necessary, uncomment this for debugging
        # min_size = self.minimumSize()
        # max_size = self.maximumSize()
        # self.console.append_message(f"Size constraints reset: min={min_size.width()}x{min_size.height()}, max={max_size.width()}x{max_size.height()}", "system")

    def show_context_menu(self, position):
        """Show context menu with window management options"""
        context_menu = QMenu(self)
        
        # Add option to reset window constraints
        reset_action = context_menu.addAction("Reset Window Constraints")
        reset_action.triggered.connect(self.reset_size_constraints_complete)
        
        # Show the menu at the cursor position
        context_menu.exec_(self.mapToGlobal(position))

    def setup_menu(self):
        # Create menu bar
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet(f"background-color: {CyberpunkColors.BACKGROUND}; color: {CyberpunkColors.TEXT_LIGHT};")
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        # Add "Save All Configurations" action
        save_all_configs_action = QAction("Save All Configurations", self)
        save_all_configs_action.triggered.connect(self.save_all_configs)
        save_all_configs_action.setShortcut("Ctrl+S")  # Add keyboard shortcut
        file_menu.addAction(save_all_configs_action)
        
        # Add Settings menu
        settings_menu = menu_bar.addMenu("Settings")
        
        # Add Configuration item
        config_action = QAction("Configuration", self)
        config_action.triggered.connect(self.show_configuration)
        settings_menu.addAction(config_action)
        
        # Add API Keys item
        apikeys_action = QAction("API Keys", self)
        apikeys_action.triggered.connect(self.show_api_keys)
        settings_menu.addAction(apikeys_action)
        
        # Add AI Settings item
        ai_settings_action = QAction("AI Settings", self)
        ai_settings_action.triggered.connect(self.show_ai_settings)
        settings_menu.addAction(ai_settings_action)
        
        # Add "Exit" action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Add "Agents" menu
        agents_menu = menu_bar.addMenu("Agents")
        
        # Add agent actions to the menu
        copybot_action = QAction("Start Copybot", self)
        copybot_action.triggered.connect(lambda: self.start_agent("copybot"))
        self.agent_menu_actions["copybot"] = copybot_action
        agents_menu.addAction(copybot_action)
        
        risk_action = QAction("Start Risk Management", self)
        risk_action.triggered.connect(lambda: self.start_agent("risk"))
        self.agent_menu_actions["risk"] = risk_action
        agents_menu.addAction(risk_action)
        
        dca_action = QAction("Start DCA & Staking", self)
        dca_action.triggered.connect(lambda: self.start_agent("dca_staking"))
        self.agent_menu_actions["dca_staking"] = dca_action
        agents_menu.addAction(dca_action)
        
        # Add "Window" menu with reset constraints option
        window_menu = menu_bar.addMenu("Window")
        reset_constraints_action = QAction("Reset Size Constraints", self)
        reset_constraints_action.triggered.connect(
            lambda: self.reset_size_constraints_complete("menu-triggered")
        )
        window_menu.addAction(reset_constraints_action)
    
    def save_all_configs(self):
        """Save all configuration files"""
        try:
            # Save CopyBot configuration
            if hasattr(self, 'copybot_tab') and self.copybot_tab:
                self.copybot_tab.save_config()
            
            # Save DCA & Staking configuration
            if hasattr(self, 'dca_staking_tab') and self.dca_staking_tab:
                self.dca_staking_tab.save_config()
            
            # Save Risk Management configuration
            if hasattr(self, 'risk_tab') and self.risk_tab:
                self.risk_tab.save_config()
            
            # Show success message
            self.console.append_message("All configurations saved successfully", "system")
        except Exception as e:
            self.console.append_message(f"Error saving configurations: {str(e)}", "error")
    
