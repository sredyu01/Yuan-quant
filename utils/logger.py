# -*- coding: utf-8 -*-
"""
工具模块 - 日志 (utils/logger.py)
统一日志配置：同时输出到控制台和滚动文件。
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_initialized: set = set()


def get_logger(name: str = "yuan_quant") -> logging.Logger:
    """
    获取已配置好的 Logger 实例（单例模式，避免重复添加 Handler）。

    Parameters
    ----------
    name : str  Logger 名称，建议传入 __name__

    Returns
    -------
    logging.Logger
    """
    # 延迟导入，避免循环依赖
    from config.settings import LOGGING

    logger = logging.getLogger(name)

    if name in _initialized:
        return logger

    level = getattr(logging, LOGGING["level"].upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 Handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # 文件 Handler（滚动日志）
    log_dir = LOGGING["log_dir"]
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, LOGGING["log_file"])
    fh = RotatingFileHandler(
        log_path,
        maxBytes=LOGGING["max_bytes"],
        backupCount=LOGGING["backup_count"],
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    _initialized.add(name)
    return logger
