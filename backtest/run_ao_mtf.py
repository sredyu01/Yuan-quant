# -*- coding: utf-8 -*-
"""
回测模块 - AO MTF 策略回测 (backtest/run_ao_mtf.py)
"""

import pandas as pd
from connector import MT5Client
from indicators import calculate_ao, ao_color
from backtest.engine import BacktestEngine
from config import AO_MTF_CONFIG, BACKTEST
from visualization.plot_result import plot_backtest_result
from utils.logger import get_logger

logger = get_logger(__name__)


def _ao_signal_from_df(df: pd.DataFrame) -> pd.Series:
    """
    在单时间框架数据上生成简化 AO 信号（用于单维度回测）。
    规则：AO 在零轴上方且由红变绿 -> 1（做多）
          AO 在零轴下方且由绿变红 -> -1（做空）
    """
    ao     = calculate_ao(df["high"], df["low"])
    colors = ao_color(ao)
    signal = pd.Series(0, index=df.index, dtype=int, name="AO_Signal")

    prev_color = colors.shift(1)
    signal[(ao > 0) & (prev_color == "red")   & (colors == "green")] = 1
    signal[(ao < 0) & (prev_color == "green") & (colors == "red")]   = -1
    return signal


def run_ao_mtf_backtest(
    symbol: str = None,
    timeframe: str = "M1",
    bars: int = 2000,
    plot: bool = True,
):
    """
    运行 AO MTF 策略回测（单时间框架简化版）。

    Parameters
    ----------
    symbol    : 交易品种
    timeframe : 主要时间框架（默认 M1）
    bars      : K 线数量
    plot      : 是否绘图
    """
    cfg = AO_MTF_CONFIG.copy()
    if symbol:
        cfg["symbol"] = symbol

    logger.info(f"开始 AO MTF 回测: {cfg['symbol']} {timeframe}")

    client = MT5Client()
    if not client.connect():
        logger.error("MT5 连接失败")
        return None

    df = client.get_rates(cfg["symbol"], timeframe, count=bars)
    client.disconnect()

    if df.empty:
        logger.error("获取数据失败")
        return None

    signals = _ao_signal_from_df(df)
    engine  = BacktestEngine(
        df=df,
        signals=signals,
        lot=cfg["lot"],
        capital=BACKTEST["initial_capital"],
    )
    result = engine.run()
    result.print_summary()

    if plot:
        plot_backtest_result(
            df=df,
            signals=signals,
            result=result,
            title=f"AO MTF | {cfg['symbol']} {timeframe}",
        )
    return result


if __name__ == "__main__":
    run_ao_mtf_backtest()
