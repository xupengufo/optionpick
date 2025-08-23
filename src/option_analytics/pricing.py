"""
期权定价和Greeks计算
Option pricing and Greeks calculation using Black-Scholes model
"""
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq
import math
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class BlackScholesCalculator:
    """Black-Scholes期权定价计算器"""
    
    @staticmethod
    def calculate_d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> Tuple[float, float]:
        """计算d1和d2值"""
        if T <= 0 or sigma <= 0:
            return 0, 0
            
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return d1, d2
    
    @classmethod
    def option_price(cls, S: float, K: float, T: float, r: float, sigma: float, 
                    option_type: str = 'call') -> float:
        """计算期权理论价格"""
        if T <= 0:
            if option_type.lower() == 'call':
                return max(S - K, 0)
            else:
                return max(K - S, 0)
        
        try:
            d1, d2 = cls.calculate_d1_d2(S, K, T, r, sigma)
            
            if option_type.lower() == 'call':
                price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            else:  # put
                price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            
            return max(price, 0)
            
        except Exception as e:
            logger.error(f"Error calculating option price: {e}")
            return 0
    
    @classmethod
    def calculate_greeks(cls, S: float, K: float, T: float, r: float, sigma: float, 
                        option_type: str = 'call') -> Dict[str, float]:
        """计算期权Greeks"""
        if T <= 0:
            return {
                'delta': 1.0 if (option_type.lower() == 'call' and S > K) else 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0
            }
        
        try:
            d1, d2 = cls.calculate_d1_d2(S, K, T, r, sigma)
            sqrt_T = np.sqrt(T)
            
            # Delta
            if option_type.lower() == 'call':
                delta = norm.cdf(d1)
            else:
                delta = -norm.cdf(-d1)
            
            # Gamma (相同对于call和put)
            gamma = norm.pdf(d1) / (S * sigma * sqrt_T)
            
            # Theta
            theta_part1 = -(S * norm.pdf(d1) * sigma) / (2 * sqrt_T)
            if option_type.lower() == 'call':
                theta_part2 = -r * K * np.exp(-r * T) * norm.cdf(d2)
                theta = (theta_part1 + theta_part2) / 365  # 转换为每日
            else:
                theta_part2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
                theta = (theta_part1 + theta_part2) / 365  # 转换为每日
            
            # Vega (相同对于call和put)
            vega = S * norm.pdf(d1) * sqrt_T / 100  # 除以100，转换为百分比变化
            
            # Rho
            if option_type.lower() == 'call':
                rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
            else:
                rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
            
            return {
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega,
                'rho': rho
            }
            
        except Exception as e:
            logger.error(f"Error calculating Greeks: {e}")
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0
            }
    
    @classmethod
    def implied_volatility(cls, market_price: float, S: float, K: float, T: float, 
                          r: float, option_type: str = 'call') -> float:
        """计算隐含波动率"""
        if T <= 0 or market_price <= 0:
            return 0
        
        try:
            def objective_function(sigma):
                return cls.option_price(S, K, T, r, sigma, option_type) - market_price
            
            # 使用Brent方法求解
            iv = brentq(objective_function, 0.001, 5.0, xtol=1e-6)
            return iv
            
        except Exception as e:
            logger.warning(f"Could not calculate implied volatility: {e}")
            return 0

class ProbabilityCalculator:
    """概率计算器"""
    
    @staticmethod
    def prob_profit_short_option(S: float, K: float, premium: float, T: float, 
                                sigma: float, option_type: str = 'call') -> float:
        """计算卖出期权的盈利概率"""
        try:
            if option_type.lower() == 'call':
                # 对于卖出看涨期权，盈利当股价低于执行价+权利金
                breakeven = K + premium
                # 计算股价低于breakeven的概率
                d = (np.log(S / breakeven) + (0.0 - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
                prob = norm.cdf(d)
            else:
                # 对于卖出看跌期权，盈利当股价高于执行价-权利金
                breakeven = K - premium
                # 计算股价高于breakeven的概率
                d = (np.log(S / breakeven) + (0.0 - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
                prob = 1 - norm.cdf(d)
            
            return max(0, min(1, prob))
            
        except Exception as e:
            logger.error(f"Error calculating profit probability: {e}")
            return 0
    
    @staticmethod
    def prob_expire_worthless(S: float, K: float, T: float, sigma: float, 
                             option_type: str = 'call') -> float:
        """计算期权到期价值为零的概率"""
        try:
            if option_type.lower() == 'call':
                # 看涨期权价值为零当股价低于执行价
                d = (np.log(S / K) + (0.0 - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
                prob = norm.cdf(d)
            else:
                # 看跌期权价值为零当股价高于执行价
                d = (np.log(S / K) + (0.0 - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
                prob = 1 - norm.cdf(d)
            
            return max(0, min(1, prob))
            
        except Exception as e:
            logger.error(f"Error calculating expiration probability: {e}")
            return 0
    
    @staticmethod
    def expected_move(S: float, T: float, sigma: float) -> Tuple[float, float]:
        """计算期权到期时的预期移动范围（1标准差）"""
        try:
            move = S * sigma * np.sqrt(T)
            return S - move, S + move
        except Exception as e:
            logger.error(f"Error calculating expected move: {e}")
            return S, S

class OptionAnalyzer:
    """期权分析器"""
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
        self.bs_calc = BlackScholesCalculator()
        self.prob_calc = ProbabilityCalculator()
    
    def analyze_option(self, option_data: Dict, stock_price: float, 
                      days_to_expiry: int) -> Dict:
        """分析单个期权"""
        try:
            # 提取期权数据
            strike = option_data['strike']
            market_price = option_data.get('lastPrice', 0)
            bid = option_data.get('bid', 0)
            ask = option_data.get('ask', 0)
            iv = option_data.get('impliedVolatility', 0)
            volume = option_data.get('volume', 0)
            open_interest = option_data.get('openInterest', 0)
            option_type = option_data.get('type', 'call')
            
            # 时间到期（年）
            T = days_to_expiry / 365.0
            
            # 计算中间价
            mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else market_price
            
            # 计算理论价格和Greeks
            theoretical_price = self.bs_calc.option_price(
                stock_price, strike, T, self.risk_free_rate, iv, option_type
            )
            
            greeks = self.bs_calc.calculate_greeks(
                stock_price, strike, T, self.risk_free_rate, iv, option_type
            )
            
            # 计算概率
            prob_profit = self.prob_calc.prob_profit_short_option(
                stock_price, strike, mid_price, T, iv, option_type
            )
            
            prob_expire_worthless = self.prob_calc.prob_expire_worthless(
                stock_price, strike, T, iv, option_type
            )
            
            # 计算预期移动
            expected_move_down, expected_move_up = self.prob_calc.expected_move(
                stock_price, T, iv
            )
            
            # 计算一些关键指标
            moneyness = stock_price / strike if option_type == 'call' else strike / stock_price
            time_value = mid_price - max(0, stock_price - strike if option_type == 'call' else strike - stock_price)
            
            # 年化收益率（基于mid_price）
            if mid_price > 0:
                annualized_return = (mid_price / strike) * (365 / days_to_expiry) * 100
            else:
                annualized_return = 0
            
            return {
                'basic_info': {
                    'strike': strike,
                    'type': option_type,
                    'days_to_expiry': days_to_expiry,
                    'market_price': market_price,
                    'bid': bid,
                    'ask': ask,
                    'mid_price': mid_price,
                    'volume': volume,
                    'open_interest': open_interest,
                    'implied_volatility': iv * 100,  # 转换为百分比
                },
                'pricing': {
                    'theoretical_price': theoretical_price,
                    'intrinsic_value': max(0, stock_price - strike if option_type == 'call' else strike - stock_price),
                    'time_value': time_value,
                    'moneyness': moneyness,
                },
                'greeks': greeks,
                'probabilities': {
                    'prob_profit_short': prob_profit * 100,  # 转换为百分比
                    'prob_expire_worthless': prob_expire_worthless * 100,
                    'expected_move_down': expected_move_down,
                    'expected_move_up': expected_move_up,
                },
                'returns': {
                    'max_profit': mid_price,
                    'max_loss': float('inf') if option_type == 'call' else strike - mid_price,
                    'breakeven': strike + mid_price if option_type == 'call' else strike - mid_price,
                    'annualized_return': annualized_return,
                },
                'liquidity': {
                    'bid_ask_spread': ask - bid if ask > bid else 0,
                    'bid_ask_spread_pct': ((ask - bid) / mid_price * 100) if mid_price > 0 else 0,
                    'volume': volume,
                    'open_interest': open_interest,
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing option: {e}")
            return {}
    
    def analyze_options_chain(self, options_data: Dict, stock_price: float, 
                            days_to_expiry: int) -> Dict:
        """分析整个期权链"""
        try:
            calls_analysis = []
            puts_analysis = []
            
            # 分析看涨期权
            for call_data in options_data.get('calls', []):
                analysis = self.analyze_option(call_data, stock_price, days_to_expiry)
                if analysis:
                    calls_analysis.append(analysis)
            
            # 分析看跌期权
            for put_data in options_data.get('puts', []):
                analysis = self.analyze_option(put_data, stock_price, days_to_expiry)
                if analysis:
                    puts_analysis.append(analysis)
            
            return {
                'symbol': options_data.get('symbol', ''),
                'expiry_date': options_data.get('expiry_date', ''),
                'stock_price': stock_price,
                'days_to_expiry': days_to_expiry,
                'calls': calls_analysis,
                'puts': puts_analysis,
                'analysis_timestamp': pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing options chain: {e}")
            return {}