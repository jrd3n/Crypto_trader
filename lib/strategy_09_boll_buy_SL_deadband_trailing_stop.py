#!/usr/bin/env python3
import backtrader as bt
import logging
from datetime import datetime

# Global logging config
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Optional ANSI colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
RESET = '\033[0m'


class BollingerDeadbandStopTrail(bt.Strategy):
    """
    1. Buys if close <= Bollinger lower band
    2. After entering, define:
       - Stop-loss floor = entry_price * (1 - stop_loss)
       - Deadband = [stop_loss_floor, entry_price * (1 + deadband)]
         => no action in this band
    3. If close <= stop_loss_floor => sell (stop loss).
    4. If close > entry_price*(1 + deadband), track max_price_since_entry and
       if close < max_price_since_entry*(1 - trailing_stop) => sell (take profit).
    """

    params = (
        ('period', 25),                # Bollinger period
        ('dev_factor', 1.6),           # Bollinger stddev multiplier
        ('deadband', 0),           # e.g. 0.5% => 0.005
        ('stop_loss', 0.07),           # e.g. 5% => 0.05
        ('trailing_stop_percent', 0.13),# e.g. 10% => 0.1
        ('log_enabled', True),
    )

    def log(self, txt, color=None):
        if not self.p.log_enabled:
            return
        dt_str = self.datas[0].datetime.datetime(0).strftime('%Y-%m-%d %H:%M:%S')
        if color:
            txt = f"{color}{txt}{RESET}"
        logging.info(f"{dt_str} {txt}")

    def __init__(self):
        # Compute Bollinger
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.period)
        self.std = bt.indicators.StandardDeviation(self.data.close, period=self.p.period)
        self.lower_band = self.sma - self.std * self.p.dev_factor
        self.upper_band = self.sma + self.std * self.p.dev_factor

        # Track orders and state
        self.order = None
        self.entry_price = None
        self.max_price_since_entry = None

        self.log("Strategy initialized.", color=YELLOW)

    def next(self):
        """Main logic each bar."""
        if self.order:
            # If an order is pending, do nothing
            return

        current_close = self.data.close[0]
        lb = self.lower_band[0]

        if not self.position:
            # --- BUY CONDITION ---
            # close <= lower_band => buy
            if current_close <= lb:
                self.order = self.buy(size=(self.broker.getcash() * 0.95 / self.data.close[0]))
                self.log(f"BUY Signal: close={current_close:.4f} <= lower_band={lb:.4f}", color=GREEN)
        else:
            # Already in position -> check exit conditions

                # Already in position -> check exit conditions
            if self.entry_price is None:
                # The buy order has not fully executed, skip logic
                return
            
            stop_loss_floor = self.entry_price * (1 - self.p.stop_loss)
            deadband_upper  = self.entry_price * (1 + self.p.deadband)
        
            # 1) STOP LOSS
            if current_close <= stop_loss_floor:
                self.log(f"STOP LOSS Triggered: close={current_close:.4f} <= {stop_loss_floor:.4f}", color=RED)
                self.order = self.close()

                return

            # 2) If price is within [stop_loss_floor, deadband_upper], do NOTHING
            if stop_loss_floor < current_close <= deadband_upper:
                self.log(f"In deadband zone: floor={stop_loss_floor:.4f}, deadband_upper={deadband_upper:.4f}, close={current_close:.4f}")
                return

            # 3) Above deadband => trailing stop logic
            if current_close > deadband_upper:
                # Update max price
                if self.max_price_since_entry is None:
                    self.max_price_since_entry = current_close
                else:
                    self.max_price_since_entry = max(self.max_price_since_entry, current_close)

                # If current falls below [max_price * (1 - trailing_stop)] => SELL
                trail_stop_level = self.max_price_since_entry * (1 - self.p.trailing_stop_percent)
                if current_close < trail_stop_level:
                    self.log(
                        f"TRAIL STOP triggered: close={current_close:.4f} < {trail_stop_level:.4f}",
                        color=RED
                    )
                    self.order = self.close()


    def notify_order(self, order):
        """Handle fill or cancel."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.max_price_since_entry = self.entry_price
                self.log(f"BUY EXECUTED @ {self.entry_price:.4f}", color=GREEN)
            elif order.issell():
                exit_price = order.executed.price
                profit = exit_price - (self.entry_price or 0)
                profit_pct = 0.0
                if self.entry_price:
                    profit_pct = (profit / self.entry_price) * 100
                self.log(f"SELL EXECUTED @ {exit_price:.4f} | Profit: {profit:.4f} ({profit_pct:.2f}%)", color=RED)
                # Reset state
                self.entry_price = None
                self.max_price_since_entry = None
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order {order.Status[order.status]}", color=YELLOW)
            self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(
                f"TRADE PROFIT: Gross={trade.pnl:.4f}, Net={trade.pnlcomm:.4f}",
                color=(GREEN if trade.pnlcomm > 0 else RED)
            )


# ---------------------------
# Example usage in Cerebro
# ---------------------------
if __name__ == '__main__':
    from scenario_XRPUSDT import create_cerebro_with_warmup

    cerebro = create_cerebro_with_warmup(
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 3, 1)
    )

    cerebro.addstrategy(
        BollingerDeadbandStopTrail,
        period=25,                # Bollinger period
        dev_factor=3.2,           # Bollinger dev multiplier
        deadband=0.05,           # e.g. 0.5% => 0.005
        stop_loss=0.015,           # 5% below entry => immediate sell
        trailing_stop_percent=0.00, # 0.13 is best so far
        log_enabled=True
    )

    cerebro.run()
    cerebro.plot()
