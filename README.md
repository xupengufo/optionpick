# 美股期权卖方推荐工具

一个专业的期权分析和推荐系统，专门为期权卖方策略设计，帮助投资者发现和分析最优的期权卖方机会。

## 🎯 项目特色

- **智能筛选**: 基于多种指标自动筛选最优的期权卖方机会
- **风险管理**: 内置风险评估和头寸管理系统
- **策略分析**: 支持备兑看涨、现金担保看跌、宽跨式等多种策略
- **可视化分析**: 丰富的图表和收益分析
- **Web界面**: 直观的Streamlit界面，易于使用

## 📋 支持的策略

1. **备兑看涨期权 (Covered Call)**
   - 持有股票并卖出看涨期权
   - 适合中性到轻微看涨的市场观点

2. **现金担保看跌期权 (Cash Secured Put)**
   - 卖出看跌期权并准备现金购买股票
   - 适合轻微看跌到中性的市场观点

3. **卖出宽跨式 (Short Strangle)**
   - 同时卖出虚值看涨和看跌期权
   - 适合低波动性的市场环境

## 🛠️ 技术架构

### 核心模块

- **数据收集模块** (`src/data_collector/`)
  - 股票价格和期权链数据获取
  - 隐含波动率和市场情绪分析
  - 数据缓存和管理

- **期权分析引擎** (`src/option_analytics/`)
  - Black-Scholes期权定价模型
  - Greeks计算和概率分析
  - 策略收益分析

- **筛选引擎** (`src/screening/`)
  - 多维度期权筛选
  - 智能评分和排名系统
  - 预设筛选策略

- **风险管理** (`src/risk_management/`)
  - 头寸风险计算
  - 投资组合风险分析
  - 头寸规模建议

- **可视化模块** (`src/visualization/`)
  - 期权收益图表
  - 风险分析图表
  - 交互式仪表板

## 🚀 快速开始

### 1. 环境准备

确保您的系统已安装Python 3.8或更高版本。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行应用

启动Web界面：
```bash
streamlit run main.py
```

或运行示例代码：
```bash
python examples/basic_usage.py
```

### 4. 运行测试

```bash
python tests/test_basic.py
```

## 📊 使用指南

### Web界面使用

1. **设置参数**
   - 在侧边栏设置投资资金
   - 在股票池中输入要分析的股票代码（每行一个）
   - 点击"验证并应用"确认股票有效性
   - 选择筛选策略和风险偏好
   - 点击"开始分析"

2. **股票代码输入**
   - 支持任意美股代码（如AAPL、MSFT、TSLA等）
   - 每行输入一个股票代码
   - 系统会自动验证代码有效性
   - 支持个股、ETF等各类交易品种

3. **查看结果**
   - **市场概览**: 查看当前市场环境和VIX指数
   - **机会筛选**: 浏览筛选出的期权机会
   - **详细分析**: 深入分析具体的期权策略
   - **风险管理**: 评估交易风险和头寸建议

### 编程接口使用

```python
from src.screening.screener import OptionsScreener
from src.risk_management.risk_manager import RiskManager

# 初始化筛选器
screener = OptionsScreener()

# 筛选期权机会
symbols = ["AAPL", "MSFT", "TSLA"]
opportunities = screener.get_top_opportunities(symbols, max_results=10)

# 风险分析
risk_manager = RiskManager(initial_capital=100000)
for opp in opportunities:
    risk_analysis = risk_manager.analyze_trade_risk(opp, 100000)
    print(f"{opp['symbol']}: {risk_analysis['recommendation']}")
```

## 📈 功能特性

### 智能筛选功能

- **流动性筛选**: 自动过滤低流动性期权
- **时间筛选**: 基于到期时间的智能筛选
- **Greeks筛选**: Delta、Theta、Vega等指标筛选
- **收益率筛选**: 年化收益率和盈利概率筛选

### 风险管理功能

- **头寸大小计算**: 基于风险承受能力的头寸建议
- **风险指标**: VaR、最大损失、风险收益比等
- **投资组合风险**: 整体风险评估和分散化分析
- **风险警报**: 实时风险监控和提醒

### 分析工具

- **收益图**: 期权策略的盈亏图表
- **概率分析**: 盈利概率和到期价值概率
- **时间衰减**: Theta效应和时间价值分析
- **波动率分析**: IV Rank和波动率影响

## 🔧 配置说明

主要配置文件位于 `config/config.py`，包括：

- **筛选参数**: 最小流动性、Delta范围等
- **风险参数**: 最大风险比例、保证金要求等
- **数据源配置**: API设置和缓存配置
- **可视化配置**: 图表样式和颜色方案

## 📁 项目结构

```
project/
├── src/                     # 源代码
│   ├── data_collector/      # 数据收集模块
│   ├── option_analytics/    # 期权分析引擎
│   ├── screening/           # 筛选引擎
│   ├── risk_management/     # 风险管理
│   ├── visualization/       # 可视化模块
│   └── utils/              # 工具函数
├── config/                  # 配置文件
├── data/                   # 数据目录
│   ├── cache/              # 缓存数据
│   └── output/             # 输出文件
├── examples/               # 使用示例
├── tests/                  # 测试文件
├── main.py                 # 主应用入口
└── requirements.txt        # 依赖包列表
```

## 📚 技术说明

### 期权定价模型

本工具使用Black-Scholes模型进行期权定价和Greeks计算：

- **Delta**: 期权价格对标的价格的敏感性
- **Gamma**: Delta的变化率
- **Theta**: 时间衰减效应
- **Vega**: 对隐含波动率的敏感性
- **Rho**: 对利率的敏感性

### 概率计算

- **盈利概率**: 基于对数正态分布计算
- **到期价值概率**: 期权到期时的价值分布
- **预期移动**: 1个标准差的价格移动范围

### 风险指标

- **VaR (Value at Risk)**: 在给定置信水平下的最大损失
- **Expected Shortfall**: 超过VaR的平均损失
- **夏普比率**: 风险调整后的收益率
- **最大回撤**: 历史最大损失

## ⚠️ 免责声明

本工具仅供教育和研究目的使用，不构成投资建议。期权交易具有高风险，可能导致全部投资损失。在进行任何投资决策之前，请：

1. 充分了解期权交易的风险
2. 咨询专业的财务顾问
3. 仔细阅读相关的风险披露文件
4. 确保您有足够的风险承受能力

## 🤝 贡献指南

欢迎贡献代码和改进建议！请遵循以下步骤：

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 详情请查看 [LICENSE](LICENSE) 文件。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 创建Issue报告问题
- 发送Pull Request提交改进
- 在讨论区分享使用经验

---

**注意**: 本工具依赖第三方数据源，可能会受到API限制或数据延迟的影响。请确保遵守相关数据提供商的使用条款。