from binance.client import Client
import pandas as pd
import os
from ConfigBinance.Config import Config
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from tqdm import tqdm

# Initialize Binance client
client = Client(Config.BINANCE_API_KEY, Config.BINANCE_API_SECRET)

# User settings
coin_type = "XRPUSDT"  # Trading pair
history_years = 5      # Number of years to go back
interval = Client.KLINE_INTERVAL_1MINUTE  # Time interval

# Define date range
end_date = datetime.now(timezone.utc)
start_date = end_date - relativedelta(years=history_years)

# Define output folder: e.g. "downloaded_coin_data/XRPUSDT_1m"
folder_name = f"downloaded_coin_data/{coin_type}_{interval}"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)

# Build list of monthly date ranges
month_periods = []
current_date = start_date
while current_date < end_date:
    next_date = current_date + relativedelta(months=1)
    period_end = min(next_date, end_date)
    month_periods.append((current_date, period_end))
    current_date = next_date

# Loop over each month with a progress bar
for period_start, period_end in tqdm(month_periods, desc="Downloading monthly data"):
    # File name in format "YYYY_MM.csv"
    file_name = f"{period_start.year}_{period_start.month:02d}.csv"
    file_path = os.path.join(folder_name, file_name)
    
    # Skip if file already exists
    if os.path.exists(file_path):
        tqdm.write(f"File {file_name} already exists, skipping...")
        continue

    # Format dates for the API (e.g., "01 Jan, 2020")
    start_str = period_start.strftime("%d %b, %Y")
    end_str = period_end.strftime("%d %b, %Y")

    tqdm.write(f"Fetching data from {start_str} to {end_str}...")
    klines = client.get_historical_klines(coin_type, interval, start_str, end_str)

    if not klines:
        tqdm.write(f"No data returned for {start_str} to {end_str}")
        continue

    # Define expected columns (from Binance)
    columns = [
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ]
    df = pd.DataFrame(klines, columns=columns)

    # Convert numeric columns
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume',
                    'Quote asset volume', 'Taker buy base asset volume', 'Taker buy quote asset volume']
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

    # Convert timestamp columns from milliseconds to datetime objects
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')

    # Format the DataFrame for Backtrader:
    # 1. Keep only necessary columns.
    # 2. Rename to lowercase names that Backtrader expects.
    # 3. Add 'openinterest' (Backtrader uses this optionally).
    # 4. Set the datetime column as the index.
    df = df[['Open time', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    df.rename(columns={
        'Open time': 'datetime',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }, inplace=True)
    df['openinterest'] = 0  # Add openinterest column

    # Set the datetime column as the index (Backtrader requires the index to be datetime)
    df.set_index('datetime', inplace=True)

    # Save the DataFrame as CSV
    df.to_csv(file_path)
    tqdm.write(f"Saved data to {file_path}")
