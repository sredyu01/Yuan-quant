# -*- coding: utf-8 -*-
"""
指标模块 - MA（Moving Average，移动平均线）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【指标说明】
  移动平均线（MA）是最经典的趋势跟踪指标，通过对一段时期内收盘价求均值，
  平滑价格波动，揭示价格趋势方向。

  本模块支持以下三种类型：
    SMA（Simple Moving Average）      简单移动平均：各周期等权重
    EMA（Exponential Moving Average） 指数移动平均：近期价格权重更高，对价格变化更敏感
    WMA（Weighted Moving Average）    加权移动平均：线性加权，最新价格权重最高

【常用周期说明】
  MA5   → 超短期，5 根 K 线均线，反映极短期趋势
  MA20  → 短期，月线级别均线，常作为支撑/阻力参考
  MA60  → 中期，季线级别均线，趋势研判核心指标
  MA120 → 中长期，半年线
  MA250 → 长期，年线，牛熊分界重要参考

【典型交易信号】
  金叉（Golden Cross）：快速均线从下向上穿越慢速均线 → 做多信号
  死叉（Death Cross）  ：快速均线从上向下穿越慢速均线 → 做空信号
  均线多头排列          ：MA5 > MA20 > MA60 > MA120 > MA250 → 强势上涨趋势
  均线空头排列          ：MA5 < MA20 < MA60 < MA120 < MA250 → 强势下跌趋势

【参数说明】
  close   : pd.Series  – K 线收盘价序列
  period  : int        – 均线计算周期
  ma_type : str        – 均线类型，可选 'SMA' / 'EMA' / 'WMA'，默认 'SMA'

【依赖】
  pandas >= 1.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
from typing import Literal

# 预置常用周期
DEFAULT_PERIODS = [5, 20, 60, 120, 250]


def calculate_ma(
    close: pd.Series,
    period: int,
    ma_type: Literal["SMA", "EMA", "WMA"] = "SMA",
) -> pd.Series:
    """
    计算单条移动平均线。

    Parameters
    ----------
    close   : pd.Series  收盘价序列
    period  : int        均线周期
    ma_type : str        均线类型 ('SMA' | 'EMA' | 'WMA')，默认 'SMA'

    Returns
    -------
    pd.Series  均线值序列，名称格式为 '{ma_type}{period}'，如 'SMA20'
    """
    ma_type = ma_type.upper()
    if ma_type == "SMA":
        result = close.rolling(window=period).mean()
    elif ma_type == "EMA":
        result = close.ewm(span=period, adjust=False).mean()
    elif ma_type == "WMA":
        weights = pd.Series(range(1, period + 1), dtype=float)
        result = close.rolling(window=period).apply(
            lambda x: (x * weights.values).sum() / weights.sum(), raw=True
        )
    else:
        raise ValueError(f"不支持的均线类型: {ma_type}，请选择 'SMA' / 'EMA' / 'WMA'")

    result.name = f"{ma_type}{period}"
    return result


def calculate_ma_group(
    close: pd.Series,
    periods: list = None,
    ma_type: Literal["SMA", "EMA", "WMA"] = "SMA",
) -> pd.DataFrame:
    """
    批量计算多条移动平均线。

    Parameters
    ----------
    close   : pd.Series  收盘价序列
    periods : list       周期列表，默认 [5, 20, 60, 120, 250]
    ma_type : str        均线类型，默认 'SMA'

    Returns
    -------
    pd.DataFrame  每列为一条均线，列名格式如 'SMA5', 'SMA20' ...
    """
    if periods is None:
        periods = DEFAULT_PERIODS
    return pd.DataFrame(
        {f"{ma_type}{p}": calculate_ma(close, p, ma_type) for p in periods}
    )


def ma_cross_signal(
    fast_ma: pd.Series,
    slow_ma: pd.Series,
) -> pd.Series:
    """
    基于两条均线的金叉 / 死叉生成交易信号。

    Parameters
    ----------
    fast_ma : pd.Series  快速均线（周期较小）
    slow_ma : pd.Series  慢速均线（周期较大）

    Returns
    -------
    pd.Series[int]
       1  → 金叉（fast 上穿 slow，做多信号）
      -1  → 死叉（fast 下穿 slow，做空信号）
       0  → 无信号
    """
    prev_fast = fast_ma.shift(1)
    prev_slow = slow_ma.shift(1)
    signal = pd.Series(0, index=fast_ma.index, dtype=int, name="MA_Cross_Signal")
    # 金叉：前一根 fast <= slow，当前 fast > slow
    signal[(prev_fast <= prev_slow) & (fast_ma > slow_ma)] = 1
    # 死叉：前一根 fast >= slow，当前 fast < slow
    signal[(prev_fast >= prev_slow) & (fast_ma < slow_ma)] = -1
    return signal


def ma_trend_alignment(mas: pd.DataFrame) -> pd.Series:
    """
    检测均线多头 / 空头排列。
    输入 DataFrame 的列必须按周期从小到大排列（如 MA5, MA20, MA60...）。

    Returns
    -------
    pd.Series[int]
       1  → 多头排列（短期 > 中期 > 长期）
      -1  → 空头排列（短期 < 中期 < 长期）
       0  → 无明显排列
    """
    def _check(row):
        vals = row.values
        if all(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
            return 1
        if all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
            return -1
        return 0

    return mas.apply(_check, axis=1).rename("MA_Alignment")
