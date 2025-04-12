import backtrader as bt
from datetime import datetime

# ANSI color codes for convenience.
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
RESET = '\033[0m'

class market_average(bt.Strategy):
    params = (
        ('avg_type', 'EMA'),       # Moving average type: 'SMA', 'EMA', or 'WMA'
        ('sma_period', 300),       # Period for the moving average indicator
        ('buy_threshold', 0.07),   # Buy when price is at least 7% below MA
        ('sell_threshold', 0.1),   # Sell when price is at least 10% above entry price
        ('printlog', True),        # Enable logging if True
        ('backtest', False),       # Backtest mode (skip live data checks)
        ('live_lag_seconds', 65),  # Maximum allowed lag (in seconds) for a bar to be considered live
        ('min_order', 10.0)        # Minimum cash required to place a buy order
    )

    def __init__(self):
        # Create the moving average indicator.
        avg_type = self.p.avg_type.upper()
        if avg_type == 'EMA':
            self.ma = bt.indicators.ExponentialMovingAverage(self.data.close, period=self.p.sma_period)
        elif avg_type == 'SMA':
            self.ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.sma_period)
        elif avg_type == 'WMA':
            self.ma = bt.indicators.WeightedMovingAverage(self.data.close, period=self.p.sma_period)
        else:
            raise ValueError(f"Unknown avg_type: {self.p.avg_type}")
        self.order = None

    def create_status_line(self, buy_val, current, sell_val, state, profit=None, profit_pct=None, width=40):
        """
        Create a status line that shows:
          • For waiting BUY:
               "waiting BUY: {buy_val:.4f} |----*-----| {current:.4f}"
          • For waiting SELL:
               "waiting SELL: Entry {buy_val:.4f} -> Target {sell_val:.4f} |----*-----| {current:.4f} | P/L: {profit:.4f} ({profit_pct:.2f}%)"
        The '*' marker moves based on the relative position of current between the lower and upper thresholds.
        """
        if state == "waiting BUY":
            low = buy_val
            high = current  # Use current as reference
        else:
            low = buy_val
            high = sell_val

        if high == low:
            pos = width // 2
        else:
            ratio = (current - low) / (high - low)
            ratio = max(0, min(1, ratio))
            pos = int(ratio * width)
        bar = "-" * pos + "*" + "-" * (width - pos)

        if state == "waiting BUY":
            return f"waiting BUY: {buy_val:.4f} |{bar}| {current:.4f}"
        else:
            return f"waiting SELL: Entry {buy_val:.4f} -> Target {sell_val:.4f} |{bar}| {current:.4f} | P/L: {profit:.4f} ({profit_pct:.2f}%)"

    def log(self, txt, dt=None, color=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            if color:
                txt = f"{color}{txt}{RESET}"
            print(f"{dt.isoformat()} {txt}")

    def next(self):
        # When not in a position, we're waiting to buy.
        if not self.position:
            # Calculate buy trigger (MA adjusted by buy_threshold).
            trigger = self.ma[0] * (1 - self.p.buy_threshold)
            status = self.create_status_line(trigger, self.data.close[0], self.ma[0], "waiting BUY")
            self.log(f"Status: {status}")
            cash = self.broker.getcash()
            if cash < self.p.min_order:
                self.log(f"Cash ({cash:.2f}) is below min_order ({self.p.min_order}). Skipping buy.", color=YELLOW)
                return
            size = (cash / self.data.close[0]) * 0.95
            if self.data.close[0] < trigger:
                self.log(f"BUY SIGNAL: Price {self.data.close[0]:.2f} below trigger {trigger:.2f}", color=GREEN)
                self.order = self.buy(size=size)
        else:
            # When in a position, we're waiting to sell.
            profit = self.data.close[0] - self.position.price
            profit_pct = (profit / self.position.price) * 100
            target = self.position.price * (1 + self.p.sell_threshold)
            status = self.create_status_line(self.position.price, self.data.close[0], target, "waiting SELL", profit, profit_pct)
            self.log(f"Status: {status}")
            if self.data.close[0] > target:
                self.log(f"SELL SIGNAL: Price {self.data.close[0]:.2f} above target {target:.2f}", color=RED)
                self.order = self.sell(size=self.position.size)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED at {self.position.price:.2f}", color=GREEN)
            elif order.issell():
                # Check to avoid division by zero
                if self.position.price == 0:
                    profit = 0.0
                    profit_pct = 0.0
                    self.log("SELL EXECUTED, but buy price is 0. Setting profit to 0.", color=RED)
                else:
                    profit = self.data.close[0] - self.position.price
                    profit_pct = (profit / self.position.price) * 100
                    self.log(f"SELL EXECUTED at {self.data.close[0]:.2f} | P/L: {profit:.2f} ({profit_pct:.2f}%)", color=RED)
            self.order = None

if __name__ == '__main__':

    from scenario_XRPUSDT import create_cerebro_with_warmup

    cerebro = create_cerebro_with_warmup()
    
    cerebro.addstrategy(market_average,
                        avg_type='EMA',
                        sma_period=30,
                        buy_threshold=0.07,
                        sell_threshold=0.1,
                        printlog=True,
                        backtest=True,
                        live_lag_seconds=65,
                        min_order=10.0)
    cerebro.run()
    cerebro.plot()
