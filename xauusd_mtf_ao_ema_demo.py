"""MT5 XAUUSD MTF AO/EMA demo strategy.
Signals and trade actions are evaluated only after a new M1 candle closes.
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd


class Direction(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class Config:
    symbol: str = "XAUUSD"
    magic: int = 2026050701
    volume: float = 0.20
    first_exit_volume: float = 0.10
    max_spread_points: int = 80
    deviation_points: int = 30
    poll_seconds: float = 0.5
    dry_run: bool = False


STOP = False


def on_stop(signum: int, frame: object) -> None:
    global STOP
    STOP = True
    logging.info("收到停止信号，当前轮结束后退出")


def setup_logging() -> None:
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/xauusd_mtf_ao_ema.log", encoding="utf-8")],
    )


def init_mt5(path: str | None) -> None:
    ok = mt5.initialize(path=path) if path else mt5.initialize()
    if not ok:
        raise RuntimeError(f"MT5初始化失败: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None:
        raise RuntimeError("请先在MT5终端登录模拟盘账号")
    logging.info("MT5已连接: login=%s server=%s balance=%.2f equity=%.2f", account.login, account.server, account.balance, account.equity)


def ensure_symbol(symbol: str) -> None:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"找不到品种: {symbol}")
    if not info.visible and not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"无法启用品种: {symbol}")
    if info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
        raise RuntimeError(f"品种不可交易: {symbol}")


def rates(symbol: str, timeframe: int, bars: int) -> pd.DataFrame:
    raw = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if raw is None or len(raw) == 0:
        raise RuntimeError(f"无法获取K线: {symbol} {timeframe} {mt5.last_error()}")
    df = pd.DataFrame(raw)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    median = (out["high"] + out["low"]) / 2
    out["ao"] = median.rolling(5).mean() - median.rolling(34).mean()
    for n in (5, 10, 20, 60):
        out[f"ema{n}"] = out["close"].ewm(span=n, adjust=False).mean()
    out["ao_color"] = np.where(out["ao"] > out["ao"].shift(1), "green", "red")
    return out


def closed(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[:-1].copy()


def bull_htf(r: pd.Series) -> bool:
    return r.ao > 0 and r.close > r.ema20 and r.ema20 > r.ema60


def bear_htf(r: pd.Series) -> bool:
    return r.ao < 0 and r.close < r.ema20 and r.ema20 < r.ema60


def bull_m1(r: pd.Series) -> bool:
    return r.ema5 > r.ema10 > r.ema20 > r.ema60


def bear_m1(r: pd.Series) -> bool:
    return r.ema5 < r.ema10 < r.ema20 < r.ema60


def entry_signal(df1: pd.DataFrame, df5: pd.DataFrame, df15: pd.DataFrame) -> Direction | None:
    m1, m5, m15 = closed(indicators(df1)), closed(indicators(df5)), closed(indicators(df15))
    if min(len(m1), len(m5), len(m15)) < 80:
        return None
    cur, prev = m1.iloc[-1], m1.iloc[-2]
    long_trend = bull_htf(m5.iloc[-1]) and bull_htf(m15.iloc[-1]) and bull_m1(cur)
    short_trend = bear_htf(m5.iloc[-1]) and bear_htf(m15.iloc[-1]) and bear_m1(cur)
    if long_trend and cur.ao > 0 and prev.ao_color == "red" and cur.ao_color == "green" and cur.close > prev.high:
        return Direction.LONG
    if short_trend and cur.ao < 0 and prev.ao_color == "green" and cur.ao_color == "red" and cur.close < prev.low:
        return Direction.SHORT
    return None


def positions(cfg: Config):
    data = mt5.positions_get(symbol=cfg.symbol)
    if data is None:
        logging.warning("读取持仓失败: %s", mt5.last_error())
        return []
    return [p for p in data if p.magic == cfg.magic]


def spread_points(symbol: str) -> float:
    tick, info = mt5.symbol_info_tick(symbol), mt5.symbol_info(symbol)
    if tick is None or info is None or info.point <= 0:
        return 10**9
    return (tick.ask - tick.bid) / info.point


def norm_volume(symbol: str, volume: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"无法获取品种信息: {symbol}")
    v = max(info.volume_min, min(volume, info.volume_max))
    v = info.volume_min + round((v - info.volume_min) / info.volume_step) * info.volume_step
    return round(v, 2)


def open_trade(cfg: Config, direction: Direction) -> bool:
    tick = mt5.symbol_info_tick(cfg.symbol)
    if tick is None:
        logging.warning("无报价，跳过开仓")
        return False
    order_type = mt5.ORDER_TYPE_BUY if direction is Direction.LONG else mt5.ORDER_TYPE_SELL
    price = tick.ask if direction is Direction.LONG else tick.bid
    req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": cfg.symbol, "volume": norm_volume(cfg.symbol, cfg.volume), "type": order_type, "price": price, "deviation": cfg.deviation_points, "magic": cfg.magic, "comment": "MTF AO EMA entry", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
    if cfg.dry_run:
        logging.info("DRY-RUN 开仓: %s", req)
        return True
    res = mt5.order_send(req)
    if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
        logging.warning("开仓失败: result=%s error=%s", res, mt5.last_error())
        return False
    logging.info("开仓成交: %s %.2f order=%s deal=%s", direction.value, cfg.volume, res.order, res.deal)
    return True


def close_trade(pos, volume: float, cfg: Config, reason: str) -> bool:
    tick = mt5.symbol_info_tick(pos.symbol)
    if tick is None:
        logging.warning("无报价，跳过平仓 ticket=%s", pos.ticket)
        return False
    is_buy = pos.type == mt5.POSITION_TYPE_BUY
    req = {"action": mt5.TRADE_ACTION_DEAL, "position": pos.ticket, "symbol": pos.symbol, "volume": norm_volume(pos.symbol, min(volume, pos.volume)), "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY, "price": tick.bid if is_buy else tick.ask, "deviation": cfg.deviation_points, "magic": pos.magic, "comment": reason, "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
    if cfg.dry_run:
        logging.info("DRY-RUN 平仓: %s", req)
        return True
    res = mt5.order_send(req)
    if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
        logging.warning("平仓失败: result=%s error=%s", res, mt5.last_error())
        return False
    logging.info("平仓成交: ticket=%s volume=%.2f reason=%s", pos.ticket, req["volume"], reason)
    return True


def manage_exits(cfg: Config, first_done: set[int], df1: pd.DataFrame) -> None:
    m1 = closed(indicators(df1))
    if len(m1) < 40:
        return
    cur, prev = m1.iloc[-1], m1.iloc[-2]
    live = positions(cfg)
    live_tickets = {p.ticket for p in live}
    first_done.intersection_update(live_tickets)
    for pos in live:
        is_long = pos.type == mt5.POSITION_TYPE_BUY
        first_exit = cur.close < cur.open if is_long else cur.close > cur.open
        ao_exit = (prev.ao_color != "red" and cur.ao_color == "red") if is_long else (prev.ao_color != "green" and cur.ao_color == "green")
        if pos.ticket not in first_done and first_exit and pos.volume > cfg.first_exit_volume:
            if close_trade(pos, cfg.first_exit_volume, cfg, "first candle exit"):
                first_done.add(pos.ticket)
            continue
        if ao_exit:
            fresh = next((p for p in positions(cfg) if p.ticket == pos.ticket), pos)
            close_trade(fresh, fresh.volume, cfg, "ao color exit")


def on_new_closed_bar(cfg: Config, first_done: set[int]) -> None:
    sp = spread_points(cfg.symbol)
    if sp > cfg.max_spread_points:
        logging.info("点差过高跳过: %.1f > %s", sp, cfg.max_spread_points)
        return
    df1 = rates(cfg.symbol, mt5.TIMEFRAME_M1, 300)
    manage_exits(cfg, first_done, df1)
    if positions(cfg):
        return
    sig = entry_signal(df1, rates(cfg.symbol, mt5.TIMEFRAME_M5, 250), rates(cfg.symbol, mt5.TIMEFRAME_M15, 250))
    if sig:
        logging.info("入场信号: %s", sig.value)
        open_trade(cfg, sig)


def latest_closed_time(symbol: str):
    return closed(rates(symbol, mt5.TIMEFRAME_M1, 3)).iloc[-1].time


def run(cfg: Config, mt5_path: str | None) -> None:
    setup_logging()
    signal.signal(signal.SIGINT, on_stop)
    signal.signal(signal.SIGTERM, on_stop)
    init_mt5(mt5_path)
    ensure_symbol(cfg.symbol)
    logging.info("策略启动: %s", cfg)
    last = latest_closed_time(cfg.symbol)
    first_done: set[int] = set()
    try:
        while not STOP:
            try:
                now = latest_closed_time(cfg.symbol)
                if now != last:
                    logging.info("新M1收盘K线: %s", now)
                    on_new_closed_bar(cfg, first_done)
                    last = now
            except Exception as exc:
                logging.exception("策略轮询异常: %s", exc)
            time.sleep(cfg.poll_seconds)
    finally:
        mt5.shutdown()
        logging.info("策略停止")


def parse_args() -> tuple[Config, str | None]:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--volume", type=float, default=0.20)
    p.add_argument("--first-exit-volume", type=float, default=0.10)
    p.add_argument("--max-spread-points", type=int, default=80)
    p.add_argument("--deviation-points", type=int, default=30)
    p.add_argument("--magic", type=int, default=2026050701)
    p.add_argument("--poll-seconds", type=float, default=0.5)
    p.add_argument("--mt5-path", default=None)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    return Config(a.symbol, a.magic, a.volume, a.first_exit_volume, a.max_spread_points, a.deviation_points, a.poll_seconds, a.dry_run), a.mt5_path


if __name__ == "__main__":
    config, path = parse_args()
    run(config, path)
