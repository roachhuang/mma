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


def calculate_allocate(total_money: int, snapshots: dict, weights: dict) -> dict:
    g_lowerid_shares = int(total_money * weights[g_lowerid] // snapshots[g_lowerid].close)
    # Adjust shares of the fixed stock to be a multiple of 1000
    g_lowerid_shares = (g_lowerid_shares // 1000) * 1000
    g_lowerid_cost = g_lowerid_shares * snapshots[g_lowerid].close

    # Calculate the scale factor to maintain the same weights
    scale_factor = g_lowerid_cost / (total_money * weights[g_lowerid])
    scaled_total_money = total_money * scale_factor

    # Reallocate money based on scaled total money and original weights
    g_upperid_shares = int(scaled_total_money * weights[g_upperid] // snapshots[g_upperid].close)

    # just for verifying
    # t=g_lowerid_shares * snapshots[g_lowerid]+g_upperid_shares*snapshots[g_upperid]
    # l=t*weights[g_lowerid]/snapshots[g_lowerid]
    # u=t*weights[g_upperid]/snapshots[g_upperid]

    return {
        g_upperid: g_upperid_shares,
        g_lowerid: g_lowerid_shares,
    }


'''
class GridBot:
    """
    passing in api for
    Dependency Injection: This promotes loose coupling between classes, making the Bot class more reusable and testable.
    """

    def __init__(self, api, symbols: List):
        self.bought_prices = {}
        self.sell_price = {}
        self.shares_to_buy = {}
        self.pos = {}
        self.snapshots = {}
        self.trades = {}
        self.tick_value = {}
        self.previous_close_prices = {}
        self.taken_profit = 0
        self.api = api
        self.api.set_order_callback(self.order_cb)
        self.snapshots = mysj.get_snapshots(self.api, symbols)
        for symbol in symbols:
            contract = self.api.Contracts.Stocks.TSE[symbol]
            self.previous_close_prices[symbol] = contract.reference
            self.tick_value[symbol] = misc.get_tick_unit(self.snapshots[symbol].close)
        contract = api.Contracts.Indexs.TSE.TSE001
        end_date = misc.get_today()
        start_date = misc.sub_N_Days(15)
        pd = yfin.download_data("^TWII", interval="1d", start=start_date, end=end_date)
        self.previous_close_index = pd.Close.iloc[-1]

    def get_position_qty(self, symbol) -> int:
        try:
            positions = self.api.list_positions(self.api.stock_account, unit=sj.constant.Unit.Share)
            return next((pos.quantity for pos in positions if pos.code == symbol), 0)
        except sj.error.TokenError as e:
            logging.error(f"Token error: {e.detail}")
            return 0

    def buy(self, symbol, price, quantity):
        return self.place_flexible_order(symbol=symbol, action=ACTION_BUY, price=price, qty=quantity)

    def sell(self, symbol, price, quantity):
        return self.place_flexible_order(symbol=symbol, action=ACTION_SELL, price=price, qty=quantity)

    def place_flexible_order(self, symbol, price, qty, action):
        # Determine the number of regular lots and odd lot quantity
        common_lot_qty = qty // 1000  # Regular lots (1 lot = 1000 shares)
        odd_lot_qty = qty % 1000  # Remaining odd lot quantity
        contract = self.api.Contracts.Stocks[symbol]
        # Place regular lot orders if applicable
        if common_lot_qty > 0:
            order = self.api.Order(
                price=price,  # contract.limit_down,
                quantity=int(common_lot_qty),  # Total quantity in regular lots
                action=action,
                # price_type="MKT",
                price_type="LMT",
                # order_type="IOC",
                order_type="ROD",
                order_lot=STOCK_ORDER_LOT_COMMON,  # Regular lot
                account=self.api.stock_account,
            )
            trade = self.api.place_order(contract, order)
            print(f"Placed regular lot {action} order for {symbol}: {common_lot_qty} lot(s) @{price}")
            # print("status:", trade.status.status)
        # if qty like 1300 shares, and you want to place it all, change elif to if!!!
        elif odd_lot_qty > 0:
            order = self.api.Order(
                price=price,  # contract.limit_down,
                quantity=int(odd_lot_qty),  # Remaining odd lot quantity
                action=action,
                price_type="LMT",
                # ROC is the only available ord type for intraday odd lot.
                order_type="ROD",
                order_lot=STOCK_ORDER_LOT_INTRADAY_ODD,
                account=self.api.stock_account,
            )
            trade = self.api.place_order(contract, order)
            print(f"Placed odd lot {action} order for {symbol}: {odd_lot_qty} shares @{price}")
        # log the most crucial info for record
        logging.info(f"trade: {trade}")
        print("trade:", trade)
        return trade
        # print("status:", trade.status.status)

    def cancelOrders(self) -> None:
        # Before obtaining the Trade status, it must be updated with update_status!!!
        self.api.update_status(self.api.stock_account)
        tradelist = self.api.list_trades()
        trades_to_cancel = [
            trade
            for trade in tradelist
            if trade.status.status
            not in {
                stOrder.Status.Cancelled,
                stOrder.Status.Failed,
                stOrder.Status.Filled,
            }
            and trade.contract.code in symbols
        ]

        if len(trades_to_cancel) == 0:
            # nothing to cancell
            return

        for trade in trades_to_cancel:
            try:
                self.api.cancel_order(trade=trade)
                # wait till the order is cancelled.
                # while trade.status.status != "Cancelled":
                #     trade = self.api.update_status(
                #         account=self.api.stock_account)
                self.api.update_status(self.api.stock_account)
                logging.info(
                    f"order cancelled: {trade.contract.code}/{trade.status.status}, cqty {trade.status.cancel_quantity}"
                )
            except Exception as e:
                logging.error(f"Error canceling order {e}")

    # 處理訂單成交的狀況,用來更新交割款
    # order_cb confirmed ok.
    def order_cb(self, stat, msg: Dict):
        # print(f"stat: {stat}, msg:{msg}")
        # OrderState.StockDeal is a dict name
        if stat == OrderState.StockDeal:
            print(f"stk deal: {stat.StockDeal.value}, msg:{msg}")
            # global g_settlement
            code = msg["code"]
            action = msg["action"]
            price = msg["price"]
            quantity = msg["quantity"] * 1000 if msg["order_lot"] == "Common" else msg["quantity"]
            if code in symbols:
                if action == ACTION_BUY:
                    self.bought_price[code] = price
                elif action == ACTION_SELL:
                    self.taken_profit += calculate_profit(
                        buy_price=self.bought_prices[code],
                        sell_price=price,
                        quantity=quantity,
                    )
                # self.msglist.append(msg)
                # s = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logging.info(f"Deal: {action} {code} {quantity} @ {price}")

            # with self.mutexstat:
            #     self.statlist.append(stat)
        elif stat == OrderState.StockOrder:
            # print(f"ord_cb: stat: {stat}, msg:{msg}")
            pass

    def wait_for_orders_to_complete(self, symbols: list) -> None:
        """Wait until all trades for specific symbols are either Filled or Failed."""
        completed_status = ["Filled", "Failed", "Cancelled"]

        while True:
            try:
                self.api.update_status(account=self.api.stock_account)
                tradelist = self.api.list_trades()  # Fetch updated trades list
                # Filter trades only for the given symbols
                relevant_trades = [trade for trade in tradelist if trade.contract.code in symbols]
                for trade in relevant_trades:
                    print(f"{trade.contract.code}/{trade.status.status}")

                # Check if all relevant trades are completed
                if all(trade.status.status in completed_status for trade in relevant_trades):
                    break  # Exit loop if all relevant trades are completed
            except Exception as e:
                logging.error(f"Error checking specific trade statuses: {e}")
                break  # Exit loop in case of API failure or error

            time.sleep(3)
'''

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
    expected_profit = 10
    # fees = 0.385 / 100
    fees = 0.4 / 100
    total_amount = 30000
    weights = misc.pickle_read("weights.pkl")
    betas = misc.pickle_read("betas.pkl")
    # weights = {g_upperid: 0.425652829531973, g_lowerid: 0.5743471704680267}
    mutexDict = {symbols[0]: Lock(), symbols[1]: Lock()}
    cooldown = 15
    # sleep to n seconds
    til_second = 10

    # api = mysj.shioajiLogin(simulation=False)

    bot = mysj.Bot(symbols=symbols, sim=False)

    bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}
    print(bot.pos)
    # todo: maybe just one stock has value, so need to save taken_profit in case not all stocks
    if any(bot.pos.values()):
        # bot.bought_prices = {"2330": 1075, "00664R": 3.72}
        # misc.pickle_dump("bought_prices.pkl", bot.bought_prices)

        bot.bought_prices = misc.pickle_read("bought_prices.pkl")
        print(f"bought price:, {bot.bought_prices}")
        # this is for handling unfilled shares
        bot.shares_to_buy = calculate_allocate(total_amount, bot.bought_prices, weights)

        try:
            while True:  # any(bot.pos.values()):
                # time.sleep(10)
                # -------------------------------------------------------------------------
                # 1. cancel open orders
                bot.cancelOrders()

                # 2. update current positions
                bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}
                if all(value == 0 for value in bot.pos.values()):
                    break

                # 3. fetch latest market snapshots
                bot.snapshots = bot.get_snapshots(symbols)
                [print(f"Close price for {code}: {snapshot.close}") for code, snapshot in bot.snapshots.items()]

                # 4. compute profit
                current_net_profit = sum(
                    misc.calculate_profit(bot.bought_prices[symbol], bot.snapshots[symbol].close, bot.pos[symbol])
                    for symbol in symbols
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
                    time.sleep(30)
                # net profit less than expectattion and no sell transaction has been done, at this point, refill any previsouly buy shortage.
                elif bot.taken_profit == 0:
                    prev_unfilled_shares = {symbol: bot.shares_to_buy[symbol] - bot.pos[symbol] for symbol in symbols}
                    # key_of_zero = next((k for k, v in bot.pos.items() if v == 0), None)
                    # if key_of_zero is not None and bot.taken_profit == 0:
                    # cond1 = bot.snapshots[g_upperid].change_rate < 0 and bot.snapshots[g_lowerid].change_rate <= 0
                    # theory_prices = get_theory_prices(api, symbols=symbols, bot=bot)
                    # cond2 = all(theory_prices[symbol] > bot.snapshots[symbol].close - 2*bot.tick_value[symbol] for symbol in symbols)
                    if any(prev_unfilled_shares.values()):
                        for symbol in symbols:
                            cond1 = prev_unfilled_shares[symbol] > 0
                            # cond2 = bot.snapshots[symbol].change_rate <= 0
                            cond3 = bot.snapshots[symbol].close <= bot.bought_prices[symbol] - bot.tick_value[symbol]
                            if (
                                prev_unfilled_shares[symbol] > 0
                                and bot.snapshots[symbol].close
                                <= bot.bought_prices[symbol] - 2 * bot.tick_value[symbol]
                                and bot.snapshots[symbol].change_rate <= 0
                            ):
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
                    pass
                print("-" * 80)  # Optional separator

            # reconfirm, maybe not necessary
            bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}  # key: value
            print(f"all sold. pos should be 0: {bot.pos}")
        except KeyboardInterrupt:
            print("\n my Ctrl-C detected. Exiting gracefully...")
            # bot.cancelOrders()
            bot.logout()
            exit

    #################################################################################
    # empty hand, ask if want to buy
    elif misc.get_user_confirmation(question="buy"):
        bot.snapshots = bot.get_snapshots()
        bot.shares_to_buy = calculate_allocate(total_amount, bot.snapshots, weights)
        # bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}
        # always break at here to find a good pair of prices before submitting!!!
        # watch for mkt data, 2330 stock price the lower the better when 00664r price fixs!!!
        while True:
            # 1. cancel open orders
            bot.cancelOrders()
            # 2. get snapshots
            bot.snapshots = bot.get_snapshots()
            # 3. get pos
            # bot.pos = {symbol: bot.geyt_position_qty(symbol) for symbol in symbols}

            # for symbol in symbols:
            #     pct_change[symbol] = (bot.snapshots[symbol] - prev_snapshots[symbol]) / prev_snapshots[symbol] * 100
            # prev_snapshots = bot.snapshots.copy()
            # print(f"spread: {pct_change[g_upperid]-pct_change[g_lowerid]}")
            cond1 = bot.snapshots[g_upperid].change_rate < 0 and bot.snapshots[g_lowerid].change_rate <= 0
            theory_prices = bot.get_theory_prices(betas=betas, snapshots=bot.snapshots)
            cond2 = bot.snapshots[g_lowerid].close <= theory_prices[g_lowerid]
            # cond2 = all(
            #     theory_prices[symbol] > bot.snapshots[symbol].close - 2 * bot.tick_value[symbol] for symbol in symbols
            # )
            [print(f"theory: {theory_prices}, snapshots: {bot.snapshots[symbol].close}") for symbol in symbols]
            if cond1 and cond2:
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
                    while not all(trade.status.status == "Filled" for trade in bot.trades.values()):
                        for trade in bot.trades.values():
                            # trade status will be updated automatically
                            bot.api.update_status(bot.api.stock_account, trade=trade)
                            print(f"{trade.contract.code}/{trade.status.status}")
                        time.sleep(20)
                    misc.pickle_dump("bought_prices.pkl", bot.bought_prices)
                    bot.logout
                    break
                except KeyboardInterrupt:
                    print("\n my Ctrl-C detected. Exiting gracefully...")
                    if any(bot.bought_prices.values()):
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
