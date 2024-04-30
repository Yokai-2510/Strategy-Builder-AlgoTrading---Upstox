import sys
sys.stdout.flush()

import json
import threading
import time
import pprint
import os
from datetime import datetime , timedelta
import subprocess
from utilities_evaluator import set_to_threads
from utilities_misc import read_user_config , create_status_dict , json_to_strategy_dict , json_to_symbol_dict , terminate_subprocess , combine_strategy_status
from utilities_order import execute_buy , execute_sell , check_sell_criteria
from utilities_macd import fetch_live_data
from utilities_macd import sharedData
from utilities_websocket import SharedWebsocketData, run_websocket

process = subprocess.Popen(["python", "websocket_data.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True, start_new_session=True)
time.sleep(3)
sys.stdout.flush()


access_token_filename = "access_token.txt"
with open(access_token_filename, "r") as file:
    access_token = file.read()
file_path = 'Strategy.json'
shared_data = sharedData()
data_lock = threading.Lock()
buy_order_executed = False
user_config_filename = "user_config.txt"
strike_price_cap = 2000

buy_order_executed = False
market_close_time = datetime.now().replace(hour=23, minute=29, second=0, microsecond=0)  


order_data = read_user_config(user_config_filename)
strategy_dict = json_to_strategy_dict(file_path)
status_dict = create_status_dict(file_path)
symbol_dict = json_to_symbol_dict(file_path)
shared_websocket_data = SharedWebsocketData(access_token)


# Start the WebSocket thread
websocket_thread = threading.Thread(target=run_websocket, args=(strike_price_cap ,shared_websocket_data,))
websocket_thread.daemon = True
websocket_thread.start()
time.sleep(5) 


live_data_thread = threading.Thread(target=fetch_live_data, args=(access_token, shared_data))
live_data_thread.daemon = True
live_data_thread.start()
time.sleep(4)

evaluate_thread = threading.Thread(target=set_to_threads, args=(strategy_dict, shared_data, status_dict, order_data, symbol_dict,data_lock))
evaluate_thread.daemon = True
evaluate_thread.start()
time.sleep(2)



while True:
    #os.system('cls')
    #sys.stdout.flush()

    current_time = datetime.now()
    if buy_order_executed == False and current_time > market_close_time:
        print("Market Closed ! Cannot execute Buy order")
        break
    if current_time < market_close_time and buy_order_executed == False:
        live_data_values = shared_data.get_live_data()
        pprint.pprint(status_dict)
        pprint.pprint(live_data_values)


    # Check for Buy Condition and Execute Buy
    if order_data['order_flag'] == True and buy_order_executed == False and current_time < market_close_time:
        print("order signal generated")
        response = execute_buy(access_token, order_data, shared_websocket_data,shared_data,data_lock)
        print(response)
        buy_order_executed = True


    # Check for Sell Condition and Execute Sell
    if buy_order_executed:
        print("Buy Condition Set met , Waiting for sell")
        if check_sell_criteria(shared_websocket_data, order_data) or current_time > market_close_time:
            response = execute_sell(access_token, order_data)
            print(response)
            break
    time.sleep(1)

terminate_subprocess(process)