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
from typing import Dict, List

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_collector.data_manager import DataManager
from src.data_collector.github_pools import GitHubStockPoolProvider
from src.screening.screener import OptionsScreener
from src.screening.criteria import PresetScreens, ScreeningUtils
from src.risk_management.risk_manager import RiskManager
from src.visualization.charts import OptionsVisualizer
from src.utils.persistence import PortfolioStore
from src.utils.formatters import format_currency, format_strategy_name
from src.option_analytics.roll_advisor import RollAdvisor
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
        self.github_pool_provider = GitHubStockPoolProvider(
            GITHUB_POOL_CONFIG,
            preferred_symbols=DATA_CONFIG.get("popular_stocks", [])
        )
        self.screener = OptionsScreener()
        self.risk_manager = RiskManager()
        self.visualizer = OptionsVisualizer()
        self.portfolio_store = PortfolioStore()
        self.roll_advisor = RollAdvisor()
        
        # 初始化session state
        self._init_session_state()
    
    def _init_session_state(self):
        """初始化session状态"""
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = None
        if 'filtered_opportunities' not in st.session_state:
            st.session_state.filtered_opportunities = []
        if 'favorite_opportunities' not in st.session_state:
            st.session_state.favorite_opportunities = []
        if 'selected_symbols' not in st.session_state:
            # 简单的默认股票列表
            st.session_state.selected_symbols = ["AAPL", "MSFT", "TSLA", "SPY", "QQQ"]
        if 'custom_symbols_input' not in st.session_state:
            st.session_state.custom_symbols_input = "\n".join(st.session_state.selected_symbols)
        if 'portfolio_capital' not in st.session_state:
            st.session_state.portfolio_capital = 100000

    def _get_opportunity_id(self, opportunity: Dict) -> str:
        """生成机会唯一标识"""
        strategy_type = opportunity.get('strategy_type', '')
        strikes = opportunity.get('strikes', {})
        if strategy_type == 'short_strangle':
            strike_part = f"{strikes.get('put_strike', 0)}-{strikes.get('call_strike', 0)}"
        elif strategy_type == 'bull_put_spread':
            strike_part = f"{strikes.get('put_long', 0)}-{strikes.get('put_short', 0)}"
        elif strategy_type == 'bear_call_spread':
            strike_part = f"{strikes.get('call_short', 0)}-{strikes.get('call_long', 0)}"
        elif strategy_type == 'iron_condor':
            strike_part = (
                f"{strikes.get('put_long', 0)}-{strikes.get('put_short', 0)}-"
                f"{strikes.get('call_short', 0)}-{strikes.get('call_long', 0)}"
            )
        else:
            strike_part = f"{opportunity.get('strike', 0)}"

        return "|".join([
            str(opportunity.get('symbol', '')),
            str(strategy_type),
            str(opportunity.get('expiry_date', '')),
            strike_part,
        ])

    def _format_opportunity_strike(self, opportunity: Dict) -> str:
        """格式化不同策略的行权价展示"""
        def _fmt_price(value) -> str:
            try:
                return f"${float(value):.0f}"
            except (TypeError, ValueError):
                return str(value)

        strategy_type = opportunity.get('strategy_type', '')
        strikes = opportunity.get('strikes', {})
        if strategy_type == 'short_strangle':
            strikes = opportunity.get('strikes', {})
            return f"{_fmt_price(strikes.get('put_strike', 0))}/{_fmt_price(strikes.get('call_strike', 0))}"
        if strategy_type == 'bull_put_spread':
            return f"{_fmt_price(strikes.get('put_short', 0))}/{_fmt_price(strikes.get('put_long', 0))}"
        if strategy_type == 'bear_call_spread':
            return f"{_fmt_price(strikes.get('call_short', 0))}/{_fmt_price(strikes.get('call_long', 0))}"
        strike = opportunity.get('strike', 0)
        return _fmt_price(strike)

    def _format_opportunity_label(self, opportunity: Dict) -> str:
        """格式化机会标签文本"""
        return (
            f"{opportunity.get('symbol', '')} "
            f"{self._format_opportunity_strike(opportunity)} "
            f"{opportunity.get('strategy_type', '')}"
        )

    def _filter_and_sort_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """基于前端控件筛选和排序机会"""
        if not opportunities:
            return []

        strategy_options = sorted({opp.get('strategy_type', '') for opp in opportunities if opp.get('strategy_type', '')})

        st.subheader("🎛️ 结果筛选与排序")
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_strategies = st.multiselect(
                "策略类型",
                options=strategy_options,
                default=strategy_options,
                key="screen_strategy_filter"
            )
            min_prob = st.slider("最小盈利概率(%)", 0, 100, 50, key="screen_min_prob")
        with col2:
            min_yield = st.slider("最小年化收益率(%)", 0, 100, 5, key="screen_min_yield")
            min_volume = st.number_input("最小成交量", min_value=0, value=50, step=10, key="screen_min_volume")
        with col3:
            sort_by = st.selectbox(
                "排序字段",
                options=["综合评分", "年化收益率", "盈利概率", "DTE"],
                key="screen_sort_by"
            )
            sort_desc = st.checkbox("降序排序", value=True, key="screen_sort_desc")

        filtered = []
        for opp in opportunities:
            strategy_type = opp.get('strategy_type', '')
            annualized_yield = opp.get('returns', {}).get('annualized_yield', 0)
            profit_prob = opp.get('probabilities', {}).get('prob_profit_short', opp.get('returns', {}).get('profit_probability', 0))
            volume = opp.get('option_details', {}).get('liquidity', {}).get('volume', 0)

            if selected_strategies and strategy_type not in selected_strategies:
                continue
            if annualized_yield < min_yield:
                continue
            if profit_prob < min_prob:
                continue
            if volume < min_volume:
                continue
            filtered.append(opp)

        sort_key_map = {
            "综合评分": lambda x: x.get('score', 0),
            "年化收益率": lambda x: x.get('returns', {}).get('annualized_yield', 0),
            "盈利概率": lambda x: x.get('probabilities', {}).get('prob_profit_short', x.get('returns', {}).get('profit_probability', 0)),
            "DTE": lambda x: x.get('days_to_expiry', 0),
        }

        filtered.sort(key=sort_key_map[sort_by], reverse=sort_desc)
        st.caption(f"筛选后结果: {len(filtered)} / {len(opportunities)}")
        return filtered

    def _render_favorite_manager(self, opportunities: List[Dict]):
        """渲染收藏管理"""
        if not opportunities:
            return

        st.subheader("⭐ 收藏候选")
        favorite_ids = set(st.session_state.favorite_opportunities)
        records = []
        for opp in opportunities[:50]:
            opp_id = self._get_opportunity_id(opp)
            records.append({
                "收藏": opp_id in favorite_ids,
                "Symbol": opp.get('symbol', ''),
                "Strategy": opp.get('strategy_type', ''),
                "Strike": self._format_opportunity_strike(opp),
                "Expiry": opp.get('expiry_date', ''),
                "Score": round(opp.get('score', 0), 1),
                "ID": opp_id,
            })

        favorite_df = pd.DataFrame(records)
        edited_df = st.data_editor(
            favorite_df,
            hide_index=True,
            width='stretch',
            column_config={"ID": None},
            key="favorite_editor"
        )

        selected_ids = edited_df.loc[edited_df["收藏"] == True, "ID"].tolist()
        st.session_state.favorite_opportunities = selected_ids
        st.caption(f"已收藏 {len(selected_ids)} 个机会，可在详细分析页做对比。")

    def _render_comparison_panel(self, opportunities: List[Dict]):
        """渲染收藏对比面板"""
        favorite_ids = set(st.session_state.favorite_opportunities)
        favorite_opps = [opp for opp in opportunities if self._get_opportunity_id(opp) in favorite_ids]

        if len(favorite_opps) < 2:
            st.info("收藏至少 2 个机会后，可在此查看并排对比。")
            return

        st.subheader("🧮 收藏机会对比")
        compare_df = pd.DataFrame([
            {
                "Symbol": opp.get('symbol', ''),
                "Strategy": opp.get('strategy_type', ''),
                "DTE": opp.get('days_to_expiry', 0),
                "AnnualizedYield(%)": round(opp.get('returns', {}).get('annualized_yield', 0), 2),
                "ProfitProb(%)": round(opp.get('probabilities', {}).get('prob_profit_short', opp.get('returns', {}).get('profit_probability', 0)), 2),
                "MaxProfit": round(opp.get('returns', {}).get('max_profit', 0), 2),
                "MaxLoss": opp.get('returns', {}).get('max_loss', 0),
                "Score": round(opp.get('score', 0), 2),
            }
            for opp in favorite_opps[:4]
        ])
        st.dataframe(compare_df, width='stretch')
    
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

        # GitHub 公开项目指数池
        source_options = {
            "手动输入": None,
            "S&P 500 精选（GitHub）": "sp500",
            "NASDAQ 100 精选（GitHub）": "nasdaq100",
            "S&P 500 + NASDAQ 100 精选（GitHub）": "combined",
        }
        github_source_label = st.sidebar.selectbox(
            "指数股票池来源",
            options=list(source_options.keys()),
            index=0,
            help="数据来自 GitHub 公开项目 yfiua/index-constituents"
        )
        min_pool_size = int(GITHUB_POOL_CONFIG.get("min_curated_size", 10))
        max_pool_size = int(GITHUB_POOL_CONFIG.get("max_curated_size", 100))
        default_pool_size = int(GITHUB_POOL_CONFIG.get("default_curated_size", 30))
        curated_pool_size = st.sidebar.slider(
            "精选股票数量",
            min_value=min_pool_size,
            max_value=max_pool_size,
            value=min(max(default_pool_size, min_pool_size), max_pool_size),
            step=5
        )
        if st.sidebar.button("⬇️ 从GitHub加载指数股票池", width='stretch'):
            source_code = source_options[github_source_label]
            if source_code is None:
                st.sidebar.info("当前为手动输入模式，无需加载。")
            else:
                with st.sidebar.spinner("正在从 GitHub 获取指数成分股..."):
                    try:
                        if source_code == "combined":
                            symbols = self.github_pool_provider.get_combined_curated_symbols(
                                ["sp500", "nasdaq100"],
                                curated_pool_size
                            )
                        else:
                            symbols = self.github_pool_provider.get_curated_symbols(
                                source_code,
                                curated_pool_size
                            )
                        if symbols:
                            st.session_state.selected_symbols = symbols
                            st.session_state.custom_symbols_input = "\n".join(symbols)
                            st.sidebar.success(f"✅ 已加载 {len(symbols)} 只股票")
                            st.rerun()
                        else:
                            st.sidebar.warning("未获取到有效股票代码，请稍后重试。")
                    except Exception as e:
                        logger.error(f"GitHub pool load failed: {e}")
                        st.sidebar.error(f"加载失败: {e}")
        
        # 自定义股票代码输入
        custom_symbols_input = st.sidebar.text_area(
            "输入股票代码（每行一个）",
            height=120,
            help="输入格式：\nAAPL\nMSFT\nTSLA\nGOOGL\n\n支持任何美股代码",
            placeholder="AAPL\nMSFT\nTSLA\nGOOGL\nNVDA",
            key="custom_symbols_input"
        )
        
        # 处理输入的股票代码
        if custom_symbols_input:
            raw_symbols = [symbol.strip().upper() for symbol in custom_symbols_input.split('\n') if symbol.strip()]
            # 去重并保持输入顺序
            seen = set()
            input_symbols = []
            for symbol in raw_symbols:
                if symbol not in seen:
                    seen.add(symbol)
                    input_symbols.append(symbol)
            
            # 显示当前输入的股票
            if input_symbols:
                st.session_state.selected_symbols = input_symbols
                st.sidebar.info(f"📊 当前输入: {len(input_symbols)} 只股票（点击“开始分析”时自动校验）")
            else:
                st.sidebar.warning("💡 请输入至少一个股票代码")
        else:
            # 如果输入框为空，显示默认提示
            if not st.session_state.selected_symbols:
                st.sidebar.info("💡 请在上方输入要分析的股票代码")
        
        # 显示当前已验证的股票
        if st.session_state.selected_symbols:
            st.sidebar.markdown("**当前分析股票:**")
            symbols_text = ", ".join(st.session_state.selected_symbols)
            if len(symbols_text) > 60:
                symbols_text = symbols_text[:60] + "..."
            st.sidebar.success(f"🎯 {len(st.session_state.selected_symbols)} 只: {symbols_text}")
            
            # 清空按钮
            if st.sidebar.button("🗑️ 清空股票列表", help="清空所有已选择的股票"):
                st.session_state.selected_symbols = []
                st.session_state.custom_symbols_input = ""
                st.rerun()
        
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
        if st.sidebar.button("🚀 开始分析", type="primary", width='stretch'):
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
                # 统一校验代码，避免额外“验证并应用”步骤
                raw_symbols = list(st.session_state.selected_symbols)
                valid_symbols = []
                invalid_symbols = []
                for symbol in raw_symbols:
                    if self.data_manager.validate_symbol(symbol):
                        valid_symbols.append(symbol)
                    else:
                        invalid_symbols.append(symbol)

                if invalid_symbols:
                    display = ", ".join(invalid_symbols[:10])
                    if len(invalid_symbols) > 10:
                        display += f" ...（共 {len(invalid_symbols)} 个）"
                    st.warning(f"以下代码无效，已自动忽略: {display}")

                if not valid_symbols:
                    st.error("没有可用的有效股票代码，请检查输入后重试。")
                    return

                if valid_symbols != raw_symbols:
                    st.session_state.selected_symbols = valid_symbols
                    st.session_state.custom_symbols_input = "\n".join(valid_symbols)

                # 获取市场环境
                market_context = self.data_manager.get_market_context()
                
                # 获取标的波动率快照（用于 IV Rank 分布图）
                symbols_data = {}
                for symbol in valid_symbols:
                    stock_data = self.data_manager.get_complete_stock_data(symbol)
                    if stock_data:
                        symbols_data[symbol] = {'stock_data': stock_data}
                
                # 筛选机会
                opportunities = self.screener.get_top_opportunities(
                    valid_symbols,
                    max_results=20
                )
                
                # 存储结果
                st.session_state.analysis_results = {
                    'market_context': market_context,
                    'symbols_data': symbols_data,
                    'opportunities': opportunities,
                    'timestamp': datetime.now()
                }
                st.session_state.filtered_opportunities = opportunities
                
                # 持久化分析历史
                self.portfolio_store.save_analysis(
                    symbols=valid_symbols,
                    opportunities=opportunities,
                    market_context=market_context,
                )
                
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

            # IV Rank 分布
            symbols_data = st.session_state.analysis_results.get('symbols_data', {})
            if symbols_data:
                st.subheader("🌡️ IV Rank 分布")
                iv_rank_fig = self.visualizer.plot_iv_rank_distribution(symbols_data)
                if iv_rank_fig and len(iv_rank_fig.data) > 0:
                    st.plotly_chart(iv_rank_fig, width='stretch')
                else:
                    st.info("当前样本不足，暂无法生成 IV Rank 分布图。")
        
        else:
            st.info("点击侧边栏的'开始分析'按钮来获取市场数据")
    
    def _render_opportunity_screening(self):
        """渲染机会筛选"""
        st.header("🔍 期权卖方机会筛选")
        
        if st.session_state.analysis_results:
            opportunities = st.session_state.analysis_results['opportunities']
            filtered_opportunities = self._filter_and_sort_opportunities(opportunities)
            st.session_state.filtered_opportunities = filtered_opportunities
            
            if filtered_opportunities:
                # 机会总览
                st.subheader("📈 发现的机会")
                
                # 格式化结果
                results_df = ScreeningUtils.format_screening_results(filtered_opportunities)
                
                if not results_df.empty:
                    st.dataframe(
                        results_df,
                        width='stretch',
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
                    strategy_counts = pd.Series([opp.get('strategy_type', '') for opp in filtered_opportunities]).value_counts()
                    st.bar_chart(strategy_counts)
                
                with col2:
                    # 收益率分布
                    returns = [opp.get('returns', {}).get('annualized_yield', 0) for opp in filtered_opportunities]
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

                self._render_favorite_manager(filtered_opportunities)
            
            else:
                st.warning("未找到符合条件的期权机会，请调整筛选参数")
        
        else:
            st.info("请先运行分析来获取期权机会")
    
    def _render_detailed_analysis(self):
        """渲染详细分析"""
        st.header("📈 详细分析")
        
        if st.session_state.analysis_results:
            opportunities = st.session_state.filtered_opportunities or st.session_state.analysis_results['opportunities']
            
            if opportunities:
                self._render_comparison_panel(opportunities)

                # 选择要分析的机会
                opportunity_options = [
                    self._format_opportunity_label(opp)
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
                        st.write(f"**执行价**: {self._format_opportunity_strike(selected_opp)}")
                        st.write(f"**到期日**: {selected_opp.get('expiry_date', '')}")
                        st.write(f"**距离到期**: {selected_opp.get('days_to_expiry', 0)} 天")
                    
                    with col2:
                        st.subheader("💰 收益指标")
                        returns = selected_opp.get('returns', {})
                        profit_prob = selected_opp.get('probabilities', {}).get(
                            'prob_profit_short',
                            returns.get('profit_probability', 0)
                        )
                        st.write(f"**最大收益**: ${returns.get('max_profit', 0):.2f}")
                        st.write(f"**最大损失**: ${returns.get('max_loss', 0):.2f}")
                        st.write(f"**年化收益率**: {returns.get('annualized_yield', 0):.1f}%")
                        st.write(f"**盈利概率**: {profit_prob:.1f}%")
                    
                    # 收益图
                    st.subheader("📊 收益图表")
                    try:
                        payoff_fig = self.visualizer.plot_payoff_diagram(selected_opp)
                        st.plotly_chart(payoff_fig, width='stretch')
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
                        st.plotly_chart(time_decay_fig, width='stretch')
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
                    format_func=self._format_opportunity_label
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
                    elif recommendation == 'HOLD':
                        st.info(f"⚪ **持有/观望**: {reason}")
                    elif recommendation == 'CAUTION':
                        st.warning(f"🟠 **谨慎**: {reason}")
                    elif recommendation == 'AVOID':
                        st.error(f"🔴 **避免**: {reason}")
                    else:
                        st.error(f"❌ **状态异常 ({recommendation})**: {reason}")
                    
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

        tab_add, tab_open, tab_closed, tab_history, tab_greeks, tab_wheel = st.tabs([
            "➕ 添加持仓", "📂 当前持仓", "✅ 已平仓记录",
            "📜 分析历史", "🎨 Greeks 概览", "🔄 Wheel 策略"
        ])

        # ===== 添加持仓 =====
        with tab_add:
            st.subheader("➕ 新增持仓")
            col1, col2 = st.columns(2)
            with col1:
                symbol = st.text_input("股票代码", value="AAPL",
                                       key="port_symbol").upper()
                strategy_type = st.selectbox(
                    "策略类型",
                    options=['covered_call', 'cash_secured_put',
                             'short_strangle', 'iron_condor',
                             'bull_put_spread', 'bear_call_spread'],
                    format_func=format_strategy_name,
                    key="port_strategy"
                )
                strike = st.number_input("执行价 ($)", min_value=0.01,
                                         value=100.0, step=1.0,
                                         key="port_strike")
            with col2:
                expiry = st.date_input("到期日", key="port_expiry")
                contracts = st.number_input("合约数", min_value=1,
                                            value=1, step=1,
                                            key="port_contracts")
                premium = st.number_input("每张权利金 ($)", min_value=0.0,
                                          value=1.0, step=0.05,
                                          key="port_premium")
                open_date = st.date_input("开仓日期", key="port_open_date")
            notes = st.text_input("备注", key="port_notes")
            wheel_state = st.selectbox(
                "Wheel 状态（可选）",
                options=['', 'sell_put', 'assigned', 'sell_call',
                         'called_away', 'idle'],
                format_func=lambda x: PortfolioStore.WHEEL_STATES.get(
                    x, '— 不参与 Wheel') if x else '— 不参与 Wheel',
                key="port_wheel"
            )

            if st.button("➕ 添加持仓", type="primary",
                         key="port_add_btn"):
                pos_id = self.portfolio_store.add_position(
                    symbol=symbol, strategy_type=strategy_type,
                    strike=strike, expiry_date=str(expiry),
                    contracts=contracts,
                    premium_per_contract=premium,
                    open_date=str(open_date), notes=notes,
                    wheel_state=wheel_state,
                )
                if pos_id:
                    st.success(f"✅ 持仓已添加 (ID: {pos_id})")
                    st.rerun()
                else:
                    st.error("添加失败，请检查输入")

        # ===== 当前持仓 =====
        with tab_open:
            open_positions = self.portfolio_store.get_positions(status="open")
            summary = self.portfolio_store.get_portfolio_summary()

            # 汇总指标
            st.subheader("💼 组合概览")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("持仓数", summary.get('open_count', 0))
            m2.metric("已收权利金",
                      format_currency(summary.get('total_premium_collected', 0)))
            m3.metric("已实现盈亏",
                      format_currency(summary.get('realized_pnl', 0)))
            m4.metric("已平仓数", summary.get('closed_count', 0))

            if open_positions:
                st.subheader("📂 当前持仓")
                pos_df = pd.DataFrame(open_positions)
                display_cols = ['id', 'symbol', 'strategy_type', 'strike',
                                'expiry_date', 'contracts',
                                'premium_per_contract', 'open_date', 'notes']
                display_cols = [c for c in display_cols if c in pos_df.columns]
                st.dataframe(pos_df[display_cols], width='stretch',
                             hide_index=True)

                # 平仓操作
                st.subheader("🔒 平仓 / 删除")
                pos_options = {
                    f"#{p['id']} {p['symbol']} {format_strategy_name(p['strategy_type'])} ${p['strike']}": p['id']
                    for p in open_positions
                }
                selected_label = st.selectbox("选择持仓",
                                              options=list(pos_options.keys()),
                                              key="port_close_select")
                selected_id = pos_options[selected_label]

                c1, c2 = st.columns(2)
                with c1:
                    close_premium = st.number_input(
                        "平仓权利金 ($/张)", min_value=0.0, value=0.0,
                        step=0.05, key="port_close_prem"
                    )
                    if st.button("🔒 平仓", type="primary",
                                 key="port_close_btn"):
                        if self.portfolio_store.close_position(
                                selected_id, close_premium):
                            st.success("持仓已平仓")
                            st.rerun()
                with c2:
                    if st.button("🗑️ 删除持仓", key="port_delete_btn"):
                        if self.portfolio_store.delete_position(selected_id):
                            st.success("持仓已删除")
                            st.rerun()

                # ===== 滚仓建议 =====
                st.subheader("🔄 滚仓建议")
                st.caption("选择一个持仓，输入当前股价，获取滚仓方案")

                roll_pos_options = {
                    f"#{p['id']} {p['symbol']} {format_strategy_name(p['strategy_type'])} ${p['strike']}": p
                    for p in open_positions
                }
                roll_selected_label = st.selectbox(
                    "选择持仓进行滚仓分析",
                    options=list(roll_pos_options.keys()),
                    key="roll_pos_select"
                )
                roll_position = roll_pos_options[roll_selected_label]

                current_price = st.number_input(
                    f"当前 {roll_position['symbol']} 股价 ($)",
                    min_value=0.01, value=float(roll_position['strike']),
                    step=0.5, key="roll_stock_price"
                )

                # 快速建议
                quick_rec = RollAdvisor.get_roll_recommendation(
                    roll_position, current_price)
                st.info(quick_rec)

                if st.button("📊 生成滚仓方案", type="primary",
                             key="roll_generate_btn"):
                    suggestions = self.roll_advisor.suggest_rolls(
                        roll_position, current_price)

                    if suggestions:
                        roll_data = []
                        for s in suggestions:
                            roll_data.append({
                                '方案': s['label'],
                                '新Strike': f"${s['new_strike']:.0f}",
                                '新到期日': s['new_expiry'],
                                '新DTE': f"{s['new_dte']}天",
                                '预估净收支': RollAdvisor.format_credit(
                                    s['estimated_credit']),
                                '说明': s['rationale'],
                            })
                        st.dataframe(
                            pd.DataFrame(roll_data),
                            width='stretch',
                            hide_index=True
                        )
                    else:
                        st.warning("无可用滚仓方案")
            else:
                st.info("暂无持仓，请在 '添加持仓' 页签新增")

        # ===== 已平仓记录 =====
        with tab_closed:
            closed_positions = self.portfolio_store.get_positions(
                status="closed")
            if closed_positions:
                st.subheader("✅ 已平仓记录")
                closed_df = pd.DataFrame(closed_positions)
                # 计算每笔盈亏
                closed_df['pnl'] = (
                    (closed_df['premium_per_contract']
                     - closed_df['close_premium'].fillna(0))
                    * closed_df['contracts'] * 100
                )
                display_cols = ['id', 'symbol', 'strategy_type', 'strike',
                                'expiry_date', 'contracts',
                                'premium_per_contract', 'close_premium',
                                'pnl', 'open_date', 'close_date']
                display_cols = [c for c in display_cols
                                if c in closed_df.columns]
                st.dataframe(closed_df[display_cols],
                             width='stretch', hide_index=True)

                total_pnl = closed_df['pnl'].sum()
                if total_pnl >= 0:
                    st.success(f"总已实现盈亏: {format_currency(total_pnl)}")
                else:
                    st.error(f"总已实现盈亏: {format_currency(total_pnl)}")
            else:
                st.info("暂无已平仓记录")

        # ===== 分析历史 =====
        with tab_history:
            history = self.portfolio_store.get_analysis_history(limit=20)
            if history:
                st.subheader("📜 历史分析记录")
                hist_df = pd.DataFrame(history)
                st.dataframe(hist_df, width='stretch',
                             hide_index=True)
            else:
                st.info("暂无分析历史，运行分析后将自动保存")

        # ===== Greeks 概览 =====
        with tab_greeks:
            st.subheader("Σ 风险希腊字母 (Greeks)")
            greeks_data = self.portfolio_store.get_portfolio_greeks()
            
            # 总体指标
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Total Delta", f"{greeks_data.get('total_delta', 0):.2f}",
                     help="正Delta表示看多，负Delta表示看空")
            g2.metric("Total Theta", f"{greeks_data.get('total_theta', 0):.2f}",
                     help="每日时间价值损耗收益")
            g3.metric("Total Gamma", f"{greeks_data.get('total_gamma', 0):.4f}",
                     help="Delta随股价变化的敏感度")
            g4.metric("Total Vega", f"{greeks_data.get('total_vega', 0):.2f}",
                     help="波动率每变动1%的盈亏影响")
            
            # 分标的分布
            if greeks_data.get('by_symbol'):
                st.subheader("📊 标的风险分布")
                by_symbol = pd.DataFrame(greeks_data['by_symbol']).T
                st.dataframe(by_symbol.style.format("{:.2f}"))
            
            # 更新 Greeks
            st.divider()
            st.subheader("📝 更新持仓 Greeks")
            st.caption("由于缺乏实时期权链数据，请手动更新当前 Greeks")
            
            open_positions = self.portfolio_store.get_positions(status="open")
            if open_positions:
                greeks_opts = {
                    f"#{p['id']} {p['symbol']} {format_strategy_name(p['strategy_type'])} ${p['strike']}": p
                    for p in open_positions
                }
                selected_g_label = st.selectbox("选择持仓更新", 
                                              options=list(greeks_opts.keys()),
                                              key="greeks_update_select")
                selected_g_pos = greeks_opts[selected_g_label]
                
                c1, c2, c3, c4 = st.columns(4)
                new_delta = c1.number_input("Delta", value=float(selected_g_pos.get('delta', 0.0) or 0.0), step=0.01)
                new_theta = c2.number_input("Theta", value=float(selected_g_pos.get('theta', 0.0) or 0.0), step=0.01)
                new_gamma = c3.number_input("Gamma", value=float(selected_g_pos.get('gamma', 0.0) or 0.0), step=0.001, format="%.4f")
                new_vega = c4.number_input("Vega", value=float(selected_g_pos.get('vega', 0.0) or 0.0), step=0.01)
                
                if st.button("💾 更新 Greeks", key="greeks_save_btn"):
                    self.portfolio_store.update_position_greeks(
                        selected_g_pos['id'], new_delta, new_theta, new_gamma, new_vega
                    )
                    st.success("Greeks 已更新")
                    st.rerun()
            else:
                st.info("无持仓可更新")

        # ===== Wheel 策略跟踪 =====
        with tab_wheel:
            st.subheader("🔄 Wheel 策略状态追踪")
            
            # 状态说明图
            st.markdown("""
            ```mermaid
            graph LR
                IDLE((闲置资金)) -->|卖 Put| SP[🔵 卖出 Put]
                SP -->|过期| SP
                SP -->|行权| AS[🟡 持有正股]
                AS -->|卖 Call| SC[🟠 卖出 Call]
                SC -->|过期| SC
                SC -->|被叫走| CA[🟢 现金回归]
                CA --> IDLE
            ```
            """)
            
            wheel_positions = self.portfolio_store.get_wheel_positions()
            if wheel_positions:
                st.dataframe(
                    pd.DataFrame([{
                        'Symbol': p['symbol'],
                        '策略': format_strategy_name(p['strategy_type']),
                        '当前状态': PortfolioStore.WHEEL_STATES.get(p['wheel_state'], p['wheel_state']),
                        '开仓日期': p['open_date'],
                        '备注': p['notes']
                    } for p in wheel_positions]),
                    width='stretch'
                )
                
                # 状态流转
                st.divider()
                st.subheader("🔀 状态流转")
                
                w_opts = {f"#{p['id']} {p['symbol']}": p for p in wheel_positions}
                w_sel_label = st.selectbox("选择持仓", options=list(w_opts.keys()), key="wheel_pos_select")
                w_pos = w_opts[w_sel_label]
                
                current_state = w_pos.get('wheel_state', 'idle')
                st.info(f"当前状态: {PortfolioStore.WHEEL_STATES.get(current_state, current_state)}")
                
                new_state = st.selectbox(
                    "流转到新状态", 
                    options=['sell_put', 'assigned', 'sell_call', 'called_away', 'idle'],
                    format_func=lambda x: PortfolioStore.WHEEL_STATES.get(x, x),
                    key="wheel_new_state"
                )
                
                if st.button("➡️ 确认流转", key="wheel_update_btn"):
                    self.portfolio_store.update_wheel_state(w_pos['id'], new_state)
                    st.success(f"状态已更新为: {PortfolioStore.WHEEL_STATES.get(new_state)}")
                    st.rerun()
            else:
                st.info("暂无 Wheel 策略持仓。在'添加持仓'时选择 Wheel 状态即可追踪。")

def main():
    """主函数"""
    app = OptionsToolApp()
    app.run()

if __name__ == "__main__":
    main()

