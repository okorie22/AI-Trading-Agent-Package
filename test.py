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