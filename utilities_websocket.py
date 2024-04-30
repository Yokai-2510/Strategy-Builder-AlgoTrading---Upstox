# Import necessary modules
import asyncio
import json
import ssl
import upstox_client
import websockets
from google.protobuf.json_format import MessageToDict
import MarketDataFeed_pb2 as pb
import pandas as pd
import requests as rq
from threading import Event
import multiprocessing

shared_websocket_df = None
websocket_df_updated = Event()


class SharedWebsocketData:
    def __init__(self, access_token):
        self.lock = multiprocessing.Lock()
        self.websocket_df = None
        self.access_token = access_token

    def get_websocket_data(self):
        with self.lock:
            return self.websocket_df

    def set_websocket_data(self, websocket_df):
        with self.lock:
            self.websocket_df = websocket_df


def get_open_value(access_token):
    # Fetching open value from market quotes
    url = "https://api.upstox.com/v2/market-quote/quotes"
    headers = {
        'accept': 'application/json',
        'Api-Version': '2.0',
        'Authorization': f'Bearer {access_token}'
    }
    payload = {'symbol': "NSE_INDEX|Nifty Bank"}
    response = rq.get(url, headers=headers, params=payload)
    response_data = response.json()
    open_value = response_data['data']['NSE_INDEX:Nifty Bank']['ohlc']['open']
    return open_value

def BN_DF(open_value, strike_price_cap):
    print("Open Value:", open_value)
    rounded_open = round(open_value / 100) * 100
    upper_limit_ikey = rounded_open + strike_price_cap
    lower_limit_ikey = rounded_open - strike_price_cap

    # Reading instrument data from CSV
    df = pd.read_csv("https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz")

    # Filtering instruments based on criteria
    BNDF = df[(df['exchange'] == 'NSE_FO') &
              (df['instrument_type'] == 'OPTIDX') &
              (df['lot_size'] == 15) &
              (df['option_type'].isin(['CE', 'PE']))]

    BNDF = BNDF.sort_values(by='expiry')
    min_expiry = min(BNDF['expiry'].unique())
    BNDF = BNDF[BNDF['expiry'] == min_expiry][['instrument_key', 'strike', 'option_type']]
    BNDF = BNDF.rename(columns={'instrument_key': 'Instrument Key', 'option_type': 'symbol'})

    # Filter based on strike price limits
    BNDF['strike'] = pd.to_numeric(BNDF['strike'], errors='coerce')  # Convert 'strike' column to numeric, handle errors by converting to NaN
    BNDF = BNDF.dropna(subset=['strike'])  # Drop rows with NaN in 'strike' column
    BNDF['strike'] = BNDF['strike'].round(-2)  # Round to the nearest 100
    BNDF = BNDF[(BNDF['strike'] >= lower_limit_ikey) & (BNDF['strike'] <= upper_limit_ikey)]

    return BNDF

def ikey_string(BNDF):
    BNDF = pd.DataFrame(BNDF)
    instrument_keys_string = ','.join(['"{}"'.format(key) for key in BNDF['Instrument Key']])
    instrument_keys_list = BNDF['Instrument Key'].tolist()
    return instrument_keys_list

def get_market_data_feed_authorize(api_version, configuration):
    """Get authorization for market data feed."""
    api_instance = upstox_client.WebsocketApi(
        upstox_client.ApiClient(configuration))
    api_response = api_instance.get_market_data_feed_authorize(api_version)
    return api_response

def decode_protobuf(buffer):
    """Decode protobuf message."""
    feed_response = pb.FeedResponse()
    feed_response.ParseFromString(buffer)
    return feed_response

async def fetch_market_data(instrument_keys_list, access_token, BNDF, shared_websocket_data):
    global data_dict
    global websocket_df
    instrument_keys_data = {}

    # Create default SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Configure OAuth2 access token for authorization
    configuration = upstox_client.Configuration()

    api_version = '2.0'
    configuration.access_token = access_token

    # Get market data feed authorization
    response = get_market_data_feed_authorize(
        api_version, configuration)

    # Connect to the WebSocket with SSL context
    async with websockets.connect(response.data.authorized_redirect_uri, ssl=ssl_context) as websocket:
        print('Connection established')

        await asyncio.sleep(1)  # Wait for 1 second

        # Data to be sent over the WebSocket
        data = {
            "guid": "someguid",
            "method": "sub",
            "data": {
                "mode": "full",
                "instrumentKeys": instrument_keys_list
            }
        }

        # Convert data to binary and send over WebSocket
        binary_data = json.dumps(data).encode('utf-8')
        await websocket.send(binary_data)
        # Continuously receive and decode data from WebSocket
        while True:

            message = await websocket.recv()
            decoded_data = decode_protobuf(message)

            # Convert the decoded data to a dictionary
            data_dict = MessageToDict(decoded_data)

            # Process the received data and store it in a CSV file
            websocket_df = process_instruments_data(data_dict, instrument_keys_list, instrument_keys_data, BNDF)
            shared_websocket_data.set_websocket_data(websocket_df)


def run_websocket(strike_price_cap, shared_websocket_data):
    access_token = shared_websocket_data.access_token
    open_value = get_open_value(access_token)
    BNDF = BN_DF( open_value, strike_price_cap)
    instrument_keys_list = ikey_string(BNDF)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(fetch_market_data(instrument_keys_list, access_token, BNDF, shared_websocket_data))

def process_instruments_data(data_dict, instrument_keys_list, instrument_keys_data, BNDF):
    instrument_data = []

    for instrument_key in instrument_keys_list:
        instrument_info = data_dict.get("feeds", {}).get(instrument_key, {})
        
        # Retrieve the last known values if the instrument key is not present in the current iteration
        if not instrument_info:
            last_known_values = instrument_keys_data.get(instrument_key, {})
            ltp = last_known_values.get("LTP", "NA")
            theta = last_known_values.get("Theta", "NA")
            delta = last_known_values.get("Delta", "NA")
        else:
            if instrument_key == "NSE_INDEX|Nifty Bank":
                ltp = instrument_info.get("ff", {}).get("indexFF", {}).get(
                    "ltpc", {}
                ).get("ltp")
            else:
                ltp = instrument_info.get("ff", {}).get("marketFF", {}).get(
                    "ltpc", {}
                ).get("ltp")

            theta = instrument_info.get("ff", {}).get("marketFF", {}).get(
                "optionGreeks", {}
            ).get("theta")
            delta = instrument_info.get("ff", {}).get("marketFF", {}).get(
                "optionGreeks", {}
            ).get("delta")

        # Update the instrument keys data
        instrument_keys_data.setdefault(instrument_key, {})
        instrument_keys_data[instrument_key]["LTP"] = ltp
        instrument_keys_data[instrument_key]["Theta"] = theta
        instrument_keys_data[instrument_key]["Delta"] = delta

        instrument_data.append({
            "Instrument Key": instrument_key,
            "LTP": ltp,
            "Theta": theta,
            "Delta": delta,
        })

    df_instruments = pd.DataFrame(instrument_data)
    df_instruments = pd.merge(df_instruments, BNDF, on="Instrument Key", how="right")
    output_filename = 'websocket_df.csv'
    df_instruments.to_csv(output_filename, mode='w', index=False)
    
    return df_instruments

