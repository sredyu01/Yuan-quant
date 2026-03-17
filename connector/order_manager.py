# -*- coding: utf-8 -*-
"""
链接模块 - 下单操作 (connector/order_manager.py)
封装 MT5 的开仓、平仓、修改订单、查询持仓等操作。
"""

import MetaTrader5 as mt5
from typing import Optional, List
from utils.logger import get_logger

logger = get_logger(__name__)


class OrderManager:
    """MT5 订单管理器，封装买卖开平仓操作。"""

    @staticmethod
    def _build_request(
        action, symbol: str, order_type,
        lot: float, price: float,
        sl: float = 0.0, tp: float = 0.0,
        magic: int = 0, comment: str = "",
        deviation: int = 20,
    ) -> dict:
        return {
            "action":       action,
            "symbol":       symbol,
            "volume":       lot,
            "type":         order_type,
            "price":        price,
            "sl":           sl,
            "tp":           tp,
            "deviation":    deviation,
            "magic":        magic,
            "comment":      comment,
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

    def _send(self, request: dict) -> Optional[int]:
        """发送交易请求，返回 deal ticket 或 None。"""
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else "N/A"
            logger.error(f"下单失败 retcode={code} | {request}")
            return None
        logger.info(
            f"下单成功 | {request['symbol']} "
            f"{'BUY' if request['type'] == mt5.ORDER_TYPE_BUY else 'SELL'} "
            f"{request['volume']} lot | deal={result.deal}"
        )
        return result.deal

    # ──────────────────────────────────────────
    # 开仓
    # ──────────────────────────────────────────

    def open_buy(
        self, symbol: str, lot: float,
        sl: float = 0.0, tp: float = 0.0,
        magic: int = 0, comment: str = "",
    ) -> Optional[int]:
        """市价买入开多仓。返回 deal ticket，失败返回 None。"""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"无法获取 {symbol} 报价")
            return None
        req = self._build_request(
            mt5.TRADE_ACTION_DEAL, symbol, mt5.ORDER_TYPE_BUY,
            lot, tick.ask, sl, tp, magic, comment,
        )
        return self._send(req)

    def open_sell(
        self, symbol: str, lot: float,
        sl: float = 0.0, tp: float = 0.0,
        magic: int = 0, comment: str = "",
    ) -> Optional[int]:
        """市价卖出开空仓。返回 deal ticket，失败返回 None。"""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"无法获取 {symbol} 报价")
            return None
        req = self._build_request(
            mt5.TRADE_ACTION_DEAL, symbol, mt5.ORDER_TYPE_SELL,
            lot, tick.bid, sl, tp, magic, comment,
        )
        return self._send(req)

    # ──────────────────────────────────────────
    # 平仓
    # ──────────────────────────────────────────

    def close_position(self, position) -> bool:
        """
        平掉指定持仓。
        position: mt5.TradePosition 对象（由 get_positions 返回）
        """
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            return False
        if position.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        req = self._build_request(
            mt5.TRADE_ACTION_DEAL, position.symbol, order_type,
            position.volume, price, magic=position.magic,
            comment="close",
        )
        req["position"] = position.ticket
        result = mt5.order_send(req)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"平仓失败 ticket={position.ticket} retcode={result.retcode if result else 'N/A'}")
            return False
        logger.info(f"平仓成功 ticket={position.ticket} symbol={position.symbol}")
        return True

    def close_all_positions(self, symbol: str = None, magic: int = None) -> int:
        """平掉所有（或按品种/魔数筛选的）持仓，返回成功平仓数量。"""
        positions = self.get_positions(symbol=symbol, magic=magic)
        count = sum(1 for p in positions if self.close_position(p))
        logger.info(f"批量平仓完成，共平仓 {count} 笔")
        return count

    # ──────────────────────────────────────────
    # 查询
    # ──────────────────────────────────────────

    @staticmethod
    def get_positions(symbol: str = None, magic: int = None) -> List:
        """获取当前持仓列表，可按品种或魔数筛选。"""
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            return []
        if magic is not None:
            positions = [p for p in positions if p.magic == magic]
        return list(positions)

    @staticmethod
    def get_position_count(symbol: str = None, magic: int = None) -> int:
        """返回当前持仓数量。"""
        return len(OrderManager.get_positions(symbol=symbol, magic=magic))
