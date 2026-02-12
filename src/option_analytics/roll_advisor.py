"""
滚仓建议引擎
Roll Advisor - suggests roll strategies for existing positions
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RollAdvisor:
    """期权滚仓建议引擎"""

    def __init__(self, data_manager=None):
        self.data_manager = data_manager

    def suggest_rolls(self, position: Dict,
                      current_stock_price: float) -> List[Dict]:
        """
        为一个持仓生成所有可行的滚仓方案

        Args:
            position: 持仓信息 dict，包含 symbol, strategy_type, strike,
                      expiry_date, premium_per_contract, contracts
            current_stock_price: 当前股票价格

        Returns:
            List[Dict] 滚仓方案列表，每个方案包含:
                - roll_type: 滚仓类型 (roll_out / roll_down_out / roll_up_out)
                - label: 中文描述
                - new_strike: 新的执行价
                - new_expiry: 新到期日（建议）
                - estimated_credit: 预估净收入/支出 (正=收入, 负=支出)
                - new_dte: 新到期天数
                - rationale: 适用场景说明
        """
        symbol = position.get('symbol', '')
        strategy_type = position.get('strategy_type', '')
        strike = position.get('strike', 0)
        expiry_date_str = position.get('expiry_date', '')
        original_premium = position.get('premium_per_contract', 0)
        contracts = position.get('contracts', 1)

        if not symbol or strike <= 0:
            return []

        try:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            expiry_date = datetime.now()

        current_dte = (expiry_date - datetime.now()).days
        suggestions = []

        # 判断持仓状态
        if strategy_type in ('cash_secured_put', 'short_put'):
            is_itm = current_stock_price < strike
            is_threatened = current_stock_price < strike * 1.03
        elif strategy_type in ('covered_call', 'short_call'):
            is_itm = current_stock_price > strike
            is_threatened = current_stock_price > strike * 0.97
        else:
            is_itm = False
            is_threatened = False

        # ===== Roll Out (延期, 同 Strike) =====
        roll_out = self._build_roll_out(
            symbol, strategy_type, strike, current_stock_price,
            original_premium, current_dte, is_itm, is_threatened
        )
        if roll_out:
            suggestions.append(roll_out)

        # ===== Roll Down + Out (降低 Strike + 延期, 适用于 Put) =====
        if strategy_type in ('cash_secured_put', 'short_put'):
            roll_down = self._build_roll_down_out(
                symbol, strategy_type, strike, current_stock_price,
                original_premium, current_dte, is_itm
            )
            if roll_down:
                suggestions.append(roll_down)

        # ===== Roll Up + Out (提高 Strike + 延期, 适用于 Call) =====
        if strategy_type in ('covered_call', 'short_call'):
            roll_up = self._build_roll_up_out(
                symbol, strategy_type, strike, current_stock_price,
                original_premium, current_dte, is_itm
            )
            if roll_up:
                suggestions.append(roll_up)

        return suggestions

    def _build_roll_out(self, symbol: str, strategy_type: str,
                        strike: float, stock_price: float,
                        original_premium: float, current_dte: int,
                        is_itm: bool, is_threatened: bool) -> Optional[Dict]:
        """Roll Out: 延期到下一个周期, 同 Strike"""
        new_dte = max(current_dte, 7) + 30  # 延期约 30 天

        # 估算新权利金 (时间价值与 sqrt(DTE) 大致成正比)
        if current_dte > 0:
            time_value_ratio = (new_dte / current_dte) ** 0.5
        else:
            time_value_ratio = 2.0

        # 如果 ITM，回购成本更高
        if is_itm:
            if strategy_type in ('cash_secured_put', 'short_put'):
                intrinsic = max(0, strike - stock_price)
            else:
                intrinsic = max(0, stock_price - strike)
            buyback_cost = intrinsic + original_premium * 0.3
            new_premium_est = original_premium * time_value_ratio
            estimated_credit = new_premium_est - buyback_cost
        else:
            remaining_value = original_premium * 0.2 if current_dte <= 7 else original_premium * 0.4
            new_premium_est = original_premium * time_value_ratio
            estimated_credit = new_premium_est - remaining_value

        if is_itm:
            rationale = "持仓已进入实值 (ITM)，延期可以避免行权并收取额外时间价值"
        elif is_threatened:
            rationale = "股价接近执行价，提前滚仓可以降低行权风险"
        elif current_dte <= 21:
            rationale = "临近到期（≤21 DTE），锁定利润或继续收取权利金"
        else:
            rationale = "延期到下一个周期，继续收取时间价值"

        new_expiry = (datetime.now() + timedelta(days=new_dte)).strftime('%Y-%m-%d')

        return {
            'roll_type': 'roll_out',
            'label': '📅 Roll Out（延期）',
            'new_strike': strike,
            'new_expiry': new_expiry,
            'new_dte': new_dte,
            'estimated_credit': round(estimated_credit, 2),
            'original_premium': original_premium,
            'is_itm': is_itm,
            'rationale': rationale,
        }

    def _build_roll_down_out(self, symbol: str, strategy_type: str,
                              strike: float, stock_price: float,
                              original_premium: float, current_dte: int,
                              is_itm: bool) -> Optional[Dict]:
        """Roll Down + Out: 降低 Strike + 延期 (适用于 Put 卖方)"""
        # 新 Strike 降到当前股价的 95%（OTM 5%）
        new_strike = round(stock_price * 0.95, 0)
        if new_strike >= strike:
            new_strike = strike - 5  # 至少降 $5

        new_dte = max(current_dte, 7) + 30

        # 估算新权利金（Strike 更低 → 权利金更少，但更安全）
        if current_dte > 0:
            strike_discount = new_strike / strike
        else:
            strike_discount = 0.9
        new_premium_est = original_premium * strike_discount * ((new_dte / max(current_dte, 1)) ** 0.5)

        # 回购成本
        if is_itm:
            intrinsic = max(0, strike - stock_price)
            buyback_cost = intrinsic + original_premium * 0.2
        else:
            buyback_cost = original_premium * 0.3

        estimated_credit = new_premium_est - buyback_cost
        new_expiry = (datetime.now() + timedelta(days=new_dte)).strftime('%Y-%m-%d')

        return {
            'roll_type': 'roll_down_out',
            'label': '⬇️ Roll Down + Out（降低Strike + 延期）',
            'new_strike': new_strike,
            'new_expiry': new_expiry,
            'new_dte': new_dte,
            'estimated_credit': round(estimated_credit, 2),
            'original_premium': original_premium,
            'is_itm': is_itm,
            'rationale': (
                f"将 Strike 从 ${strike:.0f} 降至 ${new_strike:.0f}（OTM），"
                f"降低被行权风险。适用于股价下跌但仍看好标的的情况。"
            ),
        }

    def _build_roll_up_out(self, symbol: str, strategy_type: str,
                            strike: float, stock_price: float,
                            original_premium: float, current_dte: int,
                            is_itm: bool) -> Optional[Dict]:
        """Roll Up + Out: 提高 Strike + 延期 (适用于 Call 卖方)"""
        # 新 Strike 提到当前股价的 105%（OTM 5%）
        new_strike = round(stock_price * 1.05, 0)
        if new_strike <= strike:
            new_strike = strike + 5  # 至少升 $5

        new_dte = max(current_dte, 7) + 30

        # 估算新权利金（Strike 更高 → 权利金更少，但更安全）
        if current_dte > 0:
            strike_factor = strike / new_strike
        else:
            strike_factor = 0.9
        new_premium_est = original_premium * strike_factor * ((new_dte / max(current_dte, 1)) ** 0.5)

        # 回购成本
        if is_itm:
            intrinsic = max(0, stock_price - strike)
            buyback_cost = intrinsic + original_premium * 0.2
        else:
            buyback_cost = original_premium * 0.3

        estimated_credit = new_premium_est - buyback_cost
        new_expiry = (datetime.now() + timedelta(days=new_dte)).strftime('%Y-%m-%d')

        return {
            'roll_type': 'roll_up_out',
            'label': '⬆️ Roll Up + Out（提高Strike + 延期）',
            'new_strike': new_strike,
            'new_expiry': new_expiry,
            'new_dte': new_dte,
            'estimated_credit': round(estimated_credit, 2),
            'original_premium': original_premium,
            'is_itm': is_itm,
            'rationale': (
                f"将 Strike 从 ${strike:.0f} 升至 ${new_strike:.0f}（OTM），"
                f"避免被 Call Away 并继续持有股票。适用于股价上涨的情况。"
            ),
        }

    @staticmethod
    def format_credit(value: float) -> str:
        """格式化净借/贷"""
        if value >= 0:
            return f"🟢 净收入 ${value:.2f}"
        else:
            return f"🔴 净支出 ${abs(value):.2f}"

    @staticmethod
    def get_roll_recommendation(position: Dict,
                                current_stock_price: float) -> str:
        """根据持仓状态给出简单的滚仓建议文字"""
        strategy = position.get('strategy_type', '')
        strike = position.get('strike', 0)
        expiry_str = position.get('expiry_date', '')

        try:
            expiry = datetime.strptime(expiry_str, '%Y-%m-%d')
            dte = (expiry - datetime.now()).days
        except (ValueError, TypeError):
            dte = 999

        if strategy in ('cash_secured_put', 'short_put'):
            if current_stock_price < strike * 0.95:
                return "⚠️ 深度 ITM — 建议 Roll Down + Out 或评估是否接受行权"
            elif current_stock_price < strike:
                return "🟡 轻度 ITM — 建议 Roll Out 或 Roll Down + Out"
            elif dte <= 7:
                return "✅ 即将到期且 OTM — 可选择让其过期或 Roll Out 继续收益"
            elif dte <= 21:
                return "💡 考虑提前平仓锁定利润，或 Roll Out 到下一周期"
            else:
                return "✅ 状态良好，继续持有"
        elif strategy in ('covered_call', 'short_call'):
            if current_stock_price > strike * 1.05:
                return "⚠️ 深度 ITM — 建议 Roll Up + Out 或评估是否接受行权"
            elif current_stock_price > strike:
                return "🟡 轻度 ITM — 建议 Roll Out 或 Roll Up + Out"
            elif dte <= 7:
                return "✅ 即将到期且 OTM — 可让其过期或 Roll Out"
            elif dte <= 21:
                return "💡 考虑提前平仓锁定利润，或 Roll Out 到下一周期"
            else:
                return "✅ 状态良好，继续持有"
        else:
            return "ℹ️ 该策略类型暂不支持滚仓建议"
