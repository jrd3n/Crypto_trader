import backtrader as bt
from datetime import datetime

"""
LaguerreRSIStrategy: A Trading Strategy Based on LaguerreRSI

Overview:
-----------
This strategy uses the LaguerreRSI indicator to generate trading signals. The LaguerreRSI is computed using 
a gamma parameter that determines the smoothing factor. Trading signals are generated as follows:
  - Buy Signal: When the LaguerreRSI falls below a specified threshold (rsi_threshold_buy), it suggests 
    that the asset may be oversold and a buy signal is triggered.
  - Sell Signal: When the LaguerreRSI rises above a specified threshold (rsi_threshold_sell), it suggests 
    that the asset may be overbought and a sell signal is triggered.

Order Management:
-----------
- Only one order is active at any given time.
- When buying, the strategy uses 100% of available cash (order size = cash / current close).
- When selling, it liquidates the entire position.

Optimization:
-----------
- The script supports grid search optimization over parameters: gamma, rsi_threshold_buy, and rsi_threshold_sell.
- Results are collected in dictionaries so that the best parameter combination can be selected by name.
- After optimization, the strategy is re-run with the best parameters to generate a performance plot.

Usage:
-----------
- Historical data is loaded from a CSV file.
- The final portfolio value is used to determine the best parameter set.
"""

class LaguerreRSIStrategy(bt.Strategy):
    params = (
        ('gamma', 0.5),               # Gamma parameter for LaguerreRSI
        ('rsi_threshold_buy', 0.1),   # Buy threshold: buy when LaguerreRSI is below this value
        ('rsi_threshold_sell', 0.7),  # Sell threshold: sell when LaguerreRSI is above this value
        ('printlog', False),          # Enable logging if True
    )
    
    def __init__(self):
        # Create the LaguerreRSI indicator on the close price.
        self.laguerre_rsi = bt.indicators.LaguerreRSI(self.data.close, gamma=self.p.gamma)
        self.order = None  # Track pending orders

    def next(self):
        if self.order:
            return
        
        # If not in a position, check for a buy signal.
        if not self.position:
            if self.laguerre_rsi[0] < self.p.rsi_threshold_buy:
                cash = self.broker.getcash()
                size = (cash / self.data.close[0]) * 0.95
                self.order = self.buy(size=size)
                if self.p.printlog:
                    self.log(f"BUY: Close {self.data.close[0]:.2f}, LaguerreRSI {self.laguerre_rsi[0]:.2f}")
        else:
            # If in a position, check for a sell signal.
            if self.laguerre_rsi[0] > self.p.rsi_threshold_sell:
                self.order = self.sell(size=self.position.size)
                if self.p.printlog:
                    self.log(f"SELL: Close {self.data.close[0]:.2f}, LaguerreRSI {self.laguerre_rsi[0]:.2f}")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

if __name__ == '__main__':
    # Get a Cerebro instance and configure it via your scenario helper.
    # For example, you might have a function return_trading_scenario() that sets up Cerebro with data, cash, and commission.
    # Here, we'll create a simple Cerebro instance manually for illustration.
    cerebro = bt.Cerebro(optreturn=False)
    
    # Optimization: grid search over gamma, rsi_threshold_buy, and rsi_threshold_sell.
    cerebro.optstrategy(
        LaguerreRSIStrategy,
        gamma=[0.4, 0.5, 0.6],
        rsi_threshold_buy=[0.1, 0.2, 0.3],
        rsi_threshold_sell=[0.6, 0.7, 0.8]
    )
    
    # Load historical data from CSV.
    data = bt.feeds.GenericCSVData(
        dataname='coin_history/XRPUSDT_data.csv',
        dtformat=('%Y-%m-%d %H:%M:%S'),
        datetime=0,  # Open time column index
        open=1,      # Open column index
        high=2,      # High column index
        low=3,       # Low column index
        close=4,     # Close column index
        volume=5,    # Volume column index
        openinterest=-1,
        fromdate=datetime(2024, 3, 19),
        todate=datetime(2024, 6, 1)
    )
    cerebro.adddata(data)
    
    cerebro.broker.set_cash(100.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # Run the optimization.
    opt_runs = cerebro.run()
    
    # Process the optimization results.
    results = []
    # Flatten the nested list of strategy instances.
    all_strategies = [strat for run in opt_runs for strat in run]
    for strat in all_strategies:
        p = strat.params
        final_value = strat.broker.getvalue()
        results.append({
            "gamma": p.gamma,
            "rsi_threshold_buy": p.rsi_threshold_buy,
            "rsi_threshold_sell": p.rsi_threshold_sell,
            "final_value": final_value
        })
    
    # Identify the best parameter combination.
    best = max(results, key=lambda r: r["final_value"])
    print("\nBest parameters:")
    print(f"  Gamma: {best['gamma']}")
    print(f"  RSI Threshold Buy: {best['rsi_threshold_buy']}")
    print(f"  RSI Threshold Sell: {best['rsi_threshold_sell']}")
    print(f"  Final Portfolio Value: {best['final_value']:.5f}")
    
    # Re-run the strategy with the best parameters for plotting.
    cerebro2 = bt.Cerebro()
    cerebro2.addstrategy(LaguerreRSIStrategy,
                         gamma=best["gamma"],
                         rsi_threshold_buy=best["rsi_threshold_buy"],
                         rsi_threshold_sell=best["rsi_threshold_sell"],
                         printlog=False)
    
    cerebro2.adddata(data)
    cerebro2.broker.set_cash(100.0)
    cerebro2.broker.setcommission(commission=0.001)
    
    cerebro2.run()
    cerebro2.plot()
