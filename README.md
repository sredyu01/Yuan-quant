# Yuan-Quant 隅安量化

> 基于 Python + MetaTrader5 的量化交易系统  
> 核心理念：**低交易频率 · 高胜率 · 严格风险控制**

---

## 项目结构

```
Yuan-quant/
├── main.py                      # 统一入口文件（实盘/回测一键启动）
├── requirements.txt             # 依赖包列表
│
├── config/                      # 基础配置模块
│   ├── __init__.py
│   ├── settings.py              # MT5账户、品种、时间框架、风险、日志等全局配置
│   └── strategy_config.py       # 各策略独立参数配置（无需改动策略代码）
│
├── indicators/                  # 指标模块（每种指标独立一个文件）
│   ├── __init__.py
│   ├── ao.py                    # AO 神奇震荡指标（零轴穿越/蝶形/弱转强信号）
│   └── ma.py                    # 移动平均线（SMA/EMA/WMA，MA5/20/60/120/250）
│
├── connector/                   # MT5 链接模块
│   ├── __init__.py
│   ├── mt5_client.py            # MT5初始化、登录、断开、行情数据获取
│   └── order_manager.py         # 开仓、平仓、查询持仓等订单管理
│
├── strategies/                  # 算法（策略）模块（每种策略独立一个文件）
│   ├── __init__.py
│   ├── ma_cross.py              # 均线交叉策略（H1，MA20/MA60 金叉做多/死叉做空）
│   └── ao_mtf.py                # AO 多时间框架共振策略（M1/M5/M15 三周期共振）
│
├── backtest/                    # 回测模块
│   ├── __init__.py
│   ├── engine.py                # 通用向量化回测引擎（支持任意信号序列输入）
│   ├── run_ma_cross.py          # MA Cross 策略回测入口
│   └── run_ao_mtf.py            # AO MTF 策略回测入口
│
├── visualization/               # 可视化模块
│   ├── __init__.py
│   ├── plot_result.py           # 回测结果三联图（价格+信号 / 权益曲线 / 回撤）
│   └── plot_indicators.py       # 指标可视化（MA叠加图 / AO柱状图）
│
├── utils/                       # 工具模块
│   ├── __init__.py
│   ├── logger.py                # 统一日志（控制台 + 滚动文件）
│   └── helpers.py               # 通用辅助函数（点数转换、时间框架映射等）
│
├── logs/                        # 运行日志目录（自动生成）
└── results/                     # 回测结果图表保存目录
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置账户

编辑 `config/settings.py`，填写 MT5 账户信息：

```python
MT5_ACCOUNT = {
    "login":    your_account_number,
    "password": "your_password",
    "server":   "your_broker_server",
}
```

### 3. 运行回测

```bash
# MA 均线交叉策略回测（默认 500 根 H1 K线）
python main.py --mode backtest --strategy ma_cross

# AO MTF 策略回测（2000 根 M1 K线）
python main.py --mode backtest --strategy ao_mtf --bars 2000

# 指定品种和时间框架
python main.py --mode backtest --strategy ma_cross --symbol XAUUSD --timeframe H4 --bars 1000
```

### 4. 实盘交易

```bash
# 启动 MA 均线交叉策略实盘
python main.py --mode live --strategy ma_cross

# 启动 AO 多时间框架共振策略实盘
python main.py --mode live --strategy ao_mtf
```

---

## 模块说明

### 指标模块 (`indicators/`)

| 文件 | 指标 | 核心函数 |
|------|------|----------|
| `ao.py` | AO 神奇震荡指标 | `calculate_ao()`, `ao_color()`, `ao_zero_cross_signal()`, `ao_saucer_signal()` |
| `ma.py` | 移动平均线 | `calculate_ma()`, `calculate_ma_group()`, `ma_cross_signal()`, `ma_trend_alignment()` |

### 策略模块 (`strategies/`)

| 文件 | 策略 | 说明 |
|------|------|------|
| `ma_cross.py` | 均线交叉 | H1 时间框架，MA20 金叉 MA60 做多，死叉做空 |
| `ao_mtf.py` | AO 多时间框架共振 | M1/M5/M15 三周期 AO 同向共振入场，AO变色+亏损止损，满2根K线盈利止盈 |

### 回测引擎 (`backtest/engine.py`)

- 接收任意策略生成的信号序列（`1` / `-1` / `0`）
- 模拟逐 K 线撮合，计算净盈亏、手续费
- 输出：总交易次数、胜率、净盈亏、最大回撤、盈亏比、夏普比率
- 结果自动保存图表至 `results/` 目录

---

## 扩展开发

### 新增指标
1. 在 `indicators/` 目录新建 `xxx.py`
2. 文件顶部添加指标说明文档
3. 在 `indicators/__init__.py` 中导出

### 新增策略
1. 在 `strategies/` 目录新建 `xxx.py`，继承或参考现有策略
2. 在 `strategies/__init__.py` 中导出
3. 在 `config/strategy_config.py` 中添加策略参数
4. 在 `main.py` 的 `run_live()` 和 `run_backtest()` 中注册
5. 在 `backtest/` 目录新建对应回测入口文件

---

## 更新日志

### 2026-03-17
- 初始化项目架构
- 实现 AO 指标（零轴穿越 / 蝶形形态 / 弱转强信号）
- 实现 MA 指标（SMA/EMA/WMA，MA5/20/60/120/250，金叉/死叉/多空排列信号）
- 实现 MT5 连接模块（登录、K线获取、开平仓管理）
- 实现均线交叉策略（H1, MA20/MA60）
- 实现 AO 多时间框架共振策略（M1/M5/M15）
- 实现通用向量化回测引擎
- 实现可视化模块（回测三联图、MA叠加图、AO柱状图）
