"""
数据收集器主接口
Main interface for data collection
"""
from .base import StockDataCollector, OptionsDataCollector, MarketDataCollector
from typing import Dict, List, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataManager:
    """数据管理器 - 统一数据收集接口"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.stock_collector = StockDataCollector(cache_dir)
        self.options_collector = OptionsDataCollector(cache_dir)
        self.market_collector = MarketDataCollector(cache_dir)
    
    def get_complete_stock_data(self, symbol: str) -> Dict:
        """获取完整的股票数据"""
        try:
            # 获取基本信息
            stock_info = self.stock_collector.get_stock_info(symbol)
            
            # 获取历史数据
            historical_data = self.stock_collector.get_historical_data(symbol)
            
            # 计算当前波动率
            current_volatility = 0
            if not historical_data.empty and 'Volatility' in historical_data.columns:
                current_volatility = historical_data['Volatility'].iloc[-1]
            
            # 获取所有期权到期日
            expirations = self.options_collector.get_all_expirations(symbol)
            
            return {
                'basic_info': stock_info,
                'current_volatility': current_volatility,
                'expirations': expirations,
                'historical_data': historical_data.to_dict() if not historical_data.empty else {},
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting complete stock data for {symbol}: {e}")
            return {}
    
    def get_trading_opportunities(self, symbols: List[str], 
                                target_dte_range: Tuple[int, int] = (14, 45)) -> Dict:
        """获取交易机会数据"""
        opportunities = {}
        min_dte, max_dte = target_dte_range
        
        for symbol in symbols:
            try:
                logger.info(f"Analyzing {symbol}...")
                
                # 获取股票基本数据
                stock_data = self.get_complete_stock_data(symbol)
                if not stock_data:
                    continue
                
                symbol_opportunities = []
                
                # 分析每个到期日
                for expiry in stock_data.get('expirations', []):
                    try:
                        # 计算到期天数
                        expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
                        days_to_expiry = (expiry_date - datetime.now()).days
                        
                        # 只分析目标到期时间范围内的期权
                        if min_dte <= days_to_expiry <= max_dte:
                            options_data = self.options_collector.get_options_chain(symbol, expiry)
                            
                            if options_data:
                                # 筛选流动性好的期权
                                liquid_options = self.options_collector.filter_liquid_options(options_data)
                                
                                if liquid_options and (liquid_options['calls'] or liquid_options['puts']):
                                    symbol_opportunities.append({
                                        'expiry_date': expiry,
                                        'days_to_expiry': days_to_expiry,
                                        'options_data': liquid_options
                                    })
                    
                    except Exception as e:
                        logger.warning(f"Error processing expiry {expiry} for {symbol}: {e}")
                        continue
                
                if symbol_opportunities:
                    opportunities[symbol] = {
                        'stock_data': stock_data,
                        'opportunities': symbol_opportunities
                    }
                    
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        return opportunities
    
    def get_market_context(self) -> Dict:
        """获取市场环境数据"""
        try:
            market_sentiment = self.market_collector.get_market_sentiment()
            
            # 添加市场环境评估
            vix_level = market_sentiment.get('vix', 20)
            
            if vix_level < 15:
                market_regime = "低波动率"
                selling_attractiveness = "中等"
            elif vix_level < 25:
                market_regime = "正常波动率"
                selling_attractiveness = "良好"
            elif vix_level < 35:
                market_regime = "高波动率"
                selling_attractiveness = "很好"
            else:
                market_regime = "极高波动率"
                selling_attractiveness = "需谨慎"
            
            market_sentiment.update({
                'market_regime': market_regime,
                'selling_attractiveness': selling_attractiveness,
                'vix_level': vix_level
            })
            
            return market_sentiment
            
        except Exception as e:
            logger.error(f"Error getting market context: {e}")
            return {}
    
    def validate_symbol(self, symbol: str) -> bool:
        """验证股票代码是否有效"""
        try:
            stock_info = self.stock_collector.get_stock_info(symbol)
            return bool(stock_info and stock_info.get('current_price', 0) > 0)
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")
            return False
    
    def get_popular_symbols(self) -> List[str]:
        """获取热门股票代码列表"""
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", 
            "SPY", "QQQ", "IWM", "XLF", "XLE", "XLK", "GLD", "SLV"
        ]