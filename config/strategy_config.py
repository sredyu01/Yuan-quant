# -*- coding: utf-8 -*-
"""
策略参数配置 - strategy_config.py
集中管理各交易策略的可调参数，修改此处无需改动策略代码本身
"""

# ─────────────────────────────────────────────
# 均线交叉策略（MA Cross Strategy）
# 1H 时间框架，MA20 / MA60 金叉做多，死叉做空
# ─────────────────────────────────────────────
MA_CROSS_CONFIG = {
    "symbol":     "EURUSD",      # 交易品种
    "timeframe":  "H1",          # 时间框架
    "fast_ma":    20,             # 快线周期
    "slow_ma":    60,             # 慢线周期
    "lot":        0.01,           # 交易手数
    "sl_pips":    50,             # 止损点数（0 = 不设止损）
    "tp_pips":    100,            # 止盈点数（0 = 不设止盈）
    "magic":      10001,          # 魔术数字（唯一标识该策略的订单）
    "comment":    "MA_Cross",    # 订单备注
}

# ─────────────────────────────────────────────
# AO 多时间框架共振策略（MTF AO Strategy）
# 核心：1min / 5min / 15min AO 指标同向共振
# ─────────────────────────────────────────────
AO_MTF_CONFIG = {
    "symbol":     "EURUSD",      # 交易品种
    "timeframes": ["M1", "M5", "M15"],  # 共振时间框架列表（从小到大）
    "lot":        0.01,           # 每次开仓固定手数
    "magic":      10002,          # 魔术数字
    "comment":    "AO_MTF",      # 订单备注
    # 止盈止损策略：
    #   "fixed_pips"     → 固定点数
    #   "ao_color_change"→ AO 变色时止损
    #   "candle_count"   → 固定 K 线数止盈
    "sl_mode":    "ao_color_change",
    "tp_mode":    "candle_count",
    "tp_candles": 2,              # 固定 K 线数止盈（盈利状态下持仓满 N 根 K 线后平仓）
    "sl_pips":    0,              # 固定止损点数（sl_mode=fixed_pips 时生效）
    "tp_pips":    0,              # 固定止盈点数（tp_mode=fixed_pips 时生效）
}

# ─────────────────────────────────────────────
# AO 单时间框架零轴穿越策略（AO Zero Cross）
# ─────────────────────────────────────────────
AO_ZERO_CROSS_CONFIG = {
    "symbol":    "EURUSD",
    "timeframe": "H1",
    "lot":       0.01,
    "sl_pips":   60,
    "tp_pips":   120,
    "magic":     10003,
    "comment":   "AO_ZeroCross",
}
