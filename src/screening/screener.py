"""
期权筛选引擎
Options screening engine for finding optimal selling opportunities
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta

from ..data_collector.data_manager import DataManager
from ..option_analytics.strategies import StrategyAnalyzer
from ..option_analytics.pricing import OptionAnalyzer

logger = logging.getLogger(__name__)

class OptionsScreener:
    """期权筛选器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.data_manager = DataManager()
        self.strategy_analyzer = StrategyAnalyzer()
        self.option_analyzer = OptionAnalyzer()
    
    def _default_config(self) -> Dict:
        """默认筛选配置"""
        return {
            'min_days_to_expiry': 7,
            'max_days_to_expiry': 60,
            'min_open_interest': 100,
            'min_volume': 50,
            'min_delta': 0.1,
            'max_delta': 0.5,
            'min_iv_rank': 20,
            'min_bid_ask_spread_pct': 0,
            'max_bid_ask_spread_pct': 15,
            'min_stock_price': 10,
            'max_stock_price': 500,
            'target_strategies': ['covered_call', 'cash_secured_put', 'short_strangle'],
            'max_results_per_symbol': 5
        }
    
    def screen_covered_calls(self, symbols: List[str]) -> List[Dict]:
        """筛选备兑看涨期权机会"""
        opportunities = []
        
        for symbol in symbols:
            try:
                logger.info(f"Screening covered calls for {symbol}")
                
                # 获取股票和期权数据
                trading_data = self.data_manager.get_trading_opportunities([symbol])
                if symbol not in trading_data:
                    continue
                
                stock_data = trading_data[symbol]['stock_data']
                stock_price = stock_data['basic_info'].get('current_price', 0)
                
                if not self._validate_stock_price(stock_price):
                    continue
                
                symbol_opportunities = []
                
                for opp in trading_data[symbol]['opportunities']:
                    days_to_expiry = opp['days_to_expiry']
                    
                    if not self._validate_expiry(days_to_expiry):
                        continue
                    
                    # 筛选看涨期权
                    for call_data in opp['options_data']['calls']:
                        if self._validate_option_liquidity(call_data):
                            # 分析备兑看涨策略
                            strategy_analysis = self.strategy_analyzer.analyze_covered_call(
                                stock_price, call_data, days_to_expiry
                            )
                            
                            if strategy_analysis and self._validate_covered_call(strategy_analysis):
                                strategy_analysis['symbol'] = symbol
                                strategy_analysis['expiry_date'] = opp['expiry_date']
                                symbol_opportunities.append(strategy_analysis)
                
                # 按得分排序并限制数量
                if symbol_opportunities:
                    ranked_opportunities = self.strategy_analyzer.rank_selling_opportunities(symbol_opportunities)
                    opportunities.extend(ranked_opportunities[:self.config['max_results_per_symbol']])
                    
            except Exception as e:
                logger.error(f"Error screening covered calls for {symbol}: {e}")
                continue
        
        return opportunities
    
    def screen_cash_secured_puts(self, symbols: List[str]) -> List[Dict]:
        """筛选现金担保看跌期权机会"""
        opportunities = []
        
        for symbol in symbols:
            try:
                logger.info(f"Screening cash secured puts for {symbol}")
                
                # 获取股票和期权数据
                trading_data = self.data_manager.get_trading_opportunities([symbol])
                if symbol not in trading_data:
                    continue
                
                stock_data = trading_data[symbol]['stock_data']
                stock_price = stock_data['basic_info'].get('current_price', 0)
                
                if not self._validate_stock_price(stock_price):
                    continue
                
                symbol_opportunities = []
                
                for opp in trading_data[symbol]['opportunities']:
                    days_to_expiry = opp['days_to_expiry']
                    
                    if not self._validate_expiry(days_to_expiry):
                        continue
                    
                    # 筛选看跌期权
                    for put_data in opp['options_data']['puts']:
                        if self._validate_option_liquidity(put_data):
                            # 分析现金担保看跌策略
                            strategy_analysis = self.strategy_analyzer.analyze_cash_secured_put(
                                stock_price, put_data, days_to_expiry
                            )
                            
                            if strategy_analysis and self._validate_cash_secured_put(strategy_analysis):
                                strategy_analysis['symbol'] = symbol
                                strategy_analysis['expiry_date'] = opp['expiry_date']
                                symbol_opportunities.append(strategy_analysis)
                
                # 按得分排序并限制数量
                if symbol_opportunities:
                    ranked_opportunities = self.strategy_analyzer.rank_selling_opportunities(symbol_opportunities)
                    opportunities.extend(ranked_opportunities[:self.config['max_results_per_symbol']])
                    
            except Exception as e:
                logger.error(f"Error screening cash secured puts for {symbol}: {e}")
                continue
        
        return opportunities
    
    def screen_short_strangles(self, symbols: List[str]) -> List[Dict]:
        """筛选卖出宽跨式期权机会"""
        opportunities = []
        
        for symbol in symbols:
            try:
                logger.info(f"Screening short strangles for {symbol}")
                
                trading_data = self.data_manager.get_trading_opportunities([symbol])
                if symbol not in trading_data:
                    continue
                
                stock_data = trading_data[symbol]['stock_data']
                stock_price = stock_data['basic_info'].get('current_price', 0)
                
                if not self._validate_stock_price(stock_price):
                    continue
                
                symbol_opportunities = []
                
                for opp in trading_data[symbol]['opportunities']:
                    days_to_expiry = opp['days_to_expiry']
                    
                    if not self._validate_expiry(days_to_expiry):
                        continue
                    
                    calls = opp['options_data']['calls']
                    puts = opp['options_data']['puts']
                    
                    # 寻找合适的看涨和看跌期权组合
                    for call_data in calls:
                        for put_data in puts:
                            if (self._validate_option_liquidity(call_data) and 
                                self._validate_option_liquidity(put_data) and
                                call_data['strike'] > stock_price and
                                put_data['strike'] < stock_price):
                                
                                # 分析宽跨式策略
                                strategy_analysis = self.strategy_analyzer.analyze_short_strangle(
                                    stock_price, call_data, put_data, days_to_expiry
                                )
                                
                                if strategy_analysis and self._validate_short_strangle(strategy_analysis):
                                    strategy_analysis['symbol'] = symbol
                                    strategy_analysis['expiry_date'] = opp['expiry_date']
                                    symbol_opportunities.append(strategy_analysis)
                
                # 按得分排序并限制数量
                if symbol_opportunities:
                    # 去重 - 相同strike组合只保留一个
                    unique_opportunities = self._deduplicate_strangles(symbol_opportunities)
                    ranked_opportunities = self.strategy_analyzer.rank_selling_opportunities(unique_opportunities)
                    opportunities.extend(ranked_opportunities[:self.config['max_results_per_symbol']])
                    
            except Exception as e:
                logger.error(f"Error screening short strangles for {symbol}: {e}")
                continue
        
        return opportunities
    
    def screen_all_strategies(self, symbols: List[str]) -> Dict[str, List[Dict]]:
        """筛选所有策略"""
        results = {}
        
        if 'covered_call' in self.config['target_strategies']:
            results['covered_calls'] = self.screen_covered_calls(symbols)
        
        if 'cash_secured_put' in self.config['target_strategies']:
            results['cash_secured_puts'] = self.screen_cash_secured_puts(symbols)
        
        if 'short_strangle' in self.config['target_strategies']:
            results['short_strangles'] = self.screen_short_strangles(symbols)
        
        return results
    
    def get_top_opportunities(self, symbols: List[str], max_results: int = 20) -> List[Dict]:
        """获取最佳机会"""
        all_strategies = self.screen_all_strategies(symbols)
        
        # 合并所有策略的结果
        all_opportunities = []
        for strategy_type, opportunities in all_strategies.items():
            for opp in opportunities:
                opp['strategy_category'] = strategy_type
                all_opportunities.append(opp)
        
        # 按得分排序
        all_opportunities.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return all_opportunities[:max_results]
    
    def _validate_stock_price(self, price: float) -> bool:
        """验证股票价格"""
        return self.config['min_stock_price'] <= price <= self.config['max_stock_price']
    
    def _validate_expiry(self, days_to_expiry: int) -> bool:
        """验证到期时间"""
        return self.config['min_days_to_expiry'] <= days_to_expiry <= self.config['max_days_to_expiry']
    
    def _validate_option_liquidity(self, option_data: Dict) -> bool:
        """验证期权流动性"""
        volume = option_data.get('volume', 0)
        open_interest = option_data.get('openInterest', 0)
        bid = option_data.get('bid', 0)
        ask = option_data.get('ask', 0)
        
        # 检查基本流动性要求
        if volume < self.config['min_volume'] or open_interest < self.config['min_open_interest']:
            return False
        
        # 检查买卖价差
        if bid > 0 and ask > bid:
            mid_price = (bid + ask) / 2
            spread_pct = ((ask - bid) / mid_price) * 100
            if spread_pct > self.config['max_bid_ask_spread_pct']:
                return False
        
        return True
    
    def _validate_covered_call(self, strategy_analysis: Dict) -> bool:
        """验证备兑看涨策略"""
        try:
            greeks = strategy_analysis.get('greeks', {})
            delta = abs(greeks.get('delta', 0))
            
            returns = strategy_analysis.get('returns', {})
            annualized_yield = returns.get('annualized_yield', 0)
            
            # Delta范围检查
            if not (self.config['min_delta'] <= delta <= self.config['max_delta']):
                return False
            
            # 年化收益率检查
            if annualized_yield <= 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_cash_secured_put(self, strategy_analysis: Dict) -> bool:
        """验证现金担保看跌策略"""
        try:
            greeks = strategy_analysis.get('greeks', {})
            delta = abs(greeks.get('delta', 0))
            
            returns = strategy_analysis.get('returns', {})
            annualized_yield = returns.get('annualized_yield', 0)
            
            # Delta范围检查
            if not (self.config['min_delta'] <= delta <= self.config['max_delta']):
                return False
            
            # 年化收益率检查
            if annualized_yield <= 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_short_strangle(self, strategy_analysis: Dict) -> bool:
        """验证宽跨式策略"""
        try:
            returns = strategy_analysis.get('returns', {})
            profit_prob = returns.get('profit_probability', 0)
            net_credit = returns.get('net_credit', 0)
            
            # 盈利概率和权利金检查
            if profit_prob < 30 or net_credit <= 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _deduplicate_strangles(self, opportunities: List[Dict]) -> List[Dict]:
        """去除重复的宽跨式组合"""
        seen_combinations = set()
        unique_opportunities = []
        
        for opp in opportunities:
            strikes = opp.get('strikes', {})
            combination = (strikes.get('put_strike', 0), strikes.get('call_strike', 0))
            
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                unique_opportunities.append(opp)
        
        return unique_opportunities