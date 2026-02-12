"""
基础测试文件
Basic tests for the options tool
"""
import unittest
from unittest.mock import patch
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.option_analytics.pricing import BlackScholesCalculator, ProbabilityCalculator, OptionAnalyzer
from src.risk_management.risk_manager import RiskCalculator, PositionSizer, RiskManager
from src.screening.screener import OptionsScreener
from src.data_collector.data_manager import DataManager

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


class TestDataManagerCaching(unittest.TestCase):
    """测试DataManager在同一轮筛选中的缓存行为"""

    def test_get_complete_stock_data_uses_memory_cache(self):
        manager = DataManager()

        with patch.object(manager.stock_collector, 'get_stock_info', return_value={'current_price': 100, 'symbol': 'AAPL'}) as m_info, \
             patch.object(manager.stock_collector, 'get_historical_data') as m_hist, \
             patch.object(manager.options_collector, 'get_all_expirations', return_value=[]):
            import pandas as pd
            m_hist.return_value = pd.DataFrame({'Volatility': [0.2]})

            first = manager.get_complete_stock_data('AAPL')
            second = manager.get_complete_stock_data('AAPL')

            self.assertTrue(first)
            self.assertTrue(second)
            self.assertEqual(m_info.call_count, 1)

    def test_get_trading_opportunities_uses_memory_cache(self):
        manager = DataManager()

        fake_stock_data = {
            'basic_info': {'current_price': 100},
            'expirations': [],
            'historical_data': {},
            'current_volatility': 0.2
        }

        with patch.object(manager, 'get_complete_stock_data', return_value=fake_stock_data) as m_complete:
            first = manager.get_trading_opportunities(['AAPL'])
            second = manager.get_trading_opportunities(['AAPL'])

            self.assertEqual(first, second)
            self.assertEqual(m_complete.call_count, 1)


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
        TestDataManagerCaching
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
        print("🎉 所有测试都通过了!")
    else:
        print(f"⚠️  有 {failed_tests} 个测试失败")

if __name__ == "__main__":
    run_all_tests()