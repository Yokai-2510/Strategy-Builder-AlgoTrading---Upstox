import json
import pandas as pd
import time
import requests as rq
from datetime import datetime, timedelta



def read_user_config(user_config_filename):

    # Initialize the dictionary with default values
    order_data = {
        'order_symbol': None,
        'order_flag': False,
        'order_type': None,
        'quantity': None,
        'sell_time_condition': None,
        'target': None,
        'stop_loss': None,
        'ikey_criteria' : None,
        'ikey_value' : None ,        
        'limit_ltp': None ,
        'instrument_key' : None,
        'buy_value' : None,
        'buy_time' : None,
        'buy_ltp' : None
    }

    with open(user_config_filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
            key, value = line.strip().split(' = ')
            key = key.strip()
            value = value.strip()
            if key in order_data:
                # Convert the value to the appropriate type
                if key == 'quantity' or key == 'sell_time_condition' or key == 'Target' or key == 'stop_Loss' or key == 'ikey_value' or key == 'Limit_LTP':
                    value = float(value)
                order_data[key] = value
    
    return order_data



def terminate_subprocess(process):
    try:
        # Attempt to terminate the process
        process.terminate()
        # Wait for a short time for the process to terminate
        time.sleep(1)
        # Check if the process is still running
        if process.poll() is None:
            # Process still running after terminate, try killng it
            process.kill()
            # Wait again for a short time
            time.sleep(1)
            # Check if the process is terminated after killing
            if process.poll() is None:
                # Process could not be terminated even after killing
                return False
    except Exception as e:
        # Handle any exceptions that might occur during termination
        print(f"Error terminating process: {e}")
        return False
    
    # Process terminated successfully
    return True


def json_to_strategy_dict(file_path):
    with open(file_path, 'r') as file:
        json_data = json.load(file)

    final_dict = {}
    for item in json_data:
        set_index = str(item["SetIndex"])
        conditions = {}
        for condition_index, condition in enumerate(item["Conditions"], start=1):
            conditions[f"{set_index}.{condition_index}"] = {
                "Parameter": condition["Parameter"],
                "Operator": condition["Operator"],
                "Value": condition["Value"]
            }
        final_dict[set_index] = conditions

    return final_dict


def json_to_symbol_dict(file_path):
	
    with open(file_path, 'r') as file:
        json_data = json.load(file)

    symbol_dict = {}
    for item in json_data:
        symbol_dict[str(item['SetIndex'])] = item['Symbol']

    return symbol_dict


def create_status_dict(file_path):
    with open(file_path, 'r') as file:
        json_data = json.load(file)

    status_dict = {}
    for item in json_data:
        set_index = str(item["SetIndex"])
        for condition_index, _ in enumerate(item["Conditions"], start=1):
            status_dict[f"{set_index}.{condition_index}"] = "Pending"

    return status_dict


def combine_strategy_status(strategy_dict, status_dict):
    status_dict2 = {}

    # Iterate through the status dictionary
    for index, status in status_dict.items():
        # Check if the index exists in the strategy dictionary
        if index in strategy_dict:
            # Add corresponding key-value pairs from the strategy dictionary
            status_dict2[index] = strategy_dict[index]

            # Add status information to the existing dictionary
            status_dict2[index]['Status'] = status

    return status_dict2

# Call the function to combine the dictionaries
