# -*- coding: utf-8 -*-
"""
工具模块 - 通用辅助函数 (utils/helpers.py)
"""

import pandas as pd
import MetaTrader5 as mt5
from config import TIMEFRAMES


def pips_to_price(symbol: str, pips: float) -> float:
    """
    将点数（pips）转换为价格偏移量。
    不同品种的 point 值不同（如 EURUSD point=0.00001）。
    """
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"无法获取品种信息: {symbol}")
    return pips * info.point


def price_to_pips(symbol: str, price_diff: float) -> float:
    """将价格偏移量转换为点数。"""
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"无法获取品种信息: {symbol}")
    return price_diff / info.point


def timeframe_to_mt5(timeframe: str) -> int:
    """将时间框架字符串转为 MT5 常量。"""
    tf = TIMEFRAMES.get(timeframe.upper())
    if tf is None:
        raise ValueError(f"未知时间框架: {timeframe}")
    return tf


def ensure_series(data, name: str = None) -> pd.Series:
    """确保输入为 pd.Series，若为 DataFrame 则取第一列。"""
    if isinstance(data, pd.DataFrame):
        data = data.iloc[:, 0]
    if name:
        data = data.rename(name)
    return data
