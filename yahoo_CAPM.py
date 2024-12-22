"""
The capital asset pricing model (CAPM) is very widely used and is considered to be a very fundamental concept in investing. It determines the link between the risk and expected return of assets, in particular stocks.
What is the CAPM equation?

The CAPM is defined by the following formula:

where (i) is an individual stock

r(i)(t) = return of stock (i) at time (t)

β(i) = beta of (i)

r(m)(t) = return of market (m) at time (t)

alpha(i)(t) = alpha of (i) at time (t)

β of a stock (i) tells us about the risk the stock will add to the portfolio in comparison to the market. β=1 means that the stock is in line with the market.

According to CAPM, the value of alpha is expected to be zero and that it is very random and cannot be predicted.

The equation seen above is in the form of y = mx+b and therefore it can be treated as a form of linear regression.

手續費	0.1425%，買+賣為0.2850%
折扣後，買+賣約0.14%    
交易稅   股票型ETF 0.1%
        債券型ETF 0%
(僅賣出需收取)	
        股票型ETF：0.1%
        債券型ETF：無
合計	
        w/o discount:    0.385%
        折扣後股票型ETF約 0.24%
        債券型ETF約 0.14%
"""

from sklearn.linear_model import LinearRegression
import pandas as pd
import matplotlib.pyplot as plt

# import numpy as np

import yfinance as yf
from sklearn.impute import SimpleImputer

import os
import sys
# Get the user's home directory path
home_dir = os.path.expanduser("~")
# Construct the path to get_data.py
helpers_dir = os.path.join(home_dir, "projects/helpers")
# Add the helper directory to sys.path (optional, but recommended for absolute paths)
if helpers_dir not in sys.path:
    sys.path.append(helpers_dir)

try:
    import mykbar as kb
    import mongodb as mgdb
    import misc as misc
    import plt as my_plt
except ImportError as e:
    print(f"ImportError: {e}")


def main():
    # stocks_df = pd.DataFrame()
    symbols = [
        # "0050.tw",
        "0056.tw",  # 元大高股息
        # "00919.tw",   # 群益台灣精選高息
        # "00713.tw",   # 元大台灣高息低波
        # "00646.tw",   # S&P500, weight companies based on market capitalization (market cap). a rising market may produce more gains in the S&P 500 than in the Dow.
        # "0051.tw",    # 元大中型100
        # "9921.tw",      #jiant
        # "00662.tw",   # Nasdaq, weight companies based on market capitalization (market cap)
        "0052.tw",  # 富邦科技
        "2330.tw",
        # "2308.tw",      # delta
        # "2371.tw",      # tatung
        # "3703.tw",
        # "2414.tw",    # 精技
        # "2429.tw",    # 銘旺科
        "00664R.tw",  # 國泰臺灣加權反1
        # "00686R.tw",  # 群益臺灣加權反1
        # "00671R.tw",  # nasdaq reverse.
        # "00669R.tw",  # Dow jones reverse, Dow weights each constituent based on stock price. a blue-chip index of 30 stocks.
        # "00648R.tw",  # s&p500 reverse.
        # "00953B.tw",  # bonds
        # "00959B.tw",  # 15y+ us bond
        # '00933b.tw',  # 10y, financial bond
        # '00754b.tw',  # aaa-aa
        # '00884b.tw',  # low cubon
        # '00781b.tw',  # a tech.
        # "00945b.tw",  # us
        # todo: uncomment 2890.tw and debug line 344,
        # '2890.tw',
        # "^twii",
    ]

    def add_new_symbol_to_db(symbols, start_date, end_date) -> bool:
        df_new_symbols = get_data(
            symbols=symbols,
            start_date=str(start_date),
            end_date=str(end_date),
        )
        df_new_symbols.drop(columns="^twii", inplace=True)
        # existing_data = existing_data.join(df_temp)  # use default how='left'
        mgdb.updateDb(dbName, collectionName, df_new_symbols)

    def get_up_to_date_stocks(symbols, start_date, end_date) -> pd.DataFrame:
        """
        Retrieves up-to-date stock data for given symbols between start_date and end_date.
        Reads from a single MongoDB collection if available; fetches missing data from yfinance.
        Ensures the output DataFrame is up-to-date and consistent with the database schema.
        """
        # Read existing data from MongoDB, output: 'Date' as index and drop _id columns
        existing_data = mgdb.readFromDB(dbName=dbName, contractName=collectionName)
        if not existing_data.empty:
            # 1. collection doesn't exist, use given start and end date
            df = get_data(symbols, start_date, end_date)
            mgdb.write2Db(dbName, collectionName, df)
            return df

        # 2. get last date on the collection capm when it exists on db.
        last_date = existing_data.index.max().date()
        # 3. add new symbols data to the db if any recently added.
        symbols_ = [symbol.replace(".", "_") for symbol in symbols]
        new_symbols = [s for s in symbols_ if s not in existing_data.columns]
        if new_symbols:
            add_new_symbol_to_db(new_symbols, start_date=start_date, end_date=last_date)
            existing_data = mgdb.readFromDB(dbName=dbName, contractName=collectionName)

        # 4. Fetch missing data from yfinance coz we may run this, e.g., once every month.
        start_date = kb.add_N_Days(days=1, date=last_date)
        # sub today by 1 coz yf may not have today's data yet. yf.download exclusive end_date
        # end_date = kb.sub_N_Days(days=1)

        new_data = get_data(symbols, start_date, end_date)
        if not new_data.empty:
            # there is data to append. Prepare a DataFrame to store the complete data
            all_data = existing_data.copy()
            # new_data.index = new_data.index.date  # Convert index to date only
            # Merge new data with the existing data
            all_data = pd.concat([all_data, new_data], axis=0)
            # Ensure the DataFrame is sorted, deduplicated, and up-to-date
            all_data = all_data.sort_index().drop_duplicates()
            mgdb.updateDb(db_name=dbName, collection_name=collectionName, df=all_data)
            return all_data
        else:
            # no missing data - data is already up-to-date
            return existing_data

    def get_data(symbols, start_date, end_date) -> pd.DataFrame:
        """
        end_date is exclusinve. get data till end_date -1
        """
        if start_date >= end_date:
            return pd.DataFrame()

        dates = pd.date_range(start_date, end_date, freq="D").date
        df = pd.DataFrame(index=dates)
        df.index.name = "Date"
        if "^twii" not in symbols:  # add twii for reference, if absent
            symbols.insert(0, "^twii")

        # make sure symbols are .tw not _tw for yf.download
        symbols = [symbol.replace("_", ".") for symbol in symbols]
        for symbol in symbols:
            df_temp = yf.download(
                symbol,
                start=str(start_date),
                end=str(end_date),
                auto_adjust=True,
                rounding=True,
            )
            # df_temp=yf.download(symbol, period='1D', auto_adjust=True)
            df_temp = df_temp[["Close"]]

            # reanme to prevent clash
            df_temp.rename(columns={"Close": symbol}, inplace=True)
            # Ensure both indexes are timezone-naive
            df_temp.index = df_temp.index.tz_localize(None)
            df = df.join(df_temp)  # use default how='left'
            if symbol == "^twii":  # drop dates twii didn't trade
                df = df.dropna(subset=["^twii"])

        # forward fill & backward fill
        # watch https://www.youtube.com/watch?v=auR3R__PH0Q&t=19943s @ 1:58
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        df.rename(columns=lambda x: x.replace(".", "_"), inplace=True)
        return df

    def calculate_betas(df, benchmark_col="^twii"):
        """Calculates beta for each stock in the DataFrame against a benchmark.

        Args:
            df: A DataFrame containing stock prices.
            benchmark_col: Column name for the benchmark index.

        Returns:
            A dictionary containing beta values for each stock.
        """
        if benchmark_col not in df.columns:
            raise ValueError(
                f"Benchmark column '{benchmark_col}' not found in DataFrame."
            )

        # slop
        beta = {}
        # intercept
        alpha = {}
        # Calculate daily returns.  # x_pct.iloc[0, :] = 0  # set 1st row to zero coz no pct on it.
        returns = df.pct_change().fillna(0)
        market_returns = returns[benchmark_col].values.reshape(-1, 1)

        # Loop through each stock, excluding the benchmark
        for stock in [col for col in df.columns]: # if col != benchmark_col]:
            stock_returns = returns[stock].values.reshape(-1, 1)

            # Fit linear regression model
            model = LinearRegression().fit(market_returns, stock_returns)

            # Extract beta and alpha
            beta[stock] = model.coef_[0][0]
            alpha[stock] = model.intercept_[0]

        return beta, alpha

    def calculate_weights(beta1, beta2):
        """
        If completely eliminating market exposure doesn’t align with your goals, consider low-beta or even negative-beta portfolios. Low-beta portfolios participate in market gains to some extent,
        while negative-beta portfolios might profit from market downturns.
        Calculates the weights for two stocks to achieve a zero-beta portfolio.
            w1*beta1+w2*beta2=0
            w1+w2=1
                -> w2=1-w1
                w1*b1+(1-w1)b2=0 -> w1*b1+b2-w1*b2=0-> w1*(b1-b2)= -b2->w1=-b2/b1-b2
                factor out the negative sign w1=b2/b2-b1
        Args:
            beta1: Beta of the first stock.
            beta2: Beta of the second stock.

        Returns:
            A tuple (w1, w2) representing the weights for the two stocks.
        """

        # assert is just for debugging not for production, use raise ValueError instead.
        assert beta1 != beta2, "beta1==beta2, divide by zero!"

        # Calculate w2
        # w2 = -beta1 / (beta2 - beta1)
        # # Calculate w1 based on the constraint: w1 + w2 = 1
        # w1 = 1 - w2

        # w1 = beta2 / (beta2 - beta1)
        # w2 = 1 - abs(w1)

        # Calculate weights
        w1 = beta2 / (beta2 - beta1)
        w2 = 1 - w1

        return w1, w2

    ###################################################################################
    dbName = "1d"
    collectionName = "capm"

    # use ^twii as a reference for trading dates
    # firstable set a range of continuous date.
    end_date = kb.get_today()
    start_date = kb.sub_N_Days(365 * 8)

    df = get_up_to_date_stocks(
        symbols=symbols, start_date=start_date, end_date=end_date
    )

    # imputer = SimpleImputer(strategy='mean')
    # df_imputed = imputer.fit_transform(df)
    # df = pd.DataFrame(df_imputed, columns=df.columns)

    # df.interpolate(method="linear", inplace=True)
    # 2. Median Imputation
    # df.fillna(df.mean(), inplace=True)

    """
    important! you can try uncommenting below to see the weight difference. 
    
    """
    df = df.dropna()
    # if plt misplt, check if date is unique before plt
    # print(df.index.is_unique)

    # for better comparison, normalize price data so that all prices start at 1.0
    norm_df = misc.normalize(df)
    my_plt.plt_data(norm_df, title="Normalized Data Relative to First Row")

    # no need to normalize prices coz we end up just needing pct.
    # df_norm = normalize_prices(df)
    # skip _id field coz when writing to db it auto generate the field
    # df_norm = df.iloc[:,1:]

    # For a portfolio of n assets, the covariance matrix will be an n x n matrix. Each element (i, j) of the matrix represents the covariance between asset i and asset j.
    # cov_matrix = df_daily_ret[["2330_TW", "00664R_TW"]].cov()
    # avg_daily_ret=df_daily_ret[['2330_TW', '00664R_TW']].mean()
    # annual_ret= (1+avg_daily_ret)**252 -1
    # risk_aversion = 2

    betas, alphas = calculate_betas(df)

    # r_square[stock] = model.score(x_pct, y_pct)
    # print(f'stock: {stock}, alpha: {alpha[stock]}, beta: {beta[stock]}')

    w1_symbol = "2330"
    # w1_symbol = "0052_tw"
    w2_symbol = "00664R"
    weights={}
    w1, w2 = calculate_weights(betas[w1_symbol+'_tw'], betas[w2_symbol+'_tw'])
    print(f"Weight for {w1_symbol}:, {w1}")
    print(f"Weight for {w2_symbol}:, {w2}")
    weights[w1_symbol] = w1
    weights[w2_symbol] = w2
    misc.pickle_dump("weights", weights)
    
    # regression_line = beta * df_daily_ret["^twii"] + alpha[i]
    # axes[i].plot(df_daily_ret["^twii"], regression_line, "-", color="r")

    fig, ax = plt.subplots()
    # markers = ["o", "s", "^", "p", "x"]  # Different markers for each point
    # colors = ["red", "green", "blue", "black", "yellow"]
    # # Clear the current figure
    # plt.clf()

    plt.title("CAPM Model, x: beta(% of mkt returns), y: alpha (indepent to mkt ret)")
    for key in betas:
        ax.scatter(
            betas[key],
            alphas[key],
            # c=colors[i % len(colors)],
            # marker=markers[i % len(markers)],
        )  # Cycle through markers
        symbol = key.removesuffix("_tw") #  if key.lower().endswith("_tw") else key
        ax.annotate(symbol, (betas[key], alphas[key]))

    # plt.legend(beta.keys(), loc='lower right')  # Add legend with keys as labels
    # Add the vertical line (x=0)
    ax.axvline(x=0, color="green", linestyle="--")
    ax.axvline(x=1, color="red", linestyle="--")
    # Add the horizontal line (y=0)
    ax.axhline(y=0, color="blue", linestyle="--")

    # # Set the plot limits
    # plt.xlim(-3, 3)
    # plt.ylim(-2, 2)
    plt.show()


if __name__ == "__main__":
    main()
