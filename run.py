import sys
import os
import math
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta
import signal
import json
import random
import logging
from functools import partial
import re
import threading
import time
import pandas as pd
import numpy as np
import sqlite3
import gc  # Add garbage collection module
import matplotlib.font_manager as fm

from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QSlider, QComboBox, 
                             QLineEdit, QTextEdit, QProgressBar, QFrame, QGridLayout,
                             QSplitter, QGroupBox, QCheckBox, QSpacerItem, QSizePolicy, QScrollArea,
                             QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout, QDateEdit, QTimeEdit)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSize, QThread, QObject, QRect, QMetaObject, Q_ARG, QDate, QTime 
from PySide6.QtGui import QColor, QFont, QPalette, QLinearGradient, QGradient, QPainter, QPen, QBrush, QPixmap, QIcon, QTextCursor, QAction

# Project imports
from src.scripts.wallet_metrics_db import WalletMetricsDB
from src.scripts.wallet_analyzer import WalletAnalyzer
from src.scripts.token_list_tool import TokenAccountTracker
from src.nice_funcs import token_price
from src.config import (TRADING_MODE, USE_HYPERLIQUID, DEFAULT_LEVERAGE, 
                       MAX_LEVERAGE, LEVERAGE_SAFETY_BUFFER, MIRROR_WITH_LEVERAGE,
                       TOKEN_TO_HL_MAPPING, CASH_PERCENTAGE, MAX_POSITION_PERCENTAGE, 
                       USE_PERCENTAGE, MAX_LOSS_PERCENT, MAX_GAIN_PERCENT, MAX_LOSS_USD, 
                       MAX_GAIN_USD, MINIMUM_BALANCE_USD, USE_AI_CONFIRMATION, 
                       MAX_LOSS_GAIN_CHECK_HOURS, SLEEP_BETWEEN_RUNS_MINUTES,
                       FILTER_MODE, ENABLE_PERCENTAGE_FILTER, PERCENTAGE_THRESHOLD,
                       ENABLE_AMOUNT_FILTER, AMOUNT_THRESHOLD, ENABLE_ACTIVITY_FILTER,
                       ACTIVITY_WINDOW_HOURS, PAPER_TRADING_ENABLED, PAPER_INITIAL_BALANCE,
                       PAPER_TRADING_SLIPPAGE, PAPER_TRADING_RESET_ON_START, DYNAMIC_MODE)


# Import Solana libraries for wallet token functions
try:
    from solana.rpc.api import Client
    from solana.publickey import PublicKey
except ImportError:
    print("WARNING: Solana libraries not installed. Some functionality may be limited.")

# Attempt to import our custom token functions
try:
    from src.nice_funcs import get_wallet_tokens, get_token_balance_usd
except ImportError:
    print("WARNING: Failed to import token functions from src.nice_funcs")

# Suppress Qt warnings
logging.getLogger("PySide6").setLevel(logging.ERROR)

# Filter out specific Qt warnings
os.environ['QT_LOGGING_RULES'] = "*.debug=false;qt.qpa.*=false"

# Define maximum widget size constant (equivalent to QWIDGETSIZE_MAX in Qt)
MAX_WIDGET_SIZE = 16777215


def get_project_root():
    """Get the project root directory path, which is consistent across all code"""
    # The actual path shown in the screenshot is the trading_desktop_app folder
    # Check first if we're already in the trading_desktop_app folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if current dir ends with 'trading_desktop_app'
    if os.path.basename(current_dir) == 'trading_desktop_app':
        return current_dir
    
    # Check if parent dir is 'trading_desktop_app'
    parent_dir = os.path.dirname(current_dir)
    if os.path.basename(parent_dir) == 'trading_desktop_app':
        return parent_dir
    
    # If all else fails, assume we're in a subdirectory of trading_desktop_app
    # This would return something like /c:/Users/Admin/trading_desktop_app
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

import sys
import os
import math
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta
import signal
import json
import random
import logging
from functools import partial
import re
import threading
import time
import pandas as pd
import numpy as np
import sqlite3
import gc  # Add garbage collection module
import matplotlib.font_manager as fm

from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QSlider, QComboBox, 
                             QLineEdit, QTextEdit, QProgressBar, QFrame, QGridLayout,
                             QSplitter, QGroupBox, QCheckBox, QSpacerItem, QSizePolicy, QScrollArea,
                             QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout, QDateEdit, QTimeEdit)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSize, QThread, QObject, QRect, QMetaObject, Q_ARG, QDate, QTime 
from PySide6.QtGui import QColor, QFont, QPalette, QLinearGradient, QGradient, QPainter, QPen, QBrush, QPixmap, QIcon, QTextCursor, QAction

# Project imports
from src.scripts.wallet_metrics_db import WalletMetricsDB
from src.scripts.wallet_analyzer import WalletAnalyzer
from src.scripts.token_list_tool import TokenAccountTracker
from src.nice_funcs import token_price
from src.config import (TRADING_MODE, USE_HYPERLIQUID, DEFAULT_LEVERAGE, 
                       MAX_LEVERAGE, LEVERAGE_SAFETY_BUFFER, MIRROR_WITH_LEVERAGE,
                       TOKEN_TO_HL_MAPPING, CASH_PERCENTAGE, MAX_POSITION_PERCENTAGE, 
                       USE_PERCENTAGE, MAX_LOSS_PERCENT, MAX_GAIN_PERCENT, MAX_LOSS_USD, 
                       MAX_GAIN_USD, MINIMUM_BALANCE_USD, USE_AI_CONFIRMATION, 
                       MAX_LOSS_GAIN_CHECK_HOURS, SLEEP_BETWEEN_RUNS_MINUTES,
                       FILTER_MODE, ENABLE_PERCENTAGE_FILTER, PERCENTAGE_THRESHOLD,
                       ENABLE_AMOUNT_FILTER, AMOUNT_THRESHOLD, ENABLE_ACTIVITY_FILTER,
                       ACTIVITY_WINDOW_HOURS, PAPER_TRADING_ENABLED, PAPER_INITIAL_BALANCE,
                       PAPER_TRADING_SLIPPAGE, PAPER_TRADING_RESET_ON_START, DYNAMIC_MODE)

# Suppress Qt warnings
import logging
logging.getLogger("PySide6").setLevel(logging.ERROR)

# Filter out specific Qt warnings
import os
os.environ['QT_LOGGING_RULES'] = "*.debug=false;qt.qpa.*=false"

# Define maximum widget size constant (equivalent to QWIDGETSIZE_MAX in Qt)
MAX_WIDGET_SIZE = 16777215


def get_project_root():
    """Get the project root directory path, which is consistent across all code"""
    # The actual path shown in the screenshot is the trading_desktop_app folder
    # Check first if we're already in the trading_desktop_app folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if current dir ends with 'trading_desktop_app'
    if os.path.basename(current_dir) == 'trading_desktop_app':
        return current_dir
    
    # Check if parent dir is 'trading_desktop_app'
    parent_dir = os.path.dirname(current_dir)
    if os.path.basename(parent_dir) == 'trading_desktop_app':
        return parent_dir
    
    # If all else fails, assume we're in a subdirectory of trading_desktop_app
    # This would return something like /c:/Users/Admin/trading_desktop_app
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
        
        # Set window properties
        self.setWindowTitle("Anarcho Capital")
        self.resize(1200, 800)
        
        # Set title bar styling ONLY (Windows specific) - doesn't affect other UI elements
        if sys.platform == 'win32':
            try:
                # Use Windows-specific API to set dark mode for title bar only
                from ctypes import windll, c_int, byref, sizeof
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                windll.dwmapi.DwmSetWindowAttribute(
                    int(self.winId()),
                    20,  # DWMWA_USE_IMMERSIVE_DARK_MODE
                    byref(c_int(1)),
                    sizeof(c_int)
                )
                
                # Add blue border at the bottom of the title bar
                title_frame = QFrame(self)
                title_frame.setStyleSheet(f"background-color: {CyberpunkColors.PRIMARY}; border: none;")
                title_frame.setFixedHeight(2)  # 2px height blue line
                
                # Position directly under title bar and above menu bar
                def position_title_border():
                    menu_bar = self.menuBar()
                    menu_pos = menu_bar.pos()
                    # Position the line right above the menu bar
                    title_frame.setGeometry(0, menu_pos.y() - 2, self.width(), 2)
                
                # Call it once to set initial position
                QTimer.singleShot(100, position_title_border)
                
                # Create original resize event handler reference to preserve any existing functionality
                original_resize_event = self.resizeEvent
                
                # Create a new resize event handler
                def custom_resize_event(event):
                    # Reposition the border whenever window is resized
                    position_title_border()
                    
                    # Call original event handler if it exists
                    if original_resize_event:
                        original_resize_event(event)
                
                # Set the custom resize event handler
                self.resizeEvent = custom_resize_event
                
                # Direct approach: add a border to the top of the menu bar
                menu_bar = self.menuBar()
                menu_bar.setStyleSheet(f"""
                    QMenuBar {{
                        background-color: {CyberpunkColors.BACKGROUND};
                        color: {CyberpunkColors.TEXT_LIGHT};
                        border-top: 2px solid {CyberpunkColors.PRIMARY};
                    }}
                    QMenuBar::item {{
                        background-color: {CyberpunkColors.BACKGROUND};
                        color: {CyberpunkColors.TEXT_LIGHT};
                    }}
                    QMenuBar::item:selected {{
                        background-color: {CyberpunkColors.PRIMARY};
                        color: {CyberpunkColors.BACKGROUND};
                    }}
                """)
                # Make sure menu bar is visible
                menu_bar.setVisible(True)
                
                # Add an additional separator line between title bar and menu bar
                separator_line = QFrame(self)
                separator_line.setFrameShape(QFrame.HLine)
                separator_line.setFixedHeight(1)
                separator_line.setStyleSheet(f"background-color: {CyberpunkColors.PRIMARY}; margin: 0;")
                
                # Position it just below the title bar
                def position_separator():
                    menu_pos = menu_bar.pos()
                    separator_line.setGeometry(0, menu_pos.y() - 1, self.width(), 1)
                
                # Set initial position and add resize handler
                QTimer.singleShot(100, position_separator)
                
                # Add handling to existing resize event
                original_resize_handler = self.resizeEvent
                def enhanced_resize_handler(event):
                    position_separator()
                    position_title_border()
                    if original_resize_handler:
                        original_resize_handler(event)
                
                self.resizeEvent = enhanced_resize_handler
                
            except Exception:
                # Silently fail if this doesn't work
                pass
        
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
        title_label = QLabel("CryptoBot Super Agent")
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
        tab_widget.addTab(copybot_tab, "CopyBot Settings")
        
        # Create and add risk management tab
        risk_tab = RiskManagementTab()
        tab_widget.addTab(risk_tab, "Risk Settings")
        
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
    
    def enforce_size_during_agent(self, target_size):
        """Continuously enforce window size during agent operations"""
        current_size = self.size()
        
        # Check if current size is outside acceptable bounds
        if (abs(current_size.width() - target_size.width()) > 50 or 
            abs(current_size.height() - target_size.height()) > 50):
            
            # Re-apply constraints that allow limited manual resizing
            self.setMinimumSize(target_size.width() - 50, target_size.height() - 50)
            self.setMaximumSize(target_size.width() + 50, target_size.height() + 50)
            
            # Restore size if it's way outside bounds
            if (abs(current_size.width() - target_size.width()) > 100 or 
                abs(current_size.height() - target_size.height()) > 100):
                self.resize(target_size)
            
            # Process events to ensure constraints are applied
            QApplication.processEvents()
    
    def stop_agent(self, agent_name):
        """Stop an agent with proper thread destruction and cleanup"""
        # Lock window size during agent stopping
        current_size = self.size()
        
        # Apply constraints that prevent expansion but allow limited manual resizing
        # Allow 50px of resize flexibility in each dimension
        self.setMinimumSize(current_size.width() - 50, current_size.height() - 50)
        self.setMaximumSize(current_size.width() + 50, current_size.height() + 50)
        # Do not use setFixedSize to allow manual resizing
        
        # Process events to ensure constraints are applied immediately
        QApplication.processEvents()
        
        # Set up a temporary timer to maintain size constraints during agent stopping
        timer_attr_name = f"{agent_name}_stop_timer"
        setattr(self, timer_attr_name, QTimer(self))
        timer = getattr(self, timer_attr_name)
        timer.timeout.connect(lambda: self.enforce_size_during_agent(current_size))
        timer.start(100)  # Check every 100ms
        
        # Stop the timer after 5 seconds
        QTimer.singleShot(5000, timer.stop)
        
        # Check if agent is running
        if agent_name not in self.agent_threads or self.agent_threads[agent_name] is None:
            self.console.append_message(f"{agent_name} is not running", "warning")
            return
            
        # Update the UI
        if agent_name in self.agent_cards:
            self.agent_cards[agent_name].stop_agent()
        
        # Signal the worker to stop
        worker = self.agent_threads[agent_name]
        if hasattr(worker, 'running'):
            worker.running = False
            
        # Update menu actions
        if agent_name in self.agent_menu_actions:
            self.agent_menu_actions[agent_name].setText(f"Start {agent_name.replace('_', ' ').title()}")
            self.agent_menu_actions[agent_name].triggered.disconnect()
            self.agent_menu_actions[agent_name].triggered.connect(lambda: self.start_agent(agent_name))
        
        # Wait 500ms, then handle thread cleanup
        QTimer.singleShot(500, lambda: self._cleanup_agent_thread(agent_name))
        
        # Multiple staggered reset calls to ensure constraints are fully released
        # This helps prevent lingering constraint issues
        QTimer.singleShot(5100, lambda: self.reset_size_constraints_complete(f"{agent_name} stop-1"))
        QTimer.singleShot(8000, lambda: self.reset_size_constraints_complete(f"{agent_name} stop-2"))
        QTimer.singleShot(12000, lambda: self.reset_size_constraints_complete(f"{agent_name} stop-3"))
    
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
        
        # Add "Save Configuration" action
        save_config_action = QAction("Save Configuration", self)
        save_config_action.triggered.connect(lambda: self.save_config(self.current_config))
        file_menu.addAction(save_config_action)
        
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
        
        # Create scroll area for all settings
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

class DCAStakingTab(QWidget):
    """Tab for configuring and controlling DCA & Staking Agent with Chart Analysis integration"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configure this widget to allow expansion
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
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
            self.yield_optimization_value.setValue(self.yield_optimization_interval_value_value)
            self.yield_optimization_unit.setCurrentText(self.yield_optimization_interval_unit_value)
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
        # Remove fixed height constraints for the entire tab
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # Increase spacing between elements
        layout.setContentsMargins(10, 10, 10, 10)  # Increase margins for the main layout
        
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
        
        # Define standard width for all controls
        control_width = 635
        field_width = 635
        
        # Create scroll area for all settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setContentsMargins(10, 10, 10, 10)  # Add margins to scroll area
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)  # Increase spacing between groups
        scroll_layout.setContentsMargins(15, 15, 15, 15)  # Add padding inside the scroll area
        
        # 1. AI Prompt Section (from Chart Analysis Agent)
        ai_group = QGroupBox("Chart Analysis AI Prompt")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setContentsMargins(10, 15, 10, 10)  # Add some internal padding
        
        # AI Prompt - Create text editor but don't set text (will be loaded from config)
        self.prompt_text = QTextEdit()
        
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
        staking_ai_layout = QVBoxLayout(staking_ai_group)
        
        # Staking AI Prompt - Create text editor but don't set text (will be loaded from config)
        self.staking_prompt_text = QTextEdit()
        
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
        chart_layout = QGridLayout(chart_group)
        
        # Chart Interval
        chart_layout.addWidget(QLabel("Chart Interval:"), 0, 0)
        chart_interval_widget = QWidget()
        chart_interval_layout = QHBoxLayout(chart_interval_widget)
        chart_interval_layout.setContentsMargins(0, 0, 0, 0)

        self.chart_interval_value = QSpinBox()
        self.chart_interval_value.setRange(1, 30)
        self.chart_interval_value.setValue(2)
        self.chart_interval_value.setToolTip("Number of time units between chart analysis cycles")

        self.chart_interval_unit = QComboBox()
        self.chart_interval_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.chart_interval_unit.addItems(["Hour(s)", "Day(s)", "Week(s)", "Month(s)"])
        self.chart_interval_unit.setCurrentText("Hour(s)")
        self.chart_interval_unit.setToolTip("Time unit for chart analysis interval")

        chart_interval_layout.addWidget(self.chart_interval_value)
        chart_interval_layout.addWidget(self.chart_interval_unit)
        chart_layout.addWidget(chart_interval_widget, 0, 1)

        # Add scheduled time setting for Chart Analysis
        chart_layout.addWidget(QLabel("Run At Time:"), 1, 0)
        chart_time_widget = QWidget()
        chart_time_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        chart_time_layout = QHBoxLayout(chart_time_widget)
        chart_time_layout.setContentsMargins(0, 0, 0, 0)

        self.chart_run_at_enabled = QCheckBox("Enabled")
        self.chart_run_at_enabled.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.chart_run_at_enabled.setChecked(getattr(sys.modules['src.config'], 'CHART_RUN_AT_ENABLED', False))
        self.chart_run_at_enabled.setToolTip("When enabled, chart analysis will run at the specified time")

        self.chart_run_at_time = QTimeEdit()
        self.chart_run_at_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
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
        self.timeframes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.timeframes.addItems(['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M'])
        self.timeframes.setCurrentText('4h')
        self.timeframes.setToolTip("Select the timeframe for chart analysis")
        chart_layout.addWidget(self.timeframes, 2, 1)
        
        # Lookback Bars
        chart_layout.addWidget(QLabel("Lookback Bars:"), 3, 0)
        self.lookback_bars = QSpinBox()
        self.lookback_bars.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lookback_bars.setRange(50, 500)
        self.lookback_bars.setValue(100)
        self.lookback_bars.setToolTip("Number of candles to analyze")
        chart_layout.addWidget(self.lookback_bars, 3, 1)
        
        # Indicators
        chart_layout.addWidget(QLabel("Indicators:"), 4, 0)
        self.indicators = QLineEdit("20EMA,50EMA,100EMA,200SMA,MACD,RSI,ATR")
        self.indicators.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.indicators.setPlaceholderText("available indicators 20EMA,50EMA,100EMA,200SMA,MACD,RSI,ATR")
        self.indicators.setToolTip("Comma-separated list of indicators to display")
        chart_layout.addWidget(self.indicators, 4, 1)
        
        
        # Chart Style
        chart_layout.addWidget(QLabel("Chart Style:"), 5, 0)
        self.chart_style = QComboBox()
        self.chart_style.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.chart_style.addItems(['yahoo', 'tradingview', 'plotly', 'matplotlib'])
        self.chart_style.setCurrentText('yahoo')  # Default from config.py
        self.chart_style.setToolTip("Select the visual style for chart rendering")
        chart_layout.addWidget(self.chart_style, 5, 1)
        
        # Show Volume
        volume_widget = QWidget()
        volume_layout = QHBoxLayout(volume_widget)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        
        self.show_volume = QCheckBox("Show Volume Panel")
        self.show_volume.setChecked(True)  # Default from config.py
        self.show_volume.setToolTip("Display volume information in chart")
        
        volume_layout.addWidget(self.show_volume)
        volume_layout.addStretch()
        
        chart_layout.addWidget(QLabel("Volume Display:"), 6, 0)
        chart_layout.addWidget(volume_widget, 6, 1)
        
        
        # Add Fibonacci retracement settings
        # Enable Fibonacci toggle
        fibonacci_enable_widget = QWidget()
        fibonacci_enable_layout = QHBoxLayout(fibonacci_enable_widget)
        fibonacci_enable_layout.setContentsMargins(0, 0, 0, 0)
        
        self.enable_fibonacci = QCheckBox("Enable Fibonacci")
        self.enable_fibonacci.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.enable_fibonacci.setChecked(True)  # Default from config.py
        self.enable_fibonacci.setToolTip("Use Fibonacci retracement for entry price calculations")
        
        fibonacci_enable_layout.addWidget(self.enable_fibonacci)
        fibonacci_enable_layout.addStretch()
        
        chart_layout.addWidget(QLabel("Fibonacci Retracement:"), 7, 0)
        chart_layout.addWidget(fibonacci_enable_widget, 7, 1)
        
        # Fibonacci Levels
        chart_layout.addWidget(QLabel("Fibonacci Levels:"), 8, 0)
        self.fibonacci_levels = QLineEdit("0.236, 0.382, 0.5, 0.618, 0.786")  # Default from config.py
        self.fibonacci_levels.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.fibonacci_levels.setToolTip("Comma-separated list of Fibonacci retracement levels")
        chart_layout.addWidget(self.fibonacci_levels, 8, 1)
        
        # Fibonacci Lookback Periods
        chart_layout.addWidget(QLabel("Fibonacci Lookback Periods:"), 9, 0)
        self.fibonacci_lookback = QSpinBox()
        self.fibonacci_lookback.setRange(10, 200)
        self.fibonacci_lookback.setValue(60)  # Default from config.py
        self.fibonacci_lookback.setToolTip("Number of candles to look back for finding swing points")
        chart_layout.addWidget(self.fibonacci_lookback, 9, 1)
        
        # Apply fixed width to all widgets in chart section
        for row in range(chart_layout.rowCount()):
            item = chart_layout.itemAtPosition(row, 1)
            if item and item.widget():
                item.widget().setMinimumWidth(control_width)
                item.widget().setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        scroll_layout.addWidget(chart_group)
        
        # 3. DCA Settings
        dca_group = QGroupBox("DCA Settings")
        dca_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        dca_layout = QGridLayout(dca_group)
        
        # Make column 0 (labels) fixed width
        dca_layout.setColumnMinimumWidth(0, 200)
        # Make column 1 (input fields) fixed width
        dca_layout.setColumnMinimumWidth(1, field_width)
        
        # DCA Interval - Replace with time-based options
        dca_layout.addWidget(QLabel("DCA Interval:"), 0, 0)
        interval_widget = QWidget()
        interval_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(0, 0, 0, 0)

        self.dca_interval_value = QSpinBox()
        self.dca_interval_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.dca_interval_value.setRange(1, 30)  # Allow 1-30 units
        self.dca_interval_value.setValue(12)  # Default 12 hours
        self.dca_interval_value.setToolTip("Number of time units between DCA operations")

        self.dca_interval_unit = QComboBox()
        self.dca_interval_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.dca_interval_unit.addItems(["Hour(s)", "Day(s)", "Week(s)", "Month(s)"])
        self.dca_interval_unit.setCurrentText("Hour(s)")  # Default hours
        self.dca_interval_unit.setToolTip("Time unit for DCA interval")

        interval_layout.addWidget(self.dca_interval_value)
        interval_layout.addWidget(self.dca_interval_unit)
        dca_layout.addWidget(interval_widget, 0, 1)

        # Add scheduled time setting for DCA
        dca_layout.addWidget(QLabel("Run At Time:"), 1, 0)
        time_widget = QWidget()
        time_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        time_layout = QHBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)

        self.dca_run_at_enabled = QCheckBox("Enabled")
        self.dca_run_at_enabled.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.dca_run_at_enabled.setChecked(getattr(sys.modules['src.config'], 'DCA_RUN_AT_ENABLED', False))
        self.dca_run_at_enabled.setToolTip("When enabled, DCA will run at the specified time")

        self.dca_run_at_time = QTimeEdit()
        self.dca_run_at_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.dca_run_at_time.setDisplayFormat("HH:mm")
        self.dca_run_at_time.setTime(QTime(9, 0))  # Default 9:00 AM
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
        self.staking_allocation.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.staking_allocation.setRange(0, 100)
        self.staking_allocation.setValue(30)  # Default from config.py
        dca_layout.addWidget(self.staking_allocation, 2, 1)
        
        # Take Profit Percentage
        dca_layout.addWidget(QLabel("Take Profit (%):"), 3, 0)
        self.take_profit = QSpinBox()
        self.take_profit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.take_profit.setRange(10, 1000)
        self.take_profit.setValue(200)  # Default from config.py
        dca_layout.addWidget(self.take_profit, 3, 1)
        
        # Fixed DCA Amount
        dca_layout.addWidget(QLabel("Fixed DCA Amount (USD):"), 4, 0)
        self.fixed_dca_amount = QSpinBox()
        self.fixed_dca_amount.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.fixed_dca_amount.setRange(0, 1000)
        self.fixed_dca_amount.setValue(10)  # Default from config.py
        self.fixed_dca_amount.setToolTip("0 for dynamic DCA, or set a fixed amount")
        dca_layout.addWidget(self.fixed_dca_amount, 4, 1)
        
        # Dynamic Allocation Toggle
        dca_layout.addWidget(QLabel("Use Dynamic Allocation:"), 5, 0)
        self.use_dynamic_allocation = QCheckBox()
        
        # Try to load dynamic allocation setting from config
        try:
            from src.config import USE_DYNAMIC_ALLOCATION
            self.use_dynamic_allocation.setChecked(USE_DYNAMIC_ALLOCATION)
        except ImportError:
            self.use_dynamic_allocation.setChecked(False)  # Default to off
            
        self.use_dynamic_allocation.setToolTip("When enabled, uses dynamic allocation based on MAX_POSITION_PERCENTAGE instead of fixed amount")
        self.use_dynamic_allocation.stateChanged.connect(self.toggle_fixed_dca_amount)
        dca_layout.addWidget(self.use_dynamic_allocation, 5, 1)
        
        # Apply fixed width to all widgets in DCA section
        for row in range(dca_layout.rowCount()):
            item = dca_layout.itemAtPosition(row, 1)
            if item and item.widget():
                item.widget().setMinimumWidth(control_width)
                item.widget().setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        scroll_layout.addWidget(dca_group)
        
        # 4. Staking Settings
        staking_group = QGroupBox("Staking Settings")
        staking_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        staking_layout = QGridLayout(staking_group)
        
        # Make column 0 (labels) fixed width
        staking_layout.setColumnMinimumWidth(0, 200)
        # Make column 1 (input fields) fixed width
        staking_layout.setColumnMinimumWidth(1, field_width)
        
        # Staking Mode
        staking_layout.addWidget(QLabel("Staking Mode:"), 0, 0)
        self.staking_mode = QComboBox()
        self.staking_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.staking_mode.addItems(["separate", "auto_convert"])
        self.staking_mode.setCurrentText("separate")  # Default from config.py
        staking_layout.addWidget(self.staking_mode, 0, 1)
        
        # Auto-Convert Threshold
        staking_layout.addWidget(QLabel("Auto-Convert Threshold (USD):"), 1, 0)
        self.auto_convert_threshold = QSpinBox()
        self.auto_convert_threshold.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.auto_convert_threshold.setRange(1, 100)
        self.auto_convert_threshold.setValue(10)  # Default from config.py
        staking_layout.addWidget(self.auto_convert_threshold, 1, 1)
        
        # Min Conversion Amount
        staking_layout.addWidget(QLabel("Min Conversion Amount (USD):"), 2, 0)
        self.min_conversion_amount = QSpinBox()
        self.min_conversion_amount.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.min_conversion_amount.setRange(1, 50)
        self.min_conversion_amount.setValue(5)  # Default from config.py
        staking_layout.addWidget(self.min_conversion_amount, 2, 1)
        
        # Max Convert Percentage
        staking_layout.addWidget(QLabel("Max Convert Percentage (%):"), 3, 0)
        self.max_convert_percentage = QSpinBox()
        self.max_convert_percentage.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.max_convert_percentage.setRange(1, 100)
        self.max_convert_percentage.setValue(25)  # Default from config.py
        staking_layout.addWidget(self.max_convert_percentage, 3, 1)
        
        # Staking Protocols
        staking_layout.addWidget(QLabel("Staking Protocols:"), 4, 0)
        self.staking_protocols = QLineEdit("marinade,jito")  # Default from config.py
        self.staking_protocols.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.staking_protocols.setToolTip("Comma-separated list of supported staking protocols")
        staking_layout.addWidget(self.staking_protocols, 4, 1)
        
        # Yield Optimization Interval
        staking_layout.addWidget(QLabel("Yield Optimization Interval:"), 5, 0)
        yield_interval_widget = QWidget()
        yield_interval_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        yield_interval_layout = QHBoxLayout(yield_interval_widget)
        yield_interval_layout.setContentsMargins(0, 0, 0, 0)

        self.yield_optimization_value = QSpinBox()
        self.yield_optimization_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.yield_optimization_value.setRange(1, 30)  # Allow 1-30 units
        self.yield_optimization_value.setValue(1)  # Default 1 hour
        self.yield_optimization_value.setToolTip("How often to run yield optimization")

        self.yield_optimization_unit = QComboBox()
        self.yield_optimization_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.yield_optimization_unit.addItems(["Hour(s)", "Day(s)", "Week(s)", "Month(s)"])
        self.yield_optimization_unit.setCurrentText("Hour(s)")  # Default hours
        self.yield_optimization_unit.setToolTip("Time unit for yield optimization interval")

        yield_interval_layout.addWidget(self.yield_optimization_value)
        yield_interval_layout.addWidget(self.yield_optimization_unit)
        staking_layout.addWidget(yield_interval_widget, 5, 1)

        # Add scheduled time setting for Yield Optimization
        staking_layout.addWidget(QLabel("Yield Optimization Run At Time:"), 6, 0)
        yield_time_widget = QWidget()
        yield_time_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        yield_time_layout = QHBoxLayout(yield_time_widget)
        yield_time_layout.setContentsMargins(0, 0, 0, 0)

        self.yield_optimization_run_at_enabled = QCheckBox("Enabled")
        self.yield_optimization_run_at_enabled.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.yield_optimization_run_at_enabled.setChecked(self.yield_optimization_run_at_enabled_value)
        self.yield_optimization_run_at_enabled.setToolTip("When enabled, yield optimization will run at the specified time")

        self.yield_optimization_run_at_time = QTimeEdit()
        self.yield_optimization_run_at_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.yield_optimization_run_at_time.setDisplayFormat("HH:mm")
        self.yield_optimization_run_at_time.setTime(QTime(9, 0))  # Default 9:00 AM
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
        
        # Set yield optimization values from config
        self.yield_optimization_value.setValue(self.yield_optimization_interval_value_value)
        self.yield_optimization_unit.setCurrentText(self.yield_optimization_interval_unit_value)
        self.yield_optimization_run_at_enabled.setChecked(self.yield_optimization_run_at_enabled_value)

        # Set default time if not set
        if hasattr(self, 'yield_optimization_run_at_time_value') and self.yield_optimization_run_at_time_value:
            try:
                if isinstance(self.yield_optimization_run_at_time_value, str) and ":" in self.yield_optimization_run_at_time_value:
                    hour_str, minute_str = self.yield_optimization_run_at_time_value.split(":")
                    hour = int(hour_str)
                    minute = int(minute_str)
                    self.yield_optimization_run_at_time.setTime(QTime(hour, minute))
            except Exception as e:
                print(f"Warning: Could not parse yield optimization time: {e}")
                self.yield_optimization_run_at_time.setTime(QTime(9, 0))
        else:
            # Use default time
            self.yield_optimization_run_at_time.setTime(QTime(9, 0))
        
        # Apply fixed width to all widgets in staking section
        for row in range(staking_layout.rowCount()):
            item = staking_layout.itemAtPosition(row, 1)
            if item and item.widget():
                item.widget().setMinimumWidth(control_width)
                item.widget().setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        scroll_layout.addWidget(staking_group)
        
        # 5. Token Mapping
        token_group = QGroupBox("DCA Monitor Tokens")
        token_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        token_layout = QVBoxLayout(token_group)
        
        token_layout.addWidget(QLabel("Token Map (Solana address : symbol,hyperliquid_symbol):"))
        self.token_map = QTextEdit()
        self.token_map.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Default from config.py TOKEN_MAP
        try:
            # Try to get TOKEN_MAP from config.py
            from src.config import TOKEN_MAP
            
            # Format TOKEN_MAP into the text format expected by the UI
            token_map_lines = []
            for token_address, (symbol, hl_symbol) in TOKEN_MAP.items():
                token_map_lines.append(f"{token_address}: {symbol},{hl_symbol}")
            default_tokens = "\n".join(token_map_lines)
        except Exception as e:
            print(f"Error getting TOKEN_MAP from config: {e}")
            # Fallback to hardcoded default if TOKEN_MAP is not available
            default_tokens = """9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump: FART,FARTCOIN
HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC: AI16Z,AI16Z
So11111111111111111111111111111111111111112: SOL,SOL"""
        self.token_map.setPlainText(default_tokens)
        self.token_map.setMinimumHeight(100)
        self.token_map.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.token_map.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        token_layout.addWidget(self.token_map)
        scroll_layout.addWidget(token_group)
        
        # Add save button
        save_button = NeonButton("Save DCA/Staking Configuration", CyberpunkColors.SUCCESS)
        save_button.clicked.connect(self.save_config)
        save_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
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
            CyberpunkColors.PRIMARY,
            [
                {"name": "{portfolio_data}", "description": "Current copybot portfolio positions and performance"},
                {"name": "{market_data}", "description": "OHLCV market data and technical indicators for each position"}
            ]
        )
        scroll_layout.addWidget(copybot_frame)
        
        # Chart Analysis Agent Variables
        chart_frame = self.create_agent_frame(
            "Chart Analysis Agent Variables",
            CyberpunkColors.WARNING,
            [
                {"name": "{symbol}", "description": "Trading symbol/token being analyzed"},
                {"name": "{timeframe}", "description": "Chart timeframe (1m, 5m, 15m, 1h, etc.)"},
                {"name": "{chart_data}", "description": "Recent price action, technical indicators, and other chart data"}
            ]
        )
        scroll_layout.addWidget(chart_frame)
        
        # DCA Staking Agent Variables
        dca_frame = self.create_agent_frame(
            "Staking Agent Variables",
            CyberpunkColors.SECONDARY,
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
            CyberpunkColors.SUCCESS,
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
            CyberpunkColors.SUCCESS,
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
        table.horizontalHeader().setStyleSheet("color: black;")
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
            # Variable name - Should match frame color
            var_item = QTableWidgetItem(var["name"])
            var_item.setForeground(QColor(color))  # Variable names match frame color
            var_item.setFont(QFont("monospace", 10))
            table.setItem(i, 0, var_item)
            
            # Description - Changed to white
            desc_item = QTableWidgetItem(var["description"])
            desc_item.setForeground(QColor(CyberpunkColors.TEXT_LIGHT))  # Changed to white/light text
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
        
        # Data directory paths for persistence
        self.data_dir = os.path.join("src", "data")
        self.changes_file_path = os.path.join(self.data_dir, "change_events.csv")
        self.analysis_file_path = os.path.join(self.data_dir, "ai_analysis.csv")
        
        # Set maximum number of records to keep
        self.max_change_records = 25
        self.max_analysis_records = 25
        
        # Initialize UI first
        self.setup_ui()
        
        # Then load saved data (this ordering is important as UI elements must exist first)
        self.load_saved_data()
    
    def load_saved_data(self):
        """Load saved change events and AI analysis data"""
        try:
            # Load change events first
            self.load_change_events()
            
            # Then load AI analysis
            self.load_ai_analysis()
            
            # Log success
            print("Successfully loaded saved tracker data")
        except Exception as e:
            print(f"Error loading saved tracker data: {e}")
    
    def load_change_events(self):
        """Load change events from CSV file"""
        try:
            if not os.path.isfile(self.changes_file_path):
                return
                
            # Load events from CSV
            events_df = pd.read_csv(self.changes_file_path)
            
            # Sort by timestamp in REVERSE chronological order (newest first)
            events_df = events_df.sort_values('timestamp', ascending=False).reset_index(drop=True)
            
            # Limit to 25 records for display
            events_df = events_df.head(25)
            
            # Add each event to the table without saving again
            for idx in range(len(events_df)-1, -1, -1):
                row = events_df.iloc[idx]
                # Extract optional fields with defaults
                token_symbol = row.get('token_symbol', None)
                token_mint = row.get('token_mint', None)
                amount = row.get('amount', None)
                change = row.get('change', None)
                percent_change = row.get('percent_change', None)
                token_name = row.get('token_name', None)
                price = row.get('price', None)
                price_change = row.get('price_change', None)
                usd_change = row.get('usd_change', None)
                
                # Add to UI without saving to file again
                self.add_change_event_without_saving(
                    row['timestamp'],
                    row['event_type'],
                    row['wallet'],
                    row['token'],
                    token_symbol,
                    token_mint,
                    amount,
                    change,
                    percent_change,
                    token_name,
                    price,
                    price_change,
                    usd_change
                )
                
        except Exception as e:
            print(f"Error loading change events: {e}")
    
    def load_ai_analysis(self):
        """Load AI analysis events from CSV file"""
        try:
            if not os.path.isfile(self.analysis_file_path):
                return
                
            # Load analysis from CSV
            analysis_df = pd.read_csv(self.analysis_file_path)
            
            # Sort by timestamp in REVERSE chronological order (newest first)
            analysis_df = analysis_df.sort_values('timestamp', ascending=False).reset_index(drop=True)
            
            # Limit to 25 records for display
            analysis_df = analysis_df.head(25)
            
            # Add each analysis to the table without saving again
            for idx in range(len(analysis_df)-1, -1, -1):
                row = analysis_df.iloc[idx]
                # Extract optional fields with defaults
                change_percent = row.get('change_percent', None)
                token_mint = row.get('token_mint', None)
                token_name = row.get('token_name', None)
                
                # Add to UI without saving to file again
                self.add_ai_analysis_without_saving(
                    row['timestamp'],
                    row['action'],
                    row['token'],
                    row['token_symbol'],
                    row['analysis'],
                    row['confidence'],
                    row['price'],
                    change_percent,
                    token_mint,
                    token_name
                )
                
        except Exception as e:
            print(f"Error loading AI analysis: {e}")
    
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
        tracked_tokens_group = QGroupBox("Tracked Tokens")
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
        self.tokens_table.setColumnCount(9)
        self.tokens_table.setHorizontalHeaderLabels(["Last Updated", "Wallet", "Mint", "Token", "Symbol", "Amount", "Decimals", "Price", "USD Value"])
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
        self.changes_table.setColumnCount(12)  # Increase from 11 to 12 columns to add back percent change
        self.changes_table.setHorizontalHeaderLabels(["Time", "Type", "Wallet", "Mint", "Token", "Symbol", "Amount", "Amount Δ", "Amount %", "Price", "Price Δ", "USD Value Δ"])
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

        # Replace the auto-timer with a more cautious approach
        # Comment out the original timer
        # QTimer.singleShot(2000, self.refresh_tracked_tokens)
        
        # Add a safer version with try-except block
        def safe_refresh():
            try:
                self.refresh_tracked_tokens()
            except Exception as e:
                import traceback
                print(f"Error in auto-refresh timer: {str(e)}")
                traceback.print_exc()
                self.token_stats_label.setText(f"Token Stats: Error in auto-refresh - {str(e)}")
        
        QTimer.singleShot(5000, safe_refresh)  # Increased delay to 5 seconds
    
    def refresh_tracked_tokens(self):
        """Refresh the tracked tokens table from the artificial memory files"""
        from datetime import datetime
        import os
        import json
        from src.nice_funcs import token_price  # Import token_price function
        
        # Clear the table first
        self.tokens_table.setRowCount(0)
        
        try:
            # Determine which memory file to use based on DYNAMIC_MODE
            from src.config import DYNAMIC_MODE
            memory_file = os.path.join(
                os.getcwd(), 
                "src/data/artificial_memory_d.json" if DYNAMIC_MODE else "src/data/artificial_memory_m.json"
            )
            
            # Skip if file doesn't exist
            if not os.path.exists(memory_file):
                self.token_stats_label.setText("Token Stats: Memory file not found")
                return
            
            # Load the raw JSON data
            with open(memory_file, "r") as f:
                raw_data = f.read()
                memory_data = json.loads(raw_data)
            
            # Define empty containers that will be populated
            wallet_data = {}
            token_stats = {}
            
            # Function to safely extract data from the JSON
            def safe_extract_wallet_data(data):
                # Return a valid dict or empty dict
                if not isinstance(data, dict):
                    return {}
                
                # Check several possible paths to locate wallet data
                if 'data' in data:
                    if isinstance(data['data'], dict):
                        if 'data' in data['data'] and isinstance(data['data']['data'], dict):
                            return data['data']['data']
                        # If no nested data
                        return data['data']
                
                # Fallback: Just use what's there if it's a dict
                return data if isinstance(data, dict) else {}
            
            # Extract the wallet data safely
            wallet_data = safe_extract_wallet_data(memory_data)
            
            # Safely extract wallet stats if available
            wallet_stats = {}
            if isinstance(memory_data, dict) and isinstance(memory_data.get('data'), dict):
                stats = memory_data['data'].get('wallet_stats')
                if isinstance(stats, dict):
                    wallet_stats = stats
            
            # Row counter for the table
            row = 0
            
            # Counter for wallet tokens (will be used for stats)
            token_counts = {}
            
            # Process tokens for each wallet (if wallet_data is valid)
            if isinstance(wallet_data, dict):
                for wallet, tokens in wallet_data.items():
                    # Only process if tokens is a list or dict
                    if not isinstance(tokens, (list, dict)):
                        token_counts[wallet] = 0
                        continue
                    
                    # Count tokens
                    token_count = 0
                    
                    # Process each token
                    if isinstance(tokens, list):
                        token_items = tokens
                    else:  # If it's a dict
                        token_items = list(tokens.values())
                    
                    for token_data in token_items:
                        # Skip if not a dictionary
                        if not isinstance(token_data, dict):
                            continue
                        
                        # Add row to table
                        self.tokens_table.insertRow(row)
                        
                        # Format timestamp
                        timestamp = str(token_data.get('timestamp', ''))
                        try:
                            dt = datetime.fromisoformat(timestamp)
                            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            formatted_time = timestamp
                        
                        # Add data to table (with null checks)
                        self.tokens_table.setItem(row, 0, QTableWidgetItem(formatted_time))
                        self.tokens_table.setItem(row, 1, QTableWidgetItem(str(wallet)))
                        
                        # Token info (convert all to strings to be safe)
                        token_mint = str(token_data.get('mint', 'Unknown'))
                        token_name = str(token_data.get('name', 'Unknown Token'))
                        token_symbol = str(token_data.get('symbol', 'UNK'))
                        
                        self.tokens_table.setItem(row, 2, QTableWidgetItem(token_mint))
                        self.tokens_table.setItem(row, 3, QTableWidgetItem(token_name))
                        self.tokens_table.setItem(row, 4, QTableWidgetItem(token_symbol))
                        
                        # Amount and decimals
                        try:
                            amount = float(token_data.get('amount', 0))
                        except:
                            amount = 0
                            
                        try:
                            decimals = int(token_data.get('decimals', 0))
                        except:
                            decimals = 0
                        
                        self.tokens_table.setItem(row, 5, QTableWidgetItem(str(amount)))
                        self.tokens_table.setItem(row, 6, QTableWidgetItem(str(decimals)))
                        
                        # Price
                        try:
                            price = float(token_data.get('price', 0))
                            if price == 0:
                                try:
                                    price = token_price(token_mint)
                                except:
                                    price = 0
                        except:
                            price = 0
                        
                        # Format price
                        price_text = f"${price:.6f}" if price > 0 and price < 0.01 else f"${price:.4f}" if price > 0 else "N/A"
                        self.tokens_table.setItem(row, 7, QTableWidgetItem(price_text))
                        
                        # USD Value
                        if price > 0 and amount > 0:
                            usd_value = amount * price
                            
                            # Format the USD value
                            if usd_value >= 1000000:  # $1M+
                                usd_text = f"${usd_value/1000000:.2f}M"
                            elif usd_value >= 1000:  # $1K+
                                usd_text = f"${usd_value/1000:.2f}K"
                            elif usd_value >= 1:  # $1+
                                usd_text = f"${usd_value:.2f}"
                            else:  # < $1
                                usd_text = f"${usd_value:.4f}"
                                
                            # Highlight based on value
                            usd_item = QTableWidgetItem(usd_text)
                            if usd_value >= 10000:
                                usd_item.setForeground(QColor(CyberpunkColors.SUCCESS))
                            elif usd_value >= 1000:
                                usd_item.setForeground(QColor(CyberpunkColors.WARNING))
                            
                            self.tokens_table.setItem(row, 8, usd_item)
                        else:
                            self.tokens_table.setItem(row, 8, QTableWidgetItem("N/A"))
                        
                        # Increment counters
                        row += 1
                        token_count += 1
                    
                    # Store token count for this wallet
                    token_counts[wallet] = token_count
            
            # Prepare the stats text
            stats_parts = []
            
            # First try to use wallet_stats if available
            if isinstance(wallet_stats, dict) and wallet_stats:
                for wallet, stats in wallet_stats.items():
                    if isinstance(stats, dict):
                        found = stats.get('found', 0)
                        skipped = stats.get('skipped', 0)
                        try:
                            short_wallet = wallet[:4]
                        except:
                            short_wallet = str(wallet)
                        stats_parts.append(f"{short_wallet}: {found} found, {skipped} skipped")
            
            # If no stats from wallet_stats, use our token counts
            if not stats_parts and token_counts:
                for wallet, count in token_counts.items():
                    try:
                        short_wallet = wallet[:4]
                    except:
                        short_wallet = str(wallet)
                    stats_parts.append(f"{short_wallet}: {count} tokens")
            
            # Finalize stats text
            if stats_parts:
                stats_text = "Token Stats: " + " | ".join(stats_parts)
            else:
                stats_text = "Token Stats: No tokens found"
            
            # Update the label
            self.token_stats_label.setText(stats_text)
            
        except Exception as e:
            import traceback
            print(f"ERROR IN refresh_tracked_tokens: {type(e).__name__}: {str(e)}")
            print("---- STACK TRACE ----")
            traceback.print_exc()
            print("---- END STACK TRACE ----")
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
            
            # Process changes into the changes table - APPEND to existing data, don't clear
            if changes:
                # REMOVED: self.clear_changes() - Don't clear, just add to existing data
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
                price = details.get('price', 0)
                usd_value = details.get('usd_value', 0)
                
                self.add_change_event(
                    timestamp=timestamp,
                    event_type="NEW",
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_symbol,
                    token_mint=token_mint,
                    amount=amount,
                    token_name=token_name,
                    price=price,  # Add price
                    price_change=0,  # No change for new tokens
                    usd_change=0  # No change for new tokens
                )
            
            # Process removed tokens
            for token_mint, details in wallet_changes.get('removed', {}).items():
                token_name = details.get('name', 'Unknown Token')
                token_symbol = details.get('symbol', 'UNK')
                amount = details.get('amount', 0)
                price = details.get('price', 0)
                usd_value = details.get('usd_value', 0)
                
                self.add_change_event(
                    timestamp=timestamp,
                    event_type="REMOVED",
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_symbol,
                    token_mint=token_mint,
                    amount=amount,
                    token_name=token_name,
                    price=price,  # Add price
                    price_change=0,  # No change for removed tokens
                    usd_change=-usd_value  # Negative USD value for removed tokens
                )
            
            # Process modified tokens
            for token_mint, details in wallet_changes.get('modified', {}).items():
                token_name = details.get('name', 'Unknown Token')
                token_symbol = details.get('symbol', 'UNK')
                current_price = details.get('current_price', 0)
                price_change = details.get('price_change', 0)
                usd_change = details.get('usd_change', 0)
                
                self.add_change_event(
                    timestamp=timestamp,
                    event_type="MODIFIED",
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_symbol,
                    token_mint=token_mint,
                    amount=details['current_amount'],
                    change=details['change'],
                    percent_change=details['pct_change'],  # Keep for backwards compatibility
                    token_name=token_name,
                    price=current_price,  # Add current price
                    price_change=price_change,  # Add price change
                    usd_change=usd_change  # Add USD value change
                )
    
    def clear_changes(self):
        """Clear change events from the display AND delete the CSV file when manually requested by user"""
        try:
            # Clear the table UI
            self.changes_table.setRowCount(0)
            
            # Delete the CSV file
            if os.path.exists(self.changes_file_path):
                os.remove(self.changes_file_path)
                print(f"Successfully deleted change events file: {self.changes_file_path}")
            
            print("Manually cleared change events from display and deleted CSV file.")
        except Exception as e:
            print(f"Error deleting change events file: {e}")

    def add_change_event(self, timestamp, event_type, wallet, token, token_symbol=None, token_mint=None, amount=None, change=None, percent_change=None, token_name=None, price=None, price_change=None, usd_change=None):
        """Add a new change detection event to the table"""
        # First add to UI
        self.add_change_event_without_saving(
            timestamp, event_type, wallet, token, token_symbol, token_mint, 
            amount, change, percent_change, token_name, price, price_change, usd_change
        )
        
        # Then save to file
        self.save_change_event(
            timestamp, event_type, wallet, token, token_symbol, token_mint, 
            amount, change, percent_change, token_name, price, price_change, usd_change
        )
        
    def save_change_event(self, timestamp, event_type, wallet, token, token_symbol, token_mint, 
                         amount, change, percent_change, token_name, price, price_change, usd_change):
        """Save a change event to CSV file"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Create change event data
            event_data = {
                'timestamp': timestamp,
                'event_type': event_type,
                'wallet': wallet,
                'token': token,
                'token_symbol': token_symbol,
                'token_mint': token_mint,
                'amount': amount,
                'change': change,
                'percent_change': percent_change,
                'token_name': token_name,
                'price': price,
                'price_change': price_change,
                'usd_change': usd_change
            }
            
            # Convert to DataFrame for saving
            event_df = pd.DataFrame([event_data])
            
            # Check if file exists
            file_exists = os.path.isfile(self.changes_file_path)
            
            # Save to CSV (append mode if file exists)
            if file_exists:
                # Read existing file to check record count
                existing_df = pd.read_csv(self.changes_file_path)
                
                # Combine with new data - new data first for newest-first order
                combined_df = pd.concat([event_df, existing_df], ignore_index=True)
                
                # Limit to max records by keeping most recent
                if len(combined_df) > self.max_change_records:
                    combined_df = combined_df.head(self.max_change_records)
                
                # Save all data
                combined_df.to_csv(self.changes_file_path, index=False)
            else:
                # New file
                event_df.to_csv(self.changes_file_path, index=False)
                
        except Exception as e:
            print(f"Error saving change event: {e}")
    
    def add_change_event_without_saving(self, timestamp, event_type, wallet, token, token_symbol=None, token_mint=None, 
                                      amount=None, change=None, percent_change=None, token_name=None, price=None, 
                                      price_change=None, usd_change=None):
        """Add a change event to the table without saving to file (used when loading from file)"""
        # Insert at position 0 (top of the table) instead of at the end
        self.changes_table.insertRow(0)
        
        # Set each cell value - using row 0 for all cells
        self.changes_table.setItem(0, 0, QTableWidgetItem(timestamp))
        
        # Color-code the event type cell
        event_item = QTableWidgetItem(event_type)
        if event_type.upper() == "NEW":
            event_item.setForeground(QColor(CyberpunkColors.SUCCESS))
        elif event_type.upper() == "REMOVED":
            event_item.setForeground(QColor(CyberpunkColors.DANGER))
        elif event_type.upper() == "MODIFIED":
            event_item.setForeground(QColor(CyberpunkColors.WARNING))
        self.changes_table.setItem(0, 1, event_item)
        
        self.changes_table.setItem(0, 2, QTableWidgetItem(wallet))
        
        # Token mint, name and symbol
        self.changes_table.setItem(0, 3, QTableWidgetItem(token_mint or "Unknown"))
        self.changes_table.setItem(0, 4, QTableWidgetItem(token))
        self.changes_table.setItem(0, 5, QTableWidgetItem(token_symbol or "UNK"))
        
        # Amount and amount change columns
        self.changes_table.setItem(0, 6, QTableWidgetItem(str(amount) if amount is not None else "N/A"))
        
        # Set amount change
        if change is not None:
            change_item = QTableWidgetItem(str(change))
            if isinstance(change, (int, float)):
                if change > 0:
                    change_item.setForeground(QColor(CyberpunkColors.SUCCESS))
                elif change < 0:
                    change_item.setForeground(QColor(CyberpunkColors.DANGER))
            self.changes_table.setItem(0, 7, change_item)
        else:
            self.changes_table.setItem(0, 7, QTableWidgetItem("N/A"))
        
        # Set percent change (column 8)
        if percent_change is not None:
            pct_item = QTableWidgetItem(f"{percent_change}%")
            if isinstance(percent_change, (int, float)):
                if percent_change > 0:
                    pct_item.setForeground(QColor(CyberpunkColors.SUCCESS))
                elif percent_change < 0:
                    pct_item.setForeground(QColor(CyberpunkColors.DANGER))
            self.changes_table.setItem(0, 8, pct_item)
        else:
            self.changes_table.setItem(0, 8, QTableWidgetItem("N/A"))
        
        # Set current price (column 9)
        if price is not None:
            # Format price for display
            if isinstance(price, (int, float)):
                if price < 0.01:
                    price_text = f"${price:.6f}"
                elif price < 1:
                    price_text = f"${price:.4f}"
                else:
                    price_text = f"${price:.2f}"
                self.changes_table.setItem(0, 9, QTableWidgetItem(price_text))
            else:
                self.changes_table.setItem(0, 9, QTableWidgetItem(str(price)))
        else:
            self.changes_table.setItem(0, 9, QTableWidgetItem("N/A"))
        
        # Set price change (column 10)
        if price_change is not None:
            # Format price change
            if isinstance(price_change, (int, float)):
                if abs(price_change) < 0.01:
                    price_change_text = f"${price_change:.6f}"
                elif abs(price_change) < 1:
                    price_change_text = f"${price_change:.4f}"
                else:
                    price_change_text = f"${price_change:.2f}"
                    
                price_change_item = QTableWidgetItem(price_change_text)
                if price_change > 0:
                    price_change_item.setForeground(QColor(CyberpunkColors.SUCCESS))
                elif price_change < 0:
                    price_change_item.setForeground(QColor(CyberpunkColors.DANGER))
                self.changes_table.setItem(0, 10, price_change_item)
            else:
                self.changes_table.setItem(0, 10, QTableWidgetItem(str(price_change)))
        else:
            self.changes_table.setItem(0, 10, QTableWidgetItem("N/A"))
        
        # Set USD value change (column 11)
        if usd_change is not None:
            # Format USD change based on size
            if isinstance(usd_change, (int, float)):
                if abs(usd_change) >= 1000000:  # $1M+
                    usd_change_text = f"${usd_change/1000000:.2f}M"
                elif abs(usd_change) >= 1000:  # $1K+
                    usd_change_text = f"${usd_change/1000:.2f}K"
                elif abs(usd_change) >= 1:  # $1+
                    usd_change_text = f"${usd_change:.2f}"
                elif abs(usd_change) >= 0.01:  # $0.01+
                    usd_change_text = f"${usd_change:.4f}"
                else:  # < $0.01
                    usd_change_text = f"${usd_change:.6f}"
                    
                usd_change_item = QTableWidgetItem(usd_change_text)
                if usd_change > 0:
                    usd_change_item.setForeground(QColor(CyberpunkColors.SUCCESS))
                elif usd_change < 0:
                    usd_change_item.setForeground(QColor(CyberpunkColors.DANGER))
                self.changes_table.setItem(0, 11, usd_change_item)
            else:
                self.changes_table.setItem(0, 11, QTableWidgetItem(str(usd_change)))
        else:
            self.changes_table.setItem(0, 11, QTableWidgetItem("N/A"))
                
        # Force a repaint and make sure the table is visible
        self.changes_table.repaint()
        self.changes_table.show()
    
    def clear_analysis(self):
        """Clear AI analysis from the display AND delete the CSV file when manually requested by user"""
        try:
            # Clear the table UI
            self.analysis_table.setRowCount(0)
            
            # Delete the CSV file
            if os.path.exists(self.analysis_file_path):
                os.remove(self.analysis_file_path)
                print(f"Successfully deleted AI analysis file: {self.analysis_file_path}")
            
            print("Manually cleared AI analysis from display and deleted CSV file.")
        except Exception as e:
            print(f"Error deleting AI analysis file: {e}")
                
    def add_ai_analysis(self, timestamp, action, token, token_symbol, analysis, confidence, price, change_percent=None, token_mint=None, token_name=None):
        """Add an AI analysis event to the analysis table and save to file"""
        # First add to UI
        self.add_ai_analysis_without_saving(
            timestamp, action, token, token_symbol, analysis, confidence, price, 
            change_percent, token_mint, token_name
        )
        
        # Then save to file
        self.save_ai_analysis(
            timestamp, action, token, token_symbol, analysis, confidence, price, 
            change_percent, token_mint, token_name
        )
        
        # Scroll to the top to see the newest event (instead of bottom)
        self.analysis_table.scrollToTop()
    
    def save_ai_analysis(self, timestamp, action, token, token_symbol, analysis, confidence, price, change_percent=None, token_mint=None, token_name=None):
        """Save an AI analysis event to CSV file"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Create analysis data
            analysis_data = {
                'timestamp': timestamp,
                'action': action,
                'token': token,
                'token_symbol': token_symbol,
                'analysis': analysis,
                'confidence': confidence,
                'price': price,
                'change_percent': change_percent,
                'token_mint': token_mint,
                'token_name': token_name
            }
            
            # Convert to DataFrame for saving
            analysis_df = pd.DataFrame([analysis_data])
            
            # Check if file exists
            file_exists = os.path.isfile(self.analysis_file_path)
            
            # Save to CSV (append mode if file exists)
            if file_exists:
                # Read existing file to check record count
                existing_df = pd.read_csv(self.analysis_file_path)
                
                # Combine with new data - new data first for newest-first order
                combined_df = pd.concat([analysis_df, existing_df], ignore_index=True)
                
                # Limit to max records by keeping most recent
                if len(combined_df) > self.max_analysis_records:
                    combined_df = combined_df.head(self.max_analysis_records)
                
                # Save all data
                combined_df.to_csv(self.analysis_file_path, index=False)
            else:
                # New file
                analysis_df.to_csv(self.analysis_file_path, index=False)
                
        except Exception as e:
            print(f"Error saving AI analysis: {e}")
            
    def add_ai_analysis_without_saving(self, timestamp, action, token, token_symbol, analysis, confidence, price, change_percent=None, token_mint=None, token_name=None):
        """Add an AI analysis event to the table without saving to file (used when loading from file)"""
        # Insert at position 0 (top of the table) instead of at the end
        self.analysis_table.insertRow(0)
        
        # Set the items in each column - using row 0 for all cells
        self.analysis_table.setItem(0, 0, QTableWidgetItem(str(timestamp or "")))
        
        # Color-code the action cell based on BUY/SELL/NOTHING
        action_item = QTableWidgetItem(str(action or ""))
        if action and action.upper() == "BUY":
            action_item.setForeground(QColor(CyberpunkColors.SUCCESS))
        elif action and action.upper() == "SELL":
            action_item.setForeground(QColor(CyberpunkColors.DANGER))
        self.analysis_table.setItem(0, 1, action_item)
        
        self.analysis_table.setItem(0, 2, QTableWidgetItem(str(token or "")))
        self.analysis_table.setItem(0, 3, QTableWidgetItem(str(token_symbol or "")))
        self.analysis_table.setItem(0, 4, QTableWidgetItem(str(token_mint or "Unknown")))
        self.analysis_table.setItem(0, 5, QTableWidgetItem(str(analysis or "")))
        
        # Add confidence with percentage - handle None/empty values
        if confidence:
            conf_str = f"{confidence}%"
        else:
            conf_str = "N/A"
        self.analysis_table.setItem(0, 6, QTableWidgetItem(conf_str))
        
        # Add price - handle None/empty/N/A values
        if price and price not in ["", "N/A", "None", None]:
            price_str = str(price)
        else:
            price_str = "N/A"
        self.analysis_table.setItem(0, 7, QTableWidgetItem(price_str))
                
        # Force a repaint and make sure the table is visible
        self.analysis_table.repaint()
        self.analysis_table.show()
        
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
            price = random.randint(10, 10000) / 100.0  # Random price between $0.10 and $100.00
            
            if event_type == "MODIFIED":
                # For modified events, provide changes
                amount_change = random.randint(-500000, 500000) / 100.0
                price_change = random.randint(-200, 200) / 100.0  # Price change between -$2.00 and +$2.00
                usd_change = amount * price_change + price * amount_change  # USD change based on both price and amount
                percent_change = round((amount_change / amount) * 100 if amount != 0 else 0, 2)
                
                self.add_change_event(
                    timestamp=timestamp,
                    event_type=event_type,
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_name,
                    token_mint=token,
                    amount=amount,
                    change=amount_change,
                    percent_change=percent_change,
                    token_name=token_name,
                    price=price,
                    price_change=price_change,
                    usd_change=usd_change
                )
            elif event_type == "NEW":
                # For new tokens, no change values but include price
                self.add_change_event(
                    timestamp=timestamp,
                    event_type=event_type,
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_name,
                    token_mint=token,
                    amount=amount,
                    token_name=token_name,
                    price=price,
                    price_change=0,  # No price change for new tokens
                    usd_change=0  # No USD change for new tokens
                )
            else:  # REMOVED
                # For removed tokens, USD change is negative of total value
                usd_value = amount * price
                self.add_change_event(
                    timestamp=timestamp,
                    event_type=event_type,
                    wallet=wallet[:8] + "..." + wallet[-4:],  # Format wallet for display
                    token=token_name,
                    token_symbol=token_name,
                    token_mint=token,
                    amount=amount,
                    token_name=token_name,
                    price=price,
                    price_change=0,  # No price change for removed tokens
                    usd_change=-usd_value  # Negative USD value for removed tokens
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
        # Add this at the top of setup_ui
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
        """)
        
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
        
        # Add this to fix scroll area background
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {CyberpunkColors.BACKGROUND};
                border: none;
            }}
            QScrollArea > QWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
            }}
        """)
        
        # Container widget for charts
        self.charts_container = QWidget()
        # Add this to fix container background
        self.charts_container.setStyleSheet(f"""
            background-color: {CyberpunkColors.BACKGROUND};
        """)
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
                
                # Extract Fibonacci level from reasoning if present
                reasoning_text = latest.get('reasoning', '')
                fib_level = None
                
                # Search for Fibonacci information in the reasoning text
                fib_patterns = [
                    r"Using Fibonacci (\d+\.\d+)",
                    r"Fibonacci (\d+\.\d+)",
                    r"Fib (\d+\.\d+)"
                ]
                
                for pattern in fib_patterns:
                    import re
                    match = re.search(pattern, reasoning_text)
                    if match:
                        fib_level = match.group(1)
                        break
                
                # Add Fibonacci label if a level was found
                if fib_level:
                    fib_label = QLabel(f"Fibonacci Level: {fib_level}")
                    frame_layout.addWidget(fib_label)
                    # Also apply styling to this label
                    fib_label.setStyleSheet(f"color: {CyberpunkColors.TEXT_LIGHT}; font-size: 14px;")
                
                # Create all labels first
                timeframe_label = QLabel(f"Timeframe: {latest['timeframe']}")
                signal_label = QLabel(f"Signal: {latest['signal']}")
                confidence_label = QLabel(f"Confidence: {latest['confidence']}%")
                direction_label = QLabel(f"Market Direction: {latest['direction']}")
                regime_label = QLabel(f"Market Regime: {latest['market_regime']}")
                volume_label = QLabel(f"Volume Trend: {latest['volume_trend']}")
                current_price_label = QLabel(f"Current Price: ${latest['price']:.6f}")
                reasoning_label = QLabel(f"AI Analysis: {reasoning_text}")
                updated_label = QLabel(f"Last Updated: {datetime.fromtimestamp(latest['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Common styling for all labels
                label_style = f"color: {CyberpunkColors.TEXT_LIGHT}; font-size: 14px;"
                
                # Create a list of labels to display in order
                labels_to_display = [
                    timeframe_label, 
                    signal_label, 
                    confidence_label, 
                    direction_label, 
                    regime_label, 
                    volume_label, 
                    current_price_label
                ]
                
                # Add entry price label for BUY/SELL signals
                if latest['signal'].upper() != "NOTHING" and latest['entry_price'] > 0:
                    entry_price_label = QLabel(f"Entry Price: ${latest['entry_price']:.6f}")
                    labels_to_display.append(entry_price_label)
                
                # Add remaining labels
                labels_to_display.extend([reasoning_label, updated_label])
                
                # Apply styling and add all labels to layout in one go
                for label in labels_to_display:
                    label.setStyleSheet(label_style)
                    frame_layout.addWidget(label)
                
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
        
        # Data directory paths for persistence
        self.data_dir = os.path.join("src", "data")
        self.orders_file_path = os.path.join(self.data_dir, "orders_history.csv")
        self.display_limit = 100  # Limit for UI display
        
        # Initialize the UI
        self.setup_ui()
        
        # Load existing orders if available
        self.load_orders()
        
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
            QScrollArea > QWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
            }}
        """)
        
        # Container widget for the scroll area
        container = QWidget()
        container_layout = QVBoxLayout(container)
        
        # Add PnL Summary Section
        pnl_summary = self.create_pnl_summary_section()
        container_layout.addWidget(pnl_summary)
        
        # Add Date Range Selector
        date_range_selector = self.create_date_range_selector()
        container_layout.addWidget(date_range_selector)
        
        # Orders table
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(12) # Increased column count
        self.orders_table.setHorizontalHeaderLabels([
            "Timestamp", "Agent", "Action", "Wallet Address", "Mint Address", "Token", "Amount", 
            "Entry Price", "Exit Price", "AI Analysis", "Status", "PnL"
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
        
        # Set the container as the scroll area's widget
        scroll_area.setWidget(container)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        # Set the container background explicitly
        container.setStyleSheet(f"""
            background-color: {CyberpunkColors.BACKGROUND};
        """)
        
        # Set the widget styles
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
        """)
        
    def create_pnl_summary_section(self):
        """Create the PnL summary section"""
        summary_group = QGroupBox("PnL Summary")
        summary_group.setStyleSheet(f"""
            QGroupBox {{
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QLabel {{
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
        """)
        
        summary_layout = QGridLayout(summary_group)
        
        # Create labels for displaying summary data
        self.total_pnl_label = QLabel("$0.00")
        self.total_pnl_label.setStyleSheet(f"color: {CyberpunkColors.SUCCESS}; font-size: 16px; font-weight: bold;")
        
        self.win_rate_label = QLabel("0%")
        self.avg_win_label = QLabel("$0.00")
        self.avg_loss_label = QLabel("$0.00")
        self.trade_count_label = QLabel("0")
        
        # Add labels to grid
        summary_layout.addWidget(QLabel("Total PnL:"), 0, 0)
        summary_layout.addWidget(self.total_pnl_label, 0, 1)
        summary_layout.addWidget(QLabel("Win Rate:"), 0, 2)
        summary_layout.addWidget(self.win_rate_label, 0, 3)
        summary_layout.addWidget(QLabel("Avg Win:"), 1, 0)
        summary_layout.addWidget(self.avg_win_label, 1, 1)
        summary_layout.addWidget(QLabel("Avg Loss:"), 1, 2)
        summary_layout.addWidget(self.avg_loss_label, 1, 3)
        summary_layout.addWidget(QLabel("Trade Count:"), 1, 4)
        summary_layout.addWidget(self.trade_count_label, 1, 5)
        
        return summary_group
        
    def create_date_range_selector(self):
        """Create date range selector with preset buttons"""
        date_range_group = QGroupBox("Date Range")
        date_range_group.setStyleSheet(f"""
            QGroupBox {{
                color: {CyberpunkColors.PRIMARY};
                border: 1px solid {CyberpunkColors.PRIMARY};
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QLabel {{
                color: {CyberpunkColors.TEXT_LIGHT};
            }}
            QDateEdit {{
                background-color: {CyberpunkColors.BACKGROUND};
                color: {CyberpunkColors.TEXT_LIGHT};
                border: 1px solid {CyberpunkColors.PRIMARY};
                padding: 5px;
            }}
        """)
        
        date_layout = QGridLayout(date_range_group)
        
        # Date pickers
        today = QDate.currentDate()
        
        self.start_date = QDateEdit()
        self.start_date.setDate(today.addDays(-30))  # Default to last 30 days
        self.start_date.setCalendarPopup(True)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(today)
        self.end_date.setCalendarPopup(True)
        
        # Connect date change signals
        self.start_date.dateChanged.connect(self.on_date_range_changed)
        self.end_date.dateChanged.connect(self.on_date_range_changed)
        
        # Preset buttons for quick date ranges
        today_btn = NeonButton("Today", CyberpunkColors.PRIMARY)
        today_btn.clicked.connect(lambda: self.set_date_range("today"))
        
        week_btn = NeonButton("This Week", CyberpunkColors.PRIMARY)
        week_btn.clicked.connect(lambda: self.set_date_range("week"))
        
        month_btn = NeonButton("This Month", CyberpunkColors.PRIMARY)
        month_btn.clicked.connect(lambda: self.set_date_range("month"))
        
        year_btn = NeonButton("This Year", CyberpunkColors.PRIMARY)
        year_btn.clicked.connect(lambda: self.set_date_range("year"))
        
        all_time_btn = NeonButton("All Time", CyberpunkColors.PRIMARY)
        all_time_btn.clicked.connect(lambda: self.set_date_range("all"))
        
        apply_btn = NeonButton("Apply Filter", CyberpunkColors.SUCCESS)
        apply_btn.clicked.connect(self.apply_date_filter)
        
        # Add widgets to layout
        date_layout.addWidget(QLabel("Start Date:"), 0, 0)
        date_layout.addWidget(self.start_date, 0, 1)
        date_layout.addWidget(QLabel("End Date:"), 0, 2)
        date_layout.addWidget(self.end_date, 0, 3)
        date_layout.addWidget(apply_btn, 0, 4)
        
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(today_btn)
        preset_layout.addWidget(week_btn)
        preset_layout.addWidget(month_btn)
        preset_layout.addWidget(year_btn)
        preset_layout.addWidget(all_time_btn)
        preset_layout.addStretch()
        
        date_layout.addLayout(preset_layout, 1, 0, 1, 5)
        
        return date_range_group
        
    def set_date_range(self, preset):
        """Set date range based on preset button"""
        today = QDate.currentDate()
        
        if preset == "today":
            self.start_date.setDate(today)
            self.end_date.setDate(today)
        elif preset == "week":
            # Calculate first day of current week (Monday)
            days_since_monday = today.dayOfWeek() - 1  # Qt uses 1-7 for Monday-Sunday
            self.start_date.setDate(today.addDays(-days_since_monday))
            self.end_date.setDate(today)
        elif preset == "month":
            # First day of current month
            self.start_date.setDate(QDate(today.year(), today.month(), 1))
            self.end_date.setDate(today)
        elif preset == "year":
            # First day of current year
            self.start_date.setDate(QDate(today.year(), 1, 1))
            self.end_date.setDate(today)
        elif preset == "all":
            # Use a past date that predates all orders
            self.start_date.setDate(QDate(2020, 1, 1))
            self.end_date.setDate(today)
            
        # Apply the filter
        self.apply_date_filter()
        
    def on_date_range_changed(self):
        """Handle date range changes"""
        if self.start_date.date() > self.end_date.date():
            # Prevent invalid date ranges
            self.start_date.setDate(self.end_date.date())
            
    def apply_date_filter(self):
        """Apply date range filter to orders table"""
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().addDays(1).toString("yyyy-MM-dd")  # Include end date
        
        # Convert to datetime for comparison
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        try:
            # Load all orders from database directly
            if os.path.isfile(self.orders_file_path):
                all_orders_df = pd.read_csv(self.orders_file_path)
                
                # Filter by date range
                filtered_orders = all_orders_df[
                    (pd.to_datetime(all_orders_df['timestamp']) >= start_dt) & 
                    (pd.to_datetime(all_orders_df['timestamp']) < end_dt)
                ]
                
                # Apply agent/action/status filters from UI if needed
                agent_filter = self.agent_filter.currentText()
                if agent_filter != "All Agents":
                    filtered_orders = filtered_orders[filtered_orders['agent'] == agent_filter]
                    
                action_filter = self.action_filter.currentText()
                if action_filter != "All Actions":
                    filtered_orders = filtered_orders[filtered_orders['action'] == action_filter]
                    
                status_filter = self.status_filter.currentText()
                if status_filter != "All Statuses":
                    filtered_orders = filtered_orders[filtered_orders['status'] == status_filter]
                
                # Sort by timestamp (newest first)
                filtered_orders = filtered_orders.sort_values('timestamp', ascending=False)
                
                # Reset index to ensure ordered iteration
                filtered_orders = filtered_orders.reset_index(drop=True)
                
                # Clear table and reload with filtered data
                self.orders_table.setRowCount(0)
                
                # Display filtered orders (limited to display limit for UI performance)
                order_count = 0
                for _, row in filtered_orders.iterrows():
                    if order_count >= self.display_limit:
                        break
                        
                    # Combine PnL value and percentage into tuple if both exist
                    pnl = None
                    if 'pnl_value' in row and pd.notna(row['pnl_value']):
                        if 'pnl_percentage' in row and pd.notna(row['pnl_percentage']):
                            pnl = (row['pnl_value'], row['pnl_percentage'])
                        else:
                            pnl = row['pnl_value']
                    
                    # Add to UI without saving to file again
                    self.add_order_without_saving(
                        row['timestamp'],
                        row['agent'],
                        row['action'],
                        row['token'],
                        row['amount'],
                        row['entry_price'],
                        row.get('status', 'Executed'),
                        row.get('exit_price', None),
                        pnl,
                        row.get('wallet_address', ''),
                        row.get('mint_address', ''),
                        row.get('ai_analysis', '')
                    )
                    order_count += 1
                
                # Update PnL summary for the filtered orders
                self.update_pnl_summary()
                
        except Exception as e:
            print(f"Error applying date filter: {e}")
            
            # Fallback to old method if there's an error
            self.apply_filters()
        
    def update_pnl_summary(self):
        """Update PnL summary stats based on filtered orders"""
        total_pnl = 0.0
        win_count = 0
        loss_count = 0
        total_win_amount = 0.0
        total_loss_amount = 0.0
        visible_rows = 0
        
        # Process visible rows only
        for row in range(self.orders_table.rowCount()):
            if not self.orders_table.isRowHidden(row):
                visible_rows += 1
                
                # Get PnL from last column
                pnl_item = self.orders_table.item(row, 11)
                if pnl_item and pnl_item.text() != "N/A":
                    try:
                        # Extract numeric PnL value from formatted text like "$123.45" or "$123.45 (45.67%)"
                        pnl_text = pnl_item.text().replace("$", "").split(" ")[0]
                        pnl_value = float(pnl_text)
                        
                        total_pnl += pnl_value
                        
                        # Count wins and losses
                        if pnl_value > 0:
                            win_count += 1
                            total_win_amount += pnl_value
                        elif pnl_value < 0:
                            loss_count += 1
                            total_loss_amount += abs(pnl_value)
                    except (ValueError, IndexError):
                        # Skip rows with invalid PnL format
                        pass
        
        # Update summary labels
        self.total_pnl_label.setText(f"${total_pnl:.2f}")
        self.total_pnl_label.setStyleSheet(
            f"color: {CyberpunkColors.SUCCESS if total_pnl >= 0 else CyberpunkColors.DANGER}; "
            f"font-size: 16px; font-weight: bold;"
        )
        
        # Calculate win rate
        total_trades = win_count + loss_count
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        self.win_rate_label.setText(f"{win_rate:.1f}%")
        
        # Calculate averages
        avg_win = (total_win_amount / win_count) if win_count > 0 else 0
        avg_loss = (total_loss_amount / loss_count) if loss_count > 0 else 0
        
        self.avg_win_label.setText(f"${avg_win:.2f}")
        self.avg_loss_label.setText(f"${avg_loss:.2f}")
        self.trade_count_label.setText(f"{visible_rows}")

    def add_order(self, agent, action, token, amount, entry_price, status="Executed", 
                 exit_price=None, pnl=None, wallet_address="", mint_address="", ai_analysis=""):
        """Add a new order to the table with enhanced information"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Insert at the beginning (row 0)
        self.orders_table.insertRow(0)
        
        # Format values for display
        formatted_entry_price = f"${entry_price:.4f}" if entry_price is not None else "N/A"
        formatted_exit_price = f"${exit_price:.4f}" if exit_price is not None else "N/A"
        
        # Format PnL if available
        formatted_pnl = "N/A"
        if pnl is not None:
            if isinstance(pnl, tuple) and len(pnl) == 2:
                # If PnL is provided as (value, percentage)
                formatted_pnl = f"${pnl[0]:.2f} ({pnl[1]:.2f}%)"
            else:
                # Just a value
                formatted_pnl = f"${pnl:.2f}"
        
        # Truncate long analysis text
        if ai_analysis and len(ai_analysis) > 50:
            ai_analysis = ai_analysis[:47] + "..."
            
        # Truncate wallet and mint addresses for display
        display_wallet = wallet_address[:10] + "..." if wallet_address and len(wallet_address) > 10 else wallet_address
        display_mint = mint_address[:10] + "..." if mint_address and len(mint_address) > 10 else mint_address
        
        # Set row items
        items = [
            QTableWidgetItem(timestamp),
            QTableWidgetItem(agent),
            QTableWidgetItem(action),
            QTableWidgetItem(display_wallet),
            QTableWidgetItem(display_mint),
            QTableWidgetItem(token),
            QTableWidgetItem(str(amount)),
            QTableWidgetItem(formatted_entry_price),
            QTableWidgetItem(formatted_exit_price),
            QTableWidgetItem(ai_analysis),
            QTableWidgetItem(status),
            QTableWidgetItem(formatted_pnl)
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
            if is_paper and col == 5:  # Token column is now at index 5
                item.setText(f"[PAPER] {item.text()}")
            
            # Create tooltip for full text/addresses
            if col == 3 and wallet_address:  # Wallet Address
                item.setToolTip(wallet_address)
            elif col == 4 and mint_address:  # Mint Address
                item.setToolTip(mint_address)
            elif col == 9 and ai_analysis:  # AI Analysis
                item.setToolTip(ai_analysis)
            elif col == 11 and pnl is not None:  # PnL
                if isinstance(pnl, tuple) and len(pnl) == 2:
                    item.setToolTip(f"Value: ${pnl[0]:.2f}, Percentage: {pnl[1]:.2f}%")
                else:
                    item.setToolTip(f"Value: ${pnl:.2f}")
                
            self.orders_table.setItem(0, col, item)
            
        # Save the order to database
        self.save_order(
            timestamp, agent, action, token, amount, entry_price, 
            exit_price, pnl, wallet_address, mint_address, ai_analysis, status
        )
            
        # Limit display to display_limit rows
        if self.orders_table.rowCount() > self.display_limit:
            self.orders_table.removeRow(self.orders_table.rowCount() - 1)
        
        # Update PnL summary
        self.update_pnl_summary()

    def save_order(self, timestamp, agent, action, token, amount, entry_price, 
                  exit_price, pnl, wallet_address, mint_address, ai_analysis, status):
        """Save order data to a CSV file"""
        try:
            # Create orders directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Format PnL for storage
            pnl_value = None
            pnl_percentage = None
            
            if isinstance(pnl, tuple) and len(pnl) == 2:
                pnl_value, pnl_percentage = pnl
            else:
                pnl_value = pnl
            
            # Create order data
            order_data = {
                'timestamp': timestamp,
                'agent': agent,
                'action': action,
                'token': token,
                'amount': amount,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_value': pnl_value,
                'pnl_percentage': pnl_percentage,
                'wallet_address': wallet_address,
                'mint_address': mint_address,
                'ai_analysis': ai_analysis,
                'status': status
            }
            
            # Convert to DataFrame for saving
            order_df = pd.DataFrame([order_data])
            
            # Check if file exists
            file_exists = os.path.isfile(self.orders_file_path)
            
            # Save to CSV (append or create new)
            if file_exists:
                # Read existing file
                existing_df = pd.read_csv(self.orders_file_path)
                
                # Combine with new data - put new data first for newest-first order
                combined_df = pd.concat([order_df, existing_df], ignore_index=True)
                
                # Save all data - no limit on database size
                combined_df.to_csv(self.orders_file_path, index=False)
            else:
                # New file
                order_df.to_csv(self.orders_file_path, index=False)
        except Exception as e:
            print(f"Error saving order: {e}")
    
    def load_orders(self):
        """Load orders from CSV file"""
        try:
            if not os.path.isfile(self.orders_file_path):
                return
                
            # Load orders from CSV
            orders_df = pd.read_csv(self.orders_file_path)
            
            # Sort by timestamp in REVERSE chronological order (newest first)
            orders_df = orders_df.sort_values('timestamp', ascending=False)
            
            # Reset index to ensure ordered iteration
            orders_df = orders_df.reset_index(drop=True)
            
            # Clear existing data
            self.orders_table.setRowCount(0)
            
            # Add orders to the table, limited to display_limit
            order_count = 0
            for _, row in orders_df.iterrows():
                if order_count >= self.display_limit:
                    break
                        
                # Combine PnL value and percentage into tuple if both exist
                pnl = None
                if 'pnl_value' in row and pd.notna(row['pnl_value']):
                    if 'pnl_percentage' in row and pd.notna(row['pnl_percentage']):
                        pnl = (row['pnl_value'], row['pnl_percentage'])
                    else:
                        pnl = row['pnl_value']
                
                # Add to UI without saving to file again
                self.add_order_without_saving(
                    row['timestamp'],
                    row['agent'],
                    row['action'],
                    row['token'],
                    row['amount'],
                    row['entry_price'],
                    row.get('status', 'Executed'),
                    row.get('exit_price', None),
                    pnl,
                    row.get('wallet_address', ''),
                    row.get('mint_address', ''),
                    row.get('ai_analysis', '')
                )
                order_count += 1
                
            # Update the PnL summary
            self.update_pnl_summary()
                
        except Exception as e:
            print(f"Error loading orders: {e}")
            
    def add_order_without_saving(self, timestamp, agent, action, token, amount, entry_price, 
                               status="Executed", exit_price=None, pnl=None, 
                               wallet_address="", mint_address="", ai_analysis=""):
        """Add an order entry to the orders table without saving it to the CSV file"""
        # Insert at position 0 (top of table) instead of at the end
        self.orders_table.insertRow(0)
        
        # Order status
        status_item = QTableWidgetItem(status)
        if status == "Executed":
            status_item.setForeground(QColor(CyberpunkColors.SUCCESS))
        elif status == "Failed":
            status_item.setForeground(QColor(CyberpunkColors.DANGER))
        elif status == "Pending":
            status_item.setForeground(QColor(CyberpunkColors.WARNING))
        self.orders_table.setItem(0, 0, status_item)
        
        # Timestamp
        self.orders_table.setItem(0, 1, QTableWidgetItem(timestamp))
        
        # Agent
        self.orders_table.setItem(0, 2, QTableWidgetItem(agent))
        
        # Action (BUY/SELL)
        action_item = QTableWidgetItem(action)
        if action == "BUY":
            action_item.setForeground(QColor(CyberpunkColors.SUCCESS))
        elif action == "SELL":
            action_item.setForeground(QColor(CyberpunkColors.DANGER))
        self.orders_table.setItem(0, 3, action_item)
        
        # Token
        self.orders_table.setItem(0, 4, QTableWidgetItem(token))
        
        # Token mint
        self.orders_table.setItem(0, 5, QTableWidgetItem(mint_address))
        
        # Amount
        self.orders_table.setItem(0, 6, QTableWidgetItem(str(amount)))
        
        # Entry price
        if entry_price is not None:
            if isinstance(entry_price, (int, float)):
                if entry_price < 0.01:
                    entry_price_text = f"${entry_price:.6f}"
                elif entry_price < 1:
                    entry_price_text = f"${entry_price:.4f}"
                else:
                    entry_price_text = f"${entry_price:.2f}"
                self.orders_table.setItem(0, 7, QTableWidgetItem(entry_price_text))
            else:
                self.orders_table.setItem(0, 7, QTableWidgetItem(str(entry_price)))
        else:
            self.orders_table.setItem(0, 7, QTableWidgetItem("N/A"))
        
        # Exit price
        if exit_price is not None:
            if isinstance(exit_price, (int, float)):
                if exit_price < 0.01:
                    exit_price_text = f"${exit_price:.6f}"
                elif exit_price < 1:
                    exit_price_text = f"${exit_price:.4f}"
                else:
                    exit_price_text = f"${exit_price:.2f}"
                self.orders_table.setItem(0, 8, QTableWidgetItem(exit_price_text))
            else:
                self.orders_table.setItem(0, 8, QTableWidgetItem(str(exit_price)))
        else:
            self.orders_table.setItem(0, 8, QTableWidgetItem("N/A"))
        
        # PnL
        if pnl is not None:
            # Check if PnL is a tuple with value and percentage
            if isinstance(pnl, tuple) and len(pnl) == 2:
                pnl_value, pnl_percentage = pnl
                
                # Format PnL value
                if isinstance(pnl_value, (int, float)):
                    if abs(pnl_value) < 0.01:
                        pnl_text = f"${pnl_value:.6f}"
                    elif abs(pnl_value) < 1:
                        pnl_text = f"${pnl_value:.4f}"
                    else:
                        pnl_text = f"${pnl_value:.2f}"
                else:
                    pnl_text = str(pnl_value)
                    
                # Add percentage if available
                if pnl_percentage is not None:
                    pnl_text += f" ({pnl_percentage:.2f}%)"
                    
                # Create item with color
                pnl_item = QTableWidgetItem(pnl_text)
                if pnl_value > 0:
                    pnl_item.setForeground(QColor(CyberpunkColors.SUCCESS))
                elif pnl_value < 0:
                    pnl_item.setForeground(QColor(CyberpunkColors.DANGER))
                self.orders_table.setItem(0, 9, pnl_item)
            else:
                # Simple numeric PnL
                if isinstance(pnl, (int, float)):
                    pnl_item = QTableWidgetItem(f"${pnl:.2f}")
                    if pnl > 0:
                        pnl_item.setForeground(QColor(CyberpunkColors.SUCCESS))
                    elif pnl < 0:
                        pnl_item.setForeground(QColor(CyberpunkColors.DANGER))
                    self.orders_table.setItem(0, 9, pnl_item)
                else:
                    self.orders_table.setItem(0, 9, QTableWidgetItem(str(pnl)))
        else:
            self.orders_table.setItem(0, 9, QTableWidgetItem("N/A"))
        
        # Wallet address (shortened)
        if wallet_address:
            shortened_wallet = wallet_address[:8] + "..." + wallet_address[-4:] if len(wallet_address) > 12 else wallet_address
            self.orders_table.setItem(0, 10, QTableWidgetItem(shortened_wallet))
        else:
            self.orders_table.setItem(0, 10, QTableWidgetItem("N/A"))
            
        # AI Analysis (tooltip for context)
        analysis_item = QTableWidgetItem("View")
        analysis_item.setToolTip(ai_analysis if ai_analysis else "No analysis available")
        self.orders_table.setItem(0, 11, analysis_item)
        
        # Force a repaint
        self.orders_table.repaint()

    def apply_filters(self):
        """Apply selected filters to the orders table"""
        agent_filter = self.agent_filter.currentText()
        action_filter = self.action_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        for row in range(self.orders_table.rowCount()):
            agent = self.orders_table.item(row, 1).text()
            action = self.orders_table.item(row, 2).text()
            status = self.orders_table.item(row, 10).text()  # Updated index for status
            
            show_row = (agent_filter == "All Agents" or agent == agent_filter) and \
                      (action_filter == "All Actions" or action == action_filter) and \
                      (status_filter == "All Statuses" or status == status_filter)
                      
            self.orders_table.setRowHidden(row, not show_row)
        
        # Update PnL summary based on filtered results
        self.update_pnl_summary()
            
    def clear_filters(self):
        """Clear all filters"""
        self.agent_filter.setCurrentText("All Agents")
        self.action_filter.setCurrentText("All Actions")
        self.status_filter.setCurrentText("All Statuses")
        
        # Also reset date range to all time
        today = QDate.currentDate()
        self.start_date.setDate(QDate(2020, 1, 1))
        self.end_date.setDate(today)
        
        # Apply the reset filters
        self.apply_date_filter()

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