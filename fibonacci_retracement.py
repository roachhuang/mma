# Algorithm applying Fibonacci resistance and support bands to a price chart

import requests
import pandas as pd
import numpy as np
from get_data import download_data
# import pandas_datareader.data as web
from datetime import datetime
import matplotlib.pyplot as plt

plt.style.use("Solarize_Light2")
# Fib function


def fib_retrace(ticker):

    # Fetch data
    start = "2016-03-21"
    end = datetime.today()
    df=download_data(ticker, start=start, end=end)
    # df = web.DataReader(ticker, data_source="yahoo", start=start, end=end)

    # Fibonacci constants
    max_value = df["Close"].max()
    min_value = df["Close"].min()
    difference = max_value - min_value

    # Set Fibonacci levels
    first_level = max_value - difference * 0.236
    second_level = max_value - difference * 0.382
    third_level = max_value - difference * 0.5
    fourth_level = max_value - difference * 0.618

    # Print levels
    print("Percentage level\t Price")
    print("0.00%\t\t", round(max_value, 3))
    print("23.6\t\t", round(first_level, 3))
    print("38.2%\t\t", round(second_level, 3))
    print("50%\t\t", round(third_level, 3))
    print("61.8%\t\t", round(fourth_level, 3))
    print("100.00%\t\t", round(min_value, 3))

    # Plot Fibonacci graph
    plot_title = "Fibonacci Retracement for " + ticker
    fig = plt.figure(figsize=(22.5, 12.5))
    plt.title(plot_title, fontsize=30)
    ax = fig.add_subplot(111)
    plt.plot(df.index, df["Close"])
    plt.axhline(max_value, linestyle="--", alpha=0.5, color="purple")
    ax.fill_between(df.index, max_value, first_level, color="purple", alpha=0.2)

    # Fill sections
    plt.axhline(first_level, linestyle="--", alpha=0.5, color="blue")
    ax.fill_between(df.index, first_level, second_level, color="blue", alpha=0.2)

    plt.axhline(second_level, linestyle="--", alpha=0.5, color="green")
    ax.fill_between(df.index, second_level, third_level, color="green", alpha=0.2)

    plt.axhline(third_level, linestyle="--", alpha=0.5, color="red")
    ax.fill_between(df.index, third_level, fourth_level, color="red", alpha=0.2)

    plt.axhline(fourth_level, linestyle="--", alpha=0.5, color="orange")
    ax.fill_between(df.index, fourth_level, min_value, color="orange", alpha=0.2)

    plt.axhline(min_value, linestyle="--", alpha=0.5, color="yellow")
    plt.xlabel("Date", fontsize=20)
    plt.ylabel("Close Price (USD)", fontsize=20)


fib_retrace("BTC-USD")


fib_retrace("ADA-USD")


fib_retrace("ETH-USD")
