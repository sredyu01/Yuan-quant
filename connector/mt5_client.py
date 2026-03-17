# -*- coding: utf-8 -*-
"""
链接模块 - MT5 连接管理 (connector/mt5_client.py)
负责 MT5 终端的初始化、登录、断开连接，以及行情数据获取。
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from typing import Optional
from utils.logger import get_logger
from config import MT5_ACCOUNT, TIMEFRAMES, DATA

logger = get_logger(__name__)


class MT5Client:
    """MT5 连接客户端，封装初始化、登录和数据获取操作。"""

    def __init__(self, account: dict = None):
        """
        Parameters
        ----------
        account : dict  MT5 账户配置，默认使用 config.MT5_ACCOUNT
        """
        self.account = account or MT5_ACCOUNT
        self._connected = False

    # ──────────────────────────────────────────
    # 连接 / 断开
    # ──────────────────────────────────────────

    def connect(self) -> bool:
        """初始化 MT5 终端并登录账户。返回是否成功。"""
        path = self.account.get("path") or None
        kwargs = {"timeout": self.account["timeout"]}
        if path:
            kwargs["path"] = path

        if not mt5.initialize(**kwargs):
            logger.error(f"MT5 初始化失败: {mt5.last_error()}")
            return False

        authorized = mt5.login(
            login=self.account["login"],
            password=self.account["password"],
            server=self.account["server"],
        )
        if not authorized:
            logger.error(f"MT5 登录失败: {mt5.last_error()}")
            mt5.shutdown()
            return False

        info = mt5.account_info()
        logger.info(
            f"MT5 登录成功 | 账号: {info.login} | 服务器: {info.server} "
            f"| 余额: {info.balance} {info.currency}"
        )
        self._connected = True
        return True

    def disconnect(self):
        """断开 MT5 连接。"""
        mt5.shutdown()
        self._connected = False
        logger.info("MT5 已断开连接")

    def is_connected(self) -> bool:
        return self._connected and mt5.terminal_info() is not None

    # ──────────────────────────────────────────
    # 行情数据
    # ──────────────────────────────────────────

    def get_rates(
        self,
        symbol: str,
        timeframe: str,
        count: int = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        获取 K 线数据，返回 DataFrame。

        Parameters
        ----------
        symbol    : 交易品种
        timeframe : 时间框架字符串，如 'H1'
        count     : 拉取 K 线数量（与 date_from/date_to 二选一）
        date_from : 起始时间
        date_to   : 结束时间

        Returns
        -------
        pd.DataFrame  列：time, open, high, low, close, tick_volume, spread, real_volume
        """
        tf = TIMEFRAMES.get(timeframe)
        if tf is None:
            raise ValueError(f"未知时间框架: {timeframe}")

        if date_from and date_to:
            rates = mt5.copy_rates_range(symbol, tf, date_from, date_to)
        else:
            n = count or DATA["default_bars"]
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, n)

        if rates is None or len(rates) == 0:
            logger.warning(f"获取 {symbol} {timeframe} 数据为空: {mt5.last_error()}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
        return df

    def get_symbol_info(self, symbol: str):
        """获取交易品种信息。"""
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.warning(f"无法获取品种信息: {symbol}")
        return info

    def get_account_info(self):
        """获取账户信息。"""
        return mt5.account_info()
