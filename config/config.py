"""
美股期权卖方推荐工具配置文件
Configuration for US Options Selling Recommendation Tool
"""

# API配置
API_CONFIG = {
    "data_source": "yfinance",  # 主要数据源
    "cache_enabled": True,      # 启用缓存
    "cache_duration": 300,      # 缓存持续时间（秒）
}

# 期权筛选参数
SCREENING_CONFIG = {
    "min_days_to_expiry": 7,       # 最少到期天数
    "max_days_to_expiry": 60,      # 最多到期天数
    "min_open_interest": 100,      # 最少持仓量
    "min_volume": 50,              # 最少成交量
    "min_delta": 0.1,              # 最小Delta值
    "max_delta": 0.5,              # 最大Delta值
    "min_iv_rank": 20,             # 最小隐含波动率排名
    "target_dte_range": [14, 45],  # 目标到期时间范围
}

# 风险管理参数
RISK_CONFIG = {
    "max_portfolio_risk": 0.05,    # 最大组合风险（占总资产比例）
    "max_single_position": 0.02,   # 单个头寸最大风险
    "margin_buffer": 1.2,          # 保证金缓冲倍数
    "stop_loss_pct": 0.5,          # 止损百分比（收到权利金的倍数）
}

# 策略参数
STRATEGY_CONFIG = {
    "covered_call": {
        "enabled": True,
        "min_stock_price": 10,
        "max_stock_price": 500,
        "target_delta": 0.3,
    },
    "cash_secured_put": {
        "enabled": True,
        "min_stock_price": 10,
        "max_stock_price": 500,
        "target_delta": -0.3,
    },
    "iron_condor": {
        "enabled": True,
        "wing_width": 5,
        "target_prob_profit": 0.7,
    },
    "strangle": {
        "enabled": True,
        "target_prob_profit": 0.6,
    }
}

# 可视化配置
VISUALIZATION_CONFIG = {
    "theme": "plotly_dark",
    "default_height": 600,
    "default_width": 800,
    "color_scheme": {
        "profit": "#00CC96",
        "loss": "#FF6692",
        "neutral": "#FFA15A",
        "background": "#2F3136"
    }
}

# 数据源配置
DATA_CONFIG = {
    "popular_stocks": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "SPY", "QQQ", "IWM",
        "XLF", "XLE", "XLK", "GLD", "SLV", "TLT", "NFLX", "DIS", "JPM", "BAC"
    ],
    "etf_list": [
        "SPY", "QQQ", "IWM", "XLF", "XLE", "XLK", "XLV", "XLI", "XLU", "XLP",
        "GLD", "SLV", "TLT", "HYG", "LQD", "EEM", "VIX", "UVXY", "SQQQ", "TQQQ"
    ]
}

# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/options_tool.log"
}