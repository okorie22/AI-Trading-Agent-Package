import sys
import os
import math
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QSlider, QComboBox, 
                             QLineEdit, QTextEdit, QProgressBar, QFrame, QGridLayout,
                             QSplitter, QGroupBox, QCheckBox, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSize
from PySide6.QtGui import QColor, QFont, QPalette, QLinearGradient, QGradient, QPainter, QPen, QBrush
import random

# Define cyberpunk color scheme
class CyberpunkColors:
    BACKGROUND = "#0D0D14"
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
        self.append(f'<span style="color:{color};">{message}</span>')

class PortfolioVisualization(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.tokens = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(50)  # Update every 50ms for animation
        
    def set_portfolio_data(self, tokens):
        """
        Set portfolio data for visualization
        tokens: list of dicts with keys: name, allocation, performance, volatility
        """
        self.tokens = tokens
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
            painter.drawText(self.rect(), Qt.AlignCenter, "Portfolio Visualization\n(No data available)")
            return
            
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) * 0.8
        
        # Draw tokens in a circular pattern
        angle_step = 360 / len(self.tokens)
        current_angle = 0
        
        for token in self.tokens:
            # Calculate position
            x = center_x + radius * 0.8 * math.cos(math.radians(current_angle))
            y = center_y + radius * 0.8 * math.sin(math.radians(current_angle))
            
            # Determine color based on performance
            if token.get('performance', 0) > 0:
                color = QColor(CyberpunkColors.SUCCESS)
            elif token.get('performance', 0) < 0:
                color = QColor(CyberpunkColors.DANGER)
            else:
                color = QColor(CyberpunkColors.PRIMARY)
                
            # Determine size based on allocation
            size = 10 + (token.get('allocation', 1) * 40)
            
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
            
            # Draw token name
            painter.setPen(QColor(CyberpunkColors.TEXT_WHITE))
            painter.setFont(QFont("Rajdhani", 8, QFont.Bold))
            text_rect = painter.boundingRect(int(x - 50), int(y + size/2 + 5), 
                                           100, 20, Qt.AlignCenter, token.get('name', ''))
            painter.drawText(text_rect, Qt.AlignCenter, token.get('name', ''))
            
            current_angle += angle_step

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
        
        # Simulate progress
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(100)
        
    def stop_agent(self):
        self.status = "Inactive"
        self.status_label.setText(self.status)
        self.status_label.setStyleSheet(f"color: {CyberpunkColors.DANGER};")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Stop progress timer
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.progress_bar.setValue(0)
        
    def update_progress(self):
        current_value = self.progress_bar.value()
        if current_value >= 100:
            self.progress_bar.setValue(0)
        else:
            self.progress_bar.setValue(current_value + 1)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("AI Crypto Trading System")
        self.resize(1200, 800)
        
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
        title_label = QLabel("AI CRYPTO TRADING SYSTEM")
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
        
        # Agent status cards
        agent_cards_layout = QHBoxLayout()
        
        # Create agent cards with different colors
        self.copybot_card = AgentStatusCard("Copybot Agent", CyberpunkColors.PRIMARY)
        self.risk_card = AgentStatusCard("Risk Agent", CyberpunkColors.DANGER)
        self.dca_card = AgentStatusCard("DCA/Staking Agent", CyberpunkColors.SUCCESS)
        self.chart_card = AgentStatusCard("Chart Analysis Agent", CyberpunkColors.SECONDARY)
        
        agent_cards_layout.addWidget(self.copybot_card)
        agent_cards_layout.addWidget(self.risk_card)
        agent_cards_layout.addWidget(self.dca_card)
        agent_cards_layout.addWidget(self.chart_card)
        
        dashboard_layout.addLayout(agent_cards_layout)
        
        # Add dashboard tab
        tab_widget.addTab(dashboard_widget, "Dashboard")
        
        # Configuration tab
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        
        # Create configuration form
        config_form = QGroupBox("System Configuration")
        config_form_layout = QGridLayout(config_form)
        
        # Add some example configuration options
        config_form_layout.addWidget(QLabel("AI Model:"), 0, 0)
        ai_model_combo = QComboBox()
        ai_model_combo.addItems(["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"])
        config_form_layout.addWidget(ai_model_combo, 0, 1)
        
        config_form_layout.addWidget(QLabel("AI Temperature:"), 1, 0)
        ai_temp_slider = QSlider(Qt.Horizontal)
        ai_temp_slider.setRange(0, 100)
        ai_temp_slider.setValue(70)
        config_form_layout.addWidget(ai_temp_slider, 1, 1)
        
        config_form_layout.addWidget(QLabel("Cash Percentage:"), 2, 0)
        cash_slider = QSlider(Qt.Horizontal)
        cash_slider.setRange(0, 100)
        cash_slider.setValue(20)
        config_form_layout.addWidget(cash_slider, 2, 1)
        
        config_form_layout.addWidget(QLabel("Max Position %:"), 3, 0)
        position_slider = QSlider(Qt.Horizontal)
        position_slider.setRange(0, 100)
        position_slider.setValue(10)
        config_form_layout.addWidget(position_slider, 3, 1)
        
        config_form_layout.addWidget(QLabel("Wallet Address:"), 4, 0)
        wallet_input = QLineEdit("4wgfCBf2WwLSRKLef9iW7JXZ2AfkxUxGM4XcKpHm3Sin")
        config_form_layout.addWidget(wallet_input, 4, 1)
        
        # Add save button
        save_button = NeonButton("Save Configuration", CyberpunkColors.SUCCESS)
        config_form_layout.addWidget(save_button, 5, 1)
        
        config_layout.addWidget(config_form)
        
        # Add configuration tab
        tab_widget.addTab(config_widget, "Configuration")
        
        # Add tabs for each agent
        tab_widget.addTab(QWidget(), "Copybot")
        tab_widget.addTab(QWidget(), "Risk Management")
        tab_widget.addTab(QWidget(), "DCA & Staking")
        tab_widget.addTab(QWidget(), "Chart Analysis")
        
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
        
        # Initialize with some sample data
        self.initialize_sample_data()
        
        # Add some initial console messages
        self.console.append_message("🌙 Anarcho Capital AI Agent Trading System Starting...", "system")
        self.console.append_message("📊 Active Agents and their Intervals:", "system")
        self.console.append_message("  • Copybot: ✅ ON (Every 30 minutes)", "info")
        self.console.append_message("  • Risk Management: ✅ ON (Every 10 minutes)", "info")
        self.console.append_message("  • DCA & Staking: ✅ ON (Every 12 hours)", "info")
        self.console.append_message("  • Chart Analysis: ✅ ON (Every 4 hours)", "info")
        self.console.append_message("💓 System heartbeat - All agents running on schedule", "success")
        
        # Setup timer for simulating real-time updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.simulate_updates)
        self.update_timer.start(5000)  # Update every 5 seconds
        
    def initialize_sample_data(self):
        # Sample portfolio data
        sample_tokens = [
            {"name": "SOL", "allocation": 0.35, "performance": 0.12, "volatility": 0.08},
            {"name": "BONK", "allocation": 0.15, "performance": 0.25, "volatility": 0.15},
            {"name": "JTO", "allocation": 0.20, "performance": -0.05, "volatility": 0.10},
            {"name": "PYTH", "allocation": 0.10, "performance": 0.08, "volatility": 0.05},
            {"name": "USDC", "allocation": 0.20, "performance": 0.0, "volatility": 0.01}
        ]
        self.portfolio_viz.set_portfolio_data(sample_tokens)
        
    def simulate_updates(self):
        # Simulate console updates
        messages = [
            ("💓 System heartbeat - All agents running on schedule", "success"),
            ("📊 Checking market conditions...", "info"),
            ("💰 Current portfolio balance: $1,245.67", "info"),
            ("🤖 CopyBot analyzing wallet 0x123...456", "info"),
            ("⚠️ Risk threshold approaching for JTO position", "warning"),
            ("✅ DCA purchase complete: Bought 0.25 SOL", "success")
        ]
        
        # Add a random message to console
        message, msg_type = random.choice(messages)
        self.console.append_message(message, msg_type)
        
        # Simulate portfolio changes
        if hasattr(self, 'portfolio_viz') and self.portfolio_viz.tokens:
            tokens = self.portfolio_viz.tokens
            for token in tokens:
                # Randomly adjust performance within a small range
                perf_change = (random.random() - 0.5) * 0.05
                token['performance'] = max(-0.5, min(0.5, token['performance'] + perf_change))
            
            self.portfolio_viz.set_portfolio_data(tokens)

def main():
    app = QApplication(sys.argv)
    
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
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
