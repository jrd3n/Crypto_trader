import backtrader as bt
import pandas as pd
import logging
from datetime import datetime

# Configure logging globally.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')

# ANSI color codes for convenience.
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
RESET = '\033[0m'

"""
CustomBollingerStrategy: A Trading Strategy Based on Custom Bollinger Bands

Overview:
-----------
This strategy computes a simple moving average (SMA) and standard deviation over a specified period,
and then defines custom bands as follows:
  - Lower Band: SMA - (Standard Deviation * lower_dev)
  - Upper Band: SMA + (Standard Deviation * upper_dev)

Trading Signals:
-----------
- Buy Signal: When the current close is below the lower band, a market buy order is issued.
- Sell Signal: When the current close is above the upper band, a market sell order is issued.

Order Management:
-----------
- Only one order is active at a time.
- The strategy calculates an order size based on available cash.
- A minimum order value is enforced: orders are only placed if available cash is above this threshold.
- The optimization grid will search over different values for `period`, `lower_dev`, and `upper_dev`.

Live Trading Control:
-----------
- trade_on_live (True/False): When True, the strategy will skip trading on bars older than a certain threshold.
- live_lag_seconds: Maximum allowed age (in seconds) for a bar to be considered live.
"""

class CustomBollingerStrategy(bt.Strategy):
    params = (
        ('period', 450),         # Period for the moving average and standard deviation
        ('lower_dev', 0.55),      # Multiplier for standard deviation for the lower band
        ('upper_dev', 0.005),     # Multiplier for standard deviation for the upper band
        ('log_enabled', True),    # Enable logging if True
        ('trade_on_live', True),  # Only trade on live data (skip historical bars)
        ('live_lag_seconds', 65), # Maximum allowed lag in seconds for a bar to be considered live
        ('min_order', 10.0)       # Minimum cash required to place an order
    )

    def log(self, txt, dt=None, color=None):
        # Use the data feed's datetime if available; otherwise, fallback to current time.
        if dt is None:
            if len(self.datas[0]) > 0:
                dt = self.datas[0].datetime.datetime(0)
            else:
                dt = datetime.now()
        if color:
            txt = f"{color}{txt}{RESET}"
        logging.info(f'{dt.isoformat()} {txt}')

    def create_status_line(self, lower_val, current, upper_val, state, profit=None, profit_pct=None, width=40):
        """
        Create a status line that displays:
          - For "waiting BUY": "waiting BUY: {lower_val} |----*-----| {current}"
          - For "waiting SELL": "waiting SELL: Entry {lower_val} -> Target {upper_val} |----*-----| {current} | P/L: {profit} ({profit_pct}%)"
        The '*' marker moves based on the relative position of the current price between the trigger values.
        """
        if state == "waiting BUY":
            low = lower_val
            high = upper_val  # Use upper band as a reference for display.
        else:
            low = lower_val
            high = upper_val

        if high == low:
            pos = width // 2
        else:
            ratio = (current - low) / (high - low)
            ratio = max(0, min(1, ratio))
            pos = int(ratio * width)
        bar = "-" * pos + "*" + "-" * (width - pos)

        if state == "waiting BUY":
            return f"waiting BUY: {lower_val:.4f} |{bar}| {current:.4f}"
        else:
            return f"waiting SELL: Entry {lower_val:.4f} -> Target {upper_val:.4f} |{bar}| {current:.4f} | P/L: {profit:.4f} ({profit_pct:.2f}%)"

    def __init__(self):
        # Compute the simple moving average and standard deviation.
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.period)
        self.std = bt.indicators.StandardDeviation(self.data.close, period=self.p.period)
        
        # Define custom bands.
        self.lower_band = self.sma - self.std * self.p.lower_dev
        self.upper_band = self.sma + self.std * self.p.upper_dev

        self.order = None   # Track pending orders.
        self.last_order_volume = 0
        self.entry_price = None  # To record the entry price.
        
        self.log("Strategy initialized.", color=YELLOW)

    def next(self):
        # If trade_on_live is enabled, skip processing if the current bar is too old.
        if self.p.trade_on_live:
            bar_time = self.datas[0].datetime.datetime(0)
            now = datetime.utcnow()
            lag = (now - bar_time).total_seconds()
            if lag > self.p.live_lag_seconds:
                self.log(f"Skipping bar. Bar time lag is {lag:.1f} seconds, exceeding threshold.", color=YELLOW)
                return

        # Build and log the dynamic status line.
        if not self.position:
            status = self.create_status_line(self.lower_band[0], self.data.close[0], self.upper_band[0], "waiting BUY")
        else:
            profit = self.data.close[0] - self.position.price
            profit_pct = (profit / self.position.price) * 100
            status = self.create_status_line(self.position.price, self.data.close[0], self.upper_band[0], "waiting SELL", profit, profit_pct)
        self.log(f"Status: {status}")

        # If an order is pending, skip processing.
        if self.order:
            self.log("Order pending, skipping this bar.", color=YELLOW)
            return
        
        cash = self.broker.getcash()
        # self.log(f"Available cash: {cash:.4f}")

        # Enforce minimum order value before attempting to buy.
        if not self.position and cash < self.p.min_order:
            self.log(f"Cash ({cash:.4f}) below minimum order threshold ({self.p.min_order}), skipping buy.", color=YELLOW)
            return

        # If not in a position, check for a buy signal.
        if not self.position:
            if self.data.close[0] < self.lower_band[0]:
                self.last_order_volume = (cash / self.data.close[0]) * 0.95
                self.log(f"Buy signal detected at price {self.data.close[0]:.4f}. Placing buy order for size: {self.last_order_volume:.4f}", color=GREEN)
                self.order = self.buy(size=self.last_order_volume)
        # If in a position, check for a sell signal.
        elif self.position.size > 0:
            if self.data.close[0] > self.upper_band[0]:
                self.log(f"Sell signal detected at price {self.data.close[0]:.4f}. Placing sell order for size: {self.last_order_volume:.4f}", color=RED)
                self.order = self.sell(size=self.last_order_volume)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = self.position.price
                self.log(f"BUY EXECUTED at {self.entry_price:.4f}", color=GREEN)
            elif order.issell():
                exit_price = self.data.close[0]
                profit = exit_price - self.entry_price
                profit_pct = (profit / self.entry_price) * 100
                self.log(f"SELL EXECUTED at {exit_price:.4f} | Profit: {profit:.4f} ({profit_pct:.2f}%)", color=RED)
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order {order.Status[order.status]}", color=YELLOW)
            self.order = None

if __name__ == '__main__':

    from scenario_XRPUSDT import create_cerebro_with_warmup

    cerebro = create_cerebro_with_warmup(    start_date = datetime(2025, 1, 1),
                                             end_date = datetime(2025, 3, 1),)
    
    cerebro.addstrategy(CustomBollingerStrategy,
                         log_enabled=True,
                         trade_on_live=False,
                         lower_dev=0.1,
                         upper_dev=1)
    
    cerebro.run()
    cerebro.plot()