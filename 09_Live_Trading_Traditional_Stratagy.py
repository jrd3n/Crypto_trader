import backtrader as bt
import datetime as dt
from backtrader_binance import BinanceStore
from datetime import datetime

from ConfigBinance.Config import Config  # Configuration file

from lib.strategy_03_CustomBollinger import CustomBollingerStrategy
from lib.strategy_02_market_average_with_stop_loss import market_average_with_stop_loss
from lib.strategy_06_bollinger_with_stop_loss import CustomBollingerStrategySL

if __name__ == '__main__':

    cerebro = bt.Cerebro(quicknotify=True)

    coin_target = 'USDT'  # the base ticker in which calculations will be performed
    symbol = 'XRP' + coin_target  # the ticker by which we will receive data in the format <CodeTickerBaseTicker>

    store = BinanceStore(
        api_key=Config.BINANCE_API_KEY,
        api_secret=Config.BINANCE_API_SECRET,
        coin_target=coin_target,
        testnet=False)  # Binance Storage

    # live connection to Binance - for Offline comment these two lines
    broker = store.getbroker()
    cerebro.setbroker(broker)

    # Historical 1-minute bars for the last hour + new live bars / timeframe M1
    from_date = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=600)
    data = store.getdata(timeframe=bt.TimeFrame.Minutes, compression=1, dataname=symbol, start_date=from_date, LiveBars=True)

    cerebro.adddata(data)  # Adding data

    cerebro.addstrategy(market_average_with_stop_loss)  # Adding a trading system

    cerebro.run()  # Launching a trading system
    cerebro.plot()  # Draw a chart