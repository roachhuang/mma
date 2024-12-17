# -*- coding: utf-8 -*-
"""
Created on Tue Feb 22 20:55:00 2022

@author: user
"""

import talib
from ShioajiLogin import shioajiLogin
import matplotlib.pyplot as plt
import pandas as pd
import numpy
import backtesttool
import mykbar as kbar

# 從資料庫讀取小型台指歷史資料
# df_MXFR1 = kbar.readFromDB('kbar', 'MXFR1')
# df_MXFR1 = kbar.resampleKbars(df_MXFR1, period='1h')
# close = df_MXFR1['Close']
# high = df_MXFR1['High']
# low = df_MXFR1['Low']
df_MXFR1 = pd.DataFrame()
close = high = low = []

# 選項:
# 'MACD'
# 'KD'
# 'RSI'
# 'BBAND'
# 'PriceChannel'
# 'Grid'
target = "MACD"


#########################################
# 5.1 MACD指標
###########################################
# 製作MACD指標
# macd:快線,12日均線(EMA)-26日均線(EMA)
# macdsignal:慢線,快線的九天平均(EMA)
# macdhist:MACD柱,快線-慢縣
macd, macdsignal, macdhist = talib.MACD(
    close, fastperiod=12, slowperiod=26, signalperiod=9)

if (target == 'MACD'):
    ma_short = talib.EMA(close, 12)
    ma_long = talib.EMA(close, 26)
    plt.title('EMA(12)-EMA(26)')
    plt.plot((ma_short-ma_long)[-100:-1], color='green')
    plt.show()
    plt.title('macd')
    plt.plot(macd[-100:-1], color='green')
    plt.show()
    plt.title('macd-macdsignal')
    plt.plot((macd-macdsignal)[-100:-1], color='green')
    plt.show()
    plt.title('macdhist')
    plt.plot(macdhist[-100:-1], color='green')
    plt.show()
# 使用快慢線交叉當作買賣訊號


def createSignalMACD(close,
                     periodFast,
                     periodSlow,
                     periodSignal):
    macd, macdsignal, macdhist = talib.MACD(
        close, fastperiod=periodFast, slowperiod=periodSlow, signalperiod=periodSignal)
    ENABLESHORT = False
    # 允許放空的訊號寫法
    if (ENABLESHORT):
        BuySignal = (macdhist > 0).astype(int)
        ShortSignal = (macdhist < 0).astype(int)
        return BuySignal-ShortSignal
    # 不允許放空的訊號寫法，兩個差在允許放空的部分多了ShortSignal
    else:
        BuySignal = (macdhist > 0).astype(int)
        return BuySignal
# 找出MACD買賣訊號的最佳化參數


def OptimizeMACD(
        df,
        rangeFast,  # =numpy.arange(2,100,1,dtype=int)
        rangeSlow,  # =numpy.arange(2,100,1,dtype=int)
        rangeSignal  # =numpy.arange(2,100,1,dtype=int)
):

    openPrice = df['Open']
    closePrice = df['Close']
    bestret = 0
    bestret_series = []
    bestperiodFast = 0
    bestperiodSlow = 0
    bestperiodSignal = 0
    for periodFast in rangeFast:
        for periodSlow in rangeSlow:
            for periodSignal in rangeSignal:
                print("periodFast:"+str(periodFast))
                print("periodSlow:"+str(periodSlow))
                print("periodSignal:"+str(periodSignal))
                # 錯誤檢查,快線週期要比慢線短
                if (periodFast >= periodSlow):
                    continue
                # 製作買賣訊號
                BuySignal = createSignalMACD(closePrice,
                                             periodFast,
                                             periodSlow,
                                             periodSignal)
                # 對訊號進行回測
                retStrategy, ret_series = backtesttool.backtest_signal(
                    openPrice, BuySignal)
                # 如果結果比之前更好,就記錄下來
                if (bestret < retStrategy):
                    bestret = retStrategy
                    bestret_series = ret_series
                    bestperiodFast = periodFast
                    bestperiodSlow = periodSlow
                    bestperiodSignal = periodSignal

    return bestret, bestret_series, (bestperiodFast, bestperiodSlow, bestperiodSignal)


if (target == 'MACD'):
    # 最佳化Fast,Slow,Signal
    rangeFast = numpy.arange(2, 100, 1, dtype=int)
    rangeSlow = numpy.arange(2, 100, 1, dtype=int)
    rangeSignal = numpy.arange(2, 100, 1, dtype=int)
    bestret, bestret_series, parameters = OptimizeMACD(
        df_MXFR1,
        rangeFast,  # =numpy.arange(2,100,1,dtype=int)
        rangeSlow,  # =numpy.arange(2,100,1,dtype=int)
        rangeSignal  # =numpy.arange(2,100,1,dtype=int)
    )
    print('MACD bestret:'+str(bestret))
    print('MACD MDD:'+str(backtesttool.calculateMDD(bestret_series)))

    plt.plot(numpy.log10(
        backtesttool.prefixProd(bestret_series)), color='green')
    plt.title('MACD Profit(log)')
    plt.show()
    
"""
#########################################
# 5.2 KD指標
###########################################

# 裡面的參數是預設值,如果把fastk_period的數值改成9就是坊間使用的KD指標設定
# RSV線:(收盤價-最近a天最低價)/(最近a天最高價-最近a天最低價), a=fastk_period
# slowk為K值=k天RSV平均,b=slowk_period
# slowd為D值=d天slowk平均,c=slowd_period
# K往上穿越D為黃金交叉,做多
# K往下穿越D為死亡交叉,做空
slowk, slowd = talib.STOCH(high, low, close,
                           fastk_period=5,
                           slowk_period=3,
                           slowk_matype=talib.MA_Type.SMA,
                           slowd_period=3,
                           slowd_matype=talib.MA_Type.SMA
                           )

if (target == 'KD'):
    rollingHigh = high.rolling(5).max()
    rollingLow = low.rolling(5).min()
    RSV = (close-rollingLow)/(rollingHigh-rollingLow)
    plt.plot(talib.SMA(RSV, 3)[-100:-1])
    plt.title('SMA(RSV,3)')
    plt.show()
    plt.plot(slowk[-100:-1])
    plt.title('slowk')
    plt.show()
    plt.plot(talib.SMA(slowk, 3)[-100:-1])
    plt.title('SMA(slowk,3)')
    plt.show()
    plt.plot(slowd[-100:-1])
    plt.title('slowd')
    plt.show()
    plt.plot((slowk-slowd)[-100:-1])
    plt.title('KD signal(slowk-slowd)')
    plt.show()
# 使用KD交叉當作買賣訊號


def createSignalKD(high, low, close,
                   fastk=5,
                   slowk=3,
                   slowd=3):
    slowk, slowd = talib.STOCH(high, low, close,
                               fastk_period=fastk,
                               slowk_period=slowk,
                               slowk_matype=talib.MA_Type.SMA,
                               slowd_period=slowd,
                               slowd_matype=talib.MA_Type.SMA
                               )
    ENABLESHORT = False
    # 允許放空的訊號寫法
    if (ENABLESHORT):
        BuySignal = (slowk > slowd).astype(int)
        ShortSignal = (slowk < slowd).astype(int)
        return BuySignal-ShortSignal
    # 不允許放空的訊號寫法，兩個差在允許放空的部分多了ShortSignal
    else:
        BuySignal = (slowk > slowd).astype(int)
        return BuySignal
# 找出KD買賣訊號的最佳化參數


def OptimizeKD(
        df,
        range_fastk,  # =numpy.arange(2,100,1,dtype=int)
        range_slowk,  # =numpy.arange(2,100,1,dtype=int)
        range_slowd  # =numpy.arange(2,100,1,dtype=int)
):

    openPrice = df['Open']
    closePrice = df['Close']
    highPrice = df['High']
    lowPrice = df['Low']
    bestret = 0
    bestret_series = []
    best_fastk = 0
    best_slowk = 0
    best_slowd = 0
    for fastk in range_fastk:
        for slowk in range_slowk:
            for slowd in range_slowd:
                print("fastk:"+str(fastk))
                print("slowk:"+str(slowk))
                print("slowd:"+str(slowd))

                # 製作買賣訊號
                BuySignal = createSignalKD(highPrice, lowPrice, closePrice,
                                           fastk,
                                           slowk,
                                           slowd)
                # 對訊號進行回測
                retStrategy, ret_series = backtesttool.backtest_signal(
                    openPrice, BuySignal)
                # 如果結果比之前更好,就記錄下來
                if (bestret < retStrategy):
                    bestret = retStrategy
                    bestret_series = ret_series
                    best_fastk = fastk
                    best_slowk = slowk
                    best_slowd = slowd

    return bestret, bestret_series, (best_fastk, best_slowk, best_slowd)


if (target == 'KD'):
    # 最佳化fastk,slowk,slowd
    range_fastk = numpy.arange(2, 100, 1, dtype=int)
    range_slowk = numpy.arange(2, 100, 1, dtype=int)
    range_slowd = numpy.arange(2, 100, 1, dtype=int)
    bestret, bestret_series, parameters = OptimizeKD(
        df_MXFR1,
        range_fastk,
        range_slowk,
        range_slowd
    )
    print('KD bestret:'+str(bestret))
    print('KD MDD:'+str(backtesttool.calculateMDD(bestret_series)))
    plt.plot(numpy.log10(
        backtesttool.prefixProd(bestret_series)), color='green')
    plt.title('KD Profit(log)')
    plt.show()

#########################################
# 5.3 RSI指標
###########################################
# 定義為n日內漲幅平均值/(n日內跌幅平均值+n日內漲幅平均值)
real = talib.RSI(close, timeperiod=14)
if (target == 'RSI'):
    # 計算漲跌幅,並且把漲幅寫到pos,把跌幅寫到neg
    pos = close.copy()-close.shift(1)
    neg = close.copy()-close.shift(1)
    pos[0] = pos[1]
    neg[0] = neg[1]
    pos[pos < 0] = 0
    neg[neg > 0] = 0
    # 轉成絕對值,拿掉正負號
    pos = pos.abs()
    neg = neg.abs()
    # 算平均值
    posSMA = talib.SMA(pos, 14)
    negSMA = talib.SMA(neg, 14)
    RSI = posSMA/((posSMA+negSMA))
    plt.plot(RSI[-100:-1]*100)
    plt.title('RSI(implement with SMA)')
    plt.show()
    plt.plot(real[-100:-1])
    plt.title('real')
    plt.show()
    # https://en.wikipedia.org/wiki/Moving_average#Modified_moving_average

    def SMMA(s_in, period):
        s_out = s_in.copy()
        for i in range(1, s_in.size, 1):
            if (i < period):
                s_out[i] = s_out[i-1]*i/(i+1)+s_in[i]/(i+1)
            else:
                s_out[i] = s_out[i-1]*(period-1)/(period)\
                    + s_in[i]/(period)
        return s_out
    posSMMA = SMMA(pos, 14)
    negSMMA = SMMA(neg, 14)
    RSI = posSMMA/((posSMMA+negSMMA))
    plt.plot(RSI[-100:-1]*100)
    plt.title('RSI(SMMA)')
    plt.show()

    real2 = talib.RSI(close[-100:-1], timeperiod=14)
    plt.plot(real[-80:-1], 'green')
    plt.plot(real2[-80:-1], 'red')
    plt.title('original RSI vs RSI with only 100 kbars as input')
    plt.show()
# 使用RSI往上穿越longTH做多,往下穿越shortTH做空的買賣策略
# longTH>shortTH,longTH預設值為70,shortTH預設值為30


def createSignalRSI(close,
                    timeperiod=14,          longTH=70,
                    shortTH=30):
    real = talib.RSI(close, timeperiod=timeperiod)

    ENABLESHORT = False
    if (ENABLESHORT):
        BuySignal = (real > longTH).astype(int)
        ShortSignal = (real < shortTH).astype(int)
        return BuySignal-ShortSignal
    else:
        BuySignal = (real > longTH).astype(int)
        return BuySignal
# 找出RSI買賣訊號的最佳化參數


def OptimizeRSI(
        df,
        range_period,  # =numpy.arange(2,100,1,dtype=int)
        range_longTH,  # =numpy.arange(2,100,1,dtype=int)
        range_shortTH  # =numpy.arange(2,100,1,dtype=int)
):

    openPrice = df['Open']
    closePrice = df['Close']
    bestret = 0
    bestret_series = []
    best_period = 0
    best_longTH = 0
    best_shortTH = 0
    for period in range_period:
        for longTH in range_longTH:
            for shortTH in range_shortTH:
                print("period:"+str(period))
                print("longTH:"+str(longTH))
                print("shortTH:"+str(shortTH))
                if (longTH <= shortTH):
                    continue
                # 製作買賣訊號
                BuySignal = createSignalRSI(closePrice,
                                            period,
                                            longTH,
                                            shortTH)
                # 對訊號進行回測
                retStrategy, ret_series = backtesttool.backtest_signal(
                    openPrice, BuySignal)
                # 如果結果比之前更好,就記錄下來
                if (bestret < retStrategy):
                    bestret = retStrategy
                    bestret_series = ret_series
                    best_period = period
                    best_longTH = longTH
                    best_shortTH = shortTH

    return bestret, bestret_series, (best_period, best_longTH, best_shortTH)


if (target == 'RSI'):
    # 最佳化period,longTH,shortTH
    range_period = numpy.arange(2, 100, 1, dtype=int)
    range_longTH = numpy.arange(0, 100, 1, dtype=int)
    range_shortTH = numpy.arange(0, 100, 1, dtype=int)
    bestret, bestret_series, parameters = OptimizeRSI(
        df_MXFR1,
        range_period,
        range_longTH,
        range_shortTH
    )
    print('RSI bestret:'+str(bestret))
    print('RSI MDD:'+str(backtesttool.calculateMDD(bestret_series)))
    plt.plot(numpy.log10(
        backtesttool.prefixProd(bestret_series)), color='green')
    plt.title('RSI Profit(log)')
    plt.show()

#########################################
# 5.4 布林通道
###########################################
upperband, middleband, lowerband = \
    talib.BBANDS(close,
                 timeperiod=5,
                 nbdevup=2,
                 nbdevdn=2,
                 matype=talib.MA_Type.SMA)

if (target == 'BBAND'):
    timeperiod = 20
    SmallStdDev = 1.0
    LargeStdDev = 2.0
    upperband_Small, middleband_Small, lowerband_Small = \
        talib.BBANDS(close,
                     timeperiod=timeperiod,
                     nbdevup=SmallStdDev,
                     nbdevdn=SmallStdDev,
                     matype=talib.MA_Type.SMA)
    upperband_Large, middleband_Large, lowerband_Large = \
        talib.BBANDS(close,
                     timeperiod=timeperiod,
                     nbdevup=LargeStdDev,
                     nbdevdn=LargeStdDev,
                     matype=talib.MA_Type.SMA)
    plt.plot(middleband_Small[-200:-1], color='green')
    plt.plot(upperband_Small[-200:-1], color='blue')
    plt.plot(lowerband_Small[-200:-1], color='blue')
    plt.plot(lowerband_Large[-200:-1], color='red')
    plt.plot(upperband_Large[-200:-1], color='red')
    plt.title('BollingerBand Example')
    plt.show()
# 這邊的布林通道交易訊號使用以下連結的
# https://www.investopedia.com/trading/using-bollinger-bands-to-gauge-trends/#:~:text=Bollinger%20Bands%C2%AE%20are%20a%20trading%20tool%20used%20to%20determine,lot%20of%20other%20relevant%20information.
# Create Multiple Bands for Greater Insight


def createSignalBBAND(close,
                      timeperiod=20,
                      SmallStdDev=1.0,
                      LargeStdDev=2.0):
    upperband_Small, middleband_Small, lowerband_Small = \
        talib.BBANDS(close,
                     timeperiod=timeperiod,
                     nbdevup=SmallStdDev,
                     nbdevdn=SmallStdDev,
                     matype=talib.MA_Type.SMA)
    upperband_Large, middleband_Large, lowerband_Large = \
        talib.BBANDS(close,
                     timeperiod=timeperiod,
                     nbdevup=LargeStdDev,
                     nbdevdn=LargeStdDev,
                     matype=talib.MA_Type.SMA)
    ENABLESHORT = True
    # 允許放空的訊號寫法
    if (ENABLESHORT):
        BuySignal = ((close >= upperband_Small) & (
            close <= upperband_Large)).astype(int)
        ShortSignal = ((close >= lowerband_Large) & (
            close <= lowerband_Small)).astype(int)
        return BuySignal-ShortSignal
    # 不允許放空的訊號寫法，兩個差在允許放空的部分多了ShortSignal
    else:
        BuySignal = ((close >= upperband_Small) & (
            close <= upperband_Large)).astype(int)
        return BuySignal
# 找出BBAND買賣訊號的最佳化參數


def OptimizeBBAND(
        df,
        range_period,  # =numpy.arange(2,100,1,dtype=int)
        range_SmallStdDev,  # =numpy.arange(0.5,5,0.5,dtype=float)
        range_LargeStdDev  # =numpy.arange(0.5,5,0.5,dtype=float)
):

    openPrice = df['Open']
    closePrice = df['Close']
    bestret = 0
    bestret_series = []
    best_period = 0
    best_SmallStdDev = 0
    best_LargeStdDev = 0
    for period in range_period:
        for SmallStdDev in range_SmallStdDev:
            for LargeStdDev in range_LargeStdDev:
                print("period:"+str(period))
                print("SmallStdDev:"+str(SmallStdDev))
                print("LargeStdDev:"+str(LargeStdDev))
                if (LargeStdDev <= SmallStdDev):
                    continue
                # 製作買賣訊號
                BuySignal = createSignalBBAND(closePrice,
                                              timeperiod=period,
                                              SmallStdDev=SmallStdDev,
                                              LargeStdDev=LargeStdDev)
                # 對訊號進行回測
                retStrategy, ret_series = backtesttool.backtest_signal(
                    openPrice, BuySignal)
                # 如果結果比之前更好,就記錄下來
                if (bestret < retStrategy):
                    bestret = retStrategy
                    bestret_series = ret_series
                    best_period = period
                    best_SmallStdDev = SmallStdDev
                    best_LargeStdDev = LargeStdDev

    return bestret, bestret_series, (best_period, best_SmallStdDev, best_LargeStdDev)


if (target == 'BBAND'):
    # 最佳化period,SmallStdDev,LargeStdDev
    range_period = numpy.arange(2, 100, 1, dtype=int)
    range_SmallStdDev = numpy.arange(0.5, 3, 0.1, dtype=float)
    range_LargeStdDev = numpy.arange(0.5, 3, 0.1, dtype=float)
    bestret, bestret_series, parameters = OptimizeBBAND(
        df_MXFR1,
        range_period,
        range_SmallStdDev,
        range_LargeStdDev
    )
    print('BBAND bestret:'+str(bestret))
    print('BBAND MDD:'+str(backtesttool.calculateMDD(bestret_series)))
    plt.plot(numpy.log10(
        backtesttool.prefixProd(bestret_series)), color='green')
    plt.title('BBAND Profit(log)')
    plt.show()
#########################################
# 5.5 價格通道
###########################################
# 價格通道就是過去一段時間的最高價和最低價組成的通道線
# 當最高價創新高的時候做多,最低價創新低的時候做空

if (target == 'PriceChannel'):
    period = 20
    channel_high = high.rolling(period).max()
    channel_low = low.rolling(period).min()

    plt.plot(close[-50:-1], color='green')
    plt.plot(channel_high[-50:-1], color='blue')
    plt.plot(channel_low[-50:-1], color='blue')
    plt.plot(high[-50:-1], color='red', marker='o')
    plt.plot(low[-50:-1], color='green', marker='o')
    plt.title('PriceChannel Example')
    plt.show()


def createSignalPriceChannel(
        df, period):
    high = df['High']
    low = df['Low']
    # 創新高買進訊號
    BuySignal = (high == high.rolling(period).max()).astype(int)
    # 創新低買進訊號
    SellSignal = (low == low.rolling(period).min()).astype(int)
    signal = BuySignal-SellSignal
    # 上面的買賣訊號只有在穿過通道線的時候才有值,這邊用一些小技巧把中間的數值也填上去
    signal[signal == 0] = float("NaN")
    signal[0] = 0
    signal = signal.fillna(method="ffill")
    ENABLESHORT = False
    if (not ENABLESHORT):
        signal[signal < 0] = 0
    return signal
# 找出價格通道買賣訊號的最佳化參數


def OptimizePriceChannel(
        df,
        range_period  # =numpy.arange(2,100,1,dtype=int)
):
    openPrice = df['Open']
    closePrice = df['Close']
    bestret = 0
    bestret_series = []
    best_period = 0
    for period in range_period:
        print("period:"+str(period))
        # 製作買賣訊號
        BuySignal = createSignalPriceChannel(df, period)
        # 對訊號進行回測
        retStrategy, ret_series = backtesttool.backtest_signal(
            openPrice, BuySignal)
        # 如果結果比之前更好,就記錄下來
        if (bestret < retStrategy):
            bestret = retStrategy
            bestret_series = ret_series
            best_period = period

    return bestret, bestret_series, (best_period)


if (target == 'PriceChannel'):
    # 最佳化period
    range_period = numpy.arange(2, 1000, 1, dtype=int)
    bestret, bestret_series, parameters = OptimizePriceChannel(
        df_MXFR1,
        range_period
    )
    print('PriceChannel bestret:'+str(bestret))
    print('PriceChannel MDD:'+str(backtesttool.calculateMDD(bestret_series)))
    plt.plot(numpy.log10(
        backtesttool.prefixProd(bestret_series)), color='green')
    plt.title('PriceChannel Profit(log)')
    plt.show()
    
"""

#########################################
# 5.6. 網格交易策略
###########################################

# 根據乖離率低買高賣的策略
# 在加密貨幣試過現成的網格交易機器人,感覺滿有意思的,所以寫了自己的版本


def createGridSignal(
    df,
    BiasUpperLimit,
    UpperLimitPosition,
    BiasLowerLimit,
    LowerLimitPosition,
    BiasPeriod,
):

    close = df["close"]

    Bias = close / close.rolling(window=BiasPeriod).mean()
    # Bias = Bias.fillna(method='bfill')
    Bias = Bias.bfill()
    positiondiff = UpperLimitPosition - LowerLimitPosition
    biasdiff = BiasUpperLimit - BiasLowerLimit
    position = LowerLimitPosition + (Bias - BiasLowerLimit) * positiondiff / biasdiff
    """
    sets the position to LowerLimitPosition for those elements in the position array where the corresponding values
    in the Bias array are less than or equal to BiasLowerLimit. It's a way of adjusting the positions based on
    certain criteria or conditions.
    """
    position[Bias <= BiasLowerLimit] = LowerLimitPosition
    position[Bias >= BiasUpperLimit] = UpperLimitPosition
    return position


def OptimizeGrid(
    df,
    range_BiasUpper,  # =numpy.arange(1.0,2.0,0.1,dtype=float)
    range_UpperPosition,  # =numpy.arange(0.1,0.5,0.1,dtype=float)
    range_BiasLower,  # =numpy.arange(0.5,1.0,0.1,dtype=float)
    range_LowerPosition,  # =numpy.arange(0.5,1.0,0.1,dtype=float)
    range_period,  # =numpy.arange(2,100,1,dtype=int)
):
    openPrice = df["open"]
    closePrice = df["close"]
    bestret = 0
    bestret_series = []
    best_BiasUpper = 0
    best_UpperPosition = 0
    best_BiasLower = 0
    best_LowerPosition = 0
    best_period = 0
    for BiasUpper in range_BiasUpper:
        for UpperPosition in range_UpperPosition:
            for BiasLower in range_BiasLower:
                for LowerPosition in range_LowerPosition:
                    for period in range_period:
                        # print("BiasUpper:"+str(BiasUpper))
                        # print("UpperPosition:"+str(UpperPosition))
                        # print("BiasLower:"+str(BiasLower))
                        # print("LowerPosition:"+str(LowerPosition))
                        # print("period:"+str(period))
                        if BiasUpper <= BiasLower:
                            continue
                        if UpperPosition >= LowerPosition:
                            continue

                        # 製作買賣訊號
                        BuySignal = createGridSignal(
                            df,
                            BiasUpper,
                            UpperPosition,
                            BiasLower,
                            LowerPosition,
                            period,
                        )
                        # 對訊號進行回測
                        retStrategy, ret_series = backtesttool.backtest_signal(
                            openPrice, BuySignal
                        )
                        # 如果結果比之前更好,就記錄下來
                        if bestret < retStrategy:
                            bestret = retStrategy
                            bestret_series = ret_series
                            best_BiasUpper = BiasUpper
                            best_UpperPosition = UpperPosition
                            best_BiasLower = BiasLower
                            best_LowerPosition = LowerPosition
                            best_period = period

    return (
        bestret,
        bestret_series,
        (
            best_BiasUpper,
            best_UpperPosition,
            best_BiasLower,
            best_LowerPosition,
            best_period,
        ),
    )


if target == "Grid":
    import yfinance as yf

    # tw = yf.Ticker("0052.tw")
    # # default: interval='1d'
    # TW_hist = tw.history(period="5y")
    # us = yf.Ticker("00662.tw")
    # US_hist = us.history(period="5y")

    api = shioajiLogin(simulation=False)
    symbol = "0052"
    contract = kbar.getContract(api, name=symbol, the_type="stock")
    kbar.backFillKbars(
        api=api,
        contractObj=contract,
        # contractName="tw" + symbol,
        collectionName=symbol,
        start=kbar.sub_N_Days(days=5 * 365),
    )
    TW_hist = kbar.readFromDB("kbars", symbol)

    api = shioajiLogin(simulation=False)
    symbol = "0052"
    contract = kbar.getContract(api, name=symbol, the_type="stock")
    kbar.backFillKbars(
        api=api,
        contractObj=contract,
        collectionName=symbol,
        start=kbar.sub_N_Days(days=5 * 365),
    )
    TW_hist = kbar.readFromDB("kbars", symbol)

    symbol = "00662"
    contract = kbar.getContract(api, name=symbol, the_type="stock")
    kbar.backFillKbars(
        api=api,
        contractObj=contract,
        collectionName=symbol,
        start=kbar.sub_N_Days(days=5 * 365),
    )
    US_hist = kbar.readFromDB("kbars", symbol)

    # 兩邊歷史資料長度不一樣,取交集
    idx = numpy.intersect1d(TW_hist.index, US_hist.index)
    TW_hist = TW_hist.loc[idx]
    US_hist = US_hist.loc[idx]

    TW_open = TW_hist["open"]
    TW_close = TW_hist["close"]
    TW_high = TW_hist["high"]
    TW_low = TW_hist["low"]

    US_open = US_hist["open"]
    US_close = US_hist["close"]
    US_high = US_hist["high"]
    US_low = US_hist["low"]

    kbars = pd.DataFrame(
        {
            "ts": TW_close.index,
            "close": TW_close / US_close,
            "open": TW_open / US_open,
            "high": TW_high / US_low,
            "low": TW_low / US_high,
        }
    ).dropna()
    # 最佳化 BiasUpper,BiasLower,period
    range_BiasUpper = numpy.arange(1.0, 2.0, 0.1, dtype=float)
    range_UpperPosition = numpy.arange(0.1, 0.2, 0.1, dtype=float)
    range_BiasLower = numpy.arange(0.5, 1.0, 0.1, dtype=float)
    range_LowerPosition = numpy.arange(0.9, 1.0, 0.1, dtype=float)
    range_period = numpy.arange(2, 100, 1, dtype=int)
    bestret, bestret_series, parameters = OptimizeGrid(
        kbars,
        range_BiasUpper,
        range_UpperPosition,
        range_BiasLower,
        range_LowerPosition,
        range_period,
    )
    (
        best_BiasUpper,
        best_UpperPosition,
        best_BiasLower,
        best_LowerPosition,
        best_period,
    ) = parameters

    # 最佳化 range_UpperPosition,range_LowerPosition,range_period
    range_BiasUpper = numpy.arange(
        best_BiasUpper, best_BiasUpper + 0.1, 0.1, dtype=float
    )
    range_UpperPosition = numpy.arange(0.1, 0.5, 0.1, dtype=float)
    range_BiasLower = numpy.arange(
        best_BiasLower, best_BiasLower + 0.1, 0.1, dtype=float
    )
    range_LowerPosition = numpy.arange(0.5, 1.0, 0.1, dtype=float)
    range_period = numpy.arange(2, 100, 1, dtype=int)
    bestret, bestret_series, parameters = OptimizeGrid(
        kbars,
        range_BiasUpper,
        range_UpperPosition,
        range_BiasLower,
        range_LowerPosition,
        range_period,
    )
    (
        best_BiasUpper,
        best_UpperPosition,
        best_BiasLower,
        best_LowerPosition,
        best_period,
    ) = parameters

    # 最佳化 BiasUpper,BiasLower,range_period
    range_BiasUpper = numpy.arange(1.0, 2.0, 0.1, dtype=float)
    range_UpperPosition = numpy.arange(
        best_UpperPosition, best_UpperPosition + 0.1, 0.1, dtype=float
    )
    range_BiasLower = numpy.arange(0.5, 1.0, 0.1, dtype=float)
    range_LowerPosition = numpy.arange(
        best_LowerPosition, best_LowerPosition + 0.1, 0.1, dtype=float
    )
    range_period = numpy.arange(2, 100, 1, dtype=int)
    bestret, bestret_series, parameters = OptimizeGrid(
        kbars,
        range_BiasUpper,
        range_UpperPosition,
        range_BiasLower,
        range_LowerPosition,
        range_period,
    )

    ### 跨市網格交易報酬計算 ###
    (
        best_BiasUpper,
        best_UpperPosition,
        best_BiasLower,
        best_LowerPosition,
        best_period,
    ) = parameters

    print("best params:\n")
    print("best_BiasUpper:", best_BiasUpper)
    print("best_BiasLower:", best_BiasLower)
    print("best_UpperPosition:", best_UpperPosition)
    print("best_LowerPosition:", best_LowerPosition)
    print("best_period:", best_period)

    position = createGridSignal(
        kbars,
        best_BiasUpper,
        best_UpperPosition,
        best_BiasLower,
        best_LowerPosition,
        best_period,
    )
    buyTW = position
    buyUS = 1.0 - position

    retTW, retseriesTW = backtesttool.backtest_signal(
        TW_open, buyTW, tradecost=0.0000176
    )
    retUS, retseriesUS = backtesttool.backtest_signal(
        US_open, buyUS, tradecost=0.0000176
    )
    retseries = (retseriesTW - 1.0) + (retseriesUS - 1.0) + 1.0
    prefixProfit = backtesttool.prefixProd(retseries)
    # plt.plot(buyTW,color='red')
    print("strategyMDD:", backtesttool.calculateMDD(retseries))
    print("USMDD:", backtesttool.calculateMDD_fromClose(US_close))
    print("TWMDD:", backtesttool.calculateMDD_fromClose(TW_close))
    print("strategyProfit:", (prefixProfit.tolist()[-1] / prefixProfit.tolist()[0]) - 1)
    print("USProfit:", (US_close.tolist()[-1] / US_close.tolist()[0]) - 1)
    print("TWProfit:", (TW_close.tolist()[-1] / TW_close.tolist()[0]) - 1)
    plt.plot(numpy.log10(backtesttool.prefixProd(retseries)), color="green")
    plt.title("Grid Profit(log)")
    plt.show()
