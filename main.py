"""
美股期权卖方推荐工具主界面
Main interface for US Options Selling Recommendation Tool
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_collector.data_manager import DataManager
from src.screening.screener import OptionsScreener
from src.screening.criteria import PresetScreens, ScreeningUtils
from src.risk_management.risk_manager import RiskManager
from src.visualization.charts import OptionsVisualizer
from config.config import *

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置页面配置
st.set_page_config(
    page_title="美股期权卖方推荐工具",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

class OptionsToolApp:
    """期权工具应用主类"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.screener = OptionsScreener()
        self.risk_manager = RiskManager()
        self.visualizer = OptionsVisualizer()
        
        # 初始化session state
        self._init_session_state()
    
    def _init_session_state(self):
        """初始化session状态"""
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = None
        if 'selected_symbols' not in st.session_state:
            st.session_state.selected_symbols = DATA_CONFIG['popular_stocks'][:5]
        if 'portfolio_capital' not in st.session_state:
            st.session_state.portfolio_capital = 100000
    
    def run(self):
        """运行应用"""
        st.title("🎯 美股期权卖方推荐工具")
        st.markdown("---")
        
        # 侧边栏配置
        self._render_sidebar()
        
        # 主内容区域
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 市场概览", "🔍 机会筛选", "📈 详细分析", "⚠️ 风险管理", "📋 投资组合"
        ])
        
        with tab1:
            self._render_market_overview()
        
        with tab2:
            self._render_opportunity_screening()
        
        with tab3:
            self._render_detailed_analysis()
        
        with tab4:
            self._render_risk_management()
        
        with tab5:
            self._render_portfolio_management()
    
    def _render_sidebar(self):
        """渲染侧边栏"""
        st.sidebar.header("⚙️ 设置")
        
        # 资金配置
        st.sidebar.subheader("资金配置")
        st.session_state.portfolio_capital = st.sidebar.number_input(
            "投资组合资金 ($)",
            min_value=1000,
            max_value=10000000,
            value=st.session_state.portfolio_capital,
            step=1000
        )
        
        # 股票选择
        st.sidebar.subheader("股票池")
        
        # 添加股票分类展示
        with st.sidebar.expander("📊 热门股票分类", expanded=False):
            categories = DATA_CONFIG.get('stock_categories', {})
            
            # 显示每个分类
            for category, stocks in categories.items():
                st.markdown(f"**{category}:**")
                # 将股票代码按每衔3个分行显示
                for i in range(0, len(stocks), 3):
                    row_stocks = stocks[i:i+3]
                    st.markdown(f"  `{' | '.join(row_stocks)}`")
                st.markdown("")  # 空行
        
        # 预设股票池
        available_symbols = DATA_CONFIG['popular_stocks'] + DATA_CONFIG['etf_list']
        
        # 快速选择分类
        st.sidebar.markdown("**⚡ 快速选择分类:**")
        category_choice = st.sidebar.selectbox(
            "选择一个分类快速添加",
            options=["不选择"] + list(DATA_CONFIG.get('stock_categories', {}).keys()),
            help="选择一个分类可以快速添加该分类下的所有股票"
        )
        
        # 添加自定义输入功能
        st.sidebar.markdown("**预设股票选择:**")
        selected_symbols = st.sidebar.multiselect(
            "从预设列表中选择",
            options=available_symbols,
            default=st.session_state.selected_symbols if all(symbol in available_symbols for symbol in st.session_state.selected_symbols) else [],
            help="选择要分析的热门股票代码"
        )
        
        # 处理分类选择
        if category_choice != "不选择":
            category_stocks = DATA_CONFIG.get('stock_categories', {}).get(category_choice, [])
            if category_stocks:
                # 合并分类中的股票
                selected_symbols = list(set(selected_symbols + category_stocks))
                st.sidebar.success(f"✅ 已添加 {category_choice} 分类下的 {len(category_stocks)} 只股票")
        
        # 自定义股票代码输入
        st.sidebar.markdown("**自定义股票代码:**")
        custom_symbols_input = st.sidebar.text_area(
            "输入股票代码（每行一个）",
            height=100,
            help="输入格式：\nAAPL\nTSLA\nGOOGL\n等，每行一个代码",
            placeholder="AAPL\nTSLA\nNVDA\nMSFT"
        )
        
        # 处理自定义输入
        custom_symbols = []
        if custom_symbols_input:
            custom_symbols = [symbol.strip().upper() for symbol in custom_symbols_input.split('\n') if symbol.strip()]
            
            # 验证股票代码有效性
            if st.sidebar.button("✅ 验证自定义代码", help="检查输入的股票代码是否有效"):
                with st.sidebar.spinner("验证中..."):
                    valid_symbols = []
                    invalid_symbols = []
                    
                    for symbol in custom_symbols:
                        if self.data_manager.validate_symbol(symbol):
                            valid_symbols.append(symbol)
                        else:
                            invalid_symbols.append(symbol)
                    
                    if valid_symbols:
                        st.sidebar.success(f"✅ 有效代码: {', '.join(valid_symbols)}")
                    if invalid_symbols:
                        st.sidebar.error(f"❌ 无效代码: {', '.join(invalid_symbols)}")
                        
                    # 更新自定义代码列表，只保留有效的
                    custom_symbols = valid_symbols
        
        # 合并预设选择和自定义输入
        all_selected_symbols = list(set(selected_symbols + custom_symbols))
        
        # 显示最终选择的股票
        if all_selected_symbols:
            st.sidebar.markdown("**当前选择的股票:**")
            symbols_display = ", ".join(all_selected_symbols)
            if len(symbols_display) > 50:
                symbols_display = symbols_display[:50] + "..."
            st.sidebar.info(f"{len(all_selected_symbols)} 只股票: {symbols_display}")
            
            # 添加清空按钮
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("🗑️ 清空选择", help="清空所有已选择的股票"):
                    st.session_state.selected_symbols = []
                    st.rerun()
            with col2:
                if st.button("🔄 重置默认", help="重置为默认股票列表"):
                    st.session_state.selected_symbols = DATA_CONFIG['popular_stocks'][:5]
                    st.rerun()
            
            st.session_state.selected_symbols = all_selected_symbols
        else:
            st.sidebar.warning("⚠️ 请选择至少一只股票进行分析")
        
        # 筛选预设
        st.sidebar.subheader("筛选策略")
        screening_preset = st.sidebar.selectbox(
            "选择筛选策略",
            options=["自定义", "保守收入型", "激进收入型", "高概率型"],
            index=0
        )
        
        # 风险偏好
        st.sidebar.subheader("风险偏好")
        risk_tolerance = st.sidebar.select_slider(
            "风险承受能力",
            options=["保守", "稳健", "平衡", "激进", "高风险"],
            value="平衡"
        )
        
        # 更新筛选配置
        self._update_screening_config(screening_preset, risk_tolerance)
        
        # 分析按钮
        st.sidebar.markdown("---")
        if st.sidebar.button("🚀 开始分析", type="primary", use_container_width=True):
            self._run_analysis()
    
    def _update_screening_config(self, preset: str, risk_tolerance: str):
        """更新筛选配置"""
        config = None
        
        if preset == "保守收入型":
            config = PresetScreens.conservative_income()
        elif preset == "激进收入型":
            config = PresetScreens.aggressive_income()
        elif preset == "高概率型":
            config = PresetScreens.high_probability()
        
        if config:
            self.screener.config.update(config)
        
        # 根据风险偏好调整
        risk_adjustments = {
            "保守": {"max_delta": 0.25, "min_profit_probability": 70},
            "稳健": {"max_delta": 0.3, "min_profit_probability": 60},
            "平衡": {"max_delta": 0.4, "min_profit_probability": 50},
            "激进": {"max_delta": 0.5, "min_profit_probability": 40},
            "高风险": {"max_delta": 0.6, "min_profit_probability": 30}
        }
        
        if risk_tolerance in risk_adjustments:
            self.screener.config.update(risk_adjustments[risk_tolerance])
    
    def _run_analysis(self):
        """运行分析"""
        with st.spinner("正在分析期权机会..."):
            try:
                # 获取市场环境
                market_context = self.data_manager.get_market_context()
                
                # 筛选机会
                opportunities = self.screener.get_top_opportunities(
                    st.session_state.selected_symbols, 
                    max_results=20
                )
                
                # 存储结果
                st.session_state.analysis_results = {
                    'market_context': market_context,
                    'opportunities': opportunities,
                    'timestamp': datetime.now()
                }
                
                st.success(f"分析完成！找到 {len(opportunities)} 个潜在机会")
                
            except Exception as e:
                st.error(f"分析失败: {e}")
                logger.error(f"Analysis failed: {e}")
    
    def _render_market_overview(self):
        """渲染市场概览"""
        st.header("📊 市场概览")
        
        if st.session_state.analysis_results:
            market_context = st.session_state.analysis_results['market_context']
            
            # 市场指标
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                vix_level = market_context.get('vix_level', 0)
                st.metric("VIX指数", f"{vix_level:.1f}", 
                         delta=None, help="恐慌指数，衡量市场波动性")
            
            with col2:
                market_regime = market_context.get('market_regime', '未知')
                st.metric("市场状态", market_regime)
            
            with col3:
                selling_attractiveness = market_context.get('selling_attractiveness', '中等')
                st.metric("卖方吸引力", selling_attractiveness)
            
            with col4:
                spy_momentum = market_context.get('spy_momentum', 0)
                st.metric("SPY动量", f"{spy_momentum:.1f}%", 
                         delta=spy_momentum if spy_momentum != 0 else None)
            
            # 市场建议
            st.subheader("💡 市场环境分析")
            if vix_level < 15:
                st.info("📉 当前VIX较低，市场波动性小，期权权利金相对较低，适合等待更好的卖方机会。")
            elif vix_level < 25:
                st.success("✅ 市场波动性适中，适合进行期权卖方策略。")
            elif vix_level < 35:
                st.warning("⚠️ 市场波动性较高，期权权利金丰厚，但需要注意风险管理。")
            else:
                st.error("🚨 市场极度波动，虽然权利金很高，但风险极大，建议谨慎操作。")
        
        else:
            st.info("点击侧边栏的'开始分析'按钮来获取市场数据")
    
    def _render_opportunity_screening(self):
        """渲染机会筛选"""
        st.header("🔍 期权卖方机会筛选")
        
        if st.session_state.analysis_results:
            opportunities = st.session_state.analysis_results['opportunities']
            
            if opportunities:
                # 机会总览
                st.subheader("📈 发现的机会")
                
                # 格式化结果
                results_df = ScreeningUtils.format_screening_results(opportunities)
                
                if not results_df.empty:
                    st.dataframe(
                        results_df,
                        use_container_width=True,
                        height=400
                    )
                    
                    # 下载按钮
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="📥 下载结果 (CSV)",
                        data=csv,
                        file_name=f"options_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                # 策略分布
                st.subheader("📊 策略分布")
                col1, col2 = st.columns(2)
                
                with col1:
                    strategy_counts = pd.Series([opp.get('strategy_type', '') for opp in opportunities]).value_counts()
                    st.bar_chart(strategy_counts)
                
                with col2:
                    # 收益率分布
                    returns = [opp.get('returns', {}).get('annualized_yield', 0) for opp in opportunities]
                    if returns:
                        # 创建直方图数据
                        import numpy as np
                        hist_data, bin_edges = np.histogram(returns, bins=10)
                        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                        hist_df = pd.DataFrame({
                            '收益率区间': [f"{edge:.1f}%" for edge in bin_centers],
                            '数量': hist_data
                        }).set_index('收益率区间')
                        st.bar_chart(hist_df)
                    st.caption("年化收益率分布")
            
            else:
                st.warning("未找到符合条件的期权机会，请调整筛选条件")
        
        else:
            st.info("请先运行分析来获取期权机会")
    
    def _render_detailed_analysis(self):
        """渲染详细分析"""
        st.header("📈 详细分析")
        
        if st.session_state.analysis_results:
            opportunities = st.session_state.analysis_results['opportunities']
            
            if opportunities:
                # 选择要分析的机会
                opportunity_options = [
                    f"{opp.get('symbol', '')} ${opp.get('strike', 0):.0f} {opp.get('strategy_type', '')}"
                    for opp in opportunities[:10]
                ]
                
                selected_idx = st.selectbox(
                    "选择要详细分析的机会",
                    range(len(opportunity_options)),
                    format_func=lambda x: opportunity_options[x]
                )
                
                if selected_idx is not None:
                    selected_opp = opportunities[selected_idx]
                    
                    # 基本信息
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📋 基本信息")
                        st.write(f"**股票代码**: {selected_opp.get('symbol', '')}")
                        st.write(f"**策略类型**: {selected_opp.get('strategy_type', '')}")
                        st.write(f"**执行价**: ${selected_opp.get('strike', 0):.2f}")
                        st.write(f"**到期日**: {selected_opp.get('expiry_date', '')}")
                        st.write(f"**距离到期**: {selected_opp.get('days_to_expiry', 0)} 天")
                    
                    with col2:
                        st.subheader("💰 收益指标")
                        returns = selected_opp.get('returns', {})
                        st.write(f"**最大收益**: ${returns.get('max_profit', 0):.2f}")
                        st.write(f"**最大损失**: ${returns.get('max_loss', 0):.2f}")
                        st.write(f"**年化收益率**: {returns.get('annualized_yield', 0):.1f}%")
                        st.write(f"**盈利概率**: {selected_opp.get('probabilities', {}).get('prob_profit_short', 0):.1f}%")
                    
                    # 收益图
                    st.subheader("📊 收益图表")
                    try:
                        payoff_fig = self.visualizer.plot_payoff_diagram(selected_opp)
                        st.plotly_chart(payoff_fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"无法生成收益图: {e}")
                    
                    # Greeks分析
                    st.subheader("🔢 Greeks分析")
                    greeks = selected_opp.get('greeks', {})
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Delta", f"{greeks.get('delta', 0):.3f}")
                    with col2:
                        st.metric("Gamma", f"{greeks.get('gamma', 0):.3f}")
                    with col3:
                        st.metric("Theta", f"{greeks.get('theta', 0):.3f}")
                    with col4:
                        st.metric("Vega", f"{greeks.get('vega', 0):.3f}")
                    
                    # 时间衰减分析
                    try:
                        time_decay_fig = self.visualizer.plot_time_decay_analysis(selected_opp)
                        st.plotly_chart(time_decay_fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"无法生成时间衰减图: {e}")
        
        else:
            st.info("请先运行分析来获取详细信息")
    
    def _render_risk_management(self):
        """渲染风险管理"""
        st.header("⚠️ 风险管理")
        
        if st.session_state.analysis_results:
            opportunities = st.session_state.analysis_results['opportunities']
            
            if opportunities:
                st.subheader("💼 交易风险分析")
                
                # 选择要分析风险的机会
                selected_opp = st.selectbox(
                    "选择要分析风险的交易",
                    opportunities,
                    format_func=lambda x: f"{x.get('symbol', '')} ${x.get('strike', 0):.0f} {x.get('strategy_type', '')}"
                )
                
                if selected_opp:
                    # 风险分析
                    risk_analysis = self.risk_manager.analyze_trade_risk(
                        selected_opp, 
                        st.session_state.portfolio_capital
                    )
                    
                    # 显示建议
                    recommendation = risk_analysis.get('recommendation', 'HOLD')
                    reason = risk_analysis.get('reason', '')
                    
                    if recommendation == 'STRONG_BUY':
                        st.success(f"🟢 **强烈推荐**: {reason}")
                    elif recommendation == 'BUY':
                        st.success(f"🟡 **推荐**: {reason}")
                    elif recommendation == 'CAUTION':
                        st.warning(f"🟠 **谨慎**: {reason}")
                    else:
                        st.error(f"🔴 **避免**: {reason}")
                    
                    # 风险指标
                    col1, col2, col3 = st.columns(3)
                    
                    risk_metrics = risk_analysis.get('risk_metrics', {})
                    with col1:
                        st.metric("最大损失", f"${risk_metrics.get('max_loss', 0):.2f}")
                    with col2:
                        st.metric("资金风险比例", f"{risk_metrics.get('capital_at_risk_pct', 0):.1f}%")
                    with col3:
                        st.metric("风险收益比", f"{risk_metrics.get('risk_reward_ratio', 0):.1f}")
                    
                    # 头寸建议
                    sizing_info = risk_analysis.get('sizing_info', {})
                    st.subheader("📏 头寸大小建议")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**推荐合约数**: {sizing_info.get('recommended_size', 0)}")
                        st.write(f"**所需保证金**: ${sizing_info.get('margin_required', 0):,.2f}")
                    with col2:
                        st.write(f"**实际风险金额**: ${sizing_info.get('actual_risk_amount', 0):,.2f}")
                        st.write(f"**实际风险比例**: {sizing_info.get('actual_risk_pct', 0):.1f}%")
                    
                    # 警告信息
                    warnings = sizing_info.get('warnings', [])
                    if warnings:
                        st.subheader("⚠️ 风险警告")
                        for warning in warnings:
                            st.warning(warning)
        
        else:
            st.info("请先运行分析来获取风险信息")
    
    def _render_portfolio_management(self):
        """渲染投资组合管理"""
        st.header("📋 投资组合管理")
        
        # 这里可以添加投资组合跟踪功能
        st.info("投资组合管理功能正在开发中...")
        
        # 可以添加的功能：
        # - 当前持仓跟踪
        # - 投资组合风险分析
        # - 收益跟踪
        # - 头寸管理建议

def main():
    """主函数"""
    app = OptionsToolApp()
    app.run()

if __name__ == "__main__":
    main()