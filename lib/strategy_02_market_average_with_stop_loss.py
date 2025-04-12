#!/usr/bin/env python3
import backtrader as bt
from datetime import datetime, timedelta, timezone

# ANSI color codes for convenience.
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
RESET = '\033[0m'

class market_average_with_stop_loss(bt.Strategy):

    params = (
        ('avg_type', 'EMA'),       # 'SMA', 'EMA', or 'WMA'
        ('sma_period', 600),       # Period for the moving average indicator
        ('buy_threshold', 0.03),   # Buy when price is at least 3% below the average
        ('sell_threshold', 0.07),  # Sell when price is at least 7% above the entry price
        ('stop_loss', 0.05),       # Stop loss: exit if price drops 5% below entry
        ('trade_on_live', True),   # Only trade on live data (skip historical bars)
        ('live_lag_seconds', 65),  # Bar age threshold in seconds
        ('printlog', True)         # Set to False to disable printing
    )

    def printout(self, txt, color=None):
        """Simple print wrapper that adds a color if enabled."""
        if self.p.printlog:
            now = self.datas[0].datetime.datetime(0) if len(self.datas[0]) > 0 else datetime.now()
            if color:
                txt = f"{color}{txt}{RESET}"
            print(f"{now.isoformat()} {txt}")

    def create_status_line(self, buy_val, current, sell_val, state, profit=None, profit_pct=None, width=30):
        """
        Build a status line that aligns fields in fixed-width columns.
        
        For waiting BUY, returns a line like:
        "Waiting BUY:  0.3055 |----*-----|  0.3000  0.3055 |"
        
        For waiting SELL, returns a line like:
        "Waiting SELL: 0.3055 |----*-----|  0.3362  0.3400 | P/L:  0.0307 ( 10.04%)"
        """
        lower = buy_val
        upper = sell_val
        if upper == lower:
            pos = width // 2
        else:
            ratio = (current - lower) / (upper - lower)
            ratio = max(0, min(1, ratio))
            pos = int(ratio * width)
        bar = "-" * pos + "{"+ f"{current:8.4f}"  +"}" + "-" * (width - pos)
        if state == "waiting BUY":
            return f"Waiting BUY : {buy_val:8.4f} |{bar}| {sell_val:8.4f} |"
        else:
            return f"Waiting SELL: {buy_val:8.4f} |{bar}| {sell_val:8.4f} | P/L: {profit:8.4f} ({profit_pct:6.2f}%)"

    def __init__(self):
        avg_type = self.p.avg_type.upper()
        if avg_type == 'SMA':
            self.ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.sma_period)
        elif avg_type == 'EMA':
            self.ma = bt.indicators.ExponentialMovingAverage(self.data.close, period=self.p.sma_period)
        elif avg_type == 'WMA':
            self.ma = bt.indicators.WeightedMovingAverage(self.data.close, period=self.p.sma_period)
        else:
            raise ValueError(f"Unknown avg_type: {self.p.avg_type}")
        self.order = None
        self.entry_price = None
        self.printout(f"Strategy initialized with avg_type {self.p.avg_type}, sma_period {self.p.sma_period}", color=YELLOW)

    def next(self):
        # If live trading is enabled, skip bars that are too old.
        if self.p.trade_on_live:
            # Make bar_time timezone-aware.
            bar_time = self.datas[0].datetime.datetime(0).replace(tzinfo=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            lag = (now - bar_time).total_seconds()
            if lag > self.p.live_lag_seconds:
                self.printout(f"Skipping bar. Bar lag {lag:.1f} sec exceeds threshold.", color=YELLOW)
                return
            
        target_price_sell = self.data.close[0] * (1 + self.p.sell_threshold)

        if not self.position:
            trigger = self.ma[0] * (1 - self.p.buy_threshold)
            status = self.create_status_line(trigger, self.data.close[0], self.data.close[0], "waiting BUY")
            self.printout(f"{status}")
            if self.data.close[0] <= trigger:
                self.printout(f"BUY SIGNAL: Price {self.data.close[0]:.4f} below trigger {trigger:.4f}", color=GREEN)
                self.order = self.buy(size=(self.broker.getcash() / self.data.close[0]) * 0.95)
        else:

            target_price_sell = self.position.price * (1 + self.p.sell_threshold)
            stop_loss_price = self.position.price * (1 - self.p.stop_loss)
            profit = self.data.close[0] - self.position.price
            profit_pct = (profit / self.position.price) * 100
            status = self.create_status_line(self.position.price, self.data.close[0], target_price_sell, "waiting SELL", profit, profit_pct)
            self.printout(f"{status}")
            if self.data.close[0] <= stop_loss_price:
                self.printout(f"STOP LOSS SIGNAL: Price {self.data.close[0]:.4f} below stop loss {stop_loss_price:.4f}", color=RED)
                self.order = self.sell(size=self.position.size)
            elif self.data.close[0] >= target_price_sell:
                self.printout(f"TAKE PROFIT SIGNAL: Price {self.data.close[0]:.4f} above target {target_price_sell:.4f}", color=RED)
                self.order = self.sell(size=self.position.size)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = self.position.price
                self.printout(f"BUY EXECUTED at {self.entry_price:.4f}", color=GREEN)
            elif order.issell():
                exit_price = self.data.close[0]
                profit = exit_price - self.entry_price
                profit_pct = (profit / self.entry_price) * 100
                self.printout(f"SELL EXECUTED at {exit_price:.4f} | Profit: {profit:.4f} ({profit_pct:.2f}%)", color=RED)
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.printout("Order cancelled/margin/rejected", color=YELLOW)
            self.order = None

if __name__ == '__main__':

    from scenario_XRPUSDT import create_cerebro_with_warmup

    cerebro = create_cerebro_with_warmup(    start_date = datetime(2025, 1, 1),
                                             end_date = datetime(2025, 3, 1),)
    
    cerebro.addstrategy(market_average_with_stop_loss,
                        avg_type='EMA',
                        sma_period=20,
                        buy_threshold=0.025,
                        sell_threshold=0.045,
                        stop_loss=0.05,
                        trade_on_live=False,
                        live_lag_seconds=65,
                        printlog=True)
    
    cerebro.broker.setcommission(commission=0.001)
    cerebro.run()
    cerebro.plot()
