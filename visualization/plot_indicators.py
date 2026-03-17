# -*- coding: utf-8 -*-
"""
可视化模块 - 指标图表 (visualization/plot_indicators.py)
绘制价格与指标叠加图（MA、AO 等）。
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

MA_COLORS = {
    5:   "#FF9800",
    20:  "#2196F3",
    60:  "#9C27B0",
    120: "#F44336",
    250: "#4CAF50",
}


def plot_ma(
    df: pd.DataFrame,
    mas: pd.DataFrame,
    title: str = "Price & MA",
    save: bool = False,
    show: bool = True,
):
    """
    绘制收盘价与多条均线叠加图。

    Parameters
    ----------
    df   : K 线 DataFrame（含 close 列，time 为索引）
    mas  : 均线 DataFrame，每列一条均线（列名如 SMA5, SMA20 ...）
    """
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.plot(df.index, df["close"], color="#37474F", linewidth=1,
            label="Close", alpha=0.8)

    for col in mas.columns:
        period = int("".join(filter(str.isdigit, col)))
        color  = MA_COLORS.get(period, "#607D8B")
        ax.plot(mas.index, mas[col], linewidth=1.2, label=col, color=color)

    ax.set_title(title, fontsize=13)
    ax.set_ylabel("Price")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()

    if save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        path = os.path.join(RESULTS_DIR, f"{title.replace(' ', '_')}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        print(f"图表已保存: {path}")

    if show:
        plt.show()
    plt.close(fig)


def plot_ao(
    df: pd.DataFrame,
    ao: pd.Series,
    title: str = "Price & AO",
    save: bool = False,
    show: bool = True,
):
    """
    绘制收盘价与 AO 指标双联图。

    Parameters
    ----------
    df : K 线 DataFrame
    ao : AO 值序列
    """
    fig = plt.figure(figsize=(16, 8))
    gs  = gridspec.GridSpec(2, 1, height_ratios=[2, 1], hspace=0.25)

    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df.index, df["close"], color="#37474F", linewidth=1)
    ax1.set_ylabel("Price")
    ax1.set_title(title, fontsize=13)
    ax1.grid(alpha=0.3)

    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    diff = ao.diff()
    colors = ["#00C853" if d >= 0 else "#FF1744" for d in diff]
    ax2.bar(ao.index, ao.values, color=colors, width=0.6, alpha=0.85)
    ax2.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax2.set_ylabel("AO")
    ax2.grid(alpha=0.3)

    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.tight_layout()

    if save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        path = os.path.join(RESULTS_DIR, f"{title.replace(' ', '_')}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        print(f"图表已保存: {path}")

    if show:
        plt.show()
    plt.close(fig)
