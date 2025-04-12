#!/usr/bin/env python3
from datetime import datetime
from lib.scenario_XRPUSDT import create_cerebro_with_warmup
from lib.strategy_09_boll_buy_SL_deadband_trailing_stop import BollingerDeadbandStopTrail  # Adjust filename as needed

# Define backtest period
start_date = datetime(2025, 1, 1)
end_date   = datetime(2025, 3, 1)

# -------------------------
# 1) Optimization Backtest
# -------------------------
# Create Cerebro for Optimization
cerebro_opt = create_cerebro_with_warmup(
    start_date=start_date,
    end_date=end_date
)

# Set up the optimization grid for our strategy:
cerebro_opt.optstrategy(
    BollingerDeadbandStopTrail,
    period=[25],               # Bollinger period
    dev_factor=[3.7, 3.6, 3.5, 3.4, 3.2, 3.0],             # Bollinger standard deviation multiplier
    deadband=[0.0035],       # Deadband percentage (e.g., 0.005 = 0.5%)
    stop_loss=[0.044],        # Stop loss percentage (e.g., 0.05 = 5%)
    trailing_stop_percent=[0],   # Trailing stop percent (e.g., 0.1 = 10%)
    log_enabled=[False],               # Turn logging off during optimization for speed
    # trade_on_live=[False],
    # live_lag_seconds=[65],
    # min_order=[10.0]
)

# Set broker commission for optimization
cerebro_opt.broker.setcommission(commission=0.001)

# Run the optimization
optimized_runs = cerebro_opt.run(optreturn=False, preload=True, runonce=True)

# -------------------------
# 2) Find the Best Parameters
# -------------------------
best_portfolio_value = float('-inf')
best_params = None

for run in optimized_runs:
    # Each run is a list with one strategy instance
    strat_instance = run[0]
    final_value = strat_instance.broker.getvalue()
    if final_value > best_portfolio_value:
        best_portfolio_value = final_value
        p = strat_instance.params
        best_params = {
            'period': p.period,
            'dev_factor': p.dev_factor,
            'deadband': p.deadband,
            'stop_loss': p.stop_loss,
            'trailing_stop_percent': p.trailing_stop_percent,
            # 'trade_on_live': p.trade_on_live,
            # 'live_lag_seconds': p.live_lag_seconds,
            # 'min_order': p.min_order,
            # Enable logging for final run:
            'log_enabled': True
        }

print("\nOptimization complete.")

# -------------------------
# 3) Final Run with Best Params + Logging
# -------------------------
# Create a fresh Cerebro instance for the final run.
cerebro_final = create_cerebro_with_warmup(
    start_date=start_date,
    end_date=end_date
)

cerebro_final.addstrategy(BollingerDeadbandStopTrail, **best_params)
cerebro_final.broker.setcommission(commission=0.001)

print("\nRunning final backtest with best parameters and logging enabled...\n")
final_runs = cerebro_final.run()

print(f"Number of combinations tested: {len(optimized_runs)}")
print(f"Best Final Portfolio Value: {best_portfolio_value:.2f}")
print(f"Best Parameters: {best_params}")

cerebro_final.plot()


