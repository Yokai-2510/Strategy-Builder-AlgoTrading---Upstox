import json
from datetime import datetime , time , timedelta
import threading
import time
from utilities_macd import sharedData

def evaluate_parameters(current_parameter, operator, target_value, shared_data, data_lock):
    
    while True:
        data_lock.acquire()
        try:
            live_data = shared_data.get_live_data()
            macd_value = live_data[0]
            signal_value = live_data[1]
            histogram_value = live_data[2]
            spot_price_value = live_data[3]
        finally:
            data_lock.release()

        if current_parameter == 'Time':
            target_value = str(target_value)
            target_value = datetime.strptime(target_value, '%H:%M:%S').time()
            current_time = datetime.now().time()
            if operator == '>':
                if current_time > target_value:
                    return True
            elif operator == '<':
                if current_time < target_value:
                    return True

        elif current_parameter == 'MACD':
            target_value = float(target_value)
            if operator == '>':
                if macd_value > target_value:
                    return True
            elif operator == '<':
                if macd_value < target_value:
                    return True

        elif current_parameter == 'Signal':
            if target_value == 'MACD':
                target_value = macd_value
            else:
                target_value = float(target_value)
            if operator == '>':
                if signal_value > target_value:
                    return True
            elif operator == '<':
                if signal_value < target_value:
                    return True

        elif current_parameter == 'Histogram':
            target_value = float(target_value)
            if operator == '>':
                if histogram_value > target_value:
                    return True
            elif operator == '<':
                if histogram_value < target_value:
                    return True

        elif current_parameter == 'Spot_Price':
            target_value = float(target_value)
            if operator == '>':
                if spot_price_value > target_value:
                    return True
            elif operator == '<':
                if spot_price_value < target_value:
                    return True

 
def evaluate_param_set(custom_strategy_dict, shared_data, status_dict, set_number, order_data, symbol_dict, data_lock):

    for key, strategy_dict in custom_strategy_dict.items():
        current_parameter = strategy_dict["Parameter"]
        operator = strategy_dict["Operator"]
        target_value = strategy_dict["Value"]

        # Update status to "Checking" before evaluation
        status_dict[key] = "Checking"

        if evaluate_parameters(current_parameter, operator, target_value, shared_data, data_lock):
            status_dict[key] = "Completed"

    order_data['order_symbol'] = symbol_dict[str(set_number)]
    order_data['order_flag'] = True



def get_custom_strategy_dict(strategy_dict, set_number):
    custom_strategy_dict = {}
    set_key = str(set_number)
    if set_key in strategy_dict:
        custom_strategy_dict = strategy_dict[set_key]
    return custom_strategy_dict



def set_to_threads(strategy_dict, shared_data, status_dict, order_data, symbol_dict, data_lock):
    threads = []
    for set_number in strategy_dict:
        custom_strategy_dict = get_custom_strategy_dict(strategy_dict, set_number)
        thread = threading.Thread(target=evaluate_param_set, args=(custom_strategy_dict, shared_data, status_dict, set_number, order_data, symbol_dict, data_lock))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()