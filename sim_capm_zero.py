import time
import shioaji.order as stOrder
import pandas as pd

# import shioaji.shioaji
import shioaji as sj
from typing import Dict, List, Optional
from shioaji.constant import (
    OrderState,
    ACTION_BUY,
    ACTION_SELL,
    StockOrderCond,
    STOCK_ORDER_LOT_INTRADAY_ODD,
    STOCK_ORDER_LOT_COMMON,
)

import logging
from datetime import date, datetime, timedelta
from threading import Lock

# 處理ticks即時資料更新的部分
from shioaji import BidAskSTKv1, Exchange, TickSTKv1

####################################################
# import os
from pathlib import Path
import sys

# # Get the user's home directory path
# home_dir = os.path.expanduser("~")
# # Construct the path to get_data.py
# helpers_dir = os.path.join(home_dir, "projects//helpers")
# # Add the helper directory to sys.path (optional, but recommended for absolute paths)
# if helpers_dir not in sys.path:
#     sys.path.append(helpers_dir)

# Get the helpers directory
helpers_dir = Path(__file__).resolve().parent.parent / "helpers"
# Add to sys.path
sys.path.insert(0, str(helpers_dir))
######################################################
try:
    import ShioajiLogin as mysj  # import shioajiLogin, get_snapshots
    import misc
    import yf_data as yfin
except ImportError as e:
    print(f"ImportError: {e}")


def calculate_pair_trade_condition(bot):
    # z-scroe: tells us how many std dev a number is above or blow the mean.
    # g_upperid = "2330"
    # g_lowerid = "00664R"

    # Thresholds
    Z_SPREAD_THRESHOLD = 1.0
    Z_THRESHOLD = 2  # Significant deviation threshold
    RSI_THRESHOLD = 30  # Oversold threshold
    # contract = bot.api.Contracts.Indexs.TSE.TSE001
    # TSE001_snapshot = bot.api.snapshots([contract])
    # current_index = TSE001_snapshot[0].close
    mkt_chg = bot.api.snapshots([bot.api.Contracts.Indexs.TSE.TSE001])[0].change_rate
    mean_std = misc.pickle_read("mean_std.pkl")
    zscore = {}
    snapshots = bot.get_snapshots(symbols)

    # Calculate Z-Scores
    for k in mean_std["mean"]:
        zscore[k] = (snapshots[k].change_rate - mean_std["mean"][k]) / mean_std["std"][k]

    # Check Z-Scores for significant deviation
    zspread = abs(zscore[g_upperid]) - abs(zscore[g_lowerid])
    print(f"market_chg: {mkt_chg}, z-spread: {zspread}")
    if mkt_chg > 0:  # up
        if zspread < -(Z_SPREAD_THRESHOLD + 0.3):
            return True
    elif mkt_chg < 0:  # Market goes down (handle this scenario as needed)
        if zspread > Z_SPREAD_THRESHOLD + 0.3:
            return True
    else:
        # Market is unchanged (handle this scenario as needed)
        # You can define specific conditions for unchanged market
        return False


def calculate_allocate(total_money: int, snapshots: dict, weights: dict) -> dict:
    g_lowerid_shares = int(total_money * weights[g_lowerid] // snapshots[g_lowerid])
    # Adjust shares of the fixed stock to be a multiple of 1000
    g_lowerid_shares = (g_lowerid_shares // 1000) * 1000
    g_lowerid_cost = g_lowerid_shares * snapshots[g_lowerid]

    # Calculate the scale factor to maintain the same weights
    scale_factor = g_lowerid_cost / (total_money * weights[g_lowerid])
    scaled_total_money = total_money * scale_factor

    # Reallocate money based on scaled total money and original weights
    g_upperid_shares = int(scaled_total_money * weights[g_upperid] // snapshots[g_upperid])

    # just for verifying
    # t=g_lowerid_shares * snapshots[g_lowerid]+g_upperid_shares*snapshots[g_upperid]
    # l=t*weights[g_lowerid]/snapshots[g_lowerid]
    # u=t*weights[g_upperid]/snapshots[g_upperid]

    return {
        g_upperid: g_upperid_shares,
        g_lowerid: g_lowerid_shares,
    }


def chk_buy_cond(bot, betas):
    threshold = 0.1425 * 2 * 0.38 + 0.3
    mkt_chg = bot.api.snapshots([bot.api.Contracts.Indexs.TSE.TSE001])[0].change_rate
    expected_g_lowerid_chg = betas[g_lowerid+'_tw'] * mkt_chg
    expected_g_upperid_chg = betas[g_upperid+'_tw'] * mkt_chg
    spread = abs(bot.snapshots[g_upperid].change_rate - expected_g_upperid_chg) + abs(
        bot.snapshots[g_lowerid].change_rate - expected_g_lowerid_chg
    )

    if (
        bot.snapshots[g_upperid].change_rate < expected_g_upperid_chg
        and bot.snapshots[g_lowerid] < expected_g_lowerid_chg
    ):
        if spread > threshold:
            return True
    else:
        return False


#######################################################################################################################
#######################################################################################################################
# main fn. Zero-Beta Portfolio: This portfolio is constructed to have zero systematic risk, meaning its returns are not influenced by market movements.
# It's essentially a portfolio that is uncorrelated with the market portfolio
########################################################################################################################
########################################################################################################################

g_upperid = "2330"
# g_upperid = "0052"
g_lowerid = "00664R"
symbols = [g_upperid.upper(), g_lowerid.upper()]


def main():
    expected_profit = -270
    # fees = 0.385 / 100
    fees = 0.4 / 100
    total_amount = 30000
    weights = misc.pickle_read("weights.pkl")
    betas = misc.pickle_read("betas.pkl")
    # mean_std = misc.pickle_read("mean_std.pkl")

    # weights = {g_upperid: 0.425652829531973, g_lowerid: 0.5743471704680267}
    mutexDict = {symbols[0]: Lock(), symbols[1]: Lock()}
    cooldown = 15
    # sleep to n seconds
    til_second = 10

    bot = mysj.Bot(symbols=symbols, sim=False)
    bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}
    print(bot.pos)
    # todo: maybe just one stock has value, so need to save taken_profit in case not all stocks
    if any(bot.pos.values()):
        # bot.bought_prices = {"2330": 1110, "00664R": 3.63}
        # misc.pickle_dump("bought_prices.pkl", bot.bought_prices)

        bot.bought_prices = misc.pickle_read("bought_prices.pkl")
        print(f"bought price:, {bot.bought_prices}")
        # this is for handling unfilled shares
        bot.shares_to_buy = calculate_allocate(total_amount, bot.bought_prices, weights)

        try:
            while True:  # any(bot.pos.values()):
                # 1. cancel open orders
                bot.cancelOrders()

                # 2. update current positions
                bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}
                if all(value == 0 for value in bot.pos.values()):
                    break

                # 3. fetch latest market snapshots
                bot.snapshots = bot.get_snapshots(symbols)
                [print(f"Close price for {code}: {snapshot.close}") for code, snapshot in bot.snapshots.items()]

                a = calculate_pair_trade_condition(bot)
                theory_prices = bot.get_theory_prices(betas=betas, snapshots=bot.snapshots)
                [print(f"theory: {theory_prices}, snapshots: {bot.snapshots[symbol].close}") for symbol in symbols]
                
                # 4. compute profit
                current_net_profit = sum(
                    misc.calculate_profit(
                        bot.bought_prices[symbol],
                        bot.snapshots[symbol].close,
                        bot.pos[symbol],
                        tax_rate= bot.tax_rate
                    )
                    for symbol in bot.pos.keys()
                    if bot.pos[symbol] > 0
                )

                print(f"current net profit: {current_net_profit}, taken profit: {bot.taken_profit}")

                # todo: if partial filled, net_profit should be recalucated!!!
                if current_net_profit >= expected_profit - bot.taken_profit:
                    # 5. place sell orders
                    for symbol in symbols:
                        if bot.pos[symbol] > 0:
                            bot.trades[symbol] = bot.sell(
                                symbol=symbol,
                                quantity=bot.pos[symbol],
                                price=bot.snapshots[symbol].close,  # -bot.tick_value[symbol],
                            )
                    time.sleep(50)
                # net profit less than expectattion and no sell transaction has been done, at this point, refill any previsouly buy shortage.
                elif bot.taken_profit == 0:
                    prev_unfilled_shares = {symbol: bot.shares_to_buy[symbol] - bot.pos[symbol] for symbol in symbols}
                    # key_of_zero = next((k for k, v in bot.pos.items() if v == 0), None)
                    # if key_of_zero is not None and bot.taken_profit == 0:
                    # theory_prices = get_theory_prices(api, symbols=symbols, bot=bot)
                    # cond2 = all(theory_prices[symbol] > bot.snapshots[symbol].close - 2*bot.tick_value[symbol] for symbol in symbols)
                    if any(prev_unfilled_shares.values()):
                        for symbol in symbols:
                            cond1 = prev_unfilled_shares[symbol] > 0
                            cond2 = bot.snapshots[symbol].close <= bot.bought_prices[symbol] - bot.tick_value[symbol]
                            # cond2 = bot.snapshots[symbol].change_rate <= 0
                            if cond1 and cond2:
                                bot.trades[symbol] = bot.buy(
                                    symbol=symbol,
                                    quantity=prev_unfilled_shares[symbol],
                                    price=bot.snapshots[symbol].close,
                                )
                                print(f"buy0 {symbol} {prev_unfilled_shares[symbol]}@{bot.snapshots[symbol].close}")
                        time.sleep(20)

                current_time = time.time()
                time_to_sleep = cooldown - (current_time % cooldown) + til_second
                # sleep between 20 second to 80 second, should be wait till fully filled.
                time.sleep(time_to_sleep)

                now = datetime.now()
                # every 3 minutes
                if now.minute % 3 == 0:
                    bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}
                    print(f"pos: {bot.pos}")
                print("-" * 80)  # Optional separator

            # reconfirm, maybe not necessary
            bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}  # key: value
            print(f"all sold. pos should be 0: {bot.pos}")
        except KeyboardInterrupt:
            print("\n my Ctrl-C detected. Exiting gracefully...")
            # the buying of previous unfilled share may filled, so need update the file.
            misc.pickle_dump("bought_prices.pkl", bot.bought_prices)
            # bot.cancelOrders()
            bot.logout()
            exit

    #################################################################################
    # empty hand, ask if want to buy
    elif misc.get_user_confirmation(question="buy"):
        bot.bought_prices = {}
        bot.snapshots = bot.get_snapshots(symbols)
        stk_prices = [{k: v.close} for k, v in bot.snapshots.items()]
        bot.shares_to_buy = calculate_allocate(total_amount, stk_prices, weights)
        # bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}
        # always break at here to find a good pair of prices before submitting!!!
        # watch for mkt data, 2330 stock price the lower the better when 00664r price fixs!!!
        while True:
            # 1. cancel open orders
            bot.cancelOrders()
            # 2. get snapshots
            bot.snapshots = bot.get_snapshots(symbols)
            # 3. get pos
            # bot.pos = {symbol: bot.geyt_position_qty(symbol) for symbol in symbols}

            # if abs(bot.snapshots[g_upperid].change_rate) < bot.snapshots[g_lowerid].change_rate:
            #     cond1 = False
            # else:
            #     diff_pct_change = abs(bot.snapshots[g_upperid].change_rate + bot.snapshots[g_lowerid].change_rate)
            #     cond1 = diff_pct_change > 0.1425 * 2 * 0.38 + 0.3
            #     print(f"diff_pct_change: {diff_pct_change}")

            # cond1 = bot.snapshots[g_upperid].change_rate < 0 and bot.snapshots[g_lowerid].change_rate <= 0
            theory_prices = bot.get_theory_prices(betas=betas, snapshots=bot.snapshots)
            # cond2 = bot.snapshots[g_lowerid].close <= theory_prices[g_lowerid]
            # cond2 = all(bot.snapshots[symbol].close < theory_prices[symbol] for symbol in symbols)
            [print(f"theory: {theory_prices}, snapshots: {bot.snapshots[symbol].close}") for symbol in symbols]

            if chk_buy_cond(bot, betas=betas):
                [
                    print(f"shares_to_buy:{bot.shares_to_buy}, @price {bot.snapshots[symbol].close}")
                    for symbol in symbols
                ]
                for symbol in symbols:
                    bot.trades[symbol] = bot.buy(
                        symbol=symbol,
                        quantity=bot.shares_to_buy[symbol],
                        price=bot.snapshots[symbol].close,
                    )

                try:
                    # wait till all buy orders are filled.
                    bot.wait_till_filled()
                    misc.pickle_dump("bought_prices.pkl", bot.bought_prices)
                    bot.logout
                    break
                except KeyboardInterrupt:
                    print("\n my Ctrl-C detected. Exiting gracefully...")
                    key_of_zero = next((k for k, v in bot.bought_prices.items() if v == 0), None)
                    if any(bot.bought_prices.values()):
                        bot.bought_prices[key_of_zero] = bot.snapshots[key_of_zero].close
                        misc.pickle_dump("bought_prices.pkl", bot.bought_prices)
                    bot.logout()
                    exit()

            time.sleep(25)
            # Print a separator with a message
            print("-" * 80)
    else:
        print("END: empty-handed and do nothing.")
        bot.logout()


if __name__ == "__main__":
    main()
