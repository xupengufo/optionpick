"""
期权策略分析模块
Option strategies analysis for selling opportunities
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from .pricing import OptionAnalyzer

logger = logging.getLogger(__name__)

class StrategyAnalyzer:
    """期权策略分析器"""
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.option_analyzer = OptionAnalyzer(risk_free_rate)
        
    def analyze_covered_call(self, stock_price: float, call_data: Dict, 
                           days_to_expiry: int, shares_owned: int = 100) -> Dict:
        """分析备兑看涨期权策略"""
        try:
            # 分析期权
            option_analysis = self.option_analyzer.analyze_option(
                call_data, stock_price, days_to_expiry
            )
            
            if not option_analysis:
                return {}
            
            strike = call_data['strike']
            premium = option_analysis['basic_info']['mid_price']
            
            # 计算策略指标
            max_profit = (strike - stock_price + premium) * shares_owned
            max_loss = stock_price * shares_owned  # 理论上无限制，但这里用当前股价作为参考
            breakeven = stock_price - premium
            
            # 收益率计算
            if stock_price > 0:
                yield_if_unchanged = (premium / stock_price) * 100
                yield_if_called = ((strike - stock_price + premium) / stock_price) * 100
                annualized_yield = yield_if_called * (365 / days_to_expiry)
            else:
                yield_if_unchanged = 0
                yield_if_called = 0
                annualized_yield = 0
            
            # 保护程度
            downside_protection = (premium / stock_price) * 100 if stock_price > 0 else 0
            
            return {
                'strategy_type': 'covered_call',
                'stock_price': stock_price,
                'strike': strike,
                'premium': premium,
                'shares': shares_owned,
                'returns': {
                    'max_profit': max_profit,
                    'max_loss': max_loss,
                    'breakeven': breakeven,
                    'yield_if_unchanged': yield_if_unchanged,
                    'yield_if_called': yield_if_called,
                    'annualized_yield': annualized_yield,
                    'downside_protection': downside_protection,
                },
                'probabilities': option_analysis['probabilities'],
                'greeks': option_analysis['greeks'],
                'option_details': option_analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing covered call: {e}")
            return {}
    
    def analyze_cash_secured_put(self, stock_price: float, put_data: Dict, 
                               days_to_expiry: int) -> Dict:
        """分析现金担保看跌期权策略"""
        try:
            # 分析期权
            option_analysis = self.option_analyzer.analyze_option(
                put_data, stock_price, days_to_expiry
            )
            
            if not option_analysis:
                return {}
            
            strike = put_data['strike']
            premium = option_analysis['basic_info']['mid_price']
            
            # 计算策略指标
            max_profit = premium * 100  # 假设1个合约
            max_loss = (strike - premium) * 100
            breakeven = strike - premium
            
            # 收益率计算
            cash_required = strike * 100  # 需要的现金
            if cash_required > 0:
                yield_on_cash = (premium * 100 / cash_required) * 100
                annualized_yield = yield_on_cash * (365 / days_to_expiry)
            else:
                yield_on_cash = 0
                annualized_yield = 0
            
            # 如果被行权，实际购买成本
            net_cost_if_assigned = strike - premium
            discount_to_current = ((stock_price - net_cost_if_assigned) / stock_price) * 100 if stock_price > 0 else 0
            
            return {
                'strategy_type': 'cash_secured_put',
                'stock_price': stock_price,
                'strike': strike,
                'premium': premium,
                'cash_required': cash_required,
                'returns': {
                    'max_profit': max_profit,
                    'max_loss': max_loss,
                    'breakeven': breakeven,
                    'yield_on_cash': yield_on_cash,
                    'annualized_yield': annualized_yield,
                    'net_cost_if_assigned': net_cost_if_assigned,
                    'discount_to_current': discount_to_current,
                },
                'probabilities': option_analysis['probabilities'],
                'greeks': option_analysis['greeks'],
                'option_details': option_analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing cash secured put: {e}")
            return {}
    
    def analyze_iron_condor(self, stock_price: float, call_short: Dict, call_long: Dict,
                          put_short: Dict, put_long: Dict, days_to_expiry: int) -> Dict:
        """分析铁鹰策略"""
        try:
            # 分析各个期权
            call_short_analysis = self.option_analyzer.analyze_option(call_short, stock_price, days_to_expiry)
            call_long_analysis = self.option_analyzer.analyze_option(call_long, stock_price, days_to_expiry)
            put_short_analysis = self.option_analyzer.analyze_option(put_short, stock_price, days_to_expiry)
            put_long_analysis = self.option_analyzer.analyze_option(put_long, stock_price, days_to_expiry)
            
            if not all([call_short_analysis, call_long_analysis, put_short_analysis, put_long_analysis]):
                return {}
            
            # 计算净权利金收入
            net_credit = (
                call_short_analysis['basic_info']['mid_price'] +
                put_short_analysis['basic_info']['mid_price'] -
                call_long_analysis['basic_info']['mid_price'] -
                put_long_analysis['basic_info']['mid_price']
            ) * 100
            
            # 计算收益范围
            put_strike_short = put_short['strike']
            call_strike_short = call_short['strike']
            
            lower_breakeven = put_strike_short - (net_credit / 100)
            upper_breakeven = call_strike_short + (net_credit / 100)
            
            # 计算最大收益和损失
            max_profit = net_credit
            wing_width = min(
                call_long['strike'] - call_short['strike'],
                put_short['strike'] - put_long['strike']
            )
            max_loss = (wing_width * 100) - net_credit
            
            # 盈利概率（股价在盈利区间的概率）
            profit_zone_width = upper_breakeven - lower_breakeven
            profit_prob = min(100, (profit_zone_width / stock_price) * 50)  # 简化计算
            
            return {
                'strategy_type': 'iron_condor',
                'stock_price': stock_price,
                'strikes': {
                    'put_long': put_long['strike'],
                    'put_short': put_short['strike'],
                    'call_short': call_short['strike'],
                    'call_long': call_long['strike']
                },
                'returns': {
                    'net_credit': net_credit,
                    'max_profit': max_profit,
                    'max_loss': max_loss,
                    'lower_breakeven': lower_breakeven,
                    'upper_breakeven': upper_breakeven,
                    'profit_zone_width': profit_zone_width,
                    'profit_probability': profit_prob,
                    'max_profit_pct': (max_profit / abs(max_loss)) * 100 if max_loss != 0 else 0
                },
                'wing_width': wing_width,
                'days_to_expiry': days_to_expiry
            }
            
        except Exception as e:
            logger.error(f"Error analyzing iron condor: {e}")
            return {}
    
    def analyze_short_strangle(self, stock_price: float, call_data: Dict, put_data: Dict,
                             days_to_expiry: int) -> Dict:
        """分析卖出宽跨式策略"""
        try:
            # 分析各个期权
            call_analysis = self.option_analyzer.analyze_option(call_data, stock_price, days_to_expiry)
            put_analysis = self.option_analyzer.analyze_option(put_data, stock_price, days_to_expiry)
            
            if not all([call_analysis, put_analysis]):
                return {}
            
            call_strike = call_data['strike']
            put_strike = put_data['strike']
            
            # 计算净权利金收入
            net_credit = (call_analysis['basic_info']['mid_price'] + 
                         put_analysis['basic_info']['mid_price']) * 100
            
            # 计算盈亏平衡点
            upper_breakeven = call_strike + (net_credit / 100)
            lower_breakeven = put_strike - (net_credit / 100)
            
            # 最大收益和理论最大损失
            max_profit = net_credit
            max_loss = float('inf')  # 理论上无限
            
            # 盈利区间
            profit_zone_width = upper_breakeven - lower_breakeven
            
            # 简化的盈利概率计算
            current_iv = (call_analysis['basic_info']['implied_volatility'] + 
                         put_analysis['basic_info']['implied_volatility']) / 2
            expected_move = stock_price * (current_iv / 100) * np.sqrt(days_to_expiry / 365)
            
            # 如果预期移动小于盈利区间，则盈利概率较高
            if expected_move > 0:
                profit_prob = min(100, (profit_zone_width / (2 * expected_move)) * 100)
            else:
                profit_prob = 50
            
            return {
                'strategy_type': 'short_strangle',
                'stock_price': stock_price,
                'strikes': {
                    'put_strike': put_strike,
                    'call_strike': call_strike
                },
                'returns': {
                    'net_credit': net_credit,
                    'max_profit': max_profit,
                    'max_loss': max_loss,
                    'upper_breakeven': upper_breakeven,
                    'lower_breakeven': lower_breakeven,
                    'profit_zone_width': profit_zone_width,
                    'profit_probability': profit_prob,
                    'annualized_yield': (net_credit / (stock_price * 100)) * (365 / days_to_expiry) * 100 if stock_price > 0 and days_to_expiry > 0 else 0,
                },
                'risk_metrics': {
                    'expected_move': expected_move,
                    'current_iv': current_iv,
                    'delta_neutral': abs(call_analysis['greeks']['delta'] + put_analysis['greeks']['delta']) < 0.1
                },
                'days_to_expiry': days_to_expiry
            }
            
        except Exception as e:
            logger.error(f"Error analyzing short strangle: {e}")
            return {}
    
    def rank_selling_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """对卖方机会进行排名"""
        try:
            scored_opportunities = []
            
            for opp in opportunities:
                score = 0
                
                # 根据不同指标计算得分
                if 'returns' in opp:
                    returns = opp['returns']
                    
                    # 年化收益率得分（0-30分）
                    annualized_return = returns.get('annualized_yield', 0)
                    if annualized_return > 0:
                        score += min(30, annualized_return * 2)
                    
                    # 盈利概率得分（0-25分）
                    if 'probabilities' in opp:
                        prob_profit = opp['probabilities'].get('prob_profit_short', 0)
                        score += min(25, prob_profit * 0.25)
                    
                    # 流动性得分（0-20分）
                    if 'option_details' in opp and 'liquidity' in opp['option_details']:
                        liquidity = opp['option_details']['liquidity']
                        volume = liquidity.get('volume', 0)
                        open_interest = liquidity.get('open_interest', 0)
                        bid_ask_spread_pct = liquidity.get('bid_ask_spread_pct', 100)
                        
                        # 成交量和持仓量得分
                        if volume >= 100 and open_interest >= 500:
                            score += 10
                        elif volume >= 50 and open_interest >= 200:
                            score += 5
                        
                        # 买卖价差得分
                        if bid_ask_spread_pct < 5:
                            score += 10
                        elif bid_ask_spread_pct < 10:
                            score += 5
                    
                    # 风险调整得分（0-15分）
                    max_loss = returns.get('max_loss', float('inf'))
                    max_profit = returns.get('max_profit', 0)
                    if max_loss != float('inf') and max_loss > 0:
                        risk_reward = max_profit / max_loss
                        score += min(15, risk_reward * 30)
                    
                    # Delta得分（0-10分）- 偏好适中的Delta值
                    if 'greeks' in opp:
                        delta = abs(opp['greeks'].get('delta', 0))
                        if 0.15 <= delta <= 0.35:
                            score += 10
                        elif 0.1 <= delta <= 0.5:
                            score += 5
                
                opp_with_score = opp.copy()
                opp_with_score['score'] = score
                scored_opportunities.append(opp_with_score)
            
            # 按得分降序排序
            scored_opportunities.sort(key=lambda x: x['score'], reverse=True)
            
            return scored_opportunities
            
        except Exception as e:
            logger.error(f"Error ranking opportunities: {e}")
            return opportunities