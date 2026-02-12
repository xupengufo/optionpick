"""
基础测试文件
Basic tests for the options tool
"""
import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.option_analytics.pricing import BlackScholesCalculator, ProbabilityCalculator, OptionAnalyzer
from src.risk_management.risk_manager import RiskCalculator, PositionSizer, RiskManager
from src.screening.screener import OptionsScreener
from src.visualization.charts import OptionsVisualizer
from src.data_collector.github_pools import GitHubStockPoolProvider

class TestBlackScholesCalculator(unittest.TestCase):
    """测试Black-Scholes计算器"""
    
    def setUp(self):
        self.bs_calc = BlackScholesCalculator()
    
    def test_option_price_call(self):
        """测试看涨期权定价"""
        price = self.bs_calc.option_price(
            S=100, K=105, T=0.25, r=0.05, sigma=0.2, option_type='call'
        )
        self.assertGreater(price, 0)
        self.assertLess(price, 100)
    
    def test_option_price_put(self):
        """测试看跌期权定价"""
        price = self.bs_calc.option_price(
            S=100, K=105, T=0.25, r=0.05, sigma=0.2, option_type='put'
        )
        self.assertGreater(price, 0)
        self.assertLess(price, 105)
    
    def test_greeks_calculation(self):
        """测试Greeks计算"""
        greeks = self.bs_calc.calculate_greeks(
            S=100, K=105, T=0.25, r=0.05, sigma=0.2, option_type='call'
        )
        
        # 检查所有Greeks是否存在
        required_greeks = ['delta', 'gamma', 'theta', 'vega', 'rho']
        for greek in required_greeks:
            self.assertIn(greek, greeks)
        
        # 看涨期权Delta应该在0到1之间
        self.assertGreater(greeks['delta'], 0)
        self.assertLess(greeks['delta'], 1)
        
        # Gamma应该大于0
        self.assertGreater(greeks['gamma'], 0)
    
    def test_zero_time_to_expiry(self):
        """测试零到期时间的情况"""
        # 实值看涨期权
        price = self.bs_calc.option_price(
            S=110, K=100, T=0, r=0.05, sigma=0.2, option_type='call'
        )
        self.assertAlmostEqual(price, 10, places=2)
        
        # 虚值看涨期权
        price = self.bs_calc.option_price(
            S=90, K=100, T=0, r=0.05, sigma=0.2, option_type='call'
        )
        self.assertAlmostEqual(price, 0, places=2)

class TestProbabilityCalculator(unittest.TestCase):
    """测试概率计算器"""
    
    def setUp(self):
        self.prob_calc = ProbabilityCalculator()
    
    def test_profit_probability(self):
        """测试盈利概率计算"""
        prob = self.prob_calc.prob_profit_short_option(
            S=100, K=105, premium=2, T=0.25, sigma=0.2, option_type='call'
        )
        self.assertGreater(prob, 0)
        self.assertLess(prob, 1)
    
    def test_expire_worthless_probability(self):
        """测试期权价值为零的概率"""
        prob = self.prob_calc.prob_expire_worthless(
            S=100, K=105, T=0.25, sigma=0.2, option_type='call'
        )
        self.assertGreater(prob, 0)
        self.assertLess(prob, 1)
    
    def test_expected_move(self):
        """测试预期移动计算"""
        lower, upper = self.prob_calc.expected_move(S=100, T=0.25, sigma=0.2)
        self.assertLess(lower, 100)
        self.assertGreater(upper, 100)
        self.assertGreater(upper - lower, 0)

    def test_short_option_profit_probability_direction(self):
        """测试卖方盈利概率方向是否正确"""
        # short call: breakeven 远高于现价，应为高盈利概率
        call_high = self.prob_calc.prob_profit_short_option(
            S=100, K=150, premium=0, T=0.25, sigma=0.2, option_type='call'
        )
        # short call: breakeven 远低于现价，应为低盈利概率
        call_low = self.prob_calc.prob_profit_short_option(
            S=100, K=50, premium=0, T=0.25, sigma=0.2, option_type='call'
        )
        self.assertGreater(call_high, 0.95)
        self.assertLess(call_low, 0.05)

        # short put: breakeven 远低于现价，应为高盈利概率
        put_high = self.prob_calc.prob_profit_short_option(
            S=100, K=50, premium=0, T=0.25, sigma=0.2, option_type='put'
        )
        # short put: breakeven 远高于现价，应为低盈利概率
        put_low = self.prob_calc.prob_profit_short_option(
            S=100, K=150, premium=0, T=0.25, sigma=0.2, option_type='put'
        )
        self.assertGreater(put_high, 0.95)
        self.assertLess(put_low, 0.05)

class TestRiskCalculator(unittest.TestCase):
    """测试风险计算器"""
    
    def setUp(self):
        self.risk_calc = RiskCalculator(initial_capital=100000)
    
    def test_position_risk_covered_call(self):
        """测试备兑看涨期权头寸风险"""
        strategy_analysis = {
            'strategy_type': 'covered_call',
            'stock_price': 100,
            'strike': 105,
            'returns': {
                'max_profit': 200,
                'max_loss': 10000
            }
        }
        
        risk = self.risk_calc.calculate_position_risk(strategy_analysis, position_size=1)
        
        self.assertIn('max_profit', risk)
        self.assertIn('max_loss', risk)
        self.assertIn('capital_at_risk_pct', risk)
        self.assertGreater(risk['max_profit'], 0)
        self.assertGreater(risk['max_loss'], 0)
    
    def test_position_risk_cash_secured_put(self):
        """测试现金担保看跌期权头寸风险"""
        strategy_analysis = {
            'strategy_type': 'cash_secured_put',
            'stock_price': 100,
            'strike': 95,
            'returns': {
                'max_profit': 150,
                'max_loss': 9350
            }
        }
        
        risk = self.risk_calc.calculate_position_risk(strategy_analysis, position_size=1)
        
        self.assertGreater(risk['max_profit'], 0)
        self.assertGreater(risk['max_loss'], 0)
        self.assertLess(risk['capital_at_risk_pct'], 100)

class TestPositionSizer(unittest.TestCase):
    """测试头寸规模计算器"""
    
    def setUp(self):
        self.position_sizer = PositionSizer()
    
    def test_optimal_size_calculation(self):
        """测试最优头寸大小计算"""
        strategy_analysis = {
            'strategy_type': 'covered_call',
            'stock_price': 100,
            'strike': 105,
            'returns': {
                'max_profit': 200,
                'max_loss': 500
            }
        }
        
        sizing = self.position_sizer.calculate_optimal_size(strategy_analysis, 100000)
        
        self.assertIn('recommended_size', sizing)
        self.assertIn('actual_risk_pct', sizing)
        self.assertGreaterEqual(sizing['recommended_size'], 0)
    
    def test_high_risk_scenario(self):
        """测试高风险情况"""
        strategy_analysis = {
            'strategy_type': 'short_strangle',
            'stock_price': 100,
            'returns': {
                'max_profit': 100,
                'max_loss': 50000  # 非常高的最大损失
            }
        }
        
        sizing = self.position_sizer.calculate_optimal_size(strategy_analysis, 100000)
        
        # 应该推荐很小的头寸或者0
        self.assertLessEqual(sizing['recommended_size'], 1)

class TestRiskManager(unittest.TestCase):
    """测试风险管理器"""
    
    def setUp(self):
        self.risk_manager = RiskManager(initial_capital=100000)
    
    def test_analyze_trade_risk(self):
        """测试交易风险分析"""
        strategy_analysis = {
            'strategy_type': 'covered_call',
            'stock_price': 100,
            'strike': 105,
            'returns': {
                'max_profit': 200,
                'max_loss': 500
            },
            'probabilities': {
                'prob_profit_short': 70
            },
            'greeks': {
                'delta': 0.3
            }
        }
        
        analysis = self.risk_manager.analyze_trade_risk(strategy_analysis, 100000)
        
        self.assertIn('recommendation', analysis)
        self.assertIn('risk_level', analysis)
        self.assertIn('position_risk', analysis)
        self.assertIn('sizing_info', analysis)
        
        # 建议应该是有效的
        valid_recommendations = ['STRONG_BUY', 'BUY', 'HOLD', 'CAUTION', 'AVOID', 'ERROR']
        self.assertIn(analysis['recommendation'], valid_recommendations)

class TestOptionsScreenerConfigEnforcement(unittest.TestCase):
    """测试筛选配置是否被真正执行"""

    def setUp(self):
        self.screener = OptionsScreener()

    def test_covered_call_respects_profit_probability_and_min_return(self):
        self.screener.config.update({
            'min_delta': 0.1,
            'max_delta': 0.5,
            'min_profit_probability': 70,
            'min_annualized_return': 10,
        })

        low_prob = {
            'greeks': {'delta': 0.2},
            'returns': {'annualized_yield': 20},
            'probabilities': {'prob_profit_short': 60},
        }
        self.assertFalse(self.screener._validate_covered_call(low_prob))

        low_return = {
            'greeks': {'delta': 0.2},
            'returns': {'annualized_yield': 8},
            'probabilities': {'prob_profit_short': 80},
        }
        self.assertFalse(self.screener._validate_covered_call(low_return))

        valid = {
            'greeks': {'delta': 0.2},
            'returns': {'annualized_yield': 12},
            'probabilities': {'prob_profit_short': 80},
        }
        self.assertTrue(self.screener._validate_covered_call(valid))

    def test_short_strangle_respects_min_return(self):
        self.screener.config.update({
            'min_profit_probability': 40,
            'min_annualized_return': 15,
        })

        insufficient = {
            'returns': {
                'profit_probability': 50,
                'net_credit': 200,
                'annualized_yield': 10,
            }
        }
        self.assertFalse(self.screener._validate_short_strangle(insufficient))

        valid = {
            'returns': {
                'profit_probability': 50,
                'net_credit': 200,
                'annualized_yield': 20,
            }
        }
        self.assertTrue(self.screener._validate_short_strangle(valid))

    def test_top_opportunities_balances_strategy_mix(self):
        self.screener.config.update({'max_results_per_strategy_total': 1})

        def _make_opp(strategy_type, score):
            return {
                'strategy_type': strategy_type,
                'symbol': 'TEST',
                'score': score
            }

        self.screener.screen_all_strategies = lambda symbols: {
            'bear_call_spreads': [
                _make_opp('bear_call_spread', 99),
                _make_opp('bear_call_spread', 98),
                _make_opp('bear_call_spread', 97),
            ],
            'cash_secured_puts': [
                _make_opp('cash_secured_put', 60),
                _make_opp('cash_secured_put', 59),
            ]
        }

        results = self.screener.get_top_opportunities(['TEST'], max_results=3)
        types = [r.get('strategy_type') for r in results]
        self.assertIn('bear_call_spread', types)
        self.assertIn('cash_secured_put', types)


class TestStrategySchemaConsistency(unittest.TestCase):
    """测试策略输出字段一致性"""

    def test_short_strangle_contains_annualized_yield(self):
        from src.option_analytics.strategies import StrategyAnalyzer

        analyzer = StrategyAnalyzer()
        call_data = {
            'type': 'call',
            'strike': 105,
            'lastPrice': 1.2,
            'bid': 1.1,
            'ask': 1.3,
            'volume': 100,
            'openInterest': 200,
            'impliedVolatility': 0.2
        }
        put_data = {
            'type': 'put',
            'strike': 95,
            'lastPrice': 1.1,
            'bid': 1.0,
            'ask': 1.2,
            'volume': 120,
            'openInterest': 240,
            'impliedVolatility': 0.22
        }

        result = analyzer.analyze_short_strangle(100, call_data, put_data, 30)
        self.assertIn('returns', result)
        self.assertIn('annualized_yield', result['returns'])
        self.assertGreaterEqual(result['returns']['annualized_yield'], 0)


class TestOptionsVisualizer(unittest.TestCase):
    """测试可视化收益与IV Rank计算"""

    def setUp(self):
        self.visualizer = OptionsVisualizer(style="light")

    def test_spread_payoff_not_flat(self):
        prices = np.array([80.0, 100.0, 120.0])

        bull_put = {
            'strategy_type': 'bull_put_spread',
            'strikes': {'put_short': 95, 'put_long': 90},
            'returns': {'net_credit': 120}
        }
        bull_payoff = self.visualizer._calculate_payoffs(bull_put, prices)
        self.assertLess(bull_payoff[0], bull_payoff[1])
        self.assertEqual(bull_payoff[1], 120)
        self.assertEqual(bull_payoff[2], 120)

        bear_call = {
            'strategy_type': 'bear_call_spread',
            'strikes': {'call_short': 105, 'call_long': 110},
            'returns': {'net_credit': 150}
        }
        bear_payoff = self.visualizer._calculate_payoffs(bear_call, prices)
        self.assertEqual(bear_payoff[0], 150)
        self.assertEqual(bear_payoff[1], 150)
        self.assertLess(bear_payoff[2], bear_payoff[1])

    def test_iv_rank_estimation(self):
        stock_data = {
            'current_volatility': 0.35,
            'historical_data': {
                'Volatility': {'a': 0.1, 'b': 0.2, 'c': 0.3, 'd': 0.4}
            }
        }
        iv_rank = self.visualizer._estimate_iv_rank(stock_data)
        self.assertGreaterEqual(iv_rank, 70)
        self.assertLessEqual(iv_rank, 80)

        fallback_rank = self.visualizer._estimate_iv_rank({'current_volatility': 0})
        self.assertEqual(fallback_rank, 50.0)


class TestGitHubStockPoolProvider(unittest.TestCase):
    """测试 GitHub 股票池加载与精选逻辑"""

    def test_normalize_symbols(self):
        symbols = GitHubStockPoolProvider._normalize_symbols(
            ["aapl", "AAPL", " msft ", "BRK.B", "INVALID-1", "", None]
        )
        self.assertEqual(symbols, ["AAPL", "MSFT", "BRK.B"])

    def test_curated_prefers_popular_symbols(self):
        cfg = {
            "sources": {
                "sp500": {
                    "url": "unused",
                    "symbol_columns": ["Symbol"]
                }
            }
        }
        provider = GitHubStockPoolProvider(
            cfg,
            preferred_symbols=["MSFT", "AAPL", "NVDA"]
        )
        curated = provider._build_curated(
            ["AAPL", "GOOGL", "MSFT", "TSLA"],
            size=3
        )
        # 优先保留热门列表中的成分股，再补齐
        self.assertEqual(curated, ["MSFT", "AAPL", "GOOGL"])


class TestSpreadPairOrdering(unittest.TestCase):
    """测试价差配对在常见升序链表下可正常产出机会"""

    def test_bull_put_spread_handles_ascending_put_chain(self):
        screener = OptionsScreener()
        screener.config.update({
            'min_volume': 1,
            'min_open_interest': 1,
            'spread_width_min': 2,
            'spread_width_max': 10,
            'max_results_per_symbol': 10,
        })

        class DummyDataManager:
            def get_trading_opportunities(self, symbols, target_dte_range=(14, 45)):
                return {
                    'TEST': {
                        'stock_data': {
                            'basic_info': {
                                'current_price': 105.0,
                                'days_to_earnings': None,
                                'next_earnings_date': None,
                            }
                        },
                        'opportunities': [{
                            'expiry_date': '2099-01-01',
                            'days_to_expiry': 30,
                            # 常见情况：按 strike 升序
                            'options_data': {
                                'puts': [
                                    {'strike': 90, 'bid': 0.5, 'ask': 0.55, 'volume': 100, 'openInterest': 200},
                                    {'strike': 95, 'bid': 1.0, 'ask': 1.08, 'volume': 100, 'openInterest': 200},
                                    {'strike': 100, 'bid': 2.0, 'ask': 2.16, 'volume': 100, 'openInterest': 200},
                                ],
                                'calls': [],
                            }
                        }]
                    }
                }

        class DummyStrategyAnalyzer:
            @staticmethod
            def analyze_bull_put_spread(stock_price, short_put, long_put, days_to_expiry):
                return {
                    'strategy_type': 'bull_put_spread',
                    'strike': short_put['strike'],
                    'returns': {
                        'net_credit': 100,
                        'annualized_yield': 20,
                        'max_profit': 100,
                        'max_loss': 300,
                        'profit_probability': 60,
                    },
                    'probabilities': {'prob_profit_short': 60},
                    'greeks': {'delta': 0.2},
                    'option_details': {'liquidity': {'volume': 100, 'open_interest': 200, 'bid_ask_spread_pct': 5}},
                }

            @staticmethod
            def rank_selling_opportunities(opportunities):
                return opportunities

        screener.data_manager = DummyDataManager()
        screener.strategy_analyzer = DummyStrategyAnalyzer()
        results = screener.screen_bull_put_spreads(['TEST'])
        self.assertGreater(len(results), 0)


def run_all_tests():
    """运行所有测试"""
    print("运行期权工具基础测试...")
    print("=" * 50)
    
    # 创建测试套件
    test_classes = [
        TestBlackScholesCalculator,
        TestProbabilityCalculator,
        TestRiskCalculator,
        TestPositionSizer,
        TestRiskManager,
        TestOptionsScreenerConfigEnforcement,
        TestStrategySchemaConsistency,
        TestOptionsVisualizer,
        TestGitHubStockPoolProvider,
        TestSpreadPairOrdering
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n测试 {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        class_total = result.testsRun
        class_failed = len(result.failures) + len(result.errors)
        class_passed = class_total - class_failed
        
        total_tests += class_total
        passed_tests += class_passed
        failed_tests += class_failed
        
        print(f"  运行: {class_total}, 通过: {class_passed}, 失败: {class_failed}")
        
        if result.failures:
            print("  失败的测试:")
            for failure in result.failures:
                print(f"    - {failure[0]}")
        
        if result.errors:
            print("  错误的测试:")
            for error in result.errors:
                print(f"    - {error[0]}")
    
    print("\n" + "=" * 50)
    print(f"测试总结:")
    print(f"总计: {total_tests}, 通过: {passed_tests}, 失败: {failed_tests}")
    print(f"成功率: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0.0%")
    
    if failed_tests == 0:
        print("[PASS] 所有测试都通过了!")
    else:
        print(f"[FAIL] 有 {failed_tests} 个测试失败")

if __name__ == "__main__":
    run_all_tests()
