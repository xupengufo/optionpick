"""
可视化模块
Visualization module for options analysis and risk management
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

logger = logging.getLogger(__name__)

class OptionsVisualizer:
    """期权可视化器"""
    
    def __init__(self, style: str = "dark"):
        self.style = style
        self.colors = self._get_color_scheme()
        self._setup_style()
    
    def _get_color_scheme(self) -> Dict[str, str]:
        """获取颜色方案"""
        if self.style == "dark":
            return {
                'background': '#2F3136',
                'text': '#FFFFFF',
                'profit': '#00CC96',
                'loss': '#FF6692',
                'neutral': '#FFA15A',
                'grid': '#444444',
                'accent': '#7C4DFF'
            }
        else:
            return {
                'background': '#FFFFFF',
                'text': '#000000',
                'profit': '#2E8B57',
                'loss': '#DC143C',
                'neutral': '#FF8C00',
                'grid': '#CCCCCC',
                'accent': '#4169E1'
            }
    
    def _setup_style(self):
        """设置绘图样式"""
        if self.style == "dark":
            plt.style.use('dark_background')
        else:
            plt.style.use('default')
        
        sns.set_palette([self.colors['profit'], self.colors['loss'], self.colors['neutral'], self.colors['accent']])
    
    def plot_payoff_diagram(self, strategy_analysis: Dict, price_range_pct: float = 0.3) -> go.Figure:
        """绘制期权策略收益图"""
        try:
            strategy_type = strategy_analysis.get('strategy_type', '')
            stock_price = strategy_analysis.get('stock_price', 100)
            
            # 计算价格范围
            price_min = stock_price * (1 - price_range_pct)
            price_max = stock_price * (1 + price_range_pct)
            prices = np.linspace(price_min, price_max, 100)
            
            # 计算收益
            payoffs = self._calculate_payoffs(strategy_analysis, prices)
            
            # 创建图表
            fig = go.Figure()
            
            # 添加收益线
            fig.add_trace(go.Scatter(
                x=prices,
                y=payoffs,
                mode='lines',
                name='策略收益',
                line=dict(color=self.colors['profit'], width=3),
                hovertemplate='股价: $%{x:.2f}<br>收益: $%{y:.2f}<extra></extra>'
            ))
            
            # 添加盈亏平衡线
            fig.add_hline(y=0, line_dash="dash", line_color=self.colors['neutral'], 
                         annotation_text="盈亏平衡线")
            
            # 添加当前股价线
            fig.add_vline(x=stock_price, line_dash="dot", line_color=self.colors['accent'],
                         annotation_text=f"当前股价: ${stock_price:.2f}")
            
            # 标记盈亏平衡点
            breakeven_points = self._find_breakeven_points(strategy_analysis, prices, payoffs)
            for point in breakeven_points:
                fig.add_trace(go.Scatter(
                    x=[point],
                    y=[0],
                    mode='markers',
                    marker=dict(color=self.colors['neutral'], size=10, symbol='diamond'),
                    name=f'盈亏平衡点: ${point:.2f}',
                    showlegend=False
                ))
            
            # 设置布局
            fig.update_layout(
                title=f'{self._get_strategy_name(strategy_type)} 收益图',
                xaxis_title='股票价格 ($)',
                yaxis_title='收益 ($)',
                template='plotly_dark' if self.style == 'dark' else 'plotly_white',
                hovermode='x unified',
                height=500
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating payoff diagram: {e}")
            return go.Figure()
    
    def plot_risk_metrics_radar(self, opportunities: List[Dict]) -> go.Figure:
        """绘制风险指标雷达图"""
        try:
            if not opportunities:
                return go.Figure()
            
            # 准备数据
            metrics = ['收益率', '盈利概率', '流动性', '时间价值', 'Delta', '风险收益比']
            
            fig = go.Figure()
            
            colors = px.colors.qualitative.Set1
            
            for i, opp in enumerate(opportunities[:5]):  # 最多显示5个机会
                values = self._extract_radar_values(opp)
                
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=metrics,
                    fill='toself',
                    name=f"{opp.get('symbol', '')} ${opp.get('strike', 0):.0f}",
                    line_color=colors[i % len(colors)],
                    opacity=0.6
                ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=True,
                title="期权机会风险指标对比",
                template='plotly_dark' if self.style == 'dark' else 'plotly_white',
                height=500
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating radar chart: {e}")
            return go.Figure()
    
    def plot_iv_rank_distribution(self, symbols_data: Dict) -> go.Figure:
        """绘制隐含波动率排名分布"""
        try:
            iv_data = []
            
            for symbol, data in symbols_data.items():
                stock_data = data.get('stock_data', {})
                current_volatility = stock_data.get('current_volatility', 0)
                
                if current_volatility > 0:
                    # 这里应该计算真实的IV rank，简化处理
                    iv_rank = np.random.uniform(20, 80)  # 模拟数据
                    iv_data.append({
                        'Symbol': symbol,
                        'IV_Rank': iv_rank,
                        'Current_IV': current_volatility * 100
                    })
            
            if not iv_data:
                return go.Figure()
            
            df = pd.DataFrame(iv_data)
            
            fig = go.Figure()
            
            # 添加散点图
            fig.add_trace(go.Scatter(
                x=df['IV_Rank'],
                y=df['Current_IV'],
                mode='markers+text',
                text=df['Symbol'],
                textposition="top center",
                marker=dict(
                    size=12,
                    color=df['IV_Rank'],
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="IV排名")
                ),
                hovertemplate='%{text}<br>IV排名: %{x:.1f}<br>当前IV: %{y:.1f}%<extra></extra>'
            ))
            
            # 添加分区线
            fig.add_hline(y=30, line_dash="dash", line_color=self.colors['neutral'],
                         annotation_text="高IV阈值")
            fig.add_vline(x=50, line_dash="dash", line_color=self.colors['neutral'],
                         annotation_text="中位数")
            
            fig.update_layout(
                title='隐含波动率排名分布',
                xaxis_title='IV排名 (%)',
                yaxis_title='当前隐含波动率 (%)',
                template='plotly_dark' if self.style == 'dark' else 'plotly_white',
                height=500
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating IV rank distribution: {e}")
            return go.Figure()
    
    def plot_portfolio_risk_analysis(self, portfolio_metrics: Dict) -> go.Figure:
        """绘制投资组合风险分析"""
        try:
            # 创建子图
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('风险分布', '保证金使用', 'VaR分析', '多样化分析'),
                specs=[[{"type": "pie"}, {"type": "bar"}],
                       [{"type": "bar"}, {"type": "pie"}]]
            )
            
            # 风险分布饼图
            risk_labels = ['已使用风险', '剩余风险容量']
            portfolio_risk = portfolio_metrics.get('portfolio_risk_pct', 0)
            remaining_risk = max(0, 10 - portfolio_risk)  # 假设10%为最大风险
            
            fig.add_trace(go.Pie(
                labels=risk_labels,
                values=[portfolio_risk, remaining_risk],
                name="风险分布",
                marker_colors=[self.colors['loss'], self.colors['profit']]
            ), row=1, col=1)
            
            # 保证金使用条形图
            margin_utilization = portfolio_metrics.get('margin_utilization_pct', 0)
            fig.add_trace(go.Bar(
                x=['保证金使用率'],
                y=[margin_utilization],
                name="保证金使用",
                marker_color=self.colors['accent']
            ), row=1, col=2)
            
            # VaR分析
            var_95 = portfolio_metrics.get('var_95', 0)
            var_99 = portfolio_metrics.get('var_99', 0)
            expected_shortfall = portfolio_metrics.get('expected_shortfall', 0)
            
            fig.add_trace(go.Bar(
                x=['VaR 95%', 'VaR 99%', '期望短缺'],
                y=[var_95, var_99, expected_shortfall],
                name="VaR分析",
                marker_color=[self.colors['neutral'], self.colors['loss'], self.colors['loss']]
            ), row=2, col=1)
            
            # 多样化分析
            diversification = portfolio_metrics.get('diversification_ratio', 0)
            concentration = 1 - diversification
            
            fig.add_trace(go.Pie(
                labels=['多样化', '集中度'],
                values=[diversification, concentration],
                name="多样化分析",
                marker_colors=[self.colors['profit'], self.colors['loss']]
            ), row=2, col=2)
            
            fig.update_layout(
                title_text="投资组合风险分析",
                template='plotly_dark' if self.style == 'dark' else 'plotly_white',
                height=600
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating portfolio risk analysis: {e}")
            return go.Figure()
    
    def plot_greeks_heatmap(self, opportunities: List[Dict]) -> go.Figure:
        """绘制Greeks热力图"""
        try:
            if not opportunities:
                return go.Figure()
            
            # 准备数据
            symbols = []
            strikes = []
            deltas = []
            gammas = []
            thetas = []
            vegas = []
            
            for opp in opportunities:
                symbols.append(opp.get('symbol', ''))
                strikes.append(f"${opp.get('strike', 0):.0f}")
                
                greeks = opp.get('greeks', {})
                deltas.append(greeks.get('delta', 0))
                gammas.append(greeks.get('gamma', 0))
                thetas.append(greeks.get('theta', 0))
                vegas.append(greeks.get('vega', 0))
            
            # 创建DataFrame
            greeks_data = pd.DataFrame({
                'Symbol_Strike': [f"{s} {st}" for s, st in zip(symbols, strikes)],
                'Delta': deltas,
                'Gamma': gammas,
                'Theta': thetas,
                'Vega': vegas
            })
            
            # 标准化数据
            greeks_normalized = greeks_data.set_index('Symbol_Strike')
            for col in greeks_normalized.columns:
                greeks_normalized[col] = (greeks_normalized[col] - greeks_normalized[col].mean()) / greeks_normalized[col].std()
            
            fig = go.Figure(data=go.Heatmap(
                z=greeks_normalized.values,
                x=greeks_normalized.columns,
                y=greeks_normalized.index,
                colorscale='RdBu',
                zmid=0,
                hovertemplate='%{y}<br>%{x}: %{z:.2f}<extra></extra>'
            ))
            
            fig.update_layout(
                title='期权Greeks热力图 (标准化)',
                xaxis_title='Greeks指标',
                yaxis_title='期权合约',
                template='plotly_dark' if self.style == 'dark' else 'plotly_white',
                height=max(400, len(opportunities) * 30)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating Greeks heatmap: {e}")
            return go.Figure()
    
    def plot_time_decay_analysis(self, strategy_analysis: Dict) -> go.Figure:
        """绘制时间价值衰减分析"""
        try:
            # 模拟时间衰减
            days_remaining = np.arange(0, 60, 1)
            time_values = []
            
            current_theta = strategy_analysis.get('greeks', {}).get('theta', -0.02)
            initial_premium = strategy_analysis.get('returns', {}).get('max_profit', 100)
            
            for day in days_remaining:
                # 简化的时间价值衰减模型
                time_value = initial_premium * np.exp(-abs(current_theta) * day / 365)
                time_values.append(time_value)
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=days_remaining,
                y=time_values,
                mode='lines',
                name='时间价值',
                line=dict(color=self.colors['profit'], width=3),
                fill='tonexty',
                hovertemplate='天数: %{x}<br>时间价值: $%{y:.2f}<extra></extra>'
            ))
            
            # 添加重要时间节点
            important_days = [7, 14, 21, 30, 45]
            for day in important_days:
                if day < len(time_values):
                    fig.add_vline(
                        x=day,
                        line_dash="dash",
                        line_color=self.colors['neutral'],
                        annotation_text=f"{day}天"
                    )
            
            fig.update_layout(
                title='时间价值衰减分析',
                xaxis_title='距离到期天数',
                yaxis_title='时间价值 ($)',
                template='plotly_dark' if self.style == 'dark' else 'plotly_white',
                height=400
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating time decay analysis: {e}")
            return go.Figure()
    
    def _calculate_payoffs(self, strategy_analysis: Dict, prices: np.ndarray) -> np.ndarray:
        """计算策略收益"""
        strategy_type = strategy_analysis.get('strategy_type', '')
        
        if strategy_type == 'covered_call':
            return self._covered_call_payoff(strategy_analysis, prices)
        elif strategy_type == 'cash_secured_put':
            return self._cash_secured_put_payoff(strategy_analysis, prices)
        elif strategy_type == 'short_strangle':
            return self._short_strangle_payoff(strategy_analysis, prices)
        else:
            return np.zeros_like(prices)
    
    def _covered_call_payoff(self, strategy_analysis: Dict, prices: np.ndarray) -> np.ndarray:
        """备兑看涨期权收益"""
        strike = strategy_analysis.get('strike', 100)
        premium = strategy_analysis.get('returns', {}).get('max_profit', 0) / 100  # 转换为每股
        stock_price = strategy_analysis.get('stock_price', 100)
        
        # 股票收益 + 期权收益
        stock_pnl = prices - stock_price
        option_pnl = np.where(prices > strike, -(prices - strike), 0) + premium
        
        return (stock_pnl + option_pnl) * 100  # 转换为每合约
    
    def _cash_secured_put_payoff(self, strategy_analysis: Dict, prices: np.ndarray) -> np.ndarray:
        """现金担保看跌期权收益"""
        strike = strategy_analysis.get('strike', 100)
        premium = strategy_analysis.get('returns', {}).get('max_profit', 0)
        
        # 期权收益
        return np.where(prices < strike, -(strike - prices) * 100, 0) + premium
    
    def _short_strangle_payoff(self, strategy_analysis: Dict, prices: np.ndarray) -> np.ndarray:
        """卖出宽跨式收益"""
        strikes = strategy_analysis.get('strikes', {})
        put_strike = strikes.get('put_strike', 90)
        call_strike = strikes.get('call_strike', 110)
        net_credit = strategy_analysis.get('returns', {}).get('net_credit', 0)
        
        # 看跌期权收益
        put_pnl = np.where(prices < put_strike, -(put_strike - prices) * 100, 0)
        # 看涨期权收益
        call_pnl = np.where(prices > call_strike, -(prices - call_strike) * 100, 0)
        
        return put_pnl + call_pnl + net_credit
    
    def _find_breakeven_points(self, strategy_analysis: Dict, prices: np.ndarray, payoffs: np.ndarray) -> List[float]:
        """寻找盈亏平衡点"""
        breakeven_points = []
        
        for i in range(len(payoffs) - 1):
            if (payoffs[i] <= 0 and payoffs[i + 1] > 0) or (payoffs[i] >= 0 and payoffs[i + 1] < 0):
                # 线性插值找到精确的盈亏平衡点
                x1, x2 = prices[i], prices[i + 1]
                y1, y2 = payoffs[i], payoffs[i + 1]
                
                if y2 != y1:
                    breakeven = x1 - y1 * (x2 - x1) / (y2 - y1)
                    breakeven_points.append(breakeven)
        
        return breakeven_points
    
    def _extract_radar_values(self, opportunity: Dict) -> List[float]:
        """提取雷达图数值"""
        returns = opportunity.get('returns', {})
        probabilities = opportunity.get('probabilities', {})
        greeks = opportunity.get('greeks', {})
        liquidity = opportunity.get('option_details', {}).get('liquidity', {})
        
        # 标准化到0-100范围
        values = [
            min(100, max(0, returns.get('annualized_yield', 0) * 5)),  # 收益率
            min(100, max(0, probabilities.get('prob_profit_short', 0))),  # 盈利概率
            min(100, max(0, (liquidity.get('volume', 0) + liquidity.get('open_interest', 0)) / 50)),  # 流动性
            min(100, max(0, abs(greeks.get('theta', 0)) * 1000)),  # 时间价值
            min(100, max(0, abs(greeks.get('delta', 0)) * 200)),  # Delta
            min(100, max(0, 100 - returns.get('risk_reward_ratio', 3) * 20))  # 风险收益比（反转）
        ]
        
        return values
    
    def _get_strategy_name(self, strategy_type: str) -> str:
        """获取策略中文名称"""
        names = {
            'covered_call': '备兑看涨期权',
            'cash_secured_put': '现金担保看跌期权',
            'short_strangle': '卖出宽跨式',
            'iron_condor': '铁鹰策略',
            'short_straddle': '卖出跨式'
        }
        return names.get(strategy_type, strategy_type)