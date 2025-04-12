#!/usr/bin/env python3

from datetime import datetime
from lib.scenario_XRPUSDT import create_cerebro_with_warmup
from lib.strategy_08_bollinger_buy_max_profit_sell import BollingerTrailingStopStrategy

# Define backtest window
start_date = datetime(2025, 1, 1)
end_date   = datetime(2025, 3, 1)

# 1) Create Cerebro for Optimization
cerebro_opt = create_cerebro_with_warmup(
    start_date=start_date,
    end_date=end_date
)

# Provide parameter grids for optstrategy
cerebro_opt.optstrategy(
    BollingerTrailingStopStrategy,
    period=[20, 30, 50],     # Bollinger period
    dev_factor=[0.1, 0.5, 1.5, 2.0, 2.5, 3],  # standard deviation multipliers
    trail_percent=[0.015, 0.05, 0.3 ],
    log_enabled=[False]          # Turn off logs for speed
)

# Run all combinations with optreturn=False so we get real Strategy objects
optimized_runs = cerebro_opt.run(
    optreturn=False,
    preload=True,  # pre-load data
    runonce=True   # batch indicator calculation
)

# 2) Find the best run by final portfolio value
best_portfolio_value = float('-inf')
best_params = None

for run in optimized_runs:
    # Each "run" is typically a list with one strategy instance
    strat_instance = run[0]
    final_value = strat_instance.broker.getvalue()
    if final_value > best_portfolio_value:
        best_portfolio_value = final_value
        p = strat_instance.params
        # Store the best parameters
        best_params = {
            'period': p.period,
            'dev_factor': p.dev_factor,
            'trail_percent': p.trail_percent,
            # We'll enable logging on the final run
            'log_enabled': True
        }

# 3) Final Run with Best Params + Logging
cerebro_final = create_cerebro_with_warmup(
    start_date=start_date,
    end_date=end_date
)

cerebro_final.addstrategy(BollingerTrailingStopStrategy, **best_params)

print("\nRunning final backtest with best parameters and full logging...\n")
result = cerebro_final.run()

print(f"\nOptimization complete. Number of combos tested: {len(optimized_runs)}")
print(f"Best Final Portfolio Value: {best_portfolio_value:.2f}")
print(f"Best Params: {best_params}")

# Optional: plot final
cerebro_final.plot()
