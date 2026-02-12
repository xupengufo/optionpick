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

            call_greeks = call_analysis.get('greeks', {})
            put_greeks = put_analysis.get('greeks', {})
            net_greeks = {
                'delta': call_greeks.get('delta', 0) + put_greeks.get('delta', 0),
                'gamma': call_greeks.get('gamma', 0) + put_greeks.get('gamma', 0),
                'theta': call_greeks.get('theta', 0) + put_greeks.get('theta', 0),
                'vega': call_greeks.get('vega', 0) + put_greeks.get('vega', 0),
                'rho': call_greeks.get('rho', 0) + put_greeks.get('rho', 0),
            }

            call_liq = call_analysis.get('liquidity', {})
            put_liq = put_analysis.get('liquidity', {})
            combined_mid = (call_analysis.get('basic_info', {}).get('mid_price', 0) +
                            put_analysis.get('basic_info', {}).get('mid_price', 0))
            combined_spread = (call_liq.get('bid_ask_spread', 0) +
                               put_liq.get('bid_ask_spread', 0))
            combined_liquidity = {
                'bid_ask_spread': combined_spread,
                'bid_ask_spread_pct': ((combined_spread / combined_mid) * 100)
                if combined_mid > 0 else 0,
                # 双腿组合的可成交量受较弱一腿约束
                'volume': min(call_liq.get('volume', 0), put_liq.get('volume', 0)),
                'open_interest': min(call_liq.get('open_interest', 0),
                                     put_liq.get('open_interest', 0)),
            }
            
            return {
                'strategy_type': 'short_strangle',
                'stock_price': stock_price,
                'strike': put_strike,
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
                'probabilities': {
                    'prob_profit_short': profit_prob,
                },
                'greeks': net_greeks,
                'option_details': {
                    'basic_info': {
                        'implied_volatility': current_iv,
                        'put_strike': put_strike,
                        'call_strike': call_strike,
                    },
                    'liquidity': combined_liquidity,
                },
                'risk_metrics': {
                    'expected_move': expected_move,
                    'current_iv': current_iv,
                    'delta_neutral': abs(net_greeks['delta']) < 0.1
                },
                'days_to_expiry': days_to_expiry
            }
            
        except Exception as e:
            logger.error(f"Error analyzing short strangle: {e}")
            return {}
    
    def analyze_bull_put_spread(self, stock_price: float, put_short_data: Dict,
                                put_long_data: Dict, days_to_expiry: int) -> Dict:
        """分析牛市看跌价差策略 (Bull Put Spread)
        卖出较高 Strike Put + 买入较低 Strike Put"""
        try:
            short_analysis = self.option_analyzer.analyze_option(
                put_short_data, stock_price, days_to_expiry)
            long_analysis = self.option_analyzer.analyze_option(
                put_long_data, stock_price, days_to_expiry)
            
            if not all([short_analysis, long_analysis]):
                return {}
            
            short_strike = put_short_data['strike']
            long_strike = put_long_data['strike']
            
            if short_strike <= long_strike:
                return {}  # short strike 必须高于 long strike
            
            short_premium = short_analysis['basic_info']['mid_price']
            long_premium = long_analysis['basic_info']['mid_price']
            
            net_credit = (short_premium - long_premium) * 100
            spread_width = (short_strike - long_strike) * 100
            max_profit = net_credit
            max_loss = spread_width - net_credit
            breakeven = short_strike - (net_credit / 100)
            
            # 收益率 (基于最大风险)
            if max_loss > 0:
                return_on_risk = (max_profit / max_loss) * 100
                annualized_yield = return_on_risk * (365 / days_to_expiry)
            else:
                return_on_risk = 0
                annualized_yield = 0
            
            # 盈利概率估算
            current_iv = short_analysis['basic_info'].get('implied_volatility', 30)
            expected_move = stock_price * (current_iv / 100) * np.sqrt(days_to_expiry / 365)
            distance = stock_price - breakeven
            if expected_move > 0:
                profit_prob = min(95, max(5, 50 + (distance / expected_move) * 30))
            else:
                profit_prob = 50
            
            return {
                'strategy_type': 'bull_put_spread',
                'stock_price': stock_price,
                'strike': short_strike,  # 主 Strike 用于显示
                'strikes': {
                    'put_short': short_strike,
                    'put_long': long_strike,
                },
                'premium': net_credit / 100,
                'returns': {
                    'net_credit': net_credit,
                    'max_profit': max_profit,
                    'max_loss': max_loss,
                    'breakeven': breakeven,
                    'return_on_risk': return_on_risk,
                    'annualized_yield': annualized_yield,
                    'spread_width': spread_width,
                    'profit_probability': profit_prob,
                },
                'probabilities': {
                    'prob_profit_short': profit_prob,
                },
                'greeks': short_analysis['greeks'],
                'option_details': short_analysis,
                'days_to_expiry': days_to_expiry,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing bull put spread: {e}")
            return {}
    
    def analyze_bear_call_spread(self, stock_price: float, call_short_data: Dict,
                                  call_long_data: Dict, days_to_expiry: int) -> Dict:
        """分析熊市看涨价差策略 (Bear Call Spread)
        卖出较低 Strike Call + 买入较高 Strike Call"""
        try:
            short_analysis = self.option_analyzer.analyze_option(
                call_short_data, stock_price, days_to_expiry)
            long_analysis = self.option_analyzer.analyze_option(
                call_long_data, stock_price, days_to_expiry)
            
            if not all([short_analysis, long_analysis]):
                return {}
            
            short_strike = call_short_data['strike']
            long_strike = call_long_data['strike']
            
            if long_strike <= short_strike:
                return {}  # long strike 必须高于 short strike
            
            short_premium = short_analysis['basic_info']['mid_price']
            long_premium = long_analysis['basic_info']['mid_price']
            
            net_credit = (short_premium - long_premium) * 100
            spread_width = (long_strike - short_strike) * 100
            max_profit = net_credit
            max_loss = spread_width - net_credit
            breakeven = short_strike + (net_credit / 100)
            
            if max_loss > 0:
                return_on_risk = (max_profit / max_loss) * 100
                annualized_yield = return_on_risk * (365 / days_to_expiry)
            else:
                return_on_risk = 0
                annualized_yield = 0
            
            current_iv = short_analysis['basic_info'].get('implied_volatility', 30)
            expected_move = stock_price * (current_iv / 100) * np.sqrt(days_to_expiry / 365)
            distance = breakeven - stock_price
            if expected_move > 0:
                profit_prob = min(95, max(5, 50 + (distance / expected_move) * 30))
            else:
                profit_prob = 50
            
            return {
                'strategy_type': 'bear_call_spread',
                'stock_price': stock_price,
                'strike': short_strike,
                'strikes': {
                    'call_short': short_strike,
                    'call_long': long_strike,
                },
                'premium': net_credit / 100,
                'returns': {
                    'net_credit': net_credit,
                    'max_profit': max_profit,
                    'max_loss': max_loss,
                    'breakeven': breakeven,
                    'return_on_risk': return_on_risk,
                    'annualized_yield': annualized_yield,
                    'spread_width': spread_width,
                    'profit_probability': profit_prob,
                },
                'probabilities': {
                    'prob_profit_short': profit_prob,
                },
                'greeks': short_analysis['greeks'],
                'option_details': short_analysis,
                'days_to_expiry': days_to_expiry,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing bear call spread: {e}")
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
