# -*- coding: utf-8 -*-
"""
算法模块 - 均线交叉策略 (strategies/ma_cross.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【策略说明】
  时间框架：H1（1小时）
  核心逻辑：
    - MA20 上穿 MA60（金叉）→ 开多单
    - MA20 下穿 MA60（死叉）→ 开空单
    - 与持仓方向相反的交叉信号出现时平仓并反向开仓

  每次只持有一个方向的仓位，新信号触发时先平旧仓再开新仓。

【参数（来自 config/strategy_config.py）】
  symbol    : 交易品种
  timeframe : H1
  fast_ma   : 20
  slow_ma   : 60
  lot       : 交易手数
  sl_pips   : 止损点数
  tp_pips   : 止盈点数
  magic     : 魔术数字
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import time
from config import MA_CROSS_CONFIG
from connector import MT5Client, OrderManager
from indicators import calculate_ma, ma_cross_signal
from utils.logger import get_logger
from utils.helpers import pips_to_price

logger = get_logger(__name__)


class MACrossStrategy:
    """均线交叉策略（MA20 / MA60，H1 时间框架）。"""

    def __init__(self, config: dict = None):
        self.cfg = config or MA_CROSS_CONFIG
        self.client = MT5Client()
        self.order_mgr = OrderManager()

    # ──────────────────────────────────────────
    # 信号计算
    # ──────────────────────────────────────────

    def _get_signal(self) -> int:
        """
        拉取最新 K 线并计算均线交叉信号。
        返回：1（金叉做多） / -1（死叉做空） / 0（无信号）
        """
        df = self.client.get_rates(
            symbol=self.cfg["symbol"],
            timeframe=self.cfg["timeframe"],
            count=self.cfg["slow_ma"] + 10,
        )
        if df.empty:
            return 0

        fast = calculate_ma(df["close"], self.cfg["fast_ma"])
        slow = calculate_ma(df["close"], self.cfg["slow_ma"])
        signal = ma_cross_signal(fast, slow)

        # 取最后一根已收盘 K 线的信号（iloc[-2] 为最后一根完整 K 线）
        return int(signal.iloc[-2])

    # ──────────────────────────────────────────
    # 执行
    # ──────────────────────────────────────────

    def _get_sl_tp(self, direction: int):
        """计算止损/止盈价格。direction: 1=多, -1=空"""
        import MetaTrader5 as mt5
        tick = mt5.symbol_info_tick(self.cfg["symbol"])
        sl_offset = pips_to_price(self.cfg["symbol"], self.cfg["sl_pips"])
        tp_offset = pips_to_price(self.cfg["symbol"], self.cfg["tp_pips"])
        if direction == 1:
            price = tick.ask
            sl = (price - sl_offset) if self.cfg["sl_pips"] else 0.0
            tp = (price + tp_offset) if self.cfg["tp_pips"] else 0.0
        else:
            price = tick.bid
            sl = (price + sl_offset) if self.cfg["sl_pips"] else 0.0
            tp = (price - tp_offset) if self.cfg["tp_pips"] else 0.0
        return sl, tp

    def run_once(self):
        """执行一次策略检查（适合定时调用或在 main 循环中调用）。"""
        signal = self._get_signal()
        if signal == 0:
            return

        symbol = self.cfg["symbol"]
        magic  = self.cfg["magic"]
        lot    = self.cfg["lot"]

        positions = self.order_mgr.get_positions(symbol=symbol, magic=magic)

        # 平掉反向持仓
        for pos in positions:
            import MetaTrader5 as mt5
            if (signal == 1 and pos.type == mt5.ORDER_TYPE_SELL) or \
               (signal == -1 and pos.type == mt5.ORDER_TYPE_BUY):
                self.order_mgr.close_position(pos)

        # 若已有同向持仓则不重复开仓
        positions = self.order_mgr.get_positions(symbol=symbol, magic=magic)
        if positions:
            return

        sl, tp = self._get_sl_tp(signal)
        if signal == 1:
            self.order_mgr.open_buy(symbol, lot, sl=sl, tp=tp,
                                    magic=magic, comment=self.cfg["comment"])
        else:
            self.order_mgr.open_sell(symbol, lot, sl=sl, tp=tp,
                                     magic=magic, comment=self.cfg["comment"])

    def run(self, interval_seconds: int = 60):
        """持续运行策略主循环。"""
        if not self.client.connect():
            logger.error("无法连接 MT5，策略退出")
            return
        logger.info(f"MA Cross 策略启动 | {self.cfg['symbol']} {self.cfg['timeframe']}")
        try:
            while True:
                self.run_once()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("策略手动停止")
        finally:
            self.client.disconnect()
