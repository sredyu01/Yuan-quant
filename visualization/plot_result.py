# -*- coding: utf-8 -*-
"""
可视化模块 - 回测结果图表 (visualization/plot_result.py)
使用 matplotlib 绘制：价格 + 信号标注、权益曲线、回撤曲线。
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from backtest.engine import BacktestResult

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def plot_backtest_result(
    df: pd.DataFrame,
    signals: pd.Series,
    result: BacktestResult,
    title: str = "Backtest Result",
    save: bool = True,
    show: bool = True,
):
    """
    绘制回测结果三联图：
      上图 - K 线收盘价 + 买卖信号标注
      中图 - 权益曲线
      下图 - 回撤曲线

    Parameters
    ----------
    df      : K 线 DataFrame
    signals : 信号序列
    result  : BacktestResult 对象
    title   : 图表标题
    save    : 是否保存图片到 results/ 目录
    show    : 是否弹窗显示
    """
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(title, fontsize=14, fontweight="bold")
    gs = gridspec.GridSpec(3, 1, height_ratios=[3, 2, 1], hspace=0.35)

    # ── 子图1：价格 + 信号 ──
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df.index, df["close"], color="#2196F3", linewidth=1, label="Close")

    buy_idx  = signals[signals == 1].index
    sell_idx = signals[signals == -1].index
    ax1.scatter(buy_idx,  df.loc[buy_idx,  "close"], marker="^", color="#00C853",
                s=80, zorder=5, label="Buy")
    ax1.scatter(sell_idx, df.loc[sell_idx, "close"], marker="v", color="#FF1744",
                s=80, zorder=5, label="Sell")
    ax1.set_ylabel("Price")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(alpha=0.3)

    # ── 子图2：权益曲线 ──
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.plot(result.equity_curve.index, result.equity_curve.values,
             color="#FF9800", linewidth=1.5, label="Equity")
    ax2.axhline(result.equity_curve.iloc[0], color="gray", linestyle="--",
                linewidth=0.8, alpha=0.7)
    ax2.set_ylabel("Equity")
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(alpha=0.3)

    # ── 子图3：回撤 ──
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.fill_between(result.drawdown.index, result.drawdown.values,
                     color="#F44336", alpha=0.5, label="Drawdown")
    ax3.set_ylabel("Drawdown")
    ax3.legend(loc="lower left", fontsize=8)
    ax3.grid(alpha=0.3)

    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), visible=False)

    if save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        safe_title = title.replace(" ", "_").replace("/", "-").replace("|", "-")
        path = os.path.join(RESULTS_DIR, f"{safe_title}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        print(f"图表已保存: {path}")

    if show:
        plt.show()

    plt.close(fig)
