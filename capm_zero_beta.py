import pickle
import time

import pandas as pd
import shioaji.order as stOrder
import shioaji.shioaji
from typing import Dict, List, Optional
from shioaji.constant import (
    OrderState,
    ACTION_BUY,
    ACTION_SELL,
    StockOrderCond,
    STOCK_ORDER_LOT_INTRADAY_ODD,
    STOCK_ORDER_LOT_COMMON,
)
from shioaji.constant import (
    QuoteVersion,
    QUOTE_TYPE_BIDASK,
    QUOTE_TYPE_TICK,
    OrderState,
    Action,
    StockOrderCond,
    QuoteType,
)
import logging
import datetime
from threading import Lock

####################################################
import os
import sys

# Get the user's home directory path
home_dir = os.path.expanduser("~")
# Construct the path to get_data.py
helpers_dir = os.path.join(home_dir, "projects/helpers")
# Add the helper directory to sys.path (optional, but recommended for absolute paths)
if helpers_dir not in sys.path:
    sys.path.append(helpers_dir)
######################################################
from ShioajiLogin import shioajiLogin

# 處理ticks即時資料更新的部分
from shioaji import BidAskSTKv1, Exchange, TickSTKv1


def pickle_dump(filename, obj):
    with open(filename, "wb") as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)


def pickle_read(filename):
    with open(filename, "rb") as handle:
        return pickle.load(handle)


class GridBot:
    # stockPrice: object
    api: shioaji.Shioaji
    mutexgSettle: any
    mutexmsg: any
    mutexstat: any
    statlist: List
    msglist: List

    def __init__(self, api: shioaji.Shioaji, logging):
        # self.stockPrice = {upperId: 0, lowerId: 0}
        # self.stockPrice = {}
        self.msglist = []
        self.statlist = []
        self.mutexgSettle = Lock()
        self.mutexmsg = Lock()
        self.mutexstat = Lock()
        self.api = api
        self.logging = logging
        # self.api.set_order_callback(self.order_cb)

    def get_position_qty(self, symbol):
        self.api.update_status(self.api.stock_account)
        positions = self.api.list_positions(self.api.stock_account, unit="Share")
        quantity = next(
            (position.quantity for position in positions if position.code == symbol),
            0,  # Default to 0 if the stock is not found
        )
        return quantity

        df_positions = pd.DataFrame(s.__dict__ for s in positions)

        position = df_positions[df_positions["code"] == symbol]
        if position.empty:
            return 0
        else:
            return int(position["quantity"].values[0])

    # # def sendOrders(self, symbol, direction, order_lot, price, quantity: int):
    # def sendOrder(self, symbol, action, price, quantity: int):
    #     if quantity > 0 and price > 0:
    #         contract = self.api.Contracts.Stocks[symbol]
    #         # contract.reference = the previous day's closing price.
    #         order = self.api.Order(
    #             price=price,
    #             quantity=quantity,
    #             action=action,
    #             price_type=shioaji.constant.StockPriceType.LMT,
    #             order_type=shioaji.constant.OrderType.ROD,
    #             # order_lot=order_lot,
    #             account=self.api.stock_account,
    #         )

    #         trade = self.api.place_order(contract, order)
    #         # print("status:", trade.status.status)
    #         s = str(datetime.datetime.now())
    #         s = f"{s}- {action}, {contract.code}@ {order.price}, qty: {order.quantity}"
    #         self.logging.info(s)

    def place_flexible_order(self, symbol, price, total_quantity, action):
        # Determine the number of regular lots and odd lot quantity
        regular_lot_qty = total_quantity // 1000  # Regular lots (1 lot = 1000 shares)
        odd_lot_qty = total_quantity % 1000  # Remaining odd lot quantity
        contract = self.api.Contracts.Stocks[symbol]
        # Place regular lot orders if applicable
        if regular_lot_qty > 0:
            order = self.api.Order(
                price=price,
                quantity=regular_lot_qty,  # Total quantity in regular lots
                action=action,
                price_type="MKT",
                # price_type="LMT",
                order_type="FOK",
                order_lot=STOCK_ORDER_LOT_COMMON,  # Regular lot
                account=self.api.stock_account,
            )
            trade = self.api.place_order(contract, order)
            print(
                f"Placed regular lot order for {symbol}: {regular_lot_qty * 1000} shares @{price}"
            )
            print("status:", trade.status.status)
        # Place odd lot order if applicable
        elif odd_lot_qty > 0:
            order = self.api.Order(
                price=price,
                quantity=odd_lot_qty,  # Remaining odd lot quantity
                action=action,
                # price_type="LMT",
                price_type="MKT",
                order_type="FOK",
                # order_type="ROD",
                order_lot=STOCK_ORDER_LOT_INTRADAY_ODD,
                account=self.api.stock_account,
            )
            trade = self.api.place_order(contract, order)
            print(f"Placed odd lot order for {symbol}: {odd_lot_qty} shares @{price}")        
        t = str(datetime.datetime.now())
        self.logging.info(f'{t}-{trade}')               
        return trade
        # print("status:", trade.status.status)

    # 處理訂單成交的狀況,用來更新交割款
    def order_cb(self, stat: OrderState, msg: Dict):
        # print(f"stat: {stat}, msg:{msg}")
        # OrderState.StockDeal is only a const, not an object. so as stat is also just a const
        if stat == OrderState.StockDeal:
            code = msg["code"]
            if code in symbols:
                print(f"stk deal: {stat.StockDeal.value}, msg:{msg}")
                # global g_settlement
                action = msg["action"]
                price = msg["price"]
                quantity = msg["quantity"]
                self.mutexmsg.acquire()
                try:
                    # self.msglist.append(msg)
                    s = str(datetime.datetime.now())
                    self.logging.info(f"deal {s}: {action} {code} {quantity} @ {price}")
                except Exception as e:  # work on python 3.x
                    self.logging.error("place_cb  Error Message A: " + str(e))
                self.mutexmsg.release()
                self.mutexstat.acquire()
                try:
                    self.statlist.append(stat)
                    # self.logging.info(self.statlist)
                except Exception as e:  # work on python 3.x
                    self.logging.error("place_cb  Error Message B: " + str(e))
                self.mutexstat.release()

g_upperid = "0052"
g_lowerid = "00664R"
symbols = [g_upperid, g_lowerid]

def main():
    def allocate_shares(total_money, stock_prices, weights):
        g_lowerid_shares = int(
            total_money * weights[g_lowerid] // stock_prices[g_lowerid]
        )
        # Adjust shares of the fixed stock to be a multiple of 1000
        g_lowerid_shares = (g_lowerid_shares // 1000) * 1000
        g_lowerid_cost = g_lowerid_shares * stock_prices[g_lowerid]

        # Calculate the scale factor to maintain the same weights
        scale_factor = g_lowerid_cost / (total_money * weights[g_lowerid])
        scaled_total_money = total_money * scale_factor

        # Reallocate money based on scaled total money and original weights
        g_upperid_shares = (
            int(scaled_total_money * weights[g_upperid]) // stock_prices[g_upperid]
        )
        return {
            g_upperid: g_upperid_shares,
            g_lowerid: g_lowerid_shares,
        }

    def get_user_confirmation():
        while True:
            user_input = input("capm_zero buy (y/n): ").lower()
            if user_input == "y":
                return True
            elif user_input == "n":
                return False
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    def calculate_profit(buy_price, sell_price, quantity):
        # break even: 0.208% after discount
        discount = 0.38
        service_fee = float(0.001425 * discount)
        tax = 0.001

        """Calculates the net profit from a stock transaction.
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

    # fees = 0.385 / 100
    fees = 0.4 / 100
    REBOOT_HOUR = 16
    END_WEEKDAY = 4  # Friday

    mutexDict = {symbols[0]: Lock(), symbols[1]: Lock()}

    api = shioajiLogin(simulation=True)

    # api.Order()

    # 創建交易機器人物件
    logging.basicConfig(filename="capm_zero_beta.log", level=logging.DEBUG)
    bot = GridBot(api, logging)

    @api.quote.on_event
    def event_callback(resp_code: int, event_code: int, info: str, event: str):
        s = str(datetime.datetime.now())
        s = s + f"Event code: {event_code} | Event: {event}"
        logging.info(s)
        # print(f'Event code: {event_code} | Event: {event}')

    api.quote.set_event_callback(event_callback)

    # @api.on_tick_stk_v1()
    # def quote_callback(exchange: Exchange, tick: TickSTKv1):
    #     print(f"Exchange: {exchange}, Tick: {tick}")
    #     code = tick["code"]
    #     # s = str(datetime.datetime.now())
    #     # s = s + f'symbol: {code}, price: {tick["close"]}'
    #     # logging.info(s)
    #     mutexDict[code].acquire()
    #     bot.stockPrice[code] = float(tick["close"])
    #     mutexDict[code].release()

    # api.quote.set_on_tick_stk_v1_callback(quote_callback)
    # 更新交易機器人裡的股票數量
    # contract_Upper = api.Contracts.Stocks[g_upperid]
    # contract_Lower = api.Contracts.Stocks[g_lowerid]
    # api.quote.subscribe(bot.contractLower, QUOTE_TYPE_TICK, QuoteVersion.v1)
    # api.quote.subscribe(contract_Upper, quote_type="tick")
    # api.quote.subscribe(contract_Lower, QUOTE_TYPE_TICK, version=QuoteVersion.v1)
    today_profit=0
    qty = {}
    for symbol in symbols:
        qty[symbol] = bot.get_position_qty(symbol)
    # qty["00664R"] = qty["00664R"] - 2000
    print(qty)
    # bought_price_dic = {g_upperid: 185.62, g_lowerid: 3.77}
    try:
        bought_price_dic = pickle_read("bought_price")
    except:
        bought_price_dic = {g_upperid: 185.62, g_lowerid: 3.77}
    try:
        while any(value > 0 for value in qty.values()):
            current_time = time.time()
            # 60secs
            cooldown = 60
            # sleep to n seconds
            til_second = 20
            time_to_sleep = til_second + cooldown - (current_time % cooldown)
            time.sleep(time_to_sleep)

            now = datetime.datetime.now()
            hour = now.hour
            minute = now.minute
            # second = now.second
            # modify/send order
            # 1.every 3 minutes
            # 2.between 15 second to 45 second
            if minute % 3 != 0:
                continue

            # -------------------------------------------------------------------------
            # 1.刪除掛單
            # bot.cancelOrders()
            # 2.更新庫存
            qty = {}
            for symbol in symbols:
                qty[symbol] = bot.get_position_qty(symbol)
            # qty["00664R"] = qty["00664R"] - 2000
            print(qty)
            # 4.掛單
            snapshots = bot.api.snapshots([contract_Lower, contract_Upper])
            for snapshot in snapshots:
                stockPrice[snapshot.code] = snapshot.close
            net_profit = 0
            
            for symbol in symbols:
                net_profit += calculate_profit(
                    bought_price_dic[symbol], stockPrice[symbol], qty[symbol]
                )

            print(f'net profit:, {net_profit}')
            if net_profit >= 100:
                today_profit+=net_profit
                print(f"today profit: {today_profit}")
                orders = place_orders(bot, symbols, qty, stockPrice, action=ACTION_SELL)
                
                # bot.api.update_status(bot.api.stock_account)
                # print(f"status: {bot.api.list_trades()[-1].status}")

    except KeyboardInterrupt:
        print("\n my Ctrl-C detected. Exiting gracefully...")
        # bot.cancelOrders()

        # pickle_dump("money.p", bot1.money)
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
    # code goes here if we're empty-handed.

    def get_order_status(bot, order_id):
        """Retrieve the status of an order by its ID."""
        for trade in bot.api.list_trades():
            if trade.order.id == order_id:
                return trade.status.status
        return None  # Return None if the order ID is not found

    def wait_for_orders_to_complete(bot, orders):
        """Wait until all orders are either Filled or Failed."""
        while True:
            bot.api.update_status(bot.api.stock_account)
            all_orders_complete = True

            for symbol, order_id in orders.items():
                status = get_order_status(bot, order_id)
                print(f"Symbol: {symbol}, Order ID: {order_id}, Status: {status}")

                if status not in ["Filled", "Failed"]:
                    all_orders_complete = False

            if all_orders_complete:
                break

            time.sleep(3)

    def process_final_order_status(bot, orders):
        """Process the final statuses of all orders."""
        filled_orders = []
        for symbol, order_id in orders.items():
            status = get_order_status(bot, order_id)
            if status == "Filled":
                print(f"Order for {symbol} has been filled!")
                filled_orders.append(symbol)
            elif status == "Failed":
                print(f"Order for {symbol} failed to fill!")
        return filled_orders

    def place_orders(bot, symbols, shares_to_buy, stock_price, action):
        """Place orders for all symbols and return a dictionary of order IDs."""
        orders = {}
        for symbol in symbols:
            trade = bot.place_flexible_order(
                symbol=symbol,
                action=action,
                price=stock_price[symbol],
                total_quantity=int(shares_to_buy[symbol]),
            )
            orders[symbol] = trade.order.id
        return orders

    # empty hand, ask if want to buy
    if get_user_confirmation():      
        snapshots = api.snapshots([contract_Lower, contract_Upper])
        for snapshot in snapshots:
            stockPrice[snapshot.code] = snapshot.close

        # Example usage:
        total_amount = 10000
        weights = {g_upperid: 0.46855829, g_lowerid: 0.531441716}

        shares_to_buy = allocate_shares(total_amount, stockPrice, weights)
        print(f'shares_to_buy:{shares_to_buy}')

        try:
            # Step 1: Place orders
            orders = place_orders(bot, symbols, shares_to_buy, stockPrice, action=ACTION_BUY)
            
            # Step 2: Wait for orders to complete
            wait_for_orders_to_complete(bot, orders)
            # Step 3: Process final order statuses
            filled_orders = process_final_order_status(bot, orders)

            # Step 4: Save the prices of filled orders
            if filled_orders:
                prices_to_save = {symbol: stockPrice[symbol] for symbol in filled_orders}
                pickle_dump("bought_prices", prices_to_save)                        
            bot.api.logout
        except KeyboardInterrupt:
            print("\n my Ctrl-C detected. Exiting gracefully...")
            api.logout()
            exit()

    else:
        print("END: empty-handed and do nothing.")
        bot.api.logout()


if __name__ == "__main__":
    main()
