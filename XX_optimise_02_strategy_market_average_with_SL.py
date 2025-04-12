#!/usr/bin/env python3

from datetime import datetime
from lib.scenario_XRPUSDT import create_cerebro_with_warmup
from lib.strategy_02_market_average_with_stop_loss import market_average_with_stop_loss

start_date=datetime(2024, 12, 1)
end_date=datetime(2025, 1, 31)

# -------------------------
# 1) Optimization Backtest
# -------------------------
# Create Cerebro with warmup for the optimization window.
cerebro_opt = create_cerebro_with_warmup(
    start_date=start_date,
    end_date=end_date
)

cerebro_opt.optstrategy(
    market_average_with_stop_loss,
    avg_type=['EMA'],
    sma_period=[10, 20, 30],  # 30, 130, 230, 330, 430, 530
    buy_threshold=[0.015, 0.025, 0.03],   # 0.0, 0.02, ..., 0.14
    sell_threshold=[0.03, 0.045],
    stop_loss=[0.045 , 0.05, 0.055],
    trade_on_live=[False],
    live_lag_seconds=[65],
    printlog=[False]
)

# Run the optimization, which returns a list of list of Strategy instances.
optimized_runs = cerebro_opt.run(optreturn=False, 
                                 preload=True,  # preload all data into memory before backtesting
                                 runonce=True,  # calculate all indicators in a tight loop once, rather than step by step
)

# -------------------------
# 2) Find the Best Parameters
# -------------------------
# We'll pick the run with the HIGHEST final portfolio value. You might also want 
# to consider other metrics (like Sharpe ratio, drawdown, etc.) if you have analyzers.

best_portfolio_value = float('-inf')
best_params = None

for run in optimized_runs:
    # Each 'run' is a list of strategies that share the same data feed
    # but differ by the parameter sets. Usually there's just one strategy per run element.
    strat_instance = run[0]
    
    # We can check final portfolio value
    final_value = strat_instance.broker.getvalue()
    
    if final_value > best_portfolio_value:
        best_portfolio_value = final_value
        # Extract the parameter values
        p = strat_instance.params
        best_params = {
            'avg_type': p.avg_type,
            'sma_period': p.sma_period,
            'buy_threshold': p.buy_threshold,
            'sell_threshold': p.sell_threshold,
            'stop_loss': p.stop_loss,
            'trade_on_live': p.trade_on_live,
            'live_lag_seconds': p.live_lag_seconds,
            # We'll turn logging on manually for the final run
            'printlog': True
        }

# -------------------------
# 3) Final Run with Best Params + Logging
# -------------------------
# Create a fresh Cerebro instance for the final run
cerebro_final = create_cerebro_with_warmup(
    start_date=start_date,
    end_date=end_date
)

# Add the strategy with the best parameters found
cerebro_final.addstrategy(market_average_with_stop_loss, **best_params)

print("\nRunning final backtest with best parameters and logging enabled...\n")
final_strats = cerebro_final.run()

print(f"\nOptimization complete. Number of combinations tested: {len(optimized_runs)}")
print(f"Best Final Portfolio Value: {best_portfolio_value:.2f}")
print(f"Best Parameters: {best_params}")

# Optionally, plot the final results
cerebro_final.plot()