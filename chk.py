parameters = {
        "BiasUpperLimit": 2.0,
        "UpperLimitPosition": 0.4,
        "BiasLowerLimit": 0.899999,
        "LowerLimitPosition": 0.899999,
        "BiasPeriod": 6,
    }

def calculateSharetarget(ma, upperprice, lowerprice):
    global uppershare, lowershare
    # 計算目標部位百分比
    shareTarget = calculateGrid(ma, upperprice, lowerprice)

    # move to order_cb
    # money=initmoney+g_settlement
    # no reset settlement after update money is required coz of using initmoney
    
    money = 0

    # 計算機器人裡面有多少資產(現金+股票)
    # upperprice=166
    # lowerprice=77
    uppershare=246
    lowershare=92
    capitalInBot = money + uppershare * upperprice + lowershare * lowerprice
    
    # 計算目標部位(股數)
    uppershareTarget = int(shareTarget * capitalInBot / upperprice)
    lowershareTarget = int((1.0 - shareTarget) * capitalInBot / lowerprice)

    # 紀錄目標部位(股數)
    print('uppershareTarget =', uppershareTarget)
    print('lowershareTarget =', lowershareTarget)
    uppershare = uppershareTarget
    lowershare = lowershareTarget

    
def calculateGrid(MA, upperprice, lowerprice):    
    # 計算目標部位百分比
    BiasUpperLimit = parameters["BiasUpperLimit"]
    UpperLimitPosition = parameters["UpperLimitPosition"]
    BiasLowerLimit = parameters["BiasLowerLimit"]
    LowerLimitPosition = parameters["LowerLimitPosition"]
    BiasPeriod = parameters["BiasPeriod"]
    # compute 乖離 rate
    Bias = (upperprice / lowerprice) / MA
    shareTarget = (Bias - BiasLowerLimit) / (BiasUpperLimit - BiasLowerLimit)
    shareTarget = (
        shareTarget * (UpperLimitPosition - LowerLimitPosition) + LowerLimitPosition
    )
    shareTarget = max(shareTarget, UpperLimitPosition)
    shareTarget = min(shareTarget, LowerLimitPosition)
    # print('0052 shareTaget:', shareTarget)
    return shareTarget

def update_sma(current_sma, look_back, new_price):
  """
  This function updates the SMA with today's closing price.

  Args:
      current_sma: The current value of the SMA.
      look_back: The number of days used to calculate the SMA.
      new_price: Today's closing price.

  Returns:
      The updated SMA value.
  """
  return (current_sma * (look_back - 1) + new_price) / look_back

def main():
    # uppershare=246
    # lowershare=92
    lowerprice=80
    upperprice=170
    # starting_value = 180
    reduction_pct = 1  # Percentage reduction (easier to read)
    ma = 2.1418
    for i in range(1, 11):
        # current_value = starting_value * (1 - reduction_pct / 100) ** i
        # starting_value = current_value
        
        # print(f"Iteration {i}: Value = {current_value:.2f}")        
        
        
        
        calculateSharetarget(ma, upperprice=upperprice, lowerprice=lowerprice)
        upperprice=upperprice*0.973
        lowerprice=lowerprice*1.002 
        ma=update_sma(ma, 6, upperprice/lowerprice)
        print('ma:', ma)
if __name__ == '__main__':
    main()
