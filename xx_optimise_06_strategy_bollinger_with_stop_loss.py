#!/usr/bin/env python3
from datetime import datetime
from lib.scenario_XRPUSDT import create_cerebro_with_warmup
from lib.strategy_06_bollinger_with_stop_loss import CustomBollingerStrategySL  # Update the import path as needed

# Specify your backtest date range
start_date = datetime(2024, 12, 1)
end_date   = datetime(2025, 1, 31)

# -------------------------
# 1) Optimization Backtest
# -------------------------
# Create Cerebro with warmup for the optimization window.
cerebro_opt = create_cerebro_with_warmup(
    start_date=start_date,
    end_date=end_date
)

# For each parameter, provide a list or range. We'll test all combinations.
cerebro_opt.optstrategy(
    CustomBollingerStrategySL,
    # Tweak these parameter grids as you like
    period=[30, 600],
    lower_dev=[0.2, 0.3],
    upper_dev=[0.03, 0.2],
    stop_loss=[0.07, 0.1],
    trade_on_live=[False],     # Keep consistent with your usage
    live_lag_seconds=[65],
    min_order=[10.0],          # If you also want to vary min_order, pass a list
    log_enabled=[False]        # Turn logging off during optimization for speed
)

# Run the optimization. With `optreturn=False`, each run returns a Strategy instance.
optimized_runs = cerebro_opt.run(
    optreturn=False,
    preload=True,  # preload data into memory
    runonce=True   # calculate indicators in a single pass
)

# -------------------------
# 2) Find the Best Parameters
# -------------------------
best_portfolio_value = float('-inf')
best_params = None

for run in optimized_runs:
    # Each run is typically a list with one strategy instance
    strat_instance = run[0]

    final_value = strat_instance.broker.getvalue()
    if final_value > best_portfolio_value:
        best_portfolio_value = final_value
        p = strat_instance.params
        best_params = {
            'period': p.period,
            'lower_dev': p.lower_dev,
            'upper_dev': p.upper_dev,
            'stop_loss': p.stop_loss,
            'trade_on_live': p.trade_on_live,
            'live_lag_seconds': p.live_lag_seconds,
            'min_order': p.min_order,
            # We'll turn logging on manually for the final run
            'log_enabled': True
        }

# -------------------------
# 3) Final Run with Best Params + Logging
# -------------------------
cerebro_final = create_cerebro_with_warmup(
    start_date=start_date,
    end_date=end_date
)

cerebro_final.addstrategy(CustomBollingerStrategySL, **best_params)

print("\nRunning final backtest with best parameters and logging enabled...\n")
results = cerebro_final.run()

print(f"\nOptimization complete. Number of combinations tested: {len(optimized_runs)}")
print(f"Best Final Portfolio Value: {best_portfolio_value:.2f}")
print(f"Best Parameters: {best_params}")

# Optionally, plot the final results
cerebro_final.plot()