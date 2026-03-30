# -*- coding: utf-8 -*-
"""
算法模块 - AO 多时间框架共振策略 (strategies/ao_mtf.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【策略说明】
  基于 1分钟、5分钟、15分钟三个时间周期的 AO 指标共振，进行多空交易。

【做多条件（三个时间框架同时满足）】
  M1  : AO 在零轴上方，且由红色变为绿色
  M5  : AO 在零轴上方，且由红变绿 或 持续绿色
  M15 : AO 在零轴上方，且由红变绿 或 持续绿色

【做空条件（三个时间框架同时满足）】
  M1  : AO 在零轴下方，且由绿色变为红色
  M5  : AO 在零轴下方，且由绿变红 或 持续红色
  M15 : AO 在零轴下方，且由绿变红 或 持续红色

【持仓管理】
  止损：每根 K 线收盘后检查，AO 变色且持仓亏损时立即平仓
  止盈：持仓处于盈利状态且满 2 根 K 线后，在第 2 根收盘时平仓

  入场必须在 K 线收盘后执行，严禁未收盘提前入场。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
from config import AO_MTF_CONFIG
from connector import MT5Client, OrderManager
from indicators import calculate_ao, ao_color
from utils.logger import get_logger

logger = get_logger(__name__)


class AOMTFStrategy:
    """AO 多时间框架共振策略（M1 / M5 / M15）。"""

    def __init__(self, config: dict = None):
        self.cfg = config or AO_MTF_CONFIG
        self.client = MT5Client()
        self.order_mgr = OrderManager()
        # 记录各持仓开仓后经历的 M1 K 线数
        self._candle_counter: dict = {}  # ticket -> candle_count

    # ──────────────────────────────────────────
    # AO 状态计算
    # ──────────────────────────────────────────

    def _ao_state(self, timeframe: str) -> dict:
        """
        获取指定时间框架最后两根已收盘 K 线的 AO 状态。

        Returns
        -------
        dict with keys:
          above_zero : bool  当前 AO 是否在零轴上方
          color      : str   当前 K 线颜色 ('green'/'red'/'neutral')
          prev_color : str   前一根 K 线颜色
          turned_green : bool  由红变绿
          turned_red   : bool  由绿变红
          stayed_green : bool  连续绿色
          stayed_red   : bool  连续红色
        """
        df = self.client.get_rates(self.cfg["symbol"], timeframe, count=50)
        if df.empty or len(df) < 36:  # AO 需要至少 34 根
            return {}

        ao = calculate_ao(df["high"], df["low"])
        colors = ao_color(ao)

        # 取倒数第 2 根（已收盘）和倒数第 3 根
        cur_ao    = ao.iloc[-2]
        cur_color = colors.iloc[-2]
        prv_color = colors.iloc[-3]

        return {
            "above_zero":   cur_ao > 0,
            "below_zero":   cur_ao < 0,
            "color":        cur_color,
            "prev_color":   prv_color,
            "turned_green": prv_color == "red"   and cur_color == "green",
            "turned_red":   prv_color == "green" and cur_color == "red",
            "stayed_green": prv_color == "green" and cur_color == "green",
            "stayed_red":   prv_color == "red"   and cur_color == "red",
        }

    # ──────────────────────────────────────────
    # 信号判断
    # ──────────────────────────────────────────

    def _check_long_signal(self) -> bool:
        """检查三时间框架做多共振条件。"""
        tf_list = self.cfg["timeframes"]  # ["M1", "M5", "M15"]
        states = {tf: self._ao_state(tf) for tf in tf_list}

        if any(not s for s in states.values()):
            return False

        m1  = states[tf_list[0]]
        m5  = states[tf_list[1]]
        m15 = states[tf_list[2]]

        cond_m1  = m1["above_zero"]  and m1["turned_green"]
        cond_m5  = m5["above_zero"]  and (m5["turned_green"]  or m5["stayed_green"])
        cond_m15 = m15["above_zero"] and (m15["turned_green"] or m15["stayed_green"])
        return cond_m1 and cond_m5 and cond_m15

    def _check_short_signal(self) -> bool:
        """检查三时间框架做空共振条件。"""
        tf_list = self.cfg["timeframes"]
        states = {tf: self._ao_state(tf) for tf in tf_list}

        if any(not s for s in states.values()):
            return False

        m1  = states[tf_list[0]]
        m5  = states[tf_list[1]]
        m15 = states[tf_list[2]]

        cond_m1  = m1["below_zero"]  and m1["turned_red"]
        cond_m5  = m5["below_zero"]  and (m5["turned_red"]  or m5["stayed_red"])
        cond_m15 = m15["below_zero"] and (m15["turned_red"] or m15["stayed_red"])
        return cond_m1 and cond_m5 and cond_m15

    # ──────────────────────────────────────────
    # 持仓管理
    # ──────────────────────────────────────────

    def _manage_positions(self):
        """逐笔检查持仓的止损 / 止盈条件。"""
        positions = self.order_mgr.get_positions(
            symbol=self.cfg["symbol"], magic=self.cfg["magic"]
        )
        m1_state = self._ao_state(self.cfg["timeframes"][0])
        if not m1_state:
            return

        for pos in positions:
            ticket = pos.ticket
            # 初始化计数器
            if ticket not in self._candle_counter:
                self._candle_counter[ticket] = 0
            self._candle_counter[ticket] += 1

            is_profit = pos.profit > 0
            is_long   = pos.type == mt5.ORDER_TYPE_BUY

            # ── 止损检查：AO 变色 + 亏损 ──
            color_changed = (
                (is_long  and m1_state["turned_red"]) or
                (not is_long and m1_state["turned_green"])
            )
            if color_changed and not is_profit:
                logger.info(f"止损平仓 ticket={ticket} profit={pos.profit:.2f}")
                self.order_mgr.close_position(pos)
                self._candle_counter.pop(ticket, None)
                continue

            # ── 止盈检查：盈利 + 满 2 根 K 线 ──
            tp_candles = self.cfg.get("tp_candles", 2)
            if is_profit and self._candle_counter[ticket] >= tp_candles:
                logger.info(f"止盈平仓 ticket={ticket} profit={pos.profit:.2f}")
                self.order_mgr.close_position(pos)
                self._candle_counter.pop(ticket, None)

    # ──────────────────────────────────────────
    # 主循环
    # ──────────────────────────────────────────

    def run_once(self):
        """执行一次完整的策略检查。"""
        self._manage_positions()

        positions = self.order_mgr.get_positions(
            symbol=self.cfg["symbol"], magic=self.cfg["magic"]
        )
        if positions:  # 已有持仓，不重复开仓
            return

        if self._check_long_signal():
            logger.info("AO MTF 做多信号触发")
            self.order_mgr.open_buy(
                self.cfg["symbol"], self.cfg["lot"],
                magic=self.cfg["magic"], comment=self.cfg["comment"],
            )
        elif self._check_short_signal():
            logger.info("AO MTF 做空信号触发")
            self.order_mgr.open_sell(
                self.cfg["symbol"], self.cfg["lot"],
                magic=self.cfg["magic"], comment=self.cfg["comment"],
            )

    def run(self, interval_seconds: int = 30):
        """持续运行策略主循环，每 interval_seconds 秒检查一次。"""
        if not self.client.connect():
            logger.error("无法连接 MT5，策略退出")
            return
        logger.info(
            f"AO MTF 策略启动 | {self.cfg['symbol']} "
            f"| 时间框架: {self.cfg['timeframes']}"
        )
        try:
            while True:
                self.run_once()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("策略手动停止")
        finally:
            self.client.disconnect()


if __name__ == "__main__":
    print("=== AOMTFStrategy 多时间框架共振策略测试 ===")
    print("本测试将连接 MT5，逐一检查各时间框架 AO 状态（不自动开仓循环）")

    strategy = AOMTFStrategy()

    if not strategy.client.connect():
        print("MT5 连接失败，测试中止")
        exit(1)

    # 1. 逐一检查各时间框架的 AO 状态
    from config import AO_MTF_CONFIG
    for tf in AO_MTF_CONFIG["timeframes"]:
        state = strategy._ao_state(tf)
        if state:
            print(
                f"[_ao_state] {tf:4s} | "
                f"above_zero={state['above_zero']}  "
                f"below_zero={state['below_zero']}  "
                f"color={state['color']:7s}  "
                f"turned_green={state['turned_green']}  "
                f"turned_red={state['turned_red']}  "
                f"stayed_green={state['stayed_green']}  "
                f"stayed_red={state['stayed_red']}"
            )
        else:
            print(f"[_ao_state] {tf} 数据不足，无法计算")

    # 2. 检查做多/做空共振信号
    long_ok  = strategy._check_long_signal()
    short_ok = strategy._check_short_signal()
    print(f"[_check_long_signal]  做多共振: {long_ok}")
    print(f"[_check_short_signal] 做空共振: {short_ok}")

    # 3. 查询当前策略持仓
    positions = strategy.order_mgr.get_positions(
        symbol=AO_MTF_CONFIG["symbol"],
        magic=AO_MTF_CONFIG["magic"],
    )
    print(f"[get_positions] 当前策略持仓数: {len(positions)}")
    for pos in positions:
        print(f"  ticket={pos.ticket}  type={'BUY' if pos.type == 0 else 'SELL'}  "
              f"profit={pos.profit:.2f}  candles_held={strategy._candle_counter.get(pos.ticket, 0)}")

    # 4. 执行一次完整策略检查
    print("[run_once] 执行一次策略检查...")
    strategy.run_once()
    print("[run_once] 完成")

    strategy.client.disconnect()
    print("=== 测试完成 ===")
