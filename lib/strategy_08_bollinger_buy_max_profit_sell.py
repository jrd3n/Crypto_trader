#!/usr/bin/env python3
import backtrader as bt
import logging
from datetime import datetime

# Configure logging globally.
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# ANSI color codes for convenience.
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
RESET = '\033[0m'


class BollingerTrailingStopStrategy(bt.Strategy):
    """
    Buys when price < lower Bollinger band, then holds until the price 
    drops `trail_percent` below the highest close since entry.
    """
    params = (
        # Bollinger parameters
        ('period', 20),           # period for SMA and StdDev
        ('dev_factor', 2.0),      # standard dev multiplier for Bollinger
        # Trailing Stop param
        ('trail_percent', 0.1),   # 10% drop from the maximum price since entry triggers a sell
        # Logging toggle
        ('log_enabled', True),
    )

    def log(self, txt, dt=None, color=None):
        """Helper method for logging with optional color."""
        if not self.p.log_enabled:
            return
        if dt is None:
            dt = self.datas[0].datetime.datetime(0)
        if color:
            txt = f"{color}{txt}{RESET}"
        logging.info(f"{dt.isoformat()} {txt}")

    def __init__(self):
        """
        Setup indicators and placeholders for tracking the max price while in a position.
        """
        # Bollinger: middle = SMA, top = SMA + dev_factor*std, bot = SMA - dev_factor*std
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.period)
        self.std = bt.indicators.StandardDeviation(self.data.close, period=self.p.period)
        self.upper_band = self.sma + self.std * self.p.dev_factor
        self.lower_band = self.sma - self.std * self.p.dev_factor

        self.order = None
        self.entry_price = None
        self.max_price_since_entry = None  # track highest close since position entry

        self.log("Strategy initialized.", color=YELLOW)

    def next(self):
        """Main logic each bar."""
        # If we already have a pending order, skip
        if self.order:
            return

        # If not in position, check for buy
        if not self.position:
            if self.data.close[0] < self.lower_band[0]:
                # Price below the lower band => buy signal
                self.order = self.buy()
                self.log(f"BUY SIGNAL at {self.data.close[0]:.4f}, band={self.lower_band[0]:.4f}", color=GREEN)
        else:
            # If in position, update the max price if needed
            current_close = self.data.close[0]
            if self.max_price_since_entry is None:
                self.max_price_since_entry = current_close
            else:
                self.max_price_since_entry = max(self.max_price_since_entry, current_close)

            # Check trailing stop condition:
            # If price < max_price_since_entry * (1 - trail_percent), exit
            trail_stop_price = self.max_price_since_entry * (1 - self.p.trail_percent)
            if current_close <= trail_stop_price:
                self.log(f"TRAIL STOP triggered. current={current_close:.4f} < {trail_stop_price:.4f}", color=RED)
                self.order = self.sell()

    def notify_order(self, order):
        """Handle order completion/cancellation."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.max_price_since_entry = self.entry_price
                self.log(f"BUY EXECUTED @ {self.entry_price:.4f}", color=GREEN)
            elif order.issell():
                exit_price = order.executed.price
                profit = exit_price - (self.entry_price or 0)
                profit_pct = 0
                if self.entry_price:
                    profit_pct = (profit / self.entry_price) * 100
                self.log(f"SELL EXECUTED @ {exit_price:.4f} | Profit: {profit:.4f} ({profit_pct:.2f}%)", color=RED)

            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order {order.Status[order.status]}", color=YELLOW)
            self.order = None

    def notify_trade(self, trade):
        """Optional: log final trade results."""
        if trade.isclosed:
            self.log(
                f"TRADE PROFIT: Gross {trade.pnl:.2f}, Net {trade.pnlcomm:.2f}",
                color=(GREEN if trade.pnlcomm > 0 else RED)
            )


# -------------------------
# Example: Setting up Cerebro
# -------------------------
if __name__ == '__main__':
    import backtrader as bt
    from scenario_XRPUSDT import create_cerebro_with_warmup

    # Create a Cerebro instance using your helper
    cerebro = create_cerebro_with_warmup(
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 3, 1)
    )

    # Add the BollingerTrailingStopStrategy
    cerebro.addstrategy(
        BollingerTrailingStopStrategy,
        period=30,
        dev_factor=0.025,
        trail_percent=0.03,
        log_enabled=True
    )

    cerebro.broker.setcash(1000.0)
    cerebro.run()
    cerebro.plot()
