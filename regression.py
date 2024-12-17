import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import mean_squared_error
import talib

from sklearn.linear_model import LinearRegression, Lasso
from sklearn.model_selection import (
    GridSearchCV,
    KFold,
    cross_val_score,
    train_test_split,
)
from sklearn.preprocessing import StandardScaler  # Optional for feature scaling


import os
import sys

# Get the user's home directory path
home_dir = os.path.expanduser("~")
# Construct the path to get_data.py
helpers_dir = os.path.join(home_dir, "projects/helpers")
# Add the helper directory to sys.path (optional, but recommended for absolute paths)
if helpers_dir not in sys.path:    
    sys.path.append(helpers_dir)

import mykbar as kb
import getDataUptodate as gd

# training set (to create model), validation set for selecting a best model, test set (2 person's models PK)
symbol = "0052"
df = gd.getData(symbol=symbol, interval="1d", years=12)
# df = kb.readFromDB(dbName="1d", collectionName=symbol)
df.indeX = pd.DatetimeIndex(df["ts"])
X = df.drop(["ts", "_id"], axis=1)
y = df.close
pct = X["close"].pct_change().values.reshape(-1, 1)
rsi = talib.RSI(X.close, timeperiod=14).values.reshape(-1, 1)
# dif, mace, osc = talib.MACD(df.close)
# k, d = talib.STOCH(df.high, df.low, df.close)
sma = talib.SMA(X.close).values.reshape(-1, 1)

X_full = np.hstack(
    (
        X.open.values.reshape(-1, 1),
        X.high.values.reshape(-1, 1),
        X.low.values.reshape(-1, 1),
        X.volume.values.reshape(-1, 1),
        X.amount.values.reshape(-1, 1),
        # pct,
        rsi,
        # dif.values.reshape(-1, 1),
        # mace.values.reshape(-1, 1),
        # osc.values.reshape(-1, 1),
        sma,
        # k.values.reshape(-1, 1),
        # d.values.reshape(-1, 1),
    )
)
X_full=X_full[50:]
y=y[50:]

# Split data into training and testing sets (80% training, 20% testing)
X_train, X_test, y_train, y_test = train_test_split(
    X_full, y, test_size=0.2, random_state=42
)

# multiple params
# construct a regression model
lm = LinearRegression() 

# Optional: Feature scaling (consider if features have different scales)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)  # Transform test set using fitted scaler

lm.fit(X_train_scaled, y_train.values.reshape(-1,1))
print("R Square: ", lm.score(X_train_scaled, y_train.values.reshape(-1,1)))  # 訓練誤差

# Make predictions on the test set
# X_test.drop(["close"], axis=1, inplace=True)
y_pred = lm.predict(X_test_scaled)
print(y_pred)
# Optional: Feature selection (analyze lm.coef_ to see which features have non-zero importance)
# Evaluate model performance (replace with your preferred metric)
mse = mean_squared_error(y_test, y_pred)
print(f"Mean Squared Error (MSE): {mse:.2f}")

# Print the coefficients (potentially shrunk due to regularization)
print(f"Coefficients: {lm.coef_.ravel()}")

# print('Coefficients:', lm.coef_)
# print('Intercept: ', lm.intercept_)
# print('R Square:', lm.score(X_full, y))

# cross validation, k-fold

plt.plot(X_train_scaled[:,5], y_train, 'bo')
plt.plot(X_test_scaled[:,5], y_pred, 'ro')
plt.show()
