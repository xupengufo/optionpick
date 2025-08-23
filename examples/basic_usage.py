"""
美股期权卖方推荐工具使用示例
Usage examples for US Options Selling Recommendation Tool
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_collector.data_manager import DataManager
from src.screening.screener import OptionsScreener
from src.risk_management.risk_manager import RiskManager
from src.visualization.charts import OptionsVisualizer
import pandas as pd

def example_basic_screening():
    """基础筛选示例"""
    print("=== 基础期权筛选示例 ===")
    
    # 初始化组件
    screener = OptionsScreener()
    
    # 设置要分析的股票
    symbols = ["AAPL", "MSFT", "TSLA"]
    
    print(f"正在分析股票: {', '.join(symbols)}")
    
    try:
        # 筛选备兑看涨期权机会
        covered_calls = screener.screen_covered_calls(symbols)
        print(f"\n找到 {len(covered_calls)} 个备兑看涨期权机会:")
        
        for i, opp in enumerate(covered_calls[:3], 1):
            print(f"\n{i}. {opp['symbol']} ${opp['strike']:.0f} Call")
            print(f"   到期日: {opp['expiry_date']}")
            print(f"   年化收益率: {opp['returns']['annualized_yield']:.1f}%")
            print(f"   盈利概率: {opp['probabilities']['prob_profit_short']:.1f}%")
            print(f"   得分: {opp.get('score', 0):.1f}")
        
        # 筛选现金担保看跌期权机会
        cash_secured_puts = screener.screen_cash_secured_puts(symbols)
        print(f"\n\n找到 {len(cash_secured_puts)} 个现金担保看跌期权机会:")
        
        for i, opp in enumerate(cash_secured_puts[:3], 1):
            print(f"\n{i}. {opp['symbol']} ${opp['strike']:.0f} Put")
            print(f"   到期日: {opp['expiry_date']}")
            print(f"   年化收益率: {opp['returns']['annualized_yield']:.1f}%")
            print(f"   盈利概率: {opp['probabilities']['prob_profit_short']:.1f}%")
            print(f"   得分: {opp.get('score', 0):.1f}")
        
    except Exception as e:
        print(f"筛选过程中出现错误: {e}")
        print("这可能是由于网络连接问题或API限制导致的")

def example_risk_analysis():
    """风险分析示例"""
    print("\n\n=== 风险分析示例 ===")
    
    # 模拟一个期权机会数据
    mock_opportunity = {
        'symbol': 'AAPL',
        'strategy_type': 'covered_call',
        'stock_price': 150.0,
        'strike': 155.0,
        'expiry_date': '2024-01-19',
        'days_to_expiry': 30,
        'returns': {
            'max_profit': 200.0,
            'max_loss': 15000.0,
            'annualized_yield': 15.0
        },
        'probabilities': {
            'prob_profit_short': 65.0
        },
        'greeks': {
            'delta': 0.3,
            'gamma': 0.02,
            'theta': -0.05,
            'vega': 0.15
        }
    }
    
    # 初始化风险管理器
    risk_manager = RiskManager(initial_capital=100000)
    
    # 分析交易风险
    risk_analysis = risk_manager.analyze_trade_risk(mock_opportunity, 100000)
    
    print("风险分析结果:")
    print(f"建议: {risk_analysis['recommendation']}")
    print(f"原因: {risk_analysis['reason']}")
    print(f"风险等级: {risk_analysis.get('risk_level', '未知')}")
    
    risk_metrics = risk_analysis.get('risk_metrics', {})
    print(f"\n风险指标:")
    print(f"最大损失: ${risk_metrics.get('max_loss', 0):,.2f}")
    print(f"最大收益: ${risk_metrics.get('max_profit', 0):,.2f}")
    print(f"风险收益比: {risk_metrics.get('risk_reward_ratio', 0):.1f}")
    print(f"资金风险比例: {risk_metrics.get('capital_at_risk_pct', 0):.1f}%")
    
    sizing_info = risk_analysis.get('sizing_info', {})
    print(f"\n头寸建议:")
    print(f"推荐合约数: {sizing_info.get('recommended_size', 0)}")
    print(f"保证金需求: ${sizing_info.get('margin_required', 0):,.2f}")
    print(f"实际风险金额: ${sizing_info.get('actual_risk_amount', 0):,.2f}")

def example_market_analysis():
    """市场分析示例"""
    print("\n\n=== 市场分析示例 ===")
    
    # 初始化数据管理器
    data_manager = DataManager()
    
    try:
        # 获取市场环境
        market_context = data_manager.get_market_context()
        
        print("当前市场环境:")
        print(f"VIX水平: {market_context.get('vix', 0):.1f}")
        print(f"市场状态: {market_context.get('market_regime', '未知')}")
        print(f"卖方吸引力: {market_context.get('selling_attractiveness', '未知')}")
        print(f"SPY动量: {market_context.get('spy_momentum', 0):.1f}%")
        
        # 验证股票代码
        symbols_to_test = ["AAPL", "MSFT", "INVALID"]
        print(f"\n验证股票代码:")
        
        for symbol in symbols_to_test:
            is_valid = data_manager.validate_symbol(symbol)
            print(f"{symbol}: {'有效' if is_valid else '无效'}")
        
    except Exception as e:
        print(f"市场分析过程中出现错误: {e}")

def example_complete_workflow():
    """完整工作流程示例"""
    print("\n\n=== 完整工作流程示例 ===")
    
    try:
        # 1. 初始化所有组件
        print("1. 初始化组件...")
        data_manager = DataManager()
        screener = OptionsScreener()
        risk_manager = RiskManager(initial_capital=100000)
        
        # 2. 获取市场环境
        print("2. 获取市场环境...")
        market_context = data_manager.get_market_context()
        print(f"   市场状态: {market_context.get('market_regime', '未知')}")
        
        # 3. 筛选交易机会
        print("3. 筛选交易机会...")
        symbols = ["AAPL", "MSFT"]
        top_opportunities = screener.get_top_opportunities(symbols, max_results=5)
        print(f"   找到 {len(top_opportunities)} 个机会")
        
        # 4. 分析最佳机会
        if top_opportunities:
            best_opportunity = top_opportunities[0]
            print(f"\n4. 分析最佳机会: {best_opportunity.get('symbol', '')} {best_opportunity.get('strategy_type', '')}")
            
            # 风险分析
            risk_analysis = risk_manager.analyze_trade_risk(best_opportunity, 100000)
            print(f"   建议: {risk_analysis['recommendation']}")
            print(f"   风险等级: {risk_analysis['risk_level']}")
            print(f"   推荐头寸: {risk_analysis['sizing_info']['recommended_size']} 合约")
        
        print("\n工作流程完成!")
        
    except Exception as e:
        print(f"工作流程中出现错误: {e}")
        print("这可能是由于网络连接或数据源问题导致的")

def example_data_formats():
    """数据格式示例"""
    print("\n\n=== 数据格式示例 ===")
    
    # 期权数据格式示例
    option_data_example = {
        'type': 'call',
        'strike': 150.0,
        'lastPrice': 2.50,
        'bid': 2.45,
        'ask': 2.55,
        'volume': 150,
        'openInterest': 500,
        'impliedVolatility': 0.25,
        'inTheMoney': False,
        'contractSymbol': 'AAPL240119C00150000'
    }
    
    print("期权数据格式示例:")
    for key, value in option_data_example.items():
        print(f"  {key}: {value}")
    
    # 策略分析结果格式示例
    strategy_result_example = {
        'symbol': 'AAPL',
        'strategy_type': 'covered_call',
        'stock_price': 150.0,
        'strike': 155.0,
        'returns': {
            'max_profit': 200.0,
            'max_loss': 15000.0,
            'annualized_yield': 15.0
        },
        'probabilities': {
            'prob_profit_short': 65.0,
            'prob_expire_worthless': 70.0
        },
        'greeks': {
            'delta': 0.3,
            'theta': -0.05,
            'vega': 0.15
        },
        'score': 85.5
    }
    
    print("\n策略分析结果格式示例:")
    for key, value in strategy_result_example.items():
        print(f"  {key}: {value}")

def main():
    """运行所有示例"""
    print("美股期权卖方推荐工具 - 使用示例")
    print("=" * 50)
    
    # 运行基础示例（不需要网络连接）
    example_data_formats()
    example_risk_analysis()
    
    # 运行需要网络连接的示例
    print("\n注意: 以下示例需要网络连接和有效的数据源")
    print("如果出现错误，通常是由于网络连接或API限制导致的")
    
    try:
        example_market_analysis()
        example_basic_screening()
        example_complete_workflow()
        
    except KeyboardInterrupt:
        print("\n\n用户中断执行")
    except Exception as e:
        print(f"\n示例执行过程中出现错误: {e}")
        print("请检查网络连接和依赖包安装")
    
    print("\n=" * 50)
    print("示例运行完成!")
    print("\n要启动完整的Web界面，请运行:")
    print("streamlit run main.py")

if __name__ == "__main__":
    main()