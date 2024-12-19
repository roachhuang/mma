import time
import shioaji.order as stOrder

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
import datetime
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

from ShioajiLogin import shioajiLogin, get_snapshots
import misc

# def process_final_order_status(bot, orders):
#     """Process the final statuses of all orders."""
#     filled_orders = []
#     for symbol, order_id in orders.items():
#         status = bot.get_order_status(order_id)
#         if status == "Filled":
#             print(f"Order for {symbol} has been filled!")
#             filled_orders.append(symbol)
#         elif status == "Failed":
#             print(f"Order for {symbol} failed to fill!")
#     return filled_orders


def get_tick_unit(stock_price: float) -> float:
    """
    Returns the fluctuation unit (TICK) for the given stock price.

    Args:
        stock_price (float): The current stock price.

    Returns:
        float: The TICK value for the stock price.
    """
    if stock_price < 10:
        return 0.01
    elif stock_price < 50:
        return 0.05
    elif stock_price < 100:
        return 0.1
    elif stock_price < 500:
        return 0.5
    elif stock_price < 1000:
        return 1.0
    else:
        return 5.0


def calculate_allocate(total_money, snapshots, weights):
    g_lowerid_shares = int(total_money * weights[g_lowerid] // snapshots[g_lowerid])
    # Adjust shares of the fixed stock to be a multiple of 1000
    g_lowerid_shares = (g_lowerid_shares // 1000) * 1000
    g_lowerid_cost = g_lowerid_shares * snapshots[g_lowerid]

    # Calculate the scale factor to maintain the same weights
    scale_factor = g_lowerid_cost / (total_money * weights[g_lowerid])
    scaled_total_money = total_money * scale_factor

    # Reallocate money based on scaled total money and original weights
    g_upperid_shares = int(
        scaled_total_money * weights[g_upperid] // snapshots[g_upperid]
    )
    return {
        g_upperid: g_upperid_shares,
        g_lowerid: g_lowerid_shares,
    }


def calculate_profit(buy_price: float, sell_price: float, quantity: int) -> int:    
    # break even: 0.208% after discount
    discount = 0.38
    service_fee = float(0.001425 * discount)
    tax = 0.001

    """Calculates the net profit from a stock transaction.
    股價               TICK股價升降單位
    每股市價未滿10元	0.01元
    10元至未滿50元	    0.05元
    50元至未滿100元	    0.1元
    100元至未滿500元	0.5元
    500元至未滿1000元	1元
    1000元以上	        5元
    Args:
        buy_price (float): The purchase price per share.
        sell_price (float): The selling price per share.
        quantity (int): The number of shares.
    Returns:
        float: The net profit from the transaction.
    """
    total_cost = round(quantity * buy_price * (1 + discount * service_fee))
    total_proceeds = round(quantity * sell_price)
    total_fees = round(total_proceeds * (service_fee + tax))
    net_profit = total_proceeds - total_cost - total_fees

    return net_profit


class GridBot:
    """
    passing in api for
    Dependency Injection: This promotes loose coupling between classes, making the Bot class more reusable and testable.
    """

    def __init__(self, api, logging: logging.Logger):
        # self.stockPrice = {upperId: 0, lowerId: 0}
        # self.stockPrice = {}
        self.msglist = []
        self.statlist = []
        self.bought_price = {}
        self.sell_price = {}
        self.pos = []
        self.trades = {}
        self.taken_profit = 0
        self.deal_cnt = 0
        self.mutexmsg = Lock()
        self.mutexstat = Lock()
        self.api = api
        self.logging = logging
        self.api.set_order_callback(self.order_cb)

    def get_position_qty(self, symbol)->int:
        try:
            positions = self.api.list_positions(self.api.stock_account, unit=sj.constant.Unit.Share)        
            for pos in positions:
                if pos.code == symbol:
                    return pos.quantity       
            return 0    # default to 0 if the stock is not found
        except sj.error.TokenError as e:
            self.logging.error(f"Token error: {e.detail}")
            return 0

    def buy(self, symbol, price, quantity):
        return self.place_flexible_order(
            symbol=symbol, action=ACTION_BUY, price=price, qty=quantity
        )

    def sell(self, symbol, price, quantity):
        return self.place_flexible_order(
            symbol=symbol, action=ACTION_SELL, price=price, qty=quantity
        )

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
            print(
                f"Placed regular lot {action} order for {symbol}: {common_lot_qty} lot(s) @{price}"
            )
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
            print(
                f"Placed odd lot {action} order for {symbol}: {odd_lot_qty} shares @{price}"
            )
        # log the most crucial info for record
        self.logging.info(f"trade: {trade}")
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
                self.logging.info(
                    f"order cancelled: {trade.contract.code}/{trade.status.status}, cqty {trade.status.cancel_quantity}"
                )
            except Exception as e:
                self.logging.error(f"Error canceling order {e}")

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
            quantity = msg["quantity"]
            if code in symbols:
                if action == ACTION_BUY:
                    self.bought_price[code] = price
                elif action == ACTION_SELL:
                    self.taken_profit += calculate_profit(
                        buy_price=self.bought_price[code],
                        sell_price=price,
                        quantity=quantity,
                    )
                # self.deal_cnt += 1

                # self.msglist.append(msg)
                # s = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.logging.info(f"Deal: {action} {code} {quantity} @ {price}")

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
                relevant_trades = [
                    trade for trade in tradelist if trade.contract.code in symbols
                ]
                for trade in relevant_trades:
                    print(f"{trade.contract.code}/{trade.status.status}")

                # Check if all relevant trades are completed
                if all(
                    trade.status.status in completed_status for trade in relevant_trades
                ):
                    break  # Exit loop if all relevant trades are completed
            except Exception as e:
                self.logging.error(f"Error checking specific trade statuses: {e}")
                break  # Exit loop in case of API failure or error

            time.sleep(3)


# shares_to_buy = {g_upperid: 0, g_lowerid: 0}

#######################################################################################################################
#######################################################################################################################
# main fn
########################################################################################################################
########################################################################################################################

g_upperid = "2330"
# g_upperid = "0052"
g_lowerid = "00664R"
symbols = [g_upperid, g_lowerid]


def main():
    dynamic_sell_threshold = 60
    # fees = 0.385 / 100
    fees = 0.4 / 100
    total_amount = 30000

    # weights = {g_upperid: 0.46772408, g_lowerid: 0.53227592}
    weights = {g_upperid: 0.425652829531973, g_lowerid: 0.5743471704680267}
    mutexDict = {symbols[0]: Lock(), symbols[1]: Lock()}
    cooldown = 15
    # sleep to n seconds
    til_second = 10

    api = shioajiLogin(simulation=False)

    # 創建交易機器人物件
    logging.basicConfig(
        filename="capm_zero_beta.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",  # auto insert current time, and logging level, just as INFO, DEBUG...
    )

    bot = GridBot(api, logging)

    bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}
    print(bot.pos)
    # todo: maybe just one stock has value, so need to save taken_profit in case not all stocks
    if any(bot.pos.values()):
        # bought_prices.p should be located on folder mma_shioaji_GridBot
        bot.bought_price = misc.pickle_read("bought_prices")
        print("bought price:", bot.bought_price)
        bot.taken_profit = 174
        try:
            while any(bot.pos.values()):
                # time.sleep(10)
                # -------------------------------------------------------------------------
                # 1. cancel open orders
                bot.cancelOrders()

                # 2. update current positions
                bot.pos = {symbol: bot.get_position_qty(symbol) for symbol in symbols}
                if all(value == 0 for value in bot.pos.values()):
                    break

                # 3. fetch latest market snapshots
                snapshots = get_snapshots(api, symbols)
                print(f"snapshots:, {snapshots}, pos: {bot.pos}")

                # 4. 算profit
                net_profit = sum(
                    calculate_profit(
                        bot.bought_price[symbol], snapshots[symbol], bot.pos[symbol]
                    )
                    for symbol in symbols
                )
                print(f"net profit: {net_profit} / taken profit: {bot.taken_profit}")

                # todo: if partial filled, net_profit should be recalucated!!!
                if net_profit >= dynamic_sell_threshold - bot.taken_profit:
                    # 3.掛單
                    for symbol in symbols:
                        if bot.pos[symbol] > 0:
                            bot.trades[symbol] = bot.sell(
                                symbol=symbol,
                                quantity=bot.pos[symbol],
                                price=snapshots[symbol],
                            )
                    time.sleep(30)
                    
                current_time = time.time()
                time_to_sleep = cooldown - (current_time % cooldown) + til_second
                # sleep between 20 second to 80 second, should be wait till fully filled.
                time.sleep(time_to_sleep)

                now = datetime.datetime.now()
                # every 3 minutes
                if now.minute % 3 == 0:
                    pass    
                print("-" * 80)  # Optional separator
            # reconfirm, maybe not necessary
            bot.pos = {
                symbol: bot.get_position_qty(symbol) for symbol in symbols
            }  # key: value
            print(f"all sold. pos should be 0: {bot.pos}")
        except KeyboardInterrupt:
            print("\n my Ctrl-C detected. Exiting gracefully...")
            # bot.cancelOrders()
            try:
                api.logout()
            except Exception as e:
                print("An error occurred:", e)
            finally:
                print(
                    "This code is always executed, regardless of whether an exception occurred or not"
                )
            print("end")
            exit

    #################################################################################
    # empty hand, ask if want to buy
    elif misc.get_user_confirmation(question="buy"):
        snapshots = get_snapshots(api, symbols)
        shares_to_buy = calculate_allocate(total_amount, snapshots, weights)

        print(f"shares_to_buy:{shares_to_buy}, @price {snapshots}")

        # always break at here to find a good pair of prices before submitting!!!
        # watch for mkt data, 2330 stock price the lower the better when 00664r price fixs!!!
        for symbol in symbols:
            bot.trades[symbol] = bot.buy(
                symbol=symbol,
                quantity=shares_to_buy[symbol],
                price=snapshots[symbol],
            )

        try:
            while not all(
                trade.status.status == "Filled" for trade in bot.trades.values()
            ):
                for trade in bot.trades.values():
                    # trade status will be updated automatically
                    api.update_status(api.stock_account, trade=trade)
                    print(f"{trade.contract.code}/{trade.status.status}")

            misc.pickle_dump("bought_prices", snapshots)
            api.logout

        except KeyboardInterrupt:
            print("\n my Ctrl-C detected. Exiting gracefully...")
            api.logout()
            exit()

    else:
        print("END: empty-handed and do nothing.")
        api.logout()


if __name__ == "__main__":
    main()
