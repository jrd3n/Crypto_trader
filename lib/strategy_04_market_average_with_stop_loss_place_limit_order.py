#!/usr/bin/env python3
import backtrader as bt
from datetime import datetime, timedelta

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
        ('sell_threshold', 0.07),  # Take profit when price is at least 7% above entry price
        ('stop_loss', 0.05),       # Stop loss: exit if price drops 5% below entry
        ('trade_on_live', True),   # Only trade on live data (skip historical bars)
        ('live_lag_seconds', 65),  # Bar age threshold in seconds
        ('printlog', True)         # Set to False to disable printing
    )

    def printout(self, txt, color=None):
        if self.p.printlog:
            now = self.datas[0].datetime.datetime(0) if len(self.datas[0]) > 0 else datetime.now()
            if color:
                txt = f"{color}{txt}{RESET}"
            print(f"{now.isoformat()} {txt}")

    def __init__(self):
        # Set up moving average based on the chosen type.
        avg_type = self.p.avg_type.upper()
        if avg_type == 'SMA':
            self.ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.sma_period)
        elif avg_type == 'EMA':
            self.ma = bt.indicators.ExponentialMovingAverage(self.data.close, period=self.p.sma_period)
        elif avg_type == 'WMA':
            self.ma = bt.indicators.WeightedMovingAverage(self.data.close, period=self.p.sma_period)
        else:
            raise ValueError(f"Unknown avg_type: {self.p.avg_type}")

        # No persistent order storage—we cancel any order each cycle.
        self.order = None
        self.entry_price = None
        self.printout(f"Strategy initialized with avg_type {self.p.avg_type}, sma_period {self.p.sma_period}", color=YELLOW)

    def next(self):
        # If live trading is enabled, skip bars that are too old.
        if self.p.trade_on_live:
            bar_time = self.datas[0].datetime.datetime(0)
            now = datetime.now(datetime.UTC)  # assuming UTC timestamps
            lag = (now - bar_time).total_seconds()
            if lag > self.p.live_lag_seconds:
                self.printout(f"Skipping bar. Bar lag {lag:.1f} sec exceeds threshold.", color=YELLOW)
                return

        # Every cycle, cancel any existing pending orders.
        if self.order:
            self.cancel(self.order)
            self.order = None
            self.printout("Cancelled pending order", color=YELLOW)

        # When not in position, place a new entry bracket order unconditionally.
        if not self.position:
            size = (self.broker.getcash() / self.data.close[0]) * 0.95
            entry_price = self.data.close[0]
            stop_loss_price = entry_price * (1 - self.p.stop_loss)
            target_price = entry_price * (1 + self.p.sell_threshold)
            self.order = self.buy_bracket(
                size=size,
                price=entry_price,
                stopprice=stop_loss_price,
                limitprice=target_price
            )
            self.printout(
                f"Placing new entry order: entry={entry_price:.4f}, stop={stop_loss_price:.4f}, target={target_price:.4f}",
                color=GREEN)
        else:
            # If already in a position, update exit orders.
            # We'll use the original entry price stored when the position was opened.
            entry_price = self.entry_price if self.entry_price is not None else self.position.price
            stop_loss_price = entry_price * (1 - self.p.stop_loss)
            target_price = entry_price * (1 + self.p.sell_threshold)
            # Here, we cancel the previous exit orders (if any) and place new ones.
            # Note: In a bracket order, the exit orders are part of a multi-order,
            # so in a real-world scenario, you might have to manage each child order separately.
            
            self.order = self.sell_bracket(
                size=self.position.size,
                price=self.data.close[0],
                stopprice=stop_loss_price,
                limitprice=target_price
            )

            self.printout(
                f"Updating exit orders: new stop={stop_loss_price:.4f}, new target={target_price:.4f}",
                color=YELLOW)

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
    cerebro = create_cerebro_with_warmup()
    cerebro.addstrategy(market_average_with_stop_loss,
                        avg_type='EMA',
                        sma_period=30,
                        buy_threshold=0.03,
                        sell_threshold=0.07,
                        stop_loss=0.05,
                        trade_on_live=False,
                        live_lag_seconds=65,
                        printlog=True)
    
    cerebro.broker.setcommission(commission=0.001)
    cerebro.run()
    cerebro.plot()
