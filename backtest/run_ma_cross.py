# -*- coding: utf-8 -*-
"""
回测模块 - MA 均线交叉策略回测 (backtest/run_ma_cross.py)
"""

import pandas as pd
from connector import MT5Client
from indicators import calculate_ma, ma_cross_signal
from backtest.engine import BacktestEngine
from config import MA_CROSS_CONFIG, BACKTEST
from visualization.plot_result import plot_backtest_result
from utils.logger import get_logger

logger = get_logger(__name__)


def run_ma_cross_backtest(
    symbol: str = None,
    timeframe: str = None,
    fast_ma: int = None,
    slow_ma: int = None,
    bars: int = 500,
    plot: bool = True,
):
    """
    运行 MA 均线交叉策略回测。

    Parameters
    ----------
    symbol    : 交易品种，默认取 MA_CROSS_CONFIG
    timeframe : 时间框架，默认取 MA_CROSS_CONFIG
    fast_ma   : 快线周期
    slow_ma   : 慢线周期
    bars      : 回测 K 线数量
    plot      : 是否绘制结果图表
    """
    cfg = MA_CROSS_CONFIG.copy()
    if symbol:    cfg["symbol"]   = symbol
    if timeframe: cfg["timeframe"] = timeframe
    if fast_ma:   cfg["fast_ma"]  = fast_ma
    if slow_ma:   cfg["slow_ma"]  = slow_ma

    logger.info(f"开始回测: MA{cfg['fast_ma']}/MA{cfg['slow_ma']} | {cfg['symbol']} {cfg['timeframe']}")

    client = MT5Client()
    if not client.connect():
        logger.error("MT5 连接失败，回测中止")
        return None

    df = client.get_rates(cfg["symbol"], cfg["timeframe"], count=bars)
    client.disconnect()

    if df.empty:
        logger.error("获取 K 线数据失败")
        return None

    fast = calculate_ma(df["close"], cfg["fast_ma"])
    slow = calculate_ma(df["close"], cfg["slow_ma"])
    signals = ma_cross_signal(fast, slow)

    engine = BacktestEngine(
        df=df, signals=signals, lot=cfg["lot"],
        capital=BACKTEST["initial_capital"],
    )
    result = engine.run()
    result.print_summary()

    if plot:
        plot_backtest_result(
            df=df, signals=signals, result=result,
            title=f"MA Cross {cfg['fast_ma']}/{cfg['slow_ma']} | {cfg['symbol']} {cfg['timeframe']}",
        )

    return result


if __name__ == "__main__":
    run_ma_cross_backtest()
