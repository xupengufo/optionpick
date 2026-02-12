"""
筛选器配置和工具函数
Screener configuration and utility functions
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ScreeningCriteria:
    """筛选条件配置类"""
    
    def __init__(self):
        # 基础筛选条件
        self.basic_criteria = {
            'min_stock_price': 10,
            'max_stock_price': 500,
            'min_days_to_expiry': 7,
            'max_days_to_expiry': 60,
            'min_volume': 50,
            'min_open_interest': 100,
            'max_bid_ask_spread_pct': 15
        }
        
        # 期权Greeks筛选条件
        self.greeks_criteria = {
            'min_delta': 0.1,
            'max_delta': 0.5,
            'min_theta': -0.05,  # 每日时间衰减
            'max_vega': 0.3      # 波动率敏感性
        }
        
        # 收益率筛选条件
        self.return_criteria = {
            'min_annualized_return': 10,    # 最低年化收益率 10%
            'min_profit_probability': 50,   # 最低盈利概率 50%
            'max_risk_reward_ratio': 3      # 最大风险收益比
        }
        
        # 市场环境筛选条件
        self.market_criteria = {
            'min_iv_rank': 20,              # 最低隐含波动率排名
            'max_iv_rank': 80,              # 最高隐含波动率排名
            'avoid_earnings': True,         # 避开财报期
            'min_market_cap': 1e9           # 最小市值 10亿美元
        }
    
    def get_criteria_for_strategy(self, strategy_type: str) -> Dict:
        """获取特定策略的筛选条件"""
        base_criteria = {**self.basic_criteria, **self.greeks_criteria, **self.return_criteria}
        
        if strategy_type == 'covered_call':
            # 备兑看涨期权偏好稍微高一点的Delta
            base_criteria.update({
                'min_delta': 0.2,
                'max_delta': 0.4,
                'min_annualized_return': 12
            })
        
        elif strategy_type == 'cash_secured_put':
            # 现金担保看跌期权可以接受稍低的Delta
            base_criteria.update({
                'min_delta': 0.15,
                'max_delta': 0.35,
                'min_annualized_return': 10
            })
        
        elif strategy_type == 'short_strangle':
            # 宽跨式策略需要更严格的条件
            base_criteria.update({
                'min_delta': 0.1,
                'max_delta': 0.3,
                'min_profit_probability': 60,
                'min_annualized_return': 15
            })
        
        elif strategy_type == 'iron_condor':
            # 铁鹰策略需要中性市场条件
            base_criteria.update({
                'min_delta': 0.05,
                'max_delta': 0.25,
                'min_profit_probability': 65,
                'max_iv_rank': 70
            })
        
        return base_criteria

class ScreeningUtils:
    """筛选工具函数"""
    
    @staticmethod
    def calculate_iv_rank(current_iv: float, iv_history: List[float], period_days: int = 252) -> float:
        """计算隐含波动率排名"""
        try:
            if not iv_history or len(iv_history) < 10:
                return 50  # 默认中等排名
            
            # 计算当前IV在历史数据中的排名
            below_current = sum(1 for iv in iv_history if iv < current_iv)
            percentile = (below_current / len(iv_history)) * 100
            
            return percentile
        except Exception as e:
            logger.error(f"Error calculating IV rank: {e}")
            return 50
    
    @staticmethod
    def is_earnings_week(symbol: str, target_date: datetime,
                         stock_data: Optional[Dict] = None) -> bool:
        """检查目标日期是否在财报日前后 7 天内"""
        try:
            earnings_date_str = None
            if stock_data:
                earnings_date_str = stock_data.get('basic_info', {}).get(
                    'next_earnings_date')
            if not earnings_date_str:
                return False
            earnings_date = datetime.strptime(earnings_date_str, '%Y-%m-%d')
            diff = abs((target_date - earnings_date).days)
            return diff <= 7
        except Exception as e:
            logger.warning(f"财报日期检查失败 {symbol}: {e}")
            return False

    @staticmethod
    def get_days_to_earnings(stock_data: Optional[Dict] = None) -> Optional[int]:
        """返回距离下次财报的天数，无数据返回 None"""
        if not stock_data:
            return None
        return stock_data.get('basic_info', {}).get('days_to_earnings')
    
    @staticmethod
    def calculate_liquidity_score(volume: int, open_interest: int, bid_ask_spread_pct: float) -> float:
        """计算流动性得分"""
        try:
            score = 0
            
            # 成交量得分 (0-40分)
            if volume >= 1000:
                score += 40
            elif volume >= 500:
                score += 30
            elif volume >= 200:
                score += 20
            elif volume >= 100:
                score += 10
            elif volume >= 50:
                score += 5
            
            # 持仓量得分 (0-40分)
            if open_interest >= 5000:
                score += 40
            elif open_interest >= 2000:
                score += 30
            elif open_interest >= 1000:
                score += 20
            elif open_interest >= 500:
                score += 10
            elif open_interest >= 100:
                score += 5
            
            # 买卖价差得分 (0-20分)
            if bid_ask_spread_pct <= 2:
                score += 20
            elif bid_ask_spread_pct <= 5:
                score += 15
            elif bid_ask_spread_pct <= 10:
                score += 10
            elif bid_ask_spread_pct <= 15:
                score += 5
            
            return score
        except Exception as e:
            logger.error(f"Error calculating liquidity score: {e}")
            return 0
    
    @staticmethod
    def calculate_risk_score(max_loss: float, max_profit: float, prob_profit: float) -> float:
        """计算风险得分"""
        try:
            score = 0
            
            # 风险收益比得分 (0-40分)
            if max_loss > 0 and max_profit > 0:
                risk_reward_ratio = max_loss / max_profit
                if risk_reward_ratio <= 2:
                    score += 40
                elif risk_reward_ratio <= 3:
                    score += 30
                elif risk_reward_ratio <= 4:
                    score += 20
                elif risk_reward_ratio <= 5:
                    score += 10
            
            # 盈利概率得分 (0-40分)
            if prob_profit >= 80:
                score += 40
            elif prob_profit >= 70:
                score += 30
            elif prob_profit >= 60:
                score += 20
            elif prob_profit >= 50:
                score += 10
            
            # 最大损失控制得分 (0-20分)
            if max_loss <= 500:  # 每合约最大损失$500
                score += 20
            elif max_loss <= 1000:
                score += 15
            elif max_loss <= 2000:
                score += 10
            elif max_loss <= 5000:
                score += 5
            
            return score
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0
    
    @staticmethod
    def filter_by_technical_analysis(stock_data: Dict, criteria: Dict) -> bool:
        """基于技术分析筛选股票"""
        try:
            # 获取历史数据
            historical_data = stock_data.get('historical_data', {})
            if not historical_data:
                return True  # 没有历史数据时不过滤
            
            # 转换为DataFrame
            df = pd.DataFrame(historical_data)
            if df.empty:
                return True
            
            current_price = stock_data.get('basic_info', {}).get('current_price', 0)
            if current_price <= 0:
                return False
            
            # 检查趋势
            if 'SMA_20' in df.columns and 'SMA_50' in df.columns:
                sma_20 = df['SMA_20'].iloc[-1] if not pd.isna(df['SMA_20'].iloc[-1]) else current_price
                sma_50 = df['SMA_50'].iloc[-1] if not pd.isna(df['SMA_50'].iloc[-1]) else current_price
                
                # 避免强烈下跌趋势
                if current_price < sma_20 * 0.9 and sma_20 < sma_50 * 0.95:
                    return False
            
            # 检查波动率
            if 'Volatility' in df.columns:
                current_volatility = df['Volatility'].iloc[-1] if not pd.isna(df['Volatility'].iloc[-1]) else 0
                
                # 避免极高波动率
                if current_volatility > 1.0:  # 100%年化波动率
                    return False
                
                # 避免极低波动率
                if current_volatility < 0.1:  # 10%年化波动率
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in technical analysis filter: {e}")
            return True
    
    @staticmethod
    def format_screening_results(opportunities: List[Dict]) -> pd.DataFrame:
        """格式化筛选结果为DataFrame"""
        try:
            results = []
            
            for opp in opportunities:
                # 财报警告
                earnings_risk = opp.get('earnings_risk', False)
                days_to_earn = opp.get('days_to_earnings')
                if earnings_risk:
                    earnings_label = f"⚠️ {days_to_earn}天" if days_to_earn is not None else "⚠️"
                elif days_to_earn is not None:
                    earnings_label = f"{days_to_earn}天"
                else:
                    earnings_label = "-"

                result = {
                    'Symbol': opp.get('symbol', ''),
                    'Strategy': opp.get('strategy_type', ''),
                    'Strike': opp.get('strike', 0),
                    'Expiry': opp.get('expiry_date', ''),
                    'DTE': opp.get('days_to_expiry', 0),
                    'Earnings': earnings_label,
                    'Premium': opp.get('returns', {}).get('max_profit', 0),
                    'Annualized_Return': f"{opp.get('returns', {}).get('annualized_yield', 0):.1f}%",
                    'Profit_Prob': f"{opp.get('probabilities', {}).get('prob_profit_short', 0):.1f}%",
                    'Delta': f"{opp.get('greeks', {}).get('delta', 0):.3f}",
                    'Theta': f"{opp.get('greeks', {}).get('theta', 0):.3f}",
                    'IV': f"{opp.get('option_details', {}).get('basic_info', {}).get('implied_volatility', 0):.1f}%",
                    'Volume': opp.get('option_details', {}).get('liquidity', {}).get('volume', 0),
                    'OI': opp.get('option_details', {}).get('liquidity', {}).get('open_interest', 0),
                    'Score': f"{opp.get('score', 0):.1f}"
                }
                results.append(result)
            
            return pd.DataFrame(results)
            
        except Exception as e:
            logger.error(f"Error formatting results: {e}")
            return pd.DataFrame()

class PresetScreens:
    """预设筛选条件"""
    
    @staticmethod
    def conservative_income() -> Dict:
        """保守收入型筛选"""
        return {
            'min_delta': 0.15,
            'max_delta': 0.3,
            'min_profit_probability': 70,
            'min_annualized_return': 8,
            'max_risk_reward_ratio': 3,
            'min_open_interest': 200,
            'min_volume': 100,
            'max_bid_ask_spread_pct': 10
        }
    
    @staticmethod
    def aggressive_income() -> Dict:
        """激进收入型筛选"""
        return {
            'min_delta': 0.2,
            'max_delta': 0.45,
            'min_profit_probability': 50,
            'min_annualized_return': 15,
            'max_risk_reward_ratio': 4,
            'min_open_interest': 100,
            'min_volume': 50,
            'max_bid_ask_spread_pct': 15
        }
    
    @staticmethod
    def high_probability() -> Dict:
        """高概率筛选"""
        return {
            'min_delta': 0.1,
            'max_delta': 0.25,
            'min_profit_probability': 75,
            'min_annualized_return': 6,
            'max_risk_reward_ratio': 2.5,
            'min_open_interest': 300,
            'min_volume': 150,
            'max_bid_ask_spread_pct': 8
        }
    
    @staticmethod
    def earnings_plays() -> Dict:
        """财报期筛选"""
        return {
            'min_delta': 0.15,
            'max_delta': 0.35,
            'min_profit_probability': 60,
            'min_annualized_return': 20,
            'max_days_to_expiry': 14,
            'min_iv_rank': 60,
            'min_open_interest': 500,
            'min_volume': 200
        }