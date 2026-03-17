# -*- coding: utf-8 -*-
"""
回测引擎 (backtest/engine.py)
通用向量化回测引擎，接收信号序列，模拟逐 K 线撮合并统计绩效。
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List
from config import BACKTEST


@dataclass
class Trade:
    """单笔交易记录。"""
    entry_time:  pd.Timestamp
    exit_time:   pd.Timestamp
    direction:   int          # 1=多, -1=空
    entry_price: float
    exit_price:  float
    lot:         float
    pnl:         float
    commission:  float


@dataclass
class BacktestResult:
    """回测结果容器。"""
    trades:       List[Trade]
    equity_curve: pd.Series
    drawdown:     pd.Series
    config:       dict = field(default_factory=dict)

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def win_trades(self) -> int:
        return sum(1 for t in self.trades if t.pnl > 0)

    @property
    def loss_trades(self) -> int:
        return sum(1 for t in self.trades if t.pnl <= 0)

    @property
    def win_rate(self) -> float:
        return self.win_trades / self.total_trades if self.total_trades else 0.0

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades)

    @property
    def avg_pnl(self) -> float:
        return self.total_pnl / self.total_trades if self.total_trades else 0.0

    @property
    def max_drawdown(self) -> float:
        return float(self.drawdown.min())

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss   = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        return gross_profit / gross_loss if gross_loss else float("inf")

    @property
    def sharpe_ratio(self) -> float:
        pnls = [t.pnl for t in self.trades]
        if len(pnls) < 2:
            return 0.0
        arr = np.array(pnls)
        return float(arr.mean() / arr.std()) if arr.std() > 0 else 0.0

    def print_summary(self):
        print("\n" + "=" * 50)
        print("  回测结果摘要")
        print("=" * 50)
        print(f"  总交易次数  : {self.total_trades}")
        print(f"  盈利次数    : {self.win_trades}")
        print(f"  亏损次数    : {self.loss_trades}")
        print(f"  胜率        : {self.win_rate:.2%}")
        print(f"  净盈亏      : {self.total_pnl:.2f}")
        print(f"  平均每笔    : {self.avg_pnl:.2f}")
        print(f"  最大回撤    : {self.max_drawdown:.2f}")
        print(f"  盈亏比      : {self.profit_factor:.2f}")
        print(f"  夏普比率    : {self.sharpe_ratio:.2f}")
        print("=" * 50 + "\n")

    def to_dataframe(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame([t.__dict__ for t in self.trades])


class BacktestEngine:
    """
    通用向量化回测引擎。

    Parameters
    ----------
    df       : pd.DataFrame  K 线数据（含 open/high/low/close 列，time 为索引）
    signals  : pd.Series     信号序列：1=开多/-1=开空/0=无信号，索引与 df 对齐
    lot      : float         每笔交易手数，默认取 config.BACKTEST 值
    capital  : float         初始资金
    commission: float        每手手续费比例
    """

    def __init__(
        self,
        df: pd.DataFrame,
        signals: pd.Series,
        lot: float = 0.01,
        capital: float = None,
        commission: float = None,
    ):
        self.df         = df.copy()
        self.signals    = signals.reindex(df.index).fillna(0)
        self.lot        = lot
        self.capital    = capital    or BACKTEST["initial_capital"]
        self.commission = commission or BACKTEST["commission"]

    def run(self) -> BacktestResult:
        """执行回测，返回 BacktestResult。"""
        df       = self.df
        signals  = self.signals
        capital  = self.capital
        equity   = [capital]
        trades: List[Trade] = []

        position   = 0    # 当前方向：1=多, -1=空, 0=空仓
        entry_price = 0.0
        entry_time  = None

        for i in range(1, len(df)):
            idx  = df.index[i]
            sig  = int(signals.iloc[i - 1])  # 前一根 K 线收盘信号
            close = df["close"].iloc[i]       # 当根 K 线开盘价近似成交

            # 平仓逻辑：信号反转时平旧仓
            if position != 0 and sig != 0 and sig != position:
                exit_price = close
                raw_pnl    = (exit_price - entry_price) * position * self.lot * 100000
                comm       = abs(raw_pnl) * self.commission
                net_pnl    = raw_pnl - comm
                capital   += net_pnl
                trades.append(Trade(
                    entry_time=entry_time, exit_time=idx,
                    direction=position,
                    entry_price=entry_price, exit_price=exit_price,
                    lot=self.lot, pnl=net_pnl, commission=comm,
                ))
                position = 0

            # 开仓逻辑
            if position == 0 and sig != 0:
                position    = sig
                entry_price = close
                entry_time  = idx

            equity.append(capital)

        # 计算权益曲线与回撤
        equity_series = pd.Series(equity, index=df.index)
        rolling_max   = equity_series.cummax()
        drawdown      = equity_series - rolling_max

        return BacktestResult(
            trades=trades,
            equity_curve=equity_series,
            drawdown=drawdown,
            config={"lot": self.lot, "capital": self.capital},
        )
