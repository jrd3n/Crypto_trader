import backtrader as bt
import pandas as pd
import tensorflow as tf
import numpy as np
from datetime import datetime

# Optional ANSI colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
RESET = '\033[0m'

class AIThresholdStrategy(bt.Strategy):
    params = (
        ('model_path', 'trained_model.h5'),  # Path to your saved model
        ('buy_threshold', -0.3),
        ('sell_threshold', 0.7),
        ('printlog', True),  # Turn logging on/off
    )
    def log(self, txt, color=None):
        """Custom logger function. Prints datetime plus custom text."""
        if self.p.printlog:
            dt_str = self.datas[0].datetime.datetime(0).strftime('%Y-%m-%d %H:%M:%S')
            if color:
                txt = f"{color}{txt}{RESET}"
            print(f"{dt_str} - {txt}")


    def create_status_line(
        self, low_val, ai_pred, high_val, state,
        profit=None, profit_pct=None, width=30
    ):
        """
        Build a status line that aligns fields in fixed-width columns.

        For example:
        - "Waiting BUY :   0.3055 |------{  0.3020}-----|   0.3100 |"
        - "Waiting SELL:   0.3055 |------{  0.3362}-----|   0.3400 | P/L:   0.0307 ( 10.04%)"
        
        Arguments:
        low_val   -> The lower bound (e.g., your 'buy' threshold or minimum)
        ai_pred   -> The AI prediction (somewhere between low_val & high_val)
        high_val  -> The upper bound (e.g., your 'sell' threshold or maximum)
        state     -> "waiting BUY" or "waiting SELL" for your logging context
        profit    -> Optional float for how much profit in absolute terms
        profit_pct-> Optional float for the percentage profit
        width     -> The total width of the bar section
        """
        # Guard against divide-by-zero if low_val == high_val
        if high_val == low_val:
            pos = width // 2
        else:
            ratio = (ai_pred - low_val) / (high_val - low_val)
            # clamp ratio to [0,1]
            ratio = max(0, min(1, ratio))
            pos = int(ratio * width)

        # Build the bar: place the AI prediction in braces at the correct spot
        left_side = "-" * pos
        right_side = "-" * (width - pos)
        bar = f"{left_side}{{{ai_pred:8.4f}}}{right_side}"

        if state == "waiting BUY":
            return f"Waiting BUY : {low_val:8.4f} |{bar}| {high_val:8.4f} |"
        else:
            # For SELL, optionally show P/L info
            return (
                f"Waiting SELL: {low_val:8.4f} |{bar}| {high_val:8.4f} "
                f"| P/L: {profit:8.4f} ({profit_pct:6.2f}%)"
            )

    def __init__(self):
        """Load a pre-trained model and define any indicators."""
        self.model = tf.keras.models.load_model(self.p.model_path)
        self.order = None
        
        # Attach all the indicators you need for your "x data"
        self.rsi_5   = bt.indicators.RSI(self.data.close, period=5)
        self.rsi_30  = bt.indicators.RSI(self.data.close, period=30)
        self.rsi_200 = bt.indicators.RSI(self.data.close, period=200)
        
        self.bb_5   = bt.indicators.BollingerBands(self.data, period=5)
        self.bb_30  = bt.indicators.BollingerBands(self.data, period=30)
        self.bb_200 = bt.indicators.BollingerBands(self.data, period=200)

        self.aroon_up_5   = bt.indicators.AroonUp(self.data, period=5)
        self.aroon_down_5 = bt.indicators.AroonDown(self.data, period=5)
        self.aroon_up_30   = bt.indicators.AroonUp(self.data, period=30)
        self.aroon_down_30 = bt.indicators.AroonDown(self.data, period=30)
        self.aroon_up_200   = bt.indicators.AroonUp(self.data, period=200)
        self.aroon_down_200 = bt.indicators.AroonDown(self.data, period=200)

        # AwesomeOscillator with different "fast"/"slow" combos
        self.ao_5   = bt.indicators.AwesomeOscillator(self.data, fast=3, slow=5)
        self.ao_30  = bt.indicators.AwesomeOscillator(self.data, fast=10, slow=30)
        self.ao_200 = bt.indicators.AwesomeOscillator(self.data, fast=50, slow=200)

        # Ichimoku
        self.ichimoku   = bt.indicators.Ichimoku(self.data)

        self.tema_5   = bt.indicators.TripleExponentialMovingAverage(self.data.close, period=5)
        self.tema_30  = bt.indicators.TripleExponentialMovingAverage(self.data.close, period=30)
        self.tema_200 = bt.indicators.TripleExponentialMovingAverage(self.data.close, period=200)
        
        self.macd_5   = bt.indicators.MACD(self.data.close, period_me1=4, period_me2=8, period_signal=3)
        self.macd_30  = bt.indicators.MACD(self.data.close, period_me1=12, period_me2=30, period_signal=9)
        self.macd_200 = bt.indicators.MACD(self.data.close, period_me1=50, period_me2=200, period_signal=20)

        self.atr_5   = bt.indicators.ATR(self.data, period=5)
        self.atr_30  = bt.indicators.ATR(self.data, period=30)
        self.atr_200 = bt.indicators.ATR(self.data, period=200)

    def next(self):
        """Runs on every bar - gather features and pass them to the model."""
        
        # Gather features in the same order they were used to train the model:
        feature_list = [
            # Basic OHLCV
            self.data.open[0],
            self.data.high[0],
            self.data.low[0],
            self.data.close[0],
            self.data.volume[0],
            
            # RSI (3 periods)
            self.rsi_5[0],
            self.rsi_30[0],
            self.rsi_200[0],

            # Bollinger top/mid/bot (3 periods)
            self.bb_5.top[0],   self.bb_5.mid[0],   self.bb_5.bot[0],
            self.bb_30.top[0],  self.bb_30.mid[0],  self.bb_30.bot[0],
            self.bb_200.top[0], self.bb_200.mid[0], self.bb_200.bot[0],

            # Aroon
            self.aroon_up_5[0],   self.aroon_down_5[0],
            self.aroon_up_30[0],  self.aroon_down_30[0],
            self.aroon_up_200[0], self.aroon_down_200[0],

            # Awesome
            self.ao_5[0],
            self.ao_30[0],
            self.ao_200[0],

            # Ichimoku
            getattr(self.ichimoku, 'tenkan_sen', [None])[0],
            getattr(self.ichimoku, 'kijun_sen', [None])[0],

            # TEMA
            self.tema_5[0],
            self.tema_30[0],
            self.tema_200[0],

            # MACD sets
            self.macd_5.macd[0],        self.macd_5.signal[0],
            self.macd_30.macd[0],       self.macd_30.signal[0],
            self.macd_200.macd[0],      self.macd_200.signal[0],

            # ATR
            self.atr_5[0],
            self.atr_30[0],
            self.atr_200[0],
        ]

        # Convert to a (1, num_features) array of float32
        features = np.array([feature_list], dtype=np.float32)

             # Predict with your loaded model
        prediction = self.model.predict(features, verbose=0)[0][0]

        # Build a status line showing "prediction" between buy_threshold and sell_threshold
        if not self.position:
            status_msg = self.create_status_line(
                self.p.sell_threshold,   # low_val
                prediction,             # ai_pred
                self.p.buy_threshold,  # high_val
                state="waiting BUY"
            )
            self.log(status_msg)
        else:
            # If you'd like to show profit, pass actual values. For now we skip:
            status_msg = self.create_status_line(
                self.p.sell_threshold,   # low_val
                prediction,             # ai_pred
                self.p.buy_threshold,  # high_val
                state="waiting SELL",
                profit=0.0,
                profit_pct=0.0
            )
            self.log(status_msg)

        # Trading logic
        if not self.position:
            if prediction > self.p.buy_threshold:
                self.order = self.buy()
                self.log("BUY ORDER SENT", color=GREEN)
        else:
            if prediction < self.p.sell_threshold:
                self.order = self.sell()
                self.log("SELL ORDER SENT", color=RED)

    def notify_order(self, order):
        """Called whenever there's an order status update."""
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None

# -------------------------
# Setting up Cerebro
# -------------------------
if __name__ == '__main__':

    from lib.scenario_XRPUSDT import create_cerebro_with_warmup
    
    # Use your existing method to load data
    cerebro = create_cerebro_with_warmup(
        start_date=datetime(2025, 2, 14),
        end_date=datetime(2025, 2, 15),
    )
    
    # Add the strategy with thresholds
    cerebro.addstrategy(
        AIThresholdStrategy,
        model_path='trained_model.h5',
        buy_threshold=0.45,
        sell_threshold=-0.45
    )

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.plot()
