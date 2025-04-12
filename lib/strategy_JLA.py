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
        self.


    def next(self):
        pass


if __name__ == "__main__":

    from scenario_XRPUSD_2024_march_June import return_trading_scenario
    cerebro = return_trading_scenario()
    cerebro.addstrategy(market_average,
                        avg_type='EMA',
                        sma_period=30,
                        buy_threshold=0.03,
                        sell_threshold=0.07,
                        min_order=100,
                        printlog=True)
    
    cerebro.broker.setcommission(commission=0.001)
    cerebro.run()
    cerebro.plot()