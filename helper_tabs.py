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

        # Force initial refresh after UI is fully loaded
        QTimer.singleShot(2000, self.refresh_tracked_tokens)
    
    def refresh_tracked_tokens(self):
        """Refresh the tracked tokens table from the artificial memory files"""
        from datetime import datetime
        import os
        import json
        from src.nice_funcs import token_price  # Import token_price function
        
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
                        
                        # Format timestamp (now in column 0)
                        timestamp = token_data.get('timestamp', '')
                        try:
                            dt = datetime.fromisoformat(timestamp)
                            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            formatted_time = timestamp
                        
                        self.tokens_table.setItem(row, 0, QTableWidgetItem(formatted_time))
                        self.tokens_table.setItem(row, 1, QTableWidgetItem(wallet))
                        
                        # Get token mint, name and symbol
                        token_mint = token_data.get('mint', 'Unknown')
                        token_name = token_data.get('name', 'Unknown Token')
                        token_symbol = token_data.get('symbol', 'UNK')
                        
                        # Display mint, name and symbol
                        self.tokens_table.setItem(row, 2, QTableWidgetItem(token_mint))
                        self.tokens_table.setItem(row, 3, QTableWidgetItem(token_name))
                        self.tokens_table.setItem(row, 4, QTableWidgetItem(token_symbol))
                        
                        # Get amount and decimals
                        amount = token_data.get('amount', 0)
                        decimals = token_data.get('decimals', 0)
                        
                        # Amount in column 5
                        self.tokens_table.setItem(row, 5, QTableWidgetItem(str(amount)))
                        
                        # Decimals in column 6 (moved to be between Amount and Price)
                        self.tokens_table.setItem(row, 6, QTableWidgetItem(str(decimals)))
                        
                        # Get price for column 7
                        # First try to get price from token_data
                        price = token_data.get('price')
                        if price is None:
                            # If price not in token_data, try to fetch it using token_price function
                            try:
                                price = token_price(token_mint)
                            except:
                                price = None
                                
                        # Format price for display
                        if price is not None:
                            price_text = f"${price:.6f}" if price < 0.01 else f"${price:.4f}"
                        else:
                            price_text = "N/A"
                            
                        # Add price in column 7
                        price_item = QTableWidgetItem(price_text)
                        self.tokens_table.setItem(row, 7, price_item)
                        
                        # Calculate and display USD value in column 8
                        if price is not None and amount is not None:
                            usd_value = amount * price
                            
                            # Format USD value
                            if usd_value >= 1000000:  # $1M+
                                usd_text = f"${usd_value/1000000:.2f}M"
                            elif usd_value >= 1000:  # $1K+
                                usd_text = f"${usd_value/1000:.2f}K"
                            elif usd_value >= 1:  # $1+
                                usd_text = f"${usd_value:.2f}"
                            elif usd_value >= 0.01:  # $0.01+
                                usd_text = f"${usd_value:.4f}"
                            else:  # < $0.01
                                usd_text = f"${usd_value:.6f}"
                                
                            # Color-code USD value based on amount
                            usd_item = QTableWidgetItem(usd_text)
                            if usd_value >= 10000:
                                usd_item.setForeground(QColor(CyberpunkColors.SUCCESS))
                            elif usd_value >= 1000:
                                usd_item.setForeground(QColor(CyberpunkColors.WARNING))
                            
                            self.tokens_table.setItem(row, 8, usd_item)
                        else:
                            self.tokens_table.setItem(row, 8, QTableWidgetItem("N/A"))
                        
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

