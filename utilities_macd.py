import pandas as pd
import requests as rq
from datetime import datetime, timedelta
import time
import json 
import threading
import multiprocessing

class sharedData:
    def __init__(self):
        self.lock = multiprocessing.Lock()
        self.live_data = multiprocessing.Array('d', [0.0] * 4)

    def get_live_data(self):
        with self.lock:
            return list(self.live_data)

    def set_live_data(self, live_macd, live_signal, live_histogram, spot_price_bn):
        with self.lock:
            self.live_data[:] = [live_macd, live_signal, live_histogram, spot_price_bn]

def calculate_macd(access_token, n): # n=4 : caliberated 
    def fetch_historical_candle_data(from_date, to_date):
        # Fetch historical candle data from Upstox API
        url = f"https://api.upstox.com/v2/historical-candle/NSE_INDEX|Nifty Bank/1minute/{from_date}/{to_date}"
        headers = {
            'accept': 'application/json',
            'Api-Version': '2.0',
            'Authorization': f'Bearer {access_token}'
        }
        response = rq.get(url, headers=headers).json()
        candles_data = response['data']['candles']
        filtered_data = [[row[0], row[4]] for row in candles_data]  
        columns = ['Datetime', 'Close']
        df = pd.DataFrame(filtered_data, columns=columns)
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        df = df.sort_values(by='Datetime')
        df.set_index('Datetime', inplace=True)
        df_resampled = df.resample('5T').last()
        df_resampled.reset_index(inplace=True)
        df_resampled = df_resampled.dropna()
        return df_resampled


    def fetch_intraday_candle_data():
        # Fetch intraday candle data from Upstox API
        url = f"https://api.upstox.com/v2/historical-candle/intraday/NSE_INDEX|Nifty Bank/1minute"
        headers = {
            'accept': 'application/json',
            'Api-Version': '2.0',
            'Authorization': f'Bearer {access_token}'
        }
        response = rq.get(url, headers=headers).json()
        candles_data = response['data']['candles']
        filtered_data = [[row[0], row[4]] for row in candles_data]  
        columns = ['Datetime', 'Close']
        df = pd.DataFrame(filtered_data, columns=columns)
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        df = df.sort_values(by='Datetime')
        df.set_index('Datetime', inplace=True)
        df_resampled = df.resample('5T').last()
        df_resampled.reset_index(inplace=True)
        df_resampled = df_resampled.dropna()
        return df_resampled


    def macd():
        # Main function to process data and calculate MACD
        working_days = []
        today = datetime.now()
        while len(working_days) < n:
            if today.weekday() < 5:  # Monday to Friday (0 to 4)
                working_days.append(today.strftime('%Y-%m-%d'))
            today -= timedelta(days=1)

        from_date = working_days[0]
        to_date = working_days[-1]

        df_resampled_historical = fetch_historical_candle_data(from_date, to_date)
        df_resampled_intraday = fetch_intraday_candle_data()

        if df_resampled_historical.empty:
            combined_df = df_resampled_intraday
        elif df_resampled_intraday.empty:
            combined_df = df_resampled_historical
        else:
            combined_df = pd.concat([df_resampled_historical, df_resampled_intraday], ignore_index=True)

        combined_df = combined_df.drop_duplicates(subset='Datetime')
        combined_df = combined_df.sort_values(by='Datetime', ascending=False)
        combined_df = combined_df.sort_values(by='Datetime', ascending=True)
        combined_df.reset_index(drop=True, inplace=True)

        short_window = 12
        long_window = 26
        combined_df['ShortEMA'] = combined_df['Close'].ewm(span=short_window, adjust=False).mean()
        combined_df['LongEMA'] = combined_df['Close'].ewm(span=long_window, adjust=False).mean()
        combined_df['MACD'] = combined_df['ShortEMA'] - combined_df['LongEMA']
        signal_window = 9
        combined_df['Signal'] = combined_df['MACD'].ewm(span=signal_window, adjust=False).mean()
        combined_df['MACD_Histogram'] = combined_df['MACD'] - combined_df['Signal']

        latest_macd = combined_df['MACD'].iloc[-1]
        latest_signal = combined_df['Signal'].iloc[-1]
        latest_histogram = combined_df['MACD_Histogram'].iloc[-1]

        return latest_macd, latest_signal, latest_histogram


    latest_macd, latest_signal, latest_histogram = macd()

    return latest_macd, latest_signal, latest_histogram


def current_bn_ltp(access_token): # Fetch Bank Nifty Current Spot Price / LTP 
    # Fetching LTP from market quotes
    url = "https://api.upstox.com/v2/market-quote/quotes"
    headers = {
        'accept': 'application/json',
        'Api-Version': '2.0',
        'Authorization': f'Bearer {access_token}'
    }
    payload = {'symbol': "NSE_INDEX|Nifty Bank"}
    response = rq.get(url, headers=headers, params=payload)
    response_data = response.json()
    ltp = response_data['data']['NSE_INDEX:Nifty Bank']['last_price']
    return ltp



def fetch_live_data(access_token, shared_data):
    while True:
        latest_macd, latest_signal, latest_histogram = calculate_macd(access_token, 4)
        bn_current_ltp = current_bn_ltp(access_token)
        shared_data.set_live_data(latest_macd, latest_signal, latest_histogram, bn_current_ltp)
        time.sleep(0.1)