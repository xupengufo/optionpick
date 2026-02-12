"""
数据收集模块基础类
Base classes for data collection
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import json
import os
import glob
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCollector:
    """数据收集器基础类"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        self._memory_cache = {}
        os.makedirs(cache_dir, exist_ok=True)
        
    def _get_cache_path(self, symbol: str, data_type: str) -> str:
        """获取缓存文件路径"""
        date_str = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.cache_dir, f"{symbol}_{data_type}_{date_str}.json")
    
    def _load_from_cache(self, cache_path: str) -> Optional[Dict]:
        """从缓存加载数据"""
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return None
    
    def _save_to_cache(self, data: Dict, cache_path: str):
        """保存数据到缓存"""
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, default=str)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _load_latest_cache(self, symbol: str, data_type: str) -> Optional[Dict]:
        """回退加载最近可用缓存（跨日期）"""
        pattern = os.path.join(self.cache_dir, f"{symbol}_{data_type}_*.json")
        files = sorted(glob.glob(pattern), reverse=True)
        for path in files:
            data = self._load_from_cache(path)
            if data:
                return data
        return None

class StockDataCollector(DataCollector):
    """股票数据收集器"""
    
    def get_stock_info(self, symbol: str) -> Dict:
        """获取股票基本信息（带限流重试和缓存回退）"""
        memory_key = f"{symbol}_info"
        if memory_key in self._memory_cache:
            return self._memory_cache[memory_key]

        cache_path = self._get_cache_path(symbol, "info")
        cached_data = self._load_from_cache(cache_path)
        if cached_data:
            self._memory_cache[memory_key] = cached_data
            return cached_data

        last_error = None
        for attempt in range(3):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                current_price = info.get('regularMarketPrice', 0)
                if not current_price:
                    try:
                        fast_info = ticker.fast_info
                        current_price = fast_info.get('lastPrice', 0) or fast_info.get('last_price', 0)
                    except Exception:
                        pass

                # 提取关键信息
                stock_info = {
                    'symbol': symbol,
                    'company_name': info.get('longName', ''),
                    'current_price': current_price,
                    'market_cap': info.get('marketCap', 0),
                    'volume': info.get('volume', 0),
                    'avg_volume': info.get('averageVolume', 0),
                    'beta': info.get('beta', 0),
                    'pe_ratio': info.get('trailingPE', 0),
                    'dividend_yield': info.get('dividendYield', 0),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                    'timestamp': datetime.now().isoformat()
                }

                if stock_info.get('current_price', 0) > 0:
                    self._save_to_cache(stock_info, cache_path)
                    self._memory_cache[memory_key] = stock_info
                    return stock_info

            except Exception as e:
                last_error = e
                # 针对限流做退避
                if "Too Many Requests" in str(e) and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                else:
                    break

        fallback = self._load_latest_cache(symbol, "info")
        if fallback:
            logger.warning(f"Using stale cache for {symbol} due to upstream rate limit/error")
            self._memory_cache[memory_key] = fallback
            return fallback

        logger.error(f"Error fetching stock info for {symbol}: {last_error}")
        return {}
    
    def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """获取历史价格数据"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            # 计算技术指标
            hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
            hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
            hist['Volatility'] = hist['Close'].pct_change().rolling(window=20).std() * np.sqrt(252)
            
            return hist
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_implied_volatility_rank(self, symbol: str, current_iv: float) -> float:
        """计算隐含波动率排名"""
        try:
            # 获取历史波动率数据
            hist_data = self.get_historical_data(symbol, period="1y")
            if hist_data.empty:
                return 0
                
            hist_volatility = hist_data['Volatility'].dropna()
            if len(hist_volatility) == 0:
                return 0
                
            # 计算当前IV在历史波动率中的排名
            percentile = (hist_volatility < current_iv).sum() / len(hist_volatility) * 100
            return percentile
            
        except Exception as e:
            logger.error(f"Error calculating IV rank for {symbol}: {e}")
            return 0

class OptionsDataCollector(DataCollector):
    """期权数据收集器"""
    
    def get_options_chain(self, symbol: str, expiry_date: str = None) -> Dict:
        """获取期权链数据"""
        cache_path = self._get_cache_path(symbol, f"options_{expiry_date or 'all'}")
        cached_data = self._load_from_cache(cache_path)
        
        if cached_data:
            return cached_data
            
        try:
            ticker = yf.Ticker(symbol)
            
            # 获取所有到期日
            if expiry_date is None:
                expirations = ticker.options
                if not expirations:
                    return {}
                expiry_date = expirations[0]  # 使用最近的到期日
            
            # 获取期权链
            option_chain = ticker.option_chain(expiry_date)
            calls = option_chain.calls
            puts = option_chain.puts
            
            # 处理calls数据
            calls_data = []
            for _, row in calls.iterrows():
                calls_data.append({
                    'type': 'call',
                    'strike': row['strike'],
                    'lastPrice': row['lastPrice'],
                    'bid': row['bid'],
                    'ask': row['ask'],
                    'volume': row['volume'],
                    'openInterest': row['openInterest'],
                    'impliedVolatility': row['impliedVolatility'],
                    'inTheMoney': row['inTheMoney'],
                    'contractSymbol': row['contractSymbol']
                })
            
            # 处理puts数据
            puts_data = []
            for _, row in puts.iterrows():
                puts_data.append({
                    'type': 'put',
                    'strike': row['strike'],
                    'lastPrice': row['lastPrice'],
                    'bid': row['bid'],
                    'ask': row['ask'],
                    'volume': row['volume'],
                    'openInterest': row['openInterest'],
                    'impliedVolatility': row['impliedVolatility'],
                    'inTheMoney': row['inTheMoney'],
                    'contractSymbol': row['contractSymbol']
                })
            
            options_data = {
                'symbol': symbol,
                'expiry_date': expiry_date,
                'calls': calls_data,
                'puts': puts_data,
                'timestamp': datetime.now().isoformat()
            }
            
            self._save_to_cache(options_data, cache_path)
            return options_data
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {e}")
            return {}
    
    def get_all_expirations(self, symbol: str) -> List[str]:
        """获取所有到期日"""
        try:
            ticker = yf.Ticker(symbol)
            return list(ticker.options)
        except Exception as e:
            logger.error(f"Error fetching expirations for {symbol}: {e}")
            return []
    
    def filter_liquid_options(self, options_data: Dict, min_volume: int = 50, 
                            min_open_interest: int = 100) -> Dict:
        """筛选流动性好的期权"""
        if not options_data:
            return {}
            
        filtered_calls = [
            option for option in options_data.get('calls', [])
            if option['volume'] >= min_volume and option['openInterest'] >= min_open_interest
        ]
        
        filtered_puts = [
            option for option in options_data.get('puts', [])
            if option['volume'] >= min_volume and option['openInterest'] >= min_open_interest
        ]
        
        return {
            'symbol': options_data['symbol'],
            'expiry_date': options_data['expiry_date'],
            'calls': filtered_calls,
            'puts': filtered_puts,
            'timestamp': options_data['timestamp']
        }

class MarketDataCollector(DataCollector):
    """市场数据收集器"""
    
    def get_vix_data(self) -> float:
        """获取VIX指数"""
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
            return 0
        except Exception as e:
            logger.error(f"Error fetching VIX data: {e}")
            return 0
    
    def get_market_sentiment(self) -> Dict:
        """获取市场情绪指标"""
        sentiment_data = {
            'vix': self.get_vix_data(),
            'timestamp': datetime.now().isoformat()
        }
        
        # 可以添加更多市场情绪指标
        try:
            # SPY作为市场基准
            spy = yf.Ticker("SPY")
            spy_hist = spy.history(period="5d")
            if not spy_hist.empty:
                sentiment_data['spy_momentum'] = (spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0] - 1) * 100
        except:
            sentiment_data['spy_momentum'] = 0
            
        return sentiment_data