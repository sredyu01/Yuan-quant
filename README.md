# Yuan Quant - MT5 XAUUSD MTF AO/EMA Demo Strategy

这是一个用于 MT5 模拟盘的 XAUUSD 多时间框架短持仓策略脚本。

## 策略逻辑

所有信号只在新的 M1 K 线收盘后检查，不在当前未收盘 K 线波动中开仓或平仓。

### 入场

5min 与 15min 同向趋势过滤：

- 多头：AO > 0、收盘价 > EMA20、EMA20 > EMA60
- 空头：AO < 0、收盘价 < EMA20、EMA20 < EMA60

1min 排列过滤：

- 多头：EMA5 > EMA10 > EMA20 > EMA60
- 空头：EMA5 < EMA10 < EMA20 < EMA60

触发：

- 多头：M1 AO 在 0 轴上方，AO 颜色红转绿，且当前收盘价突破前一根高点
- 空头：M1 AO 在 0 轴下方，AO 颜色绿转红，且当前收盘价跌破前一根低点

### 离场

- 多单：第一根阴线收盘后平 0.1 手；AO 首次变红后平剩余仓位
- 空单：第一根阳线收盘后平 0.1 手；AO 首次变绿后平剩余仓位

## 安装

```bash
pip install -r requirements.txt
```

## 运行

请先打开 MT5 终端并登录模拟盘账号，然后运行：

```bash
python xauusd_mtf_ao_ema_demo.py --symbol XAUUSD
```

如果你的券商黄金品种名不同，例如 `XAUUSDm`：

```bash
python xauusd_mtf_ao_ema_demo.py --symbol XAUUSDm
```

只打印信号和下单请求、不实际交易：

```bash
python xauusd_mtf_ao_ema_demo.py --symbol XAUUSD --dry-run
```

可调参数示例：

```bash
python xauusd_mtf_ao_ema_demo.py --symbol XAUUSD --volume 0.20 --first-exit-volume 0.10 --max-spread-points 80 --deviation-points 30
```

## 注意

该脚本是策略执行框架，不承诺收益或胜率。建议先用 `--dry-run` 和模拟盘长时间观察成交、点差、滑点、品种合约规格与日志后，再继续优化。
