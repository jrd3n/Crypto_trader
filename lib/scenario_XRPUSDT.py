import os
import glob
import pandas as pd
import backtrader as bt
from datetime import datetime, timedelta

def create_cerebro_with_warmup(
    folder: str = "downloaded_coin_data/XRPUSDT_1m",
    start_date: datetime = datetime(2023, 12, 1),
    end_date: datetime = datetime(2025, 3, 1),
    warmup_bars: int = 0,
    initial_cash: float = 100.0,
    commission_rate: float = 0.001
) -> bt.Cerebro:
    """
    Reads all monthly CSVs from `folder`, concatenates them into a single DataFrame,
    and slices the data so that we have `warmup_bars` before `start_date`, and extends up to `end_date` if provided.
    Returns a Backtrader 'cerebro' object loaded with this data slice.
    
    :param folder: Folder containing monthly CSV files
    :param start_date: The main start date for your backtest
    :param end_date: Optional end date for your backtest (None = up to last data)
    :param warmup_bars: Number of bars to include before 'start_date' as warmup
    :param initial_cash: How much cash the broker starts with
    :param commission_rate: Broker commission rate
    :return: A Backtrader 'cerebro' object ready for backtesting
    """
    # 1) Gather CSV files
    csv_files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if not csv_files:
        raise ValueError(f"No CSV files found in folder: {folder}")

    # 2) Read and combine into a single DataFrame
    dfs = []
    for file in csv_files:
        df = pd.read_csv(file, index_col=0, parse_dates=True)
        # Rename columns to match Backtrader's default naming (if needed)
        df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }, inplace=True)
        dfs.append(df)

    data = pd.concat(dfs)
    data.sort_index(inplace=True)

    # 3) Locate start_date in the index
    #    We'll go warmup_bars prior to that index (or 0 if not enough)
    if start_date not in data.index:
        start_loc = data.index.searchsorted(start_date)
    else:
        start_loc = data.index.get_loc(start_date)
    warmup_start_loc = max(0, start_loc - warmup_bars)

    # 4) Slice the DataFrame to include [warmup_start_loc : end_date]
    if end_date is not None:
        end_loc = data.index.searchsorted(end_date, side='right')
        data_sliced = data.iloc[warmup_start_loc:end_loc].copy()
    else:
        data_sliced = data.iloc[warmup_start_loc:].copy()

    # 5) Create a PandasData feed
    bt_feed = bt.feeds.PandasData(
        dataname=data_sliced,
        fromdate=start_date,
        todate=end_date
    )

    # 6) Set up the 'cerebro'
    cerebro = bt.Cerebro()
    cerebro.adddata(bt_feed)

    # Set cash and commission
    cerebro.broker.set_cash(initial_cash)
    cerebro.broker.setcommission(commission=commission_rate)

    return cerebro
