"""
验证工具函数
Validation utility functions
"""
import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def validate_symbol_format(symbol: str) -> bool:
    """验证股票代码格式 (1-5个大写字母, 可含点号如 BRK.B)"""
    pattern = r'^[A-Z]{1,5}(\.[A-Z])?$'
    return bool(re.match(pattern, symbol.upper()))


def validate_price_range(price: float, min_price: float = 0.01,
                         max_price: float = 100000) -> bool:
    """验证价格在合理范围内"""
    return min_price <= price <= max_price


def validate_dte_range(days: int, min_dte: int = 0,
                       max_dte: int = 365) -> bool:
    """验证到期天数在合理范围内"""
    return min_dte <= days <= max_dte


def validate_delta_range(delta: float) -> bool:
    """验证 Delta 值在合理范围 [-1, 1]"""
    return -1.0 <= delta <= 1.0


def validate_probability(prob: float) -> bool:
    """验证概率值在 [0, 100] 范围"""
    return 0 <= prob <= 100


def validate_capital(capital: float, min_capital: float = 1000) -> bool:
    """验证资金额度"""
    return capital >= min_capital


def validate_screening_config(config: Dict) -> Tuple[bool, List[str]]:
    """
    验证筛选配置参数合理性
    返回 (is_valid, error_messages)
    """
    errors = []

    min_dte = config.get('min_days_to_expiry', 0)
    max_dte = config.get('max_days_to_expiry', 365)
    if min_dte > max_dte:
        errors.append(f"min_days_to_expiry ({min_dte}) 不能大于 max_days_to_expiry ({max_dte})")

    min_delta = config.get('min_delta', 0)
    max_delta = config.get('max_delta', 1)
    if min_delta > max_delta:
        errors.append(f"min_delta ({min_delta}) 不能大于 max_delta ({max_delta})")

    min_price = config.get('min_stock_price', 0)
    max_price = config.get('max_stock_price', 100000)
    if min_price > max_price:
        errors.append(f"min_stock_price ({min_price}) 不能大于 max_stock_price ({max_price})")

    min_oi = config.get('min_open_interest', 0)
    if min_oi < 0:
        errors.append(f"min_open_interest ({min_oi}) 不能为负数")

    min_vol = config.get('min_volume', 0)
    if min_vol < 0:
        errors.append(f"min_volume ({min_vol}) 不能为负数")

    return len(errors) == 0, errors


def validate_position_input(symbol: str, strategy_type: str, strike: float,
                            expiry_date: str, contracts: int,
                            premium: float) -> Tuple[bool, List[str]]:
    """
    验证添加持仓时的输入参数
    返回 (is_valid, error_messages)
    """
    errors = []

    if not validate_symbol_format(symbol):
        errors.append(f"股票代码格式无效: {symbol}")

    valid_strategies = [
        'covered_call', 'cash_secured_put', 'iron_condor',
        'short_strangle', 'short_put', 'short_call'
    ]
    if strategy_type not in valid_strategies:
        errors.append(f"无效策略类型: {strategy_type}")

    if strike <= 0:
        errors.append(f"执行价必须大于 0: {strike}")

    if contracts <= 0:
        errors.append(f"合约数必须大于 0: {contracts}")

    if premium < 0:
        errors.append(f"权利金不能为负: {premium}")

    # 验证日期格式
    import re as re_mod
    if not re_mod.match(r'^\d{4}-\d{2}-\d{2}$', expiry_date):
        errors.append(f"日期格式无效 (应为 YYYY-MM-DD): {expiry_date}")

    return len(errors) == 0, errors
