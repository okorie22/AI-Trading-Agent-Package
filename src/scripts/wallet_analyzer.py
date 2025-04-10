from typing import Dict, List
import numpy as np
from datetime import datetime, timedelta

class WalletAnalyzer:
    def __init__(self):
        self.weights = {
            'win_loss_ratio': 0.3,
            'roi': 0.25,
            'avg_hold_time': 0.15,
            'trade_frequency': 0.15,
            'position_sizing': 0.15
        }
    
    def analyze_wallet(self, metrics: Dict) -> Dict:
        """Analyze wallet performance and generate a score and analysis"""
        # Calculate individual scores
        scores = {
            'win_loss_ratio': self._score_win_loss(metrics['win_loss_ratio']),
            'roi': self._score_roi(metrics['roi']),
            'avg_hold_time': self._score_hold_time(metrics['avg_hold_time']),
            'trade_frequency': self._score_trade_frequency(metrics['total_trades']),
            'position_sizing': self._score_position_sizing(metrics['token_preferences'])
        }
        
        # Calculate weighted average score
        total_score = sum(score * self.weights[metric] 
                         for metric, score in scores.items())
        
        # Generate analysis text
        analysis = self._generate_analysis(metrics, scores)
        
        return {
            'ai_score': total_score,
            'ai_analysis': analysis,
            'component_scores': scores
        }
    
    def _score_win_loss(self, ratio: float) -> float:
        """Score the win/loss ratio"""
        if ratio >= 2.0:  # Excellent
            return 10.0
        elif ratio >= 1.5:  # Good
            return 8.0
        elif ratio >= 1.2:  # Above average
            return 6.0
        elif ratio >= 1.0:  # Average
            return 5.0
        else:  # Below average
            return max(0.0, ratio * 5.0)
    
    def _score_roi(self, roi: float) -> float:
        """Score the ROI"""
        if roi >= 100:  # Excellent
            return 10.0
        elif roi >= 50:  # Good
            return 8.0
        elif roi >= 25:  # Above average
            return 6.0
        elif roi >= 10:  # Average
            return 5.0
        else:  # Below average
            return max(0.0, roi / 2.0)
    
    def _score_hold_time(self, hours: int) -> float:
        """Score the average hold time"""
        if hours >= 168:  # 1 week
            return 10.0
        elif hours >= 72:  # 3 days
            return 8.0
        elif hours >= 24:  # 1 day
            return 6.0
        elif hours >= 12:  # 12 hours
            return 5.0
        else:  # Below average
            return max(0.0, hours / 2.4)
    
    def _score_trade_frequency(self, total_trades: int) -> float:
        """Score the trade frequency"""
        if total_trades >= 100:  # Very active
            return 10.0
        elif total_trades >= 50:  # Active
            return 8.0
        elif total_trades >= 25:  # Moderate
            return 6.0
        elif total_trades >= 10:  # Light
            return 5.0
        else:  # Very light
            return max(0.0, total_trades)
    
    def _score_position_sizing(self, token_prefs: List[Dict]) -> float:
        """Score the position sizing strategy"""
        if not token_prefs:
            return 5.0
            
        # Calculate average position size
        avg_sizes = [token['avg_position_size'] for token in token_prefs]
        avg_size = np.mean(avg_sizes)
        
        # Calculate position size variance
        variance = np.var(avg_sizes) if len(avg_sizes) > 1 else 0
        
        # Score based on consistency and size
        if variance < 0.1:  # Very consistent
            return 10.0
        elif variance < 0.3:  # Consistent
            return 8.0
        elif variance < 0.5:  # Moderate
            return 6.0
        else:  # Inconsistent
            return 4.0
    
    def _generate_analysis(self, metrics: Dict, scores: Dict) -> str:
        """Generate a detailed analysis of the wallet's performance"""
        analysis = []
        
        # Overall performance
        analysis.append(f"Overall Wallet Score: {scores['win_loss_ratio']:.1f}/10")
        
        # Win/Loss analysis
        if metrics['win_loss_ratio'] >= 2.0:
            analysis.append("🌟 Exceptional win/loss ratio, showing strong trade management")
        elif metrics['win_loss_ratio'] >= 1.5:
            analysis.append("✅ Good win/loss ratio, indicating solid trading strategy")
        else:
            analysis.append("⚠️ Win/loss ratio could be improved")
        
        # ROI analysis
        if metrics['roi'] >= 100:
            analysis.append("🚀 Outstanding ROI, demonstrating excellent profit generation")
        elif metrics['roi'] >= 50:
            analysis.append("📈 Strong ROI, showing good profit potential")
        else:
            analysis.append("📊 ROI indicates room for improvement")
        
        # Hold time analysis
        if metrics['avg_hold_time'] >= 168:
            analysis.append("⏳ Long-term holding strategy, showing strong conviction")
        elif metrics['avg_hold_time'] >= 72:
            analysis.append("⏱️ Medium-term holding pattern, balanced approach")
        else:
            analysis.append("⚡ Short-term trading style, more active management")
        
        # Trade frequency analysis
        if metrics['total_trades'] >= 100:
            analysis.append("🔄 Very active trader, showing high engagement")
        elif metrics['total_trades'] >= 50:
            analysis.append("🔄 Active trader, maintaining regular market presence")
        else:
            analysis.append("🎯 Selective trading approach, quality over quantity")
        
        # Position sizing analysis
        if scores['position_sizing'] >= 8.0:
            analysis.append("⚖️ Consistent position sizing, showing disciplined risk management")
        elif scores['position_sizing'] >= 6.0:
            analysis.append("⚖️ Moderate position sizing consistency")
        else:
            analysis.append("⚠️ Position sizing could be more consistent")
        
        # Token preference analysis
        if metrics['token_preferences']:
            top_tokens = sorted(metrics['token_preferences'], 
                              key=lambda x: x['trade_count'], 
                              reverse=True)[:3]
            analysis.append("\nTop Traded Tokens:")
            for token in top_tokens:
                analysis.append(f"• {token['address'][:8]}... ({token['trade_count']} trades)")
        
        return "\n".join(analysis)