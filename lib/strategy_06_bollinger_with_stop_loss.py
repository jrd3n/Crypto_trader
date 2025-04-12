#!/usr/bin/env python3
import backtrader as bt
import logging
from datetime import datetime, timezone

# Configure logging globally
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ANSI colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
RESET = '\033[0m'

class CustomBollingerStrategySL(bt.Strategy):
    """
    Bollinger Strategy + Stop-Loss
    Buys when price < lower band, Sells when price > upper band, 
    and also uses a stop-loss parameter to exit if price drops 
    below (entry_price * (1 - stop_loss)).
    """

    params = (
        # Bollinger parameters
        ('period', 450),
        ('lower_dev', 0.55),
        ('upper_dev', 0.005),

        # Stop-Loss parameter
        ('stop_loss', 0.05),  # e.g., 5% below entry price

        # Logging/trading controls
        ('log_enabled', True),
        ('trade_on_live', True),
        ('live_lag_seconds', 65),
        ('min_order', 10.0)
    )

    def log(self, txt, color=None):
        """Helper method for logging with optional color."""
        if not self.p.log_enabled:
            return
        dt_str = self.datas[0].datetime.datetime(0).strftime('%Y-%m-%d %H:%M:%S')
        if color:
            txt = f"{color}{txt}{RESET}"
        logging.info(f"{dt_str} {txt}")

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
        # Bollinger calculations
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.period)
        self.std = bt.indicators.StandardDeviation(self.data.close, period=self.p.period)

        self.lower_band = self.sma - self.std * self.p.lower_dev
        self.upper_band = self.sma + self.std * self.p.upper_dev

        self.order = None
        self.entry_price = None

        self.log("Strategy initialized.", color=YELLOW)

    def next(self):
        """Main logic each bar."""
        # If trade_on_live is enabled, skip old bars
        if self.p.trade_on_live:
            bar_time = self.datas[0].datetime.datetime(0).replace(tzinfo=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            lag = (now - bar_time).total_seconds()
            if lag > self.p.live_lag_seconds:
                self.log(f"Skipping bar; bar lag {lag:.1f}s > threshold {self.p.live_lag_seconds}", color=YELLOW)
                return

        # Build a dynamic status line
        if not self.position:
            status_line = self.create_status_line(
                self.lower_band[0],
                self.data.close[0],
                self.upper_band[0],
                state="waiting BUY"
            )
        else:
            # If in position, compute profit stats
            profit = self.data.close[0] - self.position.price
            profit_pct = (profit / self.position.price) * 100
            status_line = self.create_status_line(
                self.position.price,
                self.data.close[0],
                self.upper_band[0],
                state="waiting SELL",
                profit=profit,
                profit_pct=profit_pct
            )
        self.log(f"Status: {status_line}")

        # If an order is pending, do nothing
        if self.order:
            self.log("Order pending, skipping bar.", color=YELLOW)
            return

        # Check if we have enough cash to buy
        cash = self.broker.getcash()
        if not self.position and cash < self.p.min_order:
            self.log(f"Cash {cash:.2f} < min_order {self.p.min_order}, skipping buy.", color=YELLOW)
            return

        if not self.position:
            # Buy if price < lower band
            if self.data.close[0] < self.lower_band[0]:
                size = (cash / self.data.close[0]) * 0.95
                self.log(f"Buy Signal: current {self.data.close[0]:.4f} < lower_band {self.lower_band[0]:.4f}, size={size:.2f}", color=GREEN)
                self.order = self.buy(size=size)
        else:
            # Check Stop Loss
            stop_loss_price = self.position.price * (1 - self.p.stop_loss)
            if self.data.close[0] <= stop_loss_price:
                self.log(
                    f"STOP LOSS triggered @ {self.data.close[0]:.4f}; threshold={stop_loss_price:.4f}",
                    color=RED
                )
                self.order = self.sell(size=self.position.size)
                return

            # Check upper band => take profit
            if self.data.close[0] > self.upper_band[0]:
                self.log(f"Take Profit: current {self.data.close[0]:.4f} > upper_band {self.upper_band[0]:.4f}", color=RED)
                self.order = self.sell(size=self.position.size)

    def notify_order(self, order):
        """Handle order status changes."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = self.position.price
                self.log(f"BUY EXECUTED @ {self.entry_price:.4f}", color=GREEN)
            elif order.issell():
                exit_price = self.data.close[0]
                profit = exit_price - self.entry_price
                profit_pct = (profit / self.entry_price) * 100
                self.log(f"SELL EXECUTED @ {exit_price:.4f} | Profit: {profit:.4f} ({profit_pct:.2f}%)", color=RED)
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order {order.Status[order.status]}", color=YELLOW)
            self.order = None


if __name__ == '__main__':

    from scenario_XRPUSDT import create_cerebro_with_warmup

    cerebro = create_cerebro_with_warmup(    start_date = datetime(2025, 1, 1),
                                             end_date = datetime(2025, 3, 1),)
    cerebro.addstrategy(
        CustomBollingerStrategySL,
        period=600,        # For Bollinger
        lower_dev=3.6,    # e.g. 5% stdev
        upper_dev=0.07,    # e.g. 7% stdev
        stop_loss=0.015,    # 5% below entry
        log_enabled=True,
        trade_on_live=False,
        live_lag_seconds=65,
        min_order=10.0
    )

    cerebro.run()
    cerebro.plot()
