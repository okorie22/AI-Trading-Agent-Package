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
