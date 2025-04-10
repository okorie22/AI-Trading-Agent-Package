import sys
import os
import math
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta
import json
import random
import logging
import re
import threading
import time
import pandas as pd
import numpy as np
import sqlite3

from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QSlider, QComboBox, 
                             QLineEdit, QTextEdit, QProgressBar, QFrame, QGridLayout,
                             QSplitter, QGroupBox, QCheckBox, QSpacerItem, QSizePolicy, QScrollArea,
                             QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout)  # Added missing widgets
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSize, QThread, QObject, QRect, QMetaObject, Q_ARG
from PySide6.QtGui import QColor, QFont, QPalette, QLinearGradient, QGradient, QPainter, QPen, QBrush, QPixmap, QIcon
from src.scripts.wallet_metrics_db import WalletMetricsDB
from src.scripts.wallet_analyzer import WalletAnalyzer
from src.config import (TRADING_MODE, USE_HYPERLIQUID, DEFAULT_LEVERAGE, 
                       MAX_LEVERAGE, LEVERAGE_SAFETY_BUFFER, MIRROR_WITH_LEVERAGE,
                       TOKEN_TO_HL_MAPPING, CASH_PERCENTAGE, MAX_POSITION_PERCENTAGE, 
                       USE_PERCENTAGE, MAX_LOSS_PERCENT, MAX_GAIN_PERCENT, MAX_LOSS_USD, 
                       MAX_GAIN_USD, MINIMUM_BALANCE_USD, USE_AI_CONFIRMATION, 
                       MAX_LOSS_GAIN_CHECK_HOURS, SLEEP_BETWEEN_RUNS_MINUTES,
                       FILTER_MODE, ENABLE_PERCENTAGE_FILTER, PERCENTAGE_THRESHOLD,
                       ENABLE_AMOUNT_FILTER, AMOUNT_THRESHOLD, ENABLE_ACTIVITY_FILTER,
                       ACTIVITY_WINDOW_HOURS, PAPER_TRADING_ENABLED, PAPER_INITIAL_BALANCE,
                       PAPER_TRADING_SLIPPAGE, PAPER_TRADING_RESET_ON_START)

# Define cyberpunk color scheme
class CyberpunkColors:
    BACKGROUND = "#000000"
    PRIMARY = "#00FFFF"    # Neon Blue
    SECONDARY = "#FF00FF"  # Neon Purple
    TERTIARY = "#00FF00"   # Neon Green
    WARNING = "#FF6600"    # Neon Orange
    DANGER = "#FF0033"     # Neon Red
    SUCCESS = "#33FF33"    # Neon Green
    TEXT_LIGHT = "#E0E0E0"
    TEXT_WHITE = "#FFFFFF"

# Custom styled widgets
class NeonButton(QPushButton):
    def __init__(self, text, color=CyberpunkColors.PRIMARY, parent=None):
        super().__init__(text, parent)
        self.color = QColor(color)
        self.setMinimumHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        
        # Set stylesheet
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border: 2px solid {color};
                border-radius: 5px;
                padding: 5px 15px;
                font-family: 'Rajdhani', sans-serif;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: {CyberpunkColors.BACKGROUND};
            }}
            QPushButton:pressed {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {color};
            }}
        """)

class NeonFrame(QFrame):
    def __init__(self, color=CyberpunkColors.PRIMARY, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(2)
        self.setStyleSheet(f"""
            NeonFrame {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: 2px solid {color};
                border-radius: 5px;
            }}
        """)

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

class PortfolioVisualization(QWidget):
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

    # Add this method to the PortfolioVisualization class
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
        
        # Connect signals
        self.start_button.clicked.connect(self.start_agent)
        self.stop_button.clicked.connect(self.stop_agent)
        
        # Set default styling
        self.setStyleSheet(f"""
            QLabel {{
                color: {CyberpunkColors.TEXT_LIGHT};
                font-family: 'Rajdhani', sans-serif;
            }}
        """)
        
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
        
        # Clear progress bar
        self.progress_bar.setValue(0)
        
        # Stop timer if running
        if hasattr(self, 'timer'):
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
        
    def update_progress(self):
        current_value = self.progress_bar.value()
        if current_value >= 100:
            # Stop the timer once we reach 100% instead of resetting to 0
            if hasattr(self, 'timer'):
                self.timer.stop()
        else:
            # Update faster for a quick flash - increase the increment
            self.progress_bar.setValue(current_value + 5)  # Increment by 5 instead of 1 for faster progress
            
    def update_status(self, status_data):
        """Update card with real agent status data"""
        if 'status' in status_data:
            self.status = status_data['status']
            self.status_label.setText(self.status)
            if self.status == "Active":
                self.status_label.setStyleSheet(f"color: {CyberpunkColors.SUCCESS};")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
                # Set progress to 100% for active status instead of cycling
                if hasattr(self, 'timer'):
                    self.timer.stop()
                self.progress_bar.setValue(100)
            else:
                self.status_label.setStyleSheet(f"color: {CyberpunkColors.DANGER};")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                self.progress_bar.setValue(0)
                
        if 'last_run' in status_data:
            self.last_run = status_data['last_run']
            self.last_run_label.setText(self.last_run)
            
        if 'next_run' in status_data:
            self.next_run = status_data['next_run']
            self.next_run_label.setText(self.next_run)
            
        if 'progress' in status_data:
            self.progress_bar.setValue(status_data['progress'])
            # If progress is 100%, stop the timer to prevent cycling
            if status_data['progress'] == 100 and hasattr(self, 'timer'):
                self.timer.stop()

    @Slot(str, int)
    def update_status_from_params(self, status, progress=None, last_run=None, next_run=None):
        """Update card status using individual parameters instead of a dictionary"""
        status_data = {}
        if status is not None:
            status_data['status'] = status
        if progress is not None:
            status_data['progress'] = progress
        if last_run is not None:
            status_data['last_run'] = last_run
        if next_run is not None:
            status_data['next_run'] = next_run
        
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

class ApiKeyEditor(QWidget):
    """Widget for securely editing API keys and credentials"""
    keys_saved = Signal()
    
    def __init__(self, env_path=None, parent=None):
        super().__init__(parent)
        self.env_path = env_path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
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
                with open(self.env_path, 'r') as src, open(backup_path, 'w') as dst:
                    dst.write(src.read())
            
            # Load existing .env content to preserve comments and structure
            env_content = []
            if os.path.exists(self.env_path):
                with open(self.env_path, 'r') as f:
                    env_content = f.readlines()
            
            # Update or add keys
            updated_keys = set()
            for key, field in self.key_fields.items():
                value = field.text()
                key_found = False
                
                # Update existing keys
                for i, line in enumerate(env_content):
                    if line.strip() and not line.strip().startswith('#') and line.strip().split('=', 1)[0].strip() == key:
                        env_content[i] = f"{key}={value}\n"
                        key_found = True
                        break
                
                # Add new keys if not found
                if not key_found:
                    env_content.append(f"{key}={value}\n")
                
                updated_keys.add(key)
            
            # Write updated content
            with open(self.env_path, 'w') as f:
                f.writelines(env_content)
            
            QMessageBox.information(self, "Keys Saved", "API keys have been saved successfully.")
            self.keys_saved.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving API keys: {str(e)}")
    
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

class AgentWorker(QObject):
    """Worker thread for running agents"""
    status_update = Signal(str, dict)  # agent_name, status_data
    console_message = Signal(str, str)  # message, message_type
    portfolio_update = Signal(list)  # token_data
    analysis_complete = Signal(str, str, str, str, str, str, str, str, str)  # timestamp, action, token, token_symbol, analysis, confidence, price, change_percent, token_mint
    changes_detected = Signal(dict)  # changes dictionary from TokenAccountTracker
    order_executed = Signal(str, str, str, float, float, bool)  # agent_name, action, token, amount, price, is_paper_trade
    
    def __init__(self, agent_name, agent_module_path, parent=None):
        super().__init__(parent)
        self.agent_name = agent_name
        self.agent_module_path = agent_module_path
        self.running = False
        self.agent = None
        
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
        self.running = True
        
        # Log paper trading status
        if self.is_paper_trading:
            self.console_message.emit(f"Starting {self.agent_name} in PAPER TRADING mode...", "system")
        else:
            self.console_message.emit(f"Starting {self.agent_name}...", "system")
        
        try:
            # Import agent module
            spec = importlib.util.spec_from_file_location("agent_module", self.agent_module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Initialize agent - Use your existing agent classes
            if self.agent_name == "copybot":
                self.agent = module.CopyBotAgent()
                
                # Connect the CopyBotAgent's analysis_complete signal to our worker's analysis_complete signal
                if hasattr(self.agent, 'analysis_complete'):
                    self.agent.analysis_complete.connect(self.analysis_complete)
                    
                # Connect changes_detected signal
                if hasattr(self.agent, 'changes_detected'):
                    self.agent.changes_detected.connect(self.changes_detected)
                
                # Connect order_executed signal if the agent has one
                if hasattr(self.agent, 'order_executed'):
                    self.agent.order_executed.connect(
                        lambda agent_name, action, token, amount, price: 
                        self.order_executed.emit(agent_name, action, token, amount, price, self.is_paper_trading)
                    )
                
                # Set up logging to UI console
                class UIConsoleHandler(logging.Handler):
                    def __init__(self, signal_fn):
                        super().__init__()
                        self.signal_fn = signal_fn
                        
                    def emit(self, record):
                        msg = self.format(record)
                        level = record.levelname.lower()
                        msg_type = "error" if level == "error" else "warning" if level == "warning" else "info"
                        self.signal_fn(msg, msg_type)
                
                # Add console handler to agent's logger if it has one
                if hasattr(self.agent, 'logger'):
                    ui_handler = UIConsoleHandler(self.console_message.emit)
                    self.agent.logger.addHandler(ui_handler)
                
                # Run the agent - call appropriate method
                self.console_message.emit("Running CopyBot portfolio analysis cycle...", "info")
                self.agent.run_analysis_cycle()
                
            elif self.agent_name == "risk":
                self.agent = module.RiskAgent()
                
                # Connect order_executed signal if the agent has one
                if hasattr(self.agent, 'order_executed'):
                    self.agent.order_executed.connect(
                        lambda agent_name, action, token, amount, price: 
                        self.order_executed.emit(agent_name, action, token, amount, price, self.is_paper_trading)
                    )
                
                # Run the risk agent
                self.console_message.emit("Running Risk Management check...", "info")
                result = self.agent.run()
                
                # Update portfolio data after risk agent runs
                if hasattr(self.agent, 'get_portfolio_value'):
                    portfolio_value = self.agent.get_portfolio_value()
                    self.console_message.emit(f"Portfolio value: ${portfolio_value:.2f}", "info")
                    
                # Get sample portfolio data to visualize
                self.update_portfolio_data()
                
            elif self.agent_name == "dca_staking":
                self.agent = module.DCAAgent()
                
                # Connect order_executed signal if the agent has one
                if hasattr(self.agent, 'order_executed'):
                    self.agent.order_executed.connect(
                        lambda agent_name, action, token, amount, price: 
                        self.order_executed.emit(agent_name, action, token, amount, price, self.is_paper_trading)
                    )
                
                # Run the DCA cycle without trying to initialize the chart analyzer from the same module
                self.console_message.emit("Running DCA/Staking System cycle...", "info")
                self.agent.run_dca_cycle()
                
                # Update status
                status_data = {
                    "status": "Active",
                    "last_run": datetime.now().strftime("%H:%M:%S"),
                    "next_run": (datetime.now() + timedelta(hours=12)).strftime("%H:%M:%S"),
                    "progress": 100
                }
                self.status_update.emit(self.agent_name, status_data)
                
            elif self.agent_name == "chart_analysis":
                self.agent = module.ChartAnalysisAgent()
                
                # Connect order_executed signal if the agent has one
                if hasattr(self.agent, 'order_executed'):
                    self.agent.order_executed.connect(
                        lambda agent_name, action, token, amount, price: 
                        self.order_executed.emit(agent_name, action, token, amount, price, self.is_paper_trading)
                    )
                
                # Run a single chart analysis cycle
                self.console_message.emit("Running Chart Analysis cycle...", "info")
                self.agent.run_monitoring_cycle()
                
                # Update status
                status_data = {
                    "status": "Active",
                    "last_run": datetime.now().strftime("%H:%M:%S"),
                    "next_run": (datetime.now() + timedelta(hours=4)).strftime("%H:%M:%S"),
                    "progress": 100
                }
                self.status_update.emit(self.agent_name, status_data)
                
            # Emit completion message
            self.console_message.emit(f"{self.agent_name} completed successfully", "success")
        
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
        
        self.running = False
    
    def stop(self):
        """Stop the agent worker"""
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
        except Exception as e:
            self.console_message.emit(f"Error in stop: {str(e)}", "error")
    
    def update_portfolio_data(self, force_update=False):
        """Get portfolio data from the agent or fetch it directly with caching"""
        # This tracks if we've recently had a successful update
        if not hasattr(self, '_last_portfolio_data'):
            self._last_portfolio_data = None
            self._last_portfolio_update = None

        # If not forcing update and we have recent data (within last minute), use cached data
        if not force_update and self._last_portfolio_data and self._last_portfolio_update:
            time_since_update = (datetime.now() - self._last_portfolio_update).total_seconds()
            if time_since_update < 60:  # Less than a minute - use cached data
                if self._last_portfolio_data:
                    self.portfolio_update.emit(self._last_portfolio_data)
                    return True
        
        try:
            import sys
            from pathlib import Path
            
            # Add parent directory to path to import from src
            sys.path.append(str(Path(self.agent_module_path).parent.parent))
            
            # Try to import nice_funcs
            from src import nice_funcs as n
            from src import config
            
            # Get real portfolio data
            self.console_message.emit("Fetching portfolio data from wallet...", "info")
            
            # Use paper trading portfolio if enabled
            if self.is_paper_trading:
                from src import paper_trading
                self.console_message.emit("Using PAPER TRADING portfolio data...", "info")
                portfolio = paper_trading.get_paper_portfolio()
            else:
                portfolio = n.fetch_wallet_holdings_og(config.address)
            
            # Convert to format needed for visualization
            portfolio_tokens = []
            
            if portfolio is not None and not portfolio.empty:
                total_value = portfolio['USD Value'].sum() if 'USD Value' in portfolio.columns else 0
                
                for _, row in portfolio.iterrows():
                    if 'USD Value' in row and row['USD Value'] > 0:
                        # Extract token details
                        token_name = row.get('Symbol', row.get('Mint Address', 'Unknown')[:6])
                        token = {
                            "name": token_name,
                            "allocation": row['USD Value'] / total_value if total_value > 0 else 0,
                            "performance": 0.0,  # We'll calculate this from historical data if available
                            "volatility": 0.05   # Default value
                        }
                        portfolio_tokens.append(token)
                        self.console_message.emit(f"Found token: {token_name} with value: ${row['USD Value']:.2f}", "info")
            
            if portfolio_tokens:
                # Cache successful data
                self._last_portfolio_data = portfolio_tokens
                self._last_portfolio_update = datetime.now()
                
                # Update UI
                self.portfolio_update.emit(portfolio_tokens)
                return True
            else:
                self.console_message.emit("No tokens found in wallet or error reading portfolio", "warning")
                return False
            
        except Exception as e:
            self.console_message.emit(f"Error fetching portfolio data: {str(e)}", "error")
            import traceback
            tb = traceback.format_exc()
            self.console_message.emit(f"Traceback: {tb}", "error")
            return False

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
        
        # Set window properties
        self.setWindowTitle("Moon Dev Trading System")
        self.resize(1200, 800)
        
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
        self.portfolio_viz = PortfolioVisualization()
        portfolio_layout.addWidget(self.portfolio_viz)
        dashboard_layout.addWidget(portfolio_group)
        
        # Connect refresh button to refresh method
        self.portfolio_viz.refresh_button.clicked.connect(lambda: self.refresh_financial_data(force=True))
        
        # Agent status cards
        agent_cards_layout = QHBoxLayout()
        
        # Create agent cards with different colors
        self.copybot_card = AgentStatusCard("Anarcho CopyBot Agent", CyberpunkColors.PRIMARY)
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
        tab_widget.addTab(copybot_tab, "CopyBot Settings")
        
        # Create and add risk management tab
        risk_tab = RiskManagementTab()
        tab_widget.addTab(risk_tab, "Risk Management Settings")
        
        dca_staking_tab = DCAStakingTab()
        tab_widget.addTab(dca_staking_tab, "Advanced DCA Settings")
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
        self.console.append_message("🌙 Moon Dev AI Agent Trading System Starting...", "system")
        self.console.append_message("📊 Active Agents and their Intervals:", "system")
        self.console.append_message("  • Copybot: ✅ ON (Every 30 minutes)", "info")
        self.console.append_message("  • Risk Management: ✅ ON (Every 10 minutes)", "info")
        self.console.append_message("  • DCA/Staking System: ✅ ON (Every 12 hours)", "info")
        self.console.append_message("💓 System heartbeat - All agents running on schedule", "success")
        
        # Add portfolio data fetching state
        self.last_portfolio_update = datetime.now() - timedelta(minutes=5)  # Force initial update
        self.portfolio_fetch_interval = 60  # Seconds between portfolio updates
        self.portfolio_fetch_errors = 0
        self.max_portfolio_errors = 5  # After this many errors, increase interval
        
        # Setup timer for simulating real-time updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.simulate_updates)
        self.update_timer.start(5000)  # Update every 5 seconds
        
        # Connect agent card signals
        self.connect_agent_signals()
        
        # Setup agent threads
        self.setup_agent_threads()
        
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
        """Setup threads for running agents"""
        self.agent_threads = {}
        self.agent_workers = {}
        
        if self.src_path:
            agent_paths = {
                "copybot": os.path.join(self.src_path, "agents", "copybot_agent.py"),
                "risk": os.path.join(self.src_path, "agents", "risk_agent.py"),
                "dca_staking": os.path.join(self.src_path, "agents", "dca_staking_agent.py"),
                "chart_analysis": os.path.join(self.src_path, "agents", "chartanalysis_agent.py")
            }
            
            for agent_name, agent_path in agent_paths.items():
                if os.path.exists(agent_path):
                    # Create worker
                    worker = AgentWorker(agent_name, agent_path)
                    
                    # Create thread
                    thread = QThread()
                    worker.moveToThread(thread)
                    
                    # Connect signals
                    thread.started.connect(worker.run)
                    worker.status_update.connect(self.update_agent_status)
                    worker.console_message.connect(self.console.append_message)
                    worker.portfolio_update.connect(self.portfolio_viz.set_portfolio_data)

                    # Connect order execution signal
                    worker.order_executed.connect(self.handle_agent_order)
                    
                    # Connect CopyBot analysis signal to the TrackerTab
                    if agent_name == "copybot":
                        worker.analysis_complete.connect(
                            lambda timestamp, action, token, token_symbol, analysis, confidence, price, change_percent, token_mint:
                            self.tracker_tab.add_ai_analysis(timestamp, action, token, token_symbol, analysis, confidence, price, change_percent, token_mint)
                        )
                        worker.changes_detected.connect(self.tracker_tab.process_token_changes)
                    
                    # Store worker and thread
                    self.agent_workers[agent_name] = worker
                    self.agent_threads[agent_name] = thread
    
    def start_agent(self, agent_name):
        """Start an agent"""
        if agent_name in self.agent_threads:
            thread = self.agent_threads[agent_name]
            if not thread.isRunning():
                # Special handling for DCA/Staking System
                if agent_name == "dca_staking":
                    # Start both DCA and Chart Analysis threads
                    thread.start()
                    
                    # Also start chart analysis if it exists
                    if "chart_analysis" in self.agent_threads:
                        chart_thread = self.agent_threads["chart_analysis"]
                        if not chart_thread.isRunning():
                            chart_thread.start()
                            
                    # Update DCA card status
                    self.dca_card.status = "Active"
                    self.dca_card.status_label.setText("Active")
                    self.dca_card.status_label.setStyleSheet(f"color: {CyberpunkColors.SUCCESS};")
                    self.dca_card.start_button.setEnabled(False)
                    self.dca_card.stop_button.setEnabled(True)
                else:
                    thread.start()
        else:
            # Fallback to simulated agent
            self.console.append_message(f"Starting {agent_name} (simulated)...", "system")
            card = getattr(self, f"{agent_name.lower().replace('_', '')}_card", None)
            if card:
                card.start_agent()
    
    def stop_agent(self, agent_name):
        """Stop an agent"""
        if agent_name in self.agent_workers:
            # Update card status immediately to give visual feedback
            card = None
            if agent_name == "copybot":
                card = self.copybot_card
            elif agent_name == "risk":
                card = self.risk_card
            elif agent_name == "dca_staking":
                card = self.dca_card
                
            if card:
                card.status = "Stopping..."
                card.status_label.setText("Stopping...")
                card.status_label.setStyleSheet(f"color: {CyberpunkColors.WARNING};")
                card.start_button.setEnabled(False)
                card.stop_button.setEnabled(False)
            
            # Process background stop in separate thread to prevent UI freezing
            def background_stop():
                try:
                    worker = self.agent_workers[agent_name]
                    worker.stop()
                    
                    # Special handling for DCA/Staking System
                    if agent_name == "dca_staking":
                        # Stop both DCA and Chart Analysis workers
                        if "chart_analysis" in self.agent_workers:
                            chart_worker = self.agent_workers["chart_analysis"]
                            chart_worker.stop()
                        
                        # Wait for both threads to finish
                        thread = self.agent_threads[agent_name]
                        if thread.isRunning():
                            thread.quit()
                            # Use a timeout to avoid hanging
                            thread.wait(2000)  # 2 second timeout
                            
                        if "chart_analysis" in self.agent_threads:
                            chart_thread = self.agent_threads["chart_analysis"]
                            if chart_thread.isRunning():
                                chart_thread.quit()
                                # Use a timeout to avoid hanging
                                chart_thread.wait(2000)  # 2 second timeout
                                
                            # Update DCA card status
                            QMetaObject.invokeMethod(
                                self.dca_card, 
                                "update_status_from_params", 
                                Qt.QueuedConnection, 
                                Q_ARG(str, "Inactive"),
                                Q_ARG(int, 0)
                            )
                        else:
                            # Wait for thread to finish
                            thread = self.agent_threads[agent_name]
                            if thread.isRunning():
                                thread.quit()
                                thread.wait(2000)  # 2 second timeout
                    
                    # Update UI in the main thread
                    if card:
                        QMetaObject.invokeMethod(
                            card, 
                            "update_status_from_params", 
                            Qt.QueuedConnection, 
                            Q_ARG(str, "Inactive"),
                            Q_ARG(int, 0)
                        )
                except Exception as e:
                    # Log error but don't block UI
                    print(f"Error stopping agent: {str(e)}")
            
            # Run the stop process in a background thread
            stop_thread = threading.Thread(target=background_stop)
            stop_thread.daemon = True
            stop_thread.start()
        else:
            # Fallback to simulated agent
            self.console.append_message(f"Stopping {agent_name} (simulated)...", "warning")
            card = getattr(self, f"{agent_name.lower().replace('_', '')}_card", None)
            if card:
                card.stop_agent()
    
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

    def handle_agent_order(self, agent_name, action, token, amount, price, is_paper_trade=False):
        """Handle order execution from any agent"""
        # Add paper trading status indicator
        status = "Paper" if is_paper_trade else "Executed"
        self.orders_tab.add_order(agent_name, action, token, amount, price, status)

class CopyBotTab(QWidget):
    """Tab for configuring and controlling CopyBot Agent"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # Set initial values from config for leverage mode
        try:
            # Set leverage mode toggle based on config
            self.leverage_mode.setChecked(TRADING_MODE.lower() == "leverage" and USE_HYPERLIQUID)
            self.default_leverage.setValue(DEFAULT_LEVERAGE)
            self.max_leverage.setValue(MAX_LEVERAGE)
            self.leverage_safety.setValue(LEVERAGE_SAFETY_BUFFER)
            self.mirror_leverage.setChecked(MIRROR_WITH_LEVERAGE)
            
            # Initialize the state of leverage settings without showing warning
            self.toggle_leverage_settings(self.leverage_mode.isChecked(), show_warning=False)
        except Exception as e:
            print(f"Error loading leverage config: {e}")
        
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
        agent_group = QGroupBox("Agent Runtime Configuration")
        agent_layout = QGridLayout(agent_group)
        
        # Update/Refresh Interval
        self.run_mode = QCheckBox("Continuous Mode")
        self.run_mode.setToolTip("When enabled, CopyBot will run continuously instead of on a fixed schedule")
        agent_layout.addWidget(self.run_mode, 0, 0)
        
        agent_layout.addWidget(QLabel("Update Interval (minutes):"), 1, 0)
        self.update_interval = QSpinBox()
        self.update_interval.setRange(1, 1440)  # 1 minute to 24 hours
        self.update_interval.setValue(30)  # Default from ACTIVE_AGENTS in main.py
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
        
        # New section for Trading Mode Configuration
        trading_mode_group = QGroupBox("Trading Mode Configuration")
        trading_layout = QGridLayout(trading_mode_group)
        
        # Add leverage mode toggle
        self.leverage_mode = QCheckBox("Enable Leverage Trading")
        self.leverage_mode.setToolTip("When enabled, CopyBot will use Hyperliquid for leverage trading instead of spot trading")
        self.leverage_mode.setStyleSheet(f"""
            QCheckBox::indicator:checked {{
                background-color: {CyberpunkColors.SUCCESS};
            }}
        """)
        trading_layout.addWidget(self.leverage_mode, 0, 0)
        
        # Add leverage settings
        leverage_settings_layout = QGridLayout()
        
        # Default leverage
        leverage_settings_layout.addWidget(QLabel("Default Leverage:"), 0, 0)
        self.default_leverage = QDoubleSpinBox()
        self.default_leverage.setRange(1.0, 10.0)
        self.default_leverage.setValue(DEFAULT_LEVERAGE)
        self.default_leverage.setSingleStep(0.1)
        self.default_leverage.setSuffix("x")
        self.default_leverage.setToolTip("Default leverage multiplier to use in trades")
        leverage_settings_layout.addWidget(self.default_leverage, 0, 1)
        
        # Maximum leverage
        leverage_settings_layout.addWidget(QLabel("Maximum Leverage:"), 1, 0)
        self.max_leverage = QDoubleSpinBox()
        self.max_leverage.setRange(1.0, 20.0)
        self.max_leverage.setValue(MAX_LEVERAGE)
        self.max_leverage.setSingleStep(0.5)
        self.max_leverage.setSuffix("x")
        self.max_leverage.setToolTip("Maximum allowed leverage multiplier")
        leverage_settings_layout.addWidget(self.max_leverage, 1, 1)
        
        # Safety buffer
        leverage_settings_layout.addWidget(QLabel("Safety Buffer:"), 2, 0)
        self.leverage_safety = QDoubleSpinBox()
        self.leverage_safety.setRange(0.1, 1.0)
        self.leverage_safety.setValue(LEVERAGE_SAFETY_BUFFER)
        self.leverage_safety.setSingleStep(0.05)
        self.leverage_safety.setToolTip("Safety buffer to reduce effective position size (0.8 = 80%)")
        leverage_settings_layout.addWidget(self.leverage_safety, 2, 1)
        
        # Warning label
        self.leverage_warning = QLabel("⚠️ Higher leverage increases both potential profits and losses")
        self.leverage_warning.setStyleSheet(f"color: {CyberpunkColors.WARNING};")
        leverage_settings_layout.addWidget(self.leverage_warning, 3, 0, 1, 2)
        
        # Add the leverage settings layout to the trading layout
        trading_layout.addLayout(leverage_settings_layout, 1, 0)
        
        # Token to HL Mapping (text area)
        trading_layout.addWidget(QLabel("Token to Hyperliquid Mapping:"), 2, 0)
        self.token_hl_mapping = QTextEdit()
        self.token_hl_mapping.setPlaceholderText("Format: SolanaTokenAddress,HyperliquidSymbol (one mapping per line)")
        mapping_text = ""
        for token, symbol in TOKEN_TO_HL_MAPPING.items():
            mapping_text += f"{token},{symbol}\n"
        self.token_hl_mapping.setPlainText(mapping_text)
        self.token_hl_mapping.setMaximumHeight(100)
        self.token_hl_mapping.setToolTip("Map Solana token addresses to Hyperliquid symbols")
        trading_layout.addWidget(self.token_hl_mapping, 3, 0)
        
        # Mirror with leverage toggle
        self.mirror_leverage = QCheckBox("Use Leverage When Mirroring")
        self.mirror_leverage.setChecked(MIRROR_WITH_LEVERAGE)  # Default from config.py
        self.leverage_safety.setToolTip("Multiply position size by this factor for safety (0.8 = 80% of calculated size)")
        leverage_settings_layout.addWidget(self.mirror_leverage, 4, 0, 1, 2)
        
        # Connect leverage mode toggle to enable/disable settings
        self.leverage_mode.toggled.connect(self.toggle_leverage_settings)
        
        # Add the trading mode group to the scroll layout
        scroll_layout.addWidget(trading_mode_group)
        
        # Add warning label
        leverage_warning = QLabel("⚠️ Higher leverage increases liquidation risk!")
        leverage_warning.setStyleSheet(f"color: {CyberpunkColors.WARNING}; font-weight: bold;")
        leverage_settings_layout.addWidget(leverage_warning, 5, 0, 1, 2)
        
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
        excluded_label = QLabel("Tokens to never trade (one per line):")
        excluded_layout.addWidget(excluded_label)
        
        self.excluded_tokens = QTextEdit()
        self.excluded_tokens.setPlaceholderText("Enter token addresses to exclude from trading, one per line")
        
        # Load excluded tokens from config
        from src.config import EXCLUDED_TOKENS, USDC_ADDRESS, SOL_ADDRESS
        excluded_text = "\n".join(EXCLUDED_TOKENS)
        self.excluded_tokens.setPlainText(excluded_text)
        
        self.excluded_tokens.setMinimumHeight(80)
        excluded_layout.addWidget(self.excluded_tokens)
        
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
        note_label.setStyleSheet(f"color: {CyberpunkColors.WARNING};")
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
        """Save the configuration to a file or update global variables"""
        try:
            # Update config.py with risk settings
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'config.py')
            
            # Read existing config file
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # Update values in the config content
            config_content = self.update_config_value(config_content, "USE_PERCENTAGE", str(self.use_percentage.isChecked()))
            config_content = self.update_config_value(config_content, "MAX_LOSS_PERCENT", str(self.max_loss_pct.value()))
            config_content = self.update_config_value(config_content, "MAX_GAIN_PERCENT", str(self.max_gain_pct.value()))
            config_content = self.update_config_value(config_content, "MAX_LOSS_USD", str(self.max_loss_usd.value()))
            config_content = self.update_config_value(config_content, "MAX_GAIN_USD", str(self.max_gain_usd.value()))
            config_content = self.update_config_value(config_content, "MINIMUM_BALANCE_USD", str(self.min_balance_usd.value()))
            
            # Update additional position sizing values
            config_content = self.update_config_value(config_content, "usd_size", str(self.usd_size.value()))
            config_content = self.update_config_value(config_content, "max_usd_order_size", str(self.max_usd_order_size.value()))
            config_content = self.update_config_value(config_content, "tx_sleep", str(self.tx_sleep.value()))
            config_content = self.update_config_value(config_content, "slippage", str(self.slippage.value()))

            # Update additional risk settings
            config_content = self.update_config_value(config_content, "CASH_PERCENTAGE", str(self.cash_percentage.value()))
            config_content = self.update_config_value(config_content, "MAX_POSITION_PERCENTAGE", str(self.max_position_percentage.value()))
            config_content = self.update_config_value(config_content, "SLEEP_AFTER_CLOSE", str(self.sleep_after_close.value()))
            config_content = self.update_config_value(config_content, "STOPLOSS_PRICE", str(self.stoploss_price.value()))
            config_content = self.update_config_value(config_content, "BREAKOUT_PRICE", str(self.breakout_price.value()))
            
            # Update leverage settings
            config_content = self.update_config_value(config_content, "DEFAULT_LEVERAGE", str(self.default_leverage.value()))
            config_content = self.update_config_value(config_content, "MAX_LEVERAGE", str(self.max_leverage.value()))
            config_content = self.update_config_value(config_content, "LEVERAGE_SAFETY_BUFFER", str(self.leverage_safety.value()))
            
            # Update time settings
            config_content = self.update_config_value(config_content, "MAX_LOSS_GAIN_CHECK_HOURS", str(self.max_loss_gain_check_hours.value()))
            config_content = self.update_config_value(config_content, "SLEEP_BETWEEN_RUNS_MINUTES", str(self.sleep_between_runs.value()))
            
            # Transaction settings
            config_content = self.update_config_value(config_content, "PRIORITY_FEE", str(self.priority_fee.value()))
            config_content = self.update_config_value(config_content, "orders_per_open", str(self.orders_per_open.value()))

            # Update paper trading settings
            config_content = self.update_config_value(config_content, "PAPER_TRADING_ENABLED", str(self.paper_trading_enabled.isChecked()))
            config_content = self.update_config_value(config_content, "PAPER_INITIAL_BALANCE", str(self.paper_initial_balance.value()))
            config_content = self.update_config_value(config_content, "PAPER_TRADING_SLIPPAGE", str(self.paper_trading_slippage.value()))
            config_content = self.update_config_value(config_content, "PAPER_TRADING_RESET_ON_START", str(self.paper_trading_reset_on_start.isChecked()))

            # Write updated config back to file
            with open(config_path, 'w') as f:
                f.write(config_content)
                
            # Update risk agent prompt if it has changed
            risk_agent_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'agents', 'risk_agent.py')
            with open(risk_agent_path, 'r') as f:
                risk_agent_content = f.read()
                
            # Create prompt text with proper escaping
            prompt_text = self.prompt_text.toPlainText()
            
            # Update the RISK_OVERRIDE_PROMPT in risk_agent.py
            import re
            updated_content = re.sub(r'RISK_OVERRIDE_PROMPT\s*=\s*""".*?"""', f'RISK_OVERRIDE_PROMPT = """\n{prompt_text}\n"""', risk_agent_content, flags=re.DOTALL)
            
            with open(risk_agent_path, 'w') as f:
                f.write(updated_content)
                
            # Update main.py with the continuous mode and interval settings
            main_py_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'main.py')
            try:
                with open(main_py_path, 'r') as f:
                    main_content = f.read()
                    
                # Update the risk agent interval in ACTIVE_AGENTS
                if not self.run_mode.isChecked():
                    # Only update interval if not in continuous mode
                    pattern = r"'risk':\s*{\s*'active':\s*True,\s*'interval':\s*\d+"
                    replacement = f"'risk': {{'active': True, 'interval': {self.sleep_between_runs.value()}"
                    main_content = re.sub(pattern, replacement, main_content)
                    
                # Save changes to main.py
                with open(main_py_path, 'w') as f:
                    f.write(main_content)
                    
                # Also update SLEEP_BETWEEN_RUNS_MINUTES in config.py for compatibility
                config_content = self.update_config_value(config_content, "SLEEP_BETWEEN_RUNS_MINUTES", str(self.sleep_between_runs.value()))
                    
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not update interval in main.py: {str(e)}\nThe interval was updated in config.py only.")
                
            # Show confirmation dialog
            QMessageBox.information(self, "Configuration Saved", 
                "Risk Management configuration has been saved successfully.\n\n"
                "To apply these changes, restart the Risk Management agent.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
            
    def update_config_value(self, content, key, value):
        """Helper function to update a value in the config file content"""
        import re
        pattern = rf"{key}\s*=\s*.*"
        replacement = f"{key} = {value}"
        return re.sub(pattern, replacement, content)

    def toggle_interval_input(self, checked):
        """Enable or disable the sleep between runs input based on continuous mode"""
        self.sleep_between_runs.setDisabled(checked)
        if checked:
            self.sleep_between_runs.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {CyberpunkColors.BACKGROUND};
                    color: rgba(224, 224, 224, 100);
                    border: 1px solid rgba(0, 255, 255, 100);
                    border-radius: 2px;
                    padding: 2px;
                }}
            """)
        else:
            self.sleep_between_runs.setStyleSheet(f"""
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

    def toggle_leverage_settings(self, checked, show_warning=True):
        """Enable or disable leverage settings based on leverage mode toggle"""
        # Enable or disable the settings
        self.mirror_leverage.setEnabled(checked)
        self.token_hl_mapping.setEnabled(checked)
        self.default_leverage.setEnabled(checked)
        self.max_leverage.setEnabled(checked)
        self.leverage_safety.setEnabled(checked)
        self.leverage_warning.setVisible(checked)
        
        # Fade out or restore the settings' appearance
        if checked:
            # Normal appearance
            self.mirror_leverage.setStyleSheet("")
            self.token_hl_mapping.setStyleSheet("")
            self.default_leverage.setStyleSheet("")
            self.max_leverage.setStyleSheet("")
            self.leverage_safety.setStyleSheet("")
            
            # Show a warning about trading risks - only when manually toggled, not during initialization
            if show_warning:
                QMessageBox.warning(self, "Leverage Trading Enabled", 
                    "⚠️ Leverage trading carries significant risk:\n\n"
                    "• Higher potential for liquidation\n"
                    "• Amplified losses on market downturns\n"
                    "• Higher trading fees\n\n"
                    "Make sure you understand the risks before using leverage."
                )
        else:
            # Faded appearance
            disabled_style = f"""
                QTextEdit, QCheckBox, QDoubleSpinBox {{
                    color: rgba(224, 224, 224, 100);
                    border: 1px solid rgba(0, 255, 255, 100);
                }}
            """
            self.mirror_leverage.setStyleSheet(disabled_style)
            self.token_hl_mapping.setStyleSheet(disabled_style)
            self.default_leverage.setStyleSheet(disabled_style)
            self.max_leverage.setStyleSheet(disabled_style)
            self.leverage_safety.setStyleSheet(disabled_style)

    def save_config(self):
        """Save the CopyBot configuration to config.py"""
        try:
            # Update config.py with CopyBot settings
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'config.py')
            
            # Read existing config file
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # Update trading mode configuration
            if self.leverage_mode.isChecked():
                config_content = self.update_config_value(config_content, "TRADING_MODE", '"leverage"')
                config_content = self.update_config_value(config_content, "USE_HYPERLIQUID", "True")
            else:
                config_content = self.update_config_value(config_content, "TRADING_MODE", '"spot"')
                config_content = self.update_config_value(config_content, "USE_HYPERLIQUID", "False")
            
            # Update mirror with leverage setting
            config_content = self.update_config_value(config_content, "MIRROR_WITH_LEVERAGE", str(self.mirror_leverage.isChecked()))
            
            # Update leverage settings
            config_content = self.update_config_value(config_content, "DEFAULT_LEVERAGE", str(self.default_leverage.value()))
            config_content = self.update_config_value(config_content, "MAX_LEVERAGE", str(self.max_leverage.value()))
            config_content = self.update_config_value(config_content, "LEVERAGE_SAFETY_BUFFER", str(self.leverage_safety.value()))
            
            # Update TOKEN_TO_HL_MAPPING
            mapping_text = self.token_hl_mapping.toPlainText().strip()
            if mapping_text:
                mapping_lines = mapping_text.split('\n')
                mapping_dict = {}
                for line in mapping_lines:
                    if ',' in line:
                        token, symbol = line.split(',', 1)
                        token = token.strip()
                        symbol = symbol.strip()
                        if token and symbol:
                            mapping_dict[token] = symbol
                
                # Create TOKEN_TO_HL_MAPPING string
                mapping_str = "TOKEN_TO_HL_MAPPING = {\n"
                for token, symbol in mapping_dict.items():
                    mapping_str += f"    '{token}': '{symbol}',\n"
                mapping_str += "}"
                
                # Replace TOKEN_TO_HL_MAPPING in config.py
                import re
                pattern = r"TOKEN_TO_HL_MAPPING\s*=\s*{[^}]*}"
                if re.search(pattern, config_content, re.DOTALL):
                    config_content = re.sub(pattern, mapping_str, config_content, flags=re.DOTALL)
                else:
                    # If pattern doesn't exist, add it to the end
                    config_content += f"\n\n{mapping_str}\n"
            
            # Update token tracking filter settings
            config_content = self.update_config_value(config_content, "FILTER_MODE", f'"{self.filter_mode.currentText()}"')
            config_content = self.update_config_value(config_content, "ENABLE_PERCENTAGE_FILTER", str(self.percentage_filter.isChecked()))
            config_content = self.update_config_value(config_content, "PERCENTAGE_THRESHOLD", str(self.percentage_threshold.value()))
            config_content = self.update_config_value(config_content, "ENABLE_AMOUNT_FILTER", str(self.amount_filter.isChecked()))
            config_content = self.update_config_value(config_content, "AMOUNT_THRESHOLD", str(self.amount_threshold.value()))
            config_content = self.update_config_value(config_content, "ENABLE_ACTIVITY_FILTER", str(self.activity_filter.isChecked()))
            config_content = self.update_config_value(config_content, "ACTIVITY_WINDOW_HOURS", str(self.activity_window.value()))
            
            # Update Monitored Tokens list
            monitored_tokens_text = self.monitored_tokens.toPlainText().strip()
            if monitored_tokens_text:
                monitored_tokens_list = [token.strip() for token in monitored_tokens_text.split('\n') if token.strip()]
                monitored_tokens_str = "MONITORED_TOKENS = [\n"
                for token in monitored_tokens_list:
                    monitored_tokens_str += f"    '{token}',\n"
                monitored_tokens_str += "]\n"
                
                # Replace MONITORED_TOKENS in config.py
                pattern = r"MONITORED_TOKENS\s*=\s*\[[^\]]*\]"
                if re.search(pattern, config_content, re.DOTALL):
                    config_content = re.sub(pattern, monitored_tokens_str, config_content, flags=re.DOTALL)
                else:
                    # If pattern doesn't exist, add it to the end
                    config_content += f"\n\n{monitored_tokens_str}\n"
            
            # Update Excluded Tokens list
            excluded_tokens_text = self.excluded_tokens.toPlainText().strip()
            additional_excluded = self.additional_excluded.toPlainText().strip()
            
            # Make sure USDC and SOL addresses are always included
            from src.config import USDC_ADDRESS, SOL_ADDRESS
            excluded_tokens_list = [token.strip() for token in excluded_tokens_text.split('\n') if token.strip()]
            
            # Add additional excluded tokens
            if additional_excluded:
                excluded_tokens_list.extend([token.strip() for token in additional_excluded.split('\n') if token.strip()])
            
            # Make sure USDC and SOL are in the list
            if USDC_ADDRESS not in excluded_tokens_list:
                excluded_tokens_list.append(USDC_ADDRESS)
            if SOL_ADDRESS not in excluded_tokens_list:
                excluded_tokens_list.append(SOL_ADDRESS)
            
            excluded_tokens_str = "EXCLUDED_TOKENS = [USDC_ADDRESS, SOL_ADDRESS"
            for token in excluded_tokens_list:
                if token != USDC_ADDRESS and token != SOL_ADDRESS:
                    excluded_tokens_str += f", '{token}'"
            excluded_tokens_str += "]\n"
            
            # Replace EXCLUDED_TOKENS in config.py
            pattern = r"EXCLUDED_TOKENS\s*=\s*\[[^\]]*\]"
            if re.search(pattern, config_content, re.DOTALL):
                config_content = re.sub(pattern, excluded_tokens_str, config_content, flags=re.DOTALL)
            else:
                # If pattern doesn't exist, add it to the end
                config_content += f"\n\n{excluded_tokens_str}\n"
            
            # Write updated config back to file
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Update WALLETS_TO_TRACK in token_list_tool.py
            token_list_tool_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'scripts', 'token_list_tool.py')
            wallets_text = self.wallets_to_track.toPlainText().strip()
            
            if wallets_text and os.path.exists(token_list_tool_path):
                with open(token_list_tool_path, 'r') as f:
                    token_list_content = f.read()
                
                # Extract wallet addresses as a list
                wallet_list = [wallet.strip() for wallet in wallets_text.split('\n') if wallet.strip()]
                
                # Create WALLETS_TO_TRACK string
                wallets_str = "WALLETS_TO_TRACK = [\n"
                for wallet in wallet_list:
                    wallets_str += f"    \"{wallet}\",  # 80% win rate & high pnl\n"
                wallets_str += "  \n\n    # Add more wallets here...\n]"
                
                # Replace WALLETS_TO_TRACK in token_list_tool.py
                pattern = r"WALLETS_TO_TRACK\s*=\s*\[[^\]]*\]"
                if re.search(pattern, token_list_content, re.DOTALL):
                    token_list_content = re.sub(pattern, wallets_str, token_list_content, flags=re.DOTALL)
                    
                    # Write updated token_list_tool.py back to file
                    with open(token_list_tool_path, 'w') as f:
                        f.write(token_list_content)
                else:
                    QMessageBox.warning(self, "Warning", "Could not find WALLETS_TO_TRACK in token_list_tool.py")
            
            # Show confirmation dialog
            QMessageBox.information(self, "Configuration Saved", 
                "CopyBot configuration has been saved successfully.\n\n" +
                ("Leverage trading is now ENABLED." if self.leverage_mode.isChecked() else "Spot trading mode is now active.") +
                "\n\nTo apply these changes, restart the CopyBot agent.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
            
    def update_config_value(self, content, key, value):
        """Helper function to update a value in the config file content"""
        import re
        pattern = rf"{key}\s*=\s*.*"
        replacement = f"{key} = {value}"
        return re.sub(pattern, replacement, content)

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
                
        # Timeframes
        chart_layout.addWidget(QLabel("Timeframes:"), 1, 0)
        self.timeframes = QLineEdit("4h,1d")  # Updated for longer-term analysis
        self.timeframes.setToolTip("Comma-separated list of timeframes to analyze (e.g., 4h,1d,1w for long-term analysis)")
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
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'config.py')
            
            # Read existing config file
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # Update DCA/Staking values in the config content
            config_content = self.update_config_value(config_content, "STAKING_ALLOCATION_PERCENTAGE", str(self.staking_allocation.value()))
            config_content = self.update_config_value(config_content, "DCA_INTERVAL_MINUTES", str(self.dca_interval.value()))
            config_content = self.update_config_value(config_content, "TAKE_PROFIT_PERCENTAGE", str(self.take_profit.value()))
            config_content = self.update_config_value(config_content, "FIXED_DCA_AMOUNT", str(self.fixed_dca_amount.value()))
            
            # Update Chart Analysis settings
            timeframes_text = self.timeframes.text()
            timeframes_list = timeframes_text.split(',')
            timeframes_formatted = "', '".join(timeframes_list)
            timeframes_value = f"['{timeframes_formatted}']"
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
            
            # Update Buy/Sell confidence thresholds
            config_content = self.update_config_value(config_content, "BUY_CONFIDENCE_THRESHOLD", str(self.buy_confidence.value()))
            config_content = self.update_config_value(config_content, "SELL_CONFIDENCE_THRESHOLD", str(self.sell_confidence.value()))
            
            # Write updated config back to file
            with open(config_path, 'w') as f:
                f.write(config_content)
                
            # Update chart analysis agent prompt
            chart_agent_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'agents', 'chartanalysis_agent.py')
            with open(chart_agent_path, 'r') as f:
                chart_agent_content = f.read()
                
            # Create prompt text with proper escaping
            prompt_text = self.prompt_text.toPlainText()
            
            # Update the CHART_ANALYSIS_PROMPT in chart_analysis_agent.py
            import re
            updated_content = re.sub(r'CHART_ANALYSIS_PROMPT\s*=\s*""".*?"""', f'CHART_ANALYSIS_PROMPT = """\n{prompt_text}\n"""', chart_agent_content, flags=re.DOTALL)
            
            # Update the MODEL_OVERRIDE in chart_analysis_agent.py
            updated_content = self.update_config_value(updated_content, "MODEL_OVERRIDE", f'"{self.model_override.currentText()}"')
            
            with open(chart_agent_path, 'w') as f:
                f.write(updated_content)
                
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
            
            # Update TOKEN_MAP in config.py
            token_map_str = "TOKEN_MAP = {\n"
            for address, (symbol, hl_symbol) in token_map_dict.items():
                token_map_str += f"    '{address}': ('{symbol}', '{hl_symbol}'),\n"
            token_map_str += "}"
            
            # Replace TOKEN_MAP in config.py
            pattern = r"TOKEN_MAP\s*=\s*{[^}]+}"
            config_content = re.sub(pattern, token_map_str, config_content, flags=re.DOTALL)
            
            with open(config_path, 'w') as f:
                f.write(config_content)
                
            # Update DCA_MONITORED_TOKENS in config.py
            dca_tokens_str = "DCA_MONITORED_TOKENS = " + str(list(token_map_dict.keys()))
            config_content = self.update_config_value(config_content, "DCA_MONITORED_TOKENS", dca_tokens_str.replace("'", '"'))
            
            with open(config_path, 'w') as f:
                f.write(config_content)
                
            # Show confirmation dialog
            QMessageBox.information(self, "Configuration Saved", 
                "DCA/Staking System configuration has been saved successfully.\n\n"
                "To apply these changes, restart the DCA/Staking and Chart Analysis agents.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
            
    def update_config_value(self, content, key, value):
        """Helper function to update a value in the config file content"""
        import re
        pattern = rf"{key}\s*=\s*.*"
        replacement = f"{key} = {value}"
        return re.sub(pattern, replacement, content)
    
class AIPromptGuideTab(QWidget):
    """Tab for AI Prompt Key Variables and Terms"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("AI Prompt Key Variables Guide")
        title_label.setStyleSheet(f"color: {CyberpunkColors.PRIMARY}; font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "When customizing AI prompts in other tabs, make sure to include these key variables "
            "to ensure the agents function properly. Each agent requires specific variables to "
            "be included in their prompts for proper analysis and decision making."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {CyberpunkColors.TEXT_LIGHT}; font-size: 14px; margin-bottom: 20px;")
        main_layout.addWidget(desc_label)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"background-color: {CyberpunkColors.BACKGROUND}; border: none;")
        
        # Container widget for scroll area
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(20)
        
        # Risk Agent Variables
        risk_frame = self.create_agent_frame(
            "Risk Management Agent Variables",
            CyberpunkColors.DANGER,
            [
                {"name": "{limit_type}", "description": "Type of limit that was hit (MAX_LOSS or MAX_GAIN)"},
                {"name": "{position_data}", "description": "JSON data of current positions and their market data"},
                {"name": "{breach_type}", "description": "Type of limit breach (MINIMUM_BALANCE, PNL_USD, or PNL_PERCENT)"},
                {"name": "{context}", "description": "Description of the current situation and limit breach"},
                {"name": "{positions_str}", "description": "Formatted string showing current positions"}
            ]
        )
        scroll_layout.addWidget(risk_frame)
        
        # CopyBot Agent Variables
        copybot_frame = self.create_agent_frame(
            "CopyBot Agent Variables",
            CyberpunkColors.TERTIARY,
            [
                {"name": "{portfolio_data}", "description": "Current copybot portfolio positions and performance"},
                {"name": "{market_data}", "description": "OHLCV market data and technical indicators for each position"}
            ]
        )
        scroll_layout.addWidget(copybot_frame)
        
        # Chart Analysis Agent Variables
        chart_frame = self.create_agent_frame(
            "Chart Analysis Agent Variables",
            CyberpunkColors.PRIMARY,
            [
                {"name": "{symbol}", "description": "Trading symbol/token being analyzed"},
                {"name": "{timeframe}", "description": "Chart timeframe (1m, 5m, 15m, 1h, etc.)"},
                {"name": "{chart_data}", "description": "Recent price action, technical indicators, and other chart data"}
            ]
        )
        scroll_layout.addWidget(chart_frame)
        
        # DCA Staking Agent Variables
        dca_frame = self.create_agent_frame(
            "DCA & Staking Agent Variables",
            CyberpunkColors.SUCCESS,
            [
                {"name": "{token_list}", "description": "List of tokens being monitored"},
                {"name": "{staking_rewards}", "description": "Current staking rewards data"},
                {"name": "{apy_data}", "description": "APY data for various pools and staking options"},
                {"name": "{market_conditions}", "description": "Current market conditions and trends"}
            ]
        )
        scroll_layout.addWidget(dca_frame)
        
        # General Formatting Guidelines
        formatting_frame = self.create_info_frame(
            "Response Format Guidelines",
            CyberpunkColors.SECONDARY,
            [
                "Each agent expects responses in specific formats.",
                "When customizing prompts, make sure to instruct the AI to maintain these formats:",
                "",
                "• Risk Agent: Expects 'OVERRIDE: <reason>' or 'RESPECT_LIMIT: <reason>'",
                "• CopyBot Agent: First line must be 'BUY', 'SELL', or 'NOTHING'",
                "• Chart Analysis Agent: First line must be 'BUY', 'SELL', or 'NOTHING', followed by reasoning and confidence",
                "• Confidence levels should be expressed as percentages (e.g., 'Confidence: 75%')"
            ]
        )
        scroll_layout.addWidget(formatting_frame)
        
        # Best Practices
        practices_frame = self.create_info_frame(
            "AI Prompt Best Practices",
            CyberpunkColors.WARNING,
            [
                "• Keep variables in curly braces exactly as shown: {variable_name}",
                "• Don't remove required variables from prompts",
                "• Be specific about what indicators to analyze",
                "• Specify risk parameters clearly",
                "• Include instructions for dealing with market conditions",
                "• Tell the AI exactly what format to respond in",
                "• Test any prompt changes with small trades first",
                "• Back up original prompts before customizing"
            ]
        )
        scroll_layout.addWidget(practices_frame)
        
        # Add the scroll area to the main layout
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
    def create_agent_frame(self, title, color, variables):
        """Create a frame for displaying agent variables"""
        frame = NeonFrame(color)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Variables table
        table = QTableWidget()
        table.setColumnCount(2)
        table.setRowCount(len(variables))
        table.setHorizontalHeaderLabels(["Variable", "Description"])
        table.horizontalHeader().setStyleSheet(f"color: {CyberpunkColors.TEXT_LIGHT};")
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setFixedHeight(30)
        table.setColumnWidth(0, 200)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
            QTableWidget::item {{
                padding: 5px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        
        # Populate table
        for i, var in enumerate(variables):
            # Variable name
            var_item = QTableWidgetItem(var["name"])
            var_item.setForeground(QColor(color))
            var_item.setFont(QFont("monospace", 10))
            table.setItem(i, 0, var_item)
            
            # Description
            desc_item = QTableWidgetItem(var["description"])
            desc_item.setForeground(QColor(CyberpunkColors.TEXT_LIGHT))
            table.setItem(i, 1, desc_item)
        
        table.setFixedHeight(len(variables) * 40 + 40)  # Adjust height based on content
        layout.addWidget(table)
        
        return frame
    
    def create_info_frame(self, title, color, bullet_points):
        """Create an information frame with bullet points"""
        frame = NeonFrame(color)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Bullet points
        for point in bullet_points:
            point_label = QLabel(point)
            point_label.setWordWrap(True)
            point_label.setStyleSheet(f"color: {CyberpunkColors.TEXT_LIGHT};")
            layout.addWidget(point_label)
        
        return frame

class TrackerTab(QWidget):
    """Widget for tracking CopyBot system activity"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        # Create a scroll area to contain all sections
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: none;
            }}
        """)
        
        # Create a container widget for the scroll area
        container = QWidget()
        container.setObjectName("scrollContainer")
        container.setStyleSheet(f"""
            QWidget#scrollContainer {{
                background-color: {CyberpunkColors.BACKGROUND};
            }}
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(20)  # Add spacing between sections
        
        # Current Tracked Tokens Section
        tracked_tokens_group = QGroupBox("Current Tracked Tokens")
        tracked_tokens_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: {CyberpunkColors.PRIMARY};
            }}
        """)
        tracked_tokens_layout = QVBoxLayout(tracked_tokens_group)
        
        self.tokens_table = QTableWidget()
        self.tokens_table.setColumnCount(6)  # Increase from 4 to 6 columns
        self.tokens_table.setHorizontalHeaderLabels(["Wallet", "Mint", "Token", "Symbol", "Amount", "Last Updated"])
        self.tokens_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tokens_table.setAlternatingRowColors(True)
        self.tokens_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                gridline-color: {CyberpunkColors.PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
            QTableWidget::item:alternate {{
                background-color: #1A1A24;
            }}
            /* Fix for the white row number column */
            QTableView QTableCornerButton::section {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
            QTableWidget QHeaderView::section:vertical {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
        """)
        
        # Set a fixed height for the table (adjust this value as needed)
        self.tokens_table.setMinimumHeight(400)  # Adjust this value as needed to match the image
        
        tracked_tokens_layout.addWidget(self.tokens_table)
        
        refresh_tokens_btn = NeonButton("Refresh Tokens", CyberpunkColors.PRIMARY)
        refresh_tokens_btn.clicked.connect(self.refresh_tracked_tokens)
        tracked_tokens_layout.addWidget(refresh_tokens_btn)
        
        # Add stats label to show tokens found and skipped
        self.token_stats_label = QLabel("Token Stats: No data available")
        self.token_stats_label.setStyleSheet(f"""
            color: {CyberpunkColors.TEXT_LIGHT};
            padding: 5px;
            background-color: rgba(0, 0, 0, 0.5);
            border: 1px solid {CyberpunkColors.PRIMARY};
            border-radius: 3px;
        """)
        self.token_stats_label.setAlignment(Qt.AlignCenter)
        tracked_tokens_layout.addWidget(self.token_stats_label)
        
        container_layout.addWidget(tracked_tokens_group)
        
        # New Change Detection Section
        change_detection_group = QGroupBox("Change Detection")
        change_detection_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: {CyberpunkColors.PRIMARY};
            }}
        """)
        change_detection_layout = QVBoxLayout(change_detection_group)
        
        self.changes_table = QTableWidget()
        self.changes_table.setColumnCount(9)  # Increase from 7 to 9 columns
        self.changes_table.setHorizontalHeaderLabels(["Time", "Type", "Wallet", "Mint", "Token", "Symbol", "Amount", "Change", "% Change"])
        self.changes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.changes_table.setAlternatingRowColors(True)
        self.changes_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                gridline-color: {CyberpunkColors.PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
            QTableWidget::item:alternate {{
                background-color: #1A1A24;
            }}
            /* Fix for the white row number column */
            QTableView QTableCornerButton::section {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
            QTableWidget QHeaderView::section:vertical {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
        """)
        
        # Set a fixed height for the changes table
        self.changes_table.setMinimumHeight(400)  # Make this table take up space
        
        change_detection_layout.addWidget(self.changes_table)
        
        # Add buttons for the change detection section
        button_row = QHBoxLayout()
        
        refresh_changes_btn = NeonButton("Refresh Changes", CyberpunkColors.PRIMARY)
        refresh_changes_btn.clicked.connect(self.manual_refresh_changes)
        button_row.addWidget(refresh_changes_btn)
        
        clear_changes_btn = NeonButton("Clear Changes", CyberpunkColors.WARNING)
        clear_changes_btn.clicked.connect(self.clear_changes)
        button_row.addWidget(clear_changes_btn)
        
        
        change_detection_layout.addLayout(button_row)
        
        container_layout.addWidget(change_detection_group)
        
        # New AI Analysis Section
        ai_analysis_group = QGroupBox("AI Analysis Results")
        ai_analysis_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: {CyberpunkColors.PRIMARY};
            }}
        """)
        ai_analysis_layout = QVBoxLayout(ai_analysis_group)
        
        self.analysis_table = QTableWidget()
        self.analysis_table.setColumnCount(8)  # Increase from 6 to 8 columns
        self.analysis_table.setHorizontalHeaderLabels(["Time", "Action", "Token", "Symbol", "Mint", "Analysis", "Confidence", "Price"])
        self.analysis_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.analysis_table.setAlternatingRowColors(True)
        self.analysis_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                gridline-color: {CyberpunkColors.PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
            QTableWidget::item:alternate {{
                background-color: #1A1A24;
            }}
            /* Fix for the white row number column */
            QTableView QTableCornerButton::section {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
            QTableWidget QHeaderView::section:vertical {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
        """)
        
        # Set a fixed height for the analysis table
        self.analysis_table.setMinimumHeight(400)  # Make this table take up space
        
        ai_analysis_layout.addWidget(self.analysis_table)
        
        clear_analysis_btn = NeonButton("Clear Analysis", CyberpunkColors.WARNING)
        clear_analysis_btn.clicked.connect(self.clear_analysis)
        ai_analysis_layout.addWidget(clear_analysis_btn)
        
        
        container_layout.addWidget(ai_analysis_group)
        
        # Set the container as the scroll area's widget
        scroll_area.setWidget(container)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)

        # Force initial refresh after UI is fully loaded
        QTimer.singleShot(2000, self.refresh_tracked_tokens)
    
    def refresh_tracked_tokens(self):
        """Refresh the tracked tokens table from the artificial memory files"""
        from datetime import datetime
        import os
        import json
        
        self.tokens_table.setRowCount(0)  # Clear existing data
        
        # Determine which memory file to use based on DYNAMIC_MODE
        from src.config import DYNAMIC_MODE
        memory_file = os.path.join(
            os.getcwd(), 
            "src/data/artificial_memory_d.json" if DYNAMIC_MODE else "src/data/artificial_memory_m.json"
        )
        
        try:
            if os.path.exists(memory_file):
                with open(memory_file, "r") as f:
                    memory_data = json.load(f)
                
                # Extract wallet data
                wallet_data = memory_data.get('data', {}).get('data', {})
                if not wallet_data and 'data' in memory_data:
                    wallet_data = memory_data['data']  # Handle different structure
                
                row = 0
                wallet_token_stats = {}  # To track tokens per wallet
                
                for wallet, tokens in wallet_data.items():
                    wallet_token_stats[wallet] = len(tokens)
                    for token_data in tokens:
                        self.tokens_table.insertRow(row)
                        self.tokens_table.setItem(row, 0, QTableWidgetItem(wallet))
                        
                        # Get token mint, name and symbol
                        token_mint = token_data.get('mint', 'Unknown')
                        token_name = token_data.get('name', 'Unknown Token')
                        token_symbol = token_data.get('symbol', 'UNK')
                        
                        # Display mint, name and symbol
                        self.tokens_table.setItem(row, 1, QTableWidgetItem(token_mint))
                        self.tokens_table.setItem(row, 2, QTableWidgetItem(token_name))
                        self.tokens_table.setItem(row, 3, QTableWidgetItem(token_symbol))
                        # Amount in column 4
                        self.tokens_table.setItem(row, 4, QTableWidgetItem(str(token_data.get('amount', 0))))
                        
                        # Format timestamp (now in column 5)
                        timestamp = token_data.get('timestamp', '')
                        try:
                            dt = datetime.fromisoformat(timestamp)
                            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            formatted_time = timestamp
                            
                        self.tokens_table.setItem(row, 5, QTableWidgetItem(formatted_time))
                        row += 1
                
                # Look for tokens found/skipped stats in the memory data
                stats_text = "Token Stats: "
                
                # Get wallet stats directly from the cache file - FIX FOR NESTED STRUCTURE
                wallet_stats = {}
                if 'data' in memory_data and 'wallet_stats' in memory_data['data']:
                    wallet_stats = memory_data['data']['wallet_stats']
                else:
                    wallet_stats = memory_data.get('wallet_stats', {})
                
                stats_parts = []
                
                # Simple display of found/skipped counts
                for wallet, stats in wallet_stats.items():
                    found = stats.get('found', 0)
                    skipped = stats.get('skipped', 0)
                    short_wallet = wallet[:4]
                    stats_parts.append(f"{short_wallet}: {found} found, {skipped} skipped")
                
                if stats_parts:
                    stats_text += " | ".join(stats_parts)
                else:
                    # Fallback to just showing token counts if no stats available
                    for wallet, count in wallet_token_stats.items():
                        short_wallet = wallet[:4]
                        stats_parts.append(f"{short_wallet}: {count} tokens")
                    if stats_parts:
                        stats_text += " | ".join(stats_parts)
                    else:
                        stats_text += "No tokens found"
                
                # Update the stats label
                self.token_stats_label.setText(stats_text)
                
        except Exception as e:
            print(f"Error refreshing tracked tokens: {str(e)}")
            self.token_stats_label.setText(f"Token Stats: Error loading data - {str(e)}")
    
    def manual_refresh_changes(self):
        """Manually refresh changes by running the tracker once - for button click only"""
        from datetime import datetime
        import time
        from src.scripts.token_list_tool import TokenAccountTracker
        
        try:
            # Show a message in the UI
            print("Manually refreshing token changes...")
            
            # Get token tracker
            tracker = TokenAccountTracker()
            
            # Get cached data before updates
            cache_data, _ = tracker.load_cache()
            
            # Run the tracker once to detect real changes
            wallet_results = tracker.track_all_wallets()
            
            # Detect changes
            changes = tracker.detect_changes(cache_data, wallet_results)
            
            # Process changes into the changes table
            if changes:
                # Clear the table first for a fresh view
                self.clear_changes()
                self.process_token_changes(changes)
                print(f"Found and displayed {len(changes)} change events")
            else:
                print("No changes detected")
            
            # Also refresh the tokens table and stats
            self.refresh_tracked_tokens()
                
        except Exception as e:
            print(f"Error manually refreshing changes: {str(e)}")
    
    def refresh_change_detection(self):
        """Refresh the change detection table from token_list_tool"""
        from datetime import datetime
        import os
        import json
        import time
        from src.scripts.token_list_tool import TokenAccountTracker
        
        # Add a cooldown to prevent excessive refreshing
        current_time = time.time()
        if hasattr(self, 'last_change_detection_update') and current_time - self.last_change_detection_update < 30:
            # If the last update was less than 30 seconds ago, don't refresh again
            return
        
        # Update the timestamp
        self.last_change_detection_update = current_time
        
        try:
            # Get token tracker and data
            tracker = TokenAccountTracker()
            
            # Get cached data before any updates
            cache_data, _ = tracker.load_cache()
            
            # Process the changes directly from the cached data instead of calling track_all_wallets
            # which might be triggering the loop
            current_results = cache_data.get('data', {})
            
            # Process the changes
            changes = tracker.detect_changes(cache_data, current_results)
            
            # Process changes into the changes table
            self.process_token_changes(changes)
            
        except Exception as e:
            print(f"Error refreshing change detection: {str(e)}")
    
    def process_token_changes(self, changes):
        """Process detected changes from token tracker into the UI"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for wallet, wallet_changes in changes.items():
            # Process new tokens
            for token_mint, details in wallet_changes.get('new', {}).items():
                token_name = details.get('name', 'Unknown Token')
                token_symbol = details.get('symbol', 'UNK')
                amount = details.get('amount', 0)
                
                self.add_change_event(
                    timestamp=timestamp,
                    event_type="NEW",
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_symbol,
                    token_mint=token_mint,
                    amount=amount,
                    token_name=token_name
                )
            
            # Process removed tokens
            for token_mint, details in wallet_changes.get('removed', {}).items():
                token_name = details.get('name', 'Unknown Token')
                token_symbol = details.get('symbol', 'UNK')
                amount = details.get('amount', 0)
                
                self.add_change_event(
                    timestamp=timestamp,
                    event_type="REMOVED",
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_symbol,
                    token_mint=token_mint,
                    amount=amount,
                    token_name=token_name
                )
            
            # Process modified tokens
            for token_mint, details in wallet_changes.get('modified', {}).items():
                token_name = details.get('name', 'Unknown Token')
                token_symbol = details.get('symbol', 'UNK')
                
                self.add_change_event(
                    timestamp=timestamp,
                    event_type="MODIFIED",
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_symbol,
                    token_mint=token_mint,
                    amount=details['current_amount'],
                    change=details['change'],
                    percent_change=details['pct_change'],
                    token_name=token_name
                )
    
    def clear_changes(self):
        """Clear all change detection events from the table"""
        self.changes_table.setRowCount(0)
    
    def add_change_event(self, timestamp, event_type, wallet, token, token_symbol=None, token_mint=None, amount=None, change=None, percent_change=None, token_name=None):
        """Add a new change detection event to the table"""
        row_position = self.changes_table.rowCount()
        self.changes_table.insertRow(row_position)
        
        # Set each cell value
        self.changes_table.setItem(row_position, 0, QTableWidgetItem(timestamp))
        
        # Color-code the event type cell
        event_item = QTableWidgetItem(event_type)
        if event_type.upper() == "NEW":
            event_item.setForeground(QColor(CyberpunkColors.SUCCESS))
        elif event_type.upper() == "REMOVED":
            event_item.setForeground(QColor(CyberpunkColors.DANGER))
        elif event_type.upper() == "MODIFIED":
            event_item.setForeground(QColor(CyberpunkColors.WARNING))
        self.changes_table.setItem(row_position, 1, event_item)
        
        self.changes_table.setItem(row_position, 2, QTableWidgetItem(wallet))
        
        # Token mint, name and symbol
        self.changes_table.setItem(row_position, 3, QTableWidgetItem(token_mint or "Unknown"))
        self.changes_table.setItem(row_position, 4, QTableWidgetItem(token))
        self.changes_table.setItem(row_position, 5, QTableWidgetItem(token_symbol or "UNK"))
        
        # Amount, change, and percent change columns
        self.changes_table.setItem(row_position, 6, QTableWidgetItem(str(amount) if amount is not None else "N/A"))
        
        # Set change and percent change if provided
        if change is not None:
            change_item = QTableWidgetItem(str(change))
            if change > 0:
                change_item.setForeground(QColor(CyberpunkColors.SUCCESS))
            elif change < 0:
                change_item.setForeground(QColor(CyberpunkColors.DANGER))
            self.changes_table.setItem(row_position, 7, change_item)
        else:
            self.changes_table.setItem(row_position, 7, QTableWidgetItem("N/A"))
        
        if percent_change is not None:
            pct_item = QTableWidgetItem(f"{percent_change}%")
            if percent_change > 0:
                pct_item.setForeground(QColor(CyberpunkColors.SUCCESS))
            elif percent_change < 0:
                pct_item.setForeground(QColor(CyberpunkColors.DANGER))
            self.changes_table.setItem(row_position, 8, pct_item)
        else:
            self.changes_table.setItem(row_position, 8, QTableWidgetItem("N/A"))
                
        # Force a repaint and make sure the table is visible
        self.changes_table.repaint()
        self.changes_table.show()
        
        # Scroll to the newest event
        self.changes_table.scrollToBottom()
    
    def clear_analysis(self):
        """Clear all AI analysis events from the table"""
        self.analysis_table.setRowCount(0)
        
    def add_ai_analysis(self, timestamp, action, token, token_symbol, analysis, confidence, price, change_percent=None, token_mint=None, token_name=None):
        """Add an AI analysis event to the analysis table"""
        row = self.analysis_table.rowCount()
        self.analysis_table.insertRow(row)
        
        # Set the items in each column
        self.analysis_table.setItem(row, 0, QTableWidgetItem(timestamp))
        
        # Color-code the action cell based on BUY/SELL/NOTHING
        action_item = QTableWidgetItem(action)
        if action.upper() == "BUY":
            action_item.setForeground(QColor(CyberpunkColors.SUCCESS))
        elif action.upper() == "SELL":
            action_item.setForeground(QColor(CyberpunkColors.DANGER))
        self.analysis_table.setItem(row, 1, action_item)
        
        self.analysis_table.setItem(row, 2, QTableWidgetItem(token))
        self.analysis_table.setItem(row, 3, QTableWidgetItem(token_symbol))
        self.analysis_table.setItem(row, 4, QTableWidgetItem(token_mint or "Unknown"))
        self.analysis_table.setItem(row, 5, QTableWidgetItem(analysis))
        
        # Add confidence with percentage
        self.analysis_table.setItem(row, 6, QTableWidgetItem(f"{confidence}%"))
        
        # Add price
        self.analysis_table.setItem(row, 7, QTableWidgetItem(price))
                
        # Force a repaint and make sure the table is visible
        self.analysis_table.repaint()
        self.analysis_table.show()
        
        # Scroll to the newest event
        self.analysis_table.scrollToBottom()
    
    def add_test_analysis(self):
        """Add a test AI analysis entry for demo purposes"""
        from datetime import datetime
        import random
        
        # Generate random test data
        token_names = ["SOL", "BONK", "JUP", "PYTH", "RNDR", "JTO", "WIF"]
        actions = ["BUY", "SELL", "NOTHING"]
        analyses = [
            "Strong bullish momentum with price above MA20/MA40",
            "Bearish trend with significant volume decrease",
            "Neutral pattern, waiting for clear direction",
            "Bullish convergence with increasing volume profile",
            "Price breaking key resistance level with volume support",
            "Declining momentum with bearish divergence signals"
        ]
        confidence_levels = [65, 70, 75, 80, 85, 90, 95]
        prices = ["$0.25", "$1.20", "$0.50", "$3.75", "$10.25", "$0.002", "$0.15"]
        
        # Generate a random change percentage between -15% and +15%
        change_percent = round(random.uniform(-15, 15), 2)
        
        # Randomly select data
        token = random.choice(token_names)
        action = random.choice(actions)
        analysis = random.choice(analyses)
        confidence = str(random.choice(confidence_levels))
        price = random.choice(prices)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Use the add_ai_analysis method to add the entry
        self.add_ai_analysis(
            timestamp,
            action,
            token,
            token,  # Using token as symbol for simplicity
            analysis,
            confidence,
            price,
            str(change_percent),
            "Example" + str(random.randint(1000, 9999))  # Sample token mint
        )

    # Add this method to the TrackerTab class
    def add_test_change(self):
        """Add test change events for demo purposes"""
        from datetime import datetime
        import random
        
        # Generate random test data
        wallet_addresses = [
            "8Lj3GFJyDjN5ykGKZbGnVWWQrjEX5WzWiLofJcjN5LJM",
            "D3xQHXADvRaG4nQM9zKrHZFJZQrfMoKFVJARRGHkHZqN",
            "6Cbe8SHiiKtvVm1VEpPezRZtdFMrJFQNDm9EuHEAzKF2",
            "2kxXAXzQCJwMuNBJaHF8gWYBoP3UhC2PYhuvStJYXaLW"
        ]
        token_mints = [
            "So11111111111111111111111111111111111111112",  # SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "7i5KKsX2weiTkry7jA4ZwSuXGhs5eJBEjY8vVxR4pfRx",  # BONK
            "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",  # JUP
            "RLYv2ubRMDLcGG2UyvPmnPmkfuQTsMbg4Jtygc7dmnq"   # RAY
        ]
        token_names = ["SOL", "USDC", "BONK", "JUP", "RAY"]
        event_types = ["NEW", "REMOVED", "MODIFIED"]
        
        # Generate a timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a few random change events
        for _ in range(3):
            event_type = random.choice(event_types)
            wallet = random.choice(wallet_addresses)
            token_index = random.randint(0, len(token_mints) - 1)
            token = token_mints[token_index]
            token_name = token_names[token_index]
            
            amount = random.randint(1000, 1000000) / 100.0
            
            if event_type == "MODIFIED":
                # For modified events, provide change and percent change
                change = random.randint(-500000, 500000) / 100.0
                percent_change = round((change / amount) * 100 if amount != 0 else 0, 2)
                
                self.add_change_event(
                    timestamp=timestamp,
                    event_type=event_type,
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_name,
                    token_mint=token,
                    amount=amount,
                    change=change,
                    percent_change=percent_change,
                    token_name=token_name
                )
            else:
                # For new or removed, don't provide change values
                self.add_change_event(
                    timestamp=timestamp,
                    event_type=event_type,
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_name,
                    token_mint=token,
                    amount=amount,
                    token_name=token_name
                )

class ChartsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # Set up timer for auto-refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_charts)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
    def setup_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        
        # Top control bar
        control_bar = QHBoxLayout()
        
        # Refresh button
        refresh_btn = NeonButton("Refresh", CyberpunkColors.PRIMARY)
        refresh_btn.clicked.connect(self.refresh_charts)
        control_bar.addWidget(refresh_btn)
        
        # Add control bar to main layout
        layout.addLayout(control_bar)
        
        # Create scroll area for charts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container widget for charts
        self.charts_container = QWidget()
        self.charts_layout = QVBoxLayout(self.charts_container)
        
        scroll.setWidget(self.charts_container)
        layout.addWidget(scroll)
        
        # Initial load
        self.refresh_charts()
        
    def refresh_charts(self):
        """Refresh all charts and analysis data"""
        # Clear existing charts
        for i in reversed(range(self.charts_layout.count())): 
            item = self.charts_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
            elif item:
                # Handle spacers or other layout items
                self.charts_layout.removeItem(item)
            
        # Get all CSV files
        charts_dir = Path("src/data/charts")
        csv_files = list(charts_dir.glob("chart_analysis_*.csv"))
        
        for csv_file in csv_files:
            try:
                # Read analysis data
                df = pd.read_csv(csv_file)
                if df.empty:
                    continue
                    
                # Get latest analysis
                latest = df.iloc[-1]
                symbol = latest['symbol']
                
                # Create frame for this symbol
                frame = NeonFrame(color=CyberpunkColors.PRIMARY)
                frame_layout = QVBoxLayout(frame)
                
                # Header with symbol
                header = QLabel(f"📊 {symbol} Analysis")
                header.setStyleSheet(f"color: {CyberpunkColors.TEXT_WHITE}; font-size: 16px; font-weight: bold;")
                frame_layout.addWidget(header)
                
                # Find matching chart image
                chart_files = list(charts_dir.glob(f"{symbol}_*.png"))
                if chart_files:
                    latest_chart = max(chart_files, key=lambda x: x.stat().st_mtime)
                    
                    # Display chart
                    chart_label = QLabel()
                    pixmap = QPixmap(str(latest_chart))
                    scaled_pixmap = pixmap.scaled(800, 400, Qt.AspectRatioMode.KeepAspectRatio)
                    chart_label.setPixmap(scaled_pixmap)
                    frame_layout.addWidget(chart_label)
                
                # Analysis details
                details = QLabel(
                    f"Timeframe: {latest['timeframe']}\n"
                    f"Signal: {latest['signal']}\n"
                    f"Confidence: {latest['confidence']}%\n"
                    f"Reasoning: {latest['reasoning']}\n"
                    f"Last Updated: {datetime.fromtimestamp(latest['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
                )
                details.setStyleSheet(f"color: {CyberpunkColors.TEXT_LIGHT}; font-size: 14px;")
                frame_layout.addWidget(details)
                
                # Add to main layout
                self.charts_layout.addWidget(frame)
                
            except Exception as e:
                print(f"Error loading chart data for {csv_file}: {str(e)}")
                
        # Add stretch to bottom
        self.charts_layout.addStretch()

class OrdersTab(QWidget):
    """Widget for displaying all agent execution orders"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Just add this one line to set the background color
        self.setStyleSheet(f"background-color: {CyberpunkColors.BACKGROUND};")
        self.setup_ui()
        
    def setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: none;
            }}
        """)
        
        # Container widget for the scroll area
        container = QWidget()
        container_layout = QVBoxLayout(container)
        
        # Orders table
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(7)
        self.orders_table.setHorizontalHeaderLabels([
            "Timestamp", "Agent", "Action", "Token", "Amount", "Price", "Status"
        ])
        
        # Style the table
        self.orders_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                gridline-color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
                padding: 4px;
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {CyberpunkColors.PRIMARY};
            }}
            /* Fix for the white row number column */
            QTableView QTableCornerButton::section {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
            QTableWidget QHeaderView::section:vertical {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
            }}
        """)
        
        # Set column widths
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.orders_table.setMinimumHeight(400)
        
        # Add filter controls
        filter_layout = QHBoxLayout()
        filter_widget = QWidget()
        filter_widget.setLayout(filter_layout)
        filter_widget.setStyleSheet(f"""
            background-color: {CyberpunkColors.BACKGROUND};
            margin: 0px;
            padding: 0px;
        """)
        
        # Agent filter dropdown
        self.agent_filter = QComboBox()
        self.agent_filter.addItems(["All Agents", "CopyBot", "DCA", "Risk"])
        self.agent_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                padding: 5px;
            }}
        """)
        self.agent_filter.currentTextChanged.connect(self.apply_filters)
        
        # Action filter dropdown
        self.action_filter = QComboBox()
        self.action_filter.addItems(["All Actions", "BUY", "SELL", "STAKE", "CLOSE"])
        self.action_filter.setStyleSheet(self.agent_filter.styleSheet())
        self.action_filter.currentTextChanged.connect(self.apply_filters)
        
        # Status filter dropdown
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Statuses", "Executed", "Paper"])
        self.status_filter.setStyleSheet(self.agent_filter.styleSheet())
        self.status_filter.currentTextChanged.connect(self.apply_filters)
        
        # Clear filters button
        clear_filters_btn = NeonButton("Clear Filters", CyberpunkColors.WARNING)
        clear_filters_btn.clicked.connect(self.clear_filters)
        
        # Add filter controls to layout
        filter_layout.addWidget(QLabel("Agent:"))
        filter_layout.addWidget(self.agent_filter)
        filter_layout.addWidget(QLabel("Action:"))
        filter_layout.addWidget(self.action_filter)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addWidget(clear_filters_btn)
        filter_layout.addStretch()
        
        # Add everything to the container layout
        container_layout.addWidget(filter_widget)  # Add the filter widget
        container_layout.addWidget(self.orders_table)
        
        # Add clear orders button
        clear_orders_btn = NeonButton("Clear Orders", CyberpunkColors.DANGER)
        clear_orders_btn.clicked.connect(self.clear_orders)
        container_layout.addWidget(clear_orders_btn)
        
        # Set the container as the scroll area's widget
        scroll_area.setWidget(container)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
    def add_order(self, agent, action, token, amount, price, status="Executed"):
        """Add a new order to the table"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_position = self.orders_table.rowCount()
        self.orders_table.insertRow(row_position)
        
        # Set row items
        items = [
            QTableWidgetItem(timestamp),
            QTableWidgetItem(agent),
            QTableWidgetItem(action),
            QTableWidgetItem(token),
            QTableWidgetItem(str(amount)),
            QTableWidgetItem(f"${price:.4f}" if price else "N/A"),
            QTableWidgetItem(status)
        ]
        
        # Set color based on action and paper trading status
        is_paper = status == "Paper"
        
        # Choose color based on action and paper trading status
        if is_paper:
            color = CyberpunkColors.SECONDARY  # Distinct color for paper trades
        else:
            color = CyberpunkColors.SUCCESS if action == "BUY" else \
                    CyberpunkColors.DANGER if action == "SELL" else \
                    CyberpunkColors.WARNING if action == "CLOSE" else \
                    CyberpunkColors.TERTIARY
        
        for col, item in enumerate(items):
            item.setForeground(QColor(color))
            # Add "[PAPER]" prefix to token name if it's a paper trade
            if is_paper and col == 3:  # Token column
                item.setText(f"[PAPER] {item.text()}")
            self.orders_table.setItem(row_position, col, item)
            
        # Scroll to the new row
        self.orders_table.scrollToBottom()
        
    def apply_filters(self):
        """Apply selected filters to the orders table"""
        agent_filter = self.agent_filter.currentText()
        action_filter = self.action_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        for row in range(self.orders_table.rowCount()):
            agent = self.orders_table.item(row, 1).text()
            action = self.orders_table.item(row, 2).text()
            status = self.orders_table.item(row, 6).text()
            
            show_row = (agent_filter == "All Agents" or agent == agent_filter) and \
                      (action_filter == "All Actions" or action == action_filter) and \
                      (status_filter == "All Statuses" or status == status_filter)
                      
            self.orders_table.setRowHidden(row, not show_row)
            
    def clear_filters(self):
        """Clear all filters"""
        self.agent_filter.setCurrentText("All Agents")
        self.action_filter.setCurrentText("All Actions")
        self.status_filter.setCurrentText("All Statuses")
        
    def clear_orders(self):
        """Clear all orders from the table"""
        self.orders_table.setRowCount(0)

class MetricsTab(QWidget):
    """Pokedex-style wallet metrics and analysis tab"""
    
    def __init__(self):
        super().__init__()
        self.db = WalletMetricsDB()
        self.analyzer = WalletAnalyzer()
        self.setup_ui()
        self.load_wallets()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet("background-color: #000000;")  # Set the entire tab background to black
        
        # Create a scroll area for the content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: #000000;")  # Set scroll area background to black
        
        # Create the main content widget
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content.setStyleSheet("background-color: #000000;")  # Set content background to black
        
        # Wallet Selection
        wallet_group = QGroupBox("Select Wallet")
        wallet_layout = QHBoxLayout(wallet_group)
        wallet_group.setStyleSheet("background-color: #000000; color: #E0E0E0;")  # Set group box background to black
        
        self.wallet_combo = QComboBox()
        self.wallet_combo.setMinimumWidth(300)
        self.wallet_combo.currentIndexChanged.connect(self.on_wallet_selected)
        wallet_layout.addWidget(self.wallet_combo)
        
        # Refresh button
        refresh_btn = NeonButton("Refresh Data", CyberpunkColors.PRIMARY)
        refresh_btn.clicked.connect(self.refresh_metrics)
        wallet_layout.addWidget(refresh_btn)
        
        content_layout.addWidget(wallet_group)
        
        # Main metrics display (Pokedex style)
        metrics_group = QGroupBox("Wallet Metrics")
        metrics_layout = QGridLayout(metrics_group)
        metrics_group.setStyleSheet("background-color: #000000; color: #E0E0E0;")  # Set group box background to black
        
        # Performance Stats
        self.win_loss_label = QLabel("Win/Loss Ratio: --")
        self.roi_label = QLabel("ROI: --")
        self.avg_hold_label = QLabel("Avg Hold Time: --")
        self.total_trades_label = QLabel("Total Trades: --")
        
        metrics_layout.addWidget(self.win_loss_label, 0, 0)
        metrics_layout.addWidget(self.roi_label, 0, 1)
        metrics_layout.addWidget(self.avg_hold_label, 1, 0)
        metrics_layout.addWidget(self.total_trades_label, 1, 1)
        
        content_layout.addWidget(metrics_group)
        
        # AI Analysis Section
        ai_group = QGroupBox("AI Analysis")
        ai_layout = QVBoxLayout(ai_group)
        ai_group.setStyleSheet("background-color: #000000; color: #E0E0E0;")  # Set group box background to black
        
        self.wallet_score = QLabel("Wallet Score: --")
        self.wallet_score.setStyleSheet(f"""
            font-size: 24px;
            color: {CyberpunkColors.PRIMARY};
            font-weight: bold;
        """)
        
        self.ai_analysis = QTextEdit()
        self.ai_analysis.setReadOnly(True)
        self.ai_analysis.setMinimumHeight(100)
        self.ai_analysis.setStyleSheet("background-color: #000000; color: #E0E0E0;")  # Set text edit background to black
        
        ai_layout.addWidget(self.wallet_score)
        ai_layout.addWidget(self.ai_analysis)
        
        content_layout.addWidget(ai_group)
        
        # Token Preferences
        token_group = QGroupBox("Token Preferences")
        token_layout = QVBoxLayout(token_group)
        token_group.setStyleSheet("background-color: #000000; color: #E0E0E0;")  # Set group box background to black
        
        self.token_table = QTableWidget()
        self.token_table.setColumnCount(3)
        self.token_table.setHorizontalHeaderLabels(["Token", "Trade Count", "Avg Position Size"])
        self.token_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.token_table.setStyleSheet("background-color: #000000; color: #000000;")  # Set table background to black
        
        token_layout.addWidget(self.token_table)
        content_layout.addWidget(token_group)
        
        # Entry/Exit Timing
        timing_group = QGroupBox("Entry/Exit Timing")
        timing_layout = QVBoxLayout(timing_group)
        timing_group.setStyleSheet("background-color: #000000; color: #E0E0E0;")  # Set group box background to black
        
        self.timing_chart = QWidget()  # Placeholder for the timing visualization
        timing_layout.addWidget(self.timing_chart)
        
        content_layout.addWidget(timing_group)
        
        # Position Size Analysis
        position_group = QGroupBox("Position Size Analysis")
        position_layout = QVBoxLayout(position_group)
        position_group.setStyleSheet("background-color: #000000; color: #E0E0E0;")  # Set group box background to black
        
        self.position_chart = QWidget()  # Placeholder for the position size visualization
        position_layout.addWidget(self.position_chart)
        
        content_layout.addWidget(position_group)
        
        # Add the content to the scroll area
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
    def load_wallets(self):
        """Load tracked wallets into the combo box"""
        self.wallet_combo.clear()
        wallets = self.db.get_all_wallets()
        self.wallet_combo.addItems(wallets)
        
    def on_wallet_selected(self, index):
        """Handle wallet selection change"""
        wallet = self.wallet_combo.currentText()
        if wallet:
            self.refresh_metrics()
            
    def refresh_metrics(self):
        """Refresh all metrics for the selected wallet"""
        wallet = self.wallet_combo.currentText()
        if not wallet:
            return
            
        # Get metrics from database
        metrics = self.db.get_wallet_metrics(wallet)
        if not metrics:
            return
            
        # Update performance stats
        self.win_loss_label.setText(f"Win/Loss Ratio: {metrics['win_loss_ratio']:.2f}")
        self.roi_label.setText(f"ROI: {metrics['roi']:.2f}%")
        self.avg_hold_label.setText(f"Avg Hold Time: {metrics['avg_hold_time']} hours")
        self.total_trades_label.setText(f"Total Trades: {metrics['total_trades']}")
        
        # Run AI analysis
        analysis = self.analyzer.analyze_wallet(metrics)
        
        # Update AI analysis
        self.wallet_score.setText(f"Wallet Score: {analysis['ai_score']:.1f}/10")
        self.ai_analysis.setText(analysis['ai_analysis'])
        
        # Update token preferences table
        self.token_table.setRowCount(len(metrics['token_preferences']))
        for i, token in enumerate(metrics['token_preferences']):
            self.token_table.setItem(i, 0, QTableWidgetItem(token['address'][:8] + '...'))
            self.token_table.setItem(i, 1, QTableWidgetItem(str(token['trade_count'])))
            self.token_table.setItem(i, 2, QTableWidgetItem(f"${token['avg_position_size']:.2f}"))
            
        # TODO: Update timing and position charts when implemented

class RiskManagementTab(QWidget):
    """Tab for configuring risk management settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        # Main layout
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
        
        # AI Prompt Section
        ai_group = QGroupBox("AI Prompt")
        ai_layout = QVBoxLayout(ai_group)
        
        # AI Prompt
        self.prompt_text = QTextEdit()
        prompt_text = """
You are Moon Dev's Risk Management Agent 🌙

Your task is to analyze the positions and determine if any should be closed based on the risk management parameters.

Data provided:
1. Current positions and their performance (profit/loss)
2. Risk management parameters (max loss, max gain, etc.)
3. Market data for each position

Analysis Criteria:
1. Has the position hit max loss threshold?
2. Has the position hit max gain threshold?
3. Is the position showing weakness/strength?
4. What is the overall market condition?

{position_data}
{market_data}
{risk_parameters}

Respond in this exact format:
1. First line must be one of: CLOSE, HOLD, or URGENT (in caps)
2. Then explain your reasoning, including:
   - Position performance analysis
   - Risk assessment
   - Market conditions
   - Risk management rule violations
   - Confidence level (as a percentage, e.g. 75%)

Remember: 
- Always prioritize risk management over potential gains
- Be conservative in volatile markets
- Consider both absolute and percentage-based thresholds
- Provide clear, actionable advice
"""
        self.prompt_text.setPlainText(prompt_text)
        self.prompt_text.setMinimumHeight(200)
        ai_layout.addWidget(self.prompt_text)
        
        scroll_layout.addWidget(ai_group)
        
        # 2. Risk Management Parameters
        risk_group = QGroupBox("Risk Management Parameters")
        risk_group.setObjectName("risk_group")
        risk_layout = QGridLayout(risk_group)
        
        # Cash Reserve %
        risk_layout.addWidget(QLabel("Cash Reserve %:"), 0, 0)
        self.cash_percentage = QSpinBox()
        self.cash_percentage.setRange(0, 100)
        self.cash_percentage.setValue(20)  # CASH_PERCENTAGE = 20
        self.cash_percentage.setToolTip("Minimum % to keep in USDC as safety buffer (0-100)")
        risk_layout.addWidget(self.cash_percentage, 0, 1)
        
        # Max Position %
        risk_layout.addWidget(QLabel("Max Position %:"), 1, 0)
        self.max_position_percentage = QSpinBox()
        self.max_position_percentage.setRange(1, 100)
        self.max_position_percentage.setValue(10)  # MAX_POSITION_PERCENTAGE = 10
        self.max_position_percentage.setToolTip("Maximum % allocation per position (0-100)")
        risk_layout.addWidget(self.max_position_percentage, 1, 1)
        
        # Minimum Balance USD
        risk_layout.addWidget(QLabel("Minimum Balance (USD):"), 2, 0)
        self.min_balance_usd = QDoubleSpinBox()
        self.min_balance_usd.setRange(0, 10000)
        self.min_balance_usd.setValue(100)  # MINIMUM_BALANCE_USD = 100
        self.min_balance_usd.setDecimals(2)
        self.min_balance_usd.setToolTip("If balance falls below this, risk agent will consider closing all positions")
        risk_layout.addWidget(self.min_balance_usd, 2, 1)
        
        # Use percentage based limits
        risk_layout.addWidget(QLabel("Use Percentage Based Limits:"), 3, 0)
        self.use_percentage = QCheckBox()
        self.use_percentage.setChecked(True)  # USE_PERCENTAGE = True
        self.use_percentage.stateChanged.connect(self.toggle_limit_inputs)
        self.use_percentage.setToolTip("If True, use percentage-based limits. If False, use USD-based limits")
        risk_layout.addWidget(self.use_percentage, 3, 1)
        
        # Max Loss (%)
        risk_layout.addWidget(QLabel("Max Loss (%):"), 4, 0)
        self.max_loss_pct = QSpinBox()
        self.max_loss_pct.setRange(1, 100)
        self.max_loss_pct.setValue(20)  # MAX_LOSS_PERCENT = 20
        self.max_loss_pct.setToolTip("Maximum loss as percentage (e.g., 20 = 20% loss)")
        risk_layout.addWidget(self.max_loss_pct, 4, 1)
        
        # Max Gain (%)
        risk_layout.addWidget(QLabel("Max Gain (%):"), 5, 0)
        self.max_gain_pct = QSpinBox()
        self.max_gain_pct.setRange(1, 1000)
        self.max_gain_pct.setValue(200)  # MAX_GAIN_PERCENT = 200
        self.max_gain_pct.setToolTip("Maximum gain as percentage (e.g., 200 = 200% gain)")
        risk_layout.addWidget(self.max_gain_pct, 5, 1)
        
        # Max Loss (USD)
        risk_layout.addWidget(QLabel("Max Loss (USD):"), 6, 0)
        self.max_loss_usd = QDoubleSpinBox()
        self.max_loss_usd.setRange(0, 10000)
        self.max_loss_usd.setValue(25)  # MAX_LOSS_USD = 25
        self.max_loss_usd.setDecimals(2)
        self.max_loss_usd.setToolTip("Maximum loss in USD before stopping trading")
        risk_layout.addWidget(self.max_loss_usd, 6, 1)
        
        # Max Gain (USD)
        risk_layout.addWidget(QLabel("Max Gain (USD):"), 7, 0)
        self.max_gain_usd = QDoubleSpinBox()
        self.max_gain_usd.setRange(0, 10000)
        self.max_gain_usd.setValue(25)  # MAX_GAIN_USD = 25
        self.max_gain_usd.setDecimals(2)
        self.max_gain_usd.setToolTip("Maximum gain in USD before stopping trading")
        risk_layout.addWidget(self.max_gain_usd, 7, 1)
        
        # Max Loss/Gain Check Hours
        risk_layout.addWidget(QLabel("Max Loss/Gain Check Hours:"), 8, 0)
        self.max_loss_gain_check_hours = QSpinBox()
        self.max_loss_gain_check_hours.setRange(1, 168)  # Up to 7 days
        self.max_loss_gain_check_hours.setValue(24)  # MAX_LOSS_GAIN_CHECK_HOURS = 24
        self.max_loss_gain_check_hours.setToolTip("How far back to check for max loss/gain limits (in hours)")
        risk_layout.addWidget(self.max_loss_gain_check_hours, 8, 1)
        
        # Sleep After Close
        risk_layout.addWidget(QLabel("Sleep After Close (seconds):"), 9, 0)
        self.sleep_after_close = QSpinBox()
        self.sleep_after_close.setRange(1, 3600)  # Up to 1 hour
        self.sleep_after_close.setValue(900)  # SLEEP_AFTER_CLOSE = 900
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
        self.usd_size.setValue(25)  # usd_size = 25
        self.usd_size.setDecimals(2)
        self.usd_size.setToolTip("Size of position to hold (account_balance * 0.085 or 0.12)")
        position_layout.addWidget(self.usd_size, 0, 1)
        
        # Max Order Size (USD)
        position_layout.addWidget(QLabel("Max Order Size (USD):"), 1, 0)
        self.max_usd_order_size = QDoubleSpinBox()
        self.max_usd_order_size.setRange(1, 1000)
        self.max_usd_order_size.setValue(3)  # max_usd_order_size = 3
        self.max_usd_order_size.setDecimals(2)
        self.max_usd_order_size.setToolTip("Maximum order size for individual trades")
        position_layout.addWidget(self.max_usd_order_size, 1, 1)
        
        # Transaction Sleep
        position_layout.addWidget(QLabel("Transaction Sleep (seconds):"), 2, 0)
        self.tx_sleep = QDoubleSpinBox()
        self.tx_sleep.setRange(0.1, 60)
        self.tx_sleep.setValue(15)  # tx_sleep = 15
        self.tx_sleep.setDecimals(1)
        self.tx_sleep.setToolTip("Sleep time between transactions")
        position_layout.addWidget(self.tx_sleep, 2, 1)
        
        # Slippage
        position_layout.addWidget(QLabel("Slippage:"), 3, 0)
        self.slippage = QSpinBox()
        self.slippage.setRange(1, 500)
        self.slippage.setValue(199)  # slippage = 199
        self.slippage.setToolTip("Slippage in basis points (500 = 5% and 50 = .5% slippage)")
        position_layout.addWidget(self.slippage, 3, 1)
        
        # Priority Fee
        position_layout.addWidget(QLabel("Priority Fee (microLamports):"), 4, 0)
        self.priority_fee = QSpinBox()
        self.priority_fee.setRange(1, 1000000)
        self.priority_fee.setValue(100000)  # PRIORITY_FEE = 100000
        self.priority_fee.setToolTip("~0.02 USD at current SOL prices")
        position_layout.addWidget(self.priority_fee, 4, 1)
        
        # Orders Per Open
        position_layout.addWidget(QLabel("Orders Per Open:"), 5, 0)
        self.orders_per_open = QSpinBox()
        self.orders_per_open.setRange(1, 10)
        self.orders_per_open.setValue(3)  # orders_per_open = 3
        self.orders_per_open.setToolTip("Multiple orders for better fill rates")
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

        # Paper Trading Enabled
        paper_layout.addWidget(QLabel("Paper Trading Enabled:"), 0, 0)
        self.paper_trading_enabled = QCheckBox()
        self.paper_trading_enabled.setChecked(False)  # PAPER_TRADING_ENABLED = False
        self.paper_trading_enabled.setToolTip("Enable paper trading mode")
        paper_layout.addWidget(self.paper_trading_enabled, 0, 1)

        # Initial Paper Balance
        paper_layout.addWidget(QLabel("Initial Paper Balance (USD):"), 1, 0)
        self.paper_initial_balance = QDoubleSpinBox()
        self.paper_initial_balance.setRange(1, 1000000)
        self.paper_initial_balance.setValue(1000)  # PAPER_INITIAL_BALANCE = 1000
        self.paper_initial_balance.setDecimals(2)
        self.paper_initial_balance.setToolTip("Initial paper trading balance in USD")
        paper_layout.addWidget(self.paper_initial_balance, 1, 1)

        # Paper Trading Slippage
        paper_layout.addWidget(QLabel("Paper Trading Slippage (%):"), 2, 0)
        self.paper_trading_slippage = QSpinBox()
        self.paper_trading_slippage.setRange(1, 1000)
        self.paper_trading_slippage.setValue(100)  # PAPER_TRADING_SLIPPAGE = 100
        self.paper_trading_slippage.setToolTip("Simulated slippage for paper trades (100 = 1%)")
        paper_layout.addWidget(self.paper_trading_slippage, 2, 1)

        # Paper Trading Reset on Start
        paper_layout.addWidget(QLabel("Reset Paper Portfolio on Start:"), 3, 0)
        self.paper_trading_reset_on_start = QCheckBox()
        self.paper_trading_reset_on_start.setChecked(False)  # PAPER_TRADING_RESET_ON_START = False
        self.paper_trading_reset_on_start.setToolTip("Reset paper trading portfolio on app start")
        paper_layout.addWidget(self.paper_trading_reset_on_start, 3, 1)

        scroll_layout.addWidget(paper_group)
        
        # Add save button
        save_button = NeonButton("Save Risk Configuration", CyberpunkColors.TERTIARY)
        save_button.clicked.connect(self.save_config)
        scroll_layout.addWidget(save_button)
        
        # Create scroll area
        scroll_area = QScrollArea()
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
            
            # Update config.py with risk settings
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'config.py')
            
            # Read existing config file
            with open(config_path, 'r') as f:
                config_content = f.read()
            
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
            config_content = self.update_config_value(config_content, "PRIORITY_FEE", str(self.priority_fee.value()))
            config_content = self.update_config_value(config_content, "orders_per_open", str(self.orders_per_open.value()))
            
            # Update data collection settings
            config_content = self.update_config_value(config_content, "DAYSBACK_4_DATA", str(self.days_back.value()))
            config_content = self.update_config_value(config_content, "DATA_TIMEFRAME", f"'{self.data_timeframe.currentText()}'")
            
            # Update paper trading settings
            config_content = self.update_config_value(config_content, "PAPER_TRADING_ENABLED", str(self.paper_trading_enabled.isChecked()))
            config_content = self.update_config_value(config_content, "PAPER_INITIAL_BALANCE", str(self.paper_initial_balance.value()))
            config_content = self.update_config_value(config_content, "PAPER_TRADING_SLIPPAGE", str(self.paper_trading_slippage.value()))
            config_content = self.update_config_value(config_content, "PAPER_TRADING_RESET_ON_START", str(self.paper_trading_reset_on_start.isChecked()))
            
            # Write updated config back to file
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Force reload config module
            import sys
            import importlib
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from src import config
            importlib.reload(config)
            
            # Update UI components with new settings
            if hasattr(self.parent().parent(), 'portfolio_viz'):
                try:
                    self.parent().parent().portfolio_viz.set_paper_trading_mode(config.PAPER_TRADING_ENABLED)
                except Exception as e:
                    print(f"Error updating portfolio viz: {e}")
            
            # Update risk agent prompt if it has changed
            try:
                risk_agent_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'agents', 'risk_agent.py')
                with open(risk_agent_path, 'r') as f:
                    risk_agent_content = f.read()
                    
                # Create prompt text with proper escaping
                prompt_text = self.prompt_text.toPlainText()
                
                # Update the RISK_OVERRIDE_PROMPT in risk_agent.py
                import re
                updated_content = re.sub(r'RISK_OVERRIDE_PROMPT\s*=\s*""".*?"""', f'RISK_OVERRIDE_PROMPT = """\n{prompt_text}\n"""', risk_agent_content, flags=re.DOTALL)
                
                with open(risk_agent_path, 'w') as f:
                    f.write(updated_content)
            except Exception as e:
                print(f"Warning: Couldn't update risk agent prompt: {e}")
                QMessageBox.warning(self, "Warning", f"Could not update risk agent prompt: {str(e)}")
            
            # If paper trading setting has changed, restart all active agents
            if paper_trading_changed:
                main_window = self.parent().parent()
                if main_window and hasattr(main_window, 'agent_threads'):
                    # Get list of currently running agents
                    running_agents = []
                    for agent_name, thread in main_window.agent_threads.items():
                        if thread and thread.isRunning():
                            running_agents.append(agent_name)
                    
                    # Stop all running agents
                    for agent_name in running_agents:
                        main_window.console.append_message(f"Stopping {agent_name} to apply paper trading change...", "system")
                        main_window.stop_agent(agent_name)
                    
                    # Allow time for threads to completely stop
                    import time
                    time.sleep(2)
                    
                    # Delete __pycache__ folders to ensure fresh module loading
                    try:
                        import shutil
                        src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        pycache_paths = [
                            os.path.join(src_path, 'src', '__pycache__'),
                            os.path.join(src_path, 'src', 'agents', '__pycache__')
                        ]
                        for path in pycache_paths:
                            if os.path.exists(path):
                                shutil.rmtree(path)
                                print(f"Cleared Python cache at {path}")
                    except Exception as e:
                        print(f"Warning: Could not clear Python cache: {e}")
                    
                    # Restart the agents that were running
                    for agent_name in running_agents:
                        main_window.console.append_message(f"Restarting {agent_name} with new paper trading setting...", "system")
                        main_window.start_agent(agent_name)
                    
                    # Additional message to confirm the change
                    paper_mode = "ENABLED" if self.paper_trading_enabled.isChecked() else "DISABLED"
                    main_window.console.append_message(f"Paper trading mode {paper_mode} - all agents restarted.", "success")
                    
                    # Show dialog confirming restart
                    QMessageBox.information(self, "Agents Restarted", 
                        f"Paper trading mode has been {paper_mode.lower()} and all running agents have been restarted.")
                else:
                    # Show confirmation dialog if we couldn't restart agents
                    paper_mode = "enabled" if self.paper_trading_enabled.isChecked() else "disabled"
                    QMessageBox.information(self, "Configuration Saved", 
                        f"Risk Management configuration has been saved. Paper trading is now {paper_mode}.\n\n"
                        "Please restart all agents manually to apply the new paper trading setting.")
            else:
                # Show standard confirmation dialog if paper trading didn't change
                QMessageBox.information(self, "Configuration Saved", 
                    "Risk Management configuration has been saved successfully.\n\n"
                    "To apply these changes, restart the Risk Management agent.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")

# Add AIConfigTab after RiskManagementTab class
class AIConfigTab(QWidget):
    """Tab for configuring AI models and settings across all agents"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.global_model_combo.setCurrentText("claude-3-haiku-20240307")  # From config.py
        model_layout.addWidget(self.global_model_combo)
        global_layout.addLayout(model_layout)
        
        # Temperature setting
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Default Temperature:"))
        self.global_temp_slider = QSlider(Qt.Horizontal)
        self.global_temp_slider.setRange(0, 100)
        self.global_temp_slider.setValue(70)  # Default 0.7 from config.py
        self.global_temp_slider.setTickPosition(QSlider.TicksBelow)
        self.global_temp_slider.setTickInterval(10)
        self.global_temp_label = QLabel("0.7")
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
        self.global_tokens_spin.setValue(1024)  # From config.py
        self.global_tokens_spin.setSingleStep(100)
        tokens_layout.addWidget(self.global_tokens_spin)
        global_layout.addLayout(tokens_layout)
        
        scroll_layout.addWidget(global_group)
        
        # 2. CopyBot Agent Settings
        copybot_group = QGroupBox("CopyBot Agent AI Settings")
        copybot_layout = QVBoxLayout(copybot_group)
        
        # Enable/Disable AI for CopyBot
        self.copybot_ai_enabled = QCheckBox("Enable AI Analysis for CopyBot")
        self.copybot_ai_enabled.setChecked(True)
        copybot_layout.addWidget(self.copybot_ai_enabled)
        
        # Override global settings
        self.copybot_override = QCheckBox("Override Global Settings")
        self.copybot_override.setChecked(True)  # Currently uses MODEL_OVERRIDE
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
        self.copybot_model_combo.setCurrentText("deepseek-reasoner")  # From MODEL_OVERRIDE
        copybot_model_layout.addWidget(self.copybot_model_combo)
        copybot_layout.addLayout(copybot_model_layout)
        
        # Confidence threshold setting
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Analysis Confidence Threshold:"))
        self.copybot_confidence_slider = QSlider(Qt.Horizontal)
        self.copybot_confidence_slider.setRange(0, 100)
        self.copybot_confidence_slider.setValue(80)  # From STRATEGY_MIN_CONFIDENCE
        self.copybot_confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.copybot_confidence_slider.setTickInterval(10)
        self.copybot_confidence_label = QLabel("80%")
        self.copybot_confidence_slider.valueChanged.connect(
            lambda v: self.copybot_confidence_label.setText(f"{v}%")
        )
        confidence_layout.addWidget(self.copybot_confidence_slider)
        confidence_layout.addWidget(self.copybot_confidence_label)
        copybot_layout.addLayout(confidence_layout)
        
        scroll_layout.addWidget(copybot_group)
        
        # 3. Combined Chart Analysis & DCA System Settings
        dca_chart_group = QGroupBox("Chart Analysis & DCA System AI Settings")
        dca_chart_layout = QVBoxLayout(dca_chart_group)
        
        # Enable/disable AI chart analysis recommendations
        self.chart_analysis_enabled = QCheckBox("Enable AI Chart Analysis Recommendations")
        self.chart_analysis_enabled.setChecked(True)  # Default to enabled
        dca_chart_layout.addWidget(self.chart_analysis_enabled)
        
        # Override global settings
        self.chart_override = QCheckBox("Override Global Settings")
        self.chart_override.setChecked(True)  # Currently uses MODEL_OVERRIDE
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
        self.chart_model_combo.setCurrentText("deepseek-reasoner")  # From MODEL_OVERRIDE
        chart_model_layout.addWidget(self.chart_model_combo)
        dca_chart_layout.addLayout(chart_model_layout)
        
        
        # Confidence thresholds for DCA
        buy_confidence_layout = QHBoxLayout()
        buy_confidence_layout.addWidget(QLabel("Buy Signal Confidence Threshold:"))
        self.dca_buy_confidence_slider = QSlider(Qt.Horizontal)
        self.dca_buy_confidence_slider.setRange(0, 100)
        self.dca_buy_confidence_slider.setValue(50)  # From BUY_CONFIDENCE_THRESHOLD
        self.dca_buy_confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.dca_buy_confidence_slider.setTickInterval(10)
        self.dca_buy_confidence_label = QLabel("50%")
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
        self.dca_sell_confidence_slider.setValue(75)  # From SELL_CONFIDENCE_THRESHOLD
        self.dca_sell_confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.dca_sell_confidence_slider.setTickInterval(10)
        self.dca_sell_confidence_label = QLabel("75%")
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
        self.risk_ai_confirmation.setChecked(True)  # From USE_AI_CONFIRMATION
        risk_layout.addWidget(self.risk_ai_confirmation)
        
        # Override global settings
        self.risk_override = QCheckBox("Override Global Settings")
        self.risk_override.setChecked(False)  # Default to using global settings
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
        self.risk_model_combo.setCurrentText("claude-3-haiku-20240307")  # Default to global model
        risk_model_layout.addWidget(self.risk_model_combo)
        risk_layout.addLayout(risk_model_layout)
        
        # Confidence threshold setting for risk agent
        risk_confidence_layout = QHBoxLayout()
        risk_confidence_layout.addWidget(QLabel("Risk Assessment Confidence Threshold:"))
        self.risk_confidence_slider = QSlider(Qt.Horizontal)
        self.risk_confidence_slider.setRange(0, 100)
        self.risk_confidence_slider.setValue(70)  # Default value
        self.risk_confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.risk_confidence_slider.setTickInterval(10)
        self.risk_confidence_label = QLabel("70%")
        self.risk_confidence_slider.valueChanged.connect(
            lambda v: self.risk_confidence_label.setText(f"{v}%")
        )
        risk_confidence_layout.addWidget(self.risk_confidence_slider)
        risk_confidence_layout.addWidget(self.risk_confidence_label)
        risk_layout.addLayout(risk_confidence_layout)
        
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
        """Save AI configuration to config.py and agent files"""
        try:
            # Read existing config.py content
            config_path = os.path.join("src", "config.py")
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # Update the global AI values
            new_values = {
                "AI_MODEL": f'"{self.global_model_combo.currentText()}"',
                "AI_TEMPERATURE": f"{float(self.global_temp_slider.value()) / 100}",
                "AI_MAX_TOKENS": f"{self.global_tokens_spin.value()}",
                "STRATEGY_MIN_CONFIDENCE": f"{float(self.copybot_confidence_slider.value()) / 100}",
                "BUY_CONFIDENCE_THRESHOLD": f"{self.dca_buy_confidence_slider.value()}", 
                "SELL_CONFIDENCE_THRESHOLD": f"{self.dca_sell_confidence_slider.value()}",
                "USE_AI_CONFIRMATION": f"{self.risk_ai_confirmation.isChecked()}",
                "ENABLE_CHART_ANALYSIS": f"{self.chart_analysis_enabled.isChecked()}",
                "RISK_CONFIDENCE_THRESHOLD": f"{self.risk_confidence_slider.value()}"
            }
            
            # Save updated config.py
            lines = config_content.split('\n')
            updated_lines = []
            for line in lines:
                updated = False
                for key, value in new_values.items():
                    if line.strip().startswith(f"{key} ="):
                        updated_lines.append(f"{key} = {value}")
                        updated = True
                        break
                if not updated:
                    updated_lines.append(line)
            
            with open(config_path, 'w') as f:
                f.write('\n'.join(updated_lines))
            
            # Update MODEL_OVERRIDE in agent files if needed
            if self.copybot_override.isChecked():
                self.update_agent_model_override(
                    "src/agents/copybot_agent.py", 
                    self.copybot_model_combo.currentText()
                )
            
            if self.chart_override.isChecked():
                self.update_agent_model_override(
                    "src/agents/chartanalysis_agent.py", 
                    self.chart_model_combo.currentText()
                )
            
            if self.risk_override.isChecked():
                self.update_agent_model_override(
                    "src/agents/risk_agent.py", 
                    self.risk_model_combo.currentText()
                )
            
            QMessageBox.information(self, "Configuration Saved", "AI configuration saved successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
            
    def update_agent_model_override(self, filepath, model_name):
        """Update MODEL_OVERRIDE in a specific agent file"""
        try:
            if not os.path.exists(filepath):
                return
                
            with open(filepath, 'r') as f:
                content = f.read()
                
            # Different format depending on if it's a string or direct variable
            if "=" in model_name:  # It's a variable like gpt-4
                replacement = f'MODEL_OVERRIDE = "{model_name}"'
            else:
                replacement = f'MODEL_OVERRIDE = "{model_name}"'
                
            # Use regex to find and replace the model override
            import re
            pattern = r'MODEL_OVERRIDE\s*=\s*.+"'
            updated = re.sub(pattern, replacement, content)
            
            with open(filepath, 'w') as f:
                f.write(updated)
                
        except Exception as e:
            print(f"Warning: Could not update model override in {filepath}: {str(e)}")

def main():
    app = QApplication(sys.argv)
    
    # Parse command line arguments
    config_path = None
    src_path = None
    
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:]):
            if arg == "--config" and i+1 < len(sys.argv)-1:
                config_path = sys.argv[i+2]
            elif arg == "--src" and i+1 < len(sys.argv)-1:
                src_path = sys.argv[i+2]
    
    # Try to find config.py and src directory if not specified
    if not config_path or not src_path:
        # Look in current directory
        if os.path.exists("config.py"):
            config_path = os.path.abspath("config.py")
        
        if os.path.exists("src"):
            src_path = os.path.abspath("src")
        
        # Look in parent directory
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not config_path and os.path.exists(os.path.join(parent_dir, "config.py")):
            config_path = os.path.join(parent_dir, "config.py")
        
        if not src_path and os.path.exists(os.path.join(parent_dir, "src")):
            src_path = os.path.join(parent_dir, "src")
    
    # Load fonts if available
    try:
        import matplotlib.font_manager as fm
        # Try to find and load cyberpunk-style fonts
        for font_file in ["Rajdhani-Regular.ttf", "ShareTechMono-Regular.ttf", "Orbitron-Regular.ttf"]:
            try:
                font_path = fm.findfont(font_file)
                if font_path:
                    QFont(font_path).family()
            except:
                pass
    except ImportError:
        pass
    
    window = MainWindow(config_path, src_path)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
