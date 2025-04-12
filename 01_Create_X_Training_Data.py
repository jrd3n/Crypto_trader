#!/usr/bin/env python3
import os
import pandas as pd
import backtrader as bt
from datetime import datetime
from tqdm import tqdm
from lib.scenario_XRPUSDT import create_cerebro_with_warmup

# ANSI color codes for convenience
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
RESET = '\033[0m'

class IndicatorRecordingStrategy(bt.Strategy):
    params = dict(
        printlog=True,
    )
    
    def __init__(self):
        """
        Attach each indicator with 3 separate periods: 5, 30, and 200.
        Some indicators (like MACD, Ichimoku, AwesomeOscillator) have multiple period parameters –
        we show one possible approach, but tweak as needed for your logic.
        """
        # -------------------------
        # RSI with 3 periods
        # -------------------------
        self.rsi_5   = bt.indicators.RSI(self.data.close, period=5)
        self.rsi_30  = bt.indicators.RSI(self.data.close, period=30)
        self.rsi_200 = bt.indicators.RSI(self.data.close, period=200)
        
        # -------------------------
        # Bollinger Bands with 3 periods
        # -------------------------
        self.bb_5   = bt.indicators.BollingerBands(self.data, period=5)
        self.bb_30  = bt.indicators.BollingerBands(self.data, period=30)
        self.bb_200 = bt.indicators.BollingerBands(self.data, period=200)
        
        # -------------------------
        # Aroon Up/Down with 3 periods
        # -------------------------
        self.aroon_up_5   = bt.indicators.AroonUp(self.data, period=5)
        self.aroon_down_5 = bt.indicators.AroonDown(self.data, period=5)
        
        self.aroon_up_30   = bt.indicators.AroonUp(self.data, period=30)
        self.aroon_down_30 = bt.indicators.AroonDown(self.data, period=30)
        
        self.aroon_up_200   = bt.indicators.AroonUp(self.data, period=200)
        self.aroon_down_200 = bt.indicators.AroonDown(self.data, period=200)
        
        # -------------------------
        # AwesomeOscillator (fast/slow)
        # We'll treat "5,30,200" as pairs of (fast, slow) in some pattern
        # This is arbitrary – adjust as needed.
        # -------------------------
        self.ao_5   = bt.indicators.AwesomeOscillator(self.data, fast=3, slow=5)   # "5" version
        self.ao_30  = bt.indicators.AwesomeOscillator(self.data, fast=10, slow=30) # "30" version
        self.ao_200 = bt.indicators.AwesomeOscillator(self.data, fast=50, slow=200)# "200" version
        
        # -------------------------
        # Ichimoku – Typically uses (9,26,52).
        # We'll just replicate "5" => (5,5,5), "30" => (30,30,30), "200" => (200,200,200)
        # -------------------------
        self.ichimoku   = bt.indicators.Ichimoku(self.data)
        
        # -------------------------
        # Triple Exponential MA (TEMA) with 3 periods
        # -------------------------
        self.tema_5   = bt.indicators.TripleExponentialMovingAverage(self.data.close, period=5)
        self.tema_30  = bt.indicators.TripleExponentialMovingAverage(self.data.close, period=30)
        self.tema_200 = bt.indicators.TripleExponentialMovingAverage(self.data.close, period=200)
        
        # -------------------------
        # MACD – typically has (fast, slow, signal). We'll scale them for 5/30/200, e.g.:
        #   - "5" => (fast=4, slow=8, signal=3)
        #   - "30" => (fast=12, slow=30, signal=9)
        #   - "200" => (fast=50, slow=200, signal=20)
        # Adjust as needed.
        # -------------------------
        self.macd_5 = bt.indicators.MACD(self.data.close, period_me1=4, period_me2=8, period_signal=3)
        self.macd_30 = bt.indicators.MACD(self.data.close, period_me1=12, period_me2=30, period_signal=9)
        self.macd_200 = bt.indicators.MACD(self.data.close, period_me1=50, period_me2=200, period_signal=20)

        # -------------------------
        # ATR with 3 periods
        # -------------------------
        self.atr_5   = bt.indicators.ATR(self.data, period=5)
        self.atr_30  = bt.indicators.ATR(self.data, period=30)
        self.atr_200 = bt.indicators.ATR(self.data, period=200)

        # Prepare a list to store rows of output
        self.output = []
    
    def printout(self, txt, color=None):
        """Simple print wrapper that adds color if enabled."""
        if self.p.printlog:
            now = self.datas[0].datetime.datetime(0) if len(self.datas[0]) > 0 else datetime.now()
            if color:
                txt = f"{color}{txt}{RESET}"
            print(f"{now.isoformat()} {txt}")
    
    def start(self):
        """Called once at the beginning of the backtest."""
        # Setup tqdm progress bar using total number of bars.
        self.total_bars = len(self.data)
        self.bar_counter = 0
        self.pbar = tqdm(total=self.total_bars, desc="Processing bars")
    
    def next(self):
        """Called on each bar."""
        try:
            dt = self.data.datetime.datetime(0)
            row = {
                'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'open':   self.data.open[0],
                'high':   self.data.high[0],
                'low':    self.data.low[0],
                'close':  self.data.close[0],
                'volume': self.data.volume[0],

                # RSI
                'rsi_5':   self.rsi_5[0],
                'rsi_30':  self.rsi_30[0],
                'rsi_200': self.rsi_200[0],

                # Bollinger top/mid/bot with 3 periods
                'bb_5_top':   self.bb_5.top[0],
                'bb_5_mid':   self.bb_5.mid[0],
                'bb_5_bot':   self.bb_5.bot[0],
                'bb_30_top':  self.bb_30.top[0],
                'bb_30_mid':  self.bb_30.mid[0],
                'bb_30_bot':  self.bb_30.bot[0],
                'bb_200_top': self.bb_200.top[0],
                'bb_200_mid': self.bb_200.mid[0],
                'bb_200_bot': self.bb_200.bot[0],

                # Aroon
                'aroon_up_5':   self.aroon_up_5[0],
                'aroon_down_5': self.aroon_down_5[0],
                'aroon_up_30':   self.aroon_up_30[0],
                'aroon_down_30': self.aroon_down_30[0],
                'aroon_up_200':   self.aroon_up_200[0],
                'aroon_down_200': self.aroon_down_200[0],

                # AwesomeOscillator
                'ao_5':   self.ao_5[0],
                'ao_30':  self.ao_30[0],
                'ao_200': self.ao_200[0],

                # Ichimoku (tenkan_sen, kijun_sen, etc.)
                'ichimoku_tenkan':  getattr(self.ichimoku,  'tenkan_sen', [None])[0],
                'ichimoku_kijun':   getattr(self.ichimoku,  'kijun_sen',  [None])[0],

                # TripleEMA
                'tema_5':   self.tema_5[0],
                'tema_30':  self.tema_30[0],
                'tema_200': self.tema_200[0],

                # MACD
                'macd_5':         self.macd_5.macd[0],
                'macd_5_signal':  self.macd_5.signal[0],
                'macd_30':        self.macd_30.macd[0],
                'macd_30_signal': self.macd_30.signal[0],
                'macd_200':       self.macd_200.macd[0],
                'macd_200_signal':self.macd_200.signal[0],

                # ATR
                'atr_5':   self.atr_5[0],
                'atr_30':  self.atr_30[0],
                'atr_200': self.atr_200[0],
            }
            self.output.append(row)
        except Exception as e:
            dt = self.data.datetime.datetime(0)
            print(f"Error on {dt.strftime('%Y-%m-%d %H:%M:%S')}: {e}")
    
        # Update the progress bar
        self.bar_counter += 1
        self.pbar.update(1)
    
    def stop(self):
        """Called once at the end of the backtest."""
        # Close the progress bar
        self.pbar.close()
    
        # Convert the collected data into a DataFrame and save to CSV
        df_output = pd.DataFrame(self.output)
        output_folder = "training_data"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        output_file = os.path.join(output_folder, "x_data.csv")
        df_output.to_csv(output_file, index=False)
        print(f"X training data saved to {output_file}")


if __name__ == '__main__':
    # Obtain cerebro from your helper function.
    cerebro = create_cerebro_with_warmup()

    # Add the IndicatorRecordingStrategy.
    cerebro.addstrategy(IndicatorRecordingStrategy)

    print("Running the strategy for X training data...")
    cerebro.run()
