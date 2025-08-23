"""
风险管理模块
Risk management module for options selling strategies
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RiskCalculator:
    """风险计算器"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.risk_free_rate = 0.05  # 5% 无风险利率
    
    def calculate_position_risk(self, strategy_analysis: Dict, position_size: int = 1) -> Dict:
        """计算单个头寸的风险指标"""
        try:
            strategy_type = strategy_analysis.get('strategy_type', '')
            returns = strategy_analysis.get('returns', {})
            
            max_profit = returns.get('max_profit', 0) * position_size
            max_loss = returns.get('max_loss', float('inf'))
            
            # 处理无限损失的情况
            if max_loss == float('inf'):
                # 对于无限损失策略，使用股价的一定倍数作为最大损失估计
                if strategy_type == 'covered_call':
                    stock_price = strategy_analysis.get('stock_price', 0)
                    max_loss = stock_price * position_size * 100  # 假设1合约=100股
                elif strategy_type in ['short_strangle', 'short_straddle']:
                    # 使用3倍股价作为极端情况损失
                    stock_price = strategy_analysis.get('stock_price', 0)
                    max_loss = stock_price * 3 * position_size * 100
                else:
                    max_loss = 0
            else:
                max_loss = max_loss * position_size
            
            # 计算风险指标
            risk_metrics = {
                'position_size': position_size,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'capital_at_risk_pct': (max_loss / self.initial_capital) * 100 if self.initial_capital > 0 else 0,
                'profit_potential_pct': (max_profit / self.initial_capital) * 100 if self.initial_capital > 0 else 0,
                'risk_reward_ratio': max_loss / max_profit if max_profit > 0 else float('inf'),
                'break_even_success_rate': max_loss / (max_loss + max_profit) if (max_loss + max_profit) > 0 else 0
            }
            
            # 计算保证金要求
            margin_requirement = self._calculate_margin_requirement(strategy_analysis, position_size)
            risk_metrics['margin_requirement'] = margin_requirement
            risk_metrics['buying_power_reduction'] = margin_requirement
            
            # 计算资本效率
            if margin_requirement > 0:
                risk_metrics['return_on_margin'] = (max_profit / margin_requirement) * 100
            else:
                risk_metrics['return_on_margin'] = 0
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Error calculating position risk: {e}")
            return {}
    
    def calculate_portfolio_risk(self, positions: List[Dict]) -> Dict:
        """计算投资组合风险"""
        try:
            if not positions:
                return {}
            
            total_max_profit = sum(pos.get('max_profit', 0) for pos in positions)
            total_max_loss = sum(pos.get('max_loss', 0) for pos in positions)
            total_margin = sum(pos.get('margin_requirement', 0) for pos in positions)
            
            # 计算相关性调整（简化处理）
            # 在实际应用中，需要考虑标的资产之间的相关性
            correlation_adjustment = 0.8  # 假设80%相关性
            adjusted_max_loss = total_max_loss * correlation_adjustment
            
            portfolio_metrics = {
                'total_positions': len(positions),
                'total_max_profit': total_max_profit,
                'total_max_loss': total_max_loss,
                'adjusted_max_loss': adjusted_max_loss,
                'total_margin_requirement': total_margin,
                'portfolio_risk_pct': (adjusted_max_loss / self.initial_capital) * 100,
                'portfolio_return_potential_pct': (total_max_profit / self.initial_capital) * 100,
                'diversification_ratio': len(set(pos.get('symbol', '') for pos in positions)) / len(positions),
                'margin_utilization_pct': (total_margin / self.initial_capital) * 100
            }
            
            # 计算VaR (Value at Risk)
            portfolio_metrics.update(self._calculate_var(positions))
            
            return portfolio_metrics
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return {}
    
    def _calculate_margin_requirement(self, strategy_analysis: Dict, position_size: int) -> float:
        """计算保证金要求"""
        try:
            strategy_type = strategy_analysis.get('strategy_type', '')
            stock_price = strategy_analysis.get('stock_price', 0)
            
            if strategy_type == 'covered_call':
                # 备兑看涨：需要持有股票，无额外保证金
                return stock_price * 100 * position_size
            
            elif strategy_type == 'cash_secured_put':
                # 现金担保看跌：需要现金等于执行价
                strike = strategy_analysis.get('strike', 0)
                return strike * 100 * position_size
            
            elif strategy_type == 'short_strangle':
                # 卖出宽跨式：使用SPAN保证金计算（简化）
                strikes = strategy_analysis.get('strikes', {})
                put_strike = strikes.get('put_strike', 0)
                call_strike = strikes.get('call_strike', 0)
                
                # 简化的保证金计算：取较大值
                put_margin = put_strike * 100 * 0.2  # 20%保证金
                call_margin = stock_price * 100 * 0.2
                
                return max(put_margin, call_margin) * position_size
            
            elif strategy_type == 'iron_condor':
                # 铁鹰：保证金等于翼宽
                wing_width = strategy_analysis.get('wing_width', 5)
                return wing_width * 100 * position_size
            
            else:
                # 默认使用股价的20%
                return stock_price * 100 * 0.2 * position_size
                
        except Exception as e:
            logger.error(f"Error calculating margin requirement: {e}")
            return 0
    
    def _calculate_var(self, positions: List[Dict], confidence_level: float = 0.95) -> Dict:
        """计算风险价值 (Value at Risk)"""
        try:
            if not positions:
                return {'var_95': 0, 'var_99': 0, 'expected_shortfall': 0}
            
            # 简化的VaR计算
            # 在实际应用中，需要使用蒙特卡洛模拟或历史模拟
            
            losses = [pos.get('max_loss', 0) for pos in positions]
            
            # 假设损失服从正态分布
            mean_loss = np.mean(losses)
            std_loss = np.std(losses) if len(losses) > 1 else mean_loss * 0.2
            
            # 计算VaR
            from scipy.stats import norm
            var_95 = norm.ppf(0.95) * std_loss + mean_loss
            var_99 = norm.ppf(0.99) * std_loss + mean_loss
            
            # 计算期望短缺 (Expected Shortfall)
            expected_shortfall = mean_loss + std_loss * norm.pdf(norm.ppf(confidence_level)) / (1 - confidence_level)
            
            return {
                'var_95': var_95,
                'var_99': var_99,
                'expected_shortfall': expected_shortfall
            }
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return {'var_95': 0, 'var_99': 0, 'expected_shortfall': 0}

class PositionSizer:
    """头寸规模计算器"""
    
    def __init__(self, max_risk_per_trade: float = 0.02, max_portfolio_risk: float = 0.1):
        self.max_risk_per_trade = max_risk_per_trade  # 单笔交易最大风险2%
        self.max_portfolio_risk = max_portfolio_risk  # 投资组合最大风险10%
    
    def calculate_optimal_size(self, strategy_analysis: Dict, available_capital: float) -> Dict:
        """计算最优头寸大小"""
        try:
            returns = strategy_analysis.get('returns', {})
            max_loss = returns.get('max_loss', 0)
            
            if max_loss <= 0 or max_loss == float('inf'):
                return {'recommended_size': 0, 'reason': 'Unable to calculate due to infinite or zero loss'}
            
            # 基于风险的头寸大小
            max_risk_amount = available_capital * self.max_risk_per_trade
            risk_based_size = int(max_risk_amount / max_loss) if max_loss > 0 else 0
            
            # 基于保证金的头寸大小
            risk_calc = RiskCalculator()
            margin_per_contract = risk_calc._calculate_margin_requirement(strategy_analysis, 1)
            margin_based_size = int(available_capital * 0.5 / margin_per_contract) if margin_per_contract > 0 else 0
            
            # 取较小值作为推荐大小
            recommended_size = min(risk_based_size, margin_based_size, 10)  # 最多10个合约
            
            # 计算实际风险
            actual_risk = max_loss * recommended_size
            actual_risk_pct = (actual_risk / available_capital) * 100 if available_capital > 0 else 0
            
            sizing_info = {
                'recommended_size': max(0, recommended_size),
                'risk_based_size': risk_based_size,
                'margin_based_size': margin_based_size,
                'actual_risk_amount': actual_risk,
                'actual_risk_pct': actual_risk_pct,
                'margin_required': margin_per_contract * recommended_size,
                'reason': 'Optimal size based on risk and margin constraints'
            }
            
            # 添加警告
            warnings = []
            if actual_risk_pct > self.max_risk_per_trade * 100:
                warnings.append(f"Risk exceeds maximum per trade limit ({self.max_risk_per_trade*100:.1f}%)")
            
            if recommended_size == 0:
                warnings.append("Position size too risky - consider reducing size or avoiding this trade")
            
            sizing_info['warnings'] = warnings
            
            return sizing_info
            
        except Exception as e:
            logger.error(f"Error calculating optimal size: {e}")
            return {'recommended_size': 0, 'reason': f'Calculation error: {e}'}

class RiskMonitor:
    """风险监控器"""
    
    def __init__(self):
        self.risk_thresholds = {
            'max_single_position_risk': 0.02,  # 单个头寸最大风险2%
            'max_portfolio_risk': 0.1,         # 投资组合最大风险10%
            'max_margin_utilization': 0.5,     # 最大保证金使用率50%
            'max_concentration': 0.25,         # 单个标的最大集中度25%
            'min_liquidity_score': 60          # 最低流动性得分
        }
    
    def assess_risk_level(self, position_risk: Dict) -> str:
        """评估风险等级"""
        try:
            risk_pct = position_risk.get('capital_at_risk_pct', 0)
            
            if risk_pct <= 1:
                return "低风险"
            elif risk_pct <= 3:
                return "中等风险"
            elif risk_pct <= 5:
                return "高风险"
            else:
                return "极高风险"
                
        except Exception as e:
            logger.error(f"Error assessing risk level: {e}")
            return "未知风险"
    
    def check_risk_violations(self, portfolio_metrics: Dict) -> List[str]:
        """检查风险违规"""
        violations = []
        
        try:
            # 检查投资组合风险
            portfolio_risk = portfolio_metrics.get('portfolio_risk_pct', 0)
            if portfolio_risk > self.risk_thresholds['max_portfolio_risk'] * 100:
                violations.append(f"投资组合风险 ({portfolio_risk:.1f}%) 超过限制 ({self.risk_thresholds['max_portfolio_risk']*100:.1f}%)")
            
            # 检查保证金使用率
            margin_utilization = portfolio_metrics.get('margin_utilization_pct', 0)
            if margin_utilization > self.risk_thresholds['max_margin_utilization'] * 100:
                violations.append(f"保证金使用率 ({margin_utilization:.1f}%) 超过限制 ({self.risk_thresholds['max_margin_utilization']*100:.1f}%)")
            
            # 检查多样化程度
            diversification = portfolio_metrics.get('diversification_ratio', 1)
            if diversification < 0.5:
                violations.append(f"投资组合集中度过高 (多样化比率: {diversification:.2f})")
            
        except Exception as e:
            logger.error(f"Error checking risk violations: {e}")
            violations.append(f"风险检查错误: {e}")
        
        return violations
    
    def generate_risk_alerts(self, positions: List[Dict]) -> List[str]:
        """生成风险警报"""
        alerts = []
        
        try:
            current_time = datetime.now()
            
            for pos in positions:
                # 检查到期时间
                expiry_date_str = pos.get('expiry_date', '')
                if expiry_date_str:
                    try:
                        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
                        days_to_expiry = (expiry_date - current_time).days
                        
                        if days_to_expiry <= 3:
                            alerts.append(f"{pos.get('symbol', '')} 期权将在 {days_to_expiry} 天内到期")
                        elif days_to_expiry <= 7:
                            alerts.append(f"{pos.get('symbol', '')} 期权将在一周内到期，请关注")
                    except:
                        pass
                
                # 检查流动性
                if 'option_details' in pos:
                    liquidity = pos['option_details'].get('liquidity', {})
                    volume = liquidity.get('volume', 0)
                    if volume < 50:
                        alerts.append(f"{pos.get('symbol', '')} 期权流动性较低 (成交量: {volume})")
                
                # 检查Delta变化
                if 'greeks' in pos:
                    delta = abs(pos['greeks'].get('delta', 0))
                    if delta > 0.5:
                        alerts.append(f"{pos.get('symbol', '')} Delta值较高 ({delta:.3f})，风险增加")
        
        except Exception as e:
            logger.error(f"Error generating risk alerts: {e}")
            alerts.append(f"风险警报生成错误: {e}")
        
        return alerts

class RiskManager:
    """风险管理主类"""
    
    def __init__(self, initial_capital: float = 100000):
        self.risk_calculator = RiskCalculator(initial_capital)
        self.position_sizer = PositionSizer()
        self.risk_monitor = RiskMonitor()
    
    def analyze_trade_risk(self, strategy_analysis: Dict, available_capital: float) -> Dict:
        """分析交易风险"""
        try:
            # 计算最优头寸大小
            sizing_info = self.position_sizer.calculate_optimal_size(strategy_analysis, available_capital)
            recommended_size = sizing_info['recommended_size']
            
            if recommended_size == 0:
                return {
                    'recommendation': 'AVOID',
                    'reason': '风险过高或无法计算适当的头寸大小',
                    'sizing_info': sizing_info
                }
            
            # 计算头寸风险
            position_risk = self.risk_calculator.calculate_position_risk(strategy_analysis, recommended_size)
            
            # 评估风险等级
            risk_level = self.risk_monitor.assess_risk_level(position_risk)
            
            # 生成建议
            recommendation = self._generate_trade_recommendation(position_risk, risk_level)
            
            return {
                'recommendation': recommendation['action'],
                'reason': recommendation['reason'],
                'risk_level': risk_level,
                'position_risk': position_risk,
                'sizing_info': sizing_info,
                'risk_metrics': {
                    'max_loss': position_risk.get('max_loss', 0),
                    'max_profit': position_risk.get('max_profit', 0),
                    'risk_reward_ratio': position_risk.get('risk_reward_ratio', 0),
                    'capital_at_risk_pct': position_risk.get('capital_at_risk_pct', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trade risk: {e}")
            return {
                'recommendation': 'ERROR',
                'reason': f'风险分析错误: {e}',
                'risk_level': '未知风险'
            }
    
    def _generate_trade_recommendation(self, position_risk: Dict, risk_level: str) -> Dict:
        """生成交易建议"""
        risk_pct = position_risk.get('capital_at_risk_pct', 0)
        risk_reward = position_risk.get('risk_reward_ratio', float('inf'))
        
        if risk_pct > 5:
            return {'action': 'AVOID', 'reason': '风险过高，建议避免此交易'}
        elif risk_pct > 3:
            return {'action': 'CAUTION', 'reason': '风险较高，请谨慎考虑'}
        elif risk_reward > 4:
            return {'action': 'CAUTION', 'reason': '风险收益比过高'}
        elif risk_level == "低风险" and risk_reward <= 2:
            return {'action': 'STRONG_BUY', 'reason': '低风险，良好的风险收益比'}
        elif risk_level == "中等风险" and risk_reward <= 3:
            return {'action': 'BUY', 'reason': '风险可控，收益潜力良好'}
        else:
            return {'action': 'HOLD', 'reason': '风险收益平衡，可以考虑'}
    
    def analyze_portfolio_risk(self, positions: List[Dict]) -> Dict:
        """分析投资组合风险"""
        try:
            portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions)
            violations = self.risk_monitor.check_risk_violations(portfolio_metrics)
            alerts = self.risk_monitor.generate_risk_alerts(positions)
            
            return {
                'portfolio_metrics': portfolio_metrics,
                'risk_violations': violations,
                'risk_alerts': alerts,
                'overall_risk_level': self._assess_overall_risk(portfolio_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio risk: {e}")
            return {
                'portfolio_metrics': {},
                'risk_violations': [f'投资组合风险分析错误: {e}'],
                'risk_alerts': [],
                'overall_risk_level': '未知风险'
            }
    
    def _assess_overall_risk(self, portfolio_metrics: Dict) -> str:
        """评估整体风险等级"""
        portfolio_risk = portfolio_metrics.get('portfolio_risk_pct', 0)
        
        if portfolio_risk <= 3:
            return "低风险"
        elif portfolio_risk <= 7:
            return "中等风险"
        elif portfolio_risk <= 12:
            return "高风险"
        else:
            return "极高风险"