import math
from datetime import datetime, time, timedelta
import json
import requests as rq
from utilities_websocket import SharedWebsocketData


def place_order(instrument_key, quantity, transaction_type, access_token, limit_price, order_type):
    url = "https://api.upstox.com/v2/order/place"
    headers = {
        'accept': 'application/json',
        'Api-Version': '2.0',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    payload = {
        "quantity": quantity,
        "product": "I",
        "validity": "DAY",
        "price": limit_price,
        "tag": "string",
        "instrument_token": instrument_key,
        "order_type": order_type,
        "transaction_type": transaction_type,
        "disclosed_quantity": 0,
        "trigger_price": 0,
        "is_amo": False
    }
    data = json.dumps(payload)
    response = rq.post(url, headers=headers, data=data)
    return response.json()


def execute_buy(access_token, order_data, shared_websocket_data,shared_data,data_lock):

    instrument_key = select_buy_ikey(shared_websocket_data, order_data,shared_data,data_lock)
    order_data["instrument_key"] = instrument_key
    quantity = order_data['quantity']
    transaction_type = "BUY"
    order_type = order_data["order_type"]
    if order_type == "MARKET":
        limit_price = 0
    else:
        limit_price = order_data["limit_ltp"]
    response = place_order(instrument_key, quantity, transaction_type, access_token, limit_price, order_type)
    order_data["buy_time"] = datetime.now().strftime('%H:%M:%S')
    print(response)
    # Fetch the LTP from the shared_websocket_data
    websocket_df = shared_websocket_data.get_websocket_data()
    if websocket_df is not None:
        instrument_row = websocket_df[websocket_df['Instrument Key'] == instrument_key]
        buy_ltp = instrument_row['LTP'].values[0]
        order_data['buy_ltp'] = buy_ltp
        print(order_data)
    return response


def execute_sell(access_token, order_data):
    instrument_key = order_data["instrument_key"]
    transaction_type = "SELL"
    quantity = order_data['quantity']
    order_type = order_data["order_type"]
    if order_type == "MARKET":
        limit_price = 0
    else:
        limit_price = order_data["limit_ltp"]
    response = place_order(instrument_key, quantity, transaction_type, access_token, limit_price, order_type)
    return response


def check_sell_criteria(shared_websocket_data, order_data):
    websocket_df = shared_websocket_data.get_websocket_data()
    if websocket_df is not None:
        instrument_row = websocket_df[websocket_df['Instrument Key'] == order_data['instrument_key']]

        if not instrument_row.empty:
            current_ltp = instrument_row['LTP'].values[0]
            current_time = datetime.now()
            buy_ltp = order_data['buy_ltp']
            stop_loss_ltp = float(buy_ltp) - float(order_data['stop_loss'])
            target_ltp = float(buy_ltp) + float(order_data['target'])

            # Get the current date
            today = datetime.now().date()

            # Combine the current date with the buy time
            buy_time = datetime.strptime(order_data['buy_time'], '%H:%M:%S')
            buy_time_dt = datetime.combine(today, buy_time.time())

            # Calculate the target_time correctly
            target_time = buy_time_dt + timedelta(minutes=order_data["sell_time_condition"])

            print("Buy time:", buy_time_dt)
            print("Current time:", current_time)
            print("Target_time:", target_time)
            print("Buy LTP:", buy_ltp)
            print("Current LTP:", current_ltp)

            if current_ltp > target_ltp:
                print("Target Hit")
                return True
            elif current_ltp < stop_loss_ltp:
                print("Stop Loss Hit")
                return True
            elif current_time > target_time:
                print("Time Condition Met")
                return True


def select_buy_ikey(shared_websocket_data, order_data,shared_data,data_lock):
    ikey_criteria = order_data["ikey_criteria"]
    ikey_criteria_value = float(order_data["ikey_value"])
    symbol = order_data['order_symbol']
    websocket_df = shared_websocket_data.get_websocket_data()
    symbol_df = websocket_df[websocket_df['symbol'] == symbol]
    data_lock.acquire()
    try:
        live_data = shared_data.get_live_data()
        spot_price_value = live_data[3]
    finally:
        data_lock.release()
    
    if ikey_criteria == 'DELTA':
        instrument_key = find_nearest_delta(symbol_df, ikey_criteria_value, websocket_df,order_data)

    elif ikey_criteria == 'LTP':
        instrument_key = find_nearest_ltp(symbol_df, ikey_criteria_value, websocket_df,order_data)
    
    elif ikey_criteria == 'ATM':
        ikey_criteria_value = spot_price_value
        if symbol == 'CE':
            instrument_key = find_atm_ce(order_data, shared_websocket_data, ikey_criteria_value)
        elif symbol == 'PE':
            instrument_key = find_atm_pe(order_data, shared_websocket_data, ikey_criteria_value)

    elif ikey_criteria == 'ITM':
        ikey_criteria_value = spot_price_value
        if symbol == 'CE':
            instrument_key = find_itm_ce(order_data, shared_websocket_data, ikey_criteria_value)
        elif symbol == 'PE':
            instrument_key = find_itm_pe(order_data, shared_websocket_data, ikey_criteria_value)

    elif  ikey_criteria == 'STRIKE' :
        instrument_key = find_strike(ikey_criteria_value,order_data, shared_websocket_data)
    return instrument_key



def find_itm_pe(order_data, shared_websocket_data, ikey_criteria_value):
    rounded_number = math.floor(ikey_criteria_value / 100) * 100
    nearest_itm = rounded_number - 100  # Subtract 100 to get the nearest ITM strike price
    print(nearest_itm)  # Print the nearest ITM for debugging purposes
    websocket_df = shared_websocket_data.get_websocket_data()
    symbol = order_data['order_symbol']

    if websocket_df is not None:
        symbol_df = websocket_df[websocket_df['symbol'] == symbol]

        for index, row in symbol_df.iterrows():
            strike = float(row['strike'])
            if strike == nearest_itm:
                order_data['buy_value'] = strike
                return row['Instrument Key']


def find_itm_ce(order_data, shared_websocket_data, ikey_criteria_value):
    rounded_number = math.ceil(ikey_criteria_value / 100) * 100
    nearest_itm = rounded_number + 100  # Add 100 to get the nearest ITM strike price for Call Option (CE)
    print(nearest_itm)  # Print the nearest ITM for debugging purposes
    websocket_df = shared_websocket_data.get_websocket_data()
    symbol = order_data['order_symbol']

    if websocket_df is not None:
        symbol_df = websocket_df[websocket_df['symbol'] == symbol]

        for index, row in symbol_df.iterrows():
            strike = float(row['strike'])
            if strike == nearest_itm:
                order_data['buy_value'] = strike
                return row['Instrument Key']

def find_atm_ce(order_data, shared_websocket_data, ikey_criteria_value):
    rounded_number = math.ceil(ikey_criteria_value / 100) * 100
    nearest_atm = rounded_number  # No adjustment needed for ATM Call Option (CE)
    print(nearest_atm)  # Print the nearest ATM for debugging purposes
    websocket_df = shared_websocket_data.get_websocket_data()
    symbol = order_data['order_symbol']

    if websocket_df is not None:
        symbol_df = websocket_df[websocket_df['symbol'] == symbol]

        for index, row in symbol_df.iterrows():
            strike = float(row['strike'])
            if strike == nearest_atm:
                order_data['buy_value'] = strike
                return row['Instrument Key']

def find_atm_pe(order_data, shared_websocket_data, ikey_criteria_value):
    rounded_number = math.floor(ikey_criteria_value / 100) * 100
    nearest_atm = rounded_number  # No adjustment needed for ATM Put Option (PE)
    print(nearest_atm)  # Print the nearest ATM for debugging purposes
    websocket_df = shared_websocket_data.get_websocket_data()
    symbol = order_data['order_symbol']

    if websocket_df is not None:
        symbol_df = websocket_df[websocket_df['symbol'] == symbol]

        for index, row in symbol_df.iterrows():
            strike = float(row['strike'])
            if strike == nearest_atm:
                order_data['buy_value'] = strike
                return row['Instrument Key']

def find_strike(ikey_criteria_value,order_data, shared_websocket_data):
    symbol = order_data['order_symbol']
    strike_price = ikey_criteria_value
    websocket_df = shared_websocket_data.get_websocket_data()
    symbol_df = websocket_df[websocket_df['symbol'] == symbol]
    filtered_df = symbol_df[symbol_df['strike'] == strike_price]
    return filtered_df.iloc[0]['Instrument Key']


def find_nearest_delta(symbol_df, ikey_criteria_value, websocket_df,order_data):
    nearest_instrument_key = None
    min_difference = float('inf')
    preferred_delta = ikey_criteria_value

    if websocket_df is not None:
        for index, row in symbol_df.iterrows():
            delta = float(row['Delta'])
            difference = abs(preferred_delta - delta)
            if difference < min_difference:
                min_difference = difference
                nearest_delta = delta
                nearest_instrument_key = row['Instrument Key']
                order_data['buy_value'] = nearest_delta
    return nearest_instrument_key


def find_nearest_ltp(symbol_df, ikey_criteria_value, websocket_df,order_data):
    nearest_instrument_key = None
    min_difference = float('inf')
    preferred_ltp = ikey_criteria_value

    if websocket_df is not None:
        for index, row in symbol_df.iterrows():
            ltp = float(row['LTP'])
            difference = abs(preferred_ltp - ltp)
            if difference < min_difference:
                min_difference = difference
                nearest_ltp = ltp
                nearest_instrument_key = row['Instrument Key']
                order_data['buy_value'] = nearest_ltp
    return nearest_instrument_key