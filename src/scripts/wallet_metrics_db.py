import sqlite3
import json
from datetime import datetime
import os

class WalletMetricsDB:
    def __init__(self, db_path=None):
        if db_path is None:
            # Use the same directory as the application
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'wallet_metrics.db')
        
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create wallet_metrics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallet_metrics (
            wallet_address TEXT PRIMARY KEY,
            win_loss_ratio REAL,
            roi REAL,
            avg_hold_time INTEGER,
            total_trades INTEGER,
            last_updated TIMESTAMP,
            ai_score REAL,
            ai_analysis TEXT
        )
        ''')
        
        # Create token_preferences table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_preferences (
            wallet_address TEXT,
            token_address TEXT,
            trade_count INTEGER,
            avg_position_size REAL,
            last_trade_time TIMESTAMP,
            PRIMARY KEY (wallet_address, token_address),
            FOREIGN KEY (wallet_address) REFERENCES wallet_metrics(wallet_address)
        )
        ''')
        
        # Create trade_history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address TEXT,
            token_address TEXT,
            entry_time TIMESTAMP,
            exit_time TIMESTAMP,
            entry_price REAL,
            exit_price REAL,
            position_size REAL,
            pnl REAL,
            FOREIGN KEY (wallet_address) REFERENCES wallet_metrics(wallet_address)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def update_wallet_metrics(self, wallet_address, metrics):
        """Update or insert wallet metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO wallet_metrics 
        (wallet_address, win_loss_ratio, roi, avg_hold_time, total_trades, last_updated, ai_score, ai_analysis)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wallet_address,
            metrics.get('win_loss_ratio'),
            metrics.get('roi'),
            metrics.get('avg_hold_time'),
            metrics.get('total_trades'),
            datetime.now(),
            metrics.get('ai_score'),
            metrics.get('ai_analysis')
        ))
        
        conn.commit()
        conn.close()
    
    def update_token_preferences(self, wallet_address, token_data):
        """Update token preferences for a wallet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for token in token_data:
            cursor.execute('''
            INSERT OR REPLACE INTO token_preferences 
            (wallet_address, token_address, trade_count, avg_position_size, last_trade_time)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                wallet_address,
                token['address'],
                token['trade_count'],
                token['avg_position_size'],
                datetime.now()
            ))
        
        conn.commit()
        conn.close()
    
    def add_trade(self, wallet_address, trade_data):
        """Add a new trade to the history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO trade_history 
        (wallet_address, token_address, entry_time, exit_time, entry_price, exit_price, position_size, pnl)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wallet_address,
            trade_data['token_address'],
            trade_data['entry_time'],
            trade_data['exit_time'],
            trade_data['entry_price'],
            trade_data['exit_price'],
            trade_data['position_size'],
            trade_data['pnl']
        ))
        
        conn.commit()
        conn.close()
    
    def get_wallet_metrics(self, wallet_address):
        """Get all metrics for a wallet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM wallet_metrics WHERE wallet_address = ?', (wallet_address,))
        metrics = cursor.fetchone()
        
        if metrics:
            cursor.execute('SELECT * FROM token_preferences WHERE wallet_address = ?', (wallet_address,))
            token_prefs = cursor.fetchall()
            
            return {
                'wallet_address': metrics[0],
                'win_loss_ratio': metrics[1],
                'roi': metrics[2],
                'avg_hold_time': metrics[3],
                'total_trades': metrics[4],
                'last_updated': metrics[5],
                'ai_score': metrics[6],
                'ai_analysis': metrics[7],
                'token_preferences': [
                    {
                        'address': pref[1],
                        'trade_count': pref[2],
                        'avg_position_size': pref[3],
                        'last_trade_time': pref[4]
                    }
                    for pref in token_prefs
                ]
            }
        
        conn.close()
        return None
    
    def get_all_wallets(self):
        """Get list of all tracked wallets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT wallet_address FROM wallet_metrics')
        wallets = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return wallets 