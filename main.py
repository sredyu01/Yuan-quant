# -*- coding: utf-8 -*-
"""
入口文件 - main.py
统一启动入口：可选择运行实盘策略或回测任务。

使用方法：
    # 实盘 - MA 均线交叉策略
    python main.py --mode live --strategy ma_cross

    # 实盘 - AO 多时间框架共振策略
    python main.py --mode live --strategy ao_mtf

    # 回测 - MA 均线交叉
    python main.py --mode backtest --strategy ma_cross --bars 1000

    # 回测 - AO MTF
    python main.py --mode backtest --strategy ao_mtf --bars 2000
"""

import argparse
from utils.logger import get_logger
 
logger = get_logger("main")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Yuan-Quant MT5 量化交易系统"
    )
    parser.add_argument(
        "--mode",
        choices=["live", "backtest"],
        default="backtest",
        help="运行模式：live=实盘 / backtest=回测（默认 backtest）",
    )
    parser.add_argument(
        "--strategy",
        choices=["ma_cross", "ao_mtf"],
        default="ma_cross",
        help="策略选择：ma_cross=均线交叉 / ao_mtf=AO多时间框架（默认 ma_cross）",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="交易品种，如 EURUSD（覆盖配置文件中的默认值）",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default=None,
        help="时间框架，如 H1 / M15（覆盖配置文件中的默认值）",
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=500,
        help="回测 K 线数量（默认 500）",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="回测时不显示图表",
    )
    return parser.parse_args()


def run_live(strategy: str, symbol: str = None, timeframe: str = None):
    """启动实盘策略。"""
    if strategy == "ma_cross":
        from strategies.str_ma_cross import MACrossStrategy
        from config import MA_CROSS_CONFIG
        cfg = MA_CROSS_CONFIG.copy()
        if symbol:    cfg["symbol"]    = symbol
        if timeframe: cfg["timeframe"] = timeframe
        logger.info(f"启动实盘策略: MA Cross | {cfg['symbol']} {cfg['timeframe']}")
        MACrossStrategy(cfg).run()

    elif strategy == "ao_mtf":
        from strategies.str_ao_mtf import AOMTFStrategy
        from config import AO_MTF_CONFIG
        cfg = AO_MTF_CONFIG.copy()
        if symbol: cfg["symbol"] = symbol
        logger.info(f"启动实盘策略: AO MTF | {cfg['symbol']}")
        AOMTFStrategy(cfg).run()


def run_backtest(strategy: str, symbol: str = None, timeframe: str = None,
                bars: int = 500, plot: bool = True):
    """启动回测任务。"""
    if strategy == "ma_cross":
        from backtest.run_ma_cross import run_ma_cross_backtest
        run_ma_cross_backtest(
            symbol=symbol, timeframe=timeframe,
            bars=bars, plot=plot,
        )

    elif strategy == "ao_mtf":
        from backtest.run_ao_mtf import run_ao_mtf_backtest
        tf = timeframe or "M1"
        run_ao_mtf_backtest(
            symbol=symbol, timeframe=tf,
            bars=bars, plot=plot,
        )


def main():
    args = parse_args()
    logger.info(
        f"Yuan-Quant 启动 | mode={args.mode} "
        f"strategy={args.strategy} symbol={args.symbol}"
    )

    if args.mode == "live":
        run_live(
            strategy=args.strategy,
            symbol=args.symbol,
            timeframe=args.timeframe,
        )
    else:
        run_backtest(
            strategy=args.strategy,
            symbol=args.symbol,
            timeframe=args.timeframe,
            bars=args.bars,
            plot=not args.no_plot,
        )


if __name__ == "__main__":
    main()
