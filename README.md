# Strategy-Builder-Automated-Trading-
Strategy Builder - 
This is a simple implementation of Trading Bot with custom Strategy Builder .

#Buy Criteria :

-The strategy is divided into sets and each set will be checked in parallel , inside each set there will be number of conditions . each condition within a set must be met in sequence , is this happens , then the set will be considered as complete and a buy signal will be generated for that set and the option type (PE or CE ) is also associated with each set , so a buy order will be placed for that option type . refer to the strategy.json to get a clear picture. 
-Each set is divided into threads and all thread share the common function which evaluates the conditions in a while True loop. 
-There can be any number of sets and any number of conditions within them , this allows the execution of multiple stategies. 
- Each set has to be specified with the option type to buy (CE or PE ) .
- Each set will have conditions . In each condition , user will have to add the parameter , the symbol ( > or < ) and the threshold value. 
- Possible Parameters : 
MACD = 'MACD'
MACD Signal = 'Signal'  , value = custom numeric value
MACD Signal = 'Signal'  , value = 'MACD'  if the user wants to compare macd and signal then set the value as MACD for the signal parameter. 
MACD Histogram = 'Histogram'
Spot price of Bank Nifty = 'Spot_price'
Time = 'Time' , value format = "02:00:00"
Note : Only for Signal the threshold value can be MACD if user wants to compare macd vs signal. 

#Sell Criteria : 
After a buy order has been placed , the conditions will be checked in parallel , these conditions are : Stop Loss, Profit  and a timer . If any condition is met a sell order will be placed for the same instrument key. 

#Strategy Input : 
-User Input :
quantity = 15               - Quantity to be Traded . Ensure that the it is in multiples of the respective instrument
order_type = MARKET         - Possible Values : LIMIT or MARKET (in caps) . Specify the order type. 
sell_time_condition = 1     - After the buy order , minutes after which sell order will be placed if sl or target is not met by then. 
target = 0.5                - Target or Profit for the Sell Order.   
stop_loss = 0.5             - Stop Loss 
limit_ltp = 145             - If the order type is specified as limit , input the limit ltp , if market then this criteria wont matter
ikey_criteria = STRIKE      - Possible Value : Delta , Theta, LTP , Strike , ATM , ITM . Users can specify a value for these and buy order will be placed for that ikey.
ikey_value = 50000          - Specify the value for the buy insturment key . wont matter in case of ATM or ITM 

