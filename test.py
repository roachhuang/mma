import time
import shioaji as sj
from shioaji import TickSTKv1, Exchange
from threading import Event
from shioaji.constant import (
    ACTION_BUY,
    ACTION_SELL,
    STOCK_ORDER_LOT_INTRADAY_ODD,
    STOCK_ORDER_LOT_COMMON,
)

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

from ShioajiLogin import shioajiLogin, get_snapshots

api = shioajiLogin(simulation=True)


@api.on_tick_stk_v1()
def quote_callback(exchange: Exchange, tick: TickSTKv1):
    print(f"Exchange: {exchange}, Tick: {tick}")


# api.quote.subscribe(
#     api.Contracts.Stocks["2330"],
#     quote_type=sj.constant.QuoteType.Tick,
#     version=sj.constant.QuoteVersion.v1,
# )


# api.quote.set_on_tick_stk_v1_callback(quote_callback)
# Event().wait()
def place_flexible_order(symbol, price, total_quantity, action):
    # Determine the number of regular lots and odd lot quantity
    regular_lot_qty = total_quantity // 1000  # Regular lots (1 lot = 1000 shares)
    odd_lot_qty = total_quantity % 1000  # Remaining odd lot quantity
    contract = api.Contracts.Stocks[symbol]
    # Place regular lot orders if applicable
    if regular_lot_qty > 0:
        order = api.Order(
            price=price,
            quantity=regular_lot_qty,  # Total quantity in regular lots
            action=action,
            price_type="MKT",
            # price_type="LMT",
            order_type="ROD",
            order_lot=STOCK_ORDER_LOT_COMMON,  # Regular lot
            account=api.stock_account,
        )

        print(
            f"Placed regular lot order for {symbol}: {regular_lot_qty * 1000} shares @{price}"
        )
        # print("status:", trade.status.status)
        return api.place_order(contract, order)
    
    # Place odd lot order if applicable
    elif odd_lot_qty > 0:
        order = api.Order(
            price=price,
            quantity=odd_lot_qty,  # Remaining odd lot quantity
            action=action,
            # price_type="LMT",
            price_type="MKT",
            # order_type="FOK",
            order_type="ROD",
            order_lot=STOCK_ORDER_LOT_INTRADAY_ODD,
            account=api.stock_account,
        )

        print(f"Placed odd lot order for {symbol}: {odd_lot_qty} shares @{price}")
        return api.place_order(contract, order)


def pos(symbol):
    api.update_status(api.stock_account)
    positions = api.list_positions(api.stock_account, unit="Share")
    # Extract the quantity of the specified stock
    return next(
        (position.quantity for position in positions if position.code == symbol),
        0,  # Default to 0 if the stock is not found
    )

g_upperid = "2330"
g_lowerid = "0050"
symbols = [g_upperid, g_lowerid]
qty = {g_upperid: 0, g_lowerid: 0}

pos = {symbol: pos(symbol=symbol) for symbol in symbols}

# qty = 10
# trade = api.place_order(contract, order)
# trade.order.id
orders = {}
trades={}


for symbol in symbols:   
    # print(f"Stock {symbol} bought quantity: {qty[symbol]}")
    if any(pos.values()):
        if pos[symbol] > 0:
            trade = place_flexible_order(
                symbol=symbol, price=100, total_quantity=pos[symbol], action=ACTION_SELL
            )
            trades[symbol] = trade
    else:
        if qty[symbol] > 0:
            trade = place_flexible_order(
                symbol=symbol, price=100, total_quantity=qty[symbol], action=ACTION_BUY
            )
            trades[symbol] = trade
    # orders[symbol] = trade.order.id


while not all(trade.status.status =='Filled' for trade in trades.values()):
    # for symbol in symbols:
    #     api.update_status(api.stock_account, trade=trades[symbol])
    #     print(f'{trades[symbol].contract.code}/{trades[symbol].status.status}')
    for trade in trades.values():
        api.update_status(api.stock_account, trade=trade)
        print(f'{trade.contract.code}/{trade.status.status}')

exit()

cnt = 0
try:
    while True:
        api.update_status(api.stock_account)
        all_orders_filled = True  # Assume all orders are filled initially
        for symbol, order_id in orders.items():
            # order_status = api.list_trades()[-1].status
            trades = api.list_trades()
            trade_status = next(
                (trade.status for trade in trades if trade.order.id == order_id), None
            )
            print(f"{cnt} - Symbol: {symbol}, Order ID: {order_id}, Status: {trade_status}")

            cnt += 1
            # print(f"status: {order_status.status}-{cnt}")

            if trade_status.status not in ["Failed", "Filled"]:
                all_orders_filled = False   # at least one order isn't filled.
            # print(f"Order status: {order_status.status}")  # Debug: Current order status
            # break
        if all_orders_filled == True:
            break   # exit while loop            

        time.sleep(5)

    # Check final statuses
    for symbol, order_id in orders.items():
        trades = api.list_trades()
        for trade in trades:
            if trade.order.id == order_id:
                if trade.status.status == "Filled":
                    print(f"Order for {symbol} has been filled!")
                elif trade.status.status == "Failed":
                    print(f"Order for {symbol} failed to fill!")
                break
    # if order_status.status == "Filled":
    #     # todo: write price to file
    #     print("Order has been filled!")
    # pickle_dump('bought_prices', stockPrice)
    # else:
    # print(f"Order finished with status: {order_status.status}")
    api.logout()


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
