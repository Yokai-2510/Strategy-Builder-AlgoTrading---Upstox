# Strategy Builder - Automated Trading

## Strategy Builder

This is a simple implementation of a Trading Bot with a custom Strategy Builder.

### Buy Criteria

- The strategy is divided into sets, and each set will be checked in parallel. Inside each set, there will be a number of conditions. Each condition within a set must be met in sequence. If this happens, then the set will be considered complete, and a buy signal will be generated for that set. The option type (Put or Call) is also associated with each set, so a buy order will be placed for that option type. Refer to the `strategy.json` file to get a clear picture.

- Each set is divided into threads, and all threads share a common function that evaluates the conditions in a `while True` loop.

- There can be any number of sets and any number of conditions within them, allowing for the execution of multiple strategies.

- Each set must be specified with the option type to buy (Call or Put).

- Each set will have conditions. In each condition, the user will have to add the parameter, the symbol (`>` or `<`), and the threshold value.

- Possible Parameters:
  - `MACD`: Moving Average Convergence Divergence
  - `Signal`: MACD Signal Line, value can be a custom numeric value or `'MACD'` if the user wants to compare MACD and Signal Line
  - `Histogram`: MACD Histogram
  - `Spot_price`: Spot price of the underlying asset (e.g., Bank Nifty)
  - `Time`: Time in the format `"HH:MM:SS"`

  **Note:** Only for the `Signal` parameter, the threshold value can be `'MACD'` if the user wants to compare MACD and Signal Line.

### Sell Criteria

After a buy order has been placed, the conditions will be checked in parallel. These conditions are Stop Loss, Profit, and a timer. If any condition is met, a sell order will be placed for the same instrument key.

### Strategy Input

- User Input:
  - `quantity`: Quantity to be traded. Ensure that it is a multiple of the respective instrument.
  - `order_type`: Possible values are `LIMIT` or `MARKET` (in caps). Specify the order type.
  - `sell_time_condition`: After the buy order, the number of minutes after which a sell order will be placed if the stop loss or target is not met by then.
  - `target`: Target or profit for the sell order.
  - `stop_loss`: Stop loss for the sell order.
  - `limit_ltp`: If the order type is specified as `LIMIT`, input the limit last traded price (LTP). If the order type is `MARKET`, this criteria won't matter.
  - `ikey_criteria`: Possible values are `Delta`, `Theta`, `LTP`, `Strike`, `ATM`, or `ITM`. Users can specify a value for these, and a buy order will be placed for that instrument key.
  - `ikey_value`: Specify the value for the buy instrument key. This won't matter in case of `ATM` or `ITM`.
