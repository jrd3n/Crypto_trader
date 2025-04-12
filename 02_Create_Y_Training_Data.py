#!/usr/bin/env python3
import backtrader as bt
import pandas as pd
from datetime import datetime
from tqdm import tqdm  # <-- For progress bar

class SMARecordingStrategy(bt.Strategy):
    params = dict(
        sma_period=14,
        output_csv="training_data/sma_data.csv"
    )

    def start(self):
        """Called once at the beginning of the backtest."""
        # We'll set up a tqdm progress bar using the total number of bars
        self.total_bars = len(self.data)
        self.bar_counter = 0
        self.pbar = tqdm(total=self.total_bars, desc="Processing bars")

    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.sma_period)
        self.output = []

    def next(self):
        dt = self.data.datetime.datetime(0)
        self.output.append({
            'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'close': self.data.close[0],
            'sma_current': self.sma[0],
        })

        # Update the progress bar
        self.bar_counter += 1
        self.pbar.update(1)

    def stop(self):
        # Close the progress bar
        self.pbar.close()

        # Convert recorded data to a DataFrame and save
        df = pd.DataFrame(self.output)
        df.to_csv(self.p.output_csv, index=False)
        print(f"SMA data saved to {self.p.output_csv}")

if __name__ == "__main__":

    from lib.scenario_XRPUSDT import create_cerebro_with_warmup

    # 1) Run the backtest to record the current SMA

    cerebro = create_cerebro_with_warmup()

    cerebro.addstrategy(SMARecordingStrategy, sma_period=100)

    cerebro.run()

    # 2) Now shift the column for future SMA
    
    lookahead_bars = 5

    df = pd.read_csv("training_data/sma_data.csv", parse_dates=['datetime'])
    df['sma_future'] = df['sma_current'].shift(-lookahead_bars)
    df['sma_diff_percent'] = ((df['sma_future'] - df['sma_current']) / df['sma_current']) * 100
    df.to_csv("training_data/y_data.csv", index=False)
    print("Updated CSV with future SMA saved as training_data/y_data.csv")
