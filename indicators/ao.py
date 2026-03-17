# -*- coding: utf-8 -*-
"""
指标模块 - AO（Awesome Oscillator，神奇震荡指标）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【指标说明】
  AO（Awesome Oscillator）由 Bill Williams 创立，衡量市场近期动能与较长期动能之差。

  计算公式：
      中间价  = (High + Low) / 2
      AO      = SMA(中间价, 5) - SMA(中间价, 34)
  其中 SMA 为简单移动平均。

【柱色定义】
  - 绿色（Green）：当前 AO 值 > 前一根 AO 值（动能增强）
  - 红色（Red）  ：当前 AO 值 < 前一根 AO 值（动能减弱）

【信号解读】
  1. 零轴穿越（Zero Cross）
     - AO 由负转正（上穿零轴）→ 买入信号
     - AO 由正转负（下穿零轴）→ 卖出信号

  2. 蝶形形态（Saucer）
     - 蝶形买入：三根均在零轴上方，第二根绝对值最小（谷底），第三根向上翻绿
     - 蝶形卖出：三根均在零轴下方，第二根绝对值最小（峰顶），第三根向下翻红

  3. 弱转强（Weak-to-Strong，用于 MTF 共振策略）
     - 零轴上方：AO 由红色变为绿色
     - 零轴下方：AO 由绿色变为红色

【参数说明】
  high  : pd.Series  – K 线最高价序列
  low   : pd.Series  – K 线最低价序列
  fast  : int        – 快速 SMA 周期，默认 5
  slow  : int        – 慢速 SMA 周期，默认 34

【依赖】
  pandas >= 1.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd


def calculate_ao(
    high: pd.Series,
    low: pd.Series,
    fast: int = 5,
    slow: int = 34,
) -> pd.Series:
    """
    计算 Awesome Oscillator（AO）值。

    Parameters
    ----------
    high : pd.Series  K 线最高价
    low  : pd.Series  K 线最低价
    fast : int        快速 SMA 窗口，默认 5
    slow : int        慢速 SMA 窗口，默认 34

    Returns
    -------
    pd.Series  AO 值序列，索引与输入相同，列名为 "AO"
    """
    midpoint = (high + low) / 2.0
    ao = midpoint.rolling(window=fast).mean() - midpoint.rolling(window=slow).mean()
    ao.name = "AO"
    return ao


def ao_color(ao: pd.Series) -> pd.Series:
    """
    计算每根 K 线 AO 柱的颜色。

    Returns
    -------
    pd.Series[str]  取值为 'green'（上升）、'red'（下降）或 'neutral'（首根）
    """
    diff = ao.diff()
    color = diff.apply(
        lambda x: "green" if x > 0 else ("red" if x < 0 else "neutral")
    )
    color.iloc[0] = "neutral"
    color.name = "AO_Color"
    return color


def ao_zero_cross_signal(ao: pd.Series) -> pd.Series:
    """
    基于零轴穿越生成交易信号。

    Returns
    -------
    pd.Series[int]
       1  → 买入（AO 由负转正，上穿零轴）
      -1  → 卖出（AO 由正转负，下穿零轴）
       0  → 无信号
    """
    prev = ao.shift(1)
    signal = pd.Series(0, index=ao.index, dtype=int, name="AO_ZeroCross_Signal")
    signal[(ao > 0) & (prev <= 0)] = 1
    signal[(ao < 0) & (prev >= 0)] = -1
    return signal


def ao_saucer_signal(ao: pd.Series) -> pd.Series:
    """
    基于蝶形形态（Saucer）生成交易信号。

    Returns
    -------
    pd.Series[int]
       1  → 蝶形买入
      -1  → 蝶形卖出
       0  → 无信号
    """
    signal = pd.Series(0, index=ao.index, dtype=int, name="AO_Saucer_Signal")
    ao_vals = ao.values

    for i in range(2, len(ao_vals)):
        a, b, c = ao_vals[i - 2], ao_vals[i - 1], ao_vals[i]
        if any(v != v for v in (a, b, c)):  # NaN 检查
            continue
        # 