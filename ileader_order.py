from ShioajiLogin import shioajiLogin
import pandas as pd
import shioaji.order as stOrder
import shioaji.shioaji


def calculate_profit(buy_price, sell_price, quantity):
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

# break even: 0.0108 after discount 

def get_position_qty(self, symbol):
    self.api.update_status(self.api.stock_account)
    portfolio = self.api.list_positions(
        api.stock_account, unit=shioaji.constant.Unit.Share
    )
    df_positions = pd.DataFrame(s.__dict__ for s in portfolio)

    position = df_positions[df_positions["code"] == symbol]
    if position.empty:
        return 0
    else:
        return int(position["quantity"].values[0])


g_upperid = "0052"
g_lowerid = "00664R"
symbols = [g_upperid, g_lowerid]
bought_price_dic = {g_upperid: 189.7, g_lowerid: 3.74}
api = shioajiLogin(simulation=False)
qty = {}
for symbol in symbols:
    qty[symbol] = get_position_qty(symbol)
calculate_profit(bought_price_dic[symbol], stockPrice[symbol], qty[symbol])
