#########################################
# Ch7 網格交易機器人
###########################################
import time
from gridbot import GridBot
# import shioaji.order as stOrder

from typing import Dict, List, Optional
from shioaji.constant import QuoteVersion, QUOTE_TYPE_BIDASK, QUOTE_TYPE_TICK, OrderState, Action, StockOrderCond, QuoteType
import logging
import pickle
import datetime
import time
from threading import Lock
# 處理ticks即時資料更新的部分
from shioaji import BidAskSTKv1, Exchange, TickSTKv1

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
import misc

REBOOT_HOUR = 16
END_WEEKDAY = 4  # Friday

g_upperid = '0052'
g_lowerid = '00662'
ENABLE_PREMARKET = True
ans = ''

def GridbotBody(api):
    # gridBody runs from here
    # 成交價
    snaprice = {}
    snaprice[g_upperid] = api.snapshots([api.Contracts.Stocks[g_upperid]])
    snaprice[g_lowerid] = api.snapshots([api.Contracts.Stocks[g_lowerid]])
    stockPrice = {g_upperid: snaprice[g_upperid][0]['close'],
                  g_lowerid: snaprice[g_lowerid][0]['close']}

    # 最高買價
    stockBid = {g_upperid: snaprice[g_upperid][0]['close'],
                g_lowerid: snaprice[g_lowerid][0]['close']}
    # 最低賣價
    stockAsk = {g_upperid: snaprice[g_upperid][0]['close'],
                g_lowerid: snaprice[g_lowerid][0]['close']}
    # # 最高買價
    # stockBid = {g_upperid: snaprice[g_upperid][0]['buy_price'],
    #             g_lowerid: snaprice[g_lowerid][0]['buy_price']}
    # # 最低賣價
    # stockAsk = {g_upperid: snaprice[g_upperid][0]['sell_price'],
    #             g_lowerid: snaprice[g_lowerid][0]['sell_price']}

    # 創建交易機器人物件
    # logging.basicConfig(filename='gridbotlog.log', level=logging.DEBUG)
    logging.basicConfig(
        filename="gridbot.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )
    # 把資料寫到硬碟和從硬碟讀取資料用的函數
    bot1 = GridBot(api, logging)
    # 更新交易機器人裡的股票數量
    bot1.getPositions()

    try:
        bot1.initmoney = misc.pickle_read('money.p')
    except:
        bot1.initmoney = 0
    totalcapital = bot1.initmoney + \
        stockPrice[g_upperid]*bot1.uppershare + \
        stockPrice[g_lowerid]*bot1.lowershare
    # 更新Trigger大小,在資產很多的時候固定2000會有點少
    bot1.trigger = max(2000, totalcapital*0.005)
    print("init money: {:.2f}".format(bot1.initmoney))
    print("uppershare: {:.2f}".format(stockPrice[g_upperid]*bot1.uppershare))
    print("lowershare: {:.2f}".format(stockPrice[g_lowerid]*bot1.lowershare))
    print("totalcapital: {:.2f}".format(totalcapital))
    # 決定要不要新增更多資金進交易機器人裡, ans won't be '' after 2nd round.
    # here declare ans as global is for updating the global value of ans
    global ans
    if (ans == ''):
        ans = input("perform withdraw or deposit(y/n):\n")
        if (ans == 'y'):
            amount = input(
                "withdraw or deposit amount(>0:deposit,<0:withdraw):\n")
            bot1.initmoney = bot1.initmoney+int(amount)
    bot1.money = bot1.initmoney

    # 用來處理多線程的變數,在更新價格和訂單成交回報時會用到
    # It contains Lock objects associated with identifiers g_upperid and g_lowerid. These locks are used to synchronize
    # access to the dictionaries stockPrice, stockBid, and stockAsk, which are accessed concurrently by multiple threads.
    mutexDict = {g_upperid: Lock(), g_lowerid: Lock()}
    mutexBidAskDict = {g_upperid: Lock(), g_lowerid: Lock()}

    # 告訴系統要訂閱
    # 1.ticks資料(用來看成交價)
    # 2.買賣價資料
    contract_Upper = api.Contracts.Stocks[g_upperid]
    contract_Lower = api.Contracts.Stocks[g_lowerid]
    api.quote.subscribe(contract_Lower, QUOTE_TYPE_TICK, QuoteVersion.v1)
    api.quote.subscribe(contract_Upper, QUOTE_TYPE_TICK, QuoteVersion.v1)
    api.quote.subscribe(contract_Lower, QUOTE_TYPE_BIDASK, QuoteVersion.v1)
    api.quote.subscribe(contract_Upper, QUOTE_TYPE_BIDASK, QuoteVersion.v1)

    @api.on_tick_stk_v1()
    def STKtick_callback(exchange: Exchange, tick: TickSTKv1):
        code = tick['code']
        mutexDict[code].acquire()
        stockPrice[code] = float(tick['close'])
        mutexDict[code].release()
    api.quote.set_on_tick_stk_v1_callback(STKtick_callback)

    # 處理bidask即時資料更新的部分
    @api.on_bidask_stk_v1()
    def STK_BidAsk_callback(exchange: Exchange, bidask: BidAskSTKv1):
        code = bidask['code']
        mutexBidAskDict[code].acquire()
        bidlist = [float(i) for i in bidask['bid_price']]
        asklist = [float(i) for i in bidask['ask_price']]
        stockBid[code] = bidlist[0]
        stockAsk[code] = asklist[0]
        mutexBidAskDict[code].release()
    api.quote.set_on_bidask_stk_v1_callback(STK_BidAsk_callback)

    @api.quote.on_event
    def event_callback(resp_code: int, event_code: int, info: str, event: str):
        # t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")        
        logging.info(f'Event code: {event_code} | Event: {event}')
        # print(f'Event code: {event_code} | Event: {event}')
    api.quote.set_event_callback(event_callback)

    # 用來更新買賣訊號和下單的迴圈
    try:
        while (1):
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
            if (minute % 3 != 0):
                continue
            # cancel all orders 10m before mkt close
            if (hour == 13 and minute > 20):
                try:
                    bot1.cancelOrders()
                except Exception as e:
                    logging.error('jobs_per1min  Error Message A: ' + str(e))
                continue
            # it is allowed to place next-day orders after 3pm.
            if (hour >= 14 and hour <= 15):
                misc.pickle_dump("money.p", bot1.money)
                break
            # if premarket is True, orders can be place out of mkt hrs.
            if (not ENABLE_PREMARKET):
                if (hour < 9 or (hour > 13)):
                    continue

            # 處理成交價不在買賣價中間的狀況
            # Acquires the lock associated with the resource identified by g_upperid in the mutexDict dictionary.
            # This lock is used to synchronize access to some shared resource related to g_upperid.
            mutexDict[g_upperid].acquire()
            mutexDict[g_lowerid].acquire()
            mutexBidAskDict[g_upperid].acquire()
            mutexBidAskDict[g_lowerid].acquire()

            if (stockPrice[g_upperid] > stockAsk[g_upperid] or stockPrice[g_upperid] < stockBid[g_upperid]):
                stockPrice[g_upperid] = (
                    stockAsk[g_upperid]+stockBid[g_upperid])/2
            if (stockPrice[g_lowerid] > stockAsk[g_lowerid] or stockPrice[g_lowerid] < stockBid[g_lowerid]):
                stockPrice[g_lowerid] = (
                    stockAsk[g_lowerid]+stockBid[g_lowerid])/2

            # save prices to gridbot
            bot1.stockPrice[g_upperid] = stockPrice[g_upperid]
            bot1.stockPrice[g_lowerid] = stockPrice[g_lowerid]
            bot1.stockBid[g_upperid] = stockBid[g_upperid]
            bot1.stockBid[g_lowerid] = stockBid[g_lowerid]
            bot1.stockAsk[g_upperid] = stockAsk[g_upperid]
            bot1.stockAsk[g_lowerid] = stockAsk[g_lowerid]
            mutexDict[g_lowerid].release()
            mutexDict[g_upperid].release()
            mutexBidAskDict[g_lowerid].release()
            mutexBidAskDict[g_upperid].release()
            
            # 更新買賣單, we can place order anytime before 2pm
            bot1.updateOrder()

    except KeyboardInterrupt:
        print("\n my Ctrl-C detected. Exiting gracefully...")
        bot1.cancelOrders()
        misc.pickle_dump("money.p", bot1.money)
        try:
            api.logout()
        except Exception as e:
            print("An error occurred:", e)
        finally:
            print(
                "This code is always executed, regardless of whether an exception occurred or not")
        print('end')
        exit

# start here


def main():
    api = shioajiLogin(simulation=True)
    # starting point of the code running 
    GridbotBody(api)
    
        # after 14:00, goes here
    while (1):
        # check reboot once per 30 minutes
        current_time = time.time()

        # current_time % cooldown calculates the time elapsed since the start of the current 30-minute interval.
        cooldown = 60*30
        # cooldown - (current_time % cooldown) determines the remaining time until the next 30-minute mark.
        time_to_sleep = cooldown - (current_time % cooldown)        
        time.sleep(time_to_sleep)

        # check weekday and n
        now = datetime.datetime.now()
        hour = now.hour
        weekday = now.weekday()
        print('hour:', hour)
        # check if hour == REBOOT_HOUR every 30m mark, e.g., at 10:30, 11:00, 11:30
        # relogin to mma every 16 hrs, coz it is reqeusted by mma
        if (hour == REBOOT_HOUR):
            print('reboot bot')
            api.logout()

            api = shioajiLogin(simulation=False)
            GridbotBody(api)
            # goes here after 14:00
        # friday
        if (END_WEEKDAY == weekday):
            break


if __name__ == '__main__':
    main()
