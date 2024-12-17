import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import mean_squared_error
import talib
import mykbar as kb
from sklearn.linear_model import LinearRegression, Lasso
from sklearn.model_selection import (
    GridSearchCV,
    KFold,
    cross_val_score,
    train_test_split,
)
from sklearn.preprocessing import StandardScaler  # Optional for feature scaling

import talib


def fibonacci_retracements(
    high, low, fibonacci_levels=[0.236, 0.382, 0.5, 0.618, 0.786]
):
    """
    Calculates Fibonacci retracement levels for a given price movement.

    Args:
        high (float): The higher price of the movement.
        low (float): The lower price of the movement.
        fibonacci_levels (list, optional): A list of Fibonacci retracement levels to calculate.
            Defaults to common levels (0.236, 0.382, 0.5, 0.618, 0.786).

    Returns:
        dict: A dictionary containing the retracement level (key) and its price (value) for each level provided.
    """

    retracements = {}
    price_range = high - low

    for level in fibonacci_levels:
        retracement_price = low + (price_range * level)
        retracements[level] = retracement_price

    return retracements


def identify_high_low(closes, timeframe="daily"):
    """
    Identifies the highest and lowest close within a specified timeframe.

    Args:
        closes (list): A list of closing prices.
        timeframe (str, optional): The timeframe to consider for high/low identification. Defaults to "daily".

    Returns:
        tuple: A tuple containing the highest and lowest close within the timeframe.
    """

    # Replace this with your logic to identify high/low based on timeframe
    # (e.g., TA-Lib functions for other timeframes)
    if timeframe == "daily":
        return max(closes), min(closes)
    else:
        raise NotImplementedError(f"Timeframe '{timeframe}' not implemented yet.")


fibonacci_levels = [0.236, 0.5, 0.786]  # Custom levels


# training set (to create model), validation set for selecting a best model, test set (2 person's models PK)
symbol = "9945"
df = kb.readFromDB(dbName="kbars", collectionName=symbol)

# df.indeX = pd.DatetimeIndex(df["ts"])

# X = df.drop(["ts", "_id"], axis=1)

highest_close, lowest_close = identify_high_low(df.close)
retracement = fibonacci_retracements(highest_close, lowest_close, fibonacci_levels)
# print("Fibonacci Retracement Levels based on Closing Prices:")
# for level, price in retracement_levels.items():
#     print(f"{level*100:.2f}%: ${price:.2f}")
y = df.close.values.reshape(-1, 1)
df["close"] = df.close.replace(to_replace=0, method="ffill")
pct = df["close"].pct_change().values.reshape(-1, 1)
rsi = talib.RSI(df.close, timeperiod=14).values.reshape(-1, 1)
macd, signal, hist = talib.MACD(df.close)
signals = []
# sell_signals=[]
# for i in range(len(macd)):
#   if rsi[i] < 30 and macd[i] > signal[i] and macd[i-1] < signal[i-1]:  # MACD crosses above signal (buy)
#     signals.append(1)
#   elif rsi[i] > 70 and macd[i] < signal[i] and macd[i-1] > signal[i-1]:  # MACD crosses below signal (sell)
#     signals.append(-1)
#   else:
#     signals.append(0)
# df_signals = pd.DataFrame(signals)

k, d = talib.STOCH(df.high, df.low, df.close)
sma = talib.SMA(df.close).values.reshape(-1, 1)

X_full = np.hstack(
    (
        # ret_levels.reshape(-1,1),
        # ret_prices.prices.reshape(-1,1),
        # df_signals.values.reshape(-1,1),
        # df.ts.values.reshape(-1,1),
        df.open.values.reshape(-1, 1),
        df.high.values.reshape(-1, 1),
        df.low.values.reshape(-1, 1),
        pct,
        df.volume.values.reshape(-1, 1),
        # X.amount.values.reshape(-1, 1),
        rsi,
        # macd.values.reshape(-1, 1),
        # signal.values.reshape(-1, 1),
        # hist.values.reshape(-1, 1),
        sma,
        # k.values.reshape(-1, 1),
        # d.values.reshape(-1, 1),
    )
)
X_full = X_full[40:]
y = y[40:]

# Split data into training and testing sets (80% training, 20% testing)
X_train, X_test, y_train, y_test = train_test_split(
    X_full, y, test_size=0.2, random_state=42
)

# multiple params

# Set up cross-validation (5-fold)
cv = KFold(n_splits=5, shuffle=True, random_state=42)  # 5-fold CV with shuffling

# Optional: Feature scaling (consider if features have different scales)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)  # Transform test set using fitted scaler

param_grid = {"alpha": np.linspace(0.01, 1.0, 10)}  # EXplore different alpha values
# Create Lasso model with GridSearchCV for hyperparameter tuning
lasso_model = GridSearchCV(
    Lasso(), param_grid=param_grid, cv=cv, scoring="neg_mean_squared_error"
)  # Minimize MSE
# Train the model on the scaled training data
lasso_model.fit(X_train_scaled, y_train.reshape(-1, 1))
print(
    "R Square: ", lasso_model.score(X_train_scaled, y_train.reshape(-1, 1))
)  # 訓練誤差

# Print the best model and its parameters
print("Best Model Parameters:", lasso_model.best_params_)

# Access the best Lasso model
best_model = lasso_model.best_estimator_

# Make predictions on the test set
# X_test.drop(["close"], axis=1, inplace=True)
y_pred = best_model.predict(X_test_scaled)

# Optional: Feature selection (analyze best_model.coef_ to see which features have non-zero importance)
# Evaluate model performance (replace with your preferred metric)
mse = mean_squared_error(y_test, y_pred)
print(f"Mean Squared Error (MSE): {mse:.2f}")

# Print the coefficients (potentially shrunk due to regularization)
print(f"Coefficients: {best_model.coef_.ravel()}")

# print('Coefficients:', best_model.coef_)
# print('Intercept: ', best_model.intercept_)
# print('R Square:', best_model.score(X_full, y))

# cross validation, k-fold

# Create a figure and a grid of subplots with 1 row and 2 columns
# ts_val=X_test.index

# fig, (ax1, ax2) = plt.subplots(1, 2)  # 1 row, 2 columns
plt.plot(X_train_scaled[:, 5], y_train, "bo")
plt.plot(X_test_scaled[:, 5], y_pred, "ro")
# ax1.plot(y_train, "bo")
# ax2.plot(y_pred, "ro")
# # Adjust spacing between plots (optional)
plt.tight_layout()
plt.show()
