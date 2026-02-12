"""
格式化工具函数
Formatting utility functions for display
"""
from datetime import datetime, timedelta
from typing import Optional


def format_currency(value: float, decimals: int = 2) -> str:
    """格式化金额显示"""
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.{decimals}f}M"
    elif abs(value) >= 1_000:
        return f"${value / 1_000:,.{decimals}f}K"
    else:
        return f"${value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """格式化百分比显示"""
    return f"{value:.{decimals}f}%"


def format_delta(value: float) -> str:
    """格式化 Delta 值，带方向符号"""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.3f}"


def format_date(date_str: str, fmt: str = "%Y-%m-%d") -> str:
    """格式化日期字符串"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        return date_str


def format_dte(days: int) -> str:
    """格式化到期天数"""
    if days <= 0:
        return "已到期"
    elif days == 1:
        return "1 天"
    elif days <= 7:
        return f"{days} 天"
    elif days <= 30:
        weeks = days // 7
        remaining = days % 7
        if remaining == 0:
            return f"{weeks} 周"
        return f"{weeks}周{remaining}天"
    else:
        return f"{days} 天"


def format_strategy_name(strategy_type: str) -> str:
    """将策略类型转为中文名称"""
    names = {
        'covered_call': '备兑看涨',
        'cash_secured_put': '现金担保看跌',
        'iron_condor': '铁鹰策略',
        'short_strangle': '卖出宽跨式',
        'short_put': '裸卖看跌',
        'short_call': '裸卖看涨',
    }
    return names.get(strategy_type, strategy_type)


def format_risk_level(level: str) -> str:
    """格式化风险等级为带颜色 emoji 的文本"""
    levels = {
        'low': '🟢 低风险',
        'medium': '🟡 中风险',
        'high': '🟠 高风险',
        'very_high': '🔴 极高风险',
    }
    return levels.get(level.lower(), f"⚪ {level}")


def format_recommendation(rec: str) -> str:
    """格式化交易建议"""
    recs = {
        'STRONG_BUY': '🟢 强烈推荐',
        'BUY': '🟡 推荐',
        'HOLD': '⚪ 持有',
        'CAUTION': '🟠 谨慎',
        'AVOID': '🔴 避免',
    }
    return recs.get(rec, rec)
