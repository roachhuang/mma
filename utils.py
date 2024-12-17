import yfinance as yf

def trailing_stop_loss(entry_price, stop_loss_pct):
    """
    This function calculates the trailing stop-loss price based on a percentage threshold.

    Args:
        entry_price (float): The price at which the position was entered.
        stop_loss_pct (float): The percentage below the entry price (for long positions)
                               or above the entry price (for short positions)
                               to place the stop-loss.

    Returns:
        float: The trailing stop-loss price.
    """
    return entry_price * (
        1 - stop_loss_pct
    )  # Adjust for long/short positions as needed




# Example usage
entry_price = 100.0  # Assuming a long position (buying)
stop_loss_pct = 0.02  # 2% stop-loss threshold

current_price = 105.0  # Current market price

# Calculate trailing stop-loss based on current price
trailing_stop = trailing_stop_loss(entry_price, stop_loss_pct)

print("Entry Price:", entry_price)
print("Current Price:", current_price)
print("Trailing Stop-Loss:", trailing_stop)

# Update trailing stop-loss as price moves favorably
if current_price > trailing_stop:
    trailing_stop = current_price * (1 - stop_loss_pct)
    print("Updated Trailing Stop-Loss:", trailing_stop)


def trailing_stop_loss_atr(entry_price, stop_loss_pct, atr_value):
    """
    This function calculates the trailing stop-loss price based on a percentage threshold and ATR.

    Args:
        entry_price (float): The price at which the position was entered.
        stop_loss_pct (float): The percentage buffer below the entry price (for long positions)
                               or above the entry price (for short positions).
        atr_value (float): The Average True Range value.

    Returns:
        float: The trailing stop-loss price.
    """
    return entry_price * (
        1 - stop_loss_pct - atr_value
    )  # Adjust for long/short positions as needed


# Example usage (assuming ATR is calculated elsewhere)
entry_price = 100.0  # Assuming a long position (buying)
stop_loss_pct = 0.01  # 1% buffer
atr_value = 2.0  # ATR value

current_price = 105.0  # Current market price

# Calculate trailing stop-loss based on price and ATR
trailing_stop = trailing_stop_loss_atr(entry_price, stop_loss_pct, atr_value)

print("Entry Price:", entry_price)
print("Current Price:", current_price)
print("Trailing Stop-Loss (ATR adjusted):", trailing_stop)

# Update trailing stop-loss as price moves favorably and ATR changes


def intraday_strategy(
    data, sma_short, sma_long, rsi_overbought, rsi_oversold, atr_multiplier
):
    """
    This function implements a basic intraday strategy using moving averages, RSI, and ATR.

    Args:
        data (pandas.DataFrame): DataFrame containing OHLC data.
        sma_short (int): Time period for the shorter moving average.
        sma_long (int): Time period for the longer moving average.
        rsi_overbought (int): RSI level indicating overbought conditions (sell signal).
        rsi_oversold (int): RSI level indicating oversold conditions (buy signal).
        atr_multiplier (float): Multiplier for the ATR used in trailing stop-loss.

    Returns:
        pandas.DataFrame: DataFrame with buy and sell signals.
    """

    close_prices = data["Close"]
    high_prices = data["High"]
    low_prices = data["Low"]

    # Calculate technical indicators
    sma_short = ta.SMA(close_prices, timeperiod=sma_short)
    sma_long = ta.SMA(close_prices, timeperiod=sma_long)
    rsi = ta.RSI(close_prices, timeperiod=14)
    atr = ta.ATR(high_prices, low_prices, close_prices, timeperiod=14)

    # Calculate trailing stop-loss based on ATR
    trailing_stop_loss = close_prices * (1 - atr_multiplier * atr)

    # Initialize signal columns
    data["Buy Signal"] = False
    data["Sell Signal"] = False

    # Generate buy and sell signals based on strategy logic
    for i in range(len(data)):
        if (
            (close_prices[i] > sma_short[i])
            and (close_prices[i] > sma_long[i])
            and (rsi[i] < rsi_oversold)
        ):
            data.loc[i, "Buy Signal"] = True
            # Set initial trailing stop-loss on buy
            data.loc[i, "Trailing Stop"] = trailing_stop_loss[i]
        elif (close_prices[i] < sma_short[i]) and (rsi[i] > rsi_overbought):
            data.loc[i, "Sell Signal"] = True
            # Clear trailing stop on sell
            data.loc[i, "Trailing Stop"] = None
        # Update trailing stop-loss on every bar for open positions
        elif data.loc[i, "Buy Signal"] == True:
            data.loc[i, "Trailing Stop"] = max(
                data.loc[i, "Trailing Stop"], trailing_stop_loss[i]
            )

    return data


# Example usage (replace with your data source)
data = pd.read_csv("intraday_data.csv")

# Strategy parameters (adjust as needed)
sma_short = 50
sma_long = 200
rsi_overbought = 70
rsi_oversold = 30
atr_multiplier = 0.5  # Adjust multiplier based on risk tolerance

# Apply strategy and analyze signals
data = intraday_strategy(
    data.copy(), sma_short, sma_long, rsi_overbought, rsi_oversold, atr_multiplier
)

print(data.tail())  # View recent signals
